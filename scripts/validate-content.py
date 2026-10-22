#!/usr/bin/env python3
"""Validate versioned package without reading or executing the prototype."""
import argparse
import importlib.util
import json
from pathlib import Path

spec = importlib.util.spec_from_file_location('extract_demo', Path(__file__).with_name('extract-demo.py'))
extract = importlib.util.module_from_spec(spec)
spec.loader.exec_module(extract)


def validate(root):
    manifest = json.loads((root / 'manifest.json').read_text())
    raw = (root / 'lesson.json').read_bytes()
    assert extract.digest(raw) == manifest['lessonSha256'], 'Lesson digest mismatch'
    lesson = json.loads(raw)
    assert lesson['id'] == manifest['lessonId'] == 'demo-01'
    assert lesson['versionId'] == manifest['versionId'] == f"demo-01-v{lesson['version']}"
    assert lesson['bookId'] is None and not lesson['releaseReady'] and not manifest['releaseReady']
    assert len(lesson['sentences']) == len(manifest['audioAssets']) == 10
    assert len(manifest['books']) == 4 and all(b['availability'] == 'catalog_only' for b in manifest['books'])
    all_ids = [i['id'] for key in ('sentences', 'vocabulary', 'exercises') for i in lesson[key]]
    assert len(all_ids) == len(set(all_ids)), 'Duplicate stable ID'
    sentence_ids = {s['id'] for s in lesson['sentences']}
    for item in lesson['vocabulary'] + lesson['exercises']:
        assert item['sentenceIds'] and set(item['sentenceIds']) <= sentence_ids, 'Cross-lesson source'
        if 'options' in item:
            assert item['answerKey'] in {o['id'] for o in item['options']}
    licenses = {item['id'] for item in manifest['licenses']}
    for number, (sentence, asset) in enumerate(zip(lesson['sentences'], manifest['audioAssets']), 1):
        path = root / asset['storageKey']
        assert asset['storageKey'] == f'audio/{number:02}.mp3' and path.resolve().is_relative_to(root.resolve())
        assert sentence['audioAssetId'] == asset['id'] and sentence['sequence'] == number
        assert asset['licenseId'] in licenses
        actual = extract.inspect_mp3(path)
        assert all(actual[key] == asset[key] for key in actual), 'Audio metadata/hash mismatch'
        assert sentence['startMs'] == 0 and sentence['endMs'] == actual['durationMs']
        assert all(sentence[key].strip() for key in ('speaker', 'text', 'translation', 'explanation', 'focus'))
    assert {p.name for p in (root / 'audio').iterdir()} == {f'{n:02}.mp3' for n in range(1, 11)}
    print('PASS: package IDs, source links, 4 catalog-only books, 10 audio hashes/MIME/sizes/decoded durations')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('root', nargs='?', type=Path, default=extract.ROOT / 'content/demo-01/v1')
    validate(parser.parse_args().root)
