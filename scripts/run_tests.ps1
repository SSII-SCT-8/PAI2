# Script para ejecutar todos los tests
# Windows PowerShell

Write-Host ""
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host " PAI2 - Ejecutando Suite de Tests" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host ""

$BASE_DIR = Split-Path -Parent $PSScriptRoot

# Cambiar al directorio raíz
Set-Location $BASE_DIR

Write-Host "Ejecutando tests..." -ForegroundColor Yellow
Write-Host ""

# Ejecutar tests con unittest discover
python -m unittest discover -s tests -p "test_*.py" -v

$exitCode = $LASTEXITCODE

Write-Host ""
if ($exitCode -eq 0) {
    Write-Host "======================================================================" -ForegroundColor Green
    Write-Host " Todos los tests pasaron exitosamente" -ForegroundColor Green
    Write-Host "======================================================================" -ForegroundColor Green
} else {
    Write-Host "======================================================================" -ForegroundColor Red
    Write-Host " Algunos tests fallaron" -ForegroundColor Red
    Write-Host "======================================================================" -ForegroundColor Red
}
Write-Host ""

exit $exitCode
