# Phase 10B-1｜安全预检与隔离迁移演练

预检：2026-10-26；最终更新：2026-10-27（Asia/Shanghai）。**当前：B01/B03功能演练PASS，附主控汇总退出1的工具问题说明，等待独立复核。** 已完成受控备份、两条隔离路径、5类故障及5次新目标恢复。最新结论见本报告末尾“最终数据安全验收”；以下原阻塞记录作为历史保留，不改写为PASS。用户授权10A-R设计复审通过作为输入，不将旧文档的“待复审”误当本轮未授权。

## 1. 修改了什么

新增只读预检脚本、A–G执行计划与证据包。未改业务代码、V001–V008、配置、秘密、依赖、内容、旧报告或全局运行时；没有创建V009候选，不开始10B-2/10B-3，未提交或推送Git。

本会话没有Plan模式切换工具，已先保持只读规划边界并保存[计划](../handoff/evidence/phase10b1/PLAN.md)。实际预检在源容器身份门禁停止：

```text
permission denied while trying to connect to the docker API at unix:///<HOME>/.docker/run/docker.sock
```

`docker inspect`实际退出1，预检脚本退出2（主动阻塞）。这是执行环境权限限制，不是数据库身份不符、数据损坏或自动审批拒绝。未申请提权或改用其他库绕过；“继续”后仅整理证据与报告。

## 2. 涉及哪些文件与已确认基线

- 报告：本文件。证据：[phase10b1目录](../handoff/evidence/phase10b1/README.md)，包含PLAN、preflight.py、baseline、命令原始输出/退出码、gate与验收表；校验清单见SHA256SUMS.json。
- 起点HEAD为`98bfedc8ac43ab68aea5447f2790cd3777b0a764`，最初`git status --short --untracked-files=all`为空（会话工具记录）；预检脚本记录时已有本轮PLAN与脚本未跟踪。未覆盖已有改动。
- 已阅读AGENTS、IMPLEMENTATION_PLAN适用规则、phase1有关草稿/录音/容灾条款、04 §2.1–6、08 B01/B03、09的10B-1与PHASE_10A。报告存在；其旧HEAD和未跟踪范围属于历史，本轮按实际Git核对。
- `baseline.json`含190个Git跟踪的apps/scripts/infra/content及根package文件SHA-256，8份实际迁移的SHA-256及逐字节对HEAD结果，**8/8一致**；不包括私人媒体、未跟踪音频和全量Git对象。实际只有V001–V008；冻结候选DDL文件名/hash为**不存在 / NOT VERIFIED**。设计V009组范围及后续排除范围在PLAN列明，不能当已测试DDL。
- 配置声明源为回环`127.0.0.1:3308`、schema `northstar_english`、容器`northstar-english-mysql-01`、项目`northstar-english-local-v1`；Web3100/API8085。账号声明为`northstar_app`/`northstar_migrator`。**均非当前连接身份已确认**；server_uuid、实际schema/账号/权限、容器标签/卷/绑定未核验。
- 本地服务记录声称API PID9116、cwd apps/api，Web PID17634、cwd apps/web；未现场核实存活/归属/活动写入，不能据此停服务。旧恢复端口记录3310；旧09-R工具声明3311/3312，不将这些既有资源当本轮新目标。
- 当前磁盘可用79,052,800,000字节，但备份/副本/临时空间需求未测，**容量门槛未通过**。
- 本地JAR含Flyway core/mysql **12.4.0**，JAR SHA-256 `99a3c24103d382c2330a872667c5d0b6d53494de9fd14c320c322cc14ef22619`。仅为构建产物检查，不证明服务实际加载版本或与HEAD对应；实际Flyway schema/history尚未读。

### 启动写入、备份和媒体边界

`application.yml`启用Flyway；`ContentSeeder`通过迁移账号执行播种；`RecordingController.@PostConstruct`创建/改权限媒体目录并更新录音状态。没有启动任何Spring实例。

