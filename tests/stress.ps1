$ErrorActionPreference = "Stop"
Push-Location (Split-Path -Parent $PSScriptRoot)
try { & python -m unittest discover -s tests -v; exit $LASTEXITCODE } finally { Pop-Location }
