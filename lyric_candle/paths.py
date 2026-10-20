"""Where Lyric Candle keeps its settings, autosaves and log.

Installed (default): the user's application data folder, e.g.
%APPDATA%\\JAVCIF\\LyricCandleAlpha on Windows.
Portable: when a file named portable.txt sits next to LyricCandle.exe (or next to
main.py when running from source), everything goes to a data folder beside it, so the
whole program can live on a USB drive. If that folder cannot be written, the installed
location is used instead.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

from PySide6.QtCore import QSettings, QStandardPaths


def program_dir() -> Path:
    """Folder of LyricCandle.exe, or of main.py when running from source."""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def portable_marker() -> Path:
    return program_dir() / 'portable.txt'


def _writable(folder: Path) -> bool:
    try:
        folder.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryFile(dir=folder):
            pass
        return True
    except OSError:
        return False


def is_portable() -> bool:
    return portable_marker().is_file() and _writable(program_dir() / 'data')


def data_dir() -> Path:
    """Settings, autosaves (recovery-*.lyric.json) and app.log live here."""
    if is_portable():
        return program_dir() / 'data'
    folder = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation))
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def app_settings() -> QSettings:
    if is_portable():
        return QSettings(str(data_dir() / 'settings.ini'), QSettings.Format.IniFormat)
    return QSettings('JAVCIF', 'LyricCandleAlpha')


def describe_location() -> str:
    return os.fspath(data_dir())
