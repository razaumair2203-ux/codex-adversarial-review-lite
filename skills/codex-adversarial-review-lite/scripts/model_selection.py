"""CLI catalogs and deterministic capability policy; Python standard library only."""
import json
import os
from pathlib import Path
import queue
import re
import subprocess
import threading
import time

EFFORTS = ("none", "minimal", "low", "medium", "high", "xhigh", "max", "ultra")


class SelectionError(Exception):
    pass


def catalog(backend, cli, directory, stop_process, timeout=35):
    """Metadata only: no user prompt, thread, tools, or generation request."""
    if backend == "claude":
        command = cli + ["-p", "--input-format", "stream-json", "--output-format", "stream-json", "--verbose",
                         "--permission-mode", "dontAsk", "--tools", "", "--disable-slash-commands",
                         "--setting-sources", "", "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}',
                         "--settings", '{"disableAllHooks":true,"autoMemoryEnabled":false}', "--no-session-persistence"]
    else:
        command = cli + ["app-server", "--listen", "stdio://", "-c", "mcp_servers={}",
                         "-c", "approval_policy=never", "-c", 'sandbox_mode="read-only"', "-c", "analytics.enabled=false"]
    events = queue.Queue(maxsize=256)
    env = dict(os.environ)
    env.pop("CLAUDECODE", None)
    env.pop("CLAUDE_CODE_ENTRYPOINT", None)
    flags = {"start_new_session": True} if os.name != "nt" else {
        "creationflags": subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP}
    with (Path(directory) / "catalog-stderr.log").open("wb") as err:
        process = subprocess.Popen(command, cwd=directory, env=env, stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, stderr=err, **flags)
        def reader():
            try:
                for line in process.stdout:
                    try:
                        event = json.loads(line)
                    except ValueError:
                        continue
                    if isinstance(event, dict):
                        try:
                            events.put_nowait(event)
                        except queue.Full:
                            # Do not leave a reader blocked when a noisy CLI exceeds the bound.
                            return
            finally:
                try:
                    events.put_nowait(None)
                except queue.Full:
                    pass
        thread = threading.Thread(target=reader, daemon=True)
        thread.start()
        deadline = time.monotonic() + timeout
        def send(value):
            process.stdin.write((json.dumps(value) + "\n").encode("utf-8"))
            process.stdin.flush()
        def receive(matches):
            while time.monotonic() < deadline:
                try:
                    event = events.get(timeout=max(0.01, deadline - time.monotonic()))
                except queue.Empty as error:
                    raise SelectionError("Model catalog timed out; no model was selected.") from error
                if event is None:
                    raise SelectionError("CLI exited before returning its model catalog. Inspect catalog-stderr.log.")
                if matches(event):
                    return event
                if event.get("type") == "control_request":
                    raise SelectionError("Catalog discovery requested permission/tool execution; stopped without approving it.")
            raise SelectionError("Model catalog timed out; no model was selected.")
        try:
            if backend == "claude":
                send({"type": "control_request", "request_id": "review-catalog", "request": {"subtype": "initialize", "hooks": {}}})
                event = receive(lambda e: e.get("type") == "control_response" and
                                e.get("response", {}).get("request_id") == "review-catalog")
                response = event.get("response", {})
                if response.get("subtype") != "success":
                    raise SelectionError("Claude catalog initialization failed: " + str(response.get("error", "unknown error")))
                models = response.get("response", {}).get("models")
            else:
                send({"id": 1, "method": "initialize", "params": {
                    "clientInfo": {"name": "independent-review-model-selector", "version": "1"},
                    "capabilities": {"experimentalApi": True}}})
                initialized = receive(lambda e: e.get("id") == 1)
                if "error" in initialized:
                    raise SelectionError("Codex catalog initialization failed: " + str(initialized["error"]))
                send({"method": "initialized", "params": {}})
                models, cursor, cursors = [], None, set()
                for page in range(20):
                    params = {"limit": 100, "includeHidden": False}
                    if cursor:
                        params["cursor"] = cursor
                    request_id = page + 2
                    send({"id": request_id, "method": "model/list", "params": params})
                    event = receive(lambda e: e.get("id") == request_id)
                    if "error" in event:
                        raise SelectionError("Codex model/list failed: " + str(event["error"]))
                    result = event.get("result", {})
                    data = result.get("data")
                    if not isinstance(data, list):
                        raise SelectionError("Codex model catalog has no model array.")
                    models.extend(data)
                    cursor = result.get("nextCursor")
                    if not cursor:
                        break
                    if cursor in cursors:
                        raise SelectionError("Codex model catalog repeated its pagination cursor.")
                    cursors.add(cursor)
                else:
                    raise SelectionError("Codex model catalog exceeded the page limit.")
            if not isinstance(models, list) or not models or any(not isinstance(m, dict) for m in models):
                raise SelectionError("CLI returned an empty or malformed model catalog. Update it or specify model and effort explicitly.")
            # Never persist the initialization account object, tokens, commands, or agents.
            fields = {"id", "model", "value", "displayName", "description", "hidden", "disabled", "available",
                      "supportedReasoningEfforts", "supportedEffortLevels", "supportsEffort", "isDefault", "upgrade"}
            return [{key: value for key, value in model.items() if key in fields} for model in models]
        except (AttributeError, TypeError) as error:
            raise SelectionError("CLI returned a malformed catalog protocol response; no model was selected.") from error
        finally:
            try:
                process.stdin.close()
            except OSError:
                pass
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                stop_process(process)
            thread.join(timeout=1)
            process.stdout.close()


