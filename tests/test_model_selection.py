"""Capability selection, account verification, and real subprocess catalog protocols."""
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

import test_runner as support
from test_runner import runner, SCRIPT

selector = runner.selection
CLAUDE_MODELS = [
    {"value": "sonnet", "displayName": "Sonnet 4.6", "supportsEffort": True,
     "supportedEffortLevels": ["low", "medium", "high"]},
    {"value": "default", "description": "Opus 4.6 · Most capable for complex work",
     "supportsEffort": True, "supportedEffortLevels": ["low", "medium", "high", "max"]},
]
CODEX_MODELS = [
    {"model": "gpt-6.1-sol", "description": "Latest workhorse", "isDefault": True,
     "supportedReasoningEfforts": [{"reasoningEffort": v} for v in ("low", "high", "max", "ultra")]},
    {"model": "gpt-6-astra", "description": "Frontier intelligence for the most demanding work",
     "supportedReasoningEfforts": [{"reasoningEffort": v} for v in ("low", "high", "max", "ultra")]},
]


class PolicyTests(unittest.TestCase):
    def test_astra_beats_newer_number_default_and_ultra_is_maximum(self):
        result = selector.choose(CODEX_MODELS, "codex", lambda *args: {"available": True})
        self.assertEqual((result["model"], result["effort"]), ("gpt-6-astra", "ultra"))

    def test_older_catalog_workhorse_sol_beats_balanced_terra(self):
        rows = [{"model": "gpt-5.6-sol", "supportedReasoningEfforts": ["ultra"]},
                {"model": "gpt-5.6-terra", "description": "Older balanced model for straightforward work",
                 "supportedReasoningEfforts": ["ultra"]}]
        result = selector.choose(rows, "codex", lambda *args: {"available": True})
        self.assertEqual(result["model"], "gpt-5.6-sol")

    def test_claude_strongest_alias_uses_advertised_max(self):
        result = selector.choose(CLAUDE_MODELS, "claude", lambda *args: {"available": True})
        self.assertEqual((result["model"], result["effort"]), ("default", "max"))

    def test_unavailable_model_moves_to_next_capability_not_default_effort(self):
        def verify(model, effort):
            return {"available": model != "gpt-6-astra", "failure_kind": "model_unavailable"}
        result = selector.choose(CODEX_MODELS, "codex", verify)
        self.assertEqual((result["model"], result["effort"]), ("gpt-6.1-sol", "ultra"))
        self.assertEqual(len(result["probes"]), 2)

    def test_unsupported_effort_uses_next_advertised_level_same_model(self):
        def verify(model, effort):
            return {"available": effort != "ultra", "failure_kind": "effort_unavailable"}
        result = selector.choose(CODEX_MODELS, "codex", verify)
        self.assertEqual((result["model"], result["effort"]), ("gpt-6-astra", "max"))

    def test_auth_quota_network_timeout_and_invalid_output_never_downgrade(self):
        for kind in ("authentication", "quota", "network", "timeout", "invalid_output"):
            calls = []
            def verify(*args):
                calls.append(args)
                return {"available": False, "failure_kind": kind}
            with self.subTest(kind=kind), self.assertRaises(selector.SelectionError):
                selector.choose(CODEX_MODELS, "codex", verify)
            self.assertEqual(len(calls), 1)

    def test_explicit_model_and_effort_are_never_substituted(self):
        calls = []
        def verify(*args):
            calls.append(args)
            return {"available": False, "failure_kind": "model_unavailable"}
        with self.assertRaises(selector.SelectionError):
            selector.choose(CODEX_MODELS, "codex", verify, "pinned", "max")
        self.assertEqual(calls, [("pinned", "max")])

    def test_unknown_models_and_unknown_effort_scales_fail_visibly(self):
        for models in ([{"model": "future-unknown"}],
                       [{"model": "gpt-6-astra", "supportedReasoningEfforts": ["future-level"]}]):
            with self.assertRaises(selector.SelectionError):
                selector.choose(models, "codex", lambda *args: {"available": True})

    def test_hidden_disabled_and_unavailable_models_are_excluded(self):
        rows = CODEX_MODELS + [{"model": "future-unknown", key: value} for key, value in
                              (("hidden", True), ("disabled", True), ("available", False))]
        self.assertEqual(len(selector.candidates(rows)), 2)

    def test_next_generation_claude_family_beats_older_opus_alias(self):
        models = CLAUDE_MODELS + [{"value": "fable", "description": "Fable 5.1",
                                  "supportedEffortLevels": ["high", "max"]}]
        result = selector.choose(models, "claude", lambda *args: {"available": True})
        self.assertEqual(result["model"], "fable")

    def test_newer_same_family_beats_older_entry_with_flagship_description(self):
        rows = [{"value": "claude-fable-5", "description": "Most capable for hardest tasks",
                 "supportedEffortLevels": ["max"]},
                {"value": "claude-fable-5-1", "description": "For your toughest challenges",
                 "supportedEffortLevels": ["max"]}]
        result = selector.choose(rows, "claude", lambda *args: {"available": True})
        self.assertEqual(result["model"], "claude-fable-5-1")

    def test_probe_limit_prevents_unbounded_calls(self):
        model = {"model": "gpt-6-astra", "supportedReasoningEfforts": list(selector.EFFORTS)}
        calls = []
        def verify(*args):
            calls.append(args)
            return {"available": False, "failure_kind": "effort_unavailable"}
        with self.assertRaises(selector.SelectionError):
            selector.choose([model], "codex", verify)
        self.assertEqual(len(calls), 6)

    def test_failure_classification_preserves_auth_priority(self):
        self.assertEqual(runner.failure_kind("Reasoning effort ultra is not supported"), "effort_unavailable")
        self.assertEqual(runner.failure_kind("Not authenticated; model reasoning effort unsupported"), "authentication")


