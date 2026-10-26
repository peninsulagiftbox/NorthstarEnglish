# 本地数据导出、备份与隔离恢复（Phase 08）

JSON 是服务端事务一致的逻辑快照，不是完整机器备份。它包含内容版本、来源字段、所有学习事件/回执、听写/阅读/测验作答、作文草稿与不可变版本、课程状态/恢复点、复习来源/自评/调度、偏好和录音元信息。格式 `northstar.snapshot.v1`，数据库版本 `008`，项目 `northstar-english-local-v1`，归属 `local`。外层 `payloadJson` 是原始 UTF-8 JSON 字符串，`sha256` 对这个字符串计算，避免跨语言数字和空白规范差异。校验和用于发现损坏，不是签名或信任证明。

个人原始作答、作文、句子上下文都属于私人数据。下载文件不含数据库密码或模型密钥，但并未加密；脚本新建备份目录权限0700、文件0600。不要提交到 Git 或公开分享。浏览器下载目录权限由浏览器管理。

## 导出与完整私人录音备份

设置页“导出学习 JSON”下载服务端快照。“选择 JSON”只做格式、校验和、版本、归属、表/列、冻结内容和迁移基线预检，显示表数/行数，**不会写入或覆盖当前库**。迁移基线比较版本、类型、脚本、校验和与成功标志，不要求另一台机器的安装时间/账号/耗时一致。外键、唯一性、CHECK和所有行值须在新目标中实际插入验证。

```sh
# 先运行本项目服务。目录必须不存在；默认API8085，使用.env中的Web来源端口。
sh scripts/backup.sh .local/backups/my-new-backup
# 隔离测试实例示例
sh scripts/backup.sh .local/backups/my-test-backup --api http://127.0.0.1:8086 --web-port 3101
```

备份生成 `learning.json`、`media-manifest.json`、`media/*.audio` 和最后写入的 `COMPLETE` 标志。每个 ready 录音按快照大小和SHA-256校验；deleted/missing录音只有历史元信息，清单 `included=false`。媒体获取失败、并发删除或哈希变化时整个备份命令失败，不写COMPLETE；保留失败目录供排查，请换新目录重做。快照事务包含DB记录，不锁定外部音频文件，因此备份时应停止新的学习写入。

不包含：尚未同步的IndexedDB草稿、测验选项、outbox命令、待上传录音；浏览器里显示未同步时先恢复服务并重试，待上传录音也可在跟读页单独下载。JSON的 `mediaIncluded=false` / `browserBuffersIncluded=false` 是硬边界。原始教材MP3属于项目 `content/demo-01/` 的受审内容包，须与程序/内容目录另行保留，不能把录音备份冒充教材音频备份。Phase09才进行完整发布复现及灾难恢复验收。

## 仅恢复到新隔离数据库

先备份当前数据。仅使用自己保管的快照；预检通过并不赋予外部JSON执行权限。脚本只使用本项目已核验容器的当前DDL，不执行文件提供的SQL，不关闭插入时的外键，所有数据在一个事务内入库。课与当前版本的循环引用通过先置空再关联处理；作文按版本顺序恢复。

```sh
# 日期后缀只作新隔离目标标识，请换成未使用值。绝不接受主库/测试库作为目标。
sh scripts/restore.sh .local/backups/my-new-backup/learning.json \
  --target northstar_restore_20261024160000 --confirm-new-isolated
```

- 不支持覆盖、清空或静默合并。目标已存在即拒绝，包括同包重复导入；不会产生重复历史。冲突/损坏/错版本包拒绝。
- ready录音必须有同目录下正确的 `media/<id>.audio`，缺失或损坏会在创建库前拒绝。只有JSON且无ready录音时可恢复。媒体清单不作为安全判据，实际逐文件按DB快照校验。
- 使用容器root在本项目容器内创建新库，并仅向现有本项目账号授予新库范围权限；不改账号密码。历史表只追加，投影/草稿可更新。
- 默认媒体写入 `~/Library/Application Support/NorthstarEnglish/recordings/<新库名>/`；可用 `--recording-root <私有父目录>` 指定，与恢复副本API的 `--northstar.recording-root` 对应。新媒体目录必须不存在。路径权限不足会明确失败。
- DDL/媒体与MySQL事务不能组成跨资源原子事务。失败时保留新库/媒体供排查，不自动删除；严禁拿现库“清理重试”。新目标创建不覆盖源库，但磁盘空间和本机MySQL权限仍是前提。
- 隔离副本启动需项目级 `DB_NAME=northstar_restore_... NORTHSTAR_ALLOW_RESTORE_DB=true`，另外指定空闲 `API_PORT` / `WEB_PORT`，保留原 `.env`。可通过 `python3 scripts/local.py exec env ... java -jar ...` 启动；不能直接省略 `exec env` 把DB_NAME写到全局。Guard只有显式开关+14位时间戳新库名+项目身份才允许迁移。
- 恢复后检查报告、作文原文和版本、复习来源/到期时间、逐表行数、录音哈希并实际回放；再用新事件继续一条练习，确认可继续学习。
- 原主站配置不自动切换；替换主库与完整升级回滚属于后续单独操作。恢复副本及首次失败目标均保留，按需人工处理，不提供清卷脚本。

