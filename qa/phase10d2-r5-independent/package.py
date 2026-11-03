"""Allowlist QA evidence and frozen source; verify archive independently after extraction."""
import hashlib,json,subprocess,tempfile,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
TOOLS=Path(__file__).resolve().parent
SOURCE=ROOT/'.local/qa-r5-independent/source'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
source_inputs=json.loads((TOOLS/'evidence/full-source-inputs.json').read_text())
for n,h in source_inputs.items():assert sha(SOURCE/n)==h,n
files={}
for folder in (TOOLS,ROOT/'output/playwright/phase10d2-r5-independent'):
    for p in folder.rglob('*'):
        if p.is_file() and '__pycache__' not in p.parts:files[str(p.relative_to(ROOT))]=p
for n in source_inputs:
    if Path(n).suffix.lower() not in ('.mp3','.wav','.m4a','.webm'):files['source/'+n]=SOURCE/n
for n in ('FinalQaFixture.java','QueuePaginationQaFixture.java'):
    files['source/apps/api/src/test/java/local/northstar/knowledge/'+n]=TOOLS/n
for n in ('docs/qa/phase10d/10D_D02_QA_R5_RETEST.md','docs/qa/phase10d/10D_FINAL_ACCEPTANCE.md','docs/progress/PHASE_10D_2_QA_R5_RETEST.md'):
    files[n]=ROOT/n
creds=json.loads((ROOT/'.local/qa-r5-independent/credentials.json').read_text())
def scan(data,name):
    for v in creds.values():assert v.encode() not in data,'secret in '+name
for n,p in files.items():
    assert p.name not in ('.env','credentials.json') and '.local' not in Path(n).parts,n
    scan(p.read_bytes(),n)
    if p.suffix=='.zip':
        with zipfile.ZipFile(p) as nested:
            for m in nested.namelist():scan(nested.read(m),n+':'+m)
manifest={n:sha(p) for n,p in sorted(files.items())}
verify=b"import hashlib,json\nfrom pathlib import Path\nr=Path(__file__).resolve().parent\nm=json.loads((r/'manifest.json').read_text())\nfor n,h in m.items():assert hashlib.sha256((r/n).read_bytes()).hexdigest()==h,n\nprint('PASS',len(m),'files')\n"
manifest['verify.py']=hashlib.sha256(verify).hexdigest()
target=ROOT/'output/review/northstar-phase10d2-r5-independent-evidence.zip'
target.parent.mkdir(parents=True,exist_ok=True)
with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
    for n,p in sorted(files.items()):z.write(p,n)
    z.writestr('verify.py',verify);z.writestr('manifest.json',json.dumps(manifest,indent=2))
with tempfile.TemporaryDirectory(prefix='northstar-r5-qa-verify-') as d:
    with zipfile.ZipFile(target) as z:z.extractall(d)
    r=subprocess.run(['python3',str(Path(d)/'verify.py')],capture_output=True,text=True)
    assert r.returncode==0,r.stderr
    print(r.stdout.strip())
target.with_suffix('.zip.sha256').write_text(sha(target)+'  '+target.name+'\n')
print(sha(target),target)
