@echo off
title Barberia - App Publica (Turnero)
cd /d "%~dp0"
echo ===================================================
echo   INICIANDO BARBERIA - APP PUBLICA (TURNERO)
echo ===================================================
echo.
echo Abriendo navegador en http://127.0.0.1:8000/ ...
start "" "http://127.0.0.1:8000/"
echo.
echo Iniciando servidor backend en puerto 8000...
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
pause
