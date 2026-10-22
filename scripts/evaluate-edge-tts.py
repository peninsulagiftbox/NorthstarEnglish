#!/usr/bin/env python3
"""Local, reproducible TTS comparison; never edits published content or MySQL.
Run in .local/tts-evaluation/venv. --generate sends only the ten original sentences
and three extra repetitions per candidate of sentence 06 to Microsoft.
Signal statistics and returned boundary text do NOT measure pronunciation quality.
"""
import argparse
import array
import asyncio
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import platform
import re
import shutil
import statistics
import subprocess
import sys
import time
import wave

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '.local/tts-evaluation'
GROUPS = {
    'current': {'Mia': 'unknown', 'Leo': 'unknown'},
    'edge-gb': {'Mia': 'en-GB-SoniaNeural', 'Leo': 'en-GB-RyanNeural'},
    'edge-us': {'Mia': 'en-US-AriaNeural', 'Leo': 'en-US-GuyNeural'},
}

def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def dbfs(value):
    return round(20 * math.log10(max(value, 1e-12)), 3)

def signal(path, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(['afconvert', '-f', 'WAVE', '-d', 'LEI16', str(path), str(destination)], check=True, capture_output=True)
    with wave.open(str(destination)) as reader:
        assert reader.getnchannels() == 1 and reader.getsampwidth() == 2
        rate = reader.getframerate()
        samples = array.array('h', reader.readframes(reader.getnframes()))
        if sys.byteorder != 'little': samples.byteswap()
    assert samples, 'Empty decoded signal'
    unit = [s / 32768 for s in samples]
    peak = max(abs(s) for s in unit)
    rms = math.sqrt(statistics.mean(s*s for s in unit))
    block = max(1, round(rate * .01))
    frames = [math.sqrt(statistics.mean(s*s for s in unit[n:n+block])) for n in range(0, len(unit), block)]
    voiced = [i for i, value in enumerate(frames) if value > 10**(-45/20)]
    active_rms = math.sqrt(statistics.mean(frames[i]**2 for i in voiced)) if voiced else 0
    result = {
        'sampleRateHz': rate, 'channels': 1, 'decodedDurationSec': round(len(unit)/rate, 4),
        'peakDbfs': dbfs(peak), 'globalRmsDbfs': dbfs(rms), 'activeFrameRmsDbfs': dbfs(active_rms),
        'nearFullScaleSamples': sum(abs(s) >= 32760 for s in samples),
        'leadingSilenceMsAtMinus45Dbfs': voiced[0]*10 if voiced else round(len(unit)/rate*1000),
        'trailingSilenceMsAtMinus45Dbfs': max(0, round(len(unit)/rate*1000)-(voiced[-1]+1)*10) if voiced else round(len(unit)/rate*1000),
    }
    # Fair listening copies: linear gain only, target active-frame RMS -22 dBFS,
    # limited to peak -1 dBFS. Originals stay byte-identical.
    gain = min(10**(-22/20)/max(active_rms, 1e-12), 10**(-1/20)/max(peak, 1e-12))
    normalized = array.array('h', (round(s*gain) for s in samples))
    normal = OUT / 'normalized' / path.parent.name / (path.stem + '.wav')
    normal.parent.mkdir(parents=True, exist_ok=True)
    if sys.byteorder != 'little': normalized.byteswap()
    with wave.open(str(normal), 'wb') as writer:
        writer.setparams((1,2,rate,0,'NONE','not compressed'));writer.writeframes(normalized.tobytes())
    result['listeningGainDb'] = dbfs(gain)
    result['normalizedPath'] = str(normal.relative_to(OUT))
    return result

async def synthesize(lesson):
    import edge_tts
    voices = await asyncio.wait_for(edge_tts.list_voices(), 30)
    dump(OUT/'voices.json', voices)
    names = {v['ShortName'] for v in voices}
    assert all(v in names for group, pair in GROUPS.items() if group != 'current' for v in pair.values())
    records = []
    record_path = OUT/'generation.json'
    if record_path.exists(): records = json.loads(record_path.read_text())
    async def one(group, sentence, repetition=None):
        voice = GROUPS[group][sentence['speaker']]
        name = f"{sentence['sequence']:02}" + (f'-repeat-{repetition}' if repetition is not None else '')
        folder = OUT/group
        path = folder/(name+'.mp3');folder.mkdir(exist_ok=True)
        if path.exists() and any(r['path']==str(path.relative_to(OUT)) and r['success'] for r in records): return
        start = time.monotonic(); metadata = []; count = 0; success = False; error = None
        try:
            communicate = edge_tts.Communicate(sentence['text'], voice, rate='+0%', volume='+0%', pitch='+0Hz', boundary='WordBoundary', connect_timeout=10, receive_timeout=25)
            async def receive():
                nonlocal count
                with path.with_suffix('.partial').open('wb') as writer:
                    async for chunk in communicate.stream():
                        if chunk['type']=='audio': writer.write(chunk['data']);count += len(chunk['data'])
                        else: metadata.append(chunk)
            await asyncio.wait_for(receive(), 40)
            assert count > 1000
            path.with_suffix('.partial').replace(path);success=True
        except Exception as exception:
            error = type(exception).__name__  # never persist URLs/tokens or proxy credentials
            path.with_suffix('.partial').unlink(missing_ok=True)
        records.append({'group':group,'sentenceId':sentence['id'],'sequence':sentence['sequence'],'speaker':sentence['speaker'],'text':sentence['text'],'voice':voice,'rate':'+0%','volume':'+0%','pitch':'+0Hz','repetition':repetition,'path':str(path.relative_to(OUT)),'elapsedSec':round(time.monotonic()-start,3),'success':success,'error':error,'bytes':count,'boundaryText':[m.get('text','') for m in metadata],'metadata':metadata})
        dump(record_path, records)
        print(group,name,voice,'OK' if success else error,round(time.monotonic()-start,2),flush=True)
    for sentence in lesson['sentences']:
        for group in ('edge-gb','edge-us'): await one(group,sentence)
    for group in ('edge-gb','edge-us'):
        for repeat in range(1,4): await one(group,lesson['sentences'][5],repeat)


def main():
    parser = argparse.ArgumentParser();parser.add_argument('--generate',action='store_true');args = parser.parse_args()
    OUT.mkdir(exist_ok=True,parents=True)
    lesson_path = ROOT/'content/demo-01/v1/lesson.json';lesson=json.loads(lesson_path.read_text())
    baseline = {'lessonSha256':sha(lesson_path),'manifestSha256':sha(lesson_path.with_name('manifest.json')),'audio':{f'{n:02}':sha(lesson_path.parent/'audio'/f'{n:02}.mp3') for n in range(1,11)}}
    baseline_path = OUT/'baseline.json'
    if baseline_path.exists(): assert baseline==json.loads(baseline_path.read_text()),'Published baseline changed'
    else: dump(baseline_path,baseline)
    (OUT/'current').mkdir(exist_ok=True)
    for n in range(1,11): shutil.copyfile(lesson_path.parent/'audio'/f'{n:02}.mp3',OUT/'current'/f'{n:02}.mp3')
    if args.generate: asyncio.run(synthesize(lesson))
    results=[]
    for group in GROUPS:
        for sentence in lesson['sentences']:
            path=OUT/group/f"{sentence['sequence']:02}.mp3"
            if not path.exists(): continue
            info=subprocess.run(['afinfo',str(path)],capture_output=True,text=True,check=True).stdout
            def number(pattern):
                match=re.search(pattern,info);return float(match.group(1)) if match else None
            row={'group':group,'sequence':sentence['sequence'],'text':sentence['text'],'voice':GROUPS[group][sentence['speaker']],'sha256':sha(path),'byteSize':path.stat().st_size,'estimatedDurationSec':number(r'estimated duration:\s*([\d.]+) sec'),'bitrate':number(r'bit rate:\s*(\d+) bits'),'path':str(path.relative_to(OUT))}
            row.update(signal(path,OUT/'pcm'/group/(path.stem+'.wav')));results.append(row)
    generation=json.loads((OUT/'generation.json').read_text()) if (OUT/'generation.json').exists() else []
    summary={}
    for group in GROUPS:
        rows=[r for r in results if r['group']==group];calls=[r for r in generation if r['group']==group]
        summary[group]={'decodedFiles':len(rows),'bytes':sum(r['byteSize'] for r in rows),'durationSec':round(sum(r['decodedDurationSec'] for r in rows),3),'sampleRatesHz':sorted({r['sampleRateHz'] for r in rows}),'nearFullScaleSamples':sum(r['nearFullScaleSamples'] for r in rows),'meanActiveRmsDbfs':round(statistics.mean(r['activeFrameRmsDbfs'] for r in rows),3) if rows else None,'meanLeadingSilenceMs':statistics.mean(r['leadingSilenceMsAtMinus45Dbfs'] for r in rows) if rows else None,'meanTrailingSilenceMs':statistics.mean(r['trailingSilenceMsAtMinus45Dbfs'] for r in rows) if rows else None,'synthesisCalls':len(calls),'synthesisSuccesses':sum(r['success'] for r in calls),'medianSynthesisSec':round(statistics.median(r['elapsedSec'] for r in calls),3) if calls else None}
    dump(OUT/'results.json',{'python':platform.python_version(),'edgeTtsVersion':importlib.metadata.version('edge-tts'),'groups':GROUPS,'summary':summary,'files':results,'limits':['No human listening scores','No independent ASR or pronunciation assessment','Boundary text is provider metadata, not recognized speech','10ms RMS frames above -45 dBFS are an energy heuristic, not linguistic VAD','Local test sample only; generation latency includes network and does not establish SLA']})
    assert baseline==json.loads(baseline_path.read_text())
    assert baseline['lessonSha256']==sha(lesson_path) and baseline['manifestSha256']==sha(lesson_path.with_name('manifest.json'))
    assert baseline['audio']=={f'{n:02}':sha(lesson_path.parent/'audio'/f'{n:02}.mp3') for n in range(1,11)}
    print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
