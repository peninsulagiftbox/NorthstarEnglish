#!/usr/bin/env python3
"""Freeze the observed calibration budget before accepting any repetition."""
import array
import hashlib
import json
import statistics
import wave
import argparse
import phase10c1_c01_analyze as analysis

OUT=analysis.ROOT/'.local/phase10c1/c01-probe'
parser=argparse.ArgumentParser()
parser.add_argument('--verify',action='store_true')
options=parser.parse_args()
CAP=analysis.CAPTURES
manifest=json.loads((OUT/'manifest.json').read_text())
known=json.loads((CAP/'known-pcm.json').read_text())
schedule=json.loads((CAP/'known-pcm-schedule.json').read_text())
raw=analysis.read('known-pcm.f32')
original=analysis.read('known-pcm-input.f32')
offset=schedule['startFrame']-known['firstFrame']
assert not known['gaps']
assert raw[offset:offset+len(original)]==original
encoder=[]
for asset in manifest['assets']:
    with wave.open(str(OUT/(asset['name']+'.wav'))) as source:
        pcm=array.array('h',source.readframes(source.getnframes()))
        env=analysis.envelope([x/32768 for x in pcm],source.getframerate())
    decoded=analysis.envelope(analysis.read('decoded-'+asset['assetId']+'.f32'))
    estimates=[analysis.fit(decoded,env,start,start-50,length=500,radius=90) for start in [200,600,1000,1500]]
    shifts=[x['windowStartMs']-x['matchedStartMs'] for x in estimates]
    encoder.append(dict(assetId=asset['assetId'],delayMediaMs=statistics.median(shifts),rangeMediaMs=max(shifts)-min(shifts),windows=estimates))
decoder=analysis.envelope(analysis.read('decoded-c1-shared-v1-a1.f32'))
decoded_onset=analysis.bursts(analysis.read('decoded-c1-shared-v1-a1.f32'))[0][0]
segments=manifest['assets'][0]['segments']
budgets=[]
for rate in [.75,1,1.25,1.5]:
    name='reference-shared-'+str(rate)
    meta=json.loads((CAP/(name+'.json')).read_text())
    assert not meta['gaps'] and meta['visibility']=='visible'
    refraw=analysis.read(name+'.f32')
    reference=analysis.envelope(refraw)
    origin=analysis.bursts(refraw)[0][0]-decoded_onset/rate
    windows=[]
    for segment in [segments[0],segments[5],segments[11]]:
        for edge in [segment['startMs'],segment['endMs']]:
            for delta in [-400,0,400]:
                target=max(200,min(len(decoder)-1000,edge+delta))
                f=analysis.fit(reference,decoder,int(origin+target/rate),target,rate=rate,length=500,radius=120)
                f['residualMediaMs']=f['matchedStartMs']-target
                windows.append(f)
    bias=statistics.median(x['residualMediaMs'] for x in windows)
    residual=max(abs(x['residualMediaMs']-bias) for x in windows)
    budget=residual+3.5*rate+1/48
    budgets.append(dict(rate=rate,detectorBiasMediaMs=bias,maximumCalibrationResidualMediaMs=residual,
                        baselineUncertaintyMediaMs=budget,referenceOriginMs=origin,
                        minimumCorrelation=min(x['correlation'] for x in windows),windows=windows))
result=dict(status='PASS' if all(b['baselineUncertaintyMediaMs']<=30 for b in budgets) else 'FAIL',
            scope='Verified browser PCM output path; does not measure physical loudspeaker propagation',
            knownPcmExact=True,knownPcmOffsetFrames=offset,knownPcmScheduleFrame=schedule['startFrame'],
            sourceToChromeMp3=encoder,perRate=budgets,
            budget='Conservative sum: maximum calibrated envelope-mapping residual after per-rate bias correction + 1ms envelope grid + 0.5ms search grid + 2ms edge threshold allowance (all converted to media ms) + 1/48ms raw sample. Per-repetition window spread must be added and <=30ms; no statistical reduction.',
            acceptanceSamplesAtCalibration=0)
if options.verify:
    assert result==json.loads((OUT/'calibration.json').read_text())
else:
    with (OUT/'calibration.json').open('x') as stream:
        stream.write(json.dumps(result,indent=2)+'\n')
print(json.dumps(dict(status=result['status'],rates=[{k:v for k,v in b.items() if k!='windows'} for b in budgets],mp3=[{k:v for k,v in e.items() if k!='windows'} for e in encoder])))
