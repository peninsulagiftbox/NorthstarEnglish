# Phase 10B-1-R｜解除Docker阻塞并恢复安全预检

日期：2026-10-27（Asia/Shanghai）。最新状态：**Docker阻塞解除；B01/B03实际功能演练PASS，附主控汇总退出1的工具说明，待独立复核**。个人数据库未迁移，未开始10B-2/3。以下第1–6节保留各轮历史状态，最终执行见第7节及PHASE_10B_1.md“最终数据安全验收”。

## 1. 修改了什么与Docker根因

新增只读Docker诊断与受限A1预检脚本，保存沙箱内外原始对照、用户授权范围、数据库身份/权限/history和后续执行计划；原失败证据保留。未改系统socket权限、Docker context/环境配置、Docker数据目录、秘密、业务代码或历史迁移。

| 排查项 | 实际证据 | 结论 |
| --- | --- | --- |
| CLI路径/版本 | /Applications/Docker.app/Contents/Resources/bin/docker；29.6.1 | PASS |
| context/覆盖 | desktop-linux；DOCKER_HOST/DOCKER_CONTEXT均未设置 | endpoint与本机socket一致，未发现context错误 |
| 执行身份/socket | uid/euid501、gid20；socket属501:20，0755；/var/run/docker.sock指向同一实际socket | 不需要chmod/sudo |
| 沙箱内 | CODEX_SANDBOX=seatbelt；socket os.access(W_OK)=false；info/inspect各退出1 permission denied；pgrep退出3无法枚举进程 | 读取被执行沙箱阻断 |
| 经人工批准的沙箱外对照 | 同用户/context/socket；os.access(W_OK)=true；info/inspect各退出0；Docker Desktop daemon 29.6.1，backend进程查询退出0 | **证实本次阻塞来自Codex沙箱限制** |
| Docker未运行/Unix权限错误/其他原因 | 同一socket沙箱外成功，无配置修改；pgrep Docker退出1仅说明未找到该精确进程名 | 当前daemon正常，不把进程名未命中误判为Docker未运行 |

修复方式是**逐命令人工批准的沙箱外只读执行**，不是永久调整Codex或系统权限；后续普通沙箱调用仍可能失败。未使用chmod 666、sudo、关闭安全保护或重启Docker。

## 2. 授权与实际命令

用户先明确批准单次Docker只读诊断，再明确批准单次A1只读预检；两次均通过工具require_escalated执行，没有自动审批拒绝。

| 命令 | 原始退出码 | 证据 |
| --- | --- | --- |
| PYTHONDONTWRITEBYTECODE=1 python3 docs/handoff/evidence/phase10b1/docker_readonly_diagnostic.py --output docs/handoff/evidence/phase10b1/recovery-20261027/sandbox | 2 | sandbox/diagnostic.json；内部info/inspect各1 |
| 同脚本 --output docs/handoff/evidence/phase10b1/recovery-20261027/approved-host | 0 | approved-host/diagnostic.json；内部info/inspect各0 |
| PYTHONDONTWRITEBYTECODE=1 python3 docs/handoff/evidence/phase10b1/a1_readonly.py | 2 | a1/commands.json、result.json；6条外部命令均0，脚本本地断言失败 |

首次A1的脚本错误：将history总行数硬写为8，实际为历史BASELINE version0标记+8条SQL迁移，共9行，导致提前停止。没有数据库命令失败或写入。失败时脚本Assert没有消息，因此原result.reason为空；本报告补充诊断，不改写原日志。第一次执行脚本副本存于originals/a1_readonly-at-first-run.py，修改后脚本只用于新批次，不覆盖旧结果。

首次ZIP打包时，仅续跑剩余A1的单次沙箱外授权请求（a1_readonly.py --continue-after-history）仍等待答复、未执行。随后用户明确批准，实际续跑结果见下方“获批续跑结果”；没有把前两次单次批准扩大使用。

已对保存的history离线重算本地SQL逐行UTF-8 CRC32：V001–V008 **8/8与实际history校验和一致、success均1**。BASELINE0由既有DatabaseGuard的identity-only初始化调用及PHASE_08的九条history记录解释，**不是V000 SQL、不代表本轮执行baseline**。本轮不调用Flyway validate/migrate/repair/clean，不手写history，不重放V008。该离线比对不是Flyway validate实际运行结果。

