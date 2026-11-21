"""Create a reviewable source archive, excluding local secrets, caches and .git."""

import hashlib
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = {'.git', '__pycache__', '.venv', 'projects', 'node_modules'}


def package(output):
    output = Path(output).resolve()
    if output.is_relative_to(ROOT):
        raise ValueError('Put the package outside the repository')
    output.parent.mkdir(parents=True, exist_ok=True)
    manifest = []
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED) as z:
        for path in sorted(ROOT.rglob('*')):
            rel = path.relative_to(ROOT)
            if not path.is_file() or any(p in EXCLUDED for p in rel.parts):
                continue
            if path.name.endswith(('.pyc', '.lock')) or (path.name.startswith('.env') and path.name != '.env.example'):
                continue
            data = path.read_bytes()
            name = 'product-strategist/' + rel.as_posix()
            z.writestr(name, data)
            manifest.append({'path': name, 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)})
        z.writestr('product-strategist/ARCHIVE-MANIFEST.json', json.dumps(manifest, ensure_ascii=False, indent=2))
    return {'archive': str(output), 'file_count': len(manifest), 'bytes': output.stat().st_size,
            'sha256': hashlib.sha256(output.read_bytes()).hexdigest()}


if __name__ == '__main__':
    print(json.dumps(package(sys.argv[1]), ensure_ascii=False, indent=2))
