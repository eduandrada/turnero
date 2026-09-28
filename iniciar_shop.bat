@echo off
title Barberia - Shop Barber (Tienda)
cd /d "%~dp0"
echo ===================================================
echo   INICIANDO BARBERIA - SHOP BARBER (TIENDA)
echo ===================================================
echo.
echo [PC Local]:  http://127.0.0.1:8000/shop.html
echo [Desde Movil (mismo WiFi)]: http://192.168.100.2:8000/shop.html
echo.
echo Iniciando servidor backend...
start "" /b cmd /c "timeout /t 2 /nobreak >nul & start http://127.0.0.1:8000/shop.html"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir app
pause


