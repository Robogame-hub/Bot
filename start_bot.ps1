# Запуск LohotronBot в фоновом режиме (PowerShell)
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Запуск LohotronBot в фоновом режиме" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Переход в директорию скрипта
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptPath

# Проверка, не запущен ли уже бот
$existingProcess = Get-Process python -ErrorAction SilentlyContinue | Where-Object {
    $_.Path -like "*python*" -and (Get-WmiObject Win32_Process -Filter "ProcessId = $($_.Id)").CommandLine -like "*LohotronBot.py*"
}

if ($existingProcess) {
    Write-Host "⚠️  Бот уже запущен! (PID: $($existingProcess.Id))" -ForegroundColor Yellow
    Write-Host "Остановите его перед повторным запуском." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Для остановки используйте:" -ForegroundColor Yellow
    Write-Host "  Stop-Process -Name python -Force" -ForegroundColor White
    pause
    exit
}

# Запуск бота в фоновом режиме
try {
    $process = Start-Process python -ArgumentList "LohotronBot.py" -WindowStyle Hidden -PassThru
    Start-Sleep -Seconds 2
    
    if (Get-Process -Id $process.Id -ErrorAction SilentlyContinue) {
        Write-Host "✅ Бот успешно запущен в фоновом режиме!" -ForegroundColor Green
        Write-Host "   PID процесса: $($process.Id)" -ForegroundColor Gray
        Write-Host ""
        Write-Host "📱 Проверьте работу бота в Telegram" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "Для остановки бота используйте:" -ForegroundColor Yellow
        Write-Host "  Stop-Process -Name python -Force" -ForegroundColor White
        Write-Host "  или" -ForegroundColor Yellow
        Write-Host "  taskkill /F /PID $($process.Id)" -ForegroundColor White
    } else {
        Write-Host "❌ Ошибка при запуске бота!" -ForegroundColor Red
    }
} catch {
    Write-Host "❌ Ошибка: $_" -ForegroundColor Red
}

Write-Host ""
pause

