# User-chosen, verified reviewer model and effort (2026-10-11)

- Ask for model/effort choice when the invocation/session or local preference
  has not supplied it. Offer known pair, advertised choices, or optional
  strongest/highest selection; no silent public model default.
- Save optional reviewer-only local preferences outside installed/public skill
  files. Explicit choices win; verify them before sending project content.
- Query Codex app-server model/list and Claude's streaming model picker;
  select the newest compatible already-installed CLI unless explicitly overridden.
- Capability-family/version ranking without fixed release IDs; unknown capability
  order fails visibly. Catalog entries alone are never treated as entitlements.
- Bounded, availability-only model/effort probes. Other failures stop without
  silent downgrade. Explicit pins and custom provider configuration remain supported.
- Record model, effort, CLI, selection provenance, probe results, and diagnostics.
  Document opt-out, latency/usage implications, and gateway uncertainty.
- 58 behavioral regressions in each package. Actual automatic-mode controls selected
  Claude Fable 5.1/max and GPT-6 Astra/ultra, found a seeded defect, and approved
  a correct change. Fresh Claude slash-command sessions invoked Codex in both
  controls; all fixture snapshots and fingerprints stayed unchanged.
- Explicit-choice controls also verified Opus 5.5/max and GPT-6.1 Sol/ultra.
  A fresh Claude choice-flow session listed advertised options, asked for a pair,
  returned selection_needed, and dispatched no reviewer generation.
- Account for selection overhead in host wait budgets. Use tracked task/session
  completion for long reviews; an observed broad-review timeout remained a
  non-approval with retained diagnostics and verified process-tree cancellation.

# Protocol 2 reliability upgrade (2026-10-10)

- Executable, mirrored CLI transport with persistent status/results, heartbeats,
  process-tree cancellation, and retained diagnostics. Direct dispatch in the
  builder agent; no transport subagent required.
- Full local validation of the declared JSON contract for both providers, exact
  rubric coverage, and automatic mutation checks. No fabricated approval on errors.
- CLI/account defaults instead of hard-coded aging models; explicit pins,
  optional availability-only fallback, custom Codex provider preservation.
- Self-contained installed offline self-tests and opt-in synthetic live probes.
- Staged, backup-preserving installers; documented current/legacy paths and the
  earlier Claude skill name. Python 3.11+ replaces multiple shell dependencies.
- Short host-native skill instructions, corrected Claude frontmatter, failure
  regressions, and Windows/Linux/macOS CI.
- Full audit checks in both directions: a seeded boundary defect was reported;
  a correct change was approved, with unchanged Git snapshots. Fresh Claude
  slash-command sessions actually invoked Codex; Codex invoked Claude through
  the host's supported approval mechanism.
- Impact-based severity guidance and independent builder severity assessment.
- Specific host-launch approval guidance for sandbox account/network/file access.
  Denied Windows process-tree cancellation now reports failure and possible
  remaining descendants, rather than falsely claiming successful termination.
- 31 behavioral checks, including the Windows cancellation-denial regression;
  explicit `not_checked` mutation status for failures before snapshot setup.

Compatibility changes: structured JSON replaces the Claude-hosted Markdown verdict
contract. Old full-access/inherit sandbox switches and approval aliases are no
longer supported; use frozen read-only review. Test-only mock runner flags are
replaced by executable CLI doubles in the regression suite.

# Historical changelog (before Protocol 2)

These entries describe earlier work. The Protocol 2 and selection entries above
supersede their legacy transport and invocation policies.


## Unreleased

### Changed
- **Renamed to Codex Adversarial Review - Lite.** The repo, skill folder, and slash
  command move from `adversarial-reviewer-lite` / `/adversarial-reviewer-lite` to
  `codex-adversarial-review-lite` / `/codex-adversarial-review-lite`. The old name gave
  no signal about which model builds and which audits; the new one states it plainly
  (Claude builds, Codex audits) and pairs cleanly with the sibling
  `claude-adversarial-review-lite` (Codex builds, Claude audits) instead of colliding
  with it in a file listing. Internal temp-file prefixes (`advreview-*`) are unchanged.

### Added
- **Review-contract confirmation before dispatch.** After building the reviewer
  prompt and before sending any repo content out, the skill now shows the user a
  concise bulleted summary of the review contract â€” scope, risk categories, test
  expectations, rubric â€” and lets them add or amend. User additions are refined into
  concrete checkable items (not pasted verbatim), the prompt body is rewritten to
  match, and only the approved contract is dispatched. The pre-dispatch mutation hash
  is captured after this step so it baselines the final contract. When the user does
  not know what rules apply, the builder drafts a rubric from the change and the
  matched floor category for the user to confirm or edit â€” the checklist obligation
  never silently falls back to a user who invoked the audit precisely because they
  lack that domain expertise.
