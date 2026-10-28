# 个人学习库迁移：执行与验证

> 2026-10-28最终结论：个人学习库已由V008迁移至V009.04，四步Flyway均退出0、旧列逐值和媒体hash全部一致。API/Web已恢复，http://127.0.0.1:3100 可用，两次API启动及Web恢复后全表逐值不变。用户已明确豁免独立复核；不将豁免记录为独立复核PASS。下文早期准备及BLOCKED记录为历史，最终证据采用20261027T204758批次，旧失败不删除。

2026-10-27（Asia/Shanghai）。用户本轮明确要求“现在迁移个人学习库”，已取得迁移意图授权；此前10B-1仅隔离演练的授权边界不再被误作永久禁令。本轮尚未连接源库、停服务、执行DDL/DML或迁移。10B-2/3仍未开始。

## 当前门槛

- 10B-1的B01/B03功能证据PASS；最终主控退出1的汇总写入故障保留，离线审计退出0。不能声称主控完整执行退出0。
- 独立复核仍为PENDING，未收到独立复核结论。依据`docs/phase10/04_MIGRATION_PLAN.md` §2.1、§4第5项，现有库迁移须同候选演练通过并审核、新鲜备份、整个窗口停写及执行授权。
- 原用户工作原则第4条要求停个人学习写服务前单独取得明确批准。此前18秒窗口的批准已执行完毕，不覆盖本次新窗口。
- 冻结四份候选大小/SHA-256、基线HEAD及最终审查ZIP的SHA-256/CRC已本轮离线核对，见`docs/handoff/evidence/personal-migration-20261027/offline-precheck.json`。这是工件核验，不是当前数据库身份或数据完整性证明。

## 待执行的具体范围与停止条件

1. **只读重核**：历史目标为容器northstar-english-mysql-01、127.0.0.1:3308、schema northstar_english、project_key northstar-english-local-v1、UUID 104d5d9d-cd3f-11f1-8da4-920f115cf5cb。重新核验完整容器ID、卷、账号权限、Flyway全部history/CRC及旧结构；重新核对API/Web PID、cwd、连接及媒体根。历史PID不是当前执行许可；任何身份/迁移范围变化即停止。
2. **停写方案**：仅暂停本项目API/Web实际写服务；历史Java9117/Next17635需重新确认。维护期间页面/API不可用，禁止继续学习/重试。先确认浏览器无新增未同步内容，再审批准确PID和停写时长。MySQL及其他服务不动。
3. **新鲜一致备份**：保持停写，取得本次SQL、全表旧列逐值快照、完整媒体/content及SHA-256清单；验证备份恢复到新隔离目标。旧20261027T154428备份不可覆盖后续学习增量。容量不足、备份/恢复不符即停止，不迁移源。
4. **迁移工具与应用兼容复核**：现有MigrationHarness明确拒绝源端口/UUID，不能删除其保护后直接复用；需另行准备绑定本次目标身份和批准文件hash的受控入口，保持旧隔离工具不变。核对新schema下固定应用读取/正常重启及备份导出恢复工具兼容性（现scripts/data-transfer.py仍校验008），未完成不得开放学习写入。
5. **仅同一冻结候选**：V009_01、V009_02、V009_03、V009_04，hash逐项沿用原candidate-manifest；只增paragraph表、sentence.paragraph_id及同版约束，回填仅两版Demo新字段。不得修改V001–V008、旧列值、其他业务或导入教材。每文件前后记录实际schema/history、日志及退出码。
6. **核对后恢复服务**：逐PK比较全部旧表旧列、原内容hash、事件/回执、作文父链、复习和录音状态；新增内容只允许冻结白名单；全部媒体hash不变。验证只读应用契约和迁移可重复校验，再按批准方式恢复本项目服务。不往个人库写入测试作答。
7. **失败策略**：DDL不能整体事务回滚。迁移开始后的任何错误或差异立即保持停写，保留真实schema/history；禁止repair/clean或自动SIGCONT。优先从本次备份恢复到另一个新目标并验证，切换/恢复须事先批准其准确范围。旧备份脚本的180秒自动恢复watchdog只适用只读备份窗口，不能直接用于个人库DDL窗口。

每一步实际命令、退出码、身份摘要及对账结论将写入新证据目录，不改写10B-1原日志。私有SQL、正文、媒体及凭据仍只存.local受控目录，不进入公开证据包。当前等待独立复核结论及本次维护窗口批准；尚不具备准确停写时长与失败切换目标，不能假称已准备可执行的最终窗口。

## 本轮实际环境检查：BLOCKED

