# Phase 10D-2-R1 候选运行说明（供独立 QA 复测）

## 候选身份

- Git HEAD：`a5084cb4442a7b78afad5c920459c22f02f679ce` + 冻结清单 `candidate-sha256.txt`（27 文件；清单哈希见 `candidate-filelist-sha256.txt`，清单文件自身不列入清单，避免自引用哈希）。
- 校验：`sh qa/phase10d2/tools/verify-candidate.sh`（只读，任何漂移非零退出）。
- JDK21：`/Users/wangshiqi/Project/NorthstarEnglish/.local/jdk21/jdk-21.0.12.1+1/Contents/Home`（不改全局）。
- 构建：`JAVA_HOME=<jdk21> apps/api/mvnw -f apps/api/pom.xml package -DskipTests`；JAR `apps/api/target/northstar-api-0.1.0-SNAPSHOT.jar`，冻结时 SHA-256 `cc4f31aecb24fe6c49e1afe779b854861b9d513711880cfe9fed61d4d4eccafb`。

## 隔离环境要求（与 D01/D02 惯例一致）

- 专用隔离 MySQL 8.4 容器（回环端口，禁止 3308），独立卷；schema `northstar_phase01_test`；应用身份播种后由 Flyway 迁移至 `012.11`。
- 环境变量：`NORTHSTAR_DB_TEST=1`、`NORTHSTAR_EXPECTED_DB_UUID=<容器uuid>`、`NORTHSTAR_TEST_AUDIO=<原创测试音>`、`NORTHSTAR_CONTENT_ROOT`、`NORTHSTAR_RECORDING_ROOT`、`DB_NAME=northstar_phase01_test`；HTTP 需 `Origin: http://127.0.0.1:3196` 与 `X-Northstar-Request: local-workspace` 头。
- 复现入口：`mvnw test -Dtest=ConceptReviewIntegrationTest`（主 checkout，环境变量齐备）；回归顺序与判据见 `docs/qa/phase10d/10D_D02_QA_TEST_PLAN.md` §4/§6。
- 禁止：操作个人 3308/3100/8085、修改 V001–V012_08、repair Flyway、把 QA 诊断副本当作本候选。
