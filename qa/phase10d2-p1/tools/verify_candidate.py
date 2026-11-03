#!/usr/bin/env python3
import argparse,hashlib,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[3]);a=p.parse_args()
e=a.root/'qa/phase10d2-p1/evidence';m=e/'candidate-inputs.json'
assert hashlib.sha256(m.read_bytes()).hexdigest()==(e/'candidate-inputs.sha256').read_text().split()[0]
rows=json.loads(m.read_text())
for name,expected in rows.items():assert hashlib.sha256((a.root/name).read_bytes()).hexdigest()==expected,'DRIFT '+name
print('PASS',len(rows),'candidate inputs')
