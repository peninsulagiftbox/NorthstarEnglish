# Phase 10C-2 补验与纠错

日期：2026-10-31（Asia/Shanghai）。基线提交 `ff0dbe1`，本轮候选由工作区SHA-256绑定，见本地 `docs/handoff/evidence/phase10c2/retest-source-binding.json`。用户要求补测未测项、修复错误并更正结论；本轮不提交、不推送、不覆盖个人已部署JAR/Web、不修改个人库。

## 1. 实际修复

| 问题 | 修复及证据 |
| --- | --- |
| 测验历史把缺少逐题明细的run固定标记为verified=true，与报告口径冲突 | 在QuizSets中复用真实计数核验，历史和报告逐轮均使用同一实现。新增真实MySQL测试构造不完整历史，修复前失败、修复后通过。没有改写旧run或回执 |
| `/reports?setId=...`过滤已生效，但`quizScope`漏回显setId | 补回setId；JUnit及真实HTTP补验核对筛选范围与分母 |
| 新协议空答案被DTO的min=1拦截为400，违反计划的422业务拒绝约定 | 去掉重复的最小条数注解，由题集答案键精确匹配统一返回422；保留非空值、选项与最多100条的入口约束，旧三题DTO不变。真实HTTP修复前得到400，修复后422，失败无半轮残留 |

涉及生产文件：`QuizSets.java`、`QuizReviewController.java`、`ReportController.java`。没有修改已应用的V010/V011迁移字节，也没有开放生产故障注入接口。

## 2. 未测项补验结果

| 原缺口 | 实际执行与结果 |
| --- | --- |
| 单题成功交卷 | `QuizScaleIntegrationTest.singleQuestionSetSubmitsWithVerifiedRun`：真实HTTP交卷、总数/提交数=1、answer/item/evidence各1条、历史verified；PASS |
| 四类事务故障 | 测试专用Primary bean覆盖QuizFault：首题写后、末题写后、父回执写前抛错；通过事务同步器在beforeCommit抛错。每次实际HTTP500后，用独立数据库连接对run/answer/item/attempt/evidence/receipt/review_item/review_source/progress九类全表逐值对账，完全一致；关闭故障后原event重试成功，再重放不新增run。四类均PASS |
| 5/12/100题浏览器 | 固定Playwright CLI + Headless Chrome，真实后端/数据库，无假API成功响应。逐题作答、完整字段渲染、ordinal顺序、未完成禁交、草稿落盘后刷新、跨课和跨版本隔离；每种规模注入一次HTTP500，刷新后重试原path/body/event；再提交全错第二轮，两轮分母/题面快照完整保留。全部PASS，pageerror=0 |
| 100题完整性 | 浏览器实际100个题目控件，原请求100条答案，历史每轮100条逐题快照；本轮浏览器重试交卷约239ms（包含浏览器等待，不是性能基准）。最终JUnit100题交卷162ms，request=5303B/response=28101B，无截断 |
| 拒绝分支 | 空答案、错选项、跨课/跨版、旧hash、path/body题集不一致、撤回版410、许可失效409，逐次核对失败前后相关对象计数不变；默认题集唯一约束通过 |
| 报告口径 | 同课5题与12题版本各两轮，汇总17/34=50%；setId筛选分母10且scope正确；pause/skip不改变测验指标；空时间窗分母0；不支持purpose返回422。PASS |
| 迁移DDL故障 | 新容器恢复固定009.15备份→010.06；拒绝migrator的CREATE权限，V011.02失败、exercise_set未创建，旧表旧列逐值保留。PASS |
| 迁移DML故障 | 新容器先迁移011.05，通过测试专用触发器拒绝回填item；V011.06失败，set/item/run_item均为0、run.total_count全NULL，旧行不变，证明回填事务回滚。PASS |
| DDL领先history | 新容器拒绝Flyway对011.02的history插入；实际exercise_set表已存在、011.02成功记录不存在，脚本识别此状态并保留失败目标。PASS |
| 新目标恢复 | 另建容器/UUID，从同一固定备份恢复并迁移011.09；原表旧列逐值保留，历史6条item补齐，不repair、不clean、不手写history。PASS |
| 异常历史拒绝 | 新隔离目标中使旧run汇总与原答案不一致；V011.06拒绝，题集回填无残留，异常输入旧值保持原样，未通过篡改history或修个人成绩绕过。PASS |
| UQ/CHECK/FK | 使用真实迁移建立的未冻结set/item，验证合法插入；重复成员/ordinal报1062，ordinal=0报3819，跨句/跨版本引用报1452，每次失败后合法item仍只有1条。PASS，原数据保全 |

