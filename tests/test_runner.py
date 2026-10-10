"""Behavioral regressions; no network, accounts, or model calls required."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
NAME = ROOT.name
SKILL = ROOT / "skills" / NAME
SCRIPT = SKILL / "scripts/review_runner.py"
spec = importlib.util.spec_from_file_location("review_runner", SCRIPT)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
GOOD = {"verdict": "approved", "review_quality": "valid", "summary": "No material defect in the supplied example.",
        "findings": [], "remaining_risks": [], "rubric_results": []}
FINDING = {"severity": "high", "category": "correctness", "location": "example.py:2", "claim": "Wrong return value.",
           "evidence": "Example returns 3; acceptance criterion requires 2.", "recommended_action": "Return 2."}

MOCK = r'''
import json, os, pathlib, subprocess, sys, time
args = sys.argv[1:]
if '--version' in args:
    print('mock-review-cli 1.0'); sys.exit(0)
if '--help' in args:
    print('--output-schema --output-last-message --sandbox --ignore-user-config --ephemeral --json-schema --tools --setting-sources --strict-mcp-config --effort'); sys.exit(0)
if args == ['auth', 'status'] or args == ['login', 'status']:
    print('{"loggedIn": true}'); sys.exit(0)
request = sys.stdin.read()
mode = os.environ.get('MOCK_MODE', 'success')
model = args[args.index('--model') + 1] if '--model' in args else 'default'
record = pathlib.Path(os.environ['MOCK_RECORD'])
with record.open('a', encoding='utf-8') as f:
    f.write(json.dumps({'argv': args, 'cwd': os.getcwd(), 'stdin': request, 'nested': os.environ.get('CLAUDECODE')}) + '\n')
if mode == 'fallback' and model == 'unavailable':
    print('Requested model not available', file=sys.stderr); sys.exit(7)
if mode == 'network':
    print('Connection to model unavailable: socket network failure', file=sys.stderr); sys.exit(7)
if mode == 'auth':
    print('Not authenticated; API key invalid token=secret-for-test', file=sys.stderr); sys.exit(7)
if mode == 'sleep':
    subprocess.Popen([sys.executable, '-c', 'import pathlib,time;time.sleep(2);pathlib.Path(' + repr(os.environ['MOCK_CHILD_MARKER']) + ').write_text("survived")'])
    time.sleep(10)
if mode == 'mutation':
    pathlib.Path(os.environ['MOCK_REPO']).joinpath('untracked.txt').write_text('changed during review')
if mode == 'missing':
    sys.exit(0)
review = json.loads(os.environ['MOCK_REVIEW'])
if '--output-schema' in args:
    pathlib.Path(args[args.index('--output-last-message') + 1]).write_text(json.dumps(review), encoding='utf-8')
    print(json.dumps({'type': 'thread.started', 'thread_id': 'synthetic-session'}))
else:
    outer = {'subtype': 'success', 'is_error': False, 'structured_output': review, 'session_id': 'synthetic-session'}
    if mode == 'outer-error':
        outer['is_error'] = True; outer['subtype'] = 'error_max_turns'
    print(json.dumps(outer))
'''


class TransportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="review tests with spaces ")
        self.directory = Path(self.temp.name)
        self.bundle = self.directory / "bundle with spaces.md"
        self.bundle.write_text("# Synthetic bundle\nLiteral `code`, $(), 'quotes', Unicode ✓; no project content.", encoding="utf-8")
        self.result = self.directory / "result.json"
        self.mock = self.directory / "mock reviewer.py"
        self.mock.write_text(MOCK, encoding="utf-8")
        self.record = self.directory / "invocations.jsonl"
        self.env = dict(os.environ, MOCK_REVIEW=json.dumps(GOOD), MOCK_RECORD=str(self.record),
                        MOCK_MODE="success", CODEX_HOME=str(self.directory / "codex home"),
                        CLAUDECODE="parent-session", MOCK_CHILD_MARKER=str(self.directory / "child-survived"))
        for key in ("CLAUDE_REVIEW_MODEL", "CODEX_REVIEW_MODEL", "CLAUDE_REVIEW_FALLBACK_MODEL", "CODEX_REVIEW_FALLBACK_MODEL"):
            self.env.pop(key, None)

    def tearDown(self):
        self.temp.cleanup()

    def run_cli(self, backend="claude", extra=(), mode="success", script=SCRIPT):
        env = dict(self.env, MOCK_MODE=mode)
        process = subprocess.run([sys.executable, str(script), "run", "--backend", backend,
                                  "--cli", str(self.mock), "--bundle", str(self.bundle), "--result", str(self.result),
                                  "--timeout", "15", *extra], env=env, capture_output=True, text=True,
                                 encoding="utf-8", timeout=25)
        result = json.loads(self.result.read_text(encoding="utf-8")) if self.result.exists() else json.loads(process.stdout)
        return process, result

    def calls(self):
        return [json.loads(line) for line in self.record.read_text(encoding="utf-8").splitlines()]

    def test_both_backends_launch_and_validate_literal_arguments(self):
        for backend in ("claude", "codex"):
            with self.subTest(backend=backend):
                process, result = self.run_cli(backend)
                self.assertEqual(process.returncode, 0, process.stderr)
                self.assertEqual(result["verdict"], "approved")
                self.assertEqual(result["session_id"], "synthetic-session")
                call = self.calls()[-1]
                self.assertIn("$()", call["stdin"])
                self.assertIn("✓", call["stdin"])
                self.assertNotEqual(Path(call["cwd"]), ROOT)
                self.assertIsNone(call["nested"])
                if backend == "claude":
                    argv = call["argv"]
                    self.assertEqual(argv[argv.index("--tools") + 1], "")
                    self.assertEqual(json.loads(argv[argv.index("--mcp-config") + 1]), {"mcpServers": {}})
                    self.assertIsInstance(json.loads(argv[argv.index("--json-schema") + 1]), dict)
                else:
                    self.assertIn("read-only", call["argv"])
                    self.assertIn("--ignore-user-config", call["argv"])

    def test_missing_executable_writes_failure_and_replaces_stale_approval(self):
        self.result.write_text(json.dumps({"result": "success", "verdict": "approved"}), encoding="utf-8")
        process, result = self.run_cli(extra=("--cli", str(self.directory / "missing.exe")))
        self.assertNotEqual(process.returncode, 0)
        self.assertEqual(result["result"], "setup_needed")
        self.assertIsNone(result["verdict"])
        self.assertIn("does not exist", result["errors"])

    def test_os_launch_error_persists_envelope(self):
        bad = self.directory / "not-executable.exe"
        bad.write_text("not an executable", encoding="utf-8")
        process, result = self.run_cli(extra=("--cli", str(bad)))
        self.assertNotEqual(process.returncode, 0)
        self.assertEqual(result["result"], "launch_failure")
        self.assertTrue(result["errors"])

    def test_missing_bundle_is_explicit_failure(self):
        self.bundle.unlink()
        process, result = self.run_cli()
        self.assertNotEqual(process.returncode, 0)
        self.assertIsNone(result["verdict"])
        self.assertTrue(result["errors"])

    def test_success_exit_without_codex_final_file_is_invalid(self):
        process, result = self.run_cli("codex", mode="missing")
        self.assertEqual(process.returncode, 4)
        self.assertEqual(result["result"], "invalid_output")

    def test_claude_outer_error_cannot_be_approval(self):
        process, result = self.run_cli(mode="outer-error")
        self.assertEqual(process.returncode, 4)
        self.assertEqual(result["result"], "invalid_output")
        self.assertIsNone(result["verdict"])

    def test_model_fallback_is_explicit_and_only_for_availability(self):
        process, result = self.run_cli(extra=("--model", "unavailable", "--fallback-model", "supported"), mode="fallback")
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(result["reviewer_model"], "supported")
        self.assertEqual([a["model"] for a in result["attempts"]], ["unavailable", "supported"])
        self.assertIn("explicitly configured fallback", process.stderr)

    def test_network_error_does_not_cycle_models(self):
        process, result = self.run_cli(extra=("--model", "unavailable", "--fallback-model", "supported"), mode="network")
        self.assertNotEqual(process.returncode, 0)
        self.assertEqual(len(result["attempts"]), 1)
        self.assertEqual(result["attempts"][0]["failure_kind"], "network")

    def test_auth_failure_keeps_diagnostics_and_redacts_console(self):
        process, result = self.run_cli(mode="auth")
        self.assertNotEqual(process.returncode, 0)
        self.assertEqual(result["result"], "setup_needed")
        self.assertNotIn("secret-for-test", result["errors"])
        self.assertNotIn("secret-for-test", process.stderr)
        self.assertTrue((Path(result["diagnostics_dir"]) / "attempt-1-stderr.log").is_file())

    def test_timeout_reports_heartbeat_and_stops_child_tree(self):
        process, result = self.run_cli(mode="sleep", extra=("--timeout", "0.7", "--heartbeat", "0.2"))
        self.assertEqual(result["result"], "timeout", process.stderr)
        self.assertEqual(process.returncode, 3)
        self.assertIn("Reviewer running", process.stderr)
        time.sleep(2.2)
        self.assertFalse(Path(self.env["MOCK_CHILD_MARKER"]).exists(), "Timed-out child escaped cancellation")

    @unittest.skipUnless(os.name == "nt", "Windows process-tree permissions")
    def test_windows_cleanup_denial_is_visible_and_parent_is_stopped(self):
        denied = subprocess.CompletedProcess(["taskkill"], 1, b"", b"Access is denied")
        with patch.object(runner.subprocess, "run", return_value=denied):
            with self.assertRaises(runner.ReviewError) as caught:
                runner.execute([sys.executable, "-c", "import time; time.sleep(10)"], self.directory, 0.2)
        self.assertEqual(caught.exception.status, "launch_failure")
        self.assertIn("Access is denied", str(caught.exception))
        self.assertIn("Parent stopped; descendants may remain", str(caught.exception))

    def test_degraded_content_is_nonzero_and_never_approved(self):
        sample = copy.deepcopy(GOOD)
        sample["review_quality"] = "degraded_content"
        self.env["MOCK_REVIEW"] = json.dumps(sample)
        process, result = self.run_cli()
        self.assertEqual(process.returncode, 4)
        self.assertEqual(result["result"], "not_verified")
        self.assertIsNone(result["verdict"])

    def test_rubric_partial_coverage_is_not_verified(self):
        rubric = self.directory / "rubric.json"
        rubric.write_text('["R1", "R2"]', encoding="utf-8")
        sample = copy.deepcopy(GOOD)
        sample["rubric_results"] = [{"item": "R1", "result": "PASS", "evidence": "Supplied line 1."}]
        self.env["MOCK_REVIEW"] = json.dumps(sample)
        process, result = self.run_cli(extra=("--rubric-items", str(rubric)))
        self.assertEqual(process.returncode, 4)
        self.assertEqual(result["missing_rubric_items"], ["R2"])

    def test_codex_config_model_and_provider_survive_isolation(self):
        config_dir = Path(self.env["CODEX_HOME"])
        config_dir.mkdir()
        (config_dir / "config.toml").write_text('model = "configured-model"\nmodel_provider = "custom"\n[model_providers.custom]\nname = "Local gateway"\nbase_url = "https://example.invalid/v1"\nwire_api = "responses"\n', encoding="utf-8")
        process, result = self.run_cli("codex")
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(result["model_source"], "codex_config")
        self.assertIn('model_provider="custom"', self.calls()[0]["argv"])

    def test_standard_codex_default_does_not_import_builder_model(self):
        config_dir = Path(self.env["CODEX_HOME"])
        config_dir.mkdir()
        (config_dir / "config.toml").write_text('model = "builder-only-model"\n', encoding="utf-8")
        process, result = self.run_cli("codex")
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(result["model_source"], "cli_default")
        self.assertNotIn("--model", self.calls()[0]["argv"])
        process, result = self.run_cli("codex", extra=("--model", "configured"))
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(result["reviewer_model"], "builder-only-model")

    def test_unwritable_result_still_returns_failure_envelope(self):
        self.result.mkdir()
        process = subprocess.run([sys.executable, str(SCRIPT), "run", "--backend", "claude", "--cli", str(self.mock),
                                  "--bundle", str(self.bundle), "--result", str(self.result)], env=self.env,
                                 capture_output=True, text=True, encoding="utf-8", timeout=15)
        self.assertEqual(process.returncode, 6)
        self.assertIsNone(json.loads(process.stdout)["verdict"])
        self.assertIn("Cannot write requested result", process.stderr)

    def make_repo(self):
        repo = self.directory / "git repo"
        repo.mkdir()
        subprocess.run(["git", "-C", str(repo), "init", "-q"], check=True, capture_output=True)
        (repo / "untracked.txt").write_text("before", encoding="utf-8")
        return repo

    def test_repository_mutation_invalidates_success(self):
        repo = self.make_repo()
        self.env["MOCK_REPO"] = str(repo)
        process, result = self.run_cli(mode="mutation", extra=("--repo", str(repo)))
        self.assertEqual(process.returncode, 5, process.stderr)
        self.assertEqual(result["result"], "mutation_detected")
        self.assertIsNone(result["verdict"])

    def test_unchanged_repository_completes_real_review(self):
        repo = self.make_repo()
        process, result = self.run_cli(extra=("--repo", str(repo), "--scope", "untracked.txt"))
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(result["mutation_check"], "unchanged")

    def test_result_inside_repository_is_rejected_without_writing(self):
        repo = self.make_repo()
        self.result = repo / "result.json"
        process, result = self.run_cli(extra=("--repo", str(repo)))
        self.assertNotEqual(process.returncode, 0)
        self.assertFalse(self.result.exists())
        self.assertEqual(result["result"], "input_error")

    def test_installed_selftest_works_without_repository_test_files(self):
        installed = self.directory / "isolated installed skill"
        shutil.copytree(SKILL, installed)
        process = subprocess.run([sys.executable, str(installed / "scripts/review_runner.py"), "selftest",
                                  "--backend", "claude", "--cli", str(self.mock)], env=self.env,
                                 capture_output=True, text=True, encoding="utf-8", timeout=20)
        self.assertEqual(process.returncode, 0, process.stderr)
        report = json.loads(process.stdout)
        self.assertEqual(report["result"], "pass")
        self.assertFalse(report["ready_for_audit"])
        self.assertEqual(report["live_probe"], "not_verified")
        self.assertFalse(self.record.exists(), "Offline test must not generate remotely")

    def test_bash_entrypoint_uses_a_working_python_instead_of_a_path_alias(self):
        bash = shutil.which("bash")
        if not bash and os.name == "nt":
            candidate = Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Git/bin/bash.exe"
            bash = str(candidate) if candidate.is_file() else None
        if not bash:
            self.skipTest("Bash unavailable")
        backend = "claude" if NAME.startswith("claude-") else "codex"
        env = dict(self.env, **{backend.upper() + "_REVIEW_CLI": str(self.mock)})
        process = subprocess.run([bash, str((SKILL / "scripts/selftest.sh").as_posix())],
                                 env=env, capture_output=True, text=True, encoding="utf-8", timeout=20)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(json.loads(process.stdout)["result"], "pass")

    def test_selftest_live_probe_is_single_json_and_no_source(self):
        process = subprocess.run([sys.executable, str(SCRIPT), "selftest", "--backend", "claude",
                                  "--cli", str(self.mock), "--live-probe"], env=self.env,
                                 capture_output=True, text=True, encoding="utf-8", timeout=20)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertTrue(json.loads(process.stdout)["ready_for_audit"])
        self.assertEqual(len(self.calls()), 1)
        self.assertIn("No repository content", self.calls()[0]["stdin"])


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.schema = runner.read_json(SKILL / "references/review-schema.json")

    def parse(self, value, rubric=()):
        return runner.parse_review("codex", json.dumps(value), self.schema, rubric)

    def test_all_required_fields_and_types_are_validated(self):
        for field in GOOD:
            with self.subTest(field=field):
                broken = copy.deepcopy(GOOD)
                del broken[field]
                with self.assertRaises(runner.ReviewError):
                    self.parse(broken)

    def test_bad_finding_evidence_severity_location_and_extra_fields(self):
        for field, bad in [("severity", "low"), ("evidence", " "), ("location", ""), ("claim", 123), ("invented", "extra")]:
            with self.subTest(field=field):
                sample = copy.deepcopy(GOOD)
                sample.update(verdict="revise", findings=[dict(FINDING, **{field: bad})])
                with self.assertRaises(runner.ReviewError):
                    self.parse(sample)

    def test_verdict_inconsistency_rejected(self):
        with self.assertRaises(runner.ReviewError):
            self.parse(dict(GOOD, verdict="revise"))

    def test_degraded_review_can_be_honest_without_invented_findings(self):
        result = self.parse(dict(GOOD, verdict="revise", review_quality="degraded_content"))
        self.assertEqual(result[1], "degraded_content")

    def test_terminal_provider_error_takes_priority_over_startup_warnings(self):
        events = json.dumps({"type": "turn.failed", "error": {"message": "The selected model is not supported for this account."}})
        diagnostic = runner.terminal_diagnostic("codex", events, "startup websocket warning")
        self.assertEqual(runner.failure_kind(diagnostic), "model_unavailable")

    def test_approved_rubric_fail_unknown_and_duplicate_rejected(self):
        for entries in [[{"item": "R1", "result": "FAIL", "evidence": "line 1"}],
                        [{"item": "wrong", "result": "PASS", "evidence": "line 1"}],
                        [{"item": "R1", "result": "PASS", "evidence": "line 1"}] * 2]:
            with self.subTest(entries=entries), self.assertRaises(runner.ReviewError):
                self.parse(dict(GOOD, rubric_results=entries), ["R1"])

    def test_unverifiable_rubric_cannot_verify_approval(self):
        result = self.parse(dict(GOOD, rubric_results=[{"item": "R1", "result": "UNVERIFIABLE", "evidence": "Not supplied"}]), ["R1"])
        self.assertEqual(result[1], "degraded_content")

    def test_windows_npm_shim_resolves_without_shell(self):
        with tempfile.TemporaryDirectory() as directory:
            shim = Path(directory) / "codex.cmd"
            shim.write_text("npm shim")
            entry = Path(directory) / "node_modules/@openai/codex/bin/codex.js"
            entry.parent.mkdir(parents=True)
            entry.write_text("// synthetic")
            with patch.object(runner.shutil, "which", return_value="node.exe"):
                command = runner.command_for_path(shim, "codex")
                self.assertEqual(command[0], "node.exe")
                self.assertEqual(len(command), 2)
                self.assertTrue(Path(command[1]).samefile(entry))


class InstallationTests(unittest.TestCase):
    def test_repeat_install_preserves_previous_copy_and_new_complete_copy(self):
        with tempfile.TemporaryDirectory(prefix="installed skill ") as directory:
            root = Path(directory) / "skills"
            command = [sys.executable, str(ROOT / "scripts/install.py"), "--skills-root", str(root)]
            first = subprocess.run(command, capture_output=True, text=True, timeout=15)
            self.assertEqual(first.returncode, 0, first.stderr)
            old = root / NAME
            (old / "personal-marker.txt").write_text("preserve me")
            second = subprocess.run(command, capture_output=True, text=True, timeout=15)
            self.assertEqual(second.returncode, 0, second.stderr)
            backups = list((root.parent / "skill-backups").glob(NAME + "-*"))
            self.assertEqual(len(backups), 1)
            self.assertEqual((backups[0] / "personal-marker.txt").read_text(), "preserve me")
            self.assertTrue((old / "scripts/review_runner.py").is_file())
            self.assertFalse((old / "personal-marker.txt").exists())


if __name__ == "__main__":
    unittest.main()
