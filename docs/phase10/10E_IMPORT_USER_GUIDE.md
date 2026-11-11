# Phase 10E 课程导入使用指南

本指南面向本地隔离环境，不指导批量导入四册教材。`northstar-content.py` 只接受本地冻结课程包；所有数据库操作要求显式隔离目标、显式批准和显式发布。不要在共享终端或 CI 中保留导入密码。

## 1. 输入包与来源审校

一个 core-v1 包至少包含：

- `package.json`：课程、段句、音频资产、知识和练习声明。
- `manifest.json`：`packageId`、`rawSha256`、规范化 `contentSha256`、来源原始文件清单和字节哈希。
- `sources[].sourceRef` 指向包内原始来源文件；文本、音频与图片分别记录来源。
- 音频必须真实可解码；manifest 中的音频哈希必须与文件一致。

正式使用前必须人工完成：

1. 核对来源、权利范围、授权期限与 `proofRef`。
2. 将 `sources[].reviewStatus` 改为 `confirmed`，填写真实 `reviewer` 和 `reviewedAt`。
3. 如涉及真人录音或第三方语音，单独确认录制者、声音使用许可和分发范围。
4. 真人试听音频后，再决定是否可发布。本阶段样例保持 `pending_review`，不能作为已审校样例。

禁止提交浏览器可读的 API Key 或数据库密码；导入所需密码只通过受限环境变量注入。

## 2. 准备隔离目标

CLI 使用以下环境变量：

| 变量 | 用途 |
| --- | --- |
| `MYSQL_PORT` | 目标 MySQL 端口；禁止 3308。 |
| `DB_NAME` | 仅允许 `northstar_english`、`northstar_phase01_test`；恢复副本须额外设置 `NORTHSTAR_ALLOW_RESTORE_DB=true`，库名须为 `northstar_restore_YYYYMMDDHHMMSS`。 |
| `NORTHSTAR_IMPORT_DB_UUID` | 目标 MySQL `@@server_uuid`；与 CLI 运行时实际值不一致会拒绝操作。 |
| `NORTHSTAR_IMPORT_MEDIA_ROOT` | 项目专用导入媒体根目录。 |
| `DB_IMPORT_PASSWORD` | `northstar_importer` 账号密码。 |

目标库必须已迁移到 V013.04。CLI 不会自动迁移。不要把个人库 UUID 或学习记录放入任何脚本；交接摘要中的个人 UUID 已被 CLI 明确拒绝。

## 3. 离线验证

在仓库根目录：

```bash
python3 scripts/northstar-content.py validate /absolute/path/to/course-package
```

通过时输出：

```json
{"valid": true, "issues": []}
```

失败退出码为 2，`issues` 包含 `code/message/path/severity/suggestion`。不要只看首条错误；修复来源后重新生成包与 manifest，不要手工修补哈希。

## 4. 零写入 dry-run

```bash
python3 scripts/northstar-content.py dry-run /absolute/path/to/course-package
```

dry-run 前后数据库摘要和媒体清单应完全不变。计划中的关键哈希用于后续 apply：

- `package_sha256`：原 `package.json` 字节哈希。
- `raw_sha256`：manifest 中声明的原始包哈希。
- `manifest_sha256`：外部 manifest 字节哈希。
- `plan_sha256`：冻结导入计划哈希。

目标状态或媒体变化后再 dry-run 会得到新的 `plan_sha256`；不要复用旧批准哈希。

## 5. 显式 apply 与 resume

```bash
python3 scripts/northstar-content.py apply /absolute/path/to/course-package /absolute/path/to/plan.json <approved_package_sha256>
```

`<approved_package_sha256>` 必须是 dry-run 计划中预期的 `package_sha256`。apply 会先落媒体，再在单课数据库事务内创建/复用版本与投影，并记录导入批次与入口。成功返回 `applied`；同包重试返回 `no_op` 并复验一致性。这不是发布。

进程中断后不要重新初始化现场：

```bash
python3 scripts/northstar-content.py status <packageId>
python3 scripts/northstar-content.py verify /absolute/path/to/course-package
python3 scripts/northstar-content.py resume /absolute/path/to/course-package /absolute/path/to/plan.json <approved_package_sha256>
```

`verify` 用于核对已落媒体和数据库状态；`resume` 只接受原冻结计划与原批准哈希。异常批次保持 `partial_failed`，保留现场再分析。CLI 不自动删除媒体或改写审计。

## 6. 显式发布

只有来源人工审校通过且真人听查完成后才发布：

```bash
python3 scripts/northstar-content.py publish /absolute/path/to/course-package <operationId> <expected_current_version_id_or_null> <actor>
```

说明：

- `expected_current_version_id_or_null` 写字面 `null` 表示当前无版本，否则填现有版本 ID。不一致会拒绝，防止覆盖并发发布。
- `actor` 是可追责的真实操作者标识，不要使用自动化占位名冒充审校人。
- 发布会重新加载导入包、复验哈希与 core-v1、锁定课程并执行 CAS。成功返回 `PUBLISHED`。
- 已发布课程仍只表示 `basic_content` 可学；没有教学计划时不得展示教学闭环或计划完成率。

## 7. 验证与故障处理

apply 后至少核对：

1. `lesson.contentReadiness` 为 `basic_content`。
2. 新课当前版本仍为未发布或符合显式发布结果。
3. 段句、音频、知识和练习数量与包一致。
4. 读取投影不包含答案键和内部存储键。
5. 备份/恢复工具已包含导入审计表与内容媒体，且冻结校验通过。

失败时保留原始包、计划、目标 UUID、日志和媒体目录；执行 `status`/`verify`。不要手工 UPDATE 导入审计表、不要删除孤儿文件、不要用新版本重用旧哈希。升级异常目标应恢复冻结备份到新隔离目标后重试。

## 8. 本阶段边界

- 只允许 `contentReadiness=basic_content`；`teaching-v1` 属于后续阶段。
- 不解析或导入四册版权教材；不接受 Web 目录批量导入。
- 测试损坏包只用于验证拒绝路径，不得当作真实课程。
- macOS 系统语音样例仅限本地验证，不声明公开再分发。
- 完成 10E 收尾后停止，等待评审和后续阶段授权。
