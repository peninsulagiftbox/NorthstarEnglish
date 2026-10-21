#!/usr/bin/env python3
"""Extract only literal data; never execute prototype JavaScript."""
import argparse
import ast
import base64
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'Northstar_English_Codex/references/phase1'
HTML = 'english_lab_desktop_prototype.html'
EXPECTED_SOURCE = '0debbd92494b34f9905e38386fe57fc833170c8dfd2ed50e1fa1cc5a4623306f'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def literal_array(source, name):
    match = re.search(r'const ' + re.escape(name) + r'=(\[.*?\]);', source)
    if not match:
        raise ValueError(f'Missing literal array: {name}')
    raw = match.group(1)
    # The frozen prototype uses JSON or single-quoted string/number dictionaries.
    # literal_eval accepts data only, never calls, expressions, or JS execution.
    raw = re.sub(r'([{,])\s*([a-zA-Z]+)\s*:', r'\1"\2":', raw)
    value = ast.literal_eval(raw)
    if not isinstance(value, list):
        raise ValueError('Expected array')
    return value


def inspect_mp3(path):
    data = path.read_bytes()
    if not 1000 < len(data) < 1_000_000 or not (data.startswith(b'ID3') or data[:2] in (b'\xff\xfb', b'\xff\xf3', b'\xff\xf2')):
        raise ValueError('Invalid MP3 header or size')
    result = subprocess.run(['afinfo', str(path)], check=True, capture_output=True, text=True).stdout
    duration = re.search(r'estimated duration:\s*([\d.]+) sec', result)
    if not duration or 'mp3' not in result.lower():
        raise ValueError('MP3 decoder did not recognize resource')
    milliseconds = round(float(duration.group(1)) * 1000)
    if not 500 < milliseconds < 30000:
        raise ValueError('Unexpected decoded duration')
    return {'mimeType': 'audio/mpeg', 'byteSize': len(data), 'durationMs': milliseconds, 'sha256': digest(data)}