默认录音父目录为`<HOME>/Library/Application Support/NorthstarEnglish/recordings`，最终附加DB_NAME；内容根为项目content。实际进程覆盖参数、真实目录、symlink/权限、文件清单/hash和DB登记状态均**NOT VERIFIED**，未读取个人媒体。

现有backup.sh是JSON+ready录音导出，不能代替SQL结构/数据/history、全部登记状态与完整媒体快照；现有restore默认会在既有实例创建schema并向已有账号授权，本轮未调用。已有recovery/09-R工具的身份核验可以参考，但不能替代新10B-1独立实例/端口/账号/卷/媒体核验。

浏览器IndexedDB草稿、outbox、未上传录音未检查。策略是保持origin/profile，先单独导出未同步数据或由用户完成同步，不代提交/丢弃；未满足前不声称完整一致快照。维护窗口未请求/未获明确批准；服务身份核实后须先列影响，再取得批准，不操作其他服务。

## 3. 运行了哪些验证

| 实际命令/检查 | 退出码或结果 | 证据与限制 |
| --- | --- | --- |
| git rev-parse HEAD / git status --short --untracked-files=all / git ls-files -z（限定范围） | 各0 | commands.json及probe-*.json |
| 8次git show HEAD:迁移路径与磁盘字节比较 | 各0；8/8一致 | baseline.json列逐文件路径、hash与gitShowReturncode |
| PYTHONDONTWRITEBYTECODE=1 python3 docs/handoff/evidence/phase10b1/preflight.py | **2** | 会话工具记录；内部命令输出已落盘 |
| docker inspect --format（仅Name/Labels/PortBindings/Mounts/State.Status） northstar-english-mysql-01 | **1** | probe-docker-identity.json保存完整argv、时间、stdout、stderr与原始退出码 |
| PYTHONDONTWRITEBYTECODE=1 python3 docs/handoff/evidence/phase10b1/verify_evidence.py | **0** | 5项本地机械检查通过：190文件及8份迁移保持一致、Python/JSON可解析、无配置密码泄露、空白和Git范围正确；生成14文件大小/hash清单 |

其余前置cat/sed/rg为本会话只读文档/源码查阅；未当数据库测试证据。没有执行SQL、mysqldump、Flyway migrate/validate/repair/clean、恢复、回填、故障注入或HTTP学习接口。数据库执行命令集合为空。报告收尾检查另见validation.json，未执行项目编译、单元/集成或Playwright，未声称其通过：本次无业务改动，数据库演练又被硬门禁阻塞。

### 六项证据与B01/B03逐项验收

| 证据/验收项 | 状态 | 依据/缺失 |
| --- | --- | --- |
| 源身份与实际schema/Flyway | BLOCKED | Docker权限受限；仅本地配置/源码基线存在 |
| SQL+媒体一致备份、大小/hash及实际可恢复性 | BLOCKED | 身份/维护窗口/浏览器缓冲未确认，无备份文件 |
| V008副本升级至冻结候选 | BLOCKED | 无备份、新隔离目标或冻结候选 |
| V001空库初始化至同一候选 | BLOCKED | 无核验后的空库或候选 |
| 三类故障及新目标恢复 | BLOCKED | 无独立故障副本；没有运行repair/clean/修改history |
| 旧表旧列按PK逐值、媒体/状态对比 | BLOCKED | 未读源行/媒体，没有前后快照 |
| B01：V001–V008文件字节/hash不变 | PASS | 8/8与HEAD一致；仅源码层 |
| B01：ID/正文/hash/event/receipt/作文父链/录音/复习到期不变 | NOT VERIFIED | 未取真实旧列快照，不把“未连接”当完整性对比通过 |
| B01：新增段句FK、索引/CHECK正反例、重复启动无损 | NOT VERIFIED | 未创建/应用候选，未启动应用 |
| B01总体 | **BLOCKED** | 六项证据不齐，不得Go |
| B03：逐条DDL后中断可识别并停写 | BLOCKED | 未执行故障注入 |
| B03：history登记失败真实状态留存 | BLOCKED | 未执行故障注入 |
| B03：回填DML失败及残留状态检查 | BLOCKED | 未执行故障注入 |
| B03：从原备份到另一新目标旧版读/真实续学/重启 | BLOCKED | 无原备份；不是只读源码可替代 |
| B03：未repair/clean/改history、未删除故障目标 | PASS（执行范围） | 本轮未连接SQL/创建故障副本；不是故障恢复已通过 |
| B03总体 | **BLOCKED** | 实际恢复演练缺失 |

