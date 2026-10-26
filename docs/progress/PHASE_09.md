# Phase 09｜最终工程化、集成回归与本地交付

更新：2026-10-26（Asia/Shanghai）。已按用户授权阅读Prompt09、实施计划、根AGENTS、Phase08报告及Phase1验收规范，并补齐此前未实现/未实测项。本地工程验收 **PASS_WITH_NOTES**，等待最终审核；素材正式发布仍为 **BLOCKED**（文本/声音授权pending_review）。实体Chrome/Safari麦克风、另一台Mac复现与外部模型调用不列为通过。未提交或推送Git。

## 缺口与本次补充

| 此前缺口 | 补充结果 |
|---|---|
| 闭环脚本未运行、草稿恢复断言与当前产品不符 | 全新Chrome上下文实际完成课程→第6句播放→盲听错答/差异/回听→阅读证据→明确跳过跟读→作文两版→错答测验→翻卡自评→刷新；修正“正式保存后草稿清空”的测试假设，另建未提交草稿验证恢复 |
| 关闭/重启后的数据缺少核对 | 全表快照比较工具、全新浏览器回访；隔离API重启前后37表及ready媒体相同，草稿/历史/复习可见 |
| 仅同MySQL新schema恢复，缺独立实例演练 | 新恢复MySQL容器/卷、回环3310；恢复37表及1份有效录音到新库；实际数据库停机503、重启恢复；浏览器原音频播放后继续听写，同event只入库一次，再重启API逐值相同 |
| 从空库初始化缺证据 | 新MySQL内仅有项目标记的应用库完成001–008及内容播种；重复启动37表hash一致，两版本/20句、真实学习历史为零；真实零数据API/UI首次首页→课程→10句Demo通过 |
| 故障、安全、无障碍/视觉证据不足 | 音频404/重试、真实离线草稿、API500/导出失败注入、麦克风拒绝/虚拟录音、快速切句、幂等重试、XSS、Host/Origin/CORS、绑定/密钥/日志与键盘焦点验证；文字对比度修正和稳定绘制截图 |
| 启停与恢复脚本有安全缺口 | 既有容器只start、新容器no-recreate；构建端口一致性检查；运行中构建缺失时拒绝覆盖；恢复目标身份/端口/卷验证及新库/新媒体目录约束 |

## 文件和设计决定

- `scripts/local.py`：上述启动保护，不改全局Node/Java，不删除/重建已有数据或卷。
- `scripts/regression-runtime.py`：隔离测试、独立恢复、新初始化应用三套进程身份与构建目录。恢复模式只接受日期型schema；`--fresh-recovery`复用新实例的应用库，绝不清库。
- `infra/compose.recovery.yml`、`scripts/recovery_mysql.py`：独立容器/卷/回环端口；复用本项目私有凭据，记录端口但不输出密码。已有同名资源身份不符即拒绝。
- `scripts/data-transfer.py`：`--separate-mysql`仅改变恢复目标；来源DDL和依赖仍从已核验源实例读取。数据十六进制编码、外键开启、新库事务插入、媒体哈希/大小核对。原默认行为保留。
- `scripts/check-snapshot.py`：只读比较全部表/列/单元值，可核对所有ready媒体；可创建0600新快照，拒绝覆盖。
- `scripts/release-browser.sh`及`full-learning-loop/release-boundaries/release-revisit/release-accessibility/release-fresh/release-continue.js`：固定既有Playwright CLI，写测试需要隔离库标记；恢复续学入口另核验独立容器、API进程与预期快照；只读入口保持拦截直至浏览器关闭；每轮保留独立日志和trace。
- `scripts/release-safety.py`、`scripts/tests/test_recovery_guards.py`：网络来源/绑定/敏感值/日志检查，以及外国项目、公开绑定、错误卷/端口和篡改快照的保护测试。
- `apps/web/src/app/globals.css`仅将辅助色`#687b96`加深至`#5f7088`；实测抽样最小对比度4.7039。无布局重设计。1440下侧栏224px、播放器76px；既有课文/助教约2.5:1（原型1512图课文略宽），980以下收起助教。差异见DESIGN_DEVIATIONS。
- README、`.env.example`、IMPLEMENTATION_PLAN、BACKUP_RESTORE、DEPENDENCIES、TEST_REPORT、RELEASE_CHECKLIST与本报告同步。

## 实际验证、命令及证据

