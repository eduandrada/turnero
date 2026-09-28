@echo off
title Barberia - Pantalla TV Cartelera en Vivo (El Que Sigue)
cd /d "%~dp0"
echo =========================================================
echo   INICIANDO PANTALLA TV CARTELERA (SIGUIENTE EN TURNO)
echo =========================================================
echo.
echo [PC Local]:  http://127.0.0.1:8000/display.html
echo [Desde Smart TV o Red Local]: http://192.168.100.2:8000/display.html
echo.
echo Iniciando servidor backend...
start "" /b cmd /c "timeout /t 2 /nobreak >nul & start http://127.0.0.1:8000/display.html"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir app
pause


