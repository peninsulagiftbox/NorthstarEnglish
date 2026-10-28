#!/usr/bin/env python3
"""Self-authored sine-wave MP3 for isolated functional decoding/playback, not speech."""
import array
import hashlib
import json
import math
from pathlib import Path
import subprocess
import lameenc
root=Path(__file__).resolve().parents[1]
out=root/'.local/phase10b2/audio';out.mkdir(parents=True,exist_ok=True)
rate=24000
pcm=array.array('h',(int(3500*math.sin(2*math.pi*440*i/rate)*min(1,i/400,(rate*2-i)/400)) for i in range(rate*2)))
encoder=lameenc.Encoder();encoder.set_bit_rate(64);encoder.set_in_sample_rate(rate);encoder.set_channels(1);encoder.set_quality(2)
raw=encoder.encode(pcm.tobytes())+encoder.flush();mp3=out/'original-test-tone.mp3';mp3.write_bytes(raw)
p=subprocess.run(['afconvert','-f','WAVE','-d','LEI16',str(mp3),str(out/'decoded.wav')],capture_output=True)
assert p.returncode==0,p.stderr.decode()
import wave
with wave.open(str(out/'decoded.wav')) as w:
    assert w.getnframes()>rate and w.getnchannels()==1
    duration=w.getnframes()/w.getframerate()
record=dict(tool='lameenc',version='1.8.5',textSource='self-authored Java test fixture',audioSource='self-authored 440Hz PCM sine wave, mathematical synthesis; no speech, no third-party recording',usage='isolated decoding and player test only; not a pronunciation demonstration',mp3Bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),decodeCommand=['afconvert','-f','WAVE','-d','LEI16',str(mp3),str(out/'decoded.wav')],decodeExitCode=p.returncode,decodedSeconds=duration)
(root/'docs/handoff/evidence/phase10b2/audio-fixture.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
print('Original test tone MP3 encoded and decoded successfully')
