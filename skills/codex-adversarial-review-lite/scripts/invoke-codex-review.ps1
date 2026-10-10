[CmdletBinding()]
param(
  [Parameter(Mandatory)][string]$BundlePath,
  [Parameter(Mandatory)][string]$ResultPath,
  [string]$RepoRoot = "", [string[]]$Scope = @(),
  [string]$Model = "", [string]$FallbackModel = "", [string]$Reasoning = "",
  [string]$RubricItemsPath = "", [int]$TimeoutSeconds = 600,
  [int]$MaxTurns = 8, [decimal]$MaxBudgetUsd = 3.00
)
$ErrorActionPreference = "Stop"
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
  @{result="setup_needed"; verdict=$null; errors="Install Python 3.11+ and reopen your terminal."} | ConvertTo-Json | Set-Content -LiteralPath $ResultPath -Encoding utf8
  exit 2
}
$arguments = @((Join-Path $PSScriptRoot "review_runner.py"), "run", "--backend", "codex", "--bundle", $BundlePath, "--result", $ResultPath, "--timeout", "$TimeoutSeconds", "--max-turns", "$MaxTurns", "--max-budget-usd", "$MaxBudgetUsd")
if ($RepoRoot) { $arguments += @("--repo", $RepoRoot) }
foreach ($path in $Scope) { $arguments += @("--scope", $path) }
if ($Model) { $arguments += @("--model", $Model) }
if ($FallbackModel) { $arguments += @("--fallback-model", $FallbackModel) }
if ($Reasoning) { $arguments += @("--reasoning", $Reasoning) }
if ($RubricItemsPath) { $arguments += @("--rubric-items", $RubricItemsPath) }
& $python.Source @arguments
exit $LASTEXITCODE
