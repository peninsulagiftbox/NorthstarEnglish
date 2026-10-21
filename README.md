# Northstar English

个人、本地运行的英语学习工作台。当前仅交付 **Phase 01 工程骨架与真实健康页**，尚未开放课程训练，未接入 AI、ASR 或专业语音评测。阶段验收见 [PHASE_01](docs/progress/PHASE_01.md)。原型使用说明保存在 [PROTOTYPE_README](docs/PROTOTYPE_README.md)，原始参考资产保持不变。

公开仓库包含工程源码、依赖锁文件和脱敏文档。`.env`、本地运行时/数据/日志、原始验收证据与个人工具配置均被排除；原型HTML内嵌的测试音频及原型截图只保留本地，待来源/授权审查后再决定分发。它们不是Phase01启动依赖。公开范围与检查方法见 [PUBLICATION](docs/PUBLICATION.md)。

## Mac 首次启动

前置：Docker Desktop 已启动、Python >=3.12（Python3及curl）、Node22 + npm10；不覆盖已有全局版本。Apple Silicon 可使用已有 `/opt/homebrew/opt/node@22/bin`；其他路径在项目 `.env` 指定 `NORTHSTAR_NODE_BIN=/absolute/path/to/node22/bin`。本项目 Maven Wrapper 首次联网下载固定 Maven3.9.9，Java21单独定位或下载。

在项目根目录运行：

```bash
# 只写本项目 .local/jdk21，约 200MB 下载；已有 Java21 可跳过并在 .env 指定 JAVA_HOME。
python3 scripts/setup-jdk.py
# 首次生成0600权限.env、独立随机密码及空闲端口；已有.env绝不覆盖。
scripts/init-local.sh
scripts/doctor.sh
# exec 给单条命令设置项目运行时，不 source .env、不影响全局。
python3 scripts/local.py exec npm ci
python3 scripts/local.py exec npm run build
python3 scripts/local.py exec apps/api/mvnw -f apps/api/pom.xml verify
scripts/dev-up.sh
```

