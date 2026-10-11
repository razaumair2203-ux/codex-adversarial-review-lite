#!/usr/bin/env python3
"""Self-contained, observable CLI review transport. Python 3.11+, no packages."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import tomllib
import uuid

SKILL = Path(__file__).resolve().parent.parent
PROTOCOL_VERSION = 2
_selection_spec = importlib.util.spec_from_file_location("review_model_selection", SKILL / "scripts/model_selection.py")
selection = importlib.util.module_from_spec(_selection_spec)
_selection_spec.loader.exec_module(selection)

SYNTHETIC_BUNDLE = (
    "# Synthetic model/effort availability probe\nNo repository content. Complete review scope.\n"
    "## Request and acceptance criteria\nReview add_one for integer inputs: return n + 1. "
    "No other features are required.\n## synthetic_example.py\n"
    "```python\ndef add_one(n):\n    return n + 1\n```\n"
    "## Verification evidence\nInspection: add_one(1) = 2; add_one(-1) = 0. No external tests run.\n"
)


class ReviewError(Exception):
    def __init__(self, status, message):
        self.status = status
        super().__init__(message)


def announce(message):
    print("[adversarial-review] " + message, file=sys.stderr, flush=True)


def safe_text(value):
    text = str(value)
    text = re.sub(r"(?i)(bearer\s+|(?:api[_-]?key|token|password)\s*[=:]\s*)[^\s,\"}]+",
                  r"\1[REDACTED]", text)
    return re.sub(r"\b(?:sk-[\w-]{12,}|gh[pousr]_[\w]{12,})\b", "[REDACTED]", text)[-2000:]


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        with temporary.open("w", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def stop_process(process):
    tree_error = None
    if os.name == "nt":
        try:
            stopped = subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                                     capture_output=True, timeout=15)
            if stopped.returncode:
                tree_error = "Process-tree cancellation could not be verified: " + safe_text(
                    stopped.stderr.decode("utf-8", "replace") or stopped.stdout.decode("utf-8", "replace"))
        except (OSError, subprocess.SubprocessError) as error:
            tree_error = "Process-tree cancellation failed: " + safe_text(error)
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    if process.poll() is None:
        process.kill()
    process.wait(timeout=15)
    if tree_error:
        raise ReviewError("launch_failure", tree_error + ". Parent stopped; descendants may remain. Inspect local processes before retrying.")


def execute(command, cwd, timeout, stdin=None, stdout=None, stderr=None, heartbeat=0):
    """Drain output to files, close stdin, and stop the process tree on interruption."""
    flags = {"start_new_session": True} if os.name != "nt" else {
        "creationflags": subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP}
    started = time.monotonic()
    env = dict(os.environ)
    env.setdefault("PYTHONUTF8", "1")
    # A deliberate independent Claude child must not inherit the nested-session marker.
    env.pop("CLAUDECODE", None)
    env.pop("CLAUDE_CODE_ENTRYPOINT", None)
    with tempfile.TemporaryFile() as fallback_out, tempfile.TemporaryFile() as fallback_err:
        process = subprocess.Popen(command, cwd=cwd, env=env, stdin=stdin or subprocess.DEVNULL,
                                   stdout=stdout or fallback_out, stderr=stderr or fallback_err,
                                   **flags)
        next_notice = heartbeat
        try:
            while process.poll() is None:
                elapsed = time.monotonic() - started
                if heartbeat and elapsed >= next_notice:
                    announce(f"Reviewer running ({int(elapsed)}s); logs are being captured.")
                    next_notice += heartbeat
                if elapsed >= timeout:
                    raise ReviewError("timeout", f"Reviewer exceeded {timeout:g}s; process tree stopped.")
                time.sleep(min(0.2, max(0.01, timeout - elapsed)))
        except BaseException:
            stop_process(process)
            raise
        fallback_out.seek(0)
        fallback_err.seek(0)
        return process.returncode, fallback_out.read().decode("utf-8", "replace"), \
            fallback_err.read().decode("utf-8", "replace")


def command_for_path(path, backend):
    path = Path(path).expanduser().resolve()
    if not path.is_file():
        raise ReviewError("setup_needed", f"Reviewer executable does not exist: {path}")
    if path.suffix.lower() in (".cmd", ".bat", ".ps1"):
        # Avoid cmd.exe quoting/injection entirely for npm's Windows shims.
        package = "@openai/codex/bin/codex.js" if backend == "codex" else "@anthropic-ai/claude-code/cli.js"
        entry = path.parent / "node_modules" / package
        node = shutil.which("node")
        if node and entry.is_file():
            return [node, str(entry)]
        raise ReviewError("setup_needed", "Windows shim cannot be resolved to its Node entrypoint. "
                          f"Set {backend.upper()}_REVIEW_CLI to the native executable or npm shim with its package installed.")
    if path.suffix.lower() == ".py":
        return [sys.executable, str(path)]
    if path.suffix.lower() in (".js", ".mjs"):
        node = shutil.which("node")
        if not node:
            raise ReviewError("setup_needed", "Node.js is required for this reviewer entrypoint.")
        return [node, str(path)]
    return [str(path)]


def discover(backend, override=None, prefer_latest=False):
    explicit = override or os.environ.get(backend.upper() + "_REVIEW_CLI") or \
        os.environ.get(backend.upper() + "_BIN")
    if explicit:
        return command_for_path(shutil.which(explicit) or explicit, backend)
    found = shutil.which(backend)
    if found and not prefer_latest:
        return command_for_path(found, backend)
    home = Path.home()
    candidates = [home / ".local/bin" / (backend + (".exe" if os.name == "nt" else ""))]
    if found:
        candidates.insert(0, Path(found))
    if os.name == "nt":
        candidates += [home / "AppData/Roaming/npm" / (backend + ".cmd")]
        extensions = home / ".vscode/extensions"
        glob = "openai.chatgpt-*/bin/windows-x86_64/codex.exe" if backend == "codex" else \
            "anthropic.claude-code-*/resources/native-binary/claude.exe"
        candidates += sorted(extensions.glob(glob), key=lambda p: p.stat().st_mtime, reverse=True)
    if prefer_latest:
        verified, seen = [], set()
        for candidate in candidates[:12]:
            if not candidate.is_file():
                continue
            try:
                command = command_for_path(candidate, backend)
                identity = tuple(command)
                if identity in seen:
                    continue
                seen.add(identity)
                version, _ = preflight(backend, command, tempfile.gettempdir())
                number = re.search(r"(\d+)\.(\d+)\.(\d+)", version)
                if number:
                    verified.append((tuple(map(int, number.groups())), command))
            except (ReviewError, OSError, subprocess.SubprocessError):
                continue
        if verified:
            return max(verified, key=lambda item: item[0])[1]
        raise ReviewError("setup_needed", "No installed compatible reviewer CLI passed version/help checks. Set an explicit --cli path; no CLI was installed or changed.")
    for candidate in candidates:
        if candidate.is_file():
            return command_for_path(candidate, backend)
    raise ReviewError("setup_needed", f"{backend} CLI not found. Install it, reopen your terminal, "
                      f"or set {backend.upper()}_REVIEW_CLI to its absolute path.")


def preflight(backend, command, cwd):
    code, version, err = execute(command + ["--version"], cwd, 20)
    if code:
        raise ReviewError("setup_needed", "CLI version probe failed: " + safe_text(err or version))
    help_args = ["exec", "--help"] if backend == "codex" else ["--help"]
    code, help_text, err = execute(command + help_args, cwd, 20)
    if code:
        raise ReviewError("setup_needed", "CLI help probe failed: " + safe_text(err or help_text))
    required = ["--output-schema", "--output-last-message", "--sandbox", "--ignore-user-config"] \
        if backend == "codex" else ["--json-schema", "--tools", "--setting-sources", "--strict-mcp-config"]
    missing = [flag for flag in required if flag not in help_text]
    if missing:
        raise ReviewError("setup_needed", "Update the reviewer CLI; required flags missing: " + ", ".join(missing))
    return version.strip(), help_text


def codex_configuration():
    config_path = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))) / "config.toml"
    if not config_path.is_file():
        return {}
    try:
        with config_path.open("rb") as stream:
            return tomllib.load(stream)
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise ReviewError("setup_needed", "Cannot read Codex config: " + safe_text(error)) from error


def preference_path(backend):
    if backend == "claude":
        home = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex")))
    else:
        home = Path(os.environ.get("CLAUDE_CONFIG_DIR", str(Path.home() / ".claude")))
    return home / "adversarial-review" / (backend + ".json")


def preferences(backend):
    path = preference_path(backend)
    if not path.is_file():
        return {}
    value = read_json(path)
    if not isinstance(value, dict) or not isinstance(value.get("model"), str) or not value["model"].strip() or \
            value.get("reasoning") not in (*selection.EFFORTS, "highest", "cli-default"):
        raise ReviewError("setup_needed", "Invalid reviewer preference file: " + str(path))
    return value


def validate(value, schema, location="review"):
    kind = schema.get("type")
    types = {"object": dict, "array": list, "string": str}
    if kind in types and not isinstance(value, types[kind]):
        raise ReviewError("invalid_output", f"{location} must be {kind}.")
    if "enum" in schema and value not in schema["enum"]:
        raise ReviewError("invalid_output", f"{location} has an invalid value.")
    if kind == "object":
        properties = schema.get("properties", {})
        if any(key not in value for key in schema.get("required", [])):
            raise ReviewError("invalid_output", f"{location} lacks required fields.")
        if schema.get("additionalProperties") is False and set(value) - set(properties):
            raise ReviewError("invalid_output", f"{location} has unexpected fields.")
        for key, item in value.items():
            if key in properties:
                validate(item, properties[key], location + "." + key)
    elif kind == "array":
        for index, item in enumerate(value):
            validate(item, schema.get("items", {}), f"{location}[{index}]")
    elif kind == "string" and len(value.strip()) < schema.get("minLength", 0):
        raise ReviewError("invalid_output", f"{location} must not be blank.")


def parse_review(backend, raw, schema, rubric_items):
    try:
        outer = json.loads(raw)
        if backend == "claude":
            if not isinstance(outer, dict) or outer.get("is_error") is True or \
                    (outer.get("subtype") and outer["subtype"] != "success"):
                raise ReviewError("invalid_output", "Claude returned an error or incomplete result envelope.")
            review = outer.get("structured_output")
            if review is None and isinstance(outer.get("result"), str):
                review = json.loads(outer["result"])
            session_id = outer.get("session_id")
        else:
            review, session_id = outer, None
        validate(review, schema)
    except (ValueError, TypeError) as error:
        raise ReviewError("invalid_output", "Reviewer did not return valid JSON matching the review contract.") from error
    findings = review["findings"]
    if (review["verdict"] == "approved" and findings) or \
            (review["verdict"] == "revise" and not findings and review["review_quality"] == "valid"):
        raise ReviewError("invalid_output", "Verdict and finding count are inconsistent.")
    entries = review["rubric_results"]
    reported = [entry["item"] for entry in entries]
    if len(set(reported)) != len(reported) or set(reported) - set(rubric_items):
        raise ReviewError("invalid_output", "Rubric results contain duplicate or unknown items.")
    if review["verdict"] == "approved" and any(entry["result"] == "FAIL" for entry in entries):
        raise ReviewError("invalid_output", "Approved verdict contradicts a rubric FAIL.")
    quality = review["review_quality"]
    missing = sorted(set(rubric_items) - set(reported))
    skipped = len(missing) + sum(entry["result"] == "UNVERIFIABLE" for entry in entries)
    if rubric_items and (missing or skipped > len(rubric_items) / 2 or
                        (review["verdict"] == "approved" and not any(e["result"] == "PASS" for e in entries))):
        quality = "degraded_content"
    return review, quality, session_id, missing


def git_bytes(repo, *args):
    process = subprocess.run(["git", "-C", str(repo), *args], stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, timeout=30)
    if process.returncode:
        raise ReviewError("setup_needed", "Git inspection failed: " + safe_text(process.stderr.decode("utf-8", "replace")))
    return process.stdout


def snapshot(repo, scope=()):
    repo = Path(repo).resolve()
    git_bytes(repo, "rev-parse", "--show-toplevel")
    digest = hashlib.sha256()
    for args in [("rev-parse", "--verify", "HEAD"), ("status", "--porcelain=v1", "-z", "--untracked-files=all"),
                 ("diff", "--binary"), ("diff", "--cached", "--binary")]:
        if args[0] == "rev-parse":
            # An unborn repository is valid; HEAD's absence must still be recorded.
            head = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, timeout=30)
            data = head.stdout if head.returncode == 0 else b"unborn-head"
        else:
            data = git_bytes(repo, *args)
        digest.update(json.dumps(args).encode() + b"\0" + data + b"\0")
    names = set(git_bytes(repo, "ls-files", "--others", "--exclude-standard", "-z").split(b"\0")) - {b""}
    names.update(os.fsencode(path) for path in scope)
    for name in sorted(names):
        path = repo / os.fsdecode(name)
        if not path.resolve().is_relative_to(repo):
            raise ReviewError("input_error", "Snapshot path leaves the repository: " + os.fsdecode(name))
        digest.update(name + b"\0")
        if path.is_symlink():
            digest.update(b"symlink:" + os.fsencode(os.readlink(path)))
        elif path.is_file():
            with path.open("rb") as stream:
                while chunk := stream.read(1024 * 1024):
                    digest.update(chunk)
        else:
            digest.update(b"missing")
    return digest.hexdigest()


def failure_kind(text):
    # Priority matters: a permissions/network message containing 'model' is not a fallback signal.
    patterns = [
        ("authentication", r"not (?:logged|signed) in|not authenticated|login required|invalid.*(?:api.?key|token)|unauthorized|authentication.*(?:fail|require)|401"),
        ("quota", r"quota|rate.?limit|insufficient.*(?:credit|balance)|usage.?limit|429"),
        ("permission", r"permission denied|sandbox|trusted directory|access denied"),
        ("configuration", r"unknown option|unexpected argument|unrecognized argument|invalid config|not a valid.*schema"),
        ("network", r"connection|network|socket|timed? out|dns|proxy|TLS|SSL"),
        ("effort_unavailable", r"(?:effort|reasoning).{0,100}(?:unsupported|not supported|invalid|not available|unknown variant)|(?:unsupported|invalid|unknown variant).{0,100}(?:effort|reasoning)"),
        ("model_unavailable", r"(?:model.{0,80}(?:not found|not available|not supported|unavailable|unsupported|does not exist|no access))|(?:(?:unknown|invalid|unsupported|unavailable|no access|do not have access).{0,50}model)"),
    ]
    for kind, pattern in patterns:
        if re.search(pattern, text, re.I):
            return kind
    return "launch"


def terminal_diagnostic(backend, stdout, stderr):
    if backend == "codex":
        for line in reversed(stdout.splitlines()):
            try:
                event = json.loads(line)
                if event.get("type") == "turn.failed":
                    return str(event.get("error", {}).get("message", "")) or stderr
                if event.get("type") == "error":
                    return str(event.get("message", "")) or stderr
            except (ValueError, AttributeError):
                pass
    return stderr or stdout


def build_command(backend, cli, help_text, schema_path, prompt, cwd, final, model, args, config):
    if backend == "claude":
        command = cli + ["-p", "--permission-mode", "dontAsk", "--tools", "", "--disable-slash-commands",
                         "--setting-sources", "", "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}',
                         "--settings", '{"disableAllHooks":true,"autoMemoryEnabled":false}',
                         "--output-format", "json", "--json-schema", json.dumps(read_json(schema_path)),
                         "--system-prompt", prompt, "--no-session-persistence",
                         "--max-turns", str(args.max_turns), "--max-budget-usd", str(args.max_budget_usd)]
        if model:
            command += ["--model", model]
        if args.reasoning:
            if "--effort" not in help_text or args.reasoning not in selection.EFFORTS:
                raise ReviewError("input_error", "This Claude CLI/effort setting is unsupported; use its advertised effort levels.")
            command += ["--effort", args.reasoning]
        return command
    command = cli + ["exec", "--ignore-user-config", "--sandbox", "read-only", "-c", "approval_policy=never",
                     "-c", "web_search=\"disabled\"", "--skip-git-repo-check", "--cd", str(cwd),
                     "--output-schema", str(schema_path), "--output-last-message", str(final), "--json", "--color", "never"]
    if "--ephemeral" in help_text:
        command += ["--ephemeral"]
    if model:
        command += ["--model", model]
    if args.reasoning:
        command += ["-c", "model_reasoning_effort=" + json.dumps(args.reasoning)]
    # Preserve explicitly configured custom providers without inheriting hooks/MCP/skills config.
    provider = config.get("model_provider")
    if provider and provider != "openai":
        details = config.get("model_providers", {}).get(provider)
        if not isinstance(details, dict):
            raise ReviewError("setup_needed", "Configured Codex model provider has no definition.")
        command += ["-c", "model_provider=" + json.dumps(provider)]
        for key, value in details.items():
            command += ["-c", "model_providers." + json.dumps(provider) + "." + key + "=" + toml_value(value)]
    command += ["-"]
    return command


def toml_value(value):
    if isinstance(value, dict):
        return "{" + ",".join(json.dumps(key) + "=" + toml_value(item) for key, item in value.items()) + "}"
    if isinstance(value, list):
        return "[" + ",".join(toml_value(item) for item in value) + "]"
    if isinstance(value, (str, bool, int, float)):
        return json.dumps(value)
    raise ReviewError("setup_needed", "Unsupported value in Codex provider config.")


def select_model(args, cli, work, primary, config, result_path, envelope):
    custom = config.get("model_provider", "openai") != "openai"
    if custom and (primary in ("highest", "cli-default") or args.reasoning == "highest"):
        raise ReviewError("setup_needed", "A custom provider is configured. Its CLI catalog may describe OpenAI models rather than that gateway. Specify --model configured (or an explicit ID) AND --reasoning <effort>|cli-default; automatic strongest selection cannot verify the gateway's capability order.")
    announce("Reading reviewer model/effort catalog; no review bundle is sent during selection.")
    models = [] if custom else selection.catalog(args.backend, cli, work, stop_process)
    write_json(work / "model-catalog.json", models)
    requested_model = None if primary == "highest" else primary
    if primary == "cli-default":
        default = next((row for row in models if row.get("isDefault") or row.get("value") == "default"), None)
        if not default:
            raise ReviewError("setup_needed", "Catalog does not identify its default; specify a model or --model highest.")
        requested_model = selection.model_id(default)
    requested_effort = None if args.reasoning in (None, "highest") else args.reasoning
    if requested_effort == "cli-default":
        requested_effort = "cli-default"  # An explicit opt-out is never lowered by selection.
    probe_number = 0
    def verify(model, effort):
        nonlocal probe_number
        probe_number += 1
        envelope["selection_phase"] = {"probe": probe_number, "model": model, "effort": effort}
        write_json(result_path, envelope)
        announce(f"Verifying advertised model {model}, effort {effort or 'unsupported by model'} with synthetic content only.")
        probe_bundle = work / "selection-probe.md"
        probe_bundle.write_text(SYNTHETIC_BUNDLE, encoding="utf-8")
        probe = argparse.Namespace(**vars(args))
        probe.bundle, probe.result = str(probe_bundle), str(work / f"selection-probe-{probe_number}.json")
        probe.repo, probe.scope, probe.rubric_items = None, [], None
        probe.model, probe.reasoning = model, effort or "cli-default"
        probe.fallback_model, probe._selection_probe, probe._cli_command = None, True, cli
        probe.timeout = min(args.timeout, 180)
        probe.max_budget_usd = min(args.max_budget_usd, 0.75)
        code = run_review(probe, emit=False)
        result = read_json(probe.result)
        attempts = result.get("attempts", [])
        resolved = result.get("reported_model") if code == 0 else None
        return {"available": code == 0, "resolved_model": resolved,
                "failure_kind": attempts[-1].get("failure_kind") if attempts else result["result"],
                "error": result.get("errors"), "result_path": probe.result}
    try:
        chosen = selection.choose(models, args.backend, verify, requested_model, requested_effort)
    except selection.SelectionError as error:
        raise ReviewError("setup_needed", str(error)) from error
    envelope["selection"] = chosen
    envelope.pop("selection_phase", None)
    envelope["model_source"] = chosen["source"]
    args.reasoning = None if chosen["effort"] == "cli-default" else chosen["effort"]
    announce(f"Selected {chosen['model']}, effort {chosen['effort'] or 'none advertised'}; synthetic availability verified.")
    return chosen["model"]


def run_review(args, emit=True):
    result_path = Path(args.result).expanduser().resolve()
    started = time.monotonic()
    envelope = dict(protocol_version=PROTOCOL_VERSION, result="running", verdict=None, review_quality="unknown",
                    review=None, errors=None, session_id=None, reviewer_model=None, model_source=None,
                    backend=args.backend, attempts=[], diagnostics_dir=None, reviewer_effort=None, selection=None,
                    mutation_check="not_checked" if args.repo else "not_requested")
    work = None
    code = 3
    before = None
    result_allowed = True
    try:
        repo = Path(args.repo).resolve() if args.repo else None
        if repo and result_path.is_relative_to(repo):
            result_allowed = False
            raise ReviewError("input_error", "Result and diagnostics must be outside the reviewed repository.")
        write_json(result_path, envelope)  # Replace any stale approval before probing or launching.
        if repo and Path(tempfile.gettempdir()).resolve().is_relative_to(repo):
            raise ReviewError("input_error", "OS temp directory is inside the reviewed repository; configure an external TEMP/TMPDIR.")
        work = Path(tempfile.mkdtemp(prefix="advreview-"))
        envelope["diagnostics_dir"] = str(work)
        announce(f"Starting {args.backend} review. Status: {result_path}; diagnostics: {work}")
        write_json(result_path, envelope)
        if args.timeout <= 0 or args.heartbeat <= 0 or args.max_turns <= 0 or args.max_budget_usd <= 0:
            raise ReviewError("input_error", "Timeout, heartbeat, turns, and budget must be positive.")
        bundle_path = Path(args.bundle).expanduser().resolve()
        bundle = bundle_path.read_text(encoding="utf-8-sig")
        if not bundle.strip():
            raise ReviewError("input_error", "Bundle is missing or empty.")
        if args.reasoning and args.reasoning not in (*selection.EFFORTS, "highest", "cli-default"):
            raise ReviewError("input_error", "Unknown reasoning level.")
        rubric_items = read_json(args.rubric_items) if args.rubric_items else []
        if not isinstance(rubric_items, list) or any(not isinstance(item, str) or not item.strip() for item in rubric_items) or \
                len(set(rubric_items)) != len(rubric_items):
            raise ReviewError("input_error", "Rubric items must be a JSON array of unique nonempty strings.")
        schema_path = SKILL / "references/review-schema.json"
        schema = read_json(schema_path)
        prompt = (SKILL / "references/reviewer-prompt.md").read_text(encoding="utf-8-sig")
        if rubric_items:
            bundle += "\n## Exact rubric item identifiers\n" + json.dumps(rubric_items, ensure_ascii=False)
        # Freeze the actual bytes sent, not a later reread of a mutable user file.
        frozen = work / "bundle.md"
        frozen.write_text((prompt + "\n\n" if args.backend == "codex" else "") + bundle, encoding="utf-8")
        saved = {} if args.model and args.reasoning else preferences(args.backend)
        env_model = os.environ.get(args.backend.upper() + "_REVIEW_MODEL")
        primary = args.model or env_model or saved.get("model")
        args.reasoning = args.reasoning or os.environ.get(args.backend.upper() + "_REVIEW_EFFORT") or saved.get("reasoning")
        if not primary or not args.reasoning:
            raise ReviewError("selection_needed", "Choose reviewer model AND effort before dispatch. Ask whether the user knows their available model; use inspect to show the CLI catalog when unsure. Choose --model MODEL --reasoning LEVEL, or explicitly choose highest/highest or cli-default/cli-default. A saved configure preference also supplies the choice.")
        if args.reasoning not in (*selection.EFFORTS, "highest", "cli-default"):
            raise ReviewError("input_error", "Unknown requested/saved reasoning level.")
        selecting = not getattr(args, "_selection_probe", False) and (primary == "highest" or args.reasoning == "highest" or
                    getattr(args, "verify_selection", False) or (bool(saved) and not args.model and not env_model))
        cli = getattr(args, "_cli_command", None) or discover(args.backend, args.cli, prefer_latest=selecting)
        version, help_text = preflight(args.backend, cli, work)
        envelope["cli_path"], envelope["cli_version"] = cli[0], version
        envelope["cli_command"] = cli
        config = codex_configuration() if args.backend == "codex" else {}
        fallback = None if getattr(args, "_selection_probe", False) else args.fallback_model or os.environ.get(args.backend.upper() + "_REVIEW_FALLBACK_MODEL")
        if selecting and fallback:
            raise ReviewError("input_error", "Automatic selection already verifies availability candidates. To use a deliberate full-review fallback, specify an explicit model and --reasoning <level>|cli-default.")
        if primary == "configured":
            primary = config.get("model")
            if not primary:
                raise ReviewError("setup_needed", "No top-level Codex model is configured; use cli-default or an explicit model.")
            envelope["model_source"] = "codex_config"
        elif primary == "cli-default" and not selecting:
            primary = None
            envelope["model_source"] = "cli_default"
        elif primary != "highest":
            envelope["model_source"] = "explicit"
        else:
            envelope["model_source"] = "pending_catalog"
        if selecting:
            primary = select_model(args, cli, work, primary, config, result_path, envelope)
        elif args.reasoning == "cli-default":
            args.reasoning = None
        envelope["reviewer_effort"] = args.reasoning or "cli_default"
        models = [primary]
        if fallback and fallback != primary:
            models.append(fallback)
        if repo:
            before = snapshot(repo, args.scope)
            write_json(work / "snapshot-before.json", {"digest": before, "scope": args.scope})
            envelope["mutation_check"] = "pending"
        # At most two attempts total. No automatic repeated full-bundle call or stale output reuse.
        for number, model in enumerate(models, 1):
            envelope["reviewer_model"] = model or "cli_default"
            attempt = {"number": number, "model": model or "cli_default", "effort": args.reasoning or "cli_default", "exit_code": None}
            envelope["attempts"].append(attempt)
            write_json(result_path, envelope)
            final = work / f"attempt-{number}-final.json"
            out_path = work / f"attempt-{number}-stdout.log"
            err_path = work / f"attempt-{number}-stderr.log"
            command = build_command(args.backend, cli, help_text, schema_path, prompt, work, final, model, args, config)
            announce(f"Launching reviewer attempt {number}, model {model or 'CLI/account default'}, effort {args.reasoning or 'CLI default'} ({version}).")
            with frozen.open("rb") as input_file, out_path.open("wb") as out_file, err_path.open("wb") as err_file:
                attempt["exit_code"], _, _ = execute(command, work, args.timeout, input_file, out_file, err_file, args.heartbeat)
            out_text = out_path.read_text(encoding="utf-8", errors="replace")
            err_text = err_path.read_text(encoding="utf-8", errors="replace")
            if attempt["exit_code"]:
                diagnostic = terminal_diagnostic(args.backend, out_text, err_text)
                kind = failure_kind(diagnostic)
                attempt["failure_kind"] = kind
                if kind == "model_unavailable" and number < len(models):
                    announce("Requested model unavailable; trying the explicitly configured fallback.")
                    continue
                status = "setup_needed" if kind in ("authentication", "configuration", "model_unavailable", "effort_unavailable") else "launch_failure"
                raise ReviewError(status, f"Reviewer exited {attempt['exit_code']} ({kind}). " + safe_text(diagnostic))
            if args.backend == "codex" and (not final.is_file() or not final.stat().st_size):
                raise ReviewError("invalid_output", "Codex exited without a nonempty final-message file.")
            raw = out_text if args.backend == "claude" else final.read_text(encoding="utf-8-sig")
            review, quality, session_id, missing = parse_review(args.backend, raw, schema, rubric_items)
            envelope.update(result="success" if quality == "valid" else "not_verified", review=review,
                            review_quality=quality, verdict=review["verdict"] if quality == "valid" else None,
                            session_id=session_id, missing_rubric_items=missing)
            if args.backend == "claude":
                models_used = list(json.loads(raw).get("modelUsage", {}))
                envelope["models_used"] = models_used
                if len(models_used) == 1:
                    envelope["reviewer_model"] = models_used[0]
                    envelope["reported_model"] = models_used[0]
                verified = (envelope.get("selection") or {}).get("verified_model")
                if verified and models_used != [verified]:
                    raise ReviewError("not_verified", "Claude's reported model changed after availability verification; refusing an unverified model substitution.")
            # Record the model reported by Codex's session metadata when available.
            if args.backend == "codex":
                for line in out_text.splitlines():
                    try:
                        event = json.loads(line)
                        if event.get("type") == "thread.started":
                            envelope["session_id"] = event.get("thread_id")
                        if event.get("type") == "session_meta" and event.get("payload", {}).get("model"):
                            envelope["reviewer_model"] = event["payload"]["model"]
                            envelope["reported_model"] = event["payload"]["model"]
                    except (ValueError, AttributeError):
                        pass
                verified = (envelope.get("selection") or {}).get("verified_model")
                if verified and envelope.get("reported_model") != verified:
                    raise ReviewError("not_verified", "Codex's reported model changed after availability verification; refusing an unverified model substitution.")
            code = 0 if quality == "valid" else 4
            break
    except KeyboardInterrupt:
        envelope.update(result="cancelled", errors="Review interrupted; no verified verdict.", verdict=None)
        code = 130
    except (ReviewError, selection.SelectionError) as error:
        if isinstance(error, selection.SelectionError):
            error = ReviewError("setup_needed", str(error))
        envelope.update(result=error.status, errors=safe_text(error), verdict=None,
                        review_quality="unknown" if error.status in ("invalid_output", "selection_needed") else "degraded_environmental")
        code = {"input_error": 2, "setup_needed": 2, "selection_needed": 2, "invalid_output": 4, "timeout": 3}.get(error.status, 3)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        envelope.update(result="launch_failure", errors=safe_text(error), verdict=None,
                        review_quality="degraded_environmental")
        code = 3
    finally:
        if before is not None:
            try:
                after = snapshot(repo, args.scope)
                write_json(work / "snapshot-after.json", {"digest": after, "scope": args.scope})
                envelope["mutation_check"] = "unchanged" if before == after else "changed"
                if before != after:
                    envelope.update(result="mutation_detected", verdict=None, errors="Repository changed during review. Do not apply fixes.")
                    code = 5
            except (ReviewError, OSError, subprocess.SubprocessError) as error:
                envelope.update(result="not_verified", verdict=None, mutation_check="failed", errors=safe_text(error))
                code = 5
        envelope["elapsed_seconds"] = round(time.monotonic() - started, 2)
        try:
            if result_allowed:
                write_json(result_path, envelope)
        except OSError as error:
            announce("Cannot write requested result: " + safe_text(error))
            print(json.dumps(envelope), flush=True)
            return 6
        announce(f"{envelope['result']}: {envelope['errors'] or envelope.get('verdict') or 'no verified verdict'}. Result: {result_path}")
    if emit:
        print(json.dumps(envelope, ensure_ascii=False), flush=True)
    return code


def inspect_models(args):
    result = {"result": "running", "backend": args.backend, "generation_requested": False}
    directory = Path(tempfile.mkdtemp(prefix="advreview-catalog-"))
    result["diagnostics_dir"] = str(directory)
    try:
        cli = discover(args.backend, args.cli, prefer_latest=True)
        version, _ = preflight(args.backend, cli, directory)
        auth_args = ["auth", "status"] if args.backend == "claude" else ["login", "status"]
        code, _, _ = execute(cli + auth_args, directory, 20)
        if code:
            raise ReviewError("setup_needed", "Reviewer authentication failed; run the provider's login command.")
        config = codex_configuration() if args.backend == "codex" else {}
        if config.get("model_provider", "openai") != "openai":
            raise ReviewError("setup_needed", "A custom provider requires its own advertised model/effort list; the public CLI catalog cannot establish gateway availability.")
        models = selection.catalog(args.backend, cli, directory, stop_process)
        write_json(directory / "model-catalog.json", models)
        result.update(result="success", cli_version=version, cli_command=cli, models=models,
                      saved_preference=preferences(args.backend), availability_verified=False,
                      note="Catalog choices are advertised capabilities; access is verified only after the user chooses a model/effort.")
    except (ReviewError, selection.SelectionError, OSError, ValueError, subprocess.SubprocessError) as error:
        result.update(result="setup_needed", errors=safe_text(error))
    if args.result:
        write_json(args.result, result)
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
    return 0 if result["result"] == "success" else 2


def selftest(args):
    checks = []
    with tempfile.TemporaryDirectory(prefix="advreview-selftest-") as directory:
        cwd = Path(directory)
        checks.append({"name": "python", "status": "pass", "detail": sys.version.split()[0]})
        try:
            probe = cwd / "write probe.json"
            write_json(probe, {"probe": "✓"})
            assert read_json(probe)["probe"] == "✓"
            checks.append({"name": "temp_write", "status": "pass", "detail": str(cwd)})
            schema = read_json(SKILL / "references/review-schema.json")
            sample = {"verdict": "approved", "review_quality": "valid", "summary": "Synthetic offline check",
                      "findings": [], "remaining_risks": [], "rubric_results": []}
            raw = json.dumps({"structured_output": sample}) if args.backend == "claude" else json.dumps(sample)
            parse_review(args.backend, raw, schema, [])
            checks.append({"name": "parser_resources", "status": "pass", "detail": "Installed schema and parser work without repository tests."})
            if not shutil.which("git"):
                raise ReviewError("setup_needed", "Install Git for real review mutation checks.")
            checks.append({"name": "git", "status": "pass", "detail": shutil.which("git")})
            prefer_latest = (args.model or os.environ.get(args.backend.upper() + "_REVIEW_MODEL") or "highest") == "highest" or args.reasoning in (None, "highest")
            cli = discover(args.backend, args.cli, prefer_latest=prefer_latest)
            version, _ = preflight(args.backend, cli, cwd)
            checks.append({"name": "reviewer_cli", "status": "pass", "detail": version + " at " + cli[0]})
            auth_args = ["auth", "status"] if args.backend == "claude" else ["login", "status"]
            code, auth, err = execute(cli + auth_args, cwd, 20)
            checks.append({"name": "authentication", "status": "pass" if code == 0 else "fail",
                           "detail": "CLI reports authenticated" if code == 0 else "Run " + args.backend + (" auth login" if args.backend == "claude" else " login")})
        except (ReviewError, OSError, ValueError, AssertionError, subprocess.SubprocessError) as error:
            checks.append({"name": "preflight", "status": "fail", "detail": safe_text(error)})
        offline_ok = all(check["status"] == "pass" for check in checks)
        live_result = None
        if args.live_probe and offline_ok:
            bundle = cwd / "synthetic bundle.md"
            bundle.write_text("# Synthetic transport check\nNo repository content. This is the complete synthetic review scope.\n"
                              "## Request and acceptance criteria\nReview add_one for integer inputs: return n + 1. "
                              "No type validation, I/O, concurrency, or other features are required.\n"
                              "## Diff: synthetic_example.py\n```python\ndef add_one(n):\n    return n + 1\n```\n"
                              "## Verification evidence\nBuilder inspection: add_one(1) = 2; add_one(-1) = 0. "
                              "No external tests run. Review the complete function supplied above.\n", encoding="utf-8")
            live_args = argparse.Namespace(**vars(args))
            live_args._cli_command = cli
            live_args.bundle, live_args.result = str(bundle), str(cwd / "live result.json")
            live_args.repo, live_args.scope, live_args.rubric_items = None, [], None
            live_code = run_review(live_args, emit=False)
            live_result = read_json(live_args.result)
            checks.append({"name": "live_probe", "status": "pass" if live_code == 0 else "fail",
                           "detail": live_result["result"], "diagnostics_dir": live_result["diagnostics_dir"]})
        okay = all(check["status"] == "pass" for check in checks)
        report = {"result": "pass" if okay else "fail", "checks": checks,
                  "live_probe": "passed" if live_result and live_result["result"] == "success" else "not_verified",
                  "ready_for_audit": bool(okay and live_result and live_result["result"] == "success")}
        if live_result:
            for key in ("selection", "reviewer_model", "reviewer_effort", "cli_version", "cli_command"):
                report[key] = live_result.get(key)
        if args.result:
            write_json(args.result, report)
        print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)
        return 0 if okay else 2


def main():
    # File/stdin protocol is UTF-8 even in a Windows console with a legacy code page.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="operation", required=True)
    for operation in ("run", "selftest"):
        sub = commands.add_parser(operation)
        sub.add_argument("--backend", required=True, choices=("claude", "codex"))
        sub.add_argument("--result", required=operation == "run")
        sub.add_argument("--cli", help="Absolute CLI path; overrides PATH discovery")
        sub.add_argument("--model", help="User choice or saved preference: model ID, highest, cli-default, configured (Codex)")
        sub.add_argument("--fallback-model", help="One explicit model fallback, only for availability errors")
        sub.add_argument("--reasoning", help="User choice or saved preference: effort level, highest, cli-default")
        sub.add_argument("--verify-selection", action="store_true", help="Verify the chosen explicit model/effort with synthetic content before sending the review bundle")
        sub.add_argument("--timeout", type=float, default=600)
        sub.add_argument("--heartbeat", type=float, default=15)
        sub.add_argument("--max-turns", type=int, default=8)
        sub.add_argument("--max-budget-usd", type=float, default=3)
        if operation == "run":
            sub.add_argument("--bundle", required=True)
            sub.add_argument("--repo", help="Reviewed Git root; enables automatic before/after mutation check")
            sub.add_argument("--scope", action="append", default=[], help="Reviewed relative path to hash explicitly")
            sub.add_argument("--rubric-items", help="JSON array of exact checklist item identifiers")
        else:
            sub.add_argument("--live-probe", action="store_true", help="One synthetic remote call; no repository content")
    prepare = commands.add_parser("prepare", help="Allocate native temp paths for the builder's Write tool")
    inspect = commands.add_parser("inspect", help="List advertised model/effort choices without generation")
    inspect.add_argument("--backend", required=True, choices=("claude", "codex"))
    inspect.add_argument("--cli")
    inspect.add_argument("--result")
    configure = commands.add_parser("configure", help="Save a reviewer-only local model/effort preference; does not change provider settings")
    configure.add_argument("--backend", required=True, choices=("claude", "codex"))
    configure.add_argument("--model", required=True)
    configure.add_argument("--reasoning", required=True, choices=(*selection.EFFORTS, "highest", "cli-default"))
    saved = commands.add_parser("preferences", help="Read reviewer-only local preference without CLI/auth/network access")
    saved.add_argument("--backend", required=True, choices=("claude", "codex"))
    args = parser.parse_args()
    if args.operation == "prepare":
        directory = Path(tempfile.mkdtemp(prefix="advreview-input-"))
        print(json.dumps({"directory": str(directory), "bundle_path": str(directory / "bundle.md"),
                          "result_path": str(directory / "result.json"), "rubric_items_path": str(directory / "rubric-items.json")}))
        return 0
    if args.operation == "inspect":
        return inspect_models(args)
    if args.operation == "preferences":
        print(json.dumps({"path": str(preference_path(args.backend)), "saved_preference": preferences(args.backend),
                          "generation_requested": False}))
        return 0
    if args.operation == "configure":
        path = preference_path(args.backend)
        write_json(path, {"model": args.model, "reasoning": args.reasoning})
        print(json.dumps({"result": "saved", "path": str(path), "model": args.model, "reasoning": args.reasoning,
                          "availability_verified": False}))
        return 0
    return run_review(args) if args.operation == "run" else selftest(args)


if __name__ == "__main__":
    raise SystemExit(main())
