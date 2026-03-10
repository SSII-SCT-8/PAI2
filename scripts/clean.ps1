# Script para limpiar logs y base de datos
# Windows PowerShell

Write-Host ""
Write-Host "======================================================================" -ForegroundColor Yellow
Write-Host " PAI2 - Limpieza de datos" -ForegroundColor Yellow
Write-Host "======================================================================" -ForegroundColor Yellow
Write-Host ""

$BASE_DIR = Split-Path -Parent $PSScriptRoot

$confirm = Read-Host "Esto eliminará logs y la base de datos. ¿Continuar? (s/n)"

if ($confirm -ne "s") {
    Write-Host "Cancelado" -ForegroundColor Gray
    exit 0
}

# Limpiar logs
if (Test-Path "$BASE_DIR\logs\*.log") {
    Write-Host "Eliminando logs..." -ForegroundColor Yellow
    Remove-Item "$BASE_DIR\logs\*.log" -Force
    Write-Host "  ✓ Logs eliminados" -ForegroundColor Green
}

# Limpiar base de datos
if (Test-Path "$BASE_DIR\data\server.db") {
    Write-Host "Eliminando base de datos..." -ForegroundColor Yellow
    Remove-Item "$BASE_DIR\data\server.db" -Force
    Write-Host "  ✓ Base de datos eliminada" -ForegroundColor Green
}

Write-Host ""
Write-Host "======================================================================" -ForegroundColor Green
Write-Host " Limpieza completada" -ForegroundColor Green
Write-Host "======================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Ejecute 'python config\seed_database.py' para recrear usuarios de prueba" -ForegroundColor Cyan
Write-Host ""
