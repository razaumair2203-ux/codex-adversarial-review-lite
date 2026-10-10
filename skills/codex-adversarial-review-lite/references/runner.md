# Executable review contract (protocol 2)

This installed skill is self-contained. `scripts/review_runner.py` uses Python
3.11+ and its standard library. No agent-generated transport, jq, GNU timeout,
bwrap preflight, or subagent is required. The two sibling skills intentionally
ship matching transport/schema/prompt files; keep protocol fixes mirrored.

Resolve `<skill>` to the absolute directory of the SKILL.md you just read.
`python` on Windows, `python3` on macOS/Linux, or `py -3.11` when appropriate:

```text
python "<skill>/scripts/review_runner.py" prepare
python "<skill>/scripts/review_runner.py" selftest --backend codex
python "<skill>/scripts/review_runner.py" selftest --backend codex --live-probe
python "<skill>/scripts/review_runner.py" run --backend codex --bundle "<bundle.md>" --result "<result.json>" --repo "<git-root>" --scope "<relative-file>"
```

The runner freezes stdin in a private OS temp directory and launches the CLI
from that directory, with stdin closed when exhausted. CLI discovery uses
`CODEX_REVIEW_CLI`, `CODEX_BIN`, PATH, common local/npm installations, and
the current user's VS Code native binary. An invalid explicit path is a visible
setup error. Windows npm shims resolve to their Node entrypoint; no shell command
is constructed. Another user's credentials/extension directories are never scanned.

## Model and capability selection

Default: omit model override, letting the authenticated CLI/account choose.
Codex custom `model_provider` definitions and their configured model are
preserved while user/project automation config is isolated. For standard accounts,
do not import a newer builder/IDE model choice into an older CLI. `--model configured`
explicitly selects the top-level Codex model; `--model cli-default` omits it. Profiles are not
implicitly selected. Explicit model: `--model MODEL` or `CODEX_REVIEW_MODEL`.
Aliases supplied by the provider are fine; reproducible runs may pin a full ID.
When the CLI does not expose the resolved default model, report `cli_default`
rather than inventing an ID. Log requested model and CLI version.

Optional `--fallback-model MODEL` / `CODEX_REVIEW_FALLBACK_MODEL` is tried only
after a model-availability error, with at most two attempts total. Explicit
fallback use is announced and recorded. Timeout/auth/quota/permission/network/
configuration/output errors stop; no weaker model or permissions are substituted.
No redundant model-health generation precedes every full review. `--reasoning`
is optional; use the model's default unless latency/quality needs justify an
override. Unsupported flags/settings produce a visible error; update the CLI.

## Isolation

Claude: `-p`, `dontAsk`, no tools or slash commands, empty settings sources,
disabled hooks/memory, strict empty MCP, replacement system prompt, no session
persistence. `--bare` is intentionally absent: it can exclude subscription OAuth.
The nested `CLAUDECODE` marker is removed only in the independent child process.
Default limits: eight turns, $3 API budget ceiling where Claude supports it.

Codex: `exec`, read-only sandbox, approval policy `never`, empty temp working root,
`--ignore-user-config`, disabled web search, schema-constrained final output,
JSONL diagnostic events, and ephemeral mode when available. Authentication stays
in its normal location. There is no silent danger-full-access fallback. The
Codex CLI's built-in tools can still exist; read-only does not mean no filesystem
read access. Frozen stdin and temp cwd limit context; they are not an OS isolation
boundary. Use an externally isolated environment for stronger confidentiality.

## Observable terminal result

The requested result file is atomically replaced with `running` before any CLI
probe. Heartbeat every 15 seconds. Default review deadline 600 seconds per attempt;
version/help/auth probes have 20-second deadlines. Timeout/interruption stops the
process tree. Change limits with `--timeout`, `--heartbeat`, `--max-turns`, and
`--max-budget-usd`. Codex has no equivalent dollar ceiling; timeout bounds duration,
not spend. Use your account's usage limits as needed.

Every handled runtime failure writes a terminal envelope, prints a diagnostic,
and returns nonzero. If the requested result is unwritable, the envelope is
printed to stdout and exit 6 names the persistence failure. Invalid arguments
return argparse usage/nonzero before a run starts. A forced runner kill/power
loss may leave `running`; this is never a review. A result inside the reviewed
repo is rejected without writing there, and the error envelope is printed.

Envelope fields: `protocol_version`, `result`, `verdict`, `review_quality`,
`review`, `errors`, `session_id`, `backend`, `reviewer_model`, `model_source`,
`cli_path`, `cli_version`, `attempts`, `diagnostics_dir`, `mutation_check`, and
`elapsed_seconds`. Fields not reached during failed preflight may be absent.

`result`: `success`, `running`, `setup_needed`, `input_error`, `launch_failure`,
`timeout`, `cancelled`, `invalid_output`, `not_verified`, `mutation_detected`.
Only `success` plus `valid` plus an unchanged requested snapshot can be accepted.
Exit codes: 0 valid review; 2 setup/input; 3 launch/timeout; 4 output/degraded;
5 mutation/check failure; 6 persistence failure; 130 interruption.

Each attempt has separate stdout/stderr/final output. Logs and frozen bundle
remain in `diagnostics_dir` on success and failure; they may contain selected
source and must not be posted publicly. Console/envelope errors redact common
token formats. Raw logs are local evidence, not guaranteed sanitized.

## Validation and mutation

Both backends receive `references/review-schema.json`. Local validation checks
every declared type, required field, enum, minimum string length, and unexpected
field. `approved` requires zero findings; `revise` with valid quality requires findings; a degraded review may honestly lack findings. Claude
outer error/budget/turn envelopes are not reviews even with exit 0.

`--rubric-items FILE` accepts a JSON array of unique identifiers that correspond
to verbatim checklist text in the bundle. Duplicate/unknown results and approval
alongside FAIL are invalid; missing identifiers, majority UNVERIFIABLE, or
all-unverified approval yield `not_verified`. With no rubric, the output array
is empty. The builder still checks whether evidence substantiates each result.

`--repo` automatically compares HEAD, Git status, working/staged binary diff,
and nonignored untracked bytes before/after, including on dispatch failure.
`--scope PATH` additionally hashes each reviewed context/source path. An unborn
Git repository is allowed. Symlink targets outside the repo are rejected. No
volatile exclusions are silently inferred. Concurrent builds can trigger a real
mutation alert; rerun after they settle. This detects persistent changes, not
transient writes that are perfectly restored or changes to ignored unreviewed files.

`selftest` needs no project checkout or repository test suite. Offline checks
prove discovery/parser/temp/auth only. `--live-probe` sends synthetic content,
costs account usage, and alone can establish live dispatch readiness. Authentication
probes may contact the provider but send no project content. Do not install CLIs,
change login/configuration, or widen permissions automatically on test failure.
