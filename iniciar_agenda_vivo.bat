@echo off
title Barberia - Agenda en Vivo (Sala de Espera / Pantalla TV)
cd /d "%~dp0"
echo =========================================================
echo   INICIANDO PANTALLA EN VIVO - AGENDA SALA DE ESPERA (TV)
echo =========================================================
echo.
echo Abriendo navegador en http://127.0.0.1:8000/live.html ...
start "" "http://127.0.0.1:8000/live.html"
echo.
echo Iniciando servidor backend en puerto 8000 si no estuviese activo...
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
pause