## 3. 已实际通过与未验证项

### 已通过

- 原证据清单14文件在本轮编辑前全部hash匹配；原报告/README/清单已另存originals。HEAD仍为98bfedc8ac43ab68aea5447f2790cd3777b0a764，tracked与cached diff均空，无新增迁移文件；复用原V001–V008有效源码基线，不重新扫描仓库。
- 容器全ID以bbf8c3f55c02开头，名称northstar-english-mysql-01，running；project标签northstar-english-local-v1、Compose项目northstar-english-local-01，127.0.0.1:3308→3306，数据卷northstar_english_mysql_01_data→/var/lib/mysql；完整ID/挂载证据在受控JSON。
- 真实DB为northstar_english，项目身份匹配；MySQL8.4.9，server_uuid为104d5d9d-cd3f-11f1-8da4-920f115cf5cb；app/migrator两次连接指向同一UUID。没有用相似schema名代替实例身份核验。
- CURRENT_USER分别为northstar_app@%与northstar_migrator@%；实际SHOW GRANTS已取得。app有SELECT及学习表INSERT/UPDATE，migrator有CREATE/ALTER/INDEX等权限；**它们不是只读账号**。本轮每次查询显式START TRANSACTION READ ONLY，随后ROLLBACK，不进行任何负例写测试或权限变更。
- 实际Flyway history已读取：历史BASELINE0+V001–V008；SQL校验和8/8匹配，未发现failed SQL或额外SQL版本。V008结构尚须以实际列核验，不能只看history判通过。

### 当前仍未完成

有效媒体根与文件状态、浏览器未同步草稿/outbox/录音、API/Web到具体schema的连接绑定、完整备份空间需求仍不能用默认配置或旧记录判PASS。V008列、表结构/计数、容量测量和PID/cwd已有下方实际证据；媒体、浏览器缓冲与静止快照门禁仍未满足。

### 获批续跑结果（2026-10-27）

用户明确批准“剩余A1只读检查”后，以require_escalated单次执行`PYTHONDONTWRITEBYTECODE=1 python3 docs/handoff/evidence/phase10b1/a1_readonly.py --continue-after-history`，**实际退出0**，证据位于a1-continuation。未重复查询权限/history；复核同一容器与源身份，使用保存history继续校验。旧报告/交付清单/status在before-continuation-delivery另存，首版ZIP未改动且SHA-256再次匹配。

| 检查 | 状态与实际结果 | 限制 |
| --- | --- | --- |
| V008实际结构 | PASS：user_setting.recording_enabled为tinyint(1)、NOT NULL、默认1 | 仅结构核验，不重跑ALTER |
| 全表结构及计数 | PASS：取得37张表SHOW CREATE TABLE及COUNT，原始记录在schema.json/row-counts.json | 服务未暂停；分次只读事务，不是同一一致快照，不是旧列逐值对账 |
| 表容量及空闲磁盘 | PARTIAL：information_schema分配1,982,464字节，其中data_length 638,976字节；磁盘空闲70,948,880,384字节 | 不是SQL导出大小；媒体/多副本/临时空间+20%预算仍NOT VERIFIED |
| API进程归属 | PASS（PID/cwd）：9116及子进程9117，均在本项目apps/api | 未读取进程环境；命令行未出现DB/media覆盖，不足以证明有效配置 |
| Web进程归属 | PASS（PID/cwd）：17634及子进程17635，均在本项目apps/web | 未验证代理地址、监听socket或请求到具体schema的完整链路 |
| 数据库连接 | 已保存app账号可见PROCESSLIST的ID/USER/HOST/DB/COMMAND，不含INFO/查询正文 | 可见范围有限，尚未与具体进程TCP连接逐一关联 |
| 媒体/浏览器缓冲 | NOT VERIFIED：没有读取私人媒体或操作浏览器 | 有效根未证明；不得按默认路径判安全或完整 |

续跑共记录92条外部命令：90条退出0，2条pgrep -P退出1表示叶子进程没有子进程，属于预期空结果；没有SQL命令失败。所有SQL均显式READ ONLY事务并ROLLBACK。没有停服务、备份、写入或启动Spring。result.json的PARTIAL表示A1整体门禁未全通过，外层退出0只表示本次受限脚本正常完成。

