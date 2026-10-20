@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Ejecuta INSTALAR.bat primero.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" main.py
pause
