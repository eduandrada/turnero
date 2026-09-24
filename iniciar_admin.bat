@echo off
title Barberia - Panel Administrativo
cd /d "%~dp0"
echo ===================================================
echo   INICIANDO BARBERIA - PANEL ADMINISTRATIVO
echo ===================================================
echo.
echo Abriendo navegador en http://127.0.0.1:8000/admin.html ...
start "" "http://127.0.0.1:8000/admin.html"
echo.
echo Iniciando servidor backend en puerto 8000...
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
pause
