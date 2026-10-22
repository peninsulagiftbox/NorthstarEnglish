#!/usr/bin/env python3
"""Create immutable demo v2 from evaluated Edge GB output; never rewrite v1/DB."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'content/demo-01/v1'
TARGET=ROOT/'content/demo-01/v2'
EVAL=ROOT/'.local/tts-evaluation'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
serialize=lambda value:(json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode()
def frozen(path,raw):
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists() and path.read_bytes()!=raw:raise ValueError('Frozen file differs: '+str(path.relative_to(ROOT)))
    path.write_bytes(raw)
def version(value):
    if isinstance(value,str):return value.replace('demo-01-v1','demo-01-v2')
    if isinstance(value,list):return [version(v) for v in value]
    if isinstance(value,dict):return {k:version(v) for k,v in value.items()}
    return value
baseline=json.loads((EVAL/'baseline.json').read_text())
assert sha((SOURCE/'lesson.json').read_bytes())==baseline['lessonSha256']
assert sha((SOURCE/'manifest.json').read_bytes())==baseline['manifestSha256']
assert {f'{n:02}':sha((SOURCE/'audio'/f'{n:02}.mp3').read_bytes()) for n in range(1,11)}==baseline['audio']
evaluated=json.loads((EVAL/'results.json').read_text())
assert evaluated['edgeTtsVersion']=='7.3.1'
old=json.loads((SOURCE/'manifest.json').read_text());lesson=version(json.loads((SOURCE/'lesson.json').read_text()));lesson['version']=2
lesson['audioLabel']='Microsoft Edge 在线合成 · 英式英语 · Mia: Sonia / Leo: Ryan'
manifest={**old,'versionId':'demo-01-v2','source':{'path':'content/demo-01/v1/lesson.json','sha256':baseline['lessonSha256']},'licenses':[old['licenses'][0]],'audioAssets':[]}
license={'id':'demo-edge-gb-v2','sourceType':'original','medium':'audio','owner':'unknown','sourceRef':'edge-tts:7.3.1:demo-01-v2','rightsScope':'local_test_only; formal publication blocked pending review','territory':'unknown','reviewStatus':'pending_review','proofRef':None,'generator':'edge-tts 7.3.1 / Microsoft Edge online text-to-speech','voice':'Mia=en-GB-SoniaNeural; Leo=en-GB-RyanNeural','declaration':'从本项目原创10句文本在线合成；生成技术与参数已记录，服务及输出正式发布权利尚未独立核实。','generatedDate':'2026-10-22','parameters':{'rate':'+0%','volume':'+0%','pitch':'+0Hz','format':'audio-24khz-48kbitrate-mono-mp3'},'selectionEvidence':'2026-10-22 user listening preference: British Edge Sonia/Ryan is better; local technical evaluation passed'}
manifest['licenses'].append(license)
for sentence in lesson['sentences']:
    n=sentence['sequence'];path=EVAL/'edge-gb'/f'{n:02}.mp3';raw=path.read_bytes()
    measured=next(row for row in evaluated['files'] if row['group']=='edge-gb' and row['sequence']==n)
    assert sha(raw)==measured['sha256'] and measured['voice']==('en-GB-SoniaNeural' if sentence['speaker']=='Mia' else 'en-GB-RyanNeural')
    info=subprocess.run(['afinfo',str(path)],capture_output=True,text=True,check=True).stdout
    duration=round(float(re.search(r'estimated duration:\s*([\d.]+)',info).group(1))*1000)
    sentence['endMs']=duration
    asset={'id':f'demo-01-v2-a{n:02}','storageKey':f'audio/{n:02}.mp3','licenseId':license['id'],'sourceKind':'original_tts','mimeType':'audio/mpeg','byteSize':len(raw),'durationMs':duration,'sha256':sha(raw),'voice':('en-GB-SoniaNeural' if sentence['speaker']=='Mia' else 'en-GB-RyanNeural')}
    manifest['audioAssets'].append(asset);frozen(TARGET/asset['storageKey'],raw)
manifest['lessonSha256']=sha(serialize(lesson))
frozen(TARGET/'lesson.json',serialize(lesson));frozen(TARGET/'manifest.json',serialize(manifest))
frozen(ROOT/'content/demo-01/active.json',serialize({'activeVersion':2,'publishedVersions':[1,2]}))
print('PASS: immutable v2 generated; 10 original v1 audio/text hashes preserved; no database access.')