class SelectionTransportTests(unittest.TestCase):
    setUp = support.TransportTests.setUp
    tearDown = support.TransportTests.tearDown
    calls = support.TransportTests.calls

    def run_cli(self, backend, mode="success", extra=()):
        self.env["MOCK_MODELS"] = json.dumps(CLAUDE_MODELS if backend == "claude" else CODEX_MODELS)
        return support.TransportTests.run_cli(self, backend, extra=("--model", "highest", "--reasoning", "highest", *extra), mode=mode)

    def test_both_real_catalog_protocols_probe_before_full_bundle(self):
        for backend, model, effort in (("claude", "default", "max"), ("codex", "gpt-6-astra", "ultra")):
            with self.subTest(backend=backend):
                self.record.unlink(missing_ok=True)
                process, result = self.run_cli(backend)
                self.assertEqual(process.returncode, 0, process.stderr)
                self.assertEqual(result["selection"]["model"], model)
                self.assertEqual(result["reviewer_effort"], effort)
                self.assertTrue(result["selection"]["availability_verified"])
                self.assertIsNone(result["selection"]["verified_model"], "A requested ID is not reported server-model metadata")
                calls = self.calls()
                self.assertEqual(len(calls), 2)
                self.assertIn("No repository content", calls[0]["stdin"])
                self.assertNotIn("Literal `code`", calls[0]["stdin"])
                self.assertIn("Literal `code`", calls[1]["stdin"])
                catalog = Path(result["diagnostics_dir"]) / "model-catalog.json"
                self.assertNotIn("do-not-persist", catalog.read_text())
                self.assertIn("Selected", process.stderr)

    def test_auth_failure_stops_before_user_content_is_sent(self):
        process, result = self.run_cli("codex", mode="auth")
        self.assertNotEqual(process.returncode, 0)
        self.assertIsNone(result["verdict"])
        self.assertEqual(len(self.calls()), 1)
        self.assertNotIn("Literal `code`", self.calls()[0]["stdin"])
        self.assertEqual(result["selection_phase"]["model"], "gpt-6-astra")

    def test_real_probe_effort_rejection_falls_back_to_advertised_max(self):
        process, result = self.run_cli("codex", mode="effort")
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(result["reviewer_effort"], "max")
        self.assertEqual(len(result["selection"]["probes"]), 2)
        self.assertEqual(len(self.calls()), 3)

    def test_custom_provider_requires_explicit_selection(self):
        config = Path(self.env["CODEX_HOME"])
        config.mkdir()
        (config / "config.toml").write_text('model_provider="gateway"\nmodel="gateway-model"\n')
        process, result = self.run_cli("codex")
        self.assertNotEqual(process.returncode, 0)
        self.assertIn("custom provider", result["errors"])
        self.assertFalse(self.record.exists())

    def test_empty_catalog_is_terminal_and_never_generates(self):
        self.env["MOCK_MODELS"] = "[]"
        process, result = support.TransportTests.run_cli(self, "codex", extra=("--model", "highest", "--reasoning", "highest"))
        self.assertNotEqual(process.returncode, 0)
        self.assertIn("empty or malformed", result["errors"])
        self.assertFalse(self.record.exists())

    def test_catalog_timeout_cleans_up_and_never_generates(self):
        env = dict(self.env, MOCK_MODE='catalog-sleep')
        with patch.dict(os.environ, env, clear=True), self.assertRaises(selector.SelectionError) as caught:
            selector.catalog('codex', [sys.executable, str(self.mock)], self.directory, runner.stop_process, timeout=0.4)
        self.assertIn('timed out', str(caught.exception))
        self.assertFalse(self.record.exists())

    def test_unverified_claude_model_substitution_is_not_approved(self):
        self.env['MOCK_CHANGED_MODEL'] = '1'
        process, result = self.run_cli('claude')
        self.assertNotEqual(process.returncode, 0)
        self.assertEqual(result['result'], 'not_verified')
        self.assertIsNone(result['verdict'])
        self.assertIn('model changed', result['errors'])

    def test_live_selftest_reports_actual_selection_and_effort(self):
        self.env['MOCK_MODELS'] = json.dumps(CODEX_MODELS)
        process = subprocess.run([sys.executable, str(SCRIPT), 'selftest', '--backend', 'codex',
                                  '--cli', str(self.mock), '--model', 'highest', '--reasoning', 'highest', '--live-probe'], env=self.env,
                                 capture_output=True, text=True, encoding='utf-8', timeout=25)
        self.assertEqual(process.returncode, 0, process.stderr)
        report = json.loads(process.stdout)
        self.assertTrue(report['ready_for_audit'])
        self.assertEqual(report['selection']['model'], 'gpt-6-astra')
        self.assertEqual(report['reviewer_effort'], 'ultra')

    def test_conflicting_fallback_is_rejected_before_spending_a_probe(self):
        process, result = self.run_cli('codex', extra=('--fallback-model', 'gpt-6.1-sol'))
        self.assertNotEqual(process.returncode, 0)
        self.assertEqual(result['result'], 'input_error')
        self.assertFalse(self.record.exists())

    def test_unspecified_selection_requires_user_choice_without_generation(self):
        process = subprocess.run([sys.executable, str(SCRIPT), 'run', '--backend', 'claude',
                                  '--cli', str(self.mock), '--bundle', str(self.bundle), '--result', str(self.result)],
                                 env=self.env, capture_output=True, text=True, encoding='utf-8', timeout=15)
        result = json.loads(self.result.read_text())
        self.assertEqual(process.returncode, 2)
        self.assertEqual(result['result'], 'selection_needed')
        self.assertEqual(result['review_quality'], 'unknown')
        self.assertIsNone(result['verdict'])
        self.assertFalse(self.record.exists())

    def test_inspect_lists_choices_without_generation_or_account_object(self):
        self.env['MOCK_MODELS'] = json.dumps(CLAUDE_MODELS)
        process = subprocess.run([sys.executable, str(SCRIPT), 'inspect', '--backend', 'claude',
                                  '--cli', str(self.mock)], env=self.env,
                                 capture_output=True, text=True, encoding='utf-8', timeout=20)
        self.assertEqual(process.returncode, 0, process.stderr)
        report = json.loads(process.stdout)
        self.assertFalse(report['generation_requested'])
        self.assertFalse(report['availability_verified'])
        self.assertEqual(report['models'], CLAUDE_MODELS)
        self.assertNotIn('do-not-persist', process.stdout)
        self.assertFalse(self.record.exists())

    def test_saved_preference_is_local_and_explicit_choice_wins(self):
        self.env['MOCK_MODELS'] = json.dumps(CLAUDE_MODELS)
        configured = subprocess.run([sys.executable, str(SCRIPT), 'configure', '--backend', 'claude',
                                     '--model', 'default', '--reasoning', 'max'], env=self.env,
                                    capture_output=True, text=True, encoding='utf-8', timeout=15)
        self.assertEqual(configured.returncode, 0, configured.stderr)
        path = Path(json.loads(configured.stdout)['path'])
        self.assertTrue(path.is_relative_to(Path(self.env['CODEX_HOME'])))
        command = [sys.executable, str(SCRIPT), 'run', '--backend', 'claude', '--cli', str(self.mock),
                   '--bundle', str(self.bundle), '--result', str(self.result)]
        process = subprocess.run(command, env=self.env, capture_output=True, text=True, encoding='utf-8', timeout=25)
        result = json.loads(self.result.read_text())
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual((result['selection']['model'], result['reviewer_effort']), ('default', 'max'))
        process = subprocess.run(command + ['--model', 'sonnet', '--reasoning', 'high', '--verify-selection'],
                                 env=self.env, capture_output=True, text=True, encoding='utf-8', timeout=25)
        result = json.loads(self.result.read_text())
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual((result['selection']['model'], result['reviewer_effort']), ('sonnet', 'high'))
        self.assertEqual(json.loads(path.read_text())['model'], 'default')

    def test_explicit_verified_model_is_not_replaced_on_unavailable(self):
        self.env['MOCK_MODELS'] = json.dumps(CLAUDE_MODELS)
        process, result = support.TransportTests.run_cli(self, 'claude', extra=('--model', 'unavailable', '--reasoning', 'max', '--verify-selection'), mode='fallback')
        self.assertNotEqual(process.returncode, 0)
        self.assertEqual(len(self.calls()), 1)
        self.assertIn('No repository content', self.calls()[0]['stdin'])
        self.assertNotIn('Literal `code`', self.calls()[0]['stdin'])

    def test_latest_installed_compatible_cli_and_explicit_override(self):
        home = self.directory / "home"
        native = home / (".local/bin/codex.exe" if runner.os.name == "nt" else ".local/bin/codex")
        native.parent.mkdir(parents=True)
        native.write_text("fixture")
        with patch.object(runner.Path, "home", return_value=home), \
             patch.object(runner.shutil, "which", return_value=str(self.mock)), \
             patch.object(runner, "preflight", side_effect=lambda backend, cmd, cwd:
                          ("codex 0.162.0" if cmd[-1] == str(native.resolve()) else "codex 0.144.1", "")):
            self.assertEqual(runner.discover("codex", prefer_latest=True), [str(native.resolve())])
            self.assertEqual(runner.discover("codex", str(self.mock), prefer_latest=True)[-1], str(self.mock.resolve()))


if __name__ == "__main__":
    unittest.main()
