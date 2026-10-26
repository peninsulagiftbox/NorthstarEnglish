#!/usr/bin/env python3
"""Read-only, exact table/column/value and optional media check against a private snapshot."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import urllib.parse
import urllib.request
import local


def payload(envelope):
    raw = envelope['payloadJson']
    if envelope['format'] != 'northstar.snapshot.v1' or hashlib.sha256(raw.encode()).hexdigest() != envelope['sha256']:
        raise ValueError('Snapshot checksum/format mismatch')
    data = json.loads(raw)
    if data['project'] != local.IDENTITY or data['owner'] != 'local':
        raise ValueError('Snapshot project/owner mismatch')
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('snapshot', type=Path)
    parser.add_argument('--api', default='http://127.0.0.1:8085')
    parser.add_argument('--media', action='store_true')
    parser.add_argument('--save-current', type=Path, help='create-only 0600 snapshot for the next restart check')
    args = parser.parse_args()
    url = urllib.parse.urlparse(args.api)
    if url.scheme != 'http' or url.hostname not in ('127.0.0.1', 'localhost') or url.path not in ('', '/') or url.username or url.query or url.fragment:
        raise ValueError('Loopback API required')
    base = args.api.rstrip('/') + '/api/v1'
    with urllib.request.urlopen(base + '/health', timeout=30) as response:
        health = json.load(response)
    if health.get('project') != local.IDENTITY or health.get('status') != 'UP':
        raise ValueError('API identity/health mismatch')
    expected = payload(json.loads(args.snapshot.read_text()))
    with urllib.request.urlopen(base + '/data/export', timeout=60) as response:
        current = json.load(response)
    actual = payload(current)
    if expected['schemaVersion'] != actual['schemaVersion']:
        raise ValueError('Schema version mismatch')
    different = sorted(k for k in expected['tables'].keys() | actual['tables'].keys()
                       if expected['tables'].get(k) != actual['tables'].get(k))
    if different:
        raise ValueError('Changed tables: ' + ', '.join(different))
    media_count = 0
    if args.media:
        data = actual['tables']['personal_recording']
        for values in data['rows']:
            row = dict(zip(data['columns'], values))
            if row['status'] != 'ready':
                continue
            with urllib.request.urlopen(base + '/recordings/' + row['id'] + '/audio', timeout=30) as response:
                content = response.read(8388609)
            if len(content) != int(row['byte_size']) or hashlib.sha256(content).hexdigest() != row['sha256']:
                raise ValueError('Media checksum/size mismatch')
            media_count += 1
    if args.save_current:
        with os.fdopen(os.open(args.save_current, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w') as output:
            json.dump(current, output, ensure_ascii=False)
    print(f'PASS: {len(actual["tables"])} tables exactly match; media checked={media_count}; no data written to API')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        # Do not echo driver responses, raw learning text, or connection configuration.
        raise SystemExit(str(error) if isinstance(error, ValueError) else type(error).__name__)
