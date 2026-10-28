#!/usr/bin/env python3
"""Final offline evidence checks plus read-only owned-container/runtime inspection. No SQL or process control."""
import ast
import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess
import urllib.request

ROOT=Path(__file__).resolve().parents[4]
OUT=Path(__file__).resolve().parent

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def command(argv):
    p=subprocess.run(argv,cwd=ROOT,capture_output=True,text=True,timeout=30)
    return dict(argv=argv,exitCode=p.returncode,stdout=p.stdout,stderr=p.stderr)

def main():
    head=command(['git','rev-parse','HEAD']);assert head['exitCode']==0
    commit=head['stdout'].strip();records=[head]
    status=command(['git','status','--short','--untracked-files=all']);records.append(status);assert status['exitCode']==0
    (OUT/'delivery-worktree-status.txt').write_text(status['stdout'])
    check=command(['git','diff','--check']);records.append(check);assert check['exitCode']==0
    before=read(OUT/'before-development-hashes.json')
    assert sha(ROOT/'apps/api/src/main/java/local/northstar/exportimport/ExportController.java')==before['apps/api/src/main/java/local/northstar/exportimport/ExportController.java']
    for p,h in before.items():
        if p.startswith(('content/','infra/')) or p in ['package.json','package-lock.json','apps/api/pom.xml','apps/web/package.json']:
            assert sha(ROOT/p)==h,'Unrelated baseline changed: '+p
    historical=[]
    for p in sorted((ROOT/'apps/api/src/main/resources/db/migration').glob('V00[1-8]*.sql')):
        actual=subprocess.check_output(['git','show','HEAD:'+str(p.relative_to(ROOT))],cwd=ROOT)
        assert p.read_bytes()==actual;historical.append(str(p.relative_to(ROOT)))
    for item in read(ROOT/'docs/handoff/evidence/phase10b1/candidate/candidate-manifest.json')['files']:
        assert sha(ROOT/item['path'])==item['sha256']
        assert sha(ROOT/'apps/api/src/main/resources/db/migration'/Path(item['path']).name)==item['sha256']
    assert sha(ROOT/'apps/api/src/main/resources/db/migration/V009_05__lesson_catalog_order.sql')==read(OUT/'migration-execution-20261028b/result.json')['migrationSha256']
    raw_count=0
    journals=[OUT/'execution-commands.jsonl',*OUT.glob('migration-execution*/commands.jsonl')]
    for journal in journals:
        for line in journal.read_text().splitlines():
            row=json.loads(line)
            if row.get('rawLog'):
                assert sha(ROOT/row['rawLog'])==row['rawLogSha256'];raw_count+=1
            elif row.get('log') and row.get('sha256'):
                assert sha(ROOT/row['log'])==row['sha256'];raw_count+=1
    # Actual state is freshly inspected, never inferred from a successful stop command.
    targets=[];docker='/Applications/Docker.app/Contents/Resources/bin/docker'
    for path in sorted((ROOT/'.local/phase10b2').glob('database*/*/state.json')):
        data=read(path);assert data['uuid']!='104d5d9d-cd3f-11f1-8da4-920f115cf5cb' and data['port']!=3308
        result=command([docker,'inspect','--format','{"id":{{json .Id}},"labels":{{json .Config.Labels}},"ports":{{json .HostConfig.PortBindings}},"mounts":{{json .Mounts}},"status":{{json .State.Status}}}',data['containerId']]);records.append(result)
        assert result['exitCode']==0;actual=json.loads(result['stdout'])
        assert actual['id']==data['containerId'] and actual['labels']['local.northstar.rehearsal']==data['namespace']
        assert actual['ports']['3306/tcp']==[{'HostIp':'127.0.0.1','HostPort':str(data['port'])}]
        assert any(m.get('Name')==data['volume'] and m['Destination']=='/var/lib/mysql' for m in actual['mounts'])
        assert actual['status']=='exited';targets.append(dict(container=data['container'],uuid=data['uuid'],status='exited',volumeRetained=True))
    for port in ['8131','3151']:
        result=command(['lsof','-nP','-iTCP:'+port,'-sTCP:LISTEN']);records.append(result)
        assert result['exitCode']==1 and not result['stdout'],'Owned acceptance listener still running'
    with urllib.request.urlopen('http://127.0.0.1:8085/api/v1/health',timeout=8) as response:health=json.load(response)
    assert health['status']=='UP' and health['project']=='northstar-english-local-v1' and health['migrationVersion']=='009.04'
    source_jar=ROOT/'apps/api/target/northstar-api-0.1.0-SNAPSHOT.jar'
    assert sha(source_jar)=='b6d4dcc1f3b8e84bdcb25c993f55448b286dabe5271084dd84bcea61a3382241'
    # Scan only deliverable text, never export the actual secret values.
    secrets=[]
    for line in (ROOT/'.env').read_text().splitlines():
        key,sep,value=line.partition('=')
        if sep and 'PASSWORD' in key and len(value)>16:secrets.append(value)
    for p in (ROOT/'.local/phase10b2').glob('database*/*/credentials.json'):secrets.extend(read(p).values())
    for path in OUT.rglob('*'):
        if path.is_file():
            text=path.read_text(errors='replace')
            assert not any(value in text for value in secrets),'Credential in deliverable: '+str(path.relative_to(ROOT))
    for path in (ROOT/'scripts').glob('phase10b2*.py'):ast.parse(path.read_text())
    for path in OUT.glob('*.py'):ast.parse(path.read_text())
    for path in [ROOT/'docs/progress/PHASE_10B_2.md',OUT/'PLAN.md',OUT/'EXECUTION_SCOPE.md']:
        text=path.read_text();assert text.endswith('\n') and all(x==x.rstrip() for x in text.splitlines())
        for link in re.findall(r'\]\(([^)]+)\)',text):
            if '://' not in link:assert (path.parent/link.split('#')[0]).exists(),link
    changed=[p for p,h in before.items() if (ROOT/p).exists() and sha(ROOT/p)!=h]
    added=[str(p.relative_to(ROOT)) for folder in ['apps/api/src/main/java/local/northstar/catalog','apps/api/src/test/java/local/northstar/catalog','apps/web/tests','scripts'] for p in (ROOT/folder).iterdir() if p.is_file() and str(p.relative_to(ROOT)) not in before and (p.name.startswith('phase10b2') or p.name in ['AudioResources.java','CatalogReader.java','DemoContentAdapter.java','MultiCourseIntegrationTest.java','catalog.test.ts'])]
    stage=sorted(set(changed+added+['README.md','docs/openapi.yaml','docs/progress/PHASE_10B_2.md','apps/api/src/main/resources/db/migration/V009_05__lesson_catalog_order.sql']))
    (OUT/'stage-files.json').write_text(json.dumps([dict(path=p,sha256=sha(ROOT/p)) for p in stage],indent=2)+'\n')
    (OUT/'delivery-audit-commands.json').write_text(json.dumps(records,indent=2)+'\n')
    result=dict(at=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='PASS',gitSha=commit,rawLogsVerified=raw_count,allOwnedTargetsStopped=targets,acceptancePortsClosed=True,sourceHealthReadOnly=health,sourceJarUnchanged=True,sourceDatabaseCommands=0,historicalMigrationsFrozen=len(historical)+4,originalContentAndAppDependenciesUnchanged=True,credentialScan='PASS',toolingAndDocumentChecks='PASS',applicationTests='See recorded Node27/Python15/Java22 and browser results; not inferred by this audit',ordinaryStartupDataProtection=read(OUT/'final-data-protection.json'),nonwebBootstrap=read(OUT/'nonweb-bootstrap.json'))
    (OUT/'delivery-audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(status='PASS',rawLogsVerified=raw_count,ownedTargetsStopped=len(targets),sourceVersion=health['migrationVersion']),ensure_ascii=False))

if __name__=='__main__':main()
