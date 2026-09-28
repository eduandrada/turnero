@echo off
title Barberia - App Publica (Turnero)
cd /d "%~dp0"
echo ===================================================
echo   INICIANDO BARBERIA - APP PUBLICA (TURNERO)
echo ===================================================
echo.
echo [PC Local]:  http://127.0.0.1:8000/
echo [Desde Movil (mismo WiFi)]: http://192.168.100.2:8000/
echo.
echo Iniciando servidor backend...
start "" /b cmd /c "timeout /t 2 /nobreak >nul & start http://127.0.0.1:8000/"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir app
pause


