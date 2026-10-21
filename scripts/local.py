#!/usr/bin/env python3
"""Local-only lifecycle. No shell sourcing, global installs, port killing or volume removal."""
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / ".local"
ALLOWED = {"WEB_PORT", "API_PORT", "MYSQL_PORT", "MYSQL_ROOT_PASSWORD", "DB_PASSWORD", "DB_MIGRATION_PASSWORD", "JAVA_HOME", "NORTHSTAR_NODE_BIN"}
PROJECT = "northstar-english-local-01"
IDENTITY = "northstar-english-local-v1"


def read_env(path):
    result = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, sep, value = line.partition("=")
        if not sep or key not in ALLOWED or "\n" in value or key in result:
            raise RuntimeError(".env 格式错误、字段重复或包含未支持字段")
        result[key] = value
    return result


def available(port):
    for family, host in ((socket.AF_INET, "127.0.0.1"), (socket.AF_INET6, "::1")):
        try:
            with socket.socket(family) as listener:
                # A stopped service can leave TCP TIME_WAIT; real servers reuse that address.
                listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                listener.bind((host, port))
        except OSError:
            return False
    return True


def initialize():
    path = ROOT / ".env"
    if path.exists():
        print("保留已有 .env；未改写任何凭据或端口。")
        return
    chosen = []
    for default in (3100, 8085, 3308):
        port = default
        while port in chosen or not available(port):
            port += 1
            if port > 65535:
                raise RuntimeError("未找到可用端口")
        chosen.append(port)
    values = dict(zip(("WEB_PORT", "API_PORT", "MYSQL_PORT"), map(str, chosen)))
    values.update({key: secrets.token_hex(32) for key in ("MYSQL_ROOT_PASSWORD", "DB_MIGRATION_PASSWORD", "DB_PASSWORD")})
    with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w") as output:
        output.write("# 本项目专属配置；不提交、不输出密码。\n")
        output.write("".join(f"{key}={value}\n" for key, value in values.items()))
    print("已生成 .env（权限 0600）；Web/API/MySQL 端口：" + "/".join(map(str, chosen)))


def environment():
    if not (ROOT / ".env").exists():
        raise RuntimeError("先运行 scripts/init-local.sh")
    config = read_env(ROOT / ".env")
    for key in ("WEB_PORT", "API_PORT", "MYSQL_PORT"):
        if not config.get(key, "").isdigit() or not 1024 <= int(config[key]) <= 65535:
            raise RuntimeError(f"{key} 必须为 1024–65535")
    if len({config[k] for k in ("WEB_PORT", "API_PORT", "MYSQL_PORT")}) != 3:
        raise RuntimeError("Web/API/MySQL 端口不能相同")
    for key in ("MYSQL_ROOT_PASSWORD", "DB_PASSWORD", "DB_MIGRATION_PASSWORD"):
        if not re.fullmatch(r"[a-f0-9]{64}", config.get(key, "")):
            raise RuntimeError(f"{key} 必须设置为 64 位十六进制随机值；不自动替换已有密码")
    env = dict(os.environ, **config)
    node_bin = config.get("NORTHSTAR_NODE_BIN") or os.environ.get("NORTHSTAR_NODE_BIN")
    if not node_bin and Path("/opt/homebrew/opt/node@22/bin/node").exists():
        node_bin = "/opt/homebrew/opt/node@22/bin"
    if node_bin:
        env["PATH"] = node_bin + os.pathsep + env["PATH"]
    java_home = config.get("JAVA_HOME")
    if not java_home:
        candidates = sorted((LOCAL / "jdk21").glob("*/Contents/Home"))
        if candidates:
            java_home = str(candidates[0])
    if not java_home:
        java_home = os.environ.get("JAVA_HOME")
    if java_home:
        env["JAVA_HOME"] = java_home
        env["PATH"] = str(Path(java_home) / "bin") + os.pathsep + env["PATH"]
    env["NEXT_TELEMETRY_DISABLED"] = "1"
    return env


def run(args, env, **kwargs):
    return subprocess.run(args, cwd=ROOT, env=env, check=True, **kwargs)


