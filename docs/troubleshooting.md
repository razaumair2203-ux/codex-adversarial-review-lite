# Troubleshooting

Start with `/codex-adversarial-review-lite selftest`. Use `live-probe` to verify the real reviewer.
Record the result and diagnostic directory, not only the last chat message.

| Symptom | Action |
|---|---|
| Skill missing from selector | Check the installer-reported path contains SKILL.md; reopen the host. Check host skill visibility settings. |
| selection_needed | Choose a reviewer model AND effort. Ask to show advertised choices with inspect, or explicitly choose strongest/highest. Save an optional local pair with configure; explicit invocation settings override it. |
| Python missing/too old | Install Python 3.11+ from python.org, enable PATH, reopen the terminal. macOS/Linux normally use python3. |
| Reviewer missing despite installation | Reopen the host after PATH changes. Set `CODEX_REVIEW_CLI` to the absolute native executable or npm shim. Invalid overrides fail visibly. |
| Windows npm shim launch fails | Ensure Node and the npm package are present beside the shim, or point the override to a native executable. The runner avoids shell quoting. |
| Authentication fails in an agent sandbox | Run the auth-status command under your normal account. Host sandbox credentials/permissions can differ. Use the host's supported approval mechanism for the specific launch. |
| Installed runner cannot be read or executed | Inspect the actual host denial; request supported approval for that specific runner command. Do not disable the reviewer's restrictions. If approval is unavailable in unattended mode, report blocked. |
| Claude says Unknown skill in an automated session | Keep the user settings source enabled for the host: excluding it with `--setting-sources ""` also hid installed user skills in the tested CLI. The isolated reviewer deliberately disables skills. |
| Model is not supported for this account | Automatic selection checks access with synthetic content and may try the next ranked advertised model only after this error. Explicit models are never silently replaced. Inspect `selection` and probe results. |
| Unknown model family/effort scale or missing catalog | Update the CLI/policy or specify `reviewer:<model> reasoning:<effort>`. Both `reviewer:cli-default reasoning:cli-default` opt out. No full bundle is sent on selection failure. |
| Custom Codex gateway | Specify `reviewer:configured` or the gateway model ID AND explicit effort or `reasoning:cli-default`. Its strongest model cannot be ranked from the bundled public catalog. |
| Unexpected CLI selected | Default selection chooses the newest compatible already-installed CLI, including common editor installations. Set the reviewer CLI environment override or `--cli` to pin your preferred binary. |
| Highest effort is slower or costs more | Inspect the selected level and probe limits. Pin an explicit model and effort, or opt out of both selection settings. No account-wide preference is changed. |
| CLI lacks required flags | Update the reviewer CLI using its official instructions. A newer documentation page does not prove your installed CLI supports a flag. |
| Auth/quota/network/config error | Fix that error; changing models or disabling sandboxing is not a general solution. Terminal JSONL provider errors take precedence over noisy startup warnings. |
| Review appears to vanish | Read the result JSON and logs. `running` means pending or interrupted, never approved. The host agent must resume a yielded process/session. |
| Timeout/cancellation | Runner stops the process tree and reports nonzero. Diagnose before one deliberate retry; do not loop full-bundle calls. |
| Process-tree cancellation denied | The result reports failure and warns descendants may remain. Inspect local processes before retrying; do not interpret a stopped parent as proof the entire tree stopped. |
| Local check passes, remote review fails | Expected distinction: offline checks do not verify model access. Inspect `live-probe` diagnostics. |
| Missing/malformed/contradictory output | Treat as invalid/not verified. The parser rejects stale output, outer CLI error envelopes, invalid evidence/severity, and contradictory verdicts. |
| Rubric partly skipped or all UNVERIFIABLE | Review is not verified. Improve evidence or clarify the checklist; do not treat a guessed PASS as evidence. |
| Mutation detected | Stop fixes and inspect changes. Concurrent builds may change the repo; rerun after they settle. Never exclude reviewed source to get a pass. |
| Legacy /adversarial-reviewer-lite installed | Use /codex-adversarial-review-lite. The legacy copy is reported and preserved; archive it when ready. |

Raw diagnostic logs can contain selected source and provider messages. Keep them
local or redact before sharing. Do not paste auth files, tokens, or environment dumps.
