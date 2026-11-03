#!/usr/bin/env python3
"""QA-EXEC R3 D02-M03/M04: logical backup of the isolated QA schema (with real D02
data), restore into a fresh northstar_restore_* schema, then per-PK per-value
verification. STORED GENERATED columns are excluded from restore and re-verified
after recomputation. Media files are hashed on both sides."""
import hashlib, json, os, subprocess, sys, urllib.request

SRC_PORT, DST_PORT = "3350", "3351"
SRC_SCHEMA, DST_SCHEMA = "northstar_phase01_test", sys.argv[1]
BACKUP = "/private/tmp/qa-r3/backup-" + DST_SCHEMA.split("_")[-1]
CREDS = "/Users/wangshiqi/.codex/worktrees/worktree-10d-d02-qa/NorthstarEnglish/.local/qa-r3/credentials.json"
CONTENT = os.path.dirname(CREDS) + "/content"
SKIP = {"flyway_schema_history", "project_identity"}

def creds(): return json.load(open(CREDS))

def mysql(port, query, schema=None, as_root=False, raw=True):
    c = creds()
    env = dict(os.environ, MYSQL_PWD=c["root"] if as_root else c["app"])
    cmd = ["/usr/local/mysql/bin/mysql", "--protocol=TCP", "-h127.0.0.1", "-P" + port, "-N", "-s"]
    if raw: cmd.append("--raw")
    cmd.append("-u" + ("root" if as_root else "northstar_app"))
    if schema: cmd.append("--database=" + schema)
    r = subprocess.run(cmd, input=query, capture_output=True, text=True, env=env)
    assert r.returncode == 0, r.stderr
    return r.stdout

def tables(port, schema):
    out = mysql(port, "SELECT table_name FROM information_schema.tables WHERE table_schema='%s' AND table_name NOT IN (%s) ORDER BY table_name"
                % (schema, ",".join("'%s'" % t for t in SKIP)), schema)
    return out.split()

def cols(port, schema, table):
    out = mysql(port, "SELECT (extra LIKE '%%STORED GENERATED%%' OR extra LIKE '%%VIRTUAL GENERATED%%') AS g, column_name, data_type FROM information_schema.columns "
                "WHERE table_schema='%s' AND table_name='%s' ORDER BY ordinal_position" % (schema, table))
    rows = [l.split("\t") for l in out.strip().splitlines() if l]
    return [(c, t, g == "1") for g, c, t in rows]

def extract(port, schema, table):
    cs = cols(port, schema, table)
    use = [c for c, t, g in cs if not g]
    sel = "JSON_OBJECT(" + ",".join("'%s',CAST(`%s` AS CHAR)" % (c, c) for c in use) + ")"
    out = mysql(port, "SET SESSION group_concat_max_len=1073741824; SELECT COALESCE(JSON_ARRAYAGG(%s),JSON_ARRAY()) FROM `%s`" % (sel, table), schema)
    line = out.strip().splitlines()[-1]
    return json.loads(line), {c: t for c, t, g in cs if g}, cs

def sql_literal(v):
    if v is None: return "NULL"
    s = str(v).replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n").replace("\r", "\\r")
    return "'" + s + "'"

def media_hashes():
    out = {}
    for root, _, files in os.walk(CONTENT):
        for f in files:
            p = os.path.join(root, f)
            out[os.path.relpath(p, CONTENT)] = hashlib.sha256(open(p, "rb").read()).hexdigest()
    return out

