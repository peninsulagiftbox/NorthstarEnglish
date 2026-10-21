# Phase 01｜工程骨架、专属数据库与真实健康页

日期：2026-10-21（Asia/Shanghai）。结论：**本机验收 PASS_WITH_NOTES，等待用户审核；Phase02–09未开始**。用户本轮明确授权开始第一阶段，已阅读 `Northstar_English_Codex/prompts/01_PHASE.md`、根AGENTS、实施计划及适用设计约束。

> 公开版隐私说明：原始日志、浏览器证据、PID、容器清单和个人绝对路径仅保留本地。下文日志/截图路径用于本机复核，未随公开仓库分发；公开版保留测试结论与未测边界。
>
> 本报告中的“未提交/未推送”记录第一阶段验收结束时的状态。之后用户已授权创建公开仓库并提交，公开前排除规则与检查流程见`docs/PUBLICATION.md`；这项授权不改变Phase02尚未开始的边界。

## 1. 改动与文件

- 根工程：`.gitignore`、`.env.example`、`.node-version`、`package.json`、`package-lock.json`。初始化Git main，但**未暂存、提交或推送**；起始目录无Git，原有素材也仍为未跟踪输入，不冒充本阶段新增素材。
- 前端：`apps/web/package.json`、Next/TS/Tailwind/ESLint配置、`src/app/{layout.tsx,page.tsx,globals.css,icon.svg}`、`src/components/HealthPanel.tsx`、`src/lib/api/client.ts`、`tests/client.test.ts`。
- 后端：`apps/api/pom.xml`、官方`mvnw/mvnw.cmd/.mvn/wrapper/maven-wrapper.properties`、应用入口、`config/{LocalProperties,DatabaseGuard,LocalAccessFilter}.java`、`common/ApiProblems.java`、`health/HealthController.java`、`application.yml`、`db/migration/V001__local_settings_and_environment.sql`；三个测试类。
- 数据库：`infra/compose.local.yml`、`infra/mysql-init.sh`。
- 工具：`scripts/{local.py,service_runner.py,setup-jdk.py,init-local.sh,doctor.sh,dev-up.sh,dev-down.sh,storage-check.py,api-smoke.py,browser-smoke.sh,browser-smoke.js}`、`scripts/tests/`。
- 文档：根README改为正式本地启动说明，原README原文保存在`docs/PROTOTYPE_README.md`；新增`docs/DEPENDENCIES.md`、`docs/openapi.yaml`、本报告与证据；实施计划只更新执行状态，保留规划快照。
- 本地私有：`.env`（0600随机独立凭据）、`.local/`运行时/下载/日志/PID、node_modules/构建输出均已忽略。没有输出密码，没有改变全局Node/Java，没有改写原始参考资产。

根`references/phase1/`、`docs/progress/`在起始时不存在，参考资料实际在`Northstar_English_Codex/references/phase1/`。本轮新建进度目录；参考资料校验归档按计划留给Phase02，不覆盖同名异版。

## 2. 关键决定与实际运行

| 项目 | 实际实现 |
| --- | --- |
| 技术栈 | Next16.4.2 / React19.3.1 / TypeScript strict / Tailwind4.3.3；Java21.0.12.1 / Boot4.1.1 / Maven3.9.9；Flyway12.4.0 / ConnectorJ9.7.0；精确依据见DEPENDENCIES |
| 运行时 | 复用`/opt/homebrew/opt/node@22/bin` Node22.23.2/npm10.9.8；Java21下载到本项目`.local/jdk21`且校验SHA256；Wrapper固定Maven分发校验。没有改全局链接或默认版本 |
| 本地端口 | Web `127.0.0.1:3100`；API `127.0.0.1:8085`；MySQL `127.0.0.1:3308`。已占用端口所属服务保持不动 |
| Compose隔离 | 项目`northstar-english-local-01`；容器`northstar-english-mysql-01`；卷`northstar_english_mysql_01_data`；MySQL8.4.9固定OCI摘要，专属网络；停机只stop，不清卷/重建 |
| 数据库 | 主库`northstar_english`和测试库`northstar_phase01_test`；两库均有`project_identity`、`user_setting`、`flyway_schema_history`。设置通过FK关联项目标记；UTC DATETIME(3)，有版本、创建/更新时间和速度约束 |
| 迁移保护 | 先检查白名单schema和唯一项目标记。仅在**只有身份表且没有迁移历史**时显式建立基线0，再执行V001；存在未知表即拒绝。`baseline-on-migrate=false`、`clean-disabled=true`；不自动建库、repair/clean |
| 权限 | 独立迁移账号和当前只读运行账号，均仅授权本项目两库；迁移账号没有DROP权限。后续阶段如有业务写入，通过新阶段显式扩权 |
| API | 按实施计划统一`/api/v1/health`，不额外建立提示词中的旧`/api/health`别名；成功直接返回资源，失败Problem JSON。健康真实查询数据库标记、设置和Flyway版本；数据库断开503 |
| 其他接口 | `/api/v1/capabilities`明确所有训练/AI/ASR关闭；`/api/v1/settings`仅GET，设置编辑/并发处理留给Phase08；API全部no-store，校验本地Host/Origin，不开通配CORS，无学习写接口 |
| UI方向 | 保留深蓝224px侧栏、浅灰背景、绿色状态、主区与右栏2:1；无远程字体或UI库。根页暂为环境准备页，仅有真实重试操作。显示加载/连接成功/故障/内容未开放，无虚假统计 |
| 生命周期 | 保存监督进程PID/cwd/命令标记；停止前验证身份；只终止自己启动的子进程。容器/卷/端口/项目label核对，不按端口杀进程。配置当数据解析，不source.env，既有.env不覆盖 |

