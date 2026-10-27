"""Local candidate inventory/privacy scan. Findings are not automatic clearance."""
from pathlib import Path,PurePosixPath
import argparse,hashlib,json,re,collections

def main():
 p=argparse.ArgumentParser();p.add_argument('candidate');p.add_argument('--output',required=True);p.add_argument('--private-terms');args=p.parse_args()
 root=Path(args.candidate).resolve();out=Path(args.output).resolve()
 if not root.is_dir() or out.exists() or out.is_relative_to(root):raise SystemExit('Use existing candidate and a new report outside it')
 terms=json.loads(Path(args.private_terms).read_text('utf8')) if args.private_terms else []
 patterns={'personal_machine_path':re.compile(r'(?i)[a-z]:[\\/]+(?:Users[\\/]+[^\\/\s"\']+|xiaos(?:[\\/]|\b))'),'credential_shape':re.compile(r'(?<![A-Za-z0-9_-])sk-[A-Za-z0-9_-]{24,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),'credential_assignment':re.compile(r'(?i)(?:api[_-]?key|access[_-]?token|password)\s*[:=]\s*["\'][A-Za-z0-9_./+=-]{20,}["\']')}
 findings=[];files=[];prohibited=[];bytes_count=0
 for file in sorted(root.rglob('*')):
  if not file.is_file():continue
  rel=file.relative_to(root).as_posix();parts=PurePosixPath(rel).parts
  if file.is_symlink() or any(x in parts for x in ['.git','.codex','.venv','node_modules','private-checks','private-assets','private-audit','__pycache__']) or file.name in {'auth.json','.env','config.toml'} or file.suffix in {'.log','.sqlite','.sqlite3','.pyc','.dmp'}:prohibited.append(rel)
  data=file.read_bytes();bytes_count+=len(data);files.append({'path':rel,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
  text=data.decode('utf8',errors='replace')
  for category,pattern in patterns.items():
   for line_no,line in enumerate(text.splitlines(),1):
    for match in pattern.finditer(line):findings.append({'path':rel,'line':line_no,'category':category,'match_sha256':hashlib.sha256(match.group().encode()).hexdigest(),'match_length':len(match.group()),'review':'REQUIRED','value':'REDACTED'})
  for index,term in enumerate(terms):
   if term and term in text:findings.append({'path':rel,'category':'private_term','term_index':index,'lines':[i+1 for i,line in enumerate(text.splitlines()) if term in line],'review':'REQUIRED','value':'REDACTED'})
 report={'scope':'candidate files only; not parent Git history or live user data','files':len(files),'bytes':bytes_count,'prohibited_paths':prohibited,'findings':findings,'finding_counts':dict(collections.Counter(row['category'] for row in findings)),'inventory':files,'limitations':['No scanner proves absence of secrets.','Binary asset copyright/visual privacy requires provenance/human review.','Potential findings are redacted and require review, not silently removed.'],'publication_ready':False}
 out.parent.mkdir(parents=True,exist_ok=True)
 with out.open('x',encoding='utf8') as f:json.dump(report,f,ensure_ascii=False,indent=2)
 print(json.dumps({k:report[k] for k in ['files','bytes','prohibited_paths','finding_counts','publication_ready']},ensure_ascii=True,indent=2))
if __name__=='__main__':main()
