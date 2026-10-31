#!/usr/bin/env python3
"""Verify the exported acoustic evidence; optional raw-root verifies every retained binary hash."""
import argparse
import csv
import hashlib
import itertools
import json
from pathlib import Path

parser=argparse.ArgumentParser()
parser.add_argument('folder',type=Path)
parser.add_argument('--raw-root',type=Path)
args=parser.parse_args()
folder=args.folder.resolve()
report=json.loads((folder/'acceptance-final.json').read_text())
rows=report['measurements']
shared_cal=json.loads((folder/'calibration.json').read_text())
independent_cal=json.loads((folder/'independent-calibration.json').read_text())
assert report['status']=='PASS' and report['requiredMeasurements']==report['validMeasurements']==report['collectedMeasurements']==240
assert len(rows)==240 and not report['invalid']
keys={(r['track'],r['rate'],r['position'],r['repeat']) for r in rows}
assert keys==set(itertools.product(['shared','independent'],[.75,1,1.25,1.5],['first','middle','last'],range(1,11)))
assert len(report['groups'])==24 and all(g['status']=='PASS' and g['count']==10 for g in report['groups'])
for row in rows:
    assert row['valid'] and row['status']=='PASS'
    assert 0<=row['uncertaintyMediaMs']<=30
    for media,wall in [('startErrorMediaMs','startErrorWallMs'),('endErrorMediaMs','endErrorWallMs'),('loopReturnErrorMediaMs','loopReturnErrorWallMs'),('loopPeriodErrorMediaMs','loopPeriodErrorWallMs')]:
        assert abs(row[media])<=150 and abs(row[media]/row['rate']-row[wall])<1e-8
    assert row['minimumPeakMargin']>.05
    if row['track']=='shared':
        calibration=next(x for x in shared_cal['perRate'] if x['rate']==row['rate'])
    else:
        asset=['first','middle','last'].index(row['position'])+1
        calibration=next(x for x in independent_cal['perAssetRate'] if x['rate']==row['rate'] and x['asset']==asset)
    assert row['jointStart']['windows']==row['jointEnd']['windows']==3
    assert abs(row['startErrorMediaMs']-row['jointStart']['offsetMediaMs']+calibration['detectorBiasMediaMs'])<1e-8
    assert abs(row['endErrorMediaMs']-row['jointEnd']['offsetMediaMs']+calibration['detectorBiasMediaMs'])<1e-8
    spread=max(max(row['startEstimates'])-min(row['startEstimates']),max(row['endEstimates'])-min(row['endEstimates']))
    budget=calibration['baselineUncertaintyMediaMs']+spread+max(0,row['edgeThresholdSpreadWallMs']-2)*row['rate']+max(0,(row['rate']-1)/48)+1.5*row['rate']
    assert abs(row['uncertaintyMediaMs']-budget)<1e-8
    assert row['minimumPeakMargin']==min(row['jointStart']['peakMargin'],row['jointEnd']['peakMargin'])
    assert abs((row['rawNextBeginMs']-row['rawBeginMs'])*row['rate']-next(g['endMs']-g['startMs'] for g in report['groups'] if g['name']==row['group'])-row['loopPeriodErrorMediaMs'])<1e-7
for metric,summary in report['perMetric'].items():
    values=sorted(abs(row[metric]) for row in rows)
    assert max(values)==summary['maxAbsoluteMs']
    assert values[(95*len(values)+99)//100-1]==summary['p95Ms']
assert max(row['uncertaintyMediaMs'] for row in rows)==report['maxUncertaintyMs']
for group in json.loads((folder/'group-statistics.json').read_text())['groups']:
    members=[row for row in rows if row['group']==group['group']]
    assert len(members)==group['count']==10
    for metric,summary in group['metrics'].items():
        values=sorted(abs(row[metric]) for row in members)
        assert summary['maxAbsoluteMs']==max(values) and summary['p95Ms']==values[9]
values=sorted(abs(row[key]) for row in rows for key in report['perMetric'])
assert report['maxAbsoluteErrorMs']==max(values) and report['p95Ms']==values[(95*len(values)+99)//100-1]
for name,field in [('calibration.json','calibrationSha256'),('independent-calibration.json','independentCalibrationSha256'),('manifest.json','stimulusManifestSha256')]:
    assert hashlib.sha256((folder/name).read_bytes()).hexdigest()==report[field]
csv_rows=list(csv.DictReader((folder/'measurements-final.csv').open()))
assert len(csv_rows)==len(rows)
for csv_row,row in zip(csv_rows,rows):
    for key,value in csv_row.items():
        assert value==str(row[key]),(row['group'],key)
manifest=json.loads((folder/'raw-manifest.json').read_text())
assert len({x['path'] for x in manifest})==len(manifest)
for row in rows:
    path='captures/'+row['group']+'.json'
    item=next(x for x in manifest if x['path']==path)
    meta_path=folder/'capture-metadata'/(row['group']+'.json')
    assert hashlib.sha256(meta_path.read_bytes()).hexdigest()==item['sha256']
    meta=json.loads(meta_path.read_text())
    assert not meta['gaps'] and meta['actualRate']==row['rate'] and meta['visibility']=='visible'
    assert all(x['playbackRate']==row['rate'] and x['visibility']=='visible' for x in meta['events'])
if args.raw_root:
    root=args.raw_root.resolve()
    for item in manifest:
        path=(root/item['path']).resolve()
        assert path.is_relative_to(root) and path.is_file()
        data=path.read_bytes()
        assert len(data)==item['bytes'] and hashlib.sha256(data).hexdigest()==item['sha256'],item['path']
print('PASS: complete 24x10 matrix, acoustic metrics/units/p95/budgets, exact CSV, frozen calibration hashes, real rate/foreground/continuous-PCM metadata'+('; all local raw hashes' if args.raw_root else ''))
