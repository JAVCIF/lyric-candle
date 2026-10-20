"""Check portable startup, silent installation, installed startup and uninstall."""
import hashlib
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lyric_candle.model import VERSION  # noqa: E402 - after adding the repo to sys.path


def run(*args):
    subprocess.run([str(arg) for arg in args], check=True, timeout=120)


def main():
    if sys.platform != 'win32':
        raise SystemExit('Windows required for executable and installer checks.')
    archive = ROOT / 'dist' / f'Lyric-Candle-{VERSION}-Windows-x64.zip'
    setup = ROOT / 'dist' / f'Lyric-Candle-{VERSION}-Setup-x64.exe'
    for file in (archive, setup):
        expected = file.with_suffix(file.suffix + '.sha256').read_text(encoding='utf-8').split()[0]
        assert hashlib.sha256(file.read_bytes()).hexdigest() == expected, file
    with tempfile.TemporaryDirectory(prefix='Lyric Candle packages ') as temp:
        target = Path(temp)
        with zipfile.ZipFile(archive) as zipped:
            zipped.extractall(target / 'Portable')
        portable = target / 'Portable/LyricCandle'
        for name in ('LyricCandle.exe', 'LICENSE', 'portable.txt', '_internal'):
            assert (portable / name).exists(), name
        run(portable / 'LyricCandle.exe', '--smoke-test')
        assert (portable / 'data/app.log').is_file(), 'Portable storage was not used'
        installed = target / 'Installed Lyric Candle'
        run(setup, '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/SP-',
            f'/DIR={installed}', f'/LOG={target / "install.log"}')
        for name in ('LyricCandle.exe', 'LICENSE', '_internal', 'unins000.exe'):
            assert (installed / name).exists(), name
        assert not (installed / 'portable.txt').exists(), 'Installer must use per-user storage'
        assert not (installed / 'data').exists(), 'Portable settings must not be installed'
        run(installed / 'LyricCandle.exe', '--smoke-test')
        run(installed / 'unins000.exe', '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART')
        for _ in range(100):
            if not (installed / 'LyricCandle.exe').exists():
                break
            time.sleep(.1)
        assert not (installed / 'LyricCandle.exe').exists(), 'Uninstall did not remove executable'
    print('SHA-256, extracted portable startup, silent install, installed startup and uninstall passed.')


if __name__ == '__main__':
    main()
