#!/usr/bin/env python3
"""Replay the established campaign on new owned containers/volumes; never adopt old roles."""
import hashlib, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[5]
sys.path.insert(0,str(ROOT/'scripts'))
import phase10d_isolated as p
p.r.STATE=ROOT/'.local/d02-risk-closure'
p.r.OUT=ROOT/'qa/phase10d/evidence/d02-risk-closure/migrations'
original=p.campaign
def campaign():
    c=original()
    c.NAMESPACE='northstar-d02-risk-20261102'
    c.ROLES=['reserved'+str(i) for i in range(50)]+['upgrade','empty','fault-ddl','fault-dml','fault-history','fault-04','fault-05','fault-06','fault-07','recovery']
    c.PATCHED_JAR=ROOT/'apps/api/target/northstar-api-0.1.0-SNAPSHOT.jar'
    assert hashlib.sha256(c.PATCHED_JAR.read_bytes()).hexdigest()=='cc4f31aecb24fe6c49e1afe779b854861b9d513711880cfe9fed61d4d4eccafb'
    return c
p.campaign=campaign
if __name__=='__main__':p.main()
