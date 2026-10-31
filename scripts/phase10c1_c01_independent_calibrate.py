#!/usr/bin/env python3
"""Recompute the frozen per-asset/rate calibration without using acceptance samples."""
import hashlib
import json
import statistics
import phase10c1_c01_analyze as a

OUT=a.ROOT/'.local/phase10c1/c01-probe'
frozen=json.loads((OUT/'independent-calibration.json').read_text())
rows=[]
for rate in [.75,1,1.25,1.5]:
    for index in [1,2,3]:
        name='reference-independent-'+str(index)+'-'+str(rate)
        raw=a.read(name+'.f32')
        reference=a.envelope(raw)
        decoded_raw=a.read('decoded-c1-independent-v1-a'+str(index)+'.f32')
        decoded=a.envelope(decoded_raw)
        origin=a.bursts(raw)[0][0]-a.bursts(decoded_raw)[0][0]/rate
        windows=[]
        for target in [200,600,1100,1600]:
            fit=a.fit(reference,decoded,int(origin+target/rate),target,rate=rate,length=500,radius=120)
            fit['residualMediaMs']=fit['matchedStartMs']-target
            windows.append(fit)
        bias=statistics.median(w['residualMediaMs'] for w in windows)
        residual=max(abs(w['residualMediaMs']-bias) for w in windows)
        rows.append(dict(rate=rate,asset=index,detectorBiasMediaMs=bias,
                         maximumCalibrationResidualMediaMs=residual,
                         baselineUncertaintyMediaMs=residual+3.5*rate+1/48,windows=windows))
assert rows==frozen['perAssetRate']
assert hashlib.sha256((OUT/'calibration.json').read_bytes()).hexdigest()==frozen['sharedCalibrationSha256']
assert frozen['status']=='PASS' and all(x['baselineUncertaintyMediaMs']<=30 for x in rows)
print('PASS: all 12 frozen independent asset/rate calibrations recomputed from real full-pass output')
