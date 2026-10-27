"""Export only the reviewed source allowlist. Does not initialize or modify Git."""
from pathlib import Path, PurePosixPath
import argparse, hashlib, json, zipfile

def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True, help='New ZIP path under release/')
    parser.add_argument('--manifest', default='docs/oss/PUBLIC-ALLOWLIST.json', help='Reviewed manifest under docs/oss; hashes must match')
    args = parser.parse_args()
    output = Path(args.output).resolve()
    if not output.is_relative_to((root / 'release').resolve()) or output.suffix != '.zip' or output.exists():
        raise SystemExit('Output must be a new ZIP under release; existing files are preserved.')
    manifest_path = (root / args.manifest).resolve()
    if not manifest_path.is_relative_to((root / 'docs/oss').resolve()) or manifest_path.is_symlink():
        raise SystemExit('Manifest must be an explicitly reviewed file under docs/oss.')
    manifest = json.loads(manifest_path.read_text(encoding='utf8'))
    if manifest.get('history_included') is not False:
        raise SystemExit('Invalid source review manifest')
    entries = []
    seen = set()
    for row in manifest['files']:
        name = row['path']; relative = PurePosixPath(name)
        if relative.is_absolute() or '..' in relative.parts or '\\' in name or ':' in name or name in seen:
            raise SystemExit('Unsafe or duplicate allowlist path')
        seen.add(name)
        source_name = row.get('source_path', name)
        source_relative = PurePosixPath(source_name)
        allowed_override = source_name == 'desktop/data-location.public.json' and name == 'desktop/data-location.json'
        allowed_override = allowed_override or (source_name.startswith('docs/oss/public-overrides/') and name.startswith('web/backend/tests/'))
        allowed_override = allowed_override or (source_name == 'docs/oss/public-overrides/check-global-replace.mjs' and name == 'web/frontend/scripts/check-global-replace.mjs')
        if source_name != name and not allowed_override:
            raise SystemExit('Unapproved public-only override: ' + name)
        if source_relative.is_absolute() or '..' in source_relative.parts or '\\' in source_name or ':' in source_name:
            raise SystemExit('Unsafe allowlist source path')
        path = root / source_name
        if not path.is_file() or path.is_symlink() or not path.resolve().is_relative_to(root):
            raise SystemExit('Missing or unsafe allowlisted file: ' + name)
        if any(parent.is_symlink() for parent in path.parents if parent.is_relative_to(root)):
            raise SystemExit('Symlink parent in allowlist: ' + name)
        content = path.read_bytes()
        if hashlib.sha256(content).hexdigest() != row['sha256']:
            raise SystemExit('Review hash changed: ' + name)
        entries.append((name, content))
    # The manifest itself is deliberately not included in its own hash list.
    entries.append((manifest_path.relative_to(root).as_posix(), manifest_path.read_bytes()))
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, 'x', zipfile.ZIP_DEFLATED) as archive:
        for name, content in entries:
            archive.writestr('novel-studio-source/' + name, content)
    with zipfile.ZipFile(output) as archive:
        if archive.testzip() is not None:
            raise SystemExit('ZIP CRC validation failed')
    print('Local review candidate; Apache-2.0 confirmed. Publication is not authorized.')
    print(output)
    print('Files:', len(entries))
    print('SHA256:', hashlib.sha256(output.read_bytes()).hexdigest())

if __name__ == '__main__':
    main()