执行已批准范围内的沙箱外只读命令：`PYTHONDONTWRITEBYTECODE=1 python3 docs/handoff/evidence/phase10b1/docker_readonly_diagnostic.py --output docs/handoff/evidence/personal-migration-20261027/docker-readonly`，实际退出2。Docker CLI、context查询退出0；Docker info和源容器inspect退出1，Docker/com.docker.backend进程查询均退出1。原始命令、时间、stderr和socket状态保存在该目录diagnostic.json。

当前daemon不可访问，不能沿用此前正常运行的环境证明；立即停止，不启动Docker、不切换context、不启动应用或数据库、不执行SQL。须先恢复用户管理的Docker Desktop环境并重新核验源身份，才能提出准确维护窗口或迁移。独立复核仍待提供，源库未连接/未写入。

## 2026-10-28｜最终执行与验收

### 授权与范围

后续用户明确要求“自己启动，完成迁移”，并对单独询问答复“明确豁免，按冻结候选完成迁移”。原始授权记录见`docs/handoff/evidence/personal-migration-20261027/authorization.json`；未宣称完成独立复核。执行时API/Web原进程均已不存在，8085/3100未监听，源schema无其他连接/事务，因此无需暂停旧服务；整个备份/迁移期间未开放学习服务。仅启动Docker Desktop和已核验完整ID的原MySQL容器，未重建卷、改密码/权限或启动其他项目服务。

个人库**本轮确实发生授权写入**：四份冻结候选DDL、新paragraph两行、20句新增paragraph_id回填及四条Flyway history。没有测试学习提交、旧列改写、源恢复、repair/clean、删表/删卷或全局版本修改。10B-1“未写源库”结论只属于当时演练，不适用于本轮。

### 工件与文件

- 源码基线HEAD仍为`98bfedc8ac43ab68aea5447f2790cd3777b0a764`，无提交/推送。V001–V008字节与HEAD及数据库CRC32均匹配。
- 正式迁移目录新增`V009_01__paragraph_table.sql`、`V009_02__sentence_paragraph_column.sql`、`V009_03__demo_paragraph_backfill.sql`、`V009_04__sentence_paragraph_constraint.sql`；与10B-1冻结候选四文件逐字节/hash一致，未扩展DDL。
- `ExportController.java`将paragraph纳入不可变CONTENT校验；`scripts/data-transfer.py`仅新增接受009.04（保留008，拒绝009.03/未知版本），服务端仍核对实际当前schema/signature/表结构；对应Python用例更新。
- 实际新JAR SHA-256为`b6d4dcc1f3b8e84bdcb25c993f55448b286dabe5271084dd84bcea61a3382241`；它包含上述备份兼容改动，因此**不是**原隔离候选JAR的哈希。该新JAR在本轮新鲜隔离副本、另一V009恢复实例和源库重复启动分别验证通过。
- 新受控工具与原始证据均在`docs/handoff/evidence/personal-migration-20261027/`，原隔离MigrationHarness的源拒绝保护未修改；本轮用独立ApprovedPersonalMigration入口固定源UUID/3308/schema/账号/项目和四文件hash。

### 新鲜备份和证据入口

私有备份位于`.local/personal-migration/20261027T204758/backup`，包括mysqldump、保持FK开启的依赖排序restore.sql、全部旧列规范化快照和完整录音/content；不进入ZIP。完整性清单及其hash见该批次result.json。迁移前再次比较源全表/结构/媒体与该备份，完全一致，避免沿用过期时点覆盖学习增量。

当前证据根为`docs/handoff/evidence/personal-migration-20261027/`：

| 验收 | 结果 | 证据 |
| --- | --- | --- |
| 实际源身份/旧history/旧迁移hash | PASS | resume-readonly-20261028.json、20261027T204758/source-readonly-commands.json、personal-execution/account-grants.json |
| 新鲜SQL+媒体完整备份 | PASS | 20261027T204758/result.json、私有SHA256SUMS.json；执行前逐文件及源当前值复核 |
| 本次备份恢复、同候选升级、重复启动 | PASS | 20261027T204758/isolated-commands.json、isolated/各阶段摘要；DB3330/API8110独立身份 |
| 新JAR导出/CLI备份/段落篡改拒绝 | PASS | 20261027T204758/application-compatibility/result.json、commands.json；篡改paragraph预检实际422 |
| 完整V009 SQL/媒体恢复至另一新实例与重启 | PASS | application-compatibility/fresh009-restored-v009-summary.json、after-restart-v009-summary.json；DB3331/API8111 |
| 个人库四步迁移、逐步旧列/约束/history核对 | PASS | 20261027T204758/personal-execution/commands.json、after-009.*.json、flyway-009.*.log；四个迁移进程均退出0 |
| 最终Flyway validate | PASS | personal-execution/flyway-validate.log，退出0；旧history不改，新四行CRC32匹配 |
| 源库旧行逐值/新字段白名单/媒体hash | PASS | personal-execution/result.json及私有source-after-009.*.json；schema与新鲜演练逐表相同 |
| 源新JAR两次启动和实际API读取 | PASS | 20261027T204758/service-verification/result.json、events.json；38表所有旧/新值在启动前后完全一致 |
| Web3100→API8085、录音bytes/hash、V009导出 | PASS | service-verification/result.json、final-runtime.json；Web路由已核对 |
| 私有原始日志完整性 | PASS（最新批次） | final-integrity.json；两个工具阶段日志目录已分离，所有命令记录的原始log SHA-256一致 |
| 独立复核 | WAIVED BY USER | 未进行独立复核，保留原10B-1主控退出1说明 |
| 真设备录音/实听/浏览器UI自动回归 | NOT VERIFIED | 本轮未冒称通过；不操作用户Chrome缓冲，不清理或代提交 |

