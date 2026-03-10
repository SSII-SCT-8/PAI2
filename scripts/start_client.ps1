# Script para ejecutar solo el cliente.
# Windows PowerShell

Write-Host ""
Write-Host "Iniciando cliente..." -ForegroundColor Yellow
Write-Host ""

$BASE_DIR = Split-Path -Parent $PSScriptRoot
$TRANSPORT_MODE = if ($env:TRANSPORT_MODE) { $env:TRANSPORT_MODE.ToUpper() } else { "PLAIN" }
$SERVER_HOST = if ($env:SERVER_HOST) { $env:SERVER_HOST } else { "127.0.0.1" }
$SERVER_PORT = if ($env:SERVER_PORT) { $env:SERVER_PORT } else { "9999" }

if (-not (Test-Path "$BASE_DIR\src\client\client.py")) {
    Write-Host "Error: no se encontro src/client/client.py" -ForegroundColor Red
    exit 1
}

Write-Host "Conectando al servidor en $SERVER_HOST`:$SERVER_PORT..." -ForegroundColor Green
Write-Host "Modo de transporte: $TRANSPORT_MODE" -ForegroundColor Cyan

if ($TRANSPORT_MODE -eq "TLS") {
    $TLS_CA_FILE = if ($env:TLS_CA_FILE) { $env:TLS_CA_FILE } else { "config/tls/ca.crt" }
    $TLS_SERVER_HOSTNAME = if ($env:TLS_SERVER_HOSTNAME) { $env:TLS_SERVER_HOSTNAME } else { $SERVER_HOST }
    $TLS_MIN_VERSION = if ($env:TLS_MIN_VERSION) { $env:TLS_MIN_VERSION } else { "1.3" }
    Write-Host "TLS CA:          $TLS_CA_FILE" -ForegroundColor Cyan
    Write-Host "TLS hostname:    $TLS_SERVER_HOSTNAME" -ForegroundColor Cyan
    Write-Host "TLS min version: $TLS_MIN_VERSION" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "Usuarios de prueba:" -ForegroundColor Cyan
Write-Host "  - alice / AliceSecure2024!" -ForegroundColor White
Write-Host "  - bob / BobPassword123#" -ForegroundColor White
Write-Host "  - admin / AdminPass2024$" -ForegroundColor White
Write-Host ""
Write-Host ("=" * 60) -ForegroundColor Gray

cd $BASE_DIR
python -m src.client.client
