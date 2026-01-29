@echo off
chcp 65001 >nul
echo ========================================
echo   Остановка LohotronBot
echo ========================================
echo.

tasklist /FI "IMAGENAME eq python.exe" 2>NUL | find /I /N "python.exe">NUL
if "%ERRORLEVEL%"=="0" (
    echo Остановка процессов Python...
    taskkill /F /IM python.exe
    if errorlevel 1 (
        echo ❌ Ошибка при остановке бота!
    ) else (
        echo ✅ Бот остановлен!
    )
) else (
    echo ℹ️  Бот не запущен.
)

echo.
pause

