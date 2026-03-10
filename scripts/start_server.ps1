# Script para ejecutar solo el servidor.
# Windows PowerShell

Write-Host ""
Write-Host ("=" * 70) -ForegroundColor Cyan
Write-Host " PAI2 - BYODSEC Road Warrior VPN SSL/TLS (Servidor)" -ForegroundColor Cyan
Write-Host ("=" * 70) -ForegroundColor Cyan
Write-Host "Iniciando servidor..." -ForegroundColor Yellow
Write-Host ""

$BASE_DIR = Split-Path -Parent $PSScriptRoot
$TRANSPORT_MODE = "TLS"

if (-not (Test-Path "$BASE_DIR\src\server\server.py")) {
    Write-Host "Error: no se encontro src/server/server.py" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path "$BASE_DIR\data\server.db")) {
    Write-Host "Base de datos no encontrada. Inicializando..." -ForegroundColor Yellow
    python "$BASE_DIR\config\seed_database.py"
    Write-Host ""
}

$TLS_CERT_FILE = if ($env:TLS_CERT_FILE) { $env:TLS_CERT_FILE } else { "config/tls/server.crt" }
$TLS_KEY_FILE = if ($env:TLS_KEY_FILE) { $env:TLS_KEY_FILE } else { "config/tls/server.key" }
$TLS_CA_FILE = if ($env:TLS_CA_FILE) { $env:TLS_CA_FILE } else { "config/tls/ca.crt" }
$TLS_MIN_VERSION = if ($env:TLS_MIN_VERSION) { $env:TLS_MIN_VERSION } else { "1.3" }

Write-Host "Iniciando servidor en puerto 9999..." -ForegroundColor Green
Write-Host "Modo de transporte: $TRANSPORT_MODE" -ForegroundColor Cyan
Write-Host "TLS cert: $TLS_CERT_FILE" -ForegroundColor Cyan
Write-Host "TLS key:  $TLS_KEY_FILE" -ForegroundColor Cyan
Write-Host "TLS ca:   $TLS_CA_FILE" -ForegroundColor Cyan
Write-Host "TLS min:  $TLS_MIN_VERSION" -ForegroundColor Cyan

Write-Host ""
Write-Host "Para detener el servidor: Ctrl+C" -ForegroundColor Cyan
Write-Host "Logs: logs/server.log" -ForegroundColor Cyan
Write-Host ""
Write-Host ("=" * 60) -ForegroundColor Gray

cd $BASE_DIR
python -m src.server.server
