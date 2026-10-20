"""Desktop entry point. See LEEME.md for Windows installation."""
import sys
import traceback
from pathlib import Path

if __name__ == '__main__':
    try:
        from lyric_candle.app import main
        sys.exit(main(smoke_test='--smoke-test' in sys.argv))
    except Exception:  # noqa: BLE001 - startup boundary: log any failure and tell the user.
        details = traceback.format_exc()
        path = Path.home() / 'Lyric-Candle-startup-error.log'
        try:
            path.write_text(details, encoding='utf-8')
        except OSError:
            pass
        if sys.platform == 'win32' and '--smoke-test' not in sys.argv:
            import ctypes
            ctypes.windll.user32.MessageBoxW(None, 'No se pudo iniciar Lyric Candle.\nEjecuta INSTALAR.bat y luego DIAGNOSTICO.bat.\n\nDetalle: ' + str(path), 'Lyric Candle · inicio', 16)
        else:
            print(details, file=sys.stderr)
        raise SystemExit(1) from None