### 个人库是否写入

**本轮助手未对个人库写入，亦未建立数据库连接或调用应用API；未启停服务。** 依据为preflight.py的执行路径、commands.json和Docker门禁失败原始日志。不能将此表述扩大为“期间没有其他进程写入”或“已由数据库审计证明零写入”：当前SHOW GRANTS和数据库操作审计均**NOT VERIFIED**，初始化脚本声明不能替代实际权限证明。源DB及文件前后摘要缺失，不能编造。

## 4. 风险、下一步与停止点

首要阻塞是Docker socket访问权限，源身份和隔离配置无法核验。未修复权限、修改秘密或切换其他数据库。需要在可核验Docker身份的执行环境重新开展A0/A1；完成实际服务归属、账号权限、媒体路径与浏览器缓冲核查后，才能提出具体维护窗口审批和一致备份。

后续只有同一冻结候选的双路径、故障恢复、逐值比较全部实际PASS并独立复核后才能签收10B-1；即便通过，仍不授权个人库迁移或10B-2/10B-3。当前交付为**阻塞证据包**，不是迁移演练完成包。无UI改动、无截图；停止，等待独立复核。

## 2026-10-27｜10B-1-R恢复预检补记

以上原记录保留为10B-1历史执行结果，原文件已在recovery-20261027/originals保存。当前状态以[恢复报告](PHASE_10B_1_RECOVERY.md)为准，不改写旧失败日志或旧gate。

经用户分别批准的单次沙箱外Docker诊断与A1只读检查，已确认Docker daemon可访问、阻塞来自seatbelt沙箱，并取得真实源实例/项目/schema/账号权限与Flyway history。V001–V008实际SQL校验和8/8匹配。历史BASELINE0标记有现有初始化代码及Phase08记录解释，未在本轮创建或修改。

首轮A1因脚本把history总行数误计为8而提前退出2，数据库命令均退出0；原失败保留并离线纠正，未repair/clean或修改history。剩余安全预检、浏览器缓冲、媒体和备份容量门禁及其最新结果见恢复报告。**数据库身份只读成功不等于B01/B03通过；两者仍BLOCKED。**

10B-1-R已经建立只读数据库连接（与上方“未建立连接”的旧轮次区分），没有对个人学习数据库执行DDL/DML、备份恢复、迁移、回填、测试写入、repair/clean或启停学习服务；没有开始10B-2/3。

随后用户明确批准剩余A1只读检查，单次续跑退出0：V008实际列核验、37张表结构/行数与容量测量、API/Web共4个进程的cwd核验已完成。数据均为在线分次读取，非一致快照；有效媒体根、浏览器缓冲、进程到schema绑定与完整备份预算仍NOT VERIFIED。新证据在a1-continuation；原脚本失败和首版ZIP保留，最新结果见恢复报告，不更改B01/B03的BLOCKED结论。

继续推进后的最新结果：有效运行配置/数据库TCP peer和媒体根已确认；2个ready录音hash全部匹配；媒体/content合计600,543字节；宿主机与Docker卷文件系统保守空间预算通过。用户声明实际Chrome同origin没有未同步内容，未冒充Chrome自动化检查。维护窗口脚本、4份最小V009候选及已编译隔离Java迁移工具已准备；源默认迁移目录不变。**具体暂停/静态备份窗口仍待单独批准，未执行备份或任何隔离迁移，B01/B03仍BLOCKED。** 全部新命令、失败重试和限制见恢复报告第6节与readiness-summary.json。

