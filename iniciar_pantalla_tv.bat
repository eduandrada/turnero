@echo off
title Barberia - Pantalla TV Cartelera en Vivo (El Que Sigue)
cd /d "%~dp0"
echo =========================================================
echo   INICIANDO PANTALLA TV CARTELERA (SIGUIENTE EN TURNO)
echo =========================================================
echo.
echo Abriendo pantalla cartelera en http://127.0.0.1:8000/display.html ...
start "" "http://127.0.0.1:8000/display.html"
echo.
echo Iniciando servidor backend en puerto 8000 si no estuviese activo...
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
pause
