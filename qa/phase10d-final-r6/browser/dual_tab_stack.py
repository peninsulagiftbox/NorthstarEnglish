import json
import subprocess

from browser_stack import wait_health
from run import q


def main():
    api = q.start_api()
    web = None
    try:
        web = subprocess.Popen([q.NODE + '/node', str(q.ROOT / 'node_modules/next/dist/bin/next'),
                                'start', '--hostname', '127.0.0.1', '--port', str(q.WEB_PORT)],
                               cwd=q.SOURCE / 'apps/web', env=q.env(),
                               stdout=(q.PRIVATE / 'dual-tab-web.log').open('xb'), stderr=subprocess.STDOUT)
        wait_health(web)
        q.run('r6-dual-tab-browser', [q.NODE + '/node', q.TOOLS / 'dual_tab.cjs'],
              env=q.env(), timeout=180)
        result = json.loads((q.OUT / 'dual-tab-result.json').read_text())
        for key in ('first', 'second'):
            card = result[key]
            count = int(q.sql(f"SELECT COUNT(*) FROM concept_review_result WHERE card_id='{card['id']}'",
                              label='r6-dual-tab-db-result-' + key))
            version = int(q.sql(f"SELECT row_version FROM concept_review_card WHERE id='{card['id']}'",
                                label='r6-dual-tab-db-version-' + key))
            assert count == 1 and version == card['initialVersion'] + 1, (key, count, version)
        q.save('dual-tab-db-audit.json', dict(status='PASS', cards=[result['first']['id'], result['second']['id']],
                                              oneResultAndOneVersionAdvanceEach=True))
    finally:
        if web:
            q.stop(web)
        q.stop(api)


if __name__ == '__main__':
    main()