def write_frozen(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_bytes() != data:
        raise ValueError(f'Refuse to overwrite changed frozen content: {path.name}; create a new version')
    path.write_bytes(data)


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode()


def extract(output):
    raw = (SOURCE / HTML).read_bytes()
    if digest(raw) != EXPECTED_SOURCE:
        raise ValueError('Prototype differs from reviewed source')
    source = raw.decode()
    sentences, audio = literal_array(source, 'LESSONS'), literal_array(source, 'AUDIO_DATA')
    if len(sentences) != 10 or len(audio) != 10:
        raise ValueError('Expected exactly ten paired sentences/audio files')
    archive = ROOT / 'references/phase1'
    archived = []
    for path in sorted(SOURCE.iterdir()):
        if path.is_file():
            write_frozen(archive / path.name, path.read_bytes())
            archived.append({'file': path.name, 'sha256': digest(path.read_bytes())})
    assets = []
    for number, (sentence, uri) in enumerate(zip(sentences, audio), 1):
        prefix = 'data:audio/mpeg;base64,'
        if not uri.startswith(prefix):
            raise ValueError('Unexpected audio MIME')
        storage = f'audio/{number:02}.mp3'
        write_frozen(output / storage, base64.b64decode(uri[len(prefix):], validate=True))
        asset = {'id': f'demo-01-v1-a{number:02}', 'storageKey': storage, 'licenseId': 'demo-audio-v1',
                 'sourceKind': 'original_tts', **inspect_mp3(output / storage)}
        assets.append(asset)
        sentence.update(id=f'demo-01-v1-s{number:02}', stableKey=f's{number:02}', sequence=number,
                        audioAssetId=asset['id'], startMs=0, endMs=asset['durationMs'])
        sentence['explanation'] = sentence.pop('explain')
    vocab = []
    for item in literal_array(source, 'VOCAB'):
        key = item['en'].replace(' ', '-')
        vocab.append({'id': f'demo-01-v1-kp-{key}', 'term': item['en'], 'meaning': item['zh'],
                      'example': item['ex'], 'sentenceIds': [sentences[item['point']]['id']]})
    exercises = []
    for number, item in enumerate(literal_array(source, 'QUIZ'), 1):
        exercise_id = f'demo-01-v1-quiz-{number:02}'
        options = [{'id': f'{exercise_id}-{chr(97+i)}', 'text': text} for i, text in enumerate(item['options'])]
        exercises.append({'id': exercise_id, 'kind': 'quiz_choice', 'prompt': item['q'], 'options': options,
                          'answerKey': options[item['right']]['id'], 'explanation': item['explain'],
                          'sentenceIds': [sentences[0 if number == 1 else 5]['id']]})
    # Read/write literals live inside HTML templates; require the reviewed text before freezing.
    reading = ['Next to the blue bench.', 'Inside the classroom.', 'Under a red table.']
    prompt = 'Where should Mia put the small plants?'
    writing = '写 2–3 句关于你在花园里帮忙的英文。'
    for text in [prompt, writing, *reading]:
        if text not in source:
            raise ValueError('Reviewed exercise literal changed')
    exercises.append({'id': 'demo-01-v1-reading-01', 'kind': 'reading_choice', 'prompt': prompt,
                      'options': [{'id': f'demo-01-v1-reading-01-{chr(97+i)}', 'text': t} for i, t in enumerate(reading)],
                      'answerKey': 'demo-01-v1-reading-01-a', 'sentenceIds': ['demo-01-v1-s06']})
    exercises.append({'id': 'demo-01-v1-writing-01', 'kind': 'writing_prompt', 'prompt': writing,
                      'targetExpressions': ['please', 'beside', 'I can'],
                      'sentenceIds': ['demo-01-v1-s05', 'demo-01-v1-s06', 'demo-01-v1-s09']})
    for sentence in sentences:
        exercises.append({'id': f"demo-01-v1-dictation-{sentence['stableKey']}", 'kind': 'dictation',
                          'prompt': '听音写句子', 'sentenceIds': [sentence['id']], 'answerKey': sentence['text']})
    lesson = {'id': 'demo-01', 'slug': 'the-neighborhood-garden', 'title': 'The Neighborhood Garden',
              'versionId': 'demo-01-v1', 'version': 1, 'kind': 'original_demo', 'bookId': None,
              'availability': 'available', 'usageScope': 'local_test_only', 'releaseReady': False,
              'licenseId': 'demo-text-v1', 'explanationLabel': '本地预置讲解',
              'sentences': sentences, 'vocabulary': vocab, 'exercises': exercises}
    lesson_data = json_bytes(lesson)
    write_frozen(output / 'lesson.json', lesson_data)
    licenses = []
    for medium in ('text', 'audio'):
        licenses.append({'id': f'demo-{medium}-v1', 'sourceType': 'original', 'medium': medium,
                         'owner': 'unknown', 'sourceRef': f'prototype:{EXPECTED_SOURCE}:{medium}',
                         'rightsScope': 'local_test_only; formal publication blocked pending review',
                         'territory': 'unknown', 'reviewStatus': 'pending_review', 'proofRef': None,
                         'generator': 'unknown', 'voice': 'unknown',
                         'declaration': '参考设计声明文本及讲解原创、音频本地合成用于功能测试；未取得独立授权凭据。'})
    books = [{'id': f'nce-book-{n}', 'catalogKey': f'nce-{n}', 'sequence': n,
              'title': f'新概念英语第{n}册', 'editionLabel': '1997 revised (catalog metadata only)',
              'availability': 'catalog_only', 'declaredLessonCount': count,
              'metadataSource': 'references/phase1/Northstar_English_Phase1_桌面Web详细设计与验收.md#P02'}
             for n, count in enumerate((144, 96, 60, 48), 1)]
    manifest = {'schemaVersion': 1, 'lessonId': lesson['id'], 'versionId': lesson['versionId'],
                'source': {'path': f'references/phase1/{HTML}', 'sha256': EXPECTED_SOURCE},
                'durationMethod': 'macOS afinfo MP3 decoder estimated duration, rounded to milliseconds; sentence-local timeline',
                'lessonSha256': digest(lesson_data), 'licenses': licenses, 'books': books, 'audioAssets': assets,
                'releaseReady': False}
    write_frozen(output / 'manifest.json', json_bytes(manifest))
    write_frozen(archive / 'archive-manifest.json', json_bytes(archived))
    print('PASS: frozen 10 sentences / 10 decoded MP3 files; rights pending_review; publication blocked')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=ROOT / 'content/demo-01/v1')
    extract(parser.parse_args().output)
