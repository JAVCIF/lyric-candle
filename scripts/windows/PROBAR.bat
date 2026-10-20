@echo off
setlocal
rem Lives in scripts\windows; work from the repository root.
cd /d "%~dp0..\.."
if not exist ".venv\Scripts\python.exe" (
    echo Ejecuta INSTALAR.bat primero.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" -m unittest discover -s tests -v
pause