原始日志/截图：`docs/evidence/phase-09/`（既有gitignore排除私人数据）；trace：`.playwright-cli/traces/`。不把文件存在当通过，下面结果均核对实际退出状态或结构化结果。

| 命令/检查 | 结果与日志 |
|---|---|
| `./scripts/doctor.sh` | Node22.23.2/npm10.9.8、Java21.0.12.1、Docker29.6.1，专属MySQL8.4.9身份/绑定/卷核验 |
| `python3 scripts/local.py exec npm ci` | 10月24日366包安装通过；锁文件此后未变，`npm-versions.log`复核实际版本；部分可选平台包被npm列为extraneous，不据此声称漏洞清零 |
| `python3 scripts/local.py exec npm run typecheck` / `npm run lint` / `npm test` | typecheck-final/lint-final/web-tests-final.log；25项通过 |
| `python3 scripts/local.py db-test` | api-verify-resume.log；真实MySQL隔离库schema008，Java生产包及20项测试通过，0失败/错误/跳过 |
| `python3 -m unittest discover -s scripts/tests` | python-delivery.log；12项通过，包含新增恢复保护测试。此前2项沙箱Error原日志保留，权限解除后全通过 |
| 隔离/恢复/新初始化/主Web webpack build | isolated-rebuild/restore-build-start/fresh-web-build/main-web-final-deploy.log；全部通过 |
| `sh scripts/release-browser.sh`完整闭环 | full-learning-loop-20261026143113.txt；passed=true/pageErrors=[]；重复提交回执相同 |
| `sh scripts/release-browser.sh release-boundaries` | release-boundaries-20261026143219.txt；passed=true/pageErrors=[]；虚拟麦克风实际MediaRecorder上传/解码，全部轨道ended |
| `python3 scripts/recovery_mysql.py start` + `restore.sh … --separate-mysql` | recovery-mysql-start.log、restore-values.log；新库`northstar_restore_20261026143448`，37表逐值相同；1份ready录音大小/SHA一致 |
| `check-snapshot.py … --media`、API/DB重启 | sourceAPI重启逐值通过；recovery-restart-continue.log记录真实DB停止503及重启后原37表/媒体一致 |
| 新浏览器`release-revisit`源/恢复副本 | revisit-source/revisit-restore.log及release-revisit-202610261438{33,40}.txt；空浏览器缓冲下恢复服务端草稿/历史/复习，恢复录音实际解码 |
| 恢复副本实际续学 | restore-continued-browser.log；原音频第10句实际解码后由UI提交非空听写，同event重放仍一条；restored-after-continue-restart.log中37表/媒体与续学后快照一致；正式脚本入口再验见restore-continue-entry/restore-entry-restart.log |
| 损坏/缺媒体/重复目标拒绝 | restore-rejections.log；失败目标未创建；不覆盖已有schema或媒体 |
| 空独立库迁移/重复初始化 | fresh-mysql-init.log；001–008、两版本20句、37表hash重复启动一致、0学习历史；fresh-browser.log是真实零数据API/UI，非响应注入 |
| `release-accessibility` | ui-final/main-readonly-retest.log；1440/375无横向溢出、标签与抽样对比度通过；键盘/弹窗焦点见boundary。并非完整WCAG认证 |
| `release-safety.py` / `api-smoke.py` | security-delivery/api-smoke-delivery.log；27份浏览器JS/HTML无配置秘密；运行日志无DB秘密/测试原始输入；Host/Origin/写标记/MIME/CORS拒绝、no-store/nosniff、回环绑定通过 |
| 重复init/up | repeated-init-final.log；.env原字节/0600不变，复用已核验进程/容器 |

### 失败与修正记录