## 最终数据安全验收（2026-10-27，Asia/Shanghai）

### 1. 修改与执行范围

用户分别明确批准了源进程短暂停顿/备份/原进程恢复，以及12个全新目标的C–F隔离演练。没有对个人学习库执行DDL、Flyway migrate、回填、测试写入、恢复、repair/clean或删除；没有重新启动源Spring。源Java9117/Next17635暂停约18.275秒后以SIGCONT恢复，监督进程/MySQL不动；最终原PID仍在、health UP/V008。没有开始10B-2/3或导入教材，没有提交/推送Git。

新增工具与候选全部位于docs/handoff/evidence/phase10b1，不进入源应用默认迁移目录；业务代码/依赖/配置/.env/V001–V008不变。完整阶段执行、问题和证据路径见[恢复报告](PHASE_10B_1_RECOVERY.md)第7节；当前机器可解析状态为[STATUS.json](../handoff/evidence/phase10b1/STATUS.json)，历史gate/acceptance/result的BLOCKED保留，不作为最新结论。

### 2. 固定基线与真实备份

- 基线commit：98bfedc8ac43ab68aea5447f2790cd3777b0a764；候选未另建commit，按四个文件SHA-256冻结，不伪称已提交。V001–V008原字节/实际checksum均不变。
- 原JAR SHA-256：99a3c24103d382c2330a872667c5d0b6d53494de9fd14c320c322cc14ef22619；隔离候选JAR：0aa22702023aa20d33405c2572e0469707fc41948ff985a687dc7fcec3ce3005。所有原JAR条目逐字节一致，仅追加4份候选SQL。
- 私有备份ID：20261027T154428，路径.local/phase10b1-backups/20261027T154428；32个清单文件合计1,298,897字节，包括原始SQL、保持FK开启的restore.sql、全旧列规范化快照和全部录音/content。清单SHA-256为2388d0c727091008bf4c9c2b6ff32f04f89a5877d5c57b05cef510593216031c。
- 停顿窗口内37张表全部旧列/结构前后逐值相同，录音/content前后文件hash相同；2个ready录音161,914字节、content25文件438,629字节均完整复制。不是只凭COMPLETE标记通过：已在6个新目标实际SQL恢复并对账（upgrade+5恢复），另有5个故障副本从同一备份还原。
- root账号实际为root@%，app/migrator/root均有写能力，不能以“账号只读权限”证明零写入；依据是明确READ ONLY查询、受控mysqldump及完整命令日志。实际SHOW GRANTS另存source-final-grants-readonly.json。没有启用全局审计，因此不声称期间其他进程零写入。

| 冻结候选文件 | SHA-256 |
| --- | --- |
| V009_01__paragraph_table.sql | 991af047d2158c89ff9bf72e2c3d3ea4a90c4abd2fb5a6337ad46335b2c046e9 |
| V009_02__sentence_paragraph_column.sql | 2cfea1ebc7a32a5b96f3bb818f19f6df20303079fe55266a574d86a731c79e0f |
| V009_03__demo_paragraph_backfill.sql | b98470e3f598f6781f8ec4c0171b63602ae60e573bc03ce17c476a1fc66c35c5 |
| V009_04__sentence_paragraph_constraint.sql | 6c9f791c225db2ceb0450dca7fd6762002ea22e3f662f864abc34710ec93ece1 |

范围仅paragraph和sentence.paragraph_id；旧表旧列的ID/payload/hash/events/receipts/草稿/作文父链/复习due与版本/录音状态全部逐PK逐值核对。候选3个DDL逐文件前后留存，5条回填事务语句都有实际Flyway statement callback。没有实现身份发布或多课业务。

