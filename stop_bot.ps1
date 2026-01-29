# Остановка LohotronBot
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Остановка LohotronBot" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$processes = Get-Process python -ErrorAction SilentlyContinue

if ($processes) {
    Write-Host "Найдено процессов Python: $($processes.Count)" -ForegroundColor Gray
    Write-Host "Остановка..." -ForegroundColor Yellow
    
    try {
        Stop-Process -Name python -Force -ErrorAction Stop
        Write-Host "✅ Бот остановлен!" -ForegroundColor Green
    } catch {
        Write-Host "❌ Ошибка при остановке: $_" -ForegroundColor Red
    }
} else {
    Write-Host "ℹ️  Бот не запущен." -ForegroundColor Gray
}

Write-Host ""
pause