def model_id(model):
    value = model.get("model") or model.get("value") or model.get("id")
    if not isinstance(value, str) or not value.strip():
        raise SelectionError("A model catalog entry has no usable identifier.")
    return value


def rank(model):
    """Explicit capability-family policy, provider descriptions and version tie-breaks.

    There is no provider strength score. This is a documented policy, not a claim
    that arbitrary future model names can be ranked objectively.
    """
    text = " ".join(str(model.get(k, "")) for k in ("model", "value", "displayName", "description")).lower()
    flagship = bool(re.search(r"most (?:capable|intelligent|powerful)|highest intelligence|frontier intelligence", text))
    families = (("mythos", 7), ("fable", 6), ("astra", 6), ("opus", 5), ("sol", 4),
                ("sonnet", 3), ("codex", 3), ("terra", 2), ("luna", 1), ("haiku", 1), ("mini", 1), ("nano", 1))
    family = next((score for name, score in families if re.search(r"\b" + name + r"\b", text)), 0)
    if not family and not flagship:
        # GPT number-only flagship catalogs remain common in older CLI releases.
        if re.search(r"\bgpt[- ]\d", text) and not re.search(r"\b(?:mini|nano)\b", text):
            family = 6 if re.search(r"\bpro\b", text) or flagship else 4
        else:
            raise SelectionError("Cannot establish capability order for model " + model_id(model) +
                                 "; specify reviewer:<model> and reasoning:<effort> rather than guessing.")
    old = bool(re.search(r"older|previous generation|legacy|deprecated", text))
    numbers = re.search(r"(?:gpt[- ]|(?:opus|sonnet|haiku|fable|mythos)[- ])(\d+)(?:[.\-](\d+))?", text)
    version = (int(numbers[1]), int(numbers[2] or 0)) if numbers else (0, 0)
    if not family and flagship:
        family = 8  # An explicitly described new flagship outranks known families.
    return (family, version, int(flagship), int(not old))


def candidates(models):
    active = [m for m in models if not m.get("hidden") and not m.get("disabled") and m.get("available") is not False]
    if not active:
        raise SelectionError("No available picker-visible review model was advertised.")
    # An unrankable new model is uncertainty, not permission to choose an older one silently.
    ordered = sorted(active, key=rank, reverse=True)
    unique, seen = [], set()
    for model in ordered:
        identifier = model_id(model)
        if identifier not in seen:
            unique.append(model)
            seen.add(identifier)
    return unique


def efforts(model, backend):
    values = model.get("supportedEffortLevels") if backend == "claude" else model.get("supportedReasoningEfforts")
    if backend == "claude" and model.get("supportsEffort") is False:
        return [None]
    if not isinstance(values, list) or not values:
        raise SelectionError("Model " + model_id(model) + " does not advertise effort capabilities; specify an effort explicitly.")
    levels = [value.get("reasoningEffort") if isinstance(value, dict) else value for value in values]
    if any(level not in EFFORTS for level in levels):
        raise SelectionError("Model advertises an unknown effort scale; specify a supported effort explicitly.")
    return sorted(set(levels), key=EFFORTS.index, reverse=True)


def choose(models, backend, verify, requested_model=None, requested_effort=None, limit=6):
    if requested_model:
        matched = next((m for m in models if requested_model in (m.get("model"), m.get("value"), m.get("id"))), None)
        if not matched and not requested_effort:
            raise SelectionError("Explicit model is absent from the CLI catalog; also specify reasoning:<effort> or reasoning:cli-default.")
        ordered = [matched or {"model": requested_model}]
    else:
        ordered = candidates(models)
    attempts = []
    for model in ordered:
        levels = [requested_effort] if requested_effort else efforts(model, backend)
        for effort in levels:
            if len(attempts) >= limit:
                raise SelectionError("Model/effort verification reached its six-probe limit. No full review was sent.")
            checked = verify(model_id(model), effort)
            attempts.append({"model": model_id(model), "effort": effort, **checked})
            if checked.get("available"):
                return {"model": model_id(model), "effort": effort, "verified_model": checked.get("resolved_model"),
                        "source": "explicit_model" if requested_model else "cli_catalog_capability_order",
                        "availability_verified": True, "probes": attempts}
            failure = checked.get("failure_kind")
            if failure == "effort_unavailable" and not requested_effort:
                continue
            if failure == "model_unavailable" and not requested_model:
                break
            raise SelectionError("Model verification stopped (" + str(failure) + "): " + str(checked.get("error", "unknown error")))
    raise SelectionError("No advertised model/effort combination passed verification. No full review was sent.")
