#!/usr/bin/env python3
"""Phase10B3 isolated builds and append-only command evidence; no personal service operations."""
import sys
from pathlib import Path
import phase10b2 as runner
runner.STATE=runner.ROOT/'.local/phase10b3'
runner.COPY=runner.STATE/'source-final'
runner.OUT=runner.ROOT/'docs/handoff/evidence/phase10b3'
if __name__=='__main__':
    if sys.argv[1:]==['sync']:runner.sync()
    elif len(sys.argv)>=4 and sys.argv[1]=='run':runner.record(sys.argv[2],sys.argv[3:],cwd=runner.COPY)
    else:raise SystemExit('sync | run NAME COMMAND...')