def compose(env, *args, **kwargs):
    return run(["docker", "compose", "--env-file", str(ROOT / ".env"), "-f", str(ROOT / "infra/compose.local.yml"), *args], env, **kwargs)


def verify_container(env):
    result = run(["docker", "inspect", "northstar-english-mysql-01"], env, capture_output=True, text=True)
    item = json.loads(result.stdout)[0]
    labels = item["Config"].get("Labels", {})
    if labels.get("com.docker.compose.project") != PROJECT or labels.get("local.northstar.project") != IDENTITY:
        raise RuntimeError("容器身份不符，拒绝操作")
    binding = item["HostConfig"]["PortBindings"].get("3306/tcp", [])
    if binding != [{"HostIp": "127.0.0.1", "HostPort": env["MYSQL_PORT"]}]:
        raise RuntimeError("容器端口与本项目配置不符，拒绝操作")
    if not any(mount.get("Name") == "northstar_english_mysql_01_data" and mount.get("Destination") == "/var/lib/mysql" for mount in item["Mounts"]):
        raise RuntimeError("数据库卷身份不符，拒绝操作")
    return item


def doctor(env):
    node = run(["node", "--version"], env, capture_output=True, text=True).stdout.strip()
    npm = run(["npm", "--version"], env, capture_output=True, text=True).stdout.strip()
    java = run(["java", "-version"], env, capture_output=True, text=True).stderr.splitlines()[0]
    if not node.startswith("v22.") or not npm.startswith("10.") or not re.search(r'"21[.\"]', java):
        raise RuntimeError("需要项目级 Node 22 / npm 10 / Java 21；不会改写全局版本")
    print(f"项目：{ROOT}\nNode {node} / npm {npm}\n{java}")
    run(["docker", "version", "--format", "Docker Server {{.Server.Version}}"], env)
    for key in ("WEB_PORT", "API_PORT", "MYSQL_PORT"):
        print(f"{key}={env[key]}：{'空闲' if available(int(env[key])) else '已监听（启动前核对项目身份）'}")
    if not available(int(env["MYSQL_PORT"])):
        verify_container(env)
        result = run(["docker", "exec", "northstar-english-mysql-01", "sh", "-c",
                      'MYSQL_PWD="$DB_PASSWORD" exec mysql --protocol=TCP -h127.0.0.1 -unorthstar_app -Nse "SELECT project_key FROM northstar_english.project_identity"'],
                     env, capture_output=True, text=True)
        if result.stdout.strip() != IDENTITY:
            raise RuntimeError("数据库项目标记不符")
        print("MySQL 容器/卷/端口/数据库项目标记一致。")
    print("配置格式通过；密码未输出。")


def owns_process(record):
    pid = record["pid"]
    cmd = subprocess.run(["ps", "-p", str(pid), "-o", "command="], capture_output=True, text=True).stdout
    cwd = subprocess.run(["lsof", "-a", "-p", str(pid), "-d", "cwd", "-Fn"], capture_output=True, text=True).stdout
    return record["token"] in cmd and ("n" + record["cwd"] + "\n") in cwd


