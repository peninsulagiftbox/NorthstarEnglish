#!/usr/bin/env python3
"""Recompute a source/afconvert marker diagnostic, NOT Chrome boundary calibration."""
import array
import hashlib
import json
import math
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / '.local/phase10c1/audio'
OUT = ROOT / 'docs/handoff/evidence/phase10c1/reacceptance'


def marker(path, expected):
    with wave.open(str(path)) as source:
        assert source.getnchannels() == 1 and source.getsampwidth() == 2
        rate = source.getframerate()
        samples = array.array('h', source.readframes(source.getnframes()))
    length, hop = rate // 100, rate // 1000
    window = [complex(math.cos(2 * math.pi * 1200 * i / rate), -math.sin(2 * math.pi * 1200 * i / rate)) for i in range(length)]
    values = []
    for start in range(max(0, int((expected - .1) * rate)), min(len(samples) - length, int((expected + .2) * rate)), hop):
        amplitude = abs(sum(samples[start + i] * window[i] for i in range(length))) * 2 / length
        values.append((start, amplitude))
    peak = max(amplitude for _, amplitude in values)
    start = next(start for start, amplitude in values if amplitude > peak * .3)
    return dict(onsetWindowMs=start * 1000 / rate, peakAmplitude=peak, sampleRate=rate,
                frameLengthMs=length * 1000 / rate, hopMs=hop * 1000 / rate)


def main():
    measurements = []
    for name, expected in [('shared-v1', .8), ('shared-v2', 1.1), ('independent-1', 0), ('independent-6', 0), ('independent-12', 0)]:
        source = SOURCE / (name + '.wav')
        decoded = SOURCE / (name + '-decoded.wav')
        first, second = marker(source, expected), marker(decoded, expected)
        measurements.append(dict(asset=name, source=first, decoded=second,
                                 relativeMarkerShiftMs=second['onsetWindowMs'] - first['onsetWindowMs'],
                                 sourceSha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                                 decodedSha256=hashlib.sha256(decoded.read_bytes()).hexdigest()))
    value = dict(status='DIAGNOSTIC ONLY',
                 method='10ms coherent 1200Hz amplitude window,1ms hop,30% peak threshold; independent source onset left-censored at 0ms; macOS afconvert decoder, not Chrome output calibration',
                 measurements=measurements, uncertaintyMs=None, acceptanceStatus='NOT VERIFIED')
    (OUT / 'mp3-marker-diagnostic.json').write_text(json.dumps(value, indent=2) + '\n')
    print('5 source/afconvert marker diagnostics computed; Chrome calibration remains NOT VERIFIED')


if __name__ == '__main__':
    main()
