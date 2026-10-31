#!/usr/bin/env python3
"""Offline acoustic edge estimator. Reads real PCM; does not substitute element event timestamps."""
import array
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAPTURES = ROOT / '.local/phase10c1/c01-probe/captures'


def read(name):
    data = array.array('f')
    data.frombytes((CAPTURES / name).read_bytes())
    return data


def envelope(samples, sample_rate=48000):
    count = sample_rate // 1000
    real = [math.cos(2 * math.pi * 7000 * i / sample_rate) for i in range(count)]
    imag = [math.sin(2 * math.pi * 7000 * i / sample_rate) for i in range(count)]
    result = []
    for start in range(0, len(samples) - count, count):
        row = samples[start:start + count]
        result.append(math.hypot(sum(x*y for x, y in zip(row, real)), sum(x*y for x, y in zip(row, imag))) * 2 / count)
    # Equal centred smoothing on reference and output suppresses carrier/WSOLA ripple.
    return [sum(result[max(0,i-5):min(len(result),i+6)]) / len(result[max(0,i-5):min(len(result),i+6)]) for i in range(len(result))]


def score(a, b):
    n = len(a)
    ax, bx = sum(a) / n, sum(b) / n
    aa = sum((x - ax)**2 for x in a)
    bb = sum((x - bx)**2 for x in b)
    return sum((x-ax)*(y-bx) for x, y in zip(a, b)) / math.sqrt(max(1e-30, aa * bb))


def fit(a, b, astart, expected, rate=1, length=180, radius=100):
    left = a[int(astart):int(astart) + length]
    matches = []
    for step in range(-radius * 2, radius * 2 + 1):
        start = expected + step / 2
        indices = [round(start + k * rate) for k in range(length)]
        if min(indices) < 0 or max(indices) >= len(b):
            continue
        right = [b[i] for i in indices]
        matches.append((score(left, right), start))
    correlation, best = max(matches)
    alternative = max((v for v, p in matches if abs(p-best)>30),default=-1)
    return dict(correlation=correlation, matchedStartMs=best, windowStartMs=int(astart), lengthMs=length,
                alternativeOutside30Ms=alternative)


def joint_fit(signal, reference, anchors, rate, length, radius=120):
    windows=[(signal[int(at):int(at)+length],expected) for at,expected in anchors]
    matches=[]
    for step in range(-radius*2,radius*2+1):
        offset=step/2
        scores=[]
        for left,expected in windows:
            indices=[round(expected+offset+k*rate) for k in range(length)]
            if min(indices)<0 or max(indices)>=len(reference):
                break
            scores.append(score(left,[reference[i] for i in indices]))
        if len(scores)==len(windows):
            matches.append((sum(scores)/len(scores),offset))
    correlation,offset=max(matches)
    alternative=max(s for s,position in matches if abs(position-offset)>30)
    return dict(offsetMediaMs=offset,correlation=correlation,alternativeOutside30Ms=alternative,
                peakMargin=correlation-alternative,windows=len(windows),windowLengthMs=length)


def bursts(samples, threshold=.004):
    energy = [math.sqrt(sum(x*x for x in samples[k:k+48])/48) for k in range(0,len(samples)-48,48)]
    edges = []
    begin = None
    for i, value in enumerate(energy + [0]):
        if value > threshold and begin is None:
            begin = i
        elif value <= threshold and begin is not None:
            if i-begin > 40:
                edges.append((begin,i))
            begin = None
    return edges


def inspect(name, rate, start_ms, end_ms):
    raw = read(name + '.f32')
    signal = envelope(raw)
    reference = envelope(read('reference-shared-' + str(rate) + '.f32'))
    decoded = envelope(read('decoded-c1-shared-v1-a1.f32'))
    reference_onset = bursts(read('reference-shared-' + str(rate) + '.f32'))[0][0]
    decoded_onset = bursts(read('decoded-c1-shared-v1-a1.f32'))[0][0]
    origin = reference_onset - decoded_onset / rate
    mapping = []
    for source_ms in (start_ms + 200, end_ms - 200):
        at = int(origin + source_ms / rate)
        mapping.append(fit(reference, decoded, at, source_ms, rate=rate))
    rows = []
    for begin, end in bursts(raw):
        if end-begin < (end_ms-start_ms)/rate*.7:
            continue
        early = fit(signal, reference, begin+100, origin+start_ms/rate+100)
        late = fit(signal, reference, end-280, origin+end_ms/rate-280)
        rows.append(dict(begin=begin,end=end,early=early,late=late,
                         startEstimateMs=(early['matchedStartMs']-100-origin)*rate-start_ms,
                         endEstimateMs=(late['matchedStartMs']+280-origin)*rate-end_ms))
    return dict(mapping=mapping,origin=origin,rows=rows)


if __name__ == '__main__':
    import sys
    print(json.dumps(inspect(sys.argv[1],float(sys.argv[2]),float(sys.argv[3]),float(sys.argv[4])),indent=2))
