# Validation evidence

Date: 2026-10-10. Windows, Python 3.12.4; Claude Code 2.1.96;
terminal Codex CLI 0.144.1. The IDE bundles a different, newer Codex CLI.

## Before repair

- Original Claude-review PowerShell suite: 10/10 passed.
- Missing process executable reproduced exit 1 with **no result file**.
- Installed selftest looked for checkout-only `tests/stress.*`, omitted by installers.
- Legacy Claude installation used `/adversarial-reviewer-lite` and older instructions.

## After repair

- 31/31 behavioral tests passed locally in each repository under the normal
  reviewer account. The six-job GitHub matrix covers Windows/Linux/macOS with
  Python 3.11 and 3.13 (the cancellation-denial test is Windows-only). A path
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

## Full installed audit controls before publication

Each isolated Git fixture began with `not (value > limit)`. The acceptance
contract requires an inclusive integer comparison. One working-tree change
used `<`, producing a reproducible failing equality test; the other used `<=`,
passing all three below/equal/above tests. Neither prompt dictated a verdict.

| Actual host / reviewer | Defective change | Correct change |
|---|---|---|
| Fresh Claude Code `/codex-adversarial-review-lite audit limit.py` / Codex | revise; one equality-boundary finding at limit.py:3 | approved; no findings |
| Current Codex session, installed skill and supported specific-launch approval / Claude | revise; one equality-boundary finding at limit.py:3 | approved; no findings |

All four results were `success`, quality `valid`, with exit-zero reviewer
attempts, recorded session identifiers, and unchanged repository snapshots.
Fresh Claude traces confirm actual Bash execution of the installed runner,
not merely a successful host exit or a claimed review. Fixture hashes and Git
state also remained unchanged through those host sessions. After the final
cancellation diagnostic fix, both installed helpers completed another real
correct-change audit with valid approval and unchanged snapshots.

The initial Claude result overstated the toy defect as critical. The builder
accepted the reproduced boundary defect and rejected the unsupported critical
impact. Both prompts now define impact-based severity; the repeated Claude
result reported high, without inventing production consequences. Severity
still requires independent builder assessment.

Both final installed runners also received a deliberately missing CLI path and
a stale approval file. They exited 2, persisted `setup_needed` with no verdict,
replaced the stale record, printed diagnostics, and retained logs. Setup did
not reach the requested snapshot, accurately reported as `not_checked`.

Restricted headless host controls produced visible blocking reports and no
review result. Claude's narrow Bash allowlist denied Git commands containing
`cd`; removing its user settings source hid the installed slash command. The
successful fresh sessions retained normal user skill discovery, explicitly
permitted the fixture's required host tools, and had no permission denials.
Codex's unattended Windows sandbox denied installed-script access. The current
Codex session succeeded through supported approval for the specific launch;
neither direction weakened the independent reviewer's settings.

A restricted Windows cancellation control denied `taskkill`: the earlier runner
mistakenly claimed the process tree stopped. The fix preserves a nonzero failure
and explicitly reports that descendants may remain. The same real restricted
control now produces `launch_failure`, no verdict, and an Access denied
diagnostic. Normal-account tree cancellation and the denial regression both
pass. These checks do not establish unattended readiness in a host that cannot
grant the required file, account, or network access.

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
