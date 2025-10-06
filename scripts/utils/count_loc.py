import os
from pathlib import Path

ROOT = Path('.').resolve()
EXCLUDE_NAMES = {
    '.git',
    '__pycache__',
    'venv',
    'htmlcov',
    'backups',
    'backup',
    'remote_backups',
    '.mypy_cache',
    '.pytest_cache',
    '.ruff_cache',
    '.idea',
    '.vscode',
    'node_modules',
    '.next',
    '.cache',
}

CODE_SUFFIXES = {
    '.py', '.pyw', '.pyx', '.pxd', '.pxi', '.pyi',
    '.js', '.mjs', '.cjs', '.ts', '.tsx', '.jsx',
    '.css', '.scss', '.sass', '.less',
    '.html', '.htm', '.jinja', '.j2', '.xml', '.xhtml',
    '.sql', '.psql', '.dbml',
    '.sh', '.bash', '.zsh', '.fish',
    '.yml', '.yaml', '.toml', '.ini', '.cfg',
    '.json', '.jsonc', '.ndjson',
}

CODE_FILENAMES = {
    'Dockerfile', 'Makefile', 'Procfile', 'Justfile', 'thywill', 'install',
}

SKIP_FILE_ENDINGS = ('.min.js', '.min.css', '.lock', '.pyc', '.pyo')

per_ext = {}
per_top = {}
total = 0

for path in ROOT.rglob('*'):
    if not path.is_file():
        continue
    if any(part in EXCLUDE_NAMES for part in path.parts):
        continue
    name_lower = path.name.lower()
    if name_lower.endswith(SKIP_FILE_ENDINGS):
        continue
    suffix = path.suffix.lower()
    include = False
    key = None
    if suffix in CODE_SUFFIXES:
        include = True
        key = suffix or path.name
    elif path.name in CODE_FILENAMES:
        include = True
        key = path.name
    elif path.stat().st_mode & 0o111:
        include = True
        key = path.name
    if not include:
        continue
    try:
        with path.open('r', encoding='utf-8', errors='ignore') as f:
            line_count = sum(1 for _ in f)
    except OSError:
        continue
    total += line_count
    per_ext[key] = per_ext.get(key, 0) + line_count
    try:
        relative = path.relative_to(ROOT)
    except ValueError:
        continue
    top = relative.parts[0] if len(relative.parts) > 1 else relative.parts[0]
    per_top[top] = per_top.get(top, 0) + line_count

print(f"TOTAL_LINES={total}")
print("BY_EXTENSION")
for key, count in sorted(per_ext.items(), key=lambda item: item[1], reverse=True):
    print(f"{key}\t{count}")
print("BY_TOPLEVEL")
for key, count in sorted(per_top.items(), key=lambda item: item[1], reverse=True):
    print(f"{key}\t{count}")
