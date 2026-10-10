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

Models can be selected with `reviewer:<model>`. Otherwise use the CLI's own
account default. For Codex, `reviewer:configured` deliberately uses its top-level
config model; `reviewer:cli-default` omits the override. This matters when an IDE
and terminal CLI have different model catalogs. Do not guess model availability.

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
