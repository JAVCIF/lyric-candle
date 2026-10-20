"""Compile a per-user Windows x64 installer with Inno Setup 6 or later."""
import argparse
import hashlib
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--compiler', help='Path to ISCC.exe')
    args = parser.parse_args()
    if sys.platform != 'win32':
        parser.error('Run on Windows after building the application folder.')
    compiler = args.compiler or shutil.which('ISCC.exe')
    if not compiler:
        for base in ('ProgramFiles(x86)', 'ProgramFiles'):
            for version in ('6', '7'):
                path = Path(os.environ.get(base, 'C:/Program Files (x86)')) / f'Inno Setup {version}/ISCC.exe'
                if path.is_file():
                    compiler = str(path)
                    break
    if not compiler:
        parser.error('Install Inno Setup 6+ or pass --compiler PATH.')
    folder = ROOT / 'dist/LyricCandle'
    if not (folder / 'LyricCandle.exe').is_file():
        parser.error('Build first: python scripts/build_windows.py --portable --zip')
    sys.path.insert(0, str(ROOT))
    from lyric_candle.model import VERSION
    numeric = '.'.join(re.match(r'^(\d+\.\d+\.\d+)', VERSION).group(1).split('.') + ['0'])
    subprocess.run([compiler, f'/DAppVersion={VERSION}', f'/DAppNumericVersion={numeric}',
                    f'/DAppSource={folder}', f'/DRepoRoot={ROOT}', f'/O{ROOT / "dist"}',
                    str(ROOT / 'scripts/installer.iss')], check=True, cwd=ROOT)
    setup = ROOT / 'dist' / f'Lyric-Candle-{VERSION}-Setup-x64.exe'
    digest = hashlib.sha256(setup.read_bytes()).hexdigest()
    setup.with_suffix('.exe.sha256').write_text(f'{digest}  {setup.name}\n', encoding='utf-8')
    print(setup)


if __name__ == '__main__':
    main()
