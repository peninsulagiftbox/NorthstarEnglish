import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).parents[1]))
import recovery_mysql

spec = importlib.util.spec_from_file_location('check_snapshot', Path(__file__).parents[1] / 'check-snapshot.py')
snapshot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(snapshot)


class RecoveryGuardTests(unittest.TestCase):
    def test_recovery_cannot_adopt_foreign_public_or_wrong_volume_container(self):
        item = {'Config': {'Labels': {'local.northstar.project': 'northstar-english-local-v1', 'local.northstar.role': recovery_mysql.ROLE}},
                'HostConfig': {'PortBindings': {'3306/tcp': [{'HostIp': '127.0.0.1', 'HostPort': '3310'}]}},
                'Mounts': [{'Name': recovery_mysql.VOLUME, 'Destination': '/var/lib/mysql'}]}
        recovery_mysql.check_identity(item, 3310)
        for change in ('project', 'role', 'public', 'port', 'volume'):
            invalid = copy.deepcopy(item)
            if change in ('project', 'role'):
                invalid['Config']['Labels']['local.northstar.' + change] = 'unrelated'
            elif change == 'public':
                invalid['HostConfig']['PortBindings']['3306/tcp'][0]['HostIp'] = '0.0.0.0'
            elif change == 'port':
                invalid['HostConfig']['PortBindings']['3306/tcp'][0]['HostPort'] = '3308'
            else:
                invalid['Mounts'][0]['Name'] = 'existing_main_data'
            with self.subTest(change=change), self.assertRaises(RuntimeError):
                recovery_mysql.check_identity(invalid, 3310)

    def test_snapshot_check_rejects_checksum_and_foreign_ownership(self):
        def envelope(data):
            raw = json.dumps(data)
            return {'format': 'northstar.snapshot.v1', 'payloadJson': raw, 'sha256': hashlib.sha256(raw.encode()).hexdigest()}
        data = {'project': 'northstar-english-local-v1', 'owner': 'local'}
        self.assertEqual(data, snapshot.payload(envelope(data)))
        invalid = envelope(data)
        invalid['payloadJson'] += ' '
        with self.assertRaises(ValueError):
            snapshot.payload(invalid)
        with self.assertRaises(ValueError):
            snapshot.payload(envelope({**data, 'owner': 'another-user'}))
