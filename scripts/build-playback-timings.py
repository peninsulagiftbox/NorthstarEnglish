#!/usr/bin/env python3
"""Extract cached TTS word boundaries, bound to the published audio hashes. No network."""
import hashlib
import html
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def build():
    package = ROOT / 'content/demo-01/v2'
    lesson = json.loads((package / 'lesson.json').read_text())
    manifest = json.loads((package / 'manifest.json').read_text())
    records_path = ROOT / '.local/tts-evaluation/generation.json'
    records = json.loads(records_path.read_text())
    assets = {a['id']: a for a in manifest['audioAssets']}
    tracks = []
    for sentence in lesson['sentences']:
        asset = assets[sentence['audioAssetId']]
        record = next(r for r in records if r['group'] == 'edge-gb' and r['sequence'] == sentence['sequence'] and r['repetition'] is None and r['success'])
        assert record['text'] == sentence['text'], 'TTS text differs'
        original = (ROOT / '.local/tts-evaluation' / record['path']).read_bytes()
        assert hashlib.sha256(original).hexdigest() == asset['sha256']
        assert hashlib.sha256((package / asset['storageKey']).read_bytes()).hexdigest() == asset['sha256']
        words = [{'text': html.unescape(w['text']), 'startMs': w['offset'] / 10000, 'durationMs': w['duration'] / 10000} for w in record['metadata'] if w['type'] == 'WordBoundary']
        normalize = lambda s: re.findall(r"[a-z]+(?:'[a-z]+)?", s.lower())
        assert normalize(' '.join(w['text'] for w in words)) == normalize(sentence['text'])
        assert words and all(0 <= w['startMs'] < asset['durationMs'] and w['durationMs'] > 0 and w['startMs'] + w['durationMs'] <= asset['durationMs'] + 1 for w in words)
        assert all(a['startMs'] < b['startMs'] for a, b in zip(words, words[1:]))
        tracks.append({'sentenceId': sentence['id'], 'audioSha256': asset['sha256'], 'durationMs': asset['durationMs'], 'words': words})
    output = {'versionId': lesson['versionId'], 'source': 'edge-tts 7.3.1 WordBoundary from the same audio generation; service alignment, not manually corrected', 'sourceRecordSha256': hashlib.sha256(records_path.read_bytes()).hexdigest(), 'tracks': tracks}
    target = ROOT / 'apps/web/src/lib/media/demo-word-timings.json'
    target.write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n')
    print(f'Validated {len(tracks)} tracks / {sum(len(t["words"]) for t in tracks)} word boundaries; published audio unchanged.')


if __name__ == '__main__':
    build()