题集数据库约束为同版本同purpose唯一；不存在正式协议支持的同版本多默认题集切换。跨题集草稿按不同版本/课的真实setId/hash以及额外过期scope键检验，不伪造生产成功响应。

## 3. 命令与原始证据

构建、测试、媒体和服务均位于`.local/phase10c2`，数据库端口3334，API8175/Web3195；所有数据库写入先核对专用容器标签、ID和UUID，不使用个人3308库。浏览器补验结束后仅停止本轮启动的隔离服务，失败迁移容器已停止，卷及原始日志保留。

| 命令入口 | 结果及本地日志 |
| --- | --- |
| `phase10c2_isolated.py run-tests ... mvn test -Dtest=QuizAtomicIntegrationTest,QuizScaleIntegrationTest` | 修复前5项中历史核验断言失败，日志`c2-gap-before-fix-1793417145480540000.log`；修复后5/5通过，`c2-gap-after-fix-1793417201834473000.log` |
| `phase10c2_retest.py api` | 首次空答案返回400，与协议不一致；最终14项补验PASS，`retest-api-1793417791500731000.log` |
| `phase10c2_retest.py browser` | PASS，`retest-browser-scale-1793417483848062000.log`；截图`output/playwright/phase10c2-retest/quiz-{5,12,100}.png` |
| `phase10c2_migration_retest.py` | DDL/DML/history/recovery PASS，`migration-retest/1793417572521974000/acceptance.json`；异常历史`migration-retest/1793417742325829000/acceptance.json`、约束`migration-retest/1793417918736448000/acceptance.json`均PASS |
| 最终干净测试库`mvn verify` | **38项，0失败、0错误、0跳过，BUILD SUCCESS**；`c2-retest-verify-1793417852674201000.log` |
| Python脚本测试 | 18/18通过；`c2-retest-python-1793417861357898000.log` |
| Web build | 隔离生产构建通过；前端业务源码本轮未修改，沿用部署前已通过的typecheck/lint/前端单测，未把旧检查冒充本轮重跑 |

原始命令、cwd、HEAD、退出码与日志SHA-256由既有runner追加到`execution-commands.jsonl`；迁移原始SQL/行值和凭据放在受限`.local/phase10c2/migration-retest/`。对外包只含合成测试结果、摘要、日志、源码及校验器，不包含备份正文、凭据或个人学习内容。

## 4. 更正与边界

阶段报告§5的单题、事务故障和规模浏览器PARTIAL已用上述实际执行结果更新；迁移故障与异常历史有本轮新证据。此前将未执行项笼统标PASS的表述不再作为验收依据。

早期迁移注入脚本因mysql CLI触发器分隔符写错而中止，保留失败日志；修正测试脚本后在全新目标重跑，未复用失败history伪造通过。首次素材生成遇到来源唯一键冲突，改用逐版本独立原创来源标识，未修改数据库约束。

真实麦克风、Safari/系统音频设备的手工项目属于既有设备验收范围，本次没有重跑。个人已部署版本仍为原提交候选，本轮三处生产修复尚未部署；不能把隔离验证结果写成线上修复已生效。新证据包：`output/review/phase10c2-retest-sanitized-evidence.zip`，以包内逐文件hash与校验器复算。

复现顺序：在既有runner中sync并准备干净测试库，运行Maven verify和隔离package/web-build；`phase10c2_retest.py seed`生成新素材，启动隔离serve后依次执行`browser`、`api`，结束后stop-serve。`api`的多轮报告断言以同一批`browser`已完成的两轮提交为前提。迁移脚本每次新建命名空间，默认执行全部角色；可用`--anomaly-only`或`--constraints-only`单独运行相应补验。
