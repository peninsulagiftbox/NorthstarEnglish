#!/usr/bin/env python3
"""Dedicated build copy and command journal; never builds over the personal runtime."""
import sys
import phase10b2 as runner
runner.STATE=runner.ROOT/'.local/phase10c2'
runner.COPY=runner.STATE/'source'
runner.OUT=runner.ROOT/'docs/handoff/evidence/phase10c2'
if __name__=='__main__':
    if sys.argv[1:]==['sync']:runner.sync()
    elif len(sys.argv)>=4 and sys.argv[1]=='run':runner.record(sys.argv[2],sys.argv[3:],cwd=runner.COPY)
    else:raise SystemExit('sync | run NAME COMMAND...')