## 4. 下一步与人工批准事项

具体方案见[后续执行计划](../handoff/evidence/phase10b1/recovery-20261027/NEXT_EXECUTION_PLAN.md)：一致停写SQL+完整媒体备份；新实例/账号/端口/卷/媒体；最小段落同版关系V009候选冻结；V008升级及V001空库双路径；三类故障与新目标恢复；全部旧表旧列按PK逐值核对。均为未执行计划，端口/资源及候选文件/hash尚未冻结，不能拿设计代替演练。

额外静态阻塞：当前DatabaseGuard对identity-only空目标会主动调用baseline，而演练方案要求空库路径不baseline。因此不能把旧应用启动作为空库迁移入口；需在隔离实施前设计并审核不baseline、不伪造history的专用初始化执行方式。本轮未修改该业务启动器或绕过此差异。

本轮没有暂停个人学习服务。后续必须先证明服务归属、列明中断影响/具体PID/恢复方法，再单独请求维护窗口批准。还需用户确认/保护浏览器未同步缓冲；在此之前不生成“完整一致备份”。不能因为Docker只读成功就直接停服务或迁移。

**本轮助手没有对个人学习数据库写入**，SQL执行记录包含全部只读事务和查询；未取得全局数据库审计证明，不声称期间其他进程零写入。A1不是停写快照，任何计数不能当最终逐值对账。

## 5. 交付与验收边界

证据目录为docs/handoff/evidence/phase10b1，原失败保留，新批次在recovery-20261027；Mac终端最小只读对照命令另存TERMINAL_DIAGNOSTIC.md，备用且未代用户执行。

最终ZIP、校验清单和收尾检查以recovery-20261027/DELIVERY_MANIFEST.json及相邻ZIP receipt为准。ZIP包含证据目录和两份阶段报告，可能含本机项目路径/UID/账号权限元数据，不含配置密码、私人正文或媒体；供受控独立审查。

应用编译/类型/单元/集成/Playwright：NOT RUN。本轮仅诊断/证据脚本与文档，无业务改动，未启动应用；不把机械校验当业务验证。B01、B03仍为BLOCKED；备份、升级、空库初始化、故障恢复、旧列逐值/媒体对比均未执行。停止于安全预检和独立审核，不开始10B-2/3。

## 6. 剩余预检推进与维护窗口准备（2026-10-27续记）

用户进一步授权推进剩余预检直至具备10B-2审核条件，并明确批准沙箱外runtime_media_preflight.py受限范围及必要同范围重试。用户确认实际浏览器为Chrome、origin为http://127.0.0.1:3100，并声明没有未同步草稿/待确认提交/未上传录音。工具仅连接IAB/MCP Apps，不能自动读取实际Chrome，因此该条为**用户声明**，不是浏览器存储自动化验收；未导航、刷新、清理或代提交。

### 新取得证据

- 第一次读取进程配置因sysctl缓冲大小参数EINVAL退出2，第二次因监督进程argv含子进程-jar参数而被误判多个JVM退出2；改为读取kern.argmax并仅选择java可执行进程。三次独立证据目录均保留，第三次实际退出0。不是数据库或媒体差异，没有触发reconcile。
- `readiness-20261027-attempt3/runtime.json`保存过滤后的非秘密环境、参数hash、JAR application.yml与源码一致性；Java9117实际监听127.0.0.1:8085并连接127.0.0.1:3308，配置schema为northstar_english。未发现CLI/Spring/JVM配置覆盖。Docker NAT下仍不声称每条TCP与PROCESSLIST都唯一映射，但已有运行配置和实际peer佐证；原始进程环境/密码未写日志。
- 有效录音根为用户Library/Application Support/NorthstarEnglish/recordings/northstar_english；2个ready文件共161,914字节，大小/hash全部匹配，missing/pending/deleted均0，无未知差异。content共25文件438,629字节。个人文件名/登记ID及逐文件清单仅保存在.local/phase10b1-readiness-20261027-attempt3/source-media-manifest.json（0600），公开证据仅摘要和清单hash。
- 宿主机空闲70,446,694,400字节；按8个隔离卷各4GiB、SQL保守预留64MiB、媒体多份拷贝/临时空间及20%余量，需要47,198,159,681字节，保守预留通过。Docker源卷文件系统另读df退出0，Available438,359,268KiB，未见虚拟盘容量阻塞。此为预算，非实际备份大小，维护窗口仍需重新核对。

