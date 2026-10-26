"""Supplemental acceptance command, hash recorded separately from frozen product/test source."""
from pathlib import Path
import json
import subprocess
import sys
sys.path.insert(0, 'scripts')
import phase09r

root = phase09r.STATE
snapshot = json.loads((root/'backup-initial/learning.json').read_text())
base = ['python3', 'scripts/data-transfer.py', 'restore', 'PLACEHOLDER', '--api', 'http://127.0.0.1:8086', '--web-port', '3101', '--target', 'PLACEHOLDER', '--confirm-new-isolated', '--recording-root', str(root/'restore/media'), '--phase09r']
for label, target in [('existing', 'northstar_restore_20261026194500'), ('checksum', 'northstar_restore_20261026194503'), ('missing-media', 'northstar_restore_20261026194504')]:
    folder = root/('verified-negative-'+label)
    folder.mkdir(exist_ok=False)
    data = dict(snapshot)
    if label == 'checksum':
        data['sha256'] = '0'*64
    path = folder/'learning.json'
    path.write_text(json.dumps(data))
    args = list(base)
    args[3], args[9] = str(path), target
    result = subprocess.run(args, capture_output=True, text=True)
    print(json.dumps({'case': label, 'argv': args, 'rawExitCode': result.returncode, 'expectedExitCode': 1, 'output': result.stdout+result.stderr}, ensure_ascii=False))
    assert result.returncode == 1
    if label != 'existing':
        assert phase09r.sql('restore', "SELECT COUNT(*) FROM information_schema.schemata WHERE schema_name='"+target+"'").strip() == '0'
print('PASS: all negative cases rejected before target creation')
