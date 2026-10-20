@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\pythonw.exe" (
    call INSTALAR.bat
    if errorlevel 1 exit /b 1
)
start "Lyric Candle" ".venv\Scripts\pythonw.exe" "%~dp0main.py"
