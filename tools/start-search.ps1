$ErrorActionPreference = 'Stop'
$repositoryRoot = Split-Path -Parent $PSScriptRoot
$pythonExecutable = Join-Path $repositoryRoot '.venv/Scripts/python.exe'
Push-Location $repositoryRoot
try {
    @'
from pathlib import Path
from dotenv import dotenv_values, set_key
import secrets
path = Path('.env')
values = dotenv_values(path)
if not values.get('SEARXNG_SECRET'):
    set_key(path, 'SEARXNG_SECRET', secrets.token_hex(32))
set_key(path, 'SEARXNG_BASE_URL', 'http://127.0.0.1:8080')
print('Local search configured; existing credentials and cloud settings preserved.')
'@ | & $pythonExecutable -
    if ($LASTEXITCODE -ne 0) { throw 'Search configuration failed' }
    docker compose up -d --wait postgres searxng
    if ($LASTEXITCODE -ne 0) { throw 'Local search services failed health checks' }
} finally {
    Pop-Location
}
