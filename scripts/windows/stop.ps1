$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot | Split-Path -Parent)
docker compose down
if ($LASTEXITCODE -ne 0) { throw 'Docker Compose shutdown failed.' }
