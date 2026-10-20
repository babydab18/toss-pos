"""Export only Git-eligible application files, never the surrounding project."""
from pathlib import Path
import subprocess
from zipfile import ZipFile, ZIP_DEFLATED

root = Path(__file__).resolve().parents[1]
output = root / '.tools' / 'toss-pos-source.zip'
names = subprocess.check_output(
    ['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z', '--', '.'],
    cwd=root,
).decode('utf-8').split('\0')
files = sorted(set(name for name in names if name))
for name in files:
    path = root / name
    if not path.resolve().is_relative_to(root) or not path.is_file():
        raise RuntimeError(f'Cannot safely export {name}')
    if any(part in {'.git', '.tools', '.venv', 'node_modules', 'uploads', 'dist'} for part in path.relative_to(root).parts):
        raise RuntimeError(f'Runtime or dependency files are tracked: {name}')
    if ((path.name == '.env' or path.name.startswith('.env.')) and path.name not in {'.env.example', '.env.sms.example'}) or path.suffix in {'.db', '.sqlite', '.sqlite3', '.pem', '.key'}:
        raise RuntimeError(f'Private data or credentials are tracked: {name}')
output.parent.mkdir(exist_ok=True)
with ZipFile(output, 'w', ZIP_DEFLATED) as archive:
    for name in files:
        archive.write(root / name, name)
print(f'Exported {len(files)} files to {output} ({output.stat().st_size:,} bytes)')