## 报告口径

所有版本历史累计；快照读取使用MySQL REPEATABLE_READ事务。首页每个保留的课版本显示六Tab：课文仅浏览，五训练的累计证据和当前状态分列。多目标状态汇总优先正在尝试、暂停、跳过、已练习；累计证据不会被新一轮状态抹掉。

- 独立听写：未暴露答案的正式提交数为分母，完全匹配为分子；另列包含暴露答案的全部次数/匹配数。
- 阅读：真实题次和正确题次，重做保留记录。
- 录音：全部上传数（含删除）与当前ready数，不能代表发音水平；回放观察才产生跟读证据。
- 作文：不可变正式版本数，不含草稿。
- 测验：完整3题交卷轮次，正确题次 / 轮数×3，重做不覆盖。
- 复习：到期卡 / 全部卡；自评次数独立列出，没有客观延时复测或能力曲线。
- 零样本显示暂无数据，不填模拟百分比。浏览、播放、暂停、跳过、收藏不计真实提交。

AI开关固定未启用，预置讲解按当前课版本和句ID读取；未配置供应商、密钥、预算或外发授权，不发起模型请求。录音开关可关闭新录制/上传，不阻断历史回放，已有草稿缓冲不删除。

## Phase 09：恢复到独立 MySQL 实例

原有默认恢复仍只创建新schema。本阶段另提供专属恢复MySQL，使用不同容器/卷（`northstar-english-phase09-recovery` / `northstar_english_phase09_recovery_data`），仅绑定127.0.0.1。首次从3310起选择空闲端口并记录 `.local/phase09-recovery.json`。复用现有私有.env中账号凭据，不输出或重写密码；它不依赖主MySQL卷。容器/卷/端口身份不匹配时拒绝操作，既有容器只start，不重建。

```sh
python3 scripts/recovery_mysql.py start
# 以下目标须使用未使用的14位日期标识；媒体目标目录也必须不存在。
sh scripts/restore.sh .local/backups/my-test-backup/learning.json \
  --api http://127.0.0.1:8086 --web-port 3101 \
  --target northstar_restore_20261026160000 --confirm-new-isolated \
  --separate-mysql --recording-root .local/phase09-media
python3 scripts/local.py exec python3 scripts/regression-runtime.py build \
  --restore-db northstar_restore_20261026160000 --api-port 8087 --web-port 3102
python3 scripts/local.py exec python3 scripts/regression-runtime.py start \
  --restore-db northstar_restore_20261026160000 --api-port 8087 --web-port 3102
python3 scripts/check-snapshot.py .local/backups/my-test-backup/learning.json \
  --api http://127.0.0.1:8087 --media
```

`check-snapshot.py`只读比较schema版本与所有表/列/单元值，逐个ready录音检查大小及SHA-256；不打印原始文本/凭据。`--save-current <新文件>`可保留0600快照，用于下一次重启前后核对，现有文件拒绝覆盖。验证前暂停测试学习写入；恢复副本一旦继续学习，应另取新快照再比较。

新浏览器只读回访可使用 `NORTHSTAR_BASE_URL=http://127.0.0.1:3102 NORTHSTAR_READ_ONLY=1 sh scripts/release-browser.sh release-revisit`。该用例在发送前阻断所有写请求，验证草稿、版本、测验/复习与实际录音解码。需验证真实续学时，使用固定恢复端口8087/3102，设置 `NORTHSTAR_CONTINUE_RESTORE=1`、`NORTHSTAR_RESTORE_SNAPSHOT=<恢复前快照路径>`，运行 `sh scripts/release-browser.sh release-continue`；入口先核验独立容器和API进程身份及全表/媒体一致性，再实际播放原句、提交一次听写并验证重试幂等。它会在恢复副本产生一条真实测试作答。

结束时先运行 `python3 scripts/regression-runtime.py stop --restore-db <目标> --api-port 8087 --web-port 3102`，再运行 `python3 scripts/recovery_mysql.py stop`。只停本轮服务，库、容器、卷、备份和录音保留。完整演练结果见PHASE_09；这不是对主库执行恢复或替换的授权。