1. 10月24–25日自动审批因使用额度拒绝运行态命令；10月26日权限恢复后完成，不绕过审批。
2. 闭环前两轮失败均为测试假设错误：恢复状态是“草稿已恢复”；正式版本保存后会清空草稿。保留browser-run-01/02及trace，修正后另保存未提交草稿并通过。
3. 音频404在预加载时已经失败，旧脚本还等待“播放本句”；按错误态重试修正后通过。初期375截图绘制残影由两帧稳定等待后重拍，不据残影改产品。
4. 并发主Web构建期间安全检查找不到静态资源，重复up触发构建锁失败；原日志保留。增加运行中构建缺失保护，完成构建后安全/幂等检查通过。工作区同时出现的`docs/handoff/`与`northstar-packages.sha256`属于其他工作，未改动或归为本阶段成果。
5. 第一次恢复续学直接请求声明audioPlayed=false，服务端按预期422拒绝；未改写为通过。随后在恢复浏览器实际播放第10句再提交成功。
6. **只读脚本过早移除route拦截**，主站一次延迟PUT更新浏览恢复点。trace证实仅该请求200，当前rowVersion恰增1、完整字段匹配测试请求；通过If-Match恢复原位置（版本号不回退）。其他36表逐值未变，study_resume仅row_version/updated_at前进。修正后拦截器一直保留到浏览器关闭；复验延迟PUT被阻断，最终与修复后快照37表一致。不会宣称本轮主库零写入。依据main-resume-reconcile-final/main-readonly-after-final.log及两次主站trace。

## 截图与原型对照

已查看原始课文工作台图、workbench-1440、audit--lesson-demo-01-{1440,375}。深蓝导航、绿色操作、浅色工作区和右侧助教保留；主学习区与助教既有独立滚动/较宽课文比例、无AI预置讲解、真实样本和词级进度是有意差异。非像素级复刻。

其他截图：dashboard-1440、dictation-diff-1440、writing-1440、review-scheduled-1440、revisit-writing/review-3101/3102、restored-continued-1440、fresh-dashboard/lesson-1440，以及首页/报告/设置375图。

## 验收结论与剩余事项

| 条目 | 结果 |
|---|---|
| 核心原创单课闭环、真实证据与幂等 | PASS |
| 实际编译/类型/lint/单测/真实MySQL集成 | PASS |
| 独立MySQL+媒体恢复、续学、API/DB重启持久化 | PASS |
| 新实例迁移/重复初始化及真实零记录UI | PASS |
| 故障、XSS/Origin/绑定/秘密/日志、基础无障碍 | PASS（具体抽样范围如上） |
| 主站数据保护 | PASS_WITH_NOTES：学习历史未改；一次测试恢复点变化已CAS恢复，版本/时间元数据前进 |
| 原型大结构/1440/375 | PASS_WITH_NOTES：延续既有设计差异，不声称像素级一致或全浏览器覆盖 |
| Chrome/Safari实体麦克风 | 手工待测；虚拟设备不能替代。拒绝或跳过不阻塞其他学习 |
| 素材文本/声音公开分发权 | BLOCKED，pending_review；releaseReady=false |
| 外部AI/ASR/专业评分、账号跨设备、全课波形 | 按一期既定范围延期，不是本阶段新业务缺陷 |

实体麦克风手工步骤：Chrome/Safari分别允许权限→录制→停止→实际回放→刷新再播→人工自评；另拒绝权限→确认明确提示→跳过后完成写作/测验。记录系统/浏览器版本、格式、回放和刷新结果；尚未执行。另一台全新Mac需自备合法素材与运行时，按README复现，未做跨机器灾难验收。

下一阶段候选仅建议：补齐素材/配音授权凭据；实体设备/跨浏览器验收；另机安装与升级/回滚演练；如需AI或更多课程，先明确数据外发、预算与合法内容来源再单独评审。本轮不开展这些开发。结束后关闭本轮隔离应用及恢复MySQL（保留库卷媒体），主站Web3100/API8085/MySQL3308保持运行，等待用户审核。


## 最终运行交付

`service-delivery-final.log`确认主站API/Web为本项目监督进程且健康，Web3100/API8085/MySQL3308保持运行；源隔离8086/3101、恢复8087/3102、新初始化8088/3103应用均关闭，新恢复MySQL3310已停止。全部schema/卷/媒体/备份保留。主站浏览器完全关闭后，`main-readonly-after-final.log`及`main-final-snapshot.log`再次37表与修复后基线完全一致；原36表学习历史及恢复点业务字段与10月24日前置快照一致，只有恢复点版本/时间元数据前进。

最终`git diff --check`通过；所有新增JS/Python/shell入口语法检查通过；最终typecheck/lint日志为typecheck-delivery/lint-delivery.log。收尾只读进程核验首轮有一处Python语法笔误（service-delivery.log），未执行其中动作；修正后service-delivery-final.log通过。未改动`docs/handoff/`、`northstar-packages.sha256`等并行产生的文件，未暂存、提交或推送。停止实施，等待最终审核。
