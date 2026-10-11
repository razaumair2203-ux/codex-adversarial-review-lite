# Setup and first audit

Follow [the README](../README.md) to install and sign in. Invoke `/codex-adversarial-review-lite selftest`
in Claude Code. Then invoke `/codex-adversarial-review-lite selftest live-probe` once to check actual
provider/model dispatch. A local pass alone is not evidence of a remote review.

From your project's Git directory, invoke `/codex-adversarial-review-lite audit`. Add a focused
file path, test specification, sample data, or domain rubric if useful. `plan`
and `feasibility` use the same transport with a different bundle. The builder
states the scope and sends only selected content. Existing explicit review
authorization is sufficient; it need not repeatedly ask to dispatch.

The runner must finish and the builder must read the terminal result before
reporting an audit. If a tool yields a process/session ID, the builder resumes it.
On failure, keep the result and diagnostic path and follow
[troubleshooting](troubleshooting.md). No fake approval or self-review substitute.

If you have not supplied or saved a model/effort pair, the skill asks whether you
know your available reviewer, want to see advertised choices, or want automatic
strongest selection. It waits for your answer before generation. You can choose
both settings for this invocation; existing preferences are announced and can
be overridden. Read `selection`, `reviewer_model`, `reviewer_effort`, and `cli_version`.

Choose `reviewer:<model> reasoning:<effort>`; the skill checks dependencies and
verifies the exact pair synthetically. Choose `reviewer:highest reasoning:highest`
for automatic strongest/highest. Choose CLI
defaults with `reviewer:cli-default reasoning:cli-default`. For custom Codex
providers, use `reviewer:configured` (or a model ID) plus explicit effort or
`reasoning:cli-default`. A public catalog cannot establish a gateway's strongest
model. Ask to save your pair or use the installed `configure` helper; local
preferences survive reinstalling and never go into the public repository.
Explicit CLI overrides remain authoritative. Verification/automatic selection adds
latency and account usage; see the executable policy for bounds and uncertainty.

`strict rubric:<path>` chooses human sign-off after findings for every change.
Without strict, existing explicit autonomous-fix authorization is respected.
Findings are assessed against evidence before any fix. Unsupported critique is
rejected; mature work needs no manufactured corrections.

An optional HTML report can use the installed sample template. Ask for it when
you want a portable report; do not publish raw logs or source without review.

Installation paths: Claude uses `CLAUDE_SKILLS_DIR`, `CLAUDE_CONFIG_DIR/skills`,
or `~/.claude/skills`. New Codex installs use `~/.agents/skills`; an existing
`~/.codex/skills/codex-adversarial-review-lite` is updated in place, and `CODEX_HOME/skills` or
`--skills-root` can select a custom location. Confirm the skill appears in your
host's selector; hosts/builds may differ in legacy-path support.
