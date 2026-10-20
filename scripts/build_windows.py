"""Build the full Windows app folder; optionally add portable settings and a ZIP."""
from __future__ import annotations
import argparse
import hashlib
from pathlib import Path
import shutil
import subprocess
import sys
import os

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--portable', action='store_true', help='Add portable.txt beside the EXE')
    parser.add_argument('--zip', action='store_true', dest='make_zip', help='Create ZIP and SHA-256 in dist/')
    args = parser.parse_args()
    if sys.platform != 'win32' or sys.maxsize <= 2**32:
        parser.error('Build on 64-bit Windows with 64-bit Python. PyInstaller does not cross-compile this app.')
    sys.path.insert(0, str(ROOT))
    from lyric_candle.model import VERSION
    command = [sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', '--windowed', '--onedir',
               '--name', 'LyricCandle', '--icon', str(ROOT / 'lyric_candle/assets/logo.ico'),
               '--distpath', str(ROOT / 'dist'), '--workpath', str(ROOT / 'build'),
               '--specpath', str(ROOT / 'build')]
    for source, target in (('lyric_candle/assets', 'lyric_candle/assets'),
                           ('examples', 'examples'), ('tools/LEEME.txt', 'tools')):
        command += ['--add-data', str(ROOT / source) + os.pathsep + target]
    command.append(str(ROOT / 'main.py'))
    subprocess.run(command, cwd=ROOT, check=True)
    folder = ROOT / 'dist/LyricCandle'
    if not (folder / 'LyricCandle.exe').is_file():
        raise RuntimeError('PyInstaller did not produce LyricCandle.exe')
    for name in ('README.md', 'README.es.md', 'LEEME.md', 'CHANGELOG.md', 'CONTRIBUTING.md',
                 'THIRD_PARTY.md', 'VERIFICACION.md', 'LICENSE'):
        shutil.copy2(ROOT / name, folder / name)
    shutil.copytree(ROOT / 'docs', folder / 'docs', dirs_exist_ok=True)
    python_license = Path(sys.base_prefix) / 'LICENSE.txt'
    if python_license.is_file():
        shutil.copy2(python_license, folder / 'docs/licenses/Python-LICENSE.txt')
    # External tools belong next to the executable; none are downloaded or bundled.
    (folder / 'tools').mkdir(exist_ok=True)
    shutil.copy2(ROOT / 'tools/LEEME.txt', folder / 'tools/LEEME.txt')
    marker = folder / 'portable.txt'
    if args.portable:
        marker.write_text('', encoding='utf-8')
    else:
        marker.unlink(missing_ok=True)
    if args.make_zip:
        base = ROOT / 'dist' / f'Lyric-Candle-{VERSION}-Windows-x64'
        archive = Path(shutil.make_archive(str(base), 'zip', root_dir=folder.parent, base_dir=folder.name))
        checksum = hashlib.sha256()
        with archive.open('rb') as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                checksum.update(chunk)
        archive.with_suffix(archive.suffix + '.sha256').write_text(f'{checksum.hexdigest()}  {archive.name}\n', encoding='utf-8')
        print(archive)
    else:
        print(folder)


if __name__ == '__main__':
    main()
