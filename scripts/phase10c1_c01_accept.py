#!/usr/bin/env python3
"""Recompute all 24 x 10 acoustic measurements from saved raw PCM and Chrome decode references."""
import argparse
import csv
import hashlib
import json
import statistics
import time
import phase10c1_c01_analyze as a

OUT=a.ROOT/'.local/phase10c1/c01-probe'
parser=argparse.ArgumentParser()
parser.add_argument('--partial',action='store_true')
options=parser.parse_args()
calibration=json.loads((OUT/'calibration.json').read_text())
assert calibration['status']=='PASS'
independent_calibration=json.loads((OUT/'independent-calibration.json').read_text())
assert independent_calibration['status']=='PASS'
manifest=json.loads((OUT/'manifest.json').read_text())
rows=[]
groups=[]
invalid=[]
for track in ['shared','independent']:
    for rate in [.75,1,1.25,1.5]:
        budget=next(b for b in calibration['perRate'] if b['rate']==rate)
        for index,position in enumerate(['first','middle','last']):
            suffix='-fixed'
            name=track+'-'+str(rate)+'-'+position+suffix
            path=a.CAPTURES/(name+'.json')
            if not path.exists():
                if options.partial:continue
                raise AssertionError('Missing '+name)
            meta=json.loads(path.read_text())
            assert not meta['gaps'] and meta['visibility']=='visible',name
            assert all(e['visibility']=='visible' for e in meta['events']),name+' background event'
            assert meta['actualRate']==rate and all(e['playbackRate']==rate for e in meta['events']),name+' rate mismatch'
            if track=='independent':
                budget=next(b for b in independent_calibration['perAssetRate'] if b['rate']==rate and b['asset']==index+1)
            asset=manifest['assets'][0 if track=='shared' else index+1]
            segment=asset['segments'][[0,5,11][index] if track=='shared' else 0]
            start,end=segment['startMs'],segment['endMs']
            raw=a.read(name+'.f32')
            waveform=a.envelope(raw)
            decoded_raw=a.read('decoded-'+asset['assetId']+'.f32')
            decoded=a.envelope(decoded_raw)
            onset=a.bursts(decoded_raw)[0][0]
            expected_start=max(start,onset)
            edges=a.bursts(raw)
            alternative_edges=[a.bursts(raw,threshold=t) for t in [.002,.008]]
            assert len(edges)>=11,(name,len(edges))
            assert all(len(x)==len(edges) for x in alternative_edges),name+' unstable edge count'
            group_rows=[]
            for repeat,(begin,finish) in enumerate(edges[:10]):
                assert finish-begin>(end-start)/rate*.7,(name,repeat,'truncated run')
                early=[a.fit(waveform,decoded,begin+offset,expected_start+rate*offset,rate=rate,length=500,radius=120) for offset in [80,250,420]]
                late=[a.fit(waveform,decoded,finish-offset,end-rate*offset,rate=rate,length=450,radius=120) for offset in [500,650,800]]
                starts=[fit['matchedStartMs']-rate*offset-expected_start for fit,offset in zip(early,[80,250,420])]
                ends=[fit['matchedStartMs']+rate*offset-end for fit,offset in zip(late,[500,650,800])]
                joint_start=a.joint_fit(waveform,decoded,[(begin+off,expected_start+rate*off) for off in [80,250,420]],rate,500)
                joint_end=a.joint_fit(waveform,decoded,[(finish-off,end-rate*off) for off in [500,650,800]],rate,450)
                start_error=joint_start['offsetMediaMs']-budget['detectorBiasMediaMs']
                end_error=joint_end['offsetMediaMs']-budget['detectorBiasMediaMs']
                edge_spread=max(abs(other[repeat][j]-edges[repeat][j]) for other in alternative_edges for j in [0,1])
                uncertainty=budget['baselineUncertaintyMediaMs']+max(max(starts)-min(starts),max(ends)-min(ends))+max(0,edge_spread-2)*rate+max(0,(rate-1)/48)
                loop_period_error=(edges[repeat+1][0]-begin)*rate-(end-start)
                next_begin=edges[repeat+1][0]
                return_fit=a.fit(waveform,waveform,next_begin+50,begin+50,length=100,radius=25)
                loop_error=start_error+(return_fit['matchedStartMs']-(begin+50))*rate
                quality=min(joint_start['peakMargin'],joint_end['peakMargin'])
                return_margin=return_fit['correlation']-return_fit['alternativeOutside30Ms']
                return_uncertainty=uncertainty+1.5*rate
                valid=return_uncertainty<=30 and quality>.05 and return_margin>.05
                row=dict(group=name,track=track,position=position,rate=rate,repeat=repeat+1,
                         startErrorMediaMs=start_error,endErrorMediaMs=end_error,loopReturnErrorMediaMs=loop_error,
                         loopPeriodErrorMediaMs=loop_period_error,
                         startErrorWallMs=start_error/rate,endErrorWallMs=end_error/rate,loopReturnErrorWallMs=loop_error/rate,
                         loopPeriodErrorWallMs=loop_period_error/rate,
                         uncertaintyMediaMs=max(uncertainty,return_uncertainty),loopUncertaintyMediaMs=return_uncertainty,
                         maximumAbsoluteErrorMediaMs=max(abs(start_error),abs(end_error),abs(loop_error),abs(loop_period_error)),
                         rawBeginMs=begin,rawEndMs=finish,rawNextBeginMs=edges[repeat+1][0],
                         acousticGapWallMs=edges[repeat+1][0]-finish,
                         edgeThresholdSpreadWallMs=edge_spread,minimumPeakMargin=quality,
                         valid=valid,status='PASS' if valid and max(abs(start_error),abs(end_error),abs(loop_error),abs(loop_period_error))<=150 else ('FAIL' if valid else 'NOT VERIFIED'),
                         returnWindow=return_fit,
                         jointStart=joint_start,jointEnd=joint_end,
                         startWindows=early,endWindows=late,startEstimates=starts,endEstimates=ends)
                rows.append(row);group_rows.append(row)
                if not valid:invalid.append(dict(group=name,repeat=repeat+1,uncertaintyMediaMs=uncertainty,minimumPeakMargin=quality))
            groups.append(dict(name=name,startMs=start,endMs=end,count=10,status='PASS' if all(r['status']=='PASS' for r in group_rows) else 'NOT PASS',
                               maxAbsoluteErrorMs=max(r['maximumAbsoluteErrorMediaMs'] for r in group_rows),
                               maxUncertaintyMs=max(r['uncertaintyMediaMs'] for r in group_rows)))
            print(json.dumps(groups[-1]),flush=True)
