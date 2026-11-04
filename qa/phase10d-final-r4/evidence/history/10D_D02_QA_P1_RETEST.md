# D02 P1 修复候选独立 QA 复测

日期：2026-11-02。角色：独立 QA。**本次定向复测 PASS，关闭 QA-D02-R4-BUG-001 及同路径合法游标 422 缺陷。D02 整体维持 CONDITIONAL PASS，等待最终签收范围确认。**

## 候选与隔离

- HEAD 基线 a5084cb4442a7b78afad5c920459c22f02f679ce + CORE 冻结包；在 QA worktree 的 `.local/qa-p1-retest/d02-p1/source` 解压后测试，无业务或测试预期修改。
- 源码输入清单 SHA-256：31131ea6b5a92b87ff12d32e61ad6fef9896e2028d16ecba5b7e9368f60b1a6c；336项输入测试前后均逐项校验通过；交付包363文件校验通过。
- 实际 HTTP 运行 JAR SHA-256：771a72e8ea66304ebfb2e4b5e873d759c60a176fc2dd09fdfe31648da7ff92c6。Maven 在冻结源码上单独编译运行测试，不把旧构件作为新候选结果。
- 独立可写测试库：新容器/卷 northstar-qa-p1-retest-20261102，MySQL 8.4.9，127.0.0.1:3374，UUID f6c04e45-d681-11f1-97a5-bae983ea433f，schema northstar_phase01_test。运行账号仅 SELECT/INSERT/UPDATE/DELETE；migrator 拥有本 schema 的测试/迁移权限。
- 原失败现场3364：northstar-d02-risk-20261102-empty，UUID e6d3595e-d67d-11f1-a92d-8696ac132eb0，仅只读访问；原库59表在全部HTTP/浏览器验证前后哈希一致。
- QA独立前端构建 BUILD_ID：MP13aIvur8Ry21lPYxbdt；API8186/Web3197回环绑定。Playwright独立会话 northstar-p1-independent-20261102，1440×900。

## 实际结果

| 验证 | 结果与证据 |
| --- | --- |
| 冻结包/源码完整性 | PASS；363包文件、336输入全部匹配，未修改冻结源码 |
| D02、D01、10C-2-R1 真实 MySQL/HTTP 回归 | PASS；ConceptReviewIntegrationTest、KnowledgeSourcesIntegrationTest、QuizScaleIntegrationTest、QuizReportR1IntegrationTest，7/7，失败0、错误0、跳过0；regression.log，退出码0 |
| 受限分页边界 | PASS；上述D02测试含混合/全撤回来源、满页受限、默认与1/20/精确整页、连续到空页、白名单、非法游标422；每条来源由真实错误Attempt产生 |
| 原83来源分页 | PASS；默认20→5页；limit1→84页（含末尾空页）；20→5页；83→2页；100→1页；每种完整读取83条，无重复、遗漏，游标严格推进 |
| 来源权限 | PASS；82条restricted只含允许字段，1条可见；visibleSourceCount=1；撤回正文与音频HTTP拒绝；failure-db-read-checks.json |
| 原库历史保护 | PASS；全59表整个复测前后哈希相同，whole-run-db-unchanged.json |
| 新库迁移/收尾 | Flyway至012.11全部success；概念card/source/result均清理为0；exercise_attempt保留4条测验套件数据，未冒称全部学习表为空；db-after.log |
| 前端构建 | PASS，真实退出码0；browser-build.log |
| Playwright真实页面 | PASS，真实退出码0；82受限/1可见，受限占位正确、撤回课程标题未出现；browser-check.log、review.png |

本次源码改动面限定在Controller和集成测试，V012.01–11字节与冻结输入一致。测试原始失败/修复前NPE由上轮风险报告与CORE红测保留，本轮所有成功结果来自本次独立执行。

## 环境失败记录

首次MySQL TCP握手未就绪（退出1）；QA新建project_identity误用继承字符集，导致V001外键类型不兼容（退出1）。两项均在业务测试前，日志保留。只重建本轮新3374schema，并以仓库要求ascii_bin身份列重新初始化；未repair Flyway或修改迁移。冻结zip未带mvnw执行位，使用bash运行同字节脚本后正常。不得将上述环境失败计作业务测试通过或业务缺陷。

## 范围和结论边界

本次PASS只关闭受限分页500/合法游标422并确认相关7项回归。未在新JAR上重复16写者×10轮、备份恢复、逐DDL故障注入、所有端口重启/断网双Tab流程及完整Node单测/lint；这些只保留各自旧候选历史证据，不迁移为本新JAR实测PASS。因此不以本轮定向PASS宣布D02全矩阵无条件PASS。

未发现本轮范围内来源泄露、跨概念关联、CAS丢更新、客观成绩污染或原失败库历史变化。未连接3308、未改CORE主树业务、未提交/合并/推送/部署、未进入10E。只停止本轮创建的API/Web/浏览器会话；新QA测试库及原失败库保留。

证据：qa/phase10d2-p1-retest/evidence；新包 output/review/northstar-phase10d2-p1-qa-retest-evidence.zip，附SHA-256。解压后运行 `python3 verify.py` 验证全部白名单文件。
