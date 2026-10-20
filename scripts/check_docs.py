"""Check repository-local Markdown links and screenshots without network access."""
from pathlib import Path
import re
import sys
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
LINK = re.compile(r'!?\[[^\]]*\]\(([^)\s]+)(?:\s+[^)]*)?\)')


def main():
    missing = []
    count = 0
    documents = list(ROOT.glob('*.md')) + list((ROOT / 'docs').rglob('*.md'))
    for document in documents:
        for match in LINK.finditer(document.read_text(encoding='utf-8')):
            target = match.group(1).strip('<>')
            if re.match(r'^[A-Za-z][A-Za-z0-9+.-]*:', target) or target.startswith('#'):
                continue
            local = unquote(target.split('#', 1)[0])
            if local:
                count += 1
                if not (document.parent / local).is_file():
                    missing.append(f'{document.relative_to(ROOT)}: {target}')
    if missing:
        print('\n'.join(missing), file=sys.stderr)
        return 1
    print(f'Checked {count} local documentation links; no missing files.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
