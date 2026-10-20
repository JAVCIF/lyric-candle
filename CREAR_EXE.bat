@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Ejecuta INSTALAR.bat primero.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" -m pip install "pyinstaller>=6.11,<7"
if errorlevel 1 goto fail
".venv\Scripts\python.exe" scripts\build_windows.py
if errorlevel 1 goto fail
echo Listo: dist\LyricCandle\LyricCandle.exe
echo Distribuye la carpeta dist\LyricCandle completa, no solamente el EXE.
echo Para exportar: coloca ffmpeg.exe y ffprobe.exe en dist\LyricCandle\tools\ o en el PATH.
echo Version portable: crea un archivo vacio portable.txt en dist\LyricCandle\.
pause
exit /b 0
:fail
echo No se pudo crear el EXE. Revisa los mensajes anteriores.
pause
exit /b 1
