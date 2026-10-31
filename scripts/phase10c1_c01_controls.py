#!/usr/bin/env python3
"""Check known raw PCM, MP3 delay, and the estimator's signed offset on planted signal windows."""
import json
from pathlib import Path
import phase10c1_c01_analyze as a

OUT=a.ROOT/'.local/phase10c1/c01-probe'
rows=[]
for schedule_path in sorted(a.CAPTURES.glob('known-pcm*-schedule.json')):
    prefix=schedule_path.name.removesuffix('-schedule.json')
    meta=json.loads((a.CAPTURES/(prefix+'.json')).read_text())
    schedule=json.loads((a.CAPTURES/(prefix+'-schedule.json')).read_text())
    original=a.read(prefix+'-input.f32')
    raw=a.read(prefix+'.f32')
    offset=schedule['startFrame']-meta['firstFrame']
    assert raw[offset:offset+len(original)]==original and not meta['gaps']
    assert not any(raw[:offset]) and not any(raw[offset+len(original):])
    rows.append(dict(name=prefix,exactSamples=len(original),rawSampleError=0,continuousBlocks=True))
decoded=a.envelope(a.read('decoded-c1-shared-v1-a1.f32'))
checks=[]
for rate in [.75,1,1.25,1.5]:
    for planted in [-90,-35,0,35,90]:
        start=17000+planted
        signal=[decoded[round(start+k*rate)] for k in range(1000)]
        measured=a.fit(signal,decoded,80,17000+80*rate,rate=rate,length=500,radius=120)
        error=measured['matchedStartMs']-80*rate-17000
        assert abs(error-planted)<=1,(rate,planted,error)
        joint=a.joint_fit(signal,decoded,[(off,17000+off*rate) for off in [80,250,420]],rate,500)
        assert abs(joint['offsetMediaMs']-planted)<=1 and joint['peakMargin']>.05,(rate,planted,joint)
        checks.append(dict(rate=rate,plantedMediaMs=planted,recoveredMediaMs=error,jointRecoveredMediaMs=joint['offsetMediaMs'],jointPeakMargin=joint['peakMargin'],absoluteErrorMs=abs(error-planted)))
result=dict(status='PASS',knownPcm=rows,plantedOffsetChecks=checks,
            maxPlantedRecoveryErrorMediaMs=max(x['absoluteErrorMs'] for x in checks),
            limitation='Planted windows test estimator sign, rate units and search-grid recovery; they are controls, not acceptance repetitions and do not replace the real browser calibration or acoustic output.')
(OUT/'controls.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(dict(status=result['status'],knownRawExact=True,plantedCases=len(checks),maximumRecoveryErrorMs=result['maxPlantedRecoveryErrorMediaMs'])))