原始源为37表，迁移后38表；旧history9行保留，加4条成功SQL记录，共13行（含历史BASELINE0）。新增paragraph2行、20句关联符合固定两版Demo白名单；旧行ID、原内容/hash、126条receipt、30条event、3条作文版本及父链、4条复习卡状态、2条录音登记及全部媒体均逐值保持。未向个人库写入任何合成学习记录。

### 真实失败与修复

1. 最初Docker daemon不可达；经用户要求启动Docker Desktop，核验原容器后只启动该容器。无chmod/sudo/修改socket安全保护。
2. 20261027T204058预检工具误把catalog-only册计作lesson，实际Demo lesson为1；源只读，无DDL。修正工具断言，原退出2保留。
3. 20261027T204151/application-compatibility-attempt1在隔离MySQL启动尚未监听时查询，ERROR2003/退出2；增加有界就绪探测，不把启动命令成功当daemon ready。
4. 20261027T204151功能通过后发现两个工具阶段复用私有日志索引，430份旧raw log的hash不再匹配。该批次保留并标SUPERSEDED_FOR_RAW_LOG_INTEGRITY，详见evidence-integrity-issue.json；未把它作为最终迁移证据。分离日志目录后重新生成20261027T204758的备份、隔离演练及应用兼容证据，原始日志hash全部通过，再执行个人库迁移。原10B-1证据未受影响。
5. 中断恢复后只读确认源仍V008、新批次备份及工件hash正确，才续跑缺失步骤；没有重复执行已经成功的源DDL。源执行、Flyway validate、服务恢复验证进程均实际退出0。

### 执行命令与验证

精确SQL/参数/原始退出码见上述各commands.json/jsonl与Flyway日志；关键入口：

```text
open -a Docker
docker start bbf8c3f55c023dd7e16377417e31b54c742cb3ecf109fd57f22c152babc58fd0
PYTHONDONTWRITEBYTECODE=1 python3 docs/handoff/evidence/personal-migration-20261027/prepare.py --backup-and-verify-isolated
PYTHONDONTWRITEBYTECODE=1 python3 scripts/local.py exec ./apps/api/mvnw -f apps/api/pom.xml package
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s scripts/tests -p test_data_transfer.py
PYTHONDONTWRITEBYTECODE=1 python3 docs/handoff/evidence/personal-migration-20261027/verify_application.py 20261027T204758
PYTHONDONTWRITEBYTECODE=1 python3 docs/handoff/evidence/personal-migration-20261027/execute.py --execute-approved-personal-migration 20261027T204758
PYTHONDONTWRITEBYTECODE=1 python3 docs/handoff/evidence/personal-migration-20261027/finalize_services.py 20261027T204758
```

构建退出0：20条Java测试中12条执行通过、8条DB环境门控跳过，零失败/错误；实际隔离数据库验证另有证据，不把跳过算通过。Python2条测试通过，AST及git diff --check通过。未改Web源码，未重复无关Web构建或宣称Playwright已跑。

### 交付与停止

API/Web实际监督PID、子进程、cwd和两端health UP/009.04见final-runtime.json。学习地址仍为`http://127.0.0.1:3100`。本轮新建隔离容器均停止并保留卷，源MySQL和学习服务正常运行。没有清卷、删除失败副本、导入真实教材或开始10B-2/3。

新增候选在未来空库仍需遵循已演练顺序：V001–V008→旧Demo播种→V009，而非让旧ContentSeeder在最终NOT NULL结构下首次插入无paragraph_id的新句。本轮是已有两版Demo的个人库升级，不宣称完成10B-2的新空库初始化能力。私有数据不纳入公开证据ZIP；汇报后停止，等待审核。
