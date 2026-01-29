@echo off
chcp 65001 >nul
echo ========================================
echo   Запуск LohotronBot в фоновом режиме
echo ========================================
echo.

cd /d "%~dp0"

REM Проверка наличия Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python не найден! Установите Python и добавьте его в PATH.
    pause
    exit /b 1
)

REM Проверка наличия файла бота
if not exist "LohotronBot.py" (
    echo ❌ Файл LohotronBot.py не найден!
    pause
    exit /b 1
)

REM Запуск бота в фоновом режиме
echo Запуск бота...
start /B python LohotronBot.py

timeout /t 2 /nobreak >nul

REM Проверка, что процесс запустился
tasklist /FI "IMAGENAME eq python.exe" 2>NUL | find /I /N "python.exe">NUL
if "%ERRORLEVEL%"=="0" (
    echo ✅ Бот успешно запущен в фоновом режиме!
    echo.
    echo 📱 Проверьте работу бота в Telegram
    echo.
    echo Для остановки бота используйте:
    echo   taskkill /F /IM python.exe
) else (
    echo ❌ Ошибка при запуске бота!
    echo Проверьте наличие ошибок выше.
)

echo.
pause

