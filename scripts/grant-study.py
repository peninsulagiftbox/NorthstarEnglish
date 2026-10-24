#!/usr/bin/env python3
"""Grant only phase-specific writes after verified migrations; preserve all data."""
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
        print(f'{schema}: PASS，study_resume INSERT/UPDATE；未修改数据。')
        if sql(f"SELECT COUNT(*) FROM {schema}.flyway_schema_history WHERE version='004' AND success=1;") == '1':
            for table in ('exercise_attempt', 'learning_evidence', 'study_event', 'review_source'):
                sql(f"GRANT INSERT ON {schema}.{table} TO 'northstar_app'@'%';")
            for table in ('command_receipt', 'study_stage', 'exercise_draft', 'review_item'):
                sql(f"GRANT INSERT, UPDATE ON {schema}.{table} TO 'northstar_app'@'%';")
            print(f'{schema}: PASS，V004 最小写权限；内容与历史证据保持只读。')
        if sql(f"SELECT COUNT(*) FROM {schema}.flyway_schema_history WHERE version='005' AND success=1;") == '1':
            sql(f"GRANT INSERT ON {schema}.reading_answer TO 'northstar_app'@'%';")
            for table in ('vocabulary_favorite', 'reading_progress'):
                sql(f"GRANT INSERT, UPDATE ON {schema}.{table} TO 'northstar_app'@'%';")
            print(f'{schema}: PASS，V005 收藏/阅读最小写权限；不授权改写历史。')

        if sql(f"SELECT COUNT(*) FROM {schema}.flyway_schema_history WHERE version='006' AND success=1;") == '1':
            for table in ('writing_revision', 'recording_observation'):
                sql(f"GRANT INSERT ON {schema}.{table} TO 'northstar_app'@'%';")
            for table in ('writing_draft', 'personal_recording', 'practice_progress'):
                sql(f"GRANT INSERT, UPDATE ON {schema}.{table} TO 'northstar_app'@'%';")
            print(f'{schema}: PASS，V006 录音/写作最小写权限；不可变版本不可改写。')

        if sql(f"SELECT COUNT(*) FROM {schema}.flyway_schema_history WHERE version='007' AND success=1;") == '1':
            for table in ('quiz_run', 'quiz_answer', 'review_result'):
                sql(f"GRANT INSERT ON {schema}.{table} TO 'northstar_app'@'%';")
            sql(f"GRANT INSERT, UPDATE ON {schema}.quiz_progress TO 'northstar_app'@'%';")
            print(f'{schema}: PASS，V007 测验/复习最小写权限；历史只追加。')


if __name__ == '__main__':
    grant(local.environment())
