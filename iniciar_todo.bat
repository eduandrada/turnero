@echo off
title Barberia Ecosystem - Todo Integrado
cd /d "%~dp0"
echo ===================================================
echo   INICIANDO SISTEMA INTEGRADO BARBERIA
echo ===================================================
echo.
echo Para acceder desde esta PC:
echo   App Publica: http://127.0.0.1:8000/
echo   Shop Barber: http://127.0.0.1:8000/shop.html
echo   Panel Admin: http://127.0.0.1:8000/admin.html
echo.
echo Para acceder desde tu CELULAR (mismo WiFi):
echo   Panel Admin: http://192.168.100.2:8000/admin.html
echo   App Publica: http://192.168.100.2:8000/
echo   Shop Barber: http://192.168.100.2:8000/shop.html
echo.
echo Iniciando servidor backend...
start "" /b cmd /c "timeout /t 2 /nobreak >nul & start http://127.0.0.1:8000/ & start http://127.0.0.1:8000/shop.html & start http://127.0.0.1:8000/admin.html"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir app
pause


