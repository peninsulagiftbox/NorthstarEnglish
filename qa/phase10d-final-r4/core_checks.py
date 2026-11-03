#!/usr/bin/env python3
"""Keep the failed shared-suite target intact; regression uses a new target."""
import run as q
q.PRIVATE=q.PRIVATE/'core'
q.PRIVATE.mkdir(exist_ok=True)
q.NAME+='-core'
q.OUT=q.OUT/'core'
q.OUT.mkdir(exist_ok=True)
q.create()
q.regressions()
