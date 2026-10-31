#!/usr/bin/env python3
"""Build private marked copies of original fixtures and serve them to the unchanged isolated player."""
import argparse
import array
import hashlib
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import subprocess
import wave
import math

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / '.local/phase10c1/c01-probe'
ASSETS = {'c1-shared-v1-a1': 'shared-v1', 'c1-independent-v1-a1': 'independent-1',
          'c1-independent-v1-a2': 'independent-6', 'c1-independent-v1-a3': 'independent-12'}


def build():
    import lameenc
    FOLDER.mkdir(exist_ok=False)
    fixtures = json.loads((ROOT / '.local/phase10c1/audio/manifest.json').read_text())
    rows = []
    for asset_id, name in ASSETS.items():
        original = ROOT / '.local/phase10c1/audio' / (name + '.wav')
        with wave.open(str(original)) as source:
            rate = source.getframerate()
            pcm = array.array('h', source.readframes(source.getnframes()))
        # A continuous high-frequency probe makes silence on either side of a boundary observable.
        pcm.extend(array.array('h', [0]) * (rate // 2))
        state = 173
        values = []
        for i in range((len(pcm) + 239) // 240):
            state = (1664525 * state + 1013904223) & 0xffffffff
            values.append(0.4 + 0.6 * (state >> 16) / 65535)
        for i in range(len(pcm)):
            carrier = int(8000 * values[i // 240] * math.sin(2 * math.pi * 7000 * i / rate))
            pcm[i] = max(-32768, min(32767, int(pcm[i] * 0.65) + carrier))
        wav = FOLDER / (name + '.wav')
        with wave.open(str(wav), 'wb') as target:
            target.setnchannels(1)
            target.setsampwidth(2)
            target.setframerate(rate)
            target.writeframes(pcm.tobytes())
        encoder = lameenc.Encoder()
        encoder.set_bit_rate(128)
        encoder.set_in_sample_rate(rate)
        encoder.set_channels(1)
        encoder.set_quality(2)
        encoded = encoder.encode(pcm.tobytes()) + encoder.flush()
        (FOLDER / (name + '.mp3')).write_bytes(encoded)
        rows.append(dict(assetId=asset_id, name=name, sourceSha256=hashlib.sha256(original.read_bytes()).hexdigest(),
                         wavSha256=hashlib.sha256(wav.read_bytes()).hexdigest(),
                         mp3Sha256=hashlib.sha256(encoded).hexdigest(), sampleRate=rate,
                         sourceFrames=len(pcm), segments=next(a['segments'] for a in fixtures['assets'] if a['name'] == name)))
    (FOLDER / 'manifest.json').write_text(json.dumps(dict(
        purpose='Measurement-only stimulus copies. Original files/database unchanged; not content publication.',
        probe='7kHz carrier; seeded 10ms random amplitude chips; original PCM attenuated 0.65; 500ms tail',
        assets=rows), indent=2) + '\n')


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        asset = self.path.split('?', 1)[0].split('/')[-1]
        if self.path.startswith('/api/v1/audio/') and asset in ASSETS:
            data = (FOLDER / (ASSETS[asset] + '.mp3')).read_bytes()
            total = len(data)
            start, end = 0, total - 1
            requested = self.headers.get('Range')
            if requested:
                left, right = requested.removeprefix('bytes=').split('-', 1)
                if left:
                    start = int(left)
                    end = min(int(right), end) if right else end
                else:
                    start = max(0, total - int(right))
                if start > end or start >= total:
                    self.send_response(416)
                    self.send_header('Content-Range', f'bytes */{total}')
                    self.end_headers()
                    return
                data = data[start:end + 1]
            self.send_response(206 if requested else 200)
            self.send_header('Content-Type', 'audio/mpeg')
            self.send_header('Accept-Ranges', 'bytes')
            self.send_header('Cache-Control', 'no-store')
            if requested:
                self.send_header('Content-Range', f'bytes {start}-{end}/{total}')
            self.send_header('X-C01-Measurement-Stimulus', hashlib.sha256(data).hexdigest())
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        elif self.path == '/__c01/manifest':
            data = (FOLDER / 'manifest.json').read_bytes()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        else:
            self.forward()

    def do_POST(self):
        if self.path.startswith('/__c01/save/'):
            if self.headers.get('Origin') != 'http://127.0.0.1:3185':
                self.send_error(403)
                return
            name = self.path.rsplit('/', 1)[-1]
            if not name or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-._' for c in name):
                self.send_error(400)
                return
            data = self.rfile.read(int(self.headers['Content-Length']))
            target = FOLDER / 'captures' / name
            target.parent.mkdir(exist_ok=True)
            with target.open('xb') as stream:
                stream.write(data)
            self.send_response(201)
            self.end_headers()
        else:
            self.forward()

    def do_PUT(self):
        self.forward()

    def do_HEAD(self):
        self.forward()

    def forward(self):
        connection = http.client.HTTPConnection('127.0.0.1', 3175, timeout=30)
        try:
            body = self.rfile.read(int(self.headers.get('Content-Length', 0)))
            headers = dict(self.headers)
            # Preserve the isolated application's existing write-origin checks.
            if headers.get('Origin') == 'http://127.0.0.1:3185':
                headers['Origin'] = 'http://127.0.0.1:3175'
            connection.request(self.command, self.path, body or None, headers)
            response = connection.getresponse()
            data = response.read()
            self.send_response(response.status)
            for key, value in response.getheaders():
                if key.lower() not in {'content-length', 'transfer-encoding', 'connection'}:
                    self.send_header(key, value)
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            if self.command != 'HEAD':
                self.wfile.write(data)
        finally:
            connection.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['build', 'serve'])
    options = parser.parse_args()
    if options.action == 'build':
        build()
    else:
        ThreadingHTTPServer(('127.0.0.1', 3185), Handler).serve_forever()
