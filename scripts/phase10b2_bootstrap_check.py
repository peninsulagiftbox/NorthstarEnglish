#!/usr/bin/env python3
"""Verify the documented one-shot non-web initializer only in a new schema on the owned test instance."""
import json
import phase10b2 as r
import phase10b2_verify as verify

c,env=verify.setup()
schema='northstar_restore_20261028114500'
query="CREATE DATABASE "+schema+" CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci; CREATE TABLE "+schema+".project_identity (project_key VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,created_at DATETIME(3) NOT NULL DEFAULT (UTC_TIMESTAMP(3))); INSERT INTO "+schema+".project_identity(project_key) VALUES ('northstar-english-local-v1'); GRANT SELECT ON "+schema+".* TO 'northstar_app'@'%'; GRANT SELECT,INSERT,UPDATE,DELETE,CREATE,ALTER,INDEX,REFERENCES ON "+schema+".* TO 'northstar_migrator'@'%';"
c.sql('empty',query)
env.update(DB_NAME=schema,NORTHSTAR_ALLOW_RESTORE_DB='true')
argv=[str(c.JAVA),'-jar',str(c.PATCHED_JAR),'--spring.main.web-application-type=none','--northstar.initialize-content=true']
try:
    r.record('nonweb-empty-initialization',argv,env=env)
    original_sql=c.sql
    def scoped(role,query,**kwargs):return original_sql(role,'USE '+schema+';'+query,**kwargs)
    c.sql=scoped
    before=c.snapshot('empty','nonweb-before-refused-repeat')
    r.record('nonweb-existing-initialization-refused',argv,env=env,expected=(1,))
    c.compare(before,c.snapshot('empty','nonweb-after-refused-repeat'))
    c.save(r.OUT/'nonweb-bootstrap.json',dict(status='PASS',newSchema=schema,initializationExitCode=0,repeatedInitializationExitCode=1,allTablesExactAfterRefusal=True,webServerStarted=False,onlyOwnedIsolatedInstance=True,jarSha256=c.digest(c.PATCHED_JAR)))
finally:
    c.stop('empty');c.save(c.OUT/'nonweb-bootstrap-commands.json',c.RECORDS)
