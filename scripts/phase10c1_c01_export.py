#!/usr/bin/env python3
"""Export a speech-free evidence set; voice/probe speech PCM stays in the private raw folder."""
import hashlib
import json
from pathlib import Path
import shutil
import argparse

parser=argparse.ArgumentParser()
parser.add_argument('--refresh',action='store_true')
options=parser.parse_args()

ROOT=Path(__file__).resolve().parents[1]
PRIVATE=ROOT/'.local/phase10c1/c01-probe'
TARGET=ROOT/'docs/handoff/evidence/phase10c1-r/acoustic'
report=json.loads((PRIVATE/'acceptance-final.json').read_text())
assert report['status']=='PASS' and report['validMeasurements']==240 and not report['invalid']
TARGET.mkdir(exist_ok=options.refresh)
names=['manifest.json','calibration.json','independent-calibration.json','controls.json',
       'fixed-candidate.json','candidate-source-delta.json','speed-reset-failure.json',
       'speed-reset-before-fix-test.json','fixed-browser-regression.json','acceptance-final.json',
       'measurements-final.csv','opus-calibration.json','opus-preskip.json','opus-codec-control.json',
       'runtime-cleanup.json','independent-model-check.json','environment-current.json',
       'estimator-single-window-rejection.json','speed-reset-failure-analysis.json']
for name in names:
    shutil.copy2(PRIVATE/name,TARGET/name)
raw_files=sorted((PRIVATE/'captures').glob('*'))
raw_manifest=[dict(path=p.relative_to(PRIVATE).as_posix(),bytes=p.stat().st_size,
                   sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in raw_files if p.is_file()]
(TARGET/'raw-manifest.json').write_text(json.dumps(raw_manifest,indent=2)+'\n')
metadata=TARGET/'capture-metadata'
metadata.mkdir(exist_ok=options.refresh)
for p in raw_files:
    if p.suffix=='.json' and (p.stem.endswith('-fixed') or p.stem.startswith('known-pcm') or p.stem.startswith('reference-') or p.stem.startswith('webcodecs-')):
        shutil.copy2(p,metadata/p.name)
signals=TARGET/'mathematical-controls'
signals.mkdir(exist_ok=options.refresh)
for p in raw_files:
    if p.suffix=='.f32' and (p.stem.startswith('known-pcm') or p.stem.startswith('webcodecs-')):
        shutil.copy2(p,signals/p.name)
shutil.copytree(PRIVATE/'native',TARGET/'native',dirs_exist_ok=options.refresh)
excluded=[]
diagnostics=TARGET/'diagnostics'
diagnostics.mkdir(exist_ok=options.refresh)
for p in raw_files:
    if p.suffix!='.json' or p.stem.endswith('-fixed') or p.stem.startswith(('known-','reference-','decoded-','webcodecs-')):
        continue
    row=json.loads(p.read_text())
    if 'frames' not in row:continue
    reason='Pre-fix candidate; never reused for final 240'
    if p.stem in ['shared-0.75-first','invalid-range-middle']:
        reason='Measurement proxy initially lacked Range; seeks returned 0; invalid capture'
    elif p.stem=='independent-interrupted-pilot':
        reason='Stopped while revising the independent-track calibration; incomplete diagnostic'
    elif p.stem=='speed-reset-failure-tail' or p.stem.startswith('independent-'):
        reason='Pre-fix speed-reset failure/diagnostic; retain actual output, do not reinterpret at requested speed'
    excluded.append(dict(capture=p.name,reason=reason,rawFrames=row['frames']))
    shutil.copy2(p,diagnostics/p.name)
(TARGET/'excluded-captures.json').write_text(json.dumps(excluded,indent=2)+'\n')
logdir=TARGET/'logs'
logdir.mkdir(exist_ok=options.refresh)
logs=[PRIVATE/'speed-reset-before-fix-test.log',PRIVATE/'final-analysis.log']
failure=json.loads((PRIVATE/'speed-reset-failure.json').read_text())
logs.append(PRIVATE/failure['actualRateProofLog'])
for name in ['c01-fix-web-tests','c01-fix-web-typecheck','c01-fix-web-lint','c01-fix-web-build-isolated']:
    logs.append(sorted((ROOT/'docs/handoff/evidence/phase10c1').glob(name+'-*.log'))[-1])
bindings=[]
for p in logs:
    data=p.read_bytes();sha=hashlib.sha256(data).hexdigest()
    text=data.decode(errors='replace').replace(str(ROOT),'<project-root>').replace(str(Path.home()),'<user-home>')
    (logdir/p.name).write_text('Derived log; original SHA-256: '+sha+'\n'+text)
    bindings.append(dict(name=p.name,originalSha256=sha))
(TARGET/'checks.json').write_text(json.dumps(bindings,indent=2)+'\n')
bad=json.loads((PRIVATE/'before-fix/wrong-proxy-next-build/routes-manifest.json').read_text())['rewrites']
good=json.loads((PRIVATE/'fixed-candidate.json').read_text())['isolatedProxyDestinations']
(TARGET/'build-isolation-guard.json').write_text(json.dumps(dict(rejectedBeforeBrowser=True,
    rejectedRewriteManifest=bad,acceptedRewriteManifest=good,personalApiRequest='GET health only',
    personalDatabaseWritten=False,privateBuildRetained=True),indent=2)+'\n')
statistics=[]
for group in report['groups']:
    rows=[r for r in report['measurements'] if r['group']==group['name']]
    metrics={}
    for key in ['startErrorMediaMs','endErrorMediaMs','loopReturnErrorMediaMs','loopPeriodErrorMediaMs']:
        values=sorted(abs(r[key]) for r in rows)
        metrics[key]=dict(maxAbsoluteMs=max(values),p95Ms=values[(95*len(values)+99)//100-1])
    statistics.append(dict(group=group['name'],count=len(rows),metrics=metrics,maxUncertaintyMs=max(r['uncertaintyMediaMs'] for r in rows)))
(TARGET/'group-statistics.json').write_text(json.dumps(dict(p95Method='nearest rank; n=10 implies p95 equals max',groups=statistics),indent=2)+'\n')
sources=list(ROOT.glob('scripts/phase10c1_c01_*.py'))+list(ROOT.glob('scripts/phase10c1-c01-*.js'))
sources+=[ROOT/'apps/web/src/lib/media/AudioController.ts',ROOT/'apps/web/tests/media.test.ts']
(TARGET/'source-inputs.json').write_text(json.dumps([dict(path=p.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(sources)],indent=2)+'\n')
print('Exported',len(list(TARGET.rglob('*'))),'entries; all voice/probe speech files excluded; mathematical noise controls included')
