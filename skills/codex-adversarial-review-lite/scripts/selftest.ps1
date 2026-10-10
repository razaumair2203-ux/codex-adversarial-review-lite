[CmdletBinding()]
param([switch]$LiveProbe)
$ErrorActionPreference = "Stop"
$arguments = @((Join-Path $PSScriptRoot "review_runner.py"), "selftest", "--backend", "codex")
if ($LiveProbe) { $arguments += "--live-probe" }
& python @arguments
exit $LASTEXITCODE