**范围说明**：首版仅建立环境标记和设置必需表；学习事件唯一键、尝试、跳过、草稿、作文历史随对应阶段分别落库，未提前创建空业务表，也未合并为完成布尔值。完整桌面路由/工作台/底部76px播放器从Phase03开始，本阶段截图不是工作台还原验收。

身份表在Docker初始化时创建，因此Flyway面对非空新schema；受限的显式基线0是为解决这个初始化边界，不会对未知已有库自动baseline。源码拒绝未知schema、错误项目标记和含未知表的新库，三种拒绝路径均有单元测试。

## 3. 实际命令与结果

所有正式命令均用项目级运行时执行，日志在`docs/evidence/phase-01/logs/`。

| 命令/场景 | 实际结果与证据 |
| --- | --- |
| `npm install --no-audit --no-fund` | PASS，生成根锁文件；未声称执行过全新机器npm ci |
| `npm run typecheck` | PASS，`web-typecheck-final.log` |
| `npm run lint` | PASS，`web-lint-retry.log` |
| `npm test` | PASS，4项API客户端测试：真实形状、503隐私、错项目响应、超时；`web-tests.log` |
| `npm run build` | PASS，Next生产构建，含图标；`web-build-final.log` |
| `apps/api/mvnw -f apps/api/pom.xml verify` | PASS，Java21编译/打包，初轮健康单测3项通过、DB集成1项明确跳过；`api-verify-retry.log`。非DB模式跳过不算集成通过 |
| `python3 scripts/local.py db-test` | PASS，最终7项测试全部通过、0失败/0错误/0跳过，包括真实MySQL集成、3项健康和3项迁移保护；`api-db-test-complete.log` |
| 真实MySQL集成 | HTTP200、重复Flyway迁移0条、非默认测试设置保留、运行账号写入拒绝、不可信Origin403；独立测试库，未删除或重建schema |
| `python3 -m unittest discover -s scripts/tests -v` | PASS，最终6项：配置按数据读取、重复/未知配置拒绝、他人PID不归属、空闲端口选择/既有env保留/0600、TIME_WAIT与实际监听区分、SIGTERM子进程回收；`scripts-tests-complete.log` |
| `python3 scripts/api-smoke.py` | PASS，真实health/capabilities/settings、no-store、404/405/Host403/Origin403及Problem结构，无通配CORS；`api-http-smoke.log` |
| `python3 scripts/local.py exec sh scripts/browser-smoke.sh` | PASS，结果明确`passed:true`。真实API、空态、加载态、模拟503、键盘Enter恢复、四窗口无横溢出、224px侧栏、无pageerror；`browser-smoke-final.log`、`browser-smoke-result.log` |
| 真实数据库停机/恢复 | PASS，只stop本项目MySQL；同源健康真实503/DATABASE_UNAVAILABLE；浏览器不显示UP；恢复同一容器后重试显示两项已连接。`actual-outage-http.log`、`browser-actual-outage.log`、`browser-actual-recovery.log` |
| `storage-check.py prepare/verify`与完整启停 | PASS，测试库设置写非默认时区并递增版本；主库只读。数据库及API/Web重启前后，两库设置/创建更新时间/项目标记/Flyway版本/校验和/执行时间快照完全一致；`storage-after-db-restart.log`、`storage-full-restart-verify.log` |
| 生命周期与doctor | 已验证停止自有服务、保留原容器/卷、恢复和真实健康；`dev-down-fixed.log`、`dev-up-acceptance-retry.log`、`doctor-final.log`；最终立即重启复核见`lifecycle-immediate-restart.log` |
| 既有服务对照 | 既有本地容器的ID、端口与连续运行状态保持一致；`existing-containers-before.log`、`existing-containers-after.log`。未对其数据库业务读写做验证 |
| 源码/秘密检查 | 目标文件逐一`git diff --no-index --check`及本地三项秘密值精确匹配扫描通过；`.env/.local/node_modules/.next/target`忽略确认；`source-safety.log` |

