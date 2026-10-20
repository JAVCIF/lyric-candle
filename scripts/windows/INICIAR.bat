@echo off
setlocal
rem Lives in scripts\windows; work from the repository root.
cd /d "%~dp0..\.."
if not exist ".venv\Scripts\pythonw.exe" (
    call "%~dp0INSTALAR.bat"
    if errorlevel 1 exit /b 1
)
start "Lyric Candle" ".venv\Scripts\pythonw.exe" "%CD%\main.py"
