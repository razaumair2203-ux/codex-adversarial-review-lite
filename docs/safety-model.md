# Trust and evidence

Both agents can be wrong. Reviewer findings are evidence to assess, never edit
instructions. An empty valid findings array is a legitimate successful review.
Scope, missing context, test limitations, and model identity are reported honestly.

The runner uses a frozen bundle and an empty temp working directory. Claude has
tools/hooks/skills/MCP disabled. Codex uses read-only sandboxing and ignores user
automation config while preserving auth and explicit custom-provider settings.
Codex built-in tools may still exist; read-only can allow filesystem reads.
Neither temp cwd nor snapshots prove OS isolation or protection of all ignored files.

Snapshots cover Git HEAD/status/diffs, nonignored untracked bytes, and explicitly
reviewed source/context paths. Persistent mutation or failed verification blocks
approval. Perfectly restored transient writes are outside this detection guarantee.

Rubric coverage and JSON invariants are checked deterministically. Schema-valid
claims still need builder verification. Auth, billing, destructive data, secrets,
and regulatory work retain a human-review floor; explicitly selected strict mode
requires human review on every change and sign-off after findings.

The user's existing authorization is respected. No process silently widens
permissions, changes login/model preferences, publishes reports, or applies fixes
outside authorized scope. Provider CLI auth/config stays in its normal location.
Results and raw diagnostics stay local; logs may include selected source.

See [the complete executable contract](../skills/codex-adversarial-review-lite/references/runner.md).
