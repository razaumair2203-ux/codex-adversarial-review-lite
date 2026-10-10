# codex-adversarial-review-lite

**Claude Code builds. Codex reviews. You decide.**

This skill sends a focused review bundle to the other provider's CLI, validates
its structured response, checks for repository mutation, and asks the builder
to verify each finding before applying fixes. It supports changes, plans,
feasibility, checklists, and a strict human review policy.

The [sibling skill](https://github.com/razaumair2203-ux/claude-adversarial-review-lite) reverses the
direction. Both use the same executable protocol; their host metadata differs.
An independent review is another source of evidence, not proof of correctness.
When no material defect is supported, no change is needed.

## Install

You need Git, **Python 3.11+**, and both coding CLIs installed and signed in.
No Python packages, jq, GNU timeout, or subagent setup are needed.
See official [Python downloads](https://www.python.org/downloads/),
[Codex setup](https://developers.openai.com/codex/cli/), and
[Claude Code setup](https://code.claude.com/docs/en/setup).

Check the prerequisites in a fresh terminal:

```text
git --version
python --version
codex --version
claude --version
codex login status
claude auth status
```

If needed, sign in with `codex login` or `claude auth login`.
On macOS/Linux use `python3` where these examples say `python`.
On Windows, enable Python's PATH option during installation; `py -3.11` also works.

```text
git clone https://github.com/razaumair2203-ux/codex-adversarial-review-lite.git
cd codex-adversarial-review-lite
python scripts/install.py --check
```

PowerShell and Bash installers remain available: `./scripts/install.ps1 -Check`
or `bash scripts/install.sh --check`. The installer stages a complete copy and
preserves any previous installation under the host's `skill-backups` directory.
It does not delete your old skill or edit your CLI login/configuration.
`--check` performs installed local checks, with no generation call.

Use the skill on your next turn; reopen Claude Code if it does not appear.

## Use

```text
/codex-adversarial-review-lite selftest
/codex-adversarial-review-lite selftest live-probe
/codex-adversarial-review-lite audit
/codex-adversarial-review-lite plan
/codex-adversarial-review-lite audit test-spec:docs/change-tests.md
/codex-adversarial-review-lite audit rubric:docs/checklist.md
/codex-adversarial-review-lite audit strict rubric:docs/checklist.md
```

`selftest` checks local discovery, authentication, temp paths, and the installed
parser. It does **not** prove the remote reviewer ran. `live-probe` makes one
synthetic review call without project content; account usage may apply. Its
result is the evidence that live dispatch works.

Model selection defaults to this CLI's account default. There is no fixed
model/version chain. You can specify `reviewer:<model-or-provider-alias>`,
`fallback:<model>`, and `reasoning:<level>` deliberately. A fallback is used only
for an availability error and is reported. Codex custom providers keep their
configured endpoint/model; `reviewer:configured` explicitly selects the top-level
Codex model and `reviewer:cli-default` skips that model setting. No account-wide
model preference is changed. Newer models alone do not establish better review
quality; measure defect detection, unsupported findings, latency, and cost.

## What you should see

The builder states the review scope, creates a frozen bundle, and launches the
runner directly. The runner reports its selected CLI/model, writes `running`,
prints progress every 15 seconds, and produces a terminal result. You then see
the review and the builder's evidence-backed decisions on each finding.

A missing executable, unsupported model, auth problem, timeout, invalid response,
or changed repository is an explicit failure/not-verified result. Logs and attempt
metadata remain available at the reported diagnostic path. A successful launch
or local self-test is never reported as a completed audit.

Installed and signed-in CLIs still need permission to run from the host. If its
sandbox blocks the installed script, account files, or network access, approve
the specific runner launch using the host's normal permission mechanism. The
independent reviewer keeps its restricted settings. A denied launch is reported
as blocked; the skill does not claim that a reviewer ran.

Rubrics receive PASS/FAIL/UNVERIFIABLE results with exact item coverage. Strict
mode requires a rubric and human sign-off after findings. Auth, billing,
destructive data, secrets, and regulatory changes retain a human-review floor.
Explicit authorization already supplied by the user is respected; ordinary
review dispatch does not add repeated confirmation prompts.

## Upgrade and troubleshooting

[How to use](docs/how-to-use.md), [troubleshooting](docs/troubleshooting.md),
[evidence and upgrade decisions](docs/upgrade-plan.md), and
[the executable protocol](skills/codex-adversarial-review-lite/references/runner.md).

Protocol 2 adds Python and structured output in both directions. Legacy shell
orchestration, textual verdict parsing, mandatory transport subagents, and
automatic full-access sandbox fallback are replaced. Positional shell runner
model arguments and PowerShell bundle/result/model parameters remain supported;
use the documented named flags for other settings.

## Privacy and limits

Only selected bundle content is intentionally sent to the external reviewer.
Claude has no tools; Codex runs read-only in a temp directory with automation
configuration isolated. Read-only sandboxing is not a no-read security boundary,
and snapshots are detection, not an OS guarantee. For stronger isolation, use an
externally isolated environment. No runner silently bypasses permissions.

Local logs include the frozen bundle and may contain source; do not publish
them without inspection. Schema-valid findings can be wrong. The builder must
verify them, and review cannot replace tests or human judgment.

## Maintainer checks

```text
python -m unittest discover -s tests -v
```

Offline CI covers Windows, Linux, and macOS on Python 3.11/3.13. Live provider
checks remain opt-in and use no repository content. Keep shared transport,
schema, prompt, and regression fixes mirrored in the sibling repository.

MIT license.

If you previously installed `/adversarial-reviewer-lite`, use the current
`/codex-adversarial-review-lite` command. The installer reports the legacy copy
and leaves it intact; archive it when you are ready.
