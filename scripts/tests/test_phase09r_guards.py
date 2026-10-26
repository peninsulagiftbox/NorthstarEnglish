import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).parents[1]))
import phase09r


class AcceptanceGuardTests(unittest.TestCase):
    def test_refuses_wrong_container_identity_binding_and_volume(self):
        env={'MYSQL_PORT':'3311'}
        item={'Config':{'Labels':{'local.northstar.role':phase09r.ROLE+'-source','local.northstar.project':phase09r.local.IDENTITY}},
              'HostConfig':{'PortBindings':{'3306/tcp':[{'HostIp':'127.0.0.1','HostPort':'3311'}]}},
              'Mounts':[{'Name':phase09r.CONTAINERS['source']+'-data','Destination':'/var/lib/mysql'}]}
        with patch.object(phase09r,'environment',return_value=env):
            with patch.object(subprocess,'run',return_value=subprocess.CompletedProcess([],0,json.dumps([item]),'')):
                self.assertEqual(env,phase09r.verify())
            for defect in ('role','project','host','port','volume'):
                wrong=copy.deepcopy(item)
                if defect in ('role','project'): wrong['Config']['Labels']['local.northstar.'+defect]='foreign'
                elif defect in ('host','port'): wrong['HostConfig']['PortBindings']['3306/tcp'][0]['HostIp' if defect=='host' else 'HostPort']='0.0.0.0' if defect=='host' else '3308'
                else: wrong['Mounts'][0]['Name']='private-main-volume'
                with self.subTest(defect=defect),patch.object(subprocess,'run',return_value=subprocess.CompletedProcess([],0,json.dumps([wrong]),'')),self.assertRaises(RuntimeError):
                    phase09r.verify()

    def test_environment_rejects_main_port_collision(self):
        with patch.object(phase09r.local,'environment',return_value={'MYSQL_PORT':'3311','API_PORT':'8085','WEB_PORT':'3100'}), self.assertRaises(RuntimeError):
            phase09r.environment()

    def test_grant_rejects_private_schema_before_sql(self):
        with patch.object(phase09r,'sql') as sql,self.assertRaises(RuntimeError):
            phase09r.grant('source','northstar_english')
        sql.assert_not_called()
