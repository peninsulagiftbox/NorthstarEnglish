#!/usr/bin/env python3
"""Resume only the two verified project children if a backup controller disappears."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import sys
import time

state=Path(sys.argv[1])
config=json.loads(state.read_text())
spec=importlib.util.spec_from_file_location('runtime',Path(__file__).with_name('runtime_media_preflight.py'))
runtime=importlib.util.module_from_spec(spec); spec.loader.exec_module(runtime)
deadline=time.monotonic()+180
while time.monotonic()<deadline:
    if state.with_suffix('.done').exists():
        sys.exit(0)
    time.sleep(.5)
results=[]
for item in config:
    try:
        args,_=runtime.process_config(item['pid'])
        assert hashlib.sha256(json.dumps(args).encode()).hexdigest()==item['argumentsSha256']
        os.kill(item['pid'],signal.SIGCONT)
        results.append({'pid':item['pid'],'resumed':True})
    except Exception as e:
        results.append({'pid':item['pid'],'resumed':False,'errorType':type(e).__name__})
state.with_suffix('.triggered').write_text(json.dumps(results)+'\n')
