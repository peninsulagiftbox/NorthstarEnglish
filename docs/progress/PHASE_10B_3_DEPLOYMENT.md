# Phase 10B-3 审核后的 GitHub 提交与本地部署

日期：2026-10-29（Asia/Shanghai）。用户明确要求“审核通过，提交github并在本地进行部署”。**个人库009.05→009.15、前后端部署及最终只读对账全部PASS，服务保持运行。** 本轮不导入课程、不转移旧成绩，不进入10C。

## 1. Git范围及并行UI保护

- `3c48348`：提交此前已验收的目录/学习路径UI及两份报告。对CSS/CatalogPages用已验收blob暂存，工作区后新增的目录弹窗字节不变。
- `2a4079f`：提交10B-3稳定身份、映射、生命周期、发布/CAS/审计、十条迁移、测试、文档和受控部署入口；普通push至origin/main，未强推。
- 部署时确认另一聊天已将目录弹窗验证并上线，故最终前端保留这两份现有已部署UI。它们仍属于另一聊天的未提交改动，本轮不代提交、覆盖或回退。该范围及逐文件hash见source-commit.json，只有globals.css/CatalogPages.tsx与2a4079f不同，10B-3输入均匹配提交。
- 私有SQL、学习记录、录音、密码、原始运行证据与构建均未纳入Git；本轮源码/报告使用显式路径暂存，没有git add -A。

## 2. 部署候选与维护门禁

发布批次 `20261029T144934`。复用已验收的最终后端JAR；独立副本重新执行Node测试/类型/lint/build，将Next同源代理构建为实际8085 API，未覆盖运行中的.next。

- 后端JAR SHA-256：`c4243bca0b7062e2c94bbe6e78fe7e5603791173c615959a4819a5f6ecdfc310`。
- 前端BUILD_ID：`udzk9U3KedJsnKrExMKWg`。
- 保留origin：Web `http://127.0.0.1:3100`、API `http://127.0.0.1:8085`、MySQL回环3308；未更换全局Java/Node、密码、容器或数据卷。
- 新维护入口 `scripts/phase10b3/ApprovedIdentityMigration.java` 固定23份SQL的文件集合与SHA-256，只允许009.05基线和十条预期pending版本；源端固定端口/UUID，演练端要求独立UUID/端口。无授权标识、错端口、改DDL的三项负例均在JDBC连接前退出1；正例及源迁移使用同一个已编译class。
- 独立发布CLI和业务current发布不是本次DDL入口。维护入口不启动Spring/Flyway播种器、不baseline/repair/clean，不修改学习记录。

## 3. 新鲜备份、隔离恢复与个人迁移

仅停止已核验监听PID、supervisor与cwd归属的本项目Web/API，数据库保持运行；确认源库无其他连接/活动事务，采集38表逐PK快照、结构/数据SQL、内容及全部录音文件/状态。保留原JAR与原Web构建，浏览器origin不变、不清IndexedDB、不提交或丢弃未同步缓冲。

新鲜备份：`.local/phase10b3-release/20261029T144934/backup/`，清单包含31份文件；清单SHA-256：`baff2afa47cd7270681f0dc39ecac3a2285dfb522e8eb73791cebcbdd12ba4c2`。私人原件仅留受限.local；备份不是允许覆盖个人库的授权。

先在新命名隔离容器/卷恢复该备份，恢复后38表完整一致；以同一编译入口实际应用十条新迁移，再核对旧列/PK/FK/CHECK、20句/2段身份登记、空映射/验证/发布审计表、原current和媒体。候选在副本普通启动两次，43表与媒体一致后才允许源迁移。

个人源库的同一入口执行退出0，实际迁移十条并Flyway validate通过。V001–V009.05和已执行V009.06–.15文件字节不改，既有history原行保留。MySQL DDL分别提交，不宣称可以把整套DDL当业务事务回滚。没有repair、写history、清卷、源库恢复或重复执行迁移。

源库迁移前后，38张旧表的原有列按PK逐值一致；只增加批准的新表/列/约束和history行。原Demo物理ID、段句归属、payload/manifest/hash、音频、学习事件/回执、作答、草稿、作文父链、录音状态与复习数据均保留。Demo仍published+legacy_unassessed、release_ready=false及原本地来源审查边界，不升级教学或正式素材许可。

## 4. 实际安装与验证

| 检查 | 实际结果 |
| --- | --- |
| 独立生产前端 npm test / typecheck / lint / build | Node28项通过，四命令退出0；代理8085 |
| 已验收后端与构建输入 | JAR复用c4243b…，API/SQL与验收hash一致，部署不以重新打包冒充新增DB测试 |
| 维护入口缺授权/错端口/改字节 | 各预期退出1，连接前拒绝 |
| 新鲜备份恢复＋同编译入口迁移 | 退出0；旧列、媒体及两次新JAR启动一致 |
| 个人库009.05→009.15 | 退出0，恰十条，末次validate通过 |
| 安装后新JAR两次启动 | 43表逐值及媒体完全一致，原current未覆盖 |
| Web/API及新前端 | 健康UP/009.15、四册仍0实际课、Demo保留、无隔离夹具进入个人库 |
| 固定Playwright只读验收 | passed=true；稳定身份10个、两版及唯一current、legacy边界、原目录弹窗、224px侧栏/76px播放器通过，pageErrors=[] |
| 浏览器写保护 | 路由阻断所有非GET/HEAD/OPTIONS；实际写请求0，个人学习测试提交0；不将此称为在个人库重跑练习闭环 |

本阶段原工程Java27/Node28/Python15及隔离Playwright证据仍见PHASE_10B_3，本轮不冒称全部重新执行。部署新增同入口、新鲜备份及运行验证；实体麦克风、另机、正式素材授权仍NOT VERIFIED。

截图：`output/playwright/phase10b3-deployed-catalog.png`、`phase10b3-deployed-workspace.png`；已查看目录截图。所有浏览器会话结束后关闭，个人前后端保留运行，演练容器停止、卷保留。

## 5. 文件、证据与停止点

新增受控维护入口/部署器、只读浏览器脚本及本报告；更新README与阶段报告后续状态。精确argv/cwd/实际退出码/日志hash、源/目标身份、备份清单hash、旧列和媒体核对位于本地 `docs/handoff/evidence/phase10b3-deployment/20261029T144934/`；源码公开，私有数据/凭据/SQL/原始证据不上传。

最终live-final-verification.json确认两服务UP/009.15，浏览器验收后43表仍与迁移后快照完全一致、媒体hash一致；演练目标已停止且卷保留。主站前后端继续运行。

本轮仅完成已授权的GitHub与本地部署，不推进10C。并行目录弹窗源码/报告/证据仍留原聊天工作区，不将其列为本轮已提交。
