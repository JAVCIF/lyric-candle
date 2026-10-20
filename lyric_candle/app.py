"""Entry point; the window itself lives in lyric_candle.window."""
from __future__ import annotations

import logging
import sys

from PySide6.QtCore import QLibraryInfo, QLocale, QProcess, QTimer, QTranslator
from PySide6.QtWidgets import QApplication, QMessageBox

from .i18n import language, resolve, set_language, tr
from .paths import app_settings, data_dir
from .widgets import app_icon
from .window.common import DARK, fps_text, image_filter, media_filter, version_label
from .window.main_window import MainWindow

# Re-exported for code and tests written against the single-module window.
__all__ = ['DARK', 'MainWindow', 'fps_text', 'image_filter', 'main', 'media_filter', 'version_label']


def main(smoke_test=False):
    if sys.platform == 'win32':
        try:  # Own taskbar identity, so Windows shows our icon instead of Python's.
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('JAVCIF.LyricCandle')
        except (AttributeError, OSError):
            pass
    app = QApplication(sys.argv)
    app.setOrganizationName('JAVCIF')
    app.setApplicationName('LyricCandleAlpha')
    app.setWindowIcon(app_icon())
    set_language(resolve(app_settings().value('language', 'auto'), QLocale.system().uiLanguages()))
    # Qt's own texts (Yes/No/Save buttons, file and color dialogs) in the same language.
    qt_translator = QTranslator(app)
    if qt_translator.load(f'qtbase_{language()}', QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)):
        app.installTranslator(qt_translator)
    log_dir = data_dir()
    logging.basicConfig(filename=log_dir / 'app.log', level=logging.INFO,
                        format='%(asctime)s %(levelname)s %(message)s')
    def handle_error(kind, value, tb):
        logging.getLogger('lyric_candle').error('Unhandled exception', exc_info=(kind, value, tb))
        if smoke_test:
            app.exit(1)
            return
        QMessageBox.critical(None, tr('Lyric Candle · error'), tr('{0}\n\nSe guardó el detalle en:\n{1}').format(value, log_dir / "app.log"))
    sys.excepthook = handle_error
    window = MainWindow(recover=not smoke_test)
    window.show()
    if smoke_test:
        QTimer.singleShot(1000, window.close)
    code = app.exec()
    if window.restart_requested:
        # Same program and arguments: LyricCandle.exe when packaged, python main.py from source.
        arguments = sys.argv[1:] if getattr(sys, 'frozen', False) else sys.argv
        QProcess.startDetached(sys.executable, arguments)
    return code
