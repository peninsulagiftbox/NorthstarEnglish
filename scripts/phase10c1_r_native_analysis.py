#!/usr/bin/env python3
"""Check archived real visibility/pause/resume cycles; no event dispatch or playback."""
import hashlib
import argparse
import json
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--tab-prefix')
    options=parser.parse_args()
    folder=ROOT/(ROOT/'.local/phase10c1/R_ACTIVE_OUTPUT').read_text().strip()
    path=folder/'native-events.jsonl'
    raw=path.read_bytes()
    events=[json.loads(line) for line in raw.decode().splitlines()]
    frozen=folder/('native-events-accepted-'+str(time.time_ns())+'.jsonl')
    with frozen.open('xb') as stream:
        stream.write(raw)
    cycles=[]
    tabs=sorted({row['id'] for row in events if not options.tab_prefix or row['id'].startswith(options.tab_prefix)})
    if options.tab_prefix:assert len(tabs)==1, 'Tab prefix must identify exactly one observed document'
    for tab in tabs:
        rows=sorted((row for row in events if row['id']==tab),key=lambda row:row['seq'])
        assert len({row['seq'] for row in rows})==len(rows)
        for hidden in rows:
            if hidden['event']!='visibilitychange' or hidden['visibility']!='hidden' or hidden['paused'] or not hidden['trusted']:
                continue
            after=[row for row in rows if row['seq']>hidden['seq']]
            pause=next((row for row in after if row['event']=='pause'),None)
            if not pause or not pause['paused'] or pause['visibility']!='hidden' or not pause['trusted']:
                continue
            visible=next((row for row in after if row['event']=='visibilitychange' and row['visibility']=='visible'),None)
            if not visible or not visible['trusted'] or not visible['paused'] or visible['seq']<=pause['seq']:
                continue
            play=next((row for row in rows if row['seq']>visible['seq'] and row['event']=='play'),None)
            if not play or play['visibility']!='visible' or play['paused'] or not play['trusted']:
                continue
            if len({row['mode'] for row in [hidden,pause,visible,play]})!=1:
                continue
            between=[row for row in rows if pause['seq']<row['seq']<play['seq']]
            assert not any(row['event'] in ['play','playing'] for row in between)
            assert abs(visible['time']-pause['time'])<.005
            assert abs(play['time']-pause['time'])<.005
            assert play['at']-visible['at']>=1000
            cycles.append(dict(mode=hidden['mode'],events=[hidden,pause,visible,play],
                               pauseEventDelayMs=pause['at']-hidden['at'],
                               foregroundPausedUntilManualPlayMs=play['at']-visible['at'],
                               pausedMediaDriftMs=(visible['time']-pause['time'])*1000,
                               resumeCoordinateDriftMs=(play['time']-pause['time'])*1000))
    assert {'single','sentence'} <= {row['mode'] for row in cycles}, 'Need both single and sentence-loop native cycles'
    result=dict(status='PASS',scope='Native Chrome tab switching, shared track, single and sentence-loop modes',
                nativeActionSource='cua_repl desktop Chrome: open test tab; start actual player; Cmd+T; Cmd+W; observe paused; click Play',
                syntheticVisibilityEvents=False,recorder='Passive same-origin script supplied only by isolated test proxy; no console paste or browser setting changes',
                rawFile=frozen.name,rawSha256=hashlib.sha256(raw).hexdigest(),rawEventCount=len(events),
                ordering='Per-tab seq, not HTTP arrival order; original arrival order retained in raw JSONL',cycles=cycles,
                limits='Event timings diagnose policy only, not acoustic precision. Other browsers, minimized windows, full-track background behavior not included.')
    (folder/'native-acceptance.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(status=result['status'],cycles=[{k:v for k,v in row.items() if k!='events'} for row in cycles])))


if __name__=='__main__':
    main()