打开脚本输出的地址，默认 [本地工作台](http://127.0.0.1:3100)。看到“已连接”表示浏览器经 Next 同源转发真实查询 API / MySQL；API或数据库不可达显示可重试错误。Web/API/MySQL 默认分别为 `127.0.0.1:3100/8085/3308`，3307保留给既有项目；首次初始化遇占用自动递增并记录到 `.env`。后续冲突会拒绝启动，手动修改本项目端口再重建前端，不会停止占用进程。

```bash
# 修改源码、端口或配置后，停止自有服务，重建再启动。
scripts/dev-down.sh
python3 scripts/local.py exec npm run build
python3 scripts/local.py exec apps/api/mvnw -f apps/api/pom.xml package
scripts/dev-up.sh
# 只停止身份验证通过的本项目PID与MySQL容器，保留容器/卷/数据。
scripts/dev-down.sh
```

也可仅启动自己的数据库：

```bash
python3 scripts/local.py exec docker compose --env-file .env -f infra/compose.local.yml up -d --wait mysql
```

## 定向验证

```bash
python3 scripts/local.py exec npm run typecheck
python3 scripts/local.py exec npm run lint
python3 scripts/local.py exec npm test
python3 scripts/local.py exec npm run build
python3 -m unittest discover -s scripts/tests -v
# 后端验证先停服务，再只启动MySQL，避免覆盖运行中的JAR。
scripts/dev-down.sh
python3 scripts/local.py exec docker compose --env-file .env -f infra/compose.local.yml up -d --wait mysql
# 只连接 northstar_phase01_test，不清空测试库。
python3 scripts/local.py db-test
scripts/dev-up.sh
# 可复现浏览器冒烟；首次需要下载固定 Playwright CLI/Chromium。
python3 scripts/local.py exec sh scripts/browser-smoke.sh
```

`mvnw verify` 默认执行单元测试，数据库集成测试明确标记跳过；`db-test` 才启用真实 MySQL 测试，检查 HTTP、重复迁移、设置保留、运行账号无写权限与不可信 Origin 拒绝。浏览器结果必须含 `passed: true`，截图写入 `output/playwright/`；首次若CLI提示缺浏览器，按其提示安装Chromium后重跑。阶段证据在报告中；新 Mac 端到端全新安装尚需独立机器验证，当前记录是本机实际结果。

可选存储重启核对：`python3 scripts/storage-check.py prepare` 仅递增**测试库**设置版本并保存快照；正常 `dev-down.sh` / `dev-up.sh` 后运行 `python3 scripts/storage-check.py verify` 比对两库设置、身份标记、迁移历史。两次命令之间不要再运行 `db-test`（它会修改测试设置）。此探针不清库、不删数据、不重建容器或卷。

健康接口为 `/api/v1/health`（按实施计划统一，不添加 `/api/health` 别名），另外只读 `/api/v1/capabilities` 和 `/api/v1/settings`。成功直接返回资源，失败返回 RFC Problem JSON；契约见 [openapi.yaml](docs/openapi.yaml)。Phase01没有学习写接口，幂等事件/尝试/跳过/草稿/作文历史表按后续阶段分别建立，不提前建空表。

## 数据隔离与安全

- Compose项目 `northstar-english-local-01`，容器 `northstar-english-mysql-01`，卷 `northstar_english_mysql_01_data`，独立Docker网络。只绑定127.0.0.1；不碰既有MySQL/Redis/Qdrant。
- 主schema `northstar_english`；集成测试schema `northstar_phase01_test`。容器首次初始化创建两库、项目身份标记、独立运行账号与迁移账号；不自动建库、不用H2、不运行Flyway clean/repair或删除卷。
- 迁移前核对schema名称和项目标记。只有确认仅含 `project_identity` 的新schema才显式建立Flyway基线0，再执行V001；发现未知表或标记不符立即失败。`baseline-on-migrate=false`、`clean-disabled=true`；以后启动只校验/迁移。身份表由容器bootstrap创建，V001设置表通过外键关联；所有默认时间UTC。
- 运行账号当前仅SELECT；迁移账号仅限本项目两库且无DROP权限。Phase01只有设置/标记/迁移历史，无学习成果或完成布尔值；事件唯一键在Phase04随真实事件表引入。
- `.env` 不提交、不打印；只提交 `.env.example`。密码要求64位十六进制；不要在已有卷初始化后随意换密码，修改.env不会自动轮换数据库账号。Node/Java仅单条项目命令选择。
- 启停脚本保存自有监督进程PID、cwd、命令标记，只终止验证通过的进程；Node改进程标题不影响归属判断。容器/卷核对项目label；停止后数据仍在。不要手动使用 `down -v`、`prune` 等危险清理。
- 当前无认证，仅限个人本地运行。API校验localhost Host/Origin、不启用跨域；后续写API须加入CSRF保护。严禁把开发端口映射公网或将API Key放浏览器。
- `.local/` 保存私有配置之外的运行时、日志、PID与构建下载，Docker卷保存数据库。当前备份/恢复工具尚未实现（Phase08–09），本机磁盘或卷损坏仍可能丢数据。

## 故障排查

运行 `scripts/doctor.sh`；API日志 `.local/api.log`，Web日志 `.local/web.log`。缺Java21/Node22时使用独立安装路径，不改机器默认版本。Docker连接失败先检查Desktop是否运行与socket权限；镜像EOF可重试相同锁定镜像，不换已有项目容器。健康503表示真实故障，不会模拟连接成功；更改端口后重建Web以更新同源转发配置。若启动中途失败，已启动的本项目进程会保留日志，可用 `dev-down.sh` 安全停止。

精确版本、来源与校验见 [DEPENDENCIES](docs/DEPENDENCIES.md)。实施阶段严格遵循 [IMPLEMENTATION_PLAN](docs/IMPLEMENTATION_PLAN.md)，Phase01汇报后等待审核。