def start_process(name, args, cwd, env, token):
    path = LOCAL / (name + ".json")
    if path.exists():
        record = json.loads(path.read_text())
        if owns_process(record):
            print(name + " 已由本项目启动")
            return
    log_path = LOCAL / (name + ".log")
    with log_path.open("ab") as log:
        runner = str(ROOT / "scripts/service_runner.py")
        child = subprocess.Popen([sys.executable, runner, name, *args], cwd=cwd, env=env,
                                 stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    record = {"pid": child.pid, "cwd": str(cwd), "token": runner + " " + name}
    path.write_text(json.dumps(record))
    print(f"{name} PID={child.pid}，日志：{log_path}")


def wait_health(url, seconds=60):
    for _ in range(seconds):
        try:
            with urllib.request.urlopen(url, timeout=4) as response:
                data = json.load(response)
                if data.get("status") == "UP" and data.get("project") == IDENTITY:
                    return
        except (urllib.error.URLError, ValueError, TimeoutError):
            pass
        time.sleep(1)
    raise RuntimeError("健康检查未通过；查看 .local/api.log / web.log；未停止其他进程")


def up(env):
    doctor(env)
    for name, key in (("api", "API_PORT"), ("web", "WEB_PORT")):
        record_path = LOCAL / (name + ".json")
        owned = record_path.exists() and owns_process(json.loads(record_path.read_text()))
        if not available(int(env[key])) and not owned:
            raise RuntimeError(f"{key} 被其他进程占用；请修改 .env，不会停止占用进程")
    existing = subprocess.run(["docker", "inspect", "northstar-english-mysql-01"], env=env, capture_output=True)
    if existing.returncode == 0:
        verify_container(env)
    volume = subprocess.run(["docker", "volume", "inspect", "northstar_english_mysql_01_data"], env=env, capture_output=True, text=True)
    if volume.returncode == 0 and json.loads(volume.stdout)[0].get("Labels", {}).get("local.northstar.project") != IDENTITY:
        raise RuntimeError("同名 Docker 卷身份不符，拒绝使用")
    if not available(int(env["MYSQL_PORT"])):
        verify_container(env)
    LOCAL.mkdir(exist_ok=True)
    compose(env, "up", "-d", "--wait", "mysql")
    verify_container(env)
    jar = ROOT / "apps/api/target/northstar-api-0.1.0-SNAPSHOT.jar"
    if not jar.exists():
        run([str(ROOT / "apps/api/mvnw"), "-f", str(ROOT / "apps/api/pom.xml"), "package", "-DskipTests"], env)
    if not (ROOT / "apps/web/.next/BUILD_ID").exists():
        run(["npm", "run", "build"], env)
    start_process("api", [shutil.which("java", path=env["PATH"]), "-jar", str(jar)], ROOT / "apps/api", env, str(jar))
    wait_health("http://127.0.0.1:" + env["API_PORT"] + "/api/v1/health")
    next_cli = str(ROOT / "node_modules/next/dist/bin/next")
    start_process("web", [shutil.which("node", path=env["PATH"]), next_cli, "start", "--hostname", "127.0.0.1", "--port", env["WEB_PORT"]], ROOT / "apps/web", env, next_cli)
    wait_health("http://127.0.0.1:" + env["WEB_PORT"] + "/api/v1/health")
    print("打开 http://127.0.0.1:" + env["WEB_PORT"])


def down(env):
    for name in ("web", "api"):
        path = LOCAL / (name + ".json")
        if not path.exists():
            continue
        record = json.loads(path.read_text())
        if owns_process(record):
            os.kill(record["pid"], signal.SIGTERM)
            for _ in range(40):
                if not owns_process(record):
                    break
                time.sleep(.5)
            else:
                raise RuntimeError(f"{name} 未能在 20 秒内退出，保留 PID 记录供检查")
            print(f"已停止本项目 {name} PID={record['pid']}")
            path.unlink()
        elif subprocess.run(["ps", "-p", str(record["pid"])], stdout=subprocess.DEVNULL).returncode == 0:
            raise RuntimeError(f"{name} PID 身份不符；拒绝停止")
        else:
            path.unlink()
    # Stop only our verified container. Never down -v, rm, prune or kill by port.
    result = subprocess.run(["docker", "inspect", "northstar-english-mysql-01"], env=env, capture_output=True)
    if result.returncode == 0:
        verify_container(env)
        compose(env, "stop", "mysql")


def main():
    action = sys.argv[1]
    if action == "init":
        initialize()
        return
    env = environment()
    if action == "doctor":
        doctor(env)
    elif action == "up":
        up(env)
    elif action == "down":
        down(env)
    elif action == "db-test":
        record_path = LOCAL / "api.json"
        if record_path.exists() and owns_process(json.loads(record_path.read_text())):
            raise RuntimeError("先停止本项目 API，再单独启动 MySQL 执行 db-test，避免覆盖运行中的 JAR")
        env.update(NORTHSTAR_DB_TEST="1", DB_NAME="northstar_phase01_test")
        run([str(ROOT / "apps/api/mvnw"), "-f", str(ROOT / "apps/api/pom.xml"), "verify"], env)
    elif action == "exec":
        run(sys.argv[2:], env)
    else:
        raise RuntimeError("未知操作")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError, subprocess.CalledProcessError) as error:
        print("操作失败：" + str(error), file=sys.stderr)
        sys.exit(1)