- **Rubric and strict-mode discoverability.** Both were previously opt-in-only â€”
  invisible unless you already knew the flag existed. Step 4 now asks about a domain
  checklist alongside the existing test-spec question, can write one from your answers
  on the spot (no pre-authored file required), and â€” when a change hits a floor
  category with no rubric set â€” tells you both `rubric:<path>` and `strict` exist,
  before dispatch, while a rubric can still be added to that audit. Fires once per
  audit, never blocks.
- **Human-review floor.** An `APPROVED` verdict is no longer terminal when the diff
  touches floor categories: auth/permissions, money/billing, migrations/destructive
  data operations, secrets, or regulatory-tagged paths. Step 4 detects the categories
  (path patterns + destructive-diff content patterns + optional per-repo
  `.advreview-floor` regex file), and Step 11 requires the user to review the diff and
  reply `reviewed-ok` (or raise a concern, which enters the normal REVISE path) before
  the audit completes. Rationale: a clean second-model approval on a billing change
  should produce more human scrutiny, not less â€” the approval previously read as
  permission to skip it.
- **Rubric input (`rubric:<path>`).** Injects a domain checklist into the reviewer
  prompt; the reviewer must report `PASS`/`FAIL`/`UNVERIFIABLE` per item with evidence
  in a `# Rubric Results` section, and any `FAIL` forces `VERDICT: REVISE`. The runner
  validates the section's presence (`RUBRIC_PRESENT` input), counts failures into
  triage (`rubric_present`, `rubric_fail_count`), and classifies a review that ignores
  the rubric â€” or approves alongside a `FAIL` â€” as `degraded_content`.
- **Strict mode (`strict`).** One flag for high-consequence repos: requires
  `rubric:<path>` (stops with guidance if missing), floor-gates every change regardless
  of category, and disables autonomous fixing â€” prior "fix whatever it finds"
  authorizations are void while strict is active, including the Step 13 structural-gate
  autonomous exception.
- **Contract hardening.** Runner R7 now classifies internally inconsistent reviews
  (`FAIL` rubric line with `VERDICT: APPROVED`; `REVISE` with a zero-revision scorecard)
  as `degraded_content` instead of passing them through as valid.
- Terminal summary (Step 14) gains `Floor gate` and `Rubric` fields.
- **Sibling parity.** The floor/rubric/strict policy layer and the reporting procedure
  (finding evaluation, audit report, HTML structure, terminal summary fields) are now
  mirrored verbatim in the reversed sibling repo
  [claude-adversarial-review-lite](https://github.com/razaumair2203-ux/claude-adversarial-review-lite)
  (Codex builds, Claude reviews). Both skills produce the same report regardless of
  which model built and which reviewed; only direction and transport differ.
- Explicit detection of the trusted-directory refusal. Step 6 and ST-6 now distinguish
  an *environmental block* (trusted-directory / sandbox / auth) from a genuine
  *model-availability* failure and print the correct remedy instead of exhausting the
  fallback chain with a misleading message.
- `runner.md` R7 lists the `not inside a trusted directory` / `--skip-git-repo-check`
  refusal as a `degraded_environmental` signal so the runner reports it as an
  environment problem rather than inventing findings.
- A troubleshooting-table entry for the "all models unavailable but auth is healthy"
  symptom.

### Fixed
- **Codex "Not inside a trusted directory" misdiagnosed as a model outage.**
  `codex exec` refuses to run outside a git repository unless `--skip-git-repo-check`
  is passed. The model **preflight** (SKILL.md Step 6) and the **self-test dispatch**
  (SKILL.md Step 0 / ST-6) previously ran `codex exec` without it and from the current
  working directory. When that directory was not a git repo, every model in the
  fallback chain failed the same way, and the skill reported *"No reviewer model is
  available â€” check auth/quota/network"* â€” pointing users at the wrong problem entirely
  (auth and models were fine).

  Both of those dispatches send only a dummy probe (`MODEL_OK` / a fixed verdict) with
  **no repository content**, so Codex's trusted-directory guard adds no protection there.
  They now pass `--skip-git-repo-check`. The **real review dispatch** is unchanged and
  keeps full git-based mutation safety by running with `-C "${REPO_ROOT}"`
  (references/runner.md, Step R4).

### Notes
- The floor/rubric additions were stress-tested before release: 42 executable
  positive/negative cases against the floor-detection and rubric-validation grep
  patterns, plus a fresh-eyes adversarial consistency review of SKILL.md + runner.md
  that surfaced and fixed 8 defects pre-commit (branch-diff floor blind spot, a dead
  `FLOOR_GATE_ALL` variable, strict mode blocking selftest, unenforced rubric coverage,
  missing R3 triage fields, missing HTML report wiring, `rm -fr`/diff-header regex
  gaps, and the all-UNVERIFIABLE-approval hole).
- Surfaced by first-run dogfooding on Windows / Git Bash: Codex CLI 0.133.0, `gpt-5.5`,
  auth healthy, but the self-test's model dispatch failed for all four models solely
  because the working directory was not a git repository.
