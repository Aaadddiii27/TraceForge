$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot | Split-Path -Parent)
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { throw 'Docker Desktop is required. Install and start Docker Desktop, then rerun this script.' }
if (-not (Test-Path '.env')) { Copy-Item '.env.example' '.env'; Write-Host 'Created .env from .env.example. Review local credentials before deployment.' }
docker compose up --build -d
if ($LASTEXITCODE -ne 0) { throw 'Docker Compose startup failed. Review the output above.' }
Write-Host ''
Write-Host 'AI Runtime is starting:'
Write-Host '  Dashboard:   http://localhost:3000'
Write-Host '  API docs:    http://localhost:8000/docs'
Write-Host '  Prometheus:  http://localhost:9090'
Write-Host '  Grafana:     http://localhost:3001 (admin / value in .env)'
Write-Host 'Use .\scripts\windows\stop.ps1 to stop the stack.'
