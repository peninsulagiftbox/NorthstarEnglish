#!/usr/bin/env python3
"""Verify the codec-only timestamp/priming control from retained mathematical-noise PCM."""
import json
import math
import phase10c1_c01_analyze as a

OUT=a.ROOT/'.local/phase10c1/c01-probe'
doc=json.loads((a.CAPTURES/'webcodecs-opus.json').read_text())
description=bytes(doc['decoderConfig']['description'])
assert description[:8]==b'OpusHead'
skip=int.from_bytes(description[10:12],'little')
original=a.read('webcodecs-opus-input.f32')
decoded=a.read('webcodecs-opus-decoded.f32')
windows=[]
for start in [6000,22000,46000,70000]:
    left=original[start:start+960]
    sx=sum(left)
    xx=sum(x*x for x in left)-sx*sx/len(left)
    scores=[]
    for lag in range(-600,601):
        right=decoded[start+lag:start+lag+960]
        if len(right)!=960:continue
        sy=sum(right)
        yy=sum(x*x for x in right)-sy*sy/len(right)
        score=(sum(x*y for x,y in zip(left,right))-sx*sy/len(left))/math.sqrt(max(1e-30,xx*yy))
        scores.append((score,lag))
    score,lag=max(scores)
    windows.append(dict(inputFrame=start,decodedLagFrames=lag,lagMs=lag/48,correlation=score))
assert skip==312 and all(abs(x['decodedLagFrames'])<=1 for x in windows)
result=dict(status='PASS',codec='Chrome WebCodecs Opus 48kHz stereo 128kbps',
            opusHeadPreSkipSamples=skip,codecPrimingMs=skip/48,
            decodedOriginTimestampUs=doc['decodedOriginTimestampUs'],windows=windows,
            maximumAbsoluteResidualMs=max(abs(x['lagMs']) for x in windows),
            explanation='Explicit OpusHead pre-skip and decoder output timestamps separate codec priming from recorder startup origin. MediaRecorder files have their own per-file alignment measured against raw PCM; no callback timestamp is substituted for an acoustic sample origin.')
assert result==json.loads((OUT/'opus-codec-control.json').read_text())
print('PASS: Opus codec priming 312 samples/6.5ms; four timestamp-aligned signal windows recover 0 frames residual')
