#!/usr/bin/env python3
"""Read-only runtime config, source media hashes and conservative capacity budget."""
import ctypes
import argparse
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import pwd
import re
import shutil
import struct
import sys
import zipfile

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[3]
OUT = BASE / 'readiness-20261027'
PRIVATE = ROOT / '.local/phase10b1-readiness-20261027'
ALLOW = {'MYSQL_PORT','API_PORT','WEB_PORT','DB_NAME','NORTHSTAR_RECORDING_ROOT','NORTHSTAR_CONTENT_ROOT',
         'SPRING_DATASOURCE_URL','SPRING_DATASOURCE_USERNAME','SPRING_FLYWAY_URL','SPRING_FLYWAY_USER'}


def process_config(pid):
    # Constants verified against the installed Apple SDK sys/sysctl.h.
    libc = ctypes.CDLL(None, use_errno=True)
    mib = (ctypes.c_int * 3)(1, 49, pid)
    argmax = ctypes.c_int()
    argmax_size = ctypes.c_size_t(ctypes.sizeof(argmax))
    if libc.sysctlbyname(b'kern.argmax',ctypes.byref(argmax),ctypes.byref(argmax_size),None,0) != 0:
        raise RuntimeError('Cannot determine kernel argument buffer size')
    size = ctypes.c_size_t(argmax.value)
    buf = ctypes.create_string_buffer(size.value)
    if libc.sysctl(mib, 3, buf, ctypes.byref(size), None, 0) != 0:
        raise RuntimeError('Cannot read selected process configuration: errno=' + str(ctypes.get_errno()))
    data = buf.raw[:size.value]
    argc = struct.unpack_from('i', data)[0]
    at = data.index(b'\0', 4) + 1
    while at < len(data) and data[at] == 0:
        at += 1
    args = []
    for _ in range(argc):
        end = data.index(b'\0', at)
        args.append(data[at:end].decode('utf-8'))
        at = end + 1
    env = {}
    unknown = []
    for raw in data[at:].split(b'\0'):
        key, sep, value = raw.partition(b'=')
        key = key.decode('utf-8', errors='replace')
        if sep and key in ALLOW:
            env[key] = value.decode('utf-8')
        if sep and (key.startswith('SPRING_') and key not in ALLOW or key in {'JAVA_TOOL_OPTIONS','_JAVA_OPTIONS','JDK_JAVA_OPTIONS'}):
            unknown.append(key)
    assert not unknown, 'Unresolved runtime override keys: ' + ','.join(unknown)
    assert not any(a.startswith(('@','-Dspring.','--spring.','--spring.config','--spring.profiles')) for a in args), 'Unresolved JVM/Spring argument override'
    return args, env


def inventory(folder):
    folder = folder.absolute()
    assert folder.is_dir(), 'Required source directory does not exist'
    assert not any(p.is_symlink() for p in [folder, *folder.parents]), 'Symlink source directory'
    rows = []
    for p in sorted(folder.rglob('*')):
        assert not p.is_symlink(), 'Symlink media entry'
        if p.is_file():
            before = p.stat()
            digest = hashlib.sha256(p.read_bytes()).hexdigest()
            after = p.stat()
            assert (before.st_size,before.st_mtime_ns) == (after.st_size,after.st_mtime_ns), 'File changed while hashing'
            rows.append(dict(path=str(p.relative_to(folder)),bytes=after.st_size,sha256=digest))
    return rows


