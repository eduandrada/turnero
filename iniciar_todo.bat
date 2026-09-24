@echo off
title Barberia Ecosystem - Todo Integrado
cd /d "%~dp0"
echo ===================================================
echo   INICIANDO SISTEMA INTEGRADO BARBERIA
echo ===================================================
echo.
echo Abriendo App Publica, Shop Barber y Panel Admin...
start "" "http://127.0.0.1:8000/"
start "" "http://127.0.0.1:8000/shop.html"
start "" "http://127.0.0.1:8000/admin.html"
echo.
echo Servidor escuchando en http://127.0.0.1:8000
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
pause
