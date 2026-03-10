param(
    [switch]$SkipDbReset,
    [switch]$GenerateCerts
)

# Script de demostracion para Windows PowerShell (TLS-only)
# Ejecuta servidor y cliente en ventanas separadas.

Write-Host ""
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host " PAI2 - BYODSEC Road Warrior VPN SSL/TLS" -ForegroundColor Cyan
Write-Host " Demo dinamica (modo: TLS)" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host ""

$BASE_DIR = Split-Path -Parent $PSScriptRoot

if (-not (Test-Path "$BASE_DIR\src")) {
    Write-Host "Error: no se encontro el directorio src/" -ForegroundColor Red
    Write-Host "Ejecute este script desde el directorio scripts/" -ForegroundColor Red
    exit 1
}

# Configuracion de entorno compartida por servidor y cliente
$env:SERVER_HOST = "127.0.0.1"
$env:SERVER_PORT = "9999"
$env:TRANSPORT_MODE = "TLS"
$env:TLS_CERT_FILE = "config/tls/server.crt"
$env:TLS_KEY_FILE = "config/tls/server.key"
$env:TLS_CA_FILE = "config/tls/ca.crt"
$env:TLS_SERVER_HOSTNAME = "localhost"
$env:TLS_MIN_VERSION = "1.3"

$missingTlsFiles = @()
foreach ($tlsFile in @($env:TLS_CERT_FILE, $env:TLS_KEY_FILE, $env:TLS_CA_FILE)) {
    if (-not (Test-Path (Join-Path $BASE_DIR $tlsFile))) {
        $missingTlsFiles += $tlsFile
    }
}

if ($GenerateCerts -or $missingTlsFiles.Count -gt 0) {
    Write-Host "1. Generando certificados TLS..." -ForegroundColor Yellow
    python "$BASE_DIR\scripts\generate_tls_certs.py" --force
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Error generando certificados TLS." -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "1. Certificados TLS detectados." -ForegroundColor Green
}

if (-not $SkipDbReset) {
    Write-Host "2. Reiniciando base de datos..." -ForegroundColor Yellow
    $dbPath = Join-Path $BASE_DIR "data\server.db"
    if (Test-Path $dbPath) {
        Remove-Item $dbPath -Force
        Write-Host "   OK Base de datos eliminada" -ForegroundColor Gray
    }
    python "$BASE_DIR\config\seed_database.py"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Error inicializando base de datos." -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "2. SkipDbReset activo: se conserva la base de datos actual." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "3. Iniciando SERVIDOR en nueva ventana..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$BASE_DIR'; .\scripts\start_server.ps1"

Write-Host ""
Write-Host "   Esperando 3 segundos para que el servidor inicie..." -ForegroundColor Gray
Start-Sleep -Seconds 3

Write-Host ""
Write-Host "4. Iniciando CLIENTE en nueva ventana..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$BASE_DIR'; .\scripts\start_client.ps1"

Write-Host ""
Write-Host "======================================================================" -ForegroundColor Green
Write-Host " Demo iniciada exitosamente" -ForegroundColor Green
Write-Host "======================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Modo activo: TLS" -ForegroundColor Cyan
Write-Host "Host/Puerto: $env:SERVER_HOST`:$env:SERVER_PORT" -ForegroundColor Cyan
Write-Host "TLS CA:      $env:TLS_CA_FILE" -ForegroundColor Cyan
Write-Host "TLS Cert:    $env:TLS_CERT_FILE" -ForegroundColor Cyan
Write-Host "TLS Hostname:$env:TLS_SERVER_HOSTNAME" -ForegroundColor Cyan
Write-Host ""
Write-Host "USUARIOS DE PRUEBA:" -ForegroundColor Cyan
Write-Host "  - Usuario: alice    | Password: AliceSecure2024!" -ForegroundColor White
Write-Host "  - Usuario: bob      | Password: BobPassword123#" -ForegroundColor White
Write-Host "  - Usuario: admin    | Password: AdminPass2024$" -ForegroundColor White
Write-Host ""
Write-Host "INSTRUCCIONES:" -ForegroundColor Cyan
Write-Host "  1. En el cliente, usa opcion 2 para LOGIN" -ForegroundColor White
Write-Host "  2. Prueba el flujo principal" -ForegroundColor White
Write-Host "  3. TLS 1.3 queda activo automaticamente" -ForegroundColor White
Write-Host ""
Write-Host "LOGS: revisa logs/server.log y logs/client.log" -ForegroundColor Cyan
Write-Host ""
Write-Host "Para detener: Ctrl+C en ambas ventanas" -ForegroundColor Gray
Write-Host ""