### 失败记录与修正

- 初始原始Wrapper源码含模板占位，无法加载WrapperMain；已替换为Apache发布的3.3.4 only-script分发，固定分发校验；原失败见`api-verify.log`。
- 初轮lint发现普通a链接与匿名默认导出，已改用Next Link及具名配置；保留`web-lint.log`，最终lint通过。
- 沙箱不允许Turbopack派生进程绑定本地端口，初轮build失败；获准环境重跑通过。保留`web-build.log`和通过日志，没有把环境失败冒称代码通过。
- Docker Hub首次镜像拉取EOF，重试同一固定摘要成功；`mysql-pull.log`、`mysql-pull-retry.log`。
- 初版监督进程信号处理重入subprocess等待锁，停止卡住。只对核验后的自有PID做恢复；改为信号只置标志、主循环统一结束子进程，并补实际SIGTERM回归。中途运行中重打JAR导致旧进程关闭时类加载错误，后续改为停API后构建，db-test也拒绝运行中覆盖JAR；历史运行日志保留。
- 停服务后TCP TIME_WAIT被误认端口冲突，已按真实服务绑定使用SO_REUSEADDR，并新增实际监听/连接关闭回归；`dev-up-acceptance.log`保留失败，修复后的启动、完整存储核对通过。
- 最初favicon404已补SVG；最终浏览器唯一console错误来自**主动注入的健康503**，不是未解释的页面异常。真实数据库停机阶段503亦为预期故障证据。

## 4. 验收条目

| 条目 | 状态 |
| --- | --- |
| 指定栈最小前后端可编译、运行 | PASS |
| 真实API/数据库健康、加载/成功/失败/空态 | PASS |
| 独立MySQL8.4、仅回环、专属卷、已有容器不变 | PASS |
| Flyway重复启动不清空表，设置和历史重启保留 | PASS |
| 错误数据库目标不迁移、没有模拟UP | PASS（迁移拒绝单测 + 真实断库） |
| 实际类型/lint/build、单元/数据库集成、最小Playwright | PASS |
| README新Mac启动流程 | PASS_WITH_NOTES：本机实际运行通过；未取得另一台全新Mac做独立端到端安装 |
| 不改全局版本、不触碰旧库卷、不泄露秘密 | PASS（目标检查和操作范围） |
| 事件幂等、原创内容与训练、麦克风/AI、完整备份恢复 | 本阶段不适用，未实现或未测试，不能标整体产品通过 |

## 5. 截图

CLI原始截图保存在被忽略的`output/playwright/`，以下本地审核副本也被排除出公开仓库：

- `docs/evidence/phase-01/screenshots/health-1440x900.png`
- `docs/evidence/phase-01/screenshots/health-1512x900.png`
- `docs/evidence/phase-01/screenshots/health-1280x800.png`
- `docs/evidence/phase-01/screenshots/health-375x812.png`
- `docs/evidence/phase-01/screenshots/health-loading.png`
- `docs/evidence/phase-01/screenshots/health-error.png`（模拟503）
- `docs/evidence/phase-01/screenshots/health-actual-db-outage.png`（真实停机）
- `docs/evidence/phase-01/screenshots/health-actual-db-recovery.png`（真实恢复）

## 6. 风险、未测与下一阶段依赖

1. 当前是无认证的个人本地工程，不应公开端口；尚未提供学习写接口，后续必须补CSRF/来源与业务数据校验。
2. 未执行另一台全新Mac安装、浏览器真麦克风/权限、AI、学习闭环、备份恢复演练；本阶段不声称这些通过。Apple Silicon下载器不适用Intel Mac，后者需指定独立JAVA_HOME。
3. `.env`在持久卷初始化后改密码不会自动轮换DB账号；脚本不会覆盖、清卷或替换已有数据。当前仅测试库写入持久化探针，无真实学习记录。
4. 本机磁盘空间有限，Java/依赖/镜像留在本项目忽略目录和Docker缓存，均未做危险清理；备份工具留待Phase08–09。
5. Git仅初始化，未提交/推送；如需提交，应单独审核本阶段范围和原始参考包，不能把未跟踪输入误当新增业务代码。
6. 审核通过后才进入Phase02：校验归档参考材料，提取10句原创内容与音频，补齐合成来源和许可审查，建立课程/媒体API；未知授权不得伪造。当前没有进行任何Phase02内容提取或导入。

交付时保留本项目Web/API/MySQL运行供审核，访问 `http://127.0.0.1:3100`；停止用`sh scripts/dev-down.sh`，只影响本项目并保留数据。报告后停止开发，等待用户审核。