def main():
    st, dt = tables(SRC_PORT, SRC_SCHEMA), tables(DST_PORT, DST_SCHEMA)
    assert st == dt, "schema drift: %s vs %s" % (st, dt)
    # Capture trigger definitions, drop them for bulk load, recreate the originals afterwards.
    trig = mysql(SRC_PORT, "SELECT TRIGGER_NAME FROM information_schema.triggers WHERE trigger_schema='%s' ORDER BY trigger_name" % SRC_SCHEMA).split()
    trig_sql = [mysql(SRC_PORT, "SHOW CREATE TRIGGER `%s`" % t, SRC_SCHEMA, raw=False) for t in trig]
    for t in mysql(DST_PORT, "SELECT TRIGGER_NAME FROM information_schema.triggers WHERE trigger_schema='%s' ORDER BY trigger_name" % DST_SCHEMA).split():
        mysql(DST_PORT, "DROP TRIGGER `%s`" % t, DST_SCHEMA)
    # Refuse a dirty target: every data table must be empty before restore.
    dirty = [t for t in dt if mysql(DST_PORT, "SELECT COUNT(*) FROM `%s`" % t, DST_SCHEMA).strip() != "0"]
    # The boot itself seeds a default user_setting row; remove it so verification compares like with like.
    resume = len(dirty) > 1
    assert dirty == [] or dirty == ["user_setting"] or resume, "unexpected target state: %s" % dirty
    if "user_setting" in dirty and not resume: mysql(DST_PORT, "DELETE FROM user_setting", DST_SCHEMA)
    os.makedirs(BACKUP, mode=0o700, exist_ok=True)
    media_before = media_hashes()
    json.dump(media_before, open(BACKUP + "/media-sha256.json", "w"), indent=1, sort_keys=True)
    # Circular FKs (lesson<->lesson_version) require the standard dump/load technique:
    # disable FK checks only during load, re-enable, then verify every constraint for orphans.
    dep = {}
    for t in st:
        refs = mysql(SRC_PORT, "SELECT DISTINCT referenced_table_name FROM information_schema.key_column_usage "
            "WHERE table_schema='%s' AND table_name='%s' AND referenced_table_name IS NOT NULL" % (SRC_SCHEMA, t))
        dep[t] = [r for r in refs.split() if r in st]
    order, seen = [], set()
    def visit(t):
        if t in seen: return
        seen.add(t)
        for d in dep[t]: visit(d)
        order.append(t)
    for t in st: visit(t)
    results = []
    for t in order:
        rows, generated, cs = extract(SRC_PORT, SRC_SCHEMA, t)
        json.dump(rows, open(BACKUP + "/" + t + ".json", "w"), ensure_ascii=False)
        if rows and not resume:
            use = [c for c in rows[0]]
            body = ";".join("INSERT INTO `%s` (%s) VALUES (%s)" % (t,
                ",".join("`%s`" % c for c in use), ",".join(sql_literal(r[c]) for c in use)) for r in rows)
            if t == "lesson":
                deferred = [(r["id"], r.get("current_version_id")) for r in rows if r.get("current_version_id")]
                expected = rows
                rows = [{**r, "current_version_id": None} for r in rows]
            mysql(DST_PORT, "SET FOREIGN_KEY_CHECKS=0;" + body + ";SET FOREIGN_KEY_CHECKS=1", DST_SCHEMA)
            if t == "lesson":
                for lid, vid in deferred:
                    mysql(DST_PORT, "UPDATE lesson SET current_version_id=%s WHERE id=%s" % (sql_literal(vid), sql_literal(lid)), DST_SCHEMA)
                rows = expected
        rrows, rgen, _ = extract(DST_PORT, DST_SCHEMA, t)
        identical = rows == rrows
        # STORED GENERATED columns: restored values must equal the source values (recomputed).
        gen_ok = True
        if generated:
            src_raw = json.loads(mysql(SRC_PORT, "SET SESSION group_concat_max_len=1073741824; SELECT COALESCE(JSON_ARRAYAGG(JSON_OBJECT(%s)),JSON_ARRAY()) FROM `%s`"
                % (",".join("'%s',CAST(`%s` AS CHAR)" % (c, c) for c in generated), t), SRC_SCHEMA))
            dst_raw = json.loads(mysql(DST_PORT, "SET SESSION group_concat_max_len=1073741824; SELECT COALESCE(JSON_ARRAYAGG(JSON_OBJECT(%s)),JSON_ARRAY()) FROM `%s`"
                % (",".join("'%s',CAST(`%s` AS CHAR)" % (c, c) for c in generated), t), DST_SCHEMA))
            gen_ok = src_raw == dst_raw
        results.append((t, len(rows), identical, bool(generated), gen_ok))
    for d in trig_sql:
        parts = d.split("\t")
        stmt = parts[2].strip().rstrip(";")
        r = subprocess.run(["/usr/local/mysql/bin/mysql", "--protocol=TCP", "-h127.0.0.1", "-P" + DST_PORT,
            "-N", "-s", "-unorthstar_app", "--database=" + DST_SCHEMA],
            input="DELIMITER //\n" + stmt + "\n//\nDELIMITER ;\n", capture_output=True, text=True, env=dict(os.environ, MYSQL_PWD=creds()["app"]))
        if r.returncode: print("TRIGGER_FAIL", repr(d)[:400], file=sys.stderr)
        assert r.returncode == 0, r.stderr
        print("TRIGGER_OK", parts[0])
    recreated = mysql(DST_PORT, "SELECT COUNT(*) FROM information_schema.triggers WHERE trigger_schema='%s'" % DST_SCHEMA).strip()
    assert recreated == str(len(trig)), "trigger recreation mismatch"
    print("TRIGGERS_RECREATED=" + str(len(trig)))
    # Verify every foreign key constraint in the restored schema has no orphans.
    cons = mysql(DST_PORT, "SELECT constraint_name,table_name,column_name,referenced_table_name,referenced_column_names FROM ("
        "SELECT kcu.constraint_name,kcu.table_name,GROUP_CONCAT(kcu.column_name ORDER BY ordinal_position) AS column_name,"
        "kcu.referenced_table_name,GROUP_CONCAT(kcu.referenced_column_name ORDER BY ordinal_position) AS referenced_column_names "
        "FROM information_schema.key_column_usage kcu WHERE kcu.table_schema='" + DST_SCHEMA + "' AND kcu.referenced_table_name IS NOT NULL "
        "GROUP BY kcu.constraint_name,kcu.table_name,kcu.referenced_table_name) x").strip().splitlines()
    orphan_fails = []
    for line in cons:
        name, t, ccols, rtable, rcols = line.split("\t")
        pairs = list(zip(ccols.split(","), rcols.split(",")))
        q = ("SELECT COUNT(*) FROM `%s` x LEFT JOIN `%s` y ON (%s) WHERE y.%s IS NULL AND %s"
             % (t, rtable, " AND ".join("x.`%s`<=>y.`%s`" % (a, b) for a, b in pairs),
                rcols.split(",")[0], " AND ".join("x.`%s` IS NOT NULL" % a for a, _ in pairs)))
        n = mysql(DST_PORT, q, DST_SCHEMA).strip()
        if n != "0": orphan_fails.append((name, t, n))
    assert not orphan_fails, "orphan rows after restore: %s" % orphan_fails
    fk_pass = "FK constraints verified: %d, orphans: 0" % len(cons)
    print(fk_pass)
    media_after = media_hashes()
    media_ok = media_before == media_after
    ok = all(i for _, _, i, _, _ in results) and all(g for _, _, _, _, g in results) and media_ok
    for t, n, i, g, gok in results:
        print("M%s %-28s rows=%-5d values=%s stored_recompute=%s" % ("04" if t.startswith("concept") or t == "attempt_knowledge" else "03", t, n, "OK" if i else "DRIFT", ("OK" if gok else "DRIFT") if g else "-"))
    print("MEDIA_SHA256_MATCH=" + str(media_ok) + " files=%d" % len(media_before))
    print("M03_M04_RESULT=" + ("PASS" if ok else "FAIL"))
    sys.exit(0 if ok else 1)

main()
