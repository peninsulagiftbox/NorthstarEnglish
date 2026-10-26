# 压缩包实际内容清单

源码冻结：2026-10-26T19:35:35.712410+08:00。压缩包位置为项目根目录。

## northstar-source.zip

顶层目录 `northstar-source/`，共 **227 文件**。

| 路径组 | 文件数 |
|---|---:|
| `.env.example` | 1 |
| `.gitattributes` | 1 |
| `.gitignore` | 1 |
| `.node-version` | 1 |
| `AGENTS.md` | 1 |
| `Northstar_English_Codex` | 15 |
| `README.md` | 1 |
| `SOURCE_FILES.json` | 1 |
| `SOURCE_PACKAGE_README.md` | 1 |
| `apps` | 107 |
| `content` | 5 |
| `docs` | 11 |
| `infra` | 3 |
| `package-lock.json` | 1 |
| `package.json` | 1 |
| `references` | 3 |
| `scripts` | 73 |

逐文件路径、大小及SHA-256见 `evidence/source-package-files.json`；包内 `SOURCE_FILES.json` 可独立验证源码（自身除外）。源包保留未提交文件；不重复携带handoff，后者单独在交接包中。

## northstar-handoff.zip

顶层目录 `northstar-handoff/`，包括本目录所有报告、审计脚本、命令/退出码/日志、筛选脱敏的既有成功与失败日志、API/迁移/源码/Git清单和哈希。

逐文件路径、大小及SHA-256见 `evidence/handoff-package-files.json`。此清单为避免递归计算，仅排除其自身；最终ZIP完整性和两个ZIP的哈希另外验证。

## 排除范围

真实.env、凭据/Token/私有配置、个人学习行/录音/数据库备份、原始服务日志及私人截图、.git、依赖/缓存/构建、原型二进制及待审MP3均不入包。`.env.example`只包含占位符；源码清单记录机器路径脱敏，配置秘密使用本地精确值匹配扫描但不输出值。

完整历史progress报告未直接复制，避免附带个人行为与本机运行细节；本交接给出原始路径和必要结论，原始证据仅选取明确的隔离测试/汇总日志。源码包缺音频，完整启动复现NOT VERIFIED。

## 校验

`northstar-packages.sha256` 在项目根目录。校验命令：`shasum -a 256 -c northstar-packages.sha256`；ZIP CRC可用 `unzip -t northstar-handoff.zip` 和 `unzip -t northstar-source.zip`。
