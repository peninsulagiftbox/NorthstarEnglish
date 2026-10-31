#!/usr/bin/env python3
"""Sequential measurements on the one owned foreground browser; preserve every failed command."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
CLI=ROOT/'scripts/phase10c1_c01_cli.py'
parser=argparse.ArgumentParser()
parser.add_argument('action',choices=['references','groups'])
parser.add_argument('--track',default='shared',choices=['shared','independent'])
args=parser.parse_args()
for rate in [.75,1,1.25,1.5]:
    if args.action=='references':
        items=[('c1-shared-v1-a1','reference-shared-'+str(rate))] if args.track=='shared' else [
            ('c1-independent-v1-a'+str(i),'reference-independent-'+str(i)+'-'+str(rate)) for i in [1,2,3]]
        for asset,name in items:
            if (ROOT/'.local/phase10c1/c01-probe/captures'/(name+'.json')).exists():
                continue
            code='async page=>page.evaluate(()=>window.c01.reference('+json.dumps(asset)+','+str(rate)+','+json.dumps(name)+'))'
            subprocess.run([sys.executable,str(CLI),code],check=True)
    else:
        for index,position in enumerate(['first','middle','last']):
            suffix='-fixed'
            name=args.track+'-'+str(rate)+'-'+position+suffix
            spec=dict(rate=rate,track=args.track,index=index,name=name)
            subprocess.run([sys.executable,str(CLI),str(ROOT/'scripts/phase10c1-c01-group.js'),json.dumps(spec)],check=True)
