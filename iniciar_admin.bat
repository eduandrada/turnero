@echo off
title Barberia - Panel Administrativo
cd /d "%~dp0"
echo ===================================================
echo   INICIANDO BARBERIA - PANEL ADMINISTRATIVO
echo ===================================================
echo.
echo [PC Local]:  http://127.0.0.1:8000/admin.html
echo [Desde Movil (mismo WiFi)]: http://192.168.100.2:8000/admin.html
echo.
start "" "http://127.0.0.1:8000/admin.html"
echo Iniciando servidor backend en 0.0.0.0:8000...
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
pause

