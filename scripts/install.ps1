[CmdletBinding()]
param([string]$SkillsRoot = "", [switch]$Check)
$ErrorActionPreference = "Stop"
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) { throw "Install Python 3.11+ from python.org, enable PATH, and reopen your terminal." }
$arguments = @((Join-Path $PSScriptRoot "install.py"))
if ($SkillsRoot) { $arguments += @("--skills-root", $SkillsRoot) }
if ($Check) { $arguments += "--check" }
& $python.Source @arguments
exit $LASTEXITCODE