### 3. 六项证据、B01/B03

| 验收项 | 状态 | 实际依据 |
| --- | --- | --- |
| 源身份、权限、实际schema/Flyway | PASS | 已核实源容器/卷/回环3308/server_uuid/project、实际账号权限、V008列及V001–V008 checksum；source-final-grants-readonly.json等 |
| 一致SQL+完整媒体备份与实际可恢复性 | PASS | backup-20261027T154428；所有备份hash验证，upgrade与5个新恢复目标的原列/结构/媒体100%一致 |
| V008恢复副本逐版本升级 | PASS | upgrade的4次迁移、旧列逐值、实际跨版FK/正值CHECK/唯一键负例、两次候选JAR启动前后不变 |
| 空库从V001到同一候选 | PASS | empty自V001起；无baseline/复制history，V008隔离播种Demo后应用同候选；最终schema/索引/FK/CHECK与upgrade一致，重复启动无损 |
| DDL/登记/DML故障与新目标恢复 | PASS | 三个候选DDL边界、history INSERT权限失败、回填事务失败均保存真实schema/history；5个另外的新目标旧版读取、写作正式提交/同event重试、重启对账通过 |
| 旧列/媒体/关系逐值核对 | PASS | 所有旧列100%逐值；新列/paragraph仅按白名单；5次续学仅允许新增1 receipt/revision/evidence和目标草稿/进度变化，原不可变行和其他行全部保持 |
| B01 | **PASS** | 两条路径、备份/媒体/旧列、约束与重复启动均有实际证据 |
| B03 | **PASS** | 5类真实故障、状态留存、不repair/clean及5次新目标恢复/续学/重启均完成 |
| 实际Chrome存储自动检查 | NOT VERIFIED | 用户声明无未同步内容；未连接实际Chrome，不假称自动检查；origin/profile未变、未清理或代提交 |
| 主控最终汇总写入 | FAIL（工具问题） | 所有12分项PASS后因旧result.json独占创建冲突，续跑进程实际退出1，原始失败保留；不重跑DB掩盖退出码 |
| 离线复核与汇总写入回归 | PASS | audit_completed_rehearsal.py退出0、writer夹具退出0；不是把主控退出码改为0 |
| 独立审核/10B-2批准 | NOT VERIFIED / 未取得 | 当前仅提交证据，不自动进入下一阶段 |

直接证据入口：[最终离线审计](../handoff/evidence/phase10b1/isolated-20261027t154428/final-audit.json)、[原始合并命令](../handoff/evidence/phase10b1/isolated-20261027t154428/commands.json)、[10份可公开Flyway原始日志](../handoff/evidence/phase10b1/isolated-20261027t154428/public-logs)、[最终运行状态](../handoff/evidence/phase10b1/isolated-final-runtime-check.json)。原始私有行/录音/秘密仅.local保存，公开证据保留原始路径/hash，不进ZIP。

### 4. 验证与停止

实际执行Java21 javac、Python AST/恢复顺序和旧列异常拒绝夹具、源端口/UUID拒绝负例、7578条隔离执行记录及12个实际MySQL/旧应用分项检查；离线重新验证全部备份、旧列、DDL映射、history checksum、故障残留与恢复后预期增量，退出0。未运行无关Web类型/lint/build或Playwright，未冒称UI/实听/真设备通过。

12个新容器均已停止，独立卷与故障状态全部保留。源schema仍V008，个人库未迁移；本包反映18秒备份窗口时点，不包含恢复服务后用户新增的学习增量。未来个人库迁移必须另获授权、重核新鲜备份，不能拿本包覆盖源。后续DDL变化必须重演对应双路径/恢复。

**数据安全演练技术门槛已满足；待独立复核本包和工具问题说明，再由用户单独批准10B-2。当前停止，不开始10B-2/3。**
