#!/usr/bin/env python3
"""Read-only minimal reproduction on preserved, UUID-verified QA clone.
Start browser_stack.py first; do not change limit to avoid the failing default page.
"""
import json
import qa_runtime as q
assert q.db("SELECT availability FROM lesson WHERE id='cr-a'")=='withdrawn'
for suffix in ['?limit=1','?limit=20','?limit=100']:
    status,body=q.request('/concept-reviews/f87999e5-8838-4981-b2a2-c616c5d3eb96/sources'+suffix)
    print(json.dumps({'suffix':suffix,'status':status,'response':body if status!=200 else {'items':len(body['items'])}},ensure_ascii=False))
    if status>=500:raise SystemExit(1)
