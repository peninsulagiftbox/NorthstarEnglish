#!/usr/bin/env python3
"""Recompute observed raw/Opus envelope offsets; never promotes diagnostics to acceptance."""
import array
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def floats(path):
    result = array.array('f')
    result.frombytes(path.read_bytes())
    return result


def envelope(samples, rate):
    n = rate // 1000
    energy = [sum(x*x for x in samples[k:k+n])/n for k in range(0, len(samples)-n, n)]
    return [math.sqrt(sum(energy[k:k+5])/5) for k in range(len(energy)-5)]


def fit(raw, opus, start, length=250):
    target = opus[start:start+length]
    assert len(target) == length
    sy, syy = sum(target), sum(y*y for y in target)
    vy = syy-sy*sy/length
    scores = []
    for lag in range(-100, 901):
        at = start+lag
        if at < 0 or at+length > len(raw):
            continue
        window = raw[at:at+length]
        sx = sum(window)
        vx = sum(x*x for x in window)-sx*sx/length
        if min(vx, vy) < 1e-10:
            continue
        score = (sum(x*y for x,y in zip(window,target))-sx*sy/length)/math.sqrt(vx*vy)
        scores.append((score,lag))
    assert scores
    score, lag = max(scores)
    alternative = max((s for s,l in scores if abs(l-lag)>20), default=None)
    return dict(opusWindowStartMs=start, lengthMs=length, rawMinusOpusOffsetMs=lag,
                correlation=score, bestAlternativeOutside20Ms=alternative)


def marker(samples, rate, expected=.8):
    n, hop = rate//100, rate//1000
    window = [complex(math.cos(2*math.pi*1200*i/rate), -math.sin(2*math.pi*1200*i/rate)) for i in range(n)]
    measured = [(k,abs(sum(samples[k+i]*window[i] for i in range(n)))*2/n)
                for k in range(int((expected-.1)*rate), int((expected+.2)*rate),hop)]
    peak = max(a for _,a in measured)
    return next(k for k,a in measured if a>peak*.3)*1000/rate


def main():
    folder = ROOT/(ROOT/'.local/phase10c1/R_ACTIVE_OUTPUT').read_text().strip()
    doc = json.loads((folder/'phase10c1-r-codec-calibration.js.json').read_text())
    reports=[]
    for capture in doc['captures']:
        if 'rawFile' not in capture:
            continue
        raw = envelope(floats(folder/capture['rawFile']),capture['sampleRate'])
        opus = envelope(floats(folder/capture['pcmFile']),capture['opusSampleRate'])
        windows = [fit(raw,opus,int(fraction*(len(opus)-250))) for fraction in [.1,.35,.6,.85]]
        offsets = [w['rawMinusOpusOffsetMs'] for w in windows]
        reports.append(dict(rate=capture['rate'],windows=windows,
                            observedOffsetSpreadMs=max(offsets)-min(offsets),resolutionWallMs=1,
                            rawBlockGaps=capture['rawBlockGaps'],uncertaintyMediaMs=None,
                            rawSha256=hashlib.sha256((folder/capture['rawFile']).read_bytes()).hexdigest(),
                            opusDecodedSha256=hashlib.sha256((folder/capture['pcmFile']).read_bytes()).hexdigest()))
    reference=json.loads((folder/'phase10c1-r-mp3-reference.js.json').read_text())['captures'][0]
    point=marker(floats(folder/reference['pcmFile']),reference['sampleRate'])
    previous=json.loads((ROOT/'docs/handoff/evidence/phase10c1/reacceptance/mp3-marker-diagnostic.json').read_text())
    source=next(x['source']['onsetWindowMs'] for x in previous['measurements'] if x['asset']=='shared-v1')
    result=dict(status='CALIBRATION DIAGNOSTIC',acceptanceStatus='NOT VERIFIED',validMeasurements=0,
                method='1ms RMS envelope with 5ms smoothing; normalized correlation of four 250ms windows per rate; offset search -100..900ms,1ms step; raw frame gaps retained and not silently filled',
                opusVersusRaw=reports,mp3ChromeVersusSource=dict(assetSha256=reference['assetSha256'],
                sourceMarkerWindowMs=source,chromeMarkerWindowMs=point,shiftMs=point-source),
                reason='Observed correlation spread is not a complete uncertainty budget. Raw clock gaps, graph delay, speed-dependent marker/edge bias, and boundary leakage observability still need validation.')
    (folder/'codec-analysis.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(opus=[dict(rate=x['rate'],spreadMs=x['observedOffsetSpreadMs'],minCorrelation=min(w['correlation'] for w in x['windows']),gaps=len(x['rawBlockGaps'])) for x in reports],mp3ShiftMs=point-source)))


if __name__=='__main__':
    main()