def main():
    global OUT, PRIVATE
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--attempt',type=int,default=1)
    options=parser.parse_args()
    assert 1<=options.attempt<=9
    if options.attempt>1:
        OUT=BASE/f'readiness-20261027-attempt{options.attempt}'
        PRIVATE=ROOT/f'.local/phase10b1-readiness-20261027-attempt{options.attempt}'
    OUT.mkdir(mode=0o700, exist_ok=False)
    PRIVATE.mkdir(mode=0o700, parents=True, exist_ok=False)
    spec = importlib.util.spec_from_file_location('a1', BASE / 'a1_readonly.py')
    probe = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(probe)
    probe.OUT = OUT
    try:
        original = json.loads((BASE/'recovery-20261027/a1/identity.json').read_text())
        # Fresh inspection and same-source identity are mandatory before media metadata reads.
        item = json.loads(probe.run([probe.DOCKER,'inspect','--format',
            '{"id":{{json .Id}},"name":{{json .Name}},"labels":{{json .Config.Labels}},"ports":{{json .HostConfig.PortBindings}},"mounts":{{json .Mounts}}}',probe.CONTAINER]))
        assert item['labels']['local.northstar.project'] == probe.PROJECT
        assert item['ports']['3306/tcp'] == [{'HostIp':'127.0.0.1','HostPort':'3308'}]
        assert any(m.get('Name')=='northstar_english_mysql_01_data' and m['Destination']=='/var/lib/mysql' for m in item['mounts'])
        assert probe.identity() == original, 'Source identity changed'
        runtime = []
        java = None
        for role in ['api','web']:
            saved = json.loads((ROOT/'.local'/f'{role}.json').read_text())
            queue = [(saved['pid'],0)]
            while queue:
                pid, depth = queue.pop(0)
                cwd = probe.run(['lsof','-a','-p',str(pid),'-d','cwd','-Fn'])
                assert '\nn'+str(ROOT/'apps'/role)+'\n' in cwd, 'Service process cwd changed'
                args, env = process_config(pid)
                # Persist only approved non-secret fields and argument hashes, never raw environment/argv.
                safe_env = {k:v for k,v in env.items() if k not in {'SPRING_DATASOURCE_URL','SPRING_FLYWAY_URL'}}
                row = dict(role=role,pid=pid,cwd=str(ROOT/'apps'/role),selectedEnvironment=safe_env,
                           argumentsSha256=hashlib.sha256(json.dumps(args).encode()).hexdigest())
                runtime.append(row)
                if role == 'api' and Path(args[0]).name == 'java' and '-jar' in args:
                    assert java is None, 'Multiple API JVMs'
                    java = (pid,args,env)
                if depth < 3:
                    children = probe.run(['pgrep','-P',str(pid)],allowed=(0,1))
                    queue.extend((int(c),depth+1) for c in children.split())
        assert java, 'No project API JVM identified'
        pid,args,env = java
        assert env.get('MYSQL_PORT','3308')=='3308' and env.get('DB_NAME','northstar_english')=='northstar_english'
        assert env.get('API_PORT','8085')=='8085' and env.get('WEB_PORT','3100')=='3100'
        for key in ['SPRING_DATASOURCE_URL','SPRING_FLYWAY_URL']:
            assert key not in env, 'Explicit JDBC override requires separate review'
        jar = Path(args[args.index('-jar')+1])
        assert jar == ROOT/'apps/api/target/northstar-api-0.1.0-SNAPSHOT.jar'
        with zipfile.ZipFile(jar) as z:
            assert z.read('BOOT-INF/classes/application.yml') == (ROOT/'apps/api/src/main/resources/application.yml').read_bytes(), 'Running JAR config differs from source'
        flags = dict(a[2:].split('=',1) for a in args if a.startswith('--') and '=' in a)
        assert all(k in {'northstar.recording-root','northstar.content-root'} for k in flags), 'Unexpected CLI overrides'
        home = Path(pwd.getpwuid(os.getuid()).pw_dir)
        user_home = [a.split('=',1)[1] for a in args if a.startswith('-Duser.home=')]
        assert not user_home, 'user.home overridden'
        media_parent = Path(flags.get('northstar.recording-root',env.get('NORTHSTAR_RECORDING_ROOT',str(home/'Library/Application Support/NorthstarEnglish/recordings'))))
        media_root = media_parent/'northstar_english'
        content_root = Path(flags.get('northstar.content-root',env.get('NORTHSTAR_CONTENT_ROOT',str(ROOT/'content'))))
        sockets = probe.run(['lsof','-nP','-a','-p',str(pid),'-iTCP','-FpnT'])
        assert '127.0.0.1:3308' in sockets and '127.0.0.1:8085' in sockets, 'API listener/database peer not confirmed'
        sessions = probe.sql("SELECT ID,HOST,DB,COMMAND FROM information_schema.PROCESSLIST WHERE USER='northstar_app'")
        probe.write('runtime.json',dict(processes=runtime,apiPid=pid,jarSha256=hashlib.sha256(jar.read_bytes()).hexdigest(),
              applicationYmlMatches=True,sourceDatabase='northstar_english',sourcePort=3308,mediaRoot=str(media_root),
              contentRoot=str(content_root),configurationBasis='Selected live process env + JVM arguments + matching JAR application.yml + controller default resolution',
              jdbcSessionMapping='Configuration and live peer corroborated; NAT does not prove each TCP-to-PROCESSLIST row identity',
              appVisibleSessions=sessions,sourceWrites=False))
        media = inventory(media_root)
        content = inventory(content_root)
        recordings = [json.loads(line) for line in probe.sql("SELECT JSON_OBJECT('id',id,'sha256',sha256,'bytes',byte_size,'status',status) FROM personal_recording ORDER BY id",private=True).splitlines()]
        by_name = {r['path']:r for r in media}
        mismatches = []
        for row in recordings:
            path = row['id']+'.audio'
            actual = by_name.get(path)
            valid = actual is not None and actual['bytes']==row['bytes'] and actual['sha256']==row['sha256']
            if row['status']=='ready' and not valid or row['status']=='missing' and valid:
                mismatches.append(hashlib.sha256(row['id'].encode()).hexdigest())
        private = dict(mediaRoot=str(media_root),contentRoot=str(content_root),media=media,content=content,recordings=recordings)
        private_path = PRIVATE/'source-media-manifest.json'
        private_path.write_text(json.dumps(private,ensure_ascii=False,indent=2)+'\n')
        private_path.chmod(0o600)
        totals = dict(mediaFiles=len(media),mediaBytes=sum(r['bytes'] for r in media),contentFiles=len(content),contentBytes=sum(r['bytes'] for r in content),
            recordingStatuses={state:sum(r['status']==state for r in recordings) for state in ['ready','missing','pending','deleted']},
            unexplainedMismatches=len(mismatches),privateManifest=str(private_path.relative_to(ROOT)),manifestSha256=hashlib.sha256(private_path.read_bytes()).hexdigest(),
            consistentSnapshot=False,mediaHashCheck='PASS' if not mismatches else 'BLOCKED')
        probe.write('media-summary.json',totals)
        assert not mismatches, 'Unexplained DB/media mismatch; no reconcile performed'
        allocated = int(probe.sql('SELECT COALESCE(SUM(DATA_LENGTH+INDEX_LENGTH),0) FROM information_schema.TABLES WHERE TABLE_SCHEMA=DATABASE()'))
        sql_allowance = max(64*1024**2,allocated*32)
        file_bytes = totals['mediaBytes']+totals['contentBytes']
        # Conservative reservation for eight preserved MySQL target volumes, dump/media and temp copies.
        base = 8*4*1024**3 + 10*(sql_allowance+file_bytes) + 4*1024**3
        required = (base*120+99)//100
        free = shutil.disk_usage(ROOT).free
        probe.write('capacity.json',dict(databaseAllocatedBytes=allocated,sqlConservativeReservationBytes=sql_allowance,
             measuredMediaContentBytes=file_bytes,isolatedVolumes=8,perVolumeReservationBytes=4*1024**3,
             requiredWith20PercentBytes=required,diskFreeBytes=free,passesConservativeBudget=free>=required,
             exactDumpBytes='NOT VERIFIED until approved static backup',note='Reservation, not measured final dump/volume size; recheck in maintenance window'))
        assert free>=required, 'Insufficient conservative backup/replica capacity'
        probe.write('result.json',dict(status='PARTIAL',runtimeConfigAndPeer='PASS',mediaHashes='PASS',capacityReservation='PASS',
             browserBuffers='AWAITING USER CONFIRMATION',maintenanceApproved=False,sourceWrites=False,B01='BLOCKED',B03='BLOCKED'))
        return 0
    except Exception as e:
        probe.write('result.json',dict(status='BLOCKED',reason=type(e).__name__+': '+str(e),sourceWrites=False,B01='BLOCKED',B03='BLOCKED'))
        return 2
    finally:
        probe.write('commands.json',probe.RECORDS)


if __name__=='__main__':
    sys.exit(main())
