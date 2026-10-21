#!/usr/bin/env python3
"""Grant only checkpoint writes after a verified V003 migration; preserve all data."""
import subprocess
import local


def grant(env):
    local.verify_container(env)
    def sql(text):
        result = subprocess.run(['docker', 'exec', '-i', 'northstar-english-mysql-01', 'sh', '-c',
                                 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" exec mysql -uroot -N'],
                                input=text, text=True, capture_output=True, env=env)
        if result.returncode:
            raise RuntimeError('恢复点权限核对失败；未输出连接凭据，请检查本项目 MySQL。')
        return result.stdout.strip()
    for schema in ('northstar_english', 'northstar_phase01_test'):
        if sql(f'SELECT project_key FROM {schema}.project_identity;') != local.IDENTITY:
            raise RuntimeError('数据库项目身份不符，拒绝授权')
        exists = sql(f"SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='{schema}' AND table_name='study_resume';")
        if exists == '0':
            print(f'{schema}: V003 尚未执行，保留现有权限。')
            continue
        if sql(f"SELECT COUNT(*) FROM {schema}.flyway_schema_history WHERE version='003' AND success=1;") != '1':
            raise RuntimeError('未发现成功的 V003，拒绝授权')
        sql(f"GRANT INSERT, UPDATE ON {schema}.study_resume TO 'northstar_app'@'%';")
        print(f'{schema}: PASS，仅授予 study_resume INSERT/UPDATE；未修改数据。')


if __name__ == '__main__':
    grant(local.environment())
