#!/usr/bin/env python3
"""Pinned Temurin21 for Apple Silicon, project-local and checksum verified."""
import hashlib
from pathlib import Path
import platform
import subprocess
import tarfile

root = Path(__file__).resolve().parents[1]
target = root / ".local/jdk21"
if list(target.glob("*/Contents/Home/bin/java")):
    print("保留已有项目级 JDK；请运行 doctor 核对版本。")
    raise SystemExit(0)
if platform.system() != "Darwin" or platform.machine() != "arm64":
    raise SystemExit("本下载器适用于 Apple Silicon Mac；其他平台请独立安装 Java 21，并在 .env 指定 JAVA_HOME。")
url = "https://github.com/adoptium/temurin21-binaries/releases/download/jdk-21.0.12.1%2B1/OpenJDK21U-jdk_aarch64_mac_hotspot_21.0.12.1_1.tar.gz"
sha = "3623232f33a9c3baadf304480b2535f9a3cba8a58d42ecbb438ba267315d9998"
archive = root / ".local/downloads/jdk21.tar.gz"
archive.parent.mkdir(parents=True, exist_ok=True)
if not archive.exists() or hashlib.sha256(archive.read_bytes()).hexdigest() != sha:
    subprocess.run(["curl", "-fL", "--retry", "2", "--max-time", "300", url, "-o", str(archive)], check=True)
if hashlib.sha256(archive.read_bytes()).hexdigest() != sha:
    raise SystemExit("SHA256 不符，停止安装。")
with tarfile.open(archive) as package:
    package.extractall(target, filter="data")
print("已校验并解压项目级 Java 21；未修改全局 Java。")
