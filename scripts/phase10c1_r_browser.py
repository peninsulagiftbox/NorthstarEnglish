#!/usr/bin/env python3
"""Pinned CLI driver; retain binary capture privately, never print base64 to the chat."""
import base64
import json
import sys
from pathlib import Path
import phase10c1_reacceptance as acceptance

r = acceptance.r
script = sys.argv[1]
if sys.argv[2:] == ['--active']:
    r.OUT = r.ROOT / (r.STATE / 'R_ACTIVE_OUTPUT').read_text().strip()
assert script in ('phase10c1-r-browser.js', 'phase10c1-r-capture.js', 'phase10c1-r-visibility-result.js', 'phase10c1-r-codec-calibration.js', 'phase10c1-r-mp3-reference.js')
session = json.loads((r.OUT / 'session.json').read_text())
command = ['node', session['cli'], '--session=northstar-phase10c1-r']
r.record('snapshot', command + ['snapshot'], cwd=r.ROOT)
p = r.record(script, command + ['run-code', (r.ROOT / 'scripts' / script).read_text()], cwd=r.ROOT, timeout=150)
raw = p.stdout.decode()
assert '### Error' not in raw, 'Browser action failed; raw log retained'
result = json.loads(raw.split('### Result\n', 1)[1].split('\n###', 1)[0])
for capture in result.get('captures', []):
    for field, suffix in [('encodedBase64', '.webm'), ('pcmBase64', '.f32'), ('rawBase64', '.raw.f32')]:
        if field in capture:
            file = r.OUT / ('capture-' + str(capture['rate']) + suffix)
            file.write_bytes(base64.b64decode(capture.pop(field)))
            capture[field.replace('Base64', 'File')] = file.name
(r.OUT / (script + '.json')).write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({k: v for k, v in result.items() if k not in ('captures', 'events')}, ensure_ascii=False))