### 已准备但未执行

- [MAINTENANCE_WINDOW.md](../handoff/evidence/phase10b1/MAINTENANCE_WINDOW.md)列出具体暂停PID、影响、备份和恢复方法。仅SIGSTOP Next17635与Java9117，监督进程/MySQL不动；静止检查后读SQL+全媒体。无论成败SIGCONT恢复同一进程，不重新启动Spring，避免源Flyway启动调用。160秒超时、180秒独立恢复watchdog作为兜底；恢复后检查相同PID状态和现有API health。
- maintenance_backup.py生成原始SQL dump、全旧列按PK的规范化快照，以及保持FK开启的依赖排序restore.sql；媒体完整复制/hash，源前后旧列/结构/文件逐值比较。**脚本尚未获维护窗口批准、未执行，备份仍不存在。** 原始dump可能包含MySQL会话级FK关闭指令，不直接执行；隔离目标只使用不关闭FK的restore.sql并实际恢复验证。
- 4份最小候选V009_01–V009_04位于证据目录candidate，SHA-256在candidate-manifest.json；不进入源应用迁移路径、不改V001–V008。白名单仅新paragraph表与sentence.paragraph_id，其余原列不变。未应用到任何数据库，不能签SQL行为PASS。
- MigrationHarness.java为独立隔离CLI，拒绝源端口和server_uuid；空库使用Flyway BEFORE_MIGRATE callback初始化project_identity，计划由Flyway自身创建history，不调用baseline。已Java21 javac实际编译退出0，**初始化时序仍待独立MySQL验证**，没有把编译当解除空库门禁。
- 三个Python工具AST与合成循环FK/作文父链恢复顺序夹具验证通过；未执行项目业务编译、单元/集成或Playwright。源码检查不是备份可恢复性证明。

截至本次交付，维护窗口问题已提出但尚未获明确答复，未暂停服务、未生成SQL备份、未创建隔离数据库或执行候选。B01/B03仍BLOCKED；下一步为批准具体维护窗口后备份、实际隔离恢复/双路径/故障演练，并提交独立复核。不能自动开始10B-2。

## 7. 获批备份与C–F演练最终执行记录

用户随后明确批准维护窗口，并明确批准完整12目标隔离演练；额度/会话续接时按既有状态续跑，没有因续接重复暂停源服务或重建已完成目标。

### 维护窗口与源保护

第一次备份脚本在任何暂停信号前因误预期root@localhost退出2，实际同一UUID/项目账号为root@%；保存该失败、只修正断言，无账号/权限修改。第二次实际退出0，15:44:29.123944–15:44:47.399054（+08:00）暂停两个已核实子进程约18.275秒；finally恢复同一PID，源Spring未重启，health恢复UP/V008。备份32文件1,298,897字节，完整SQL/规范化旧列/媒体均受控保存在.local。详情maintenance-authorization-and-result.json及backup-20261027T154428。

原始mysqldump不直接执行其中可能关闭FK的会话指令；实际隔离恢复使用从同一静态规范化快照生成的完整restore.sql。该SQL没有关闭FK/禁用键或DROP，按依赖创建新表、按父链插入，lesson/version循环按原V002方式延后创建关联约束；全部恢复后实际schema/旧列/媒体与源静态快照一致，证明不是只备份文件不恢复。

### 全部12个独立目标

命名空间northstar-english-phase10b1-20261027t154428。下列目标各自独立容器/卷/随机账号秘密/server_uuid，全部host绑定127.0.0.1，schema虽同名northstar_english，但UUID/ID/卷/角色/地址均与源分离；完整身份证据在各role-identity.json及isolated-final-runtime-check.json。全部按顺序运行、目前停止，原卷和失败状态保留。

