# Executable review contract (protocol 2)

This installed skill is self-contained. `scripts/review_runner.py` uses Python
3.11+ and its standard library. No agent-generated transport, jq, GNU timeout,
bwrap preflight, or subagent is required. The two sibling skills intentionally
ship matching transport/schema/prompt files; keep protocol fixes mirrored.

Resolve `<skill>` to the absolute directory of the SKILL.md you just read.
`python` on Windows, `python3` on macOS/Linux, or `py -3.11` when appropriate:

```text
python "<skill>/scripts/review_runner.py" prepare
python "<skill>/scripts/review_runner.py" preferences --backend codex
python "<skill>/scripts/review_runner.py" inspect --backend codex
python "<skill>/scripts/review_runner.py" selftest --backend codex
python "<skill>/scripts/review_runner.py" selftest --backend codex --live-probe --model "<chosen-model>" --reasoning "<chosen-effort>" --verify-selection
python "<skill>/scripts/review_runner.py" run --backend codex --model "<chosen-model>" --reasoning "<chosen-effort>" --verify-selection --bundle "<bundle.md>" --result "<result.json>" --repo "<git-root>" --scope "<relative-file>"
python "<skill>/scripts/review_runner.py" configure --backend codex --model "<chosen-model>" --reasoning "<chosen-effort>"
```

The runner freezes stdin in a private OS temp directory and launches the CLI
from that directory, with stdin closed when exhausted. CLI discovery uses
`CODEX_REVIEW_CLI`, `CODEX_BIN`, PATH, common local/npm installations, and
the current user's VS Code native binary. An invalid explicit path is a visible
setup error. Windows npm shims resolve to their Node entrypoint; no shell command
is constructed. Another user's credentials/extension directories are never scanned.

## Model and capability selection

First resolve the user's choice. Precedence is explicit arguments, reviewer-only
environment variables (`CODEX_REVIEW_MODEL`, `CODEX_REVIEW_EFFORT`), then the
saved local preference. With no complete model/effort pair, `run` returns
`selection_needed`, exit 2, before generation. The host asks whether the user knows
which model/effort are available, wants advertised choices, or wants automatic
strongest selection. It waits for an answer. Existing session choices count;
announce saved settings and honor overrides without asking the same question again.

`preferences` reads only the saved pair. `inspect` checks compatible CLI/authentication
and returns its model/effort catalog without generation, with
`availability_verified: false`. A catalog is not an entitlement check.
`configure` saves the user's requested pair separately from provider configuration:
Claude-review preferences are in `$CODEX_HOME/adversarial-review/claude.json`
(default `~/.codex`); Codex-review preferences are in
`$CLAUDE_CONFIG_DIR/adversarial-review/codex.json` (default `~/.claude`). Installers
preserve these outside the skill directory. Do not commit personal preference files.

The hosted skill always passes `--verify-selection` for its chosen pair. A chosen
explicit model and effort are synthetically verified without replacement.
Only when the user chooses `--model highest --reasoning highest` does the automatic
strongest policy below apply. The runner selects the newest compatible CLI already installed in the usual
current-user locations. An explicit `--cli`, `CODEX_REVIEW_CLI`, or `CODEX_BIN`
takes precedence, including an intentionally older binary. It does not install
or update programs or change account-wide preferences.

Codex queries its stdio app-server `model/list`, including pagination. Claude
queries the streaming initialization response's model picker. These are metadata
requests, without a user message or project bundle. Only model fields are saved;
the initialization account object is never persisted. Capability families rank
Mythos > Fable/Astra (or GPT Pro) > Opus > Sol > Sonnet/Codex > Terra > Luna/Haiku/Mini/Nano; within
a family, newer advertised versions win. Provider flagship descriptions help
rank unknown families and break ties. Numeric version alone is not a strength
ranking across families. Hidden, disabled, and unavailable entries are excluded.
This explicit policy uses no fixed release IDs. It is a policy, not a provider
strength score or proof that every future model will be ranked correctly.
Unrankable new families or unknown effort scales stop visibly and require an
explicit choice or a policy update; they never silently select an older default.

Effort is selected from the chosen model's advertised levels in ascending order
`none < minimal < low < medium < high < xhigh < max < ultra`; omitted/unsupported
levels are not invented. Codex may advertise `ultra` as including provider task
delegation; selecting it does not grant additional runner permissions. Claude's
`ultracode` workflow setting is not an effort level and is never substituted.

