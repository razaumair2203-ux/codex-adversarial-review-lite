# Validation evidence

Date: 2026-10-10. Windows, Python 3.12.4; Claude Code 2.1.96;
terminal Codex CLI 0.144.1. The IDE bundles a different, newer Codex CLI.

## Before repair

- Original Claude-review PowerShell suite: 10/10 passed.
- Missing process executable reproduced exit 1 with **no result file**.
- Installed selftest looked for checkout-only `tests/stress.*`, omitted by installers.
- Legacy Claude installation used `/adversarial-reviewer-lite` and older instructions.

## After repair

- 30/30 behavioral tests passed locally in each repository. The six-job GitHub
  matrix also passed on Windows/Linux/macOS with Python 3.11 and 3.13. A path
  spelling assertion was corrected to compare file identity on macOS symlinked
  temp roots and Windows short-path aliases; the runner already resolved them.
- Shared behavioral regression suite covers both providers: launch failure,
  stale approval replacement, outer error responses, strict schema/evidence,
  incomplete rubrics, timeouts with child-process cancellation, native paths,
  authentication diagnostics, provider/model configuration, read-only dispatch,
  mutation detection, offline installed checks, and recoverable installation.
- Synthetic live review passed on **both actual provider CLIs**, with structured
  output and a complete toy function. No user repository content was sent.
- Installed offline checks passed for both local skills under the normal user
  account. Sandbox credentials differed from that account; running a probe in
  a different execution context is not evidence the real account lacks auth.
- Both final installed copies passed synthetic live reviews using their normal
  defaults. A fresh Claude session invoked `/codex-adversarial-review-lite selftest`
  and actually executed the Python helper under narrowly allowed Bash permissions;
  all six offline checks passed with no permission denials. The earlier host probe
  exposed premature stopping after an optional `ls` denial; instructions now
  distinguish that from a denial of the required runner command.
- Independent Claude implementation review: approved, zero material findings,
  six rubric PASS results, repository snapshot unchanged. This verifies a
  supplied bundle, not general correctness or every deployment environment.
- Git Bash proved the Windows Store `python3` alias was unusable while `python`
  worked. Shell entrypoints now probe Python 3.11+ before choosing an interpreter;
  the regression suite exercises those entrypoints.
- Codex skill frontmatter passes the skill-creator validator. Claude frontmatter
  uses its own documented `user-invocable` and `disable-model-invocation` keys.

## Model compatibility finding

The builder's top-level configured model was rejected by the older terminal
Codex CLI's ChatGPT account. The CLI's own default succeeded. Standard-account
reviews now use that default without changing account-wide preferences;
`reviewer:configured` selects a configured model explicitly. Custom providers
retain their endpoint and configured model. Terminal provider error events take
precedence over unrelated startup/websocket/cache warnings.

## Limits

Live provider and host validation is Windows evidence. Cross-platform offline
CI passed on Windows/Linux/macOS with Python 3.11 and 3.13.
Live smoke tests do not establish real-world defect recall or false-positive
rates. For model upgrades, compare verified defect detection, unsupported
findings, latency, cost, and rubric coverage on representative tasks; do not
equate a newer model or higher reasoning setting with better review.

The older `/adversarial-reviewer-lite` copy is preserved locally; use the current
`/codex-adversarial-review-lite` command. Previous canonical installations are
backed up. Logs may contain selected source, and read-only is not OS no-read isolation.