| 角色 | DB/API端口 | 实测结果 |
| --- | --- | --- |
| upgrade | 3313 / 8093 | 原备份SQL恢复、旧应用读、4个候选逐版本、旧列/新关系、约束负例、重复启动PASS |
| empty | 3314 / 8094 | V001–V008从空库无baseline；隔离原Demo播种后同候选；schema一致与重复启动PASS |
| fault-ddl-01 | 3315 / 8095 | CREATE paragraph后SIGNAL中断，表已提交/history旧基线，PASS |
| fault-ddl-02 | 3316 / 8096 | 增新列后中断，列NULL/表已提交/history旧基线，PASS |
| fault-ddl-04 | 3317 / 8097 | 最后FK/NOT NULL DDL后中断，完整新schema而history旧基线，PASS |
| fault-history | 3318 / 8098 | DDL已成功，Flyway history INSERT实际被1142权限错误拒绝，无009记录，PASS |
| fault-dml | 3319 / 8099 | 两条DDL保留，回填事务SIGNAL失败后paragraph零行/新列全NULL，PASS |
| recover-ddl-01 | 3320 / 8100 | 从原备份到另一新实例，旧读/真实隔离写作/幂等/重启逐值与媒体PASS |
| recover-ddl-02 | 3321 / 8101 | 同上，独立新UUID，PASS |
| recover-ddl-04 | 3322 / 8102 | 同上，独立新UUID，PASS |
| recover-history | 3323 / 8103 | 同上，独立新UUID，PASS |
| recover-dml | 3324 / 8104 | 同上，独立新UUID，PASS |

故障角色8095–8099是预留API分配值，未启动应用，避免在部分schema上触发启动写入；只在新恢复目标启动固定旧应用验证。没有把这些故障角色的API端口称为实际监听证据。

没有对故障目标repair/clean、编辑history、关闭约束、删除或覆盖失败副本；恢复总是另外的新目标。5次写作续学是真实隔离HTTP正式提交和DB evidence/receipt，并用同event重试只新增一次；它们是测试样例，不是个人学习成绩或模型评分。原不可变行/父链及其他旧行保持逐值不变，只有目标草稿/进度及1个新revision/evidence/receipt为允许变化；重启后再次逐值一致。

### 问题与修复必须保留

| 事项 | 实际退出码 | 处置和证据 |
| --- | --- | --- |
| 初始全组执行 | 2 | 已通过4迁移/约束/第一次重复启动后，第二次API前端口检测误判TIME_WAIT；实际lsof无8093监听者。执行前脚本与result/commands保留于execution-attempt1-* |
| 定向续跑 | 1 | 用SO_REUSEADDR修正后，仅续跑剩余启动验证，未重放已通过DDL；继续完成其余11目标。所有12分项PASS后，独占创建旧result.json触发FileExistsError；错误处理再次碰撞。controller-finalization-failure.json保留真实退出1，未改为0 |
| 汇总写入修复 | 0（夹具） | 改为成功/唯一失败新文件名，旧result保留；controller-writer-regression.json验证旧字节不变、新汇总可写，未重跑DB或伪造整组退出0 |
| 离线最终审计 | 0 | audit_completed_rehearsal.py重新检查12分项、备份hash、所有旧列/白名单、三DDL边界/登记/DML残留、5恢复续学和重启、实际checksum/约束、12实例已停止。final-audit.json为当前结论，旧result.json仍是历史BLOCKED |

最终共有7578条合并隔离执行记录；10份Flyway原始日志已检查源/目标秘密及个人文本、零处需脱敏，导出字节与原件完全一致，含upgrade的8条新语句callback、empty的53条原链语句及同8条候选语句、真实登记失败。其他包含个人HEX行值的原始日志/快照只存.local，公开记录有实际路径/hash；不将私人内容塞入ZIP。

### 最新验收和停止点

六类证据与B01/B03均为实际PASS，根目录STATUS.json和final-audit.json给出当前机器可解析结论。主控汇总工具问题记FAIL/退出1，离线审计和修复夹具PASS/退出0；不混淆功能验收和程序退出码。源个人库仍V008且原PID健康，没有重新暂停源服务。实际账号权限已补充只读SHOW GRANTS，root本身可写，所以零助手写入结论依据执行日志和窗口前后全量比较，不声称取得全局审计。

实际Chrome未自动读取存储，用户声明无未同步内容；UI/实听/真设备和正式素材授权不在本次PASS内。应用业务源码未变，因此不重复无关前端build；Java迁移工具实际编译、MySQL集成和旧应用真实API路径已经执行。独立复核仍PENDING；只有独立复核本包（含工具问题）并单独批准后才能进入10B-2。本轮停止，不自动开始10B-2/3，不迁移个人库。
