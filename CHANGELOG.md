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

# Changelog