A catalog is not an entitlement check. Before the full review, a complete synthetic
add-one example verifies the model/effort, authentication, and output contract.
Only an explicit model-unavailable error advances to the next ranked model;
only an explicit unsupported-effort error advances to the next advertised effort
on that model. Up to six probes total, each capped at 180 seconds and Claude's
$0.75 API budget where supported. Authentication, quota, network, permissions,
configuration, timeout, or invalid output stops immediately. Selection adds
latency and account usage; these limits are per probe, not an aggregate spend cap.
Claude's reported resolved model must stay consistent between probe and review.
Codex's requested ID and successful inference are recorded; resolved session
model metadata is recorded when its CLI provides it.

Choice: `--model MODEL` / `CODEX_REVIEW_MODEL`, or `--model configured` for the
top-level Codex config model. An explicit model is never replaced automatically.
Both model and effort must be selected or saved. `--reasoning highest` explicitly
opts into the highest effort for the chosen model. The direct runner can omit
`--verify-selection` with an explicit pair to preserve legacy single-call behavior;
the hosted skill always verifies it. To choose both CLI defaults use
`--model cli-default --reasoning cli-default`. Profiles are not
implicitly selected. Custom Codex providers retain endpoint/configuration, but
require an explicit model/configured and effort/cli-default because a bundled
OpenAI catalog cannot establish a gateway's strongest model.

`--fallback-model MODEL` / `CODEX_REVIEW_FALLBACK_MODEL` applies only in the direct
legacy runner, without `--verify-selection`, with explicit model AND effort settings,
after a model-availability error, with at most two
full-review attempts. Automatic selection cannot combine with that fallback.
Errors and requested overrides are always recorded; permissions never widen.

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
process tree when OS permissions allow it. A denied/failed Windows termination
is an explicit failure: the parent is stopped, but descendants may remain;
inspect local processes before retrying. Change limits with `--timeout`, `--heartbeat`, `--max-turns`, and
`--max-budget-usd`. Codex has no equivalent dollar ceiling; timeout bounds duration,
not spend. Use your account's usage limits as needed.

The host's foreground wait must cover discovery, metadata, selection probes,
and all full-review attempts together. In the tested Claude host, a 600-second
Bash foreground limit matched the runner's full-review deadline alone, leaving
no time for verification. Use the host's tracked background task/session facility
when its foreground limit is insufficient. Preserve the task handle and result
path, await task completion with available task-output tools or bounded result
polls, and read the terminal JSON and exit status. A background launch is pending;
the host must stay on the audit until completion or a reported failure. A host
kill can leave running; it is never a verified review.

Every handled runtime failure writes a terminal envelope, prints a diagnostic,
and returns nonzero. If the requested result is unwritable, the envelope is
printed to stdout and exit 6 names the persistence failure. Invalid arguments
return argparse usage/nonzero before a run starts. A forced runner kill/power
loss may leave `running`; this is never a review. A result inside the reviewed
repo is rejected without writing there, and the error envelope is printed.

Envelope fields: `protocol_version`, `result`, `verdict`, `review_quality`,
`review`, `errors`, `session_id`, `backend`, `reviewer_model`, `model_source`,
`reported_model` (when the CLI supplies it), `reviewer_effort`, `selection`, `cli_command`, `cli_path`, `cli_version`, `attempts`, `diagnostics_dir`, `mutation_check`, and
`elapsed_seconds`. Fields not reached during failed preflight may be absent.

`result`: `success`, `running`, `selection_needed`, `setup_needed`, `input_error`, `launch_failure`,
`timeout`, `cancelled`, `invalid_output`, `not_verified`, `mutation_detected`.
Only `success` plus `valid` plus an unchanged requested snapshot can be accepted.
Exit codes: 0 valid review; 2 setup/input; 3 launch/timeout; 4 output/degraded;
5 mutation/check failure; 6 persistence failure; 130 interruption.

`selection` records chosen model/effort, source, synthetic availability verification,
resolved model when reported, and every selection probe. A failed selection retains
`selection_phase`, model-only catalog, and individual probe results in diagnostics.
Each full-review attempt has separate stdout/stderr/final output. Logs and frozen bundle
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
and nonignored untracked bytes before/after, including on failure after the
snapshot was taken. Setup failures before that point report `not_checked`,
rather than claiming a requested snapshot was completed or never requested.
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
