#!/usr/bin/env python3
"""Isolated 10C1 builds and command journal. Never operates personal services."""
import sys
import phase10b2 as runner
runner.STATE=runner.ROOT/'.local/phase10c1'
runner.COPY=runner.STATE/'source'
runner.OUT=runner.ROOT/'docs/handoff/evidence/phase10c1'
if __name__=='__main__':
    if sys.argv[1:]==['sync']:runner.sync()
    elif len(sys.argv)>=4 and sys.argv[1]=='run':runner.record(sys.argv[2],sys.argv[3:],cwd=runner.COPY)
    else:raise SystemExit('sync | run NAME COMMAND...')