absolute=[abs(r[k]) for r in rows for k in ['startErrorMediaMs','endErrorMediaMs','loopReturnErrorMediaMs','loopPeriodErrorMediaMs']]
sorted_errors=sorted(absolute)
result=dict(status='PASS' if len(rows)==240 and all(r['status']=='PASS' for r in rows) else 'NOT VERIFIED',
            requiredMeasurements=240,validMeasurements=sum(r['valid'] for r in rows),collectedMeasurements=len(rows),
            maxAbsoluteErrorMs=max(absolute,default=None),p95Ms=sorted_errors[(95*len(sorted_errors)+99)//100-1] if rows else None,
            maxUncertaintyMs=max((r['uncertaintyMediaMs'] for r in rows),default=None),
            definition='Start/end signed source-media-coordinate offsets inferred from actual 7kHz output envelope matched against Chrome decoded reference, with frozen per-rate detector bias removed. Known encoder leading silence is excluded from audible-onset error only. Loop return position is the next audible prefix matched against the current prefix plus its calibrated start offset; onset-to-onset period error and acoustic silent gap are separately recorded. No element timestamp is used for these errors.',
            groups=groups,measurements=rows,invalid=invalid,
            originalAssetsUnchanged=True,stimulusManifestSha256=hashlib.sha256((OUT/'manifest.json').read_bytes()).hexdigest(),
            calibrationSha256=hashlib.sha256((OUT/'calibration.json').read_bytes()).hexdigest())
result['independentCalibrationSha256']=hashlib.sha256((OUT/'independent-calibration.json').read_bytes()).hexdigest()
metrics={}
for metric in ['startErrorMediaMs','endErrorMediaMs','loopReturnErrorMediaMs','loopPeriodErrorMediaMs']:
    values=sorted(abs(row[metric]) for row in rows)
    metrics[metric]=dict(maxAbsoluteMs=max(values,default=None),p95Ms=values[(95*len(values)+99)//100-1] if values else None)
result['perMetric']=metrics
suffix='partial' if options.partial else 'final'
(OUT/('acceptance-'+suffix+'.json')).write_text(json.dumps(result,indent=2)+'\n')
if rows:
    keys=[k for k in rows[0] if k not in ['startWindows','endWindows','startEstimates','endEstimates','returnWindow','jointStart','jointEnd']]
    with (OUT/('measurements-'+suffix+'.csv')).open('w') as stream:
        writer=csv.DictWriter(stream,fieldnames=keys,extrasaction='ignore');writer.writeheader();writer.writerows(rows)
print(json.dumps({k:v for k,v in result.items() if k not in ['measurements','groups','invalid']}))
if invalid:print(json.dumps(dict(invalid=invalid)))
