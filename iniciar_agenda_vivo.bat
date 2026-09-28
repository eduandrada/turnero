@echo off
title Barberia - Agenda en Vivo (Sala de Espera / Pantalla TV)
cd /d "%~dp0"
echo =========================================================
echo   INICIANDO PANTALLA EN VIVO - AGENDA SALA DE ESPERA (TV)
echo =========================================================
echo.
echo [PC Local]:  http://127.0.0.1:8000/live.html
echo [Desde Red Local / TV]: http://192.168.100.2:8000/live.html
echo.
echo Iniciando servidor backend...
start "" /b cmd /c "timeout /t 2 /nobreak >nul & start http://127.0.0.1:8000/live.html"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir app
pause


