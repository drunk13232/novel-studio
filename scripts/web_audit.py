"""Read-only acceptance integrity and file inventory; writes project evidence only."""
import csv
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/web-validation'
OUT.mkdir(exist_ok=True)


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest().lower()


def git(*args, cwd=ROOT):
    # Per-command trust for our explicitly selected checkout; never global config.
    return subprocess.check_output(['git', '-c', f'safe.directory={cwd.as_posix()}', *args], cwd=cwd, text=True, encoding='utf-8')


checks = []
for source in json.loads((ROOT / 'docs/installation/source-lock.json').read_text(encoding='utf-8-sig'))['sources']:
    folder = Path(source['path'])
    mismatch = [r['path'] for r in source['files'] if not (folder / r['path']).is_file() or sha(folder / r['path']) != r['sha256'].lower()]
    checks.append({'source': source['name'], 'checked': len(source['files']), 'mismatches': mismatch,
                   'git_clean': not git('status', '--porcelain', cwd=folder).strip(),
                   'head_matches': git('rev-parse', 'HEAD', cwd=folder).strip() == source['commit']})

external = json.loads((ROOT / 'docs/installation/external-installation-paths.json').read_text(encoding='utf-8-sig'))
extchecks = []
for group in external['authorizedPaths']:
    files = [r for r in group.get('files', []) if '.git' not in Path(r['path']).relative_to(Path(group['path'])).parts]
    metadata = [r for r in group.get('files', []) if '.git' in Path(r['path']).relative_to(Path(group['path'])).parts]
    mismatches = [r['path'] for r in files if not Path(r['path']).is_file() or sha(Path(r['path'])) != r['sha256'].lower()]
    metadata_changes = [r['path'] for r in metadata if not Path(r['path']).is_file() or sha(Path(r['path'])) != r['sha256'].lower()]
    extchecks.append({'path': group['path'], 'checked': len(files), 'mismatches': mismatches,
                      'git_metadata_changes_against_installation_snapshot': metadata_changes})

baseline = json.loads((OUT / 'protected-baseline.json').read_text(encoding='utf-8'))
changes = [p for p, h in baseline.items() if not (ROOT / p).is_file() or sha(ROOT / p) != h]
config_unchanged = sha(Path(external['config']['path'])) == external['config']['sha256After'].lower()
sys.path.insert(0, str(ROOT / 'scripts'))
import novel_workflow as w
import model

state_empty = w.load_state(ROOT) == model.STATES
chapters_empty = not [p for p in (ROOT / 'chapters').iterdir() if p.name != '.gitkeep']
proposed_empty = not list((ROOT / 'state/proposed').glob('*.yaml'))
upstream_preserved = (ROOT / '.novelforge/AGENTS.md').read_text(encoding='utf-8-sig').strip() in (ROOT / 'AGENTS.md').read_text(encoding='utf-8-sig')

# Compare against the actual last-stage final hashes, not unborn Git HEAD.
old = {r['path']: r['sha256'] for r in json.loads((ROOT / 'docs/validation-v0.1/baseline.json').read_text(encoding='utf-8-sig'))}
with (ROOT / 'docs/validation-v0.1/changes-manifest.tsv').open(encoding='utf-8-sig', newline='') as stream:
    old.update({r['path']: r['sha256'] for r in csv.DictReader(stream, delimiter='\t')})
modified = [p for p, h in old.items() if (ROOT / p).is_file() and sha(ROOT / p) != h.lower()]
assert set(modified) == {'.gitignore', 'AGENTS.md', 'README.md'}, modified

inventory = git('ls-files', '--others', '--exclude-standard', cwd=ROOT.parent).splitlines()
relative = [p.removeprefix('novel-workspace/') for p in inventory if p.startswith('novel-workspace/')]
added = sorted(p for p in relative if p.startswith(('web/', 'docs/web-validation/')) or p in {
    'start-web.ps1', 'stop-web.ps1', 'install-web.ps1', 'scripts/web_audit.py', 'docs/web-console-v0.1.md'})
secret_findings = []
for name in added:
    path = ROOT / name
    if path.suffix not in {'.md', '.json', '.txt', '.ts', '.tsx', '.ps1'} or not path.is_file(): continue
    content = path.read_text(encoding='utf-8-sig')
    if re.search(r'\bsk-[A-Za-z0-9_-]{20,}\b|Bearer\s+[A-Za-z0-9._-]{20,}|eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]+\.', content):
        secret_findings.append(name)

report = {'result': 'PASS', 'third_party_sources': checks, 'native_plugin_paths': extchecks,
          'protected_changes': changes, 'formal_state_empty': state_empty, 'formal_chapters_empty': chapters_empty,
          'proposed_empty': proposed_empty, 'temporary_file_removed': not (ROOT / 'docs/web-console-codex-test.md').exists(),
          'user_config_unchanged': config_unchanged, 'upstream_agents_preserved': upstream_preserved,
          'secret_findings': secret_findings}
assert all(not c['mismatches'] for c in checks + extchecks)
assert all(c['git_clean'] and c['head_matches'] for c in checks)
assert not changes and config_unchanged and upstream_preserved and state_empty and chapters_empty and proposed_empty and not secret_findings
assert report['temporary_file_removed']
(OUT / 'integrity.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
(OUT / 'git-status.txt').write_text(git('status', '--short', '--branch', cwd=ROOT.parent), encoding='utf-8')
(OUT / 'git-diff-stat.txt').write_text(git('diff', '--stat', cwd=ROOT.parent), encoding='utf-8')
(OUT / 'git-untracked-files.txt').write_text(git('ls-files', '--others', '--exclude-standard', cwd=ROOT.parent), encoding='utf-8')
generated = ['docs/web-validation/integrity.json', 'docs/web-validation/git-status.txt',
             'docs/web-validation/git-diff-stat.txt', 'docs/web-validation/git-untracked-files.txt',
             'docs/web-validation/changed-files.md']
added = sorted(set(added) | set(generated))
(OUT / 'changed-files.md').write_text('# Web V0.1 本轮全部新增/修改\n\n依赖、构建产物、runtime 均忽略。修改项依据上一阶段最终 SHA-256；Git 尚无提交。\n\n' +
    '\n'.join('- ADDED: `' + p + '`' for p in added) + '\n\n' + '\n'.join('- MODIFIED: `' + p + '`' for p in sorted(modified)) + '\n', encoding='utf-8')
print(json.dumps({'result':'PASS', 'source_files':sum(c['checked'] for c in checks),
                  'native_plugin_files':sum(c['checked'] for c in extchecks), 'protected_files':len(baseline),
                  'added':len(added), 'modified':modified, 'secret_findings':secret_findings}, ensure_ascii=False))
