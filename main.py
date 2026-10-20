"""Desktop entry point. See LEEME.md for Windows installation."""
import sys
import traceback
from pathlib import Path

if __name__ == '__main__':
    try:
        from lyric_candle.app import main
        sys.exit(main())
    except Exception:
        details = traceback.format_exc()
        path = Path.home() / 'Lyric-Candle-startup-error.log'
        try:
            path.write_text(details, encoding='utf-8')
        except OSError:
            pass
        if sys.platform == 'win32':
            import ctypes
            ctypes.windll.user32.MessageBoxW(None, 'No se pudo iniciar Lyric Candle.\nEjecuta INSTALAR.bat y luego DIAGNOSTICO.bat.\n\nDetalle: ' + str(path), 'Lyric Candle · inicio', 16)
        else:
            print(details, file=sys.stderr)
        raise SystemExit(1)
