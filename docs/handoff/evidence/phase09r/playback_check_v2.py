import json
import re
import sys
sys.path.insert(0,'scripts')
import local
import phase09r

env=phase09r.verify('source')
record=json.loads((phase09r.STATE/'source/phase09r-api.json').read_text())
assert local.owns_process(record)
cli=['node',env['NORTHSTAR_PLAYWRIGHT_CLI_JS'],'--session=northstar-phase09r-rejection']
phase09r.recorded('playback-v2-browser-open',cli+['open',env['NORTHSTAR_BASE_URL']+'/dashboard','--config=output/playwright/phase09.config.json'],env)
try:
    phase09r.recorded('playback-v2-browser-snapshot',cli+['snapshot'],env)
    phase09r.recorded('playback-v2-browser-trace-start',cli+['tracing-start'],env)
    code=(phase09r.EVIDENCE/'playback_rejection_v2.js').read_text()
    output=phase09r.recorded('playback-v2-product-rejection',cli+['run-code',code],env)
    assert re.search(rb'"passed"\s*:\s*true',output) and b'### Error' not in output
finally:
    phase09r.recorded('playback-v2-browser-trace-stop',cli+['tracing-stop'],env)
    phase09r.recorded('playback-v2-browser-close',cli+['close'],env)
