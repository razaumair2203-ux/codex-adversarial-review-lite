# Reliability upgrade: evidence and decisions

Inspected on 2026-10-10 against the repository and locally installed skills,
Claude Code 2.1.96, and Codex CLI 0.144.1.

## Verified defects

- The PowerShell runner throws on a process-start error without writing its
  promised result JSON. Reproduced with a missing executable: exit 1, no result.
- Installed self-tests depend on `tests/stress.*` outside the installed skill;
  installers copy only the skill folder. A valid installation therefore fails.
- Local and repository skill instructions have drifted. The local Claude Code
  installation also uses the earlier `adversarial-reviewer-lite` name.
- Transport validation checks only a few fields, despite advertising schema
  validation. Invalid severity, missing evidence, and outer CLI errors can escape.
- Hard-coded versioned models/fallbacks age independently of CLI/account support.

The original PowerShell suite passed 10/10; it does not cover these defects.
These reproduce plausible causes of reported missing reviews, but do not prove
the cause of every user's incident.

## Implementation plan

1. Keep evidence-first finding assessment, frozen context, rubrics, and human
   review for high-consequence changes. Do not manufacture critique.
2. Use the same self-contained Python standard-library transport in both skills;
   keep provider-specific entrypoints and skill metadata. Python 3.11+ becomes
   an explicit dependency; jq, GNU timeout, and agent-written shell runners go away.
3. Write a running status before launch; persist logs, attempts, exit codes,
   CLI version, model selection, timing, and a terminal result. Heartbeat and
   bounded process-tree cancellation make hangs visible. Failure never means approval.
4. Use account/CLI defaults unless explicitly overridden. Only try an explicitly
   configured fallback after a model-availability error; never turn auth, quota,
   network, sandbox, or malformed output into a model downgrade.
5. Validate all schema fields and semantic invariants locally. Use JSON Schema
   output for both providers and check exact rubric coverage.
6. Isolate the reviewer from the repository, retain authentication without
   copying credentials, and never silently widen permissions. Codex runs read-only.
7. Ship installed offline checks and opt-in synthetic live probes. Add realistic
   failure, timeout, quoting, stale-output, rubric, and mutation regressions plus CI.
8. Stage installs, preserve the previous installation as a backup, respect custom
   homes, document exact commands and the legacy Claude skill name.

## Sources

- [Codex non-interactive output](https://developers.openai.com/codex/noninteractive/)
- [Codex skills](https://developers.openai.com/codex/skills/)
- [Claude programmatic output](https://code.claude.com/docs/en/headless)
- [Claude skill frontmatter](https://code.claude.com/docs/en/skills)
- [Claude model aliases](https://code.claude.com/docs/en/model-config)

CLI help/runtime behavior determines supported flags. Documentation may describe
a newer CLI than the one installed. No particular model name proves review quality.
