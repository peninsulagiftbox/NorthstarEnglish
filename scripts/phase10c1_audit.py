#!/usr/bin/env python3
"""Closeout audit only: hashes, retained evidence and owned stopped resources. No DB writes."""
import hashlib,json,subprocess
from pathlib import Path
import phase10c1_isolated as iso
r=iso.r;c=iso.campaign()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
initial=json.loads((r.OUT/'preflight-local.json').read_text());final=json.loads((r.OUT/'personal-final-readonly.json').read_text())
assert final['jarSha256']==initial['jarSha256'] and final['webBuildId']==initial['webBuildId']
assert final['tableCount']=='43' and all(x['migrationVersion']=='009.15' and x['status']=='UP' for x in final['health'].values())
assert final['migrationFilesMatchJar'] and not final['personalJarContainsV010'] and final['backup']['matches'] and final['media']['allMatch']
assert final['history']==initial['history']
frozen=json.loads((r.OUT/'frozen-migrations.json').read_text())
assert all(sha(r.ROOT/x['path'])==x['sha256'] for x in frozen)
legacy=[x for x in frozen if not Path(x['path']).name.startswith('V010')]
for item in legacy:
 old=subprocess.check_output(['git','show','HEAD:'+item['path']],cwd=r.ROOT);assert hashlib.sha256(old).hexdigest()==item['sha256']
inputs=[]
for name in ['apps/api/src','apps/web/src']:
 for p in (r.ROOT/name).rglob('*'):
  if p.is_file():inputs.append(p)
inputs += [r.ROOT/x for x in ['apps/api/pom.xml','apps/web/package.json','apps/web/next.config.ts','package.json','package-lock.json']]
assert all((r.COPY/p.relative_to(r.ROOT)).is_file() and sha(p)==sha(r.COPY/p.relative_to(r.ROOT)) for p in inputs)
commands=[json.loads(line) for line in (r.OUT/'execution-commands.jsonl').read_text().splitlines()]
for row in commands:assert sha(r.ROOT/row['log'])==row['sha256']
raw_count=0
for journal in (r.OUT/'migrations').rglob('commands.jsonl'):
 for line in journal.read_text().splitlines():
  row=json.loads(line)
  if 'rawLog' in row:assert sha(r.ROOT/row['rawLog'])==row['rawLogSha256'];raw_count+=1
containers=[]
for role in c.ROLES:
 d=c.verify(role)
 state=c.call('final-owned-status-'+role,[c.DOCKER,'inspect','--format','{{.State.Status}}',d['containerId']]).stdout.decode().strip();assert state=='exited'
 c.call('final-retained-volume-'+role,[c.DOCKER,'volume','inspect',d['volume']]);containers.append(dict(role=role,status=state,volumeRetained=True))
ports=[8155,8161,8162,3175,8098]
assert all(subprocess.run(['lsof','-nP','-iTCP:'+str(port),'-sTCP:LISTEN'],capture_output=True).returncode==1 for port in ports)
result=dict(status='PASS',sourcePersonalUP00915=True,personalJarAndWebUnchanged=True,personalHistoryExact=True,personalMediaAndOldBackupExact=True,sourceWritesPerformed=False,legacyMigrationFilesUnchanged=len(legacy),allMigrationFilesFrozen=len(frozen),buildInputFilesExact=len(inputs),commandLogsVerified=len(commands),rawDatabaseLogsVerified=raw_count,ownedContainers=containers,isolatedApiWebPortsClosed=ports,candidateJarSha256=sha(c.PATCHED_JAR),candidateWebBuildId=(r.COPY/'apps/web/.next/BUILD_ID').read_text().strip(),gitHead=final['gitHead'])
(r.OUT/'delivery-audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='ownedContainers'}))
