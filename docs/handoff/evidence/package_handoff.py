#!/usr/bin/env python3
"""Package a frozen source snapshot and curated audit evidence, never runtime data."""
from collections import Counter
from pathlib import Path
import datetime
import hashlib
import json
import re
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[3]
HANDOFF = ROOT / 'docs/handoff'
EVIDENCE = HANDOFF / 'evidence'
STAGE = Path(sys.argv[1]).resolve()
assert STAGE.parent == Path('/private/tmp') and STAGE.name.startswith('northstar-source-audit-')

secrets = []
if (ROOT / '.env').exists():
    for line in (ROOT / '.env').read_text().splitlines():
        key, _, value = line.partition('=')
        if any(part in key.upper() for part in ('PASSWORD','TOKEN','SECRET','API_KEY')) and len(value.strip()) >= 8:
            secrets.append(value.strip().encode())

def digest(data):
    return hashlib.sha256(data).hexdigest()

def scan(name, data):
    parts=Path(name).parts
    assert '..' not in parts and not name.startswith('/')
    assert not any(p in {'.git','.local','node_modules','.next','target','__pycache__','recordings','backups'} for p in parts), name
    assert not any(p.startswith('.env') and p != '.env.example' for p in parts), name
    assert not any(value in data for value in secrets), 'Configured secret found in '+name
    assert str(Path.home()).encode() not in data, 'Home path found in '+name
    assert Path.home().name.encode() not in data, 'Local identity found in '+name
    assert not re.search(rb'(?:sk-proj-|ghp_|github_pat_)[A-Za-z0-9_-]{16,}',data), 'Credential pattern in '+name
    assert not re.search(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',data), 'Private key in '+name
    assert not re.search(rb'https?://[^/\s:]+:[^@\s]+@',data), 'Credential-bearing URL in '+name

def files(directory):
    return [(p.relative_to(directory).as_posix(),p.read_bytes(),p.stat().st_mode) for p in sorted(directory.rglob('*')) if p.is_file() and not p.is_symlink() and '__pycache__' not in p.parts and p.suffix != '.pyc']

def entries(items):
    return [{'path':name,'bytes':len(data),'sha256':digest(data)} for name,data,_ in items]

def write_zip(path, prefix, items):
    for name,data,_ in items:
        scan(name,data)
    with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for name,data,mode in items:
            scan(name,data)
            info=zipfile.ZipInfo(prefix+'/'+name)
            info.external_attr=(0o100755 if mode & 0o111 else 0o100644)<<16
            info.compress_type=zipfile.ZIP_DEFLATED
            archive.writestr(info,data)
    with zipfile.ZipFile(path) as archive:
        assert archive.testzip() is None
        assert len(archive.namelist())==len(items)==len(set(archive.namelist()))
        for name,data,_ in items:
            assert archive.read(prefix+'/'+name)==data

source=files(STAGE)
snapshot=json.loads((EVIDENCE/'source-snapshot.json').read_text())
for row in snapshot['files']:
    assert digest((STAGE/row['path']).read_bytes())==row['sha256'], 'Frozen source changed'
candidate_path=EVIDENCE/'phase09r/candidate.json'
candidate=json.loads(candidate_path.read_text()) if candidate_path.exists() else None
notice='''# 源码包说明

这是冻结的工作区脱敏快照，不是已签署验收通过的发行版。
冻结时刻和源文件哈希见SOURCE_FILES.json。
源码/测试/配置模板/锁文件/迁移/原创示例JSON均保留。
另取northstar-handoff.zip阅读逐阶段验收、失败日志、并行漂移和原始证据索引。
本包不重复包含docs/handoff，避免报告和源码双份证据混淆。

排除：真实.env和凭据、个人学习数据/录音/数据库导出、原始私有日志、
原历史阶段报告、Git元数据、依赖/缓存/构建、原型HTML/图片和MP3。
音频授权pending_review且校验依赖原哈希；本包缺音频，不可单独启动完整课程。
不要重生成替代音频或在现有学习库运行写入测试以伪造验收通过。
机器路径脱敏仅影响副本，源工作区业务文件未由本次打包修改。

SOURCE_FILES.json覆盖其自身以外的每个包内文件；其自身哈希在交接包
evidence/source-package-files.json中。依赖安装/数据库启动/测试写入需单独确认环境。
'''
if candidate:
    notice+='\nPhase 09-R 验收候选：'+candidate['candidate']+' / '+candidate['gitSha']+'。\n'
    notice+='验收报告和打包元数据可能晚于候选；候选文件哈希见交接包 evidence/phase09r/candidate.json。\n'
source.append(('SOURCE_PACKAGE_README.md',notice.encode(),0o644))
source_manifest=json.dumps({'frozenAt':snapshot['frozenAt'],'selfExcluded':'SOURCE_FILES.json','files':entries(source)},ensure_ascii=False,indent=2).encode()+b'\n'
source.append(('SOURCE_FILES.json',source_manifest,0o644))
(EVIDENCE/'source-package-files.json').write_text(json.dumps(entries(source),ensure_ascii=False,indent=2)+'\n')

counts=Counter(name.split('/')[0] for name,_,_ in source)
contents=['# 压缩包实际内容清单','','源码冻结：'+snapshot['frozenAt']+'。压缩包位置为项目根目录。','',
    '## northstar-source.zip','',f'顶层目录 `northstar-source/`，共 **{len(source)} 文件**。', '',
    '| 路径组 | 文件数 |','|---|---:|']
contents += [f'| `{name}` | {count} |' for name,count in sorted(counts.items())]
contents += ['', '逐文件路径、大小及SHA-256见 `evidence/source-package-files.json`；包内 `SOURCE_FILES.json` 可独立验证源码（自身除外）。源包保留未提交文件；不重复携带handoff，后者单独在交接包中。', '',
    '## northstar-handoff.zip','', '顶层目录 `northstar-handoff/`，包括本目录所有报告、审计脚本、命令/退出码/日志、筛选脱敏的既有成功与失败日志、API/迁移/源码/Git清单和哈希。', '',
    '逐文件路径、大小及SHA-256见 `evidence/handoff-package-files.json`。此清单为避免递归计算，仅排除其自身；最终ZIP完整性和两个ZIP的哈希另外验证。', '',
    '## 排除范围','',
    '真实.env、凭据/Token/私有配置、个人学习行/录音/数据库备份、原始服务日志及私人截图、.git、依赖/缓存/构建、原型二进制及待审MP3均不入包。`.env.example`只包含占位符；源码清单记录机器路径脱敏，配置秘密使用本地精确值匹配扫描但不输出值。', '',
    '完整历史progress报告未直接复制，避免附带个人行为与本机运行细节；本交接给出原始路径和必要结论，原始证据仅选取明确的隔离测试/汇总日志。源码包缺音频，完整启动复现NOT VERIFIED。', '',
    '## 校验','', '`northstar-packages.sha256` 在项目根目录。校验命令：`shasum -a 256 -c northstar-packages.sha256`；ZIP CRC可用 `unzip -t northstar-handoff.zip` 和 `unzip -t northstar-source.zip`。', '']
(HANDOFF/'PACKAGE_CONTENTS.md').write_text('\n'.join(contents))

source_zip=ROOT/'northstar-source.zip'
handoff_zip=ROOT/'northstar-handoff.zip'
write_zip(source_zip,'northstar-source',source)
log={'command':'python3 docs/handoff/evidence/package_handoff.py <frozen-private-temp-directory>',
     'checks':['frozen source hashes match','exact configured secret scan','local identity and private path scan','credential pattern scan','source ZIP CRC and every extracted byte match','handoff ZIP CRC and every extracted byte match'],
     'sourceFiles':len(source),'sourceZipSha256':digest(source_zip.read_bytes()),
     'note':'This records packaging validation only, not project acceptance. Handoff manifest excludes itself to avoid recursive hashing.'}
(EVIDENCE/'packaging.log').write_text(json.dumps(log,ensure_ascii=False,indent=2)+'\n')
handoff=[x for x in files(HANDOFF) if x[0]!='evidence/handoff-package-files.json']
(EVIDENCE/'handoff-package-files.json').write_text(json.dumps(entries(handoff),ensure_ascii=False,indent=2)+'\n')
handoff=files(HANDOFF)
write_zip(handoff_zip,'northstar-handoff',handoff)
checksums=''.join(digest(p.read_bytes())+'  '+p.name+'\n' for p in [handoff_zip,source_zip])
(ROOT/'northstar-packages.sha256').write_text(checksums)
print(json.dumps({'exitCode':0,'sourceFiles':len(source),'handoffFiles':len(handoff),'sourceBytes':source_zip.stat().st_size,'handoffBytes':handoff_zip.stat().st_size,'archives':['northstar-handoff.zip','northstar-source.zip'],'privacyScan':'PASS within explicit scan rules; no runtime personal datasets included','CRCAndBytes':'PASS'},ensure_ascii=False))
