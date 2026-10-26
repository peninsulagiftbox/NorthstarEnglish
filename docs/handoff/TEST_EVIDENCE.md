> 当前 Phase 09-R（2026-10-26）已完成固定候选隔离复验，见 [09-R 报告](PHASE_09_R_ACCEPTANCE_REPORT.md) 与 [矩阵](ACCEPTANCE_MATRIX.md)。下文为此前交接审计原文，保留当时结论与证据边界，不能替代本次结果。

# 实际测试与证据

2026-10-26。本次命令通过 `python3 docs/handoff/evidence/run_checks.py` 编排，使用 `scripts/local.py.environment()` 选择已有项目级 Node/Java；不输出环境变量值、不连接数据库。版本、命令参数、cwd、开始时间、耗时、退出码见 `evidence/commands.json`，日志保留原始 stdout+stderr，仅作隐私路径/实际凭据脱敏。

## 本次实际执行

| 命令（cwd未注明则项目根） | 退出码 | 结果 | 日志 |
|---|---:|---|---|
| `python3 -c import subprocess,sys; print(sys.version); [subprocess.run(x,check=True) for x in [["node","--version"],["npm","--version"],["java","-version"]]]`  | 0 | 项目级 Node22/npm10/Java21；版本日志为准 | [日志](evidence/versions.log) |
| `python3 -m unittest discover -s scripts/tests -v`  | 1 | 10项：8通过、2权限Error（ps和回环socket）；不能算PASS | [日志](evidence/sandbox-python-unit.log) |
| `npm test`  | 0 | 25项通过、0失败 | [日志](evidence/web-unit.log) |
| `npm run typecheck`  | 0 | PASS | [日志](evidence/web-typecheck.log) |
| `npm run lint`  | 0 | PASS | [日志](evidence/web-lint.log) |
| `python3 scripts/validate-content.py content/demo-01/v1`  | 0 | PASS：10音频与内容关联/哈希/元数据 | [日志](evidence/content-v1.log) |
| `python3 scripts/validate-content.py content/demo-01/v2`  | 0 | PASS：10音频与内容关联/哈希/元数据 | [日志](evidence/content-v2.log) |
| `npm run build`  | 0 | PASS：Next webpack生产构建；非运行态验收 | [日志](evidence/web-build.log) |
| `./mvnw -o -Dtest=TokenAlignerTest,SimpleSchedulerTest,ContentPackageTest,DatabaseGuardTest,HealthControllerTest test` （cwd apps/api） | 1 | 12项：6通过、6 Mockito自附加Error；无数据库测试入选 | [日志](evidence/sandbox-java-unit.log) |
| `git diff --check`  | 0 | PASS：当时git diff --check | [日志](evidence/diff-check.log) |
| `./mvnw -o -Dtest=TokenAlignerTest,SimpleSchedulerTest,ContentPackageTest test` （cwd apps/api） | 0 | 6项通过、0失败/错误/跳过；TokenAligner3+SimpleScheduler1+ContentPackage2 | [日志](evidence/java-pure.log) |
| `./mvnw -o -DskipTests package` （cwd apps/api） | 0 | PASS：编译/测试编译/打包，-DskipTests不算测试通过 | [日志](evidence/java-compile.log) |

普通沙箱内 `python3 docs/handoff/evidence/probe_readonly.py` 退出1；4个GET健康请求均Operation not permitted，未取得业务响应。见 `evidence/sandbox-runtime-probes.json` 与 `sandbox-runtime-probe.log`。不据此认定服务停机。

本机权限重试被自动审批拒绝：未执行、无退出码；理由和替代检查见 `evidence/approval-rejection.txt`。没有将本机脚本绕过审批执行。

Python测试中的“已生成.env”仅来自临时目录测试，实际项目.env未由本次改写。现有临时目录fixture/内存mock不产生数据库学习记录。

## 已有原始证据（不同执行，非本次重跑）

目录 `evidence/historical/`，来源/原始文件SHA-256/脱敏项见 `historical-index.json`。这是审计期间读取到的既有及并行工作产物；全部原执行退出码 **UNKNOWN/null**。`passed:true`/BUILD SUCCESS支持日志声明，但不能补造退出码，也未证明与整个冻结源码快照逐字对应。

| 证据 | 日志声明/限制 |
|---|---|
| api-verify-resume.log | 2026-10-26 Java/MySQL 20项，0失败/错误/跳过；BUILD SUCCESS；不是本次数据库测试 |
| full-learning-loop-20261026143113.txt | 最终passed:true：目录/第6句实播、错误听写/幂等、阅读源句、口语跳过、两版写作/XSS、测验复习、焦点刷新；前两份超时失败也保留 |
| release-boundaries-20261026143219.txt | 最终passed:true：音源恢复/快速切句/离线草稿/API500/导出故障/拒绝权限/虚拟录音/键盘窄屏；143120超时失败保留 |
| release-revisit-20261026143833/143840.txt | passed:true：新浏览器恢复状态、写作/测验/复习、恢复录音真实解码；回放写入有拦截，不等于本次新作答 |
| release-accessibility-20261026144251.txt | 有限采样对比度/标签/1440及375无横溢出；不是完整WCAG认证 |
| security-runtime-final.log / security-delivery.log | passed:true，27个JS资产检查、来源/错误/回环/秘密与日志检查；初次security-runtime.log的Build assets missing保留 |
| repeated-init-final.log | 最终重复init/up保留配置和已拥有服务/容器；前序repeated-init.log构建失败保留 |
| restore-values.log / restored-after-continue-restart.log | 37表逐值、1份媒体哈希一致；后者重启后复核。非本次独立读取私有数据 |
| restore-continued-browser.log | 已有日志：原音频解码，恰好一次真实作答；不在本次追加 |
| recovery-restart-continue.log | 包含DB停止503和重启一致声明，也包含HTTP422未捕获异常；不能将整个文件算全部通过，后续成功日志另列 |
| restore-rejections.log | 损坏/缺媒体拒绝且未建目标等声明；保留失败原因，无私有备份内容 |
| fresh-mysql-init.log / release-fresh-20261026144542.txt | 独立新实例初始化到008、两版本20句，重复初始化37表哈希保留；UI零指标、无初始恢复点、10句；是同机新实例，不是另一台新Mac |
| main-snapshot-resume.log / main-snapshot-delivery.log | 既有37表一致声明，但media checked=0；不是媒体全量一致性证明 |
| python-tests-final-host.log / python-delivery.log | 既有12项OK；与本次最初10项不同：并行新增了test_recovery_guards.py |

原始浏览器截图含测试界面，但本次未逐图验证，未直接打包；包内无私人截图、trace或网络导出。历史阶段报告中更早的逐项声明可在原仓库docs/progress复核，本包未将其冒充本次结果。

## 未执行 / NOT VERIFIED

见 `evidence/not-executed.json`：本次未运行db-test、写入E2E、应用启停、SQL/媒体恢复、npm ci或实体麦克风验收；退出码均null。授权范围不允许为补齐验收再次创建学习记录或修改数据库。

## 源码与结果对应范围

源包冻结时间见 `evidence/source-snapshot.json`。前后哈希显示apps/web和apps/api的已跟踪源码在本次检查至冻结时无漂移，支持上述前后端局部结果；启动/回归/安全脚本及.env.example发生并行改动，并新增回归与守卫测试，未全部重跑。完整差异见source-integrity.json。因此不能认定整个源码包经过一次一致版本的全套回归。
