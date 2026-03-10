# Script para limpiar archivos y carpetas obsoletas del proyecto
# Windows PowerShell

Write-Host ""
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host " PAI2 - Limpieza de Proyecto (Carpetas Obsoletas)" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host ""

$BASE_DIR = Split-Path -Parent $PSScriptRoot

Write-Host "Este script eliminara:" -ForegroundColor Yellow
Write-Host "  - cliente/ (version antigua, ahora en src/client/)" -ForegroundColor Gray
Write-Host "  - servidor/ (version antigua, ahora en src/server/)" -ForegroundColor Gray
Write-Host "  - .pytest_cache/ (cache de pytest)" -ForegroundColor Gray
Write-Host "  - Todos los __pycache__/ (caches de Python)" -ForegroundColor Gray
Write-Host ""

$confirm = Read-Host "Continuar con la limpieza? (s/n)"

if ($confirm -ne "s") {
    Write-Host "Cancelado" -ForegroundColor Gray
    exit 0
}

Write-Host ""

# Eliminar carpeta cliente/ antigua
if (Test-Path "$BASE_DIR\cliente") {
    Write-Host "Eliminando cliente/ (obsoleto)..." -ForegroundColor Yellow
    Remove-Item "$BASE_DIR\cliente" -Recurse -Force
    Write-Host "  OK: cliente/ eliminado" -ForegroundColor Green
} else {
    Write-Host "  - cliente/ ya no existe" -ForegroundColor Gray
}

# Eliminar carpeta servidor/ antigua
if (Test-Path "$BASE_DIR\servidor") {
    Write-Host "Eliminando servidor/ (obsoleto)..." -ForegroundColor Yellow
    Remove-Item "$BASE_DIR\servidor" -Recurse -Force
    Write-Host "  OK: servidor/ eliminado" -ForegroundColor Green
} else {
    Write-Host "  - servidor/ ya no existe" -ForegroundColor Gray
}

# Eliminar .pytest_cache/
if (Test-Path "$BASE_DIR\.pytest_cache") {
    Write-Host "Eliminando .pytest_cache/..." -ForegroundColor Yellow
    Remove-Item "$BASE_DIR\.pytest_cache" -Recurse -Force
    Write-Host "  OK: .pytest_cache/ eliminado" -ForegroundColor Green
} else {
    Write-Host "  - .pytest_cache/ ya no existe" -ForegroundColor Gray
}

# Eliminar todos los __pycache__/
Write-Host "Eliminando todos los __pycache__/..." -ForegroundColor Yellow
$pycaches = Get-ChildItem -Path $BASE_DIR -Filter "__pycache__" -Recurse -Directory -Force -ErrorAction SilentlyContinue
$count = 0
foreach ($cache in $pycaches) {
    Remove-Item $cache.FullName -Recurse -Force -ErrorAction SilentlyContinue
    $count++
}
if ($count -gt 0) {
    Write-Host "  OK: $count __pycache__/ eliminados" -ForegroundColor Green
} else {
    Write-Host "  - No se encontraron __pycache__/" -ForegroundColor Gray
}

# Eliminar archivos .pyc, .pyo, .pyd sueltos
Write-Host "Eliminando archivos .pyc, .pyo, .pyd..." -ForegroundColor Yellow
$pyc_count = 0
$extensions = @("*.pyc", "*.pyo", "*.pyd")
foreach ($ext in $extensions) {
    $files = Get-ChildItem -Path $BASE_DIR -Filter $ext -Recurse -File -Force -ErrorAction SilentlyContinue
    foreach ($file in $files) {
        Remove-Item $file.FullName -Force -ErrorAction SilentlyContinue
        $pyc_count++
    }
}
if ($pyc_count -gt 0) {
    Write-Host "  OK: $pyc_count archivos compilados eliminados" -ForegroundColor Green
} else {
    Write-Host "  - No se encontraron archivos compilados" -ForegroundColor Gray
}

Write-Host ""
Write-Host "======================================================================" -ForegroundColor Green
Write-Host " Limpieza completada exitosamente" -ForegroundColor Green
Write-Host "======================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Estructura limpia del proyecto:" -ForegroundColor Cyan
Write-Host "  src/      Codigo fuente (client/, server/, common/)" -ForegroundColor White
Write-Host "  tests/    Tests unitarios e integracion" -ForegroundColor White
Write-Host "  scripts/  Scripts de utilidad" -ForegroundColor White
Write-Host "  config/   Configuracion y seed de BD" -ForegroundColor White
Write-Host "  data/     Base de datos SQLite" -ForegroundColor White
Write-Host "  logs/     Logs del sistema" -ForegroundColor White
Write-Host ""

