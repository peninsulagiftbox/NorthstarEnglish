#!/usr/bin/env python3
"""Explicit allowlist only; no private databases, audio, recordings, credentials or env."""
import hashlib,json,re,subprocess,sys,tempfile,zipfile
from pathlib import Path
import run as q

def main():
    files={}
    for line in (q.OUT/'qa-final-candidate-manifest.sha256').read_text().splitlines():
        expected,name=line.split('  ',1)
        p=q.ROOT/name
        assert q.sha(p)==expected,name
        # Original production audio is a frozen build input, but excluded from sanitized delivery.
        if name.startswith('.local/') or p.suffix.lower() in ('.mp3','.wav','.ogg','.opus','.m4a','.webm','.png','.jpg','.jpeg','.zip','.jar'):continue
        files['source/'+name]=p
    evidence=[
      'qa-final-candidate-manifest.sha256','candidate-identity.json','migration-inputs.json','p1-336-input-binding.json',
      'commands.jsonl','git-status.log','java-version.log','node-version.log','npm-version.log',
      'node-test.log','node-typecheck.log','node-lint.log','node-build.log','web-identity.json',
      'database-identity.json','container-mounts.log','bootstrap.log','initialize.log','flyway-history.log',
      'java-regression.log','java-regression-correct-origin.log','seed-original-fixture.log',
      '83-source-fixture.json','browser-runtime.json','browser-result.json','browser-tool-result.log',
      'http.jsonl','withdraw-original-qa-course-a.log','failure-flyway-history.log','failure-counts.log',
      'failure-db-key-values.json','private-dump-identity.json','owned-processes-after-stop.log','qa-ports-after-stop.log','retained-qa-container.log',
      'core/commands.jsonl','core/database-identity.json','core/container-mounts.log','core/flyway-history.log',
      'core/initialize.log','core/java-regression-correct-origin.log','core/java-package.log','core/jar-rebuild-comparison.json',
      'candidate-binding-final.json','tool-launch-failures.json','stop-state.json','history-status.md'
    ]
    for name in evidence:
        p=q.OUT/name
        assert p.is_file(),name
        files['evidence/'+name]=p
    for p in (q.OUT/'history').glob('*.md'):
        files['history/'+p.name]=p
    for name in ('10D_D02_QA_R4_FINAL.md','10D_FINAL_ACCEPTANCE.md'):
        files['docs/'+name]=q.ROOT/'docs/qa/phase10d'/name
    files['docs/PHASE_10D_QA_R4.md']=q.ROOT/'docs/progress/PHASE_10D_QA_R4.md'
    for name in ('sources-truncated.png','sources-truncated-trace.zip'):
        files['playwright/'+name]=q.ROOT/'output/playwright/phase10d-final-r4'/name
    write(files,q.ROOT/'output/review/northstar-phase10d-final-qa-sanitized-evidence.zip','bundle-independent-verification')

def write(files,bundle,label):
    forbidden=['.env','credentials.json','learning.json','failure-db-logical-dump.log']
    secrets=[]
    for private in (q.PRIVATE,q.PRIVATE/'core'):
        cred=private/'credentials.json'
        if cred.exists():secrets+=list(json.loads(cred.read_text()).values())
    hashes={}
    with zipfile.ZipFile(bundle,'w',compression=zipfile.ZIP_DEFLATED) as z:
        for name,p in sorted(files.items()):
            assert not any(x in Path(name).parts for x in forbidden),name
            raw=p.read_bytes()
            for secret in secrets:assert secret.encode() not in raw,'secret found in '+name
            if p.suffix=='.zip':
                with zipfile.ZipFile(p) as inner:
                    for inner_name in inner.namelist():
                        data=inner.read(inner_name)
                        for secret in secrets:assert secret.encode() not in data,'secret found in trace'
            z.writestr(name,raw);hashes[name]=hashlib.sha256(raw).hexdigest()
        z.writestr('SHA256SUMS.json',json.dumps(hashes,sort_keys=True,indent=2)+'\n')
        verify='''#!/usr/bin/env python3
import hashlib,json
from pathlib import Path
root=Path(__file__).resolve().parent
files=json.loads((root/'SHA256SUMS.json').read_text())
bad=[name for name,h in files.items() if not (root/name).is_file() or hashlib.sha256((root/name).read_bytes()).hexdigest()!=h]
if bad:raise SystemExit('FAIL '+str(bad))
print('PASS',len(files),'allowlisted files')
'''
        z.writestr('verify.py',verify)
    (Path(str(bundle)+'.sha256')).write_text(q.sha(bundle)+'  '+bundle.name+'\n')
    with tempfile.TemporaryDirectory(prefix='northstar-final-qa-') as d:
        with zipfile.ZipFile(bundle) as z:z.extractall(d)
        q.run(label,[sys.executable,Path(d)/'verify.py'])
    print('EVIDENCE',len(files),'files SHA256',q.sha(bundle),flush=True)

def fix_bundle():
    files={}
    for name in ('commands.jsonl','qa-final-candidate-manifest.sha256','candidate-identity.json','83-source-fixture.json','browser-result.json','http.jsonl','fix-runtime.json','fix-browser-result.json','fix-web-build.log','fix-node-test.log','fix-node-typecheck.log','fix-node-lint.log'):
        p=q.OUT/name;assert p.is_file(),name
        files['evidence/'+name]=p
    for name in ('apps/web/src/components/review/ConceptReviewCard.tsx','apps/web/src/lib/api/conceptReviews.ts','qa/phase10d-final-r4/run.py','qa/phase10d-final-r4/fix_stack.py','qa/phase10d-final-r4/fix_browser_checks.js','qa/phase10d-final-r4/run_fix_browser.cjs','qa/phase10d-final-r4/package_evidence.py'):
        p=q.ROOT/name;assert p.is_file(),name
        files['fix-source/'+name]=p
    for name in ('sources-truncated.png','sources-truncated-trace.zip','sources-fixed.png'):
        p=q.ROOT/'output/playwright/phase10d-final-r4'/name;assert p.is_file(),name
        files['playwright/'+name]=p
    for name in ('10D_D02_QA_R4_FINAL.md','10D_FINAL_ACCEPTANCE.md'):
        files['docs/'+name]=q.ROOT/'docs/qa/phase10d'/name
    files['docs/PHASE_10D_QA_R4.md']=q.ROOT/'docs/progress/PHASE_10D_QA_R4.md'
    write(files,q.ROOT/'output/review/northstar-phase10d-fix-verification-evidence.zip','fix-bundle-independent-verification')

if __name__=='__main__':
    if sys.argv[1:]==['fix']:fix_bundle()
    else:main()
