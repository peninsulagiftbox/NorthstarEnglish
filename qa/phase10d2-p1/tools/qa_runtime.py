"""Owned QA runtime; credentials stay in .local and are never printed."""
import hashlib,json,os,subprocess,time,urllib.request,urllib.error,socket
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'qa/phase10d2-p1/evidence'
DB_PRIVATE=ROOT/'.local/d02-risk-closure'
PRIVATE=ROOT/'.local/d02-p1'
QA=Path('/Users/wangshiqi/.codex/worktrees/worktree-10d-d02-qa/NorthstarEnglish')
SCHEMA='northstar_phase01_test'
API='http://127.0.0.1:8186/api/v1'
WEB='http://127.0.0.1:3197'

def state():return json.loads((DB_PRIVATE/'database/empty/state.json').read_text())
def credentials():return json.loads((DB_PRIVATE/'database/empty/credentials.json').read_text())
def sql(q):
    s=state();assert s['namespace']=='northstar-d02-risk-20261102' and s['port']==3364
    env=dict(os.environ,MYSQL_PWD=credentials()['root'])
    cmd=['/usr/local/mysql/bin/mysql','--protocol=TCP','-h127.0.0.1','-P3364','-uroot','-N','--batch','--raw']
    r=subprocess.run(cmd,input='SELECT @@server_uuid;'+q,capture_output=True,text=True,env=env)
    assert r.returncode==0,r.stderr
    ident,_,out=r.stdout.partition('\n');assert ident==s['uuid']
    return out.strip()
def db(q):return sql('USE '+SCHEMA+';'+q)
def request(path,body=None):
    req=urllib.request.Request(API+path,data=json.dumps(body).encode() if body else None,headers={'Content-Type':'application/json','Origin':WEB,'X-Northstar-Request':'local-workspace'})
    try:
        with urllib.request.urlopen(req,timeout=60) as r:return r.status,json.load(r)
    except urllib.error.HTTPError as e:return e.code,json.load(e)
def start_api():
    for port in (8186,3197):
        with socket.socket() as s:
            s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
            s.bind(('127.0.0.1',port))
    jar=PRIVATE/'candidate.jar'
    assert hashlib.sha256(jar.read_bytes()).hexdigest()==(PRIVATE/'candidate.sha256').read_text().strip()
    c=credentials();env=dict(os.environ,DB_NAME=SCHEMA,MYSQL_PORT='3364',DB_PASSWORD=c['app'],DB_MIGRATION_PASSWORD=c['migrator'],NORTHSTAR_DB_TEST='1',NORTHSTAR_EXPECTED_DB_UUID=state()['uuid'],NORTHSTAR_CONTENT_ROOT=str(QA/'.local/qa-r3/content'),NORTHSTAR_RECORDING_ROOT=str(PRIVATE/'browser-recordings'),API_PORT='8186',WEB_PORT='3197')
    (PRIVATE/'browser-recordings').mkdir(exist_ok=True)
    log=(PRIVATE/'runtime-api.log').open('ab')
    p=subprocess.Popen([str(ROOT/'.local/jdk21/jdk-21.0.12.1+1/Contents/Home/bin/java'),'-jar',str(jar)],env=env,stdout=log,stderr=subprocess.STDOUT)
    for _ in range(90):
        assert p.poll() is None,'API exited; see private runtime-api.log'
        try:
            if request('/health')[1]['migrationVersion']=='012.11':return p
        except OSError:pass
        time.sleep(.5)
    p.terminate();raise RuntimeError('API readiness timeout')
def stop(p):
    p.terminate()
    try:p.wait(timeout=15)
    except subprocess.TimeoutExpired:p.kill();p.wait()
