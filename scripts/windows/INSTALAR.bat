@echo off
setlocal
rem Lives in scripts\windows; work from the repository root.
cd /d "%~dp0..\.."
echo Lyric Candle - Preparando entorno local
echo Necesita Python 3.10 a 3.14. Recomendado: Python 3.12 de 64 bits.
echo.
if exist ".venv\Scripts\python.exe" goto deps
for %%V in (3.12 3.13 3.11 3.14 3.10) do (
    py -%%V -c "import sys; assert sys.maxsize > 2**32" >nul 2>nul
    if not errorlevel 1 (
        py -%%V -m venv .venv
        if not errorlevel 1 goto deps
    )
)
python -c "import sys; assert (3,10) <= sys.version_info[:2] <= (3,14) and sys.maxsize > 2**32" >nul 2>nul
if errorlevel 1 goto missing
python -m venv .venv
if errorlevel 1 goto fail
:deps
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto fail
".venv\Scripts\python.exe" -c "from PySide6.QtWidgets import QApplication; from PySide6.QtMultimedia import QMediaPlayer"
if errorlevel 1 goto fail
echo.
echo Listo. Abre INICIAR.bat para usar Lyric Candle.
echo FFmpeg es opcional para editar y necesario para exportar MP4.
pause
exit /b 0
:missing
echo No se encontro Python compatible. Instala Python 3.12 x64 desde python.org.
echo Despues vuelve a ejecutar este archivo.
pause
exit /b 1
:fail
echo.
echo La instalacion no termino. Revisa el mensaje anterior y tu conexion.
pause
exit /b 1
