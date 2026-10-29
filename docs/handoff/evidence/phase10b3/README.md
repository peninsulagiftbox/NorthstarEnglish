# Phase 10B-3 证据入口

执行：2026-10-28–29（Asia/Shanghai）。最终结论及限制见 `docs/progress/PHASE_10B_3.md`。

- `before-development.json`：实施起点 HEAD 与跟踪源码字节；三份已有 UI 修改不归本阶段。
- `demo-identity-registry.json`：历史物理 ID 到预分配 UUID 的确定性清单。每条物理记录保守登记独立身份，不推断跨版 equivalent。
- `frozen-migrations.json` / `frozen-migrations-appended.json`：首次执行的 V009.06–.14 及随后独立追加的 V009.15；旧文件不得修改。
- `backup-integrity.json`：旧 V008 备份 32 份文件的大小/hash 重算，不表示当前个人库实时快照。
- `execution-commands.jsonl`：独立构建、Java/Node/Python/Playwright/CLI/真实备份恢复的 argv、cwd、实际退出码与日志 hash；失败记录保留。
- `migrations/commands.jsonl` 与 `commands-*.json`：容器身份、端口、UUID、实际 Flyway、SQL、故障和收尾。私有原始数据日志仅通过 hash/路径引用。
- `migrations/*acceptance.json`：升级、最新空库、DML回滚、DDL语句间中断、CHECK替换、history登记失败、新恢复目标续学、独立CLI权限、实际快照工具恢复及最终重启结果。
- `schema.sql` / `schema-summary.json`：真实隔离 MySQL 结构、列与主键，不含行值；`delivery-audit.json` 为最终来源/hash/停止状态检查。
- `failure-events.json`：真实失败及后续重验，包括沙箱、原音频404兼容和初始化就绪竞态；不将失败改写成0。

私有 SQL、全表行值、录音、账号凭据和恢复副本仅在 `.local/phase10b3/`。原始运行证据保持本地忽略规则，不上传公共 GitHub。公开交付只保留本入口、确定性身份清单、工具源码、SQL和阶段报告。

测试发布 profile 为 `northstar.local.basic.v1`：当前独立句音频及基础内容门禁。不是10E完整core-v1导入器，也不授予teaching_complete。测试音为既有自编MP3波形；3×3许可分类使用明确的合成规则夹具，不代表第三方素材或真人录音授权通过。

运行器 `scripts/phase10b3*.py` 使用固定本轮命名空间、身份校验及创建拒绝保护；创建类动作不是可重复的日常命令。现存失败副本不可覆盖重跑。独立CLI实现为 `local.northstar.catalog.ContentPublicationCli`，不启动Spring/Flyway/播种/录音对账；需要显式隔离UUID与最小权限账号。个人库升级、部署与10C均未包含在本阶段授权中。
