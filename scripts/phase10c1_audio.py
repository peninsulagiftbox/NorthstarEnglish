#!/usr/bin/env python3
"""Original local speech + known PCM markers. Private fixtures; no textbook or voice redistribution."""
import array, hashlib, json, math, subprocess, wave
from pathlib import Path
import lameenc
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'.local/phase10c1/audio';OUT.mkdir(parents=True,exist_ok=True)
RATE=24000
TEXTS=['The red kite rests beside the gate.','Our small robot carries a blue cup.','I keep three pencils in this box.','Please open the window after lunch.','A quiet train crosses the green bridge.','We can plant a tree near the path.','My notebook has a silver star.','The orange lamp lights our table.','I will bring fresh water tomorrow.','Two paper boats float on the pond.','Let us count the steps together.','This little garden belongs to our team.']
def run(argv):
 p=subprocess.run(argv,capture_output=True);assert p.returncode==0,p.stderr.decode(errors='replace')
def silence(ms):return array.array('h',[0])*(RATE*ms//1000)
def tone(ms,freq=1200):return array.array('h',(int(6000*math.sin(2*math.pi*freq*i/RATE)) for i in range(RATE*ms//1000)))
def speech(n,text):
 a=OUT/f'speech-{n}.aiff';w=OUT/f'speech-{n}.wav'
 if not w.exists() or w.stat().st_size<=4096:
  run(['/usr/bin/say','-v','Samantha','-r','180','-o',str(a),text]);run(['/usr/bin/afconvert','-f','WAVE','-d',f'LEI16@{RATE}','-c','1',str(a),str(w)])
 with wave.open(str(w)) as source:assert source.getframerate()==RATE;return array.array('h',source.readframes(source.getnframes()))
def encode(name,pcm,segments):
 source=OUT/(name+'.wav')
 with wave.open(str(source),'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(RATE);w.writeframes(pcm.tobytes())
 encoder=lameenc.Encoder();encoder.set_bit_rate(64);encoder.set_in_sample_rate(RATE);encoder.set_channels(1);encoder.set_quality(2)
 path=OUT/(name+'.mp3');path.write_bytes(encoder.encode(pcm.tobytes())+encoder.flush())
 decoded=OUT/(name+'-decoded.wav');run(['/usr/bin/afconvert','-f','WAVE','-d','LEI16',str(path),str(decoded)])
 with wave.open(str(decoded)) as w:duration=w.getnframes()*1000//w.getframerate()
 return dict(name=name,path=str(path.relative_to(ROOT)),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),bytes=path.stat().st_size,durationMs=duration,sourcePcmSha256=hashlib.sha256(source.read_bytes()).hexdigest(),decodedPcmSha256=hashlib.sha256(decoded.read_bytes()).hexdigest(),sourceSampleRate=RATE,segments=segments,decodeExitCode=0)
assets=[];pcm=silence(800);segments=[]
for i,text in enumerate(TEXTS):
 line=tone(40)+silence(100)+speech(i,text)+silence(100)+tone(40,1800)
 start=len(pcm)*1000//RATE;pcm.extend(line);end=len(pcm)*1000//RATE
 segments.append(dict(sequence=i+1,text=text,startMs=start,endMs=end,startMarkerSample=start*RATE//1000,endMarkerSample=(end-40)*RATE//1000))
 pcm.extend(silence(650))
assets.append(encode('shared-v1',pcm,segments))
# New immutable version has a different leading interval and file hash.
assets.append(encode('shared-v2',silence(300)+pcm,[dict(x,startMs=x['startMs']+300,endMs=x['endMs']+300,startMarkerSample=x['startMarkerSample']+7200,endMarkerSample=x['endMarkerSample']+7200) for x in segments]))
for i in (0,5,11):
 line=tone(40)+silence(100)+speech(i,TEXTS[i])+silence(100)+tone(40,1800)
 assets.append(encode('independent-'+str(i+1),line,[dict(sequence=1,text=TEXTS[i],startMs=0,endMs=len(line)*1000//RATE)]))
long=silence(660000)
for at in (1000,320000,641000):
 mark=tone(200);long[at*RATE//1000:at*RATE//1000+len(mark)]=mark
assets.append(encode('long-660s',long,[dict(sequence=1,text='Original test signal.',startMs=640000,endMs=650000)]))
record=dict(audioSource='Original text, local macOS Samantha speech for private functional testing; mathematical marker tones; no textbook or third-party recordings',rightsScope='local isolated testing only; not approved for redistribution',humanListening='NOT VERIFIED',outputCapture='NOT VERIFIED',encoding='lameenc 1.8.5 MPEG mono 64kbps',timebase='source PCM milliseconds; MP3 encoder delay must be calibrated before output-boundary acceptance',assets=assets)
(OUT/'manifest.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n');(ROOT/'docs/handoff/evidence/phase10c1/audio-fixtures.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
print('Generated and decoded',len(assets),'original MP3 fixtures')
