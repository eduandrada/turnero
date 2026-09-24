@echo off
title Barberia - Shop Barber (Tienda)
cd /d "%~dp0"
echo ===================================================
echo   INICIANDO BARBERIA - SHOP BARBER (TIENDA)
echo ===================================================
echo.
echo Abriendo navegador en http://127.0.0.1:8000/shop.html ...
start "" "http://127.0.0.1:8000/shop.html"
echo.
echo Iniciando servidor backend en puerto 8000...
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
pause
