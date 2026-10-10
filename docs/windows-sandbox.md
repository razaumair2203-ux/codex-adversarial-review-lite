# Windows runtime

Protocol 2 no longer tests Linux bubblewrap on Windows or automatically chooses
danger-full-access. The runner uses native process APIs and the installed Codex
CLI's read-only policy. A sandbox/permission failure is reported and stops review.

Python handles temp paths, hashing, deadlines, and Windows process-tree cleanup.
PowerShell, Git Bash, and WSL entrypoints call the same executable; a Bash host
does not need GNU timeout/jq/hash utilities for this workflow.

PATH can resolve an older npm CLI while the IDE bundles a newer one. The runner
reports its CLI version/path. Set CODEX_REVIEW_CLI to a specific executable when
needed. Account model catalogs may differ from an IDE's configured model; use
the CLI account default or an explicit supported model, never a permission bypass.

Authentication in an outer agent sandbox can differ from the normal Windows
user account. Test login status in the same execution context used for review.
Read-only is not a guarantee against all filesystem reads; see safety-model.md.
