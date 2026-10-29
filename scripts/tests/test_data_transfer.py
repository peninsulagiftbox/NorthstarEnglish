import importlib.util
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
spec=importlib.util.spec_from_file_location('data_transfer',Path(__file__).resolve().parents[1]/'data-transfer.py')
transfer=importlib.util.module_from_spec(spec)
spec.loader.exec_module(transfer)

class DataTransferTests(unittest.TestCase):
    def test_snapshot_hash_version_and_owner_are_checked(self):
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'learning.json'
            payload={'project':transfer.local.IDENTITY,'owner':'local','schemaVersion':'008'}
            for owner,version,valid in [('local','008',True),('local','009.04',True),('local','009.05',True),('local','009.14',True),('local','009.15',True),('foreign','008',False),('local','999',False),('local','009.03',False)]:
                payload.update(owner=owner,schemaVersion=version)
                raw=json.dumps(payload)
                data={'format':'northstar.snapshot.v1','sha256':hashlib.sha256(raw.encode()).hexdigest(),'payloadJson':raw}
                path.write_text(json.dumps(data))
                if valid:self.assertEqual(payload,transfer.load_snapshot(path)[1])
                else:
                    with self.assertRaises(ValueError):transfer.load_snapshot(path)
            data['sha256']='0'*64
            path.write_text(json.dumps(data))
            with self.assertRaises(ValueError):transfer.load_snapshot(path)
    def test_sql_values_are_hex_encoded_including_quotes_and_unicode(self):
        text="'; DROP DATABASE northstar_english; -- 花园\n$(secret)"
        literal=transfer.literal(text)
        self.assertEqual(text,bytes.fromhex(literal.split("'")[1]).decode())
        self.assertEqual('NULL',transfer.literal(None))
        with self.assertRaises(ValueError):transfer.literal({'sql':'unsafe'})
