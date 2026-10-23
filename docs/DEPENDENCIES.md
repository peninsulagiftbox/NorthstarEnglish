# Phase 01 依赖与版本依据

核查日期：2026-10-21（Asia/Shanghai）。精确依赖以根 `package-lock.json`、`apps/api/pom.xml` 与 Boot BOM 为准。不修改机器默认 Node/Java。

| 组件 | 固定版本 | 依据与用途 |
| --- | --- | --- |
| Node / npm | 22.23.2 / 10.9.8 | 已有项目级 LTS；engines 限定 Node22、npm10；[维护日程](https://github.com/nodejs/Release) |
| Next.js | 16.4.2 | npm 官方注册表 dist-tag 实查；[支持策略](https://nextjs.org/support-policy)、[安装要求](https://nextjs.org/docs/app/getting-started/installation)；App Router |
| React / React DOM | 19.3.1 | npm 实查，与 Next peer `^19.0.0` 相容 |
| TypeScript | 5.9.3 | Next peer `>=3.3.1`，strict；固定已兼容稳定版本，不追随 npm 最新大版本 |
| Tailwind / PostCSS插件 | 4.3.3 | npm 实查；不加 UI 库、远程字体 |
| ESLint / Next配置 | 9.39.4 / 16.4.2 | Next配置 peer `eslint >=9`，独立 lint 命令 |
| 类型包 | node22.20.5 / react19.3.0 / react-dom19.3.0 | 匹配实际运行时/React主版本 |
| Java | Temurin 21.0.12.1+1 | [官方分发](https://github.com/adoptium/temurin21-binaries/releases/tag/jdk-21.0.12.1%2B1)；仅 `.local/jdk21`，Apple Silicon；SHA256 `3623232f33a9c3baadf304480b2535f9a3cba8a58d42ecbb438ba267315d9998` |
| Spring Boot | 4.1.1 | [官方项目页](https://spring.io/projects/spring-boot)、[系统要求](https://docs.spring.io/spring-boot/system-requirements.html)及 Maven Central 元数据；Java21，MVC/JDBC/Validation/Flyway |
| Maven / Wrapper | 3.9.9 / 3.3.4 only-script | [Apache Wrapper](https://maven.apache.org/wrapper/)；Maven分发 SHA512 与官方校验一致，Wrapper 固定 SHA256 `4ec3f26fb1a692473aea0235c300bd20f0f9fe741947c82c1234cefd76ac3a3c`；Enforcer 要求 Java21 |
| MySQL | 8.4.9 LTS | [官方镜像](https://hub.docker.com/_/mysql)；OCI index digest `sha256:c36050afdca850f23cef85703f84c7531a5ae155a11b5ee1c60acb09937c4084`；独立容器、卷和账号 |
| Flyway / Connector/J / JUnit | 12.4.0 / 9.7.0 / 6.0.3 | Boot 4.1.1 BOM 实际解析，不手动覆盖；见 `docs/evidence/phase-01/logs/api-dependencies.log` |
| Playwright CLI | 0.1.22 | 仅定向浏览器验收工具，脚本中固定版本，非产品运行依赖 |

只加入本阶段必要依赖。前端单元测试用 Node 内建 runner；后端 JUnit/Mockito，集成测试连接本项目 MySQL8.4 的独立 `northstar_phase01_test` schema，不用 H2。浏览器冒烟使用 Playwright CLI，不引入产品运行依赖。后续功能阶段再引入相应组件测试工具。

版本可用性与最终兼容性分开：编译、构建、测试的真实结果以 `docs/progress/PHASE_01.md` 为准。


## Phase 03 构建执行补充

依赖版本及 package-lock 未变化。`apps/web/package.json` 的生产构建指定同版 Next.js 内置 `--webpack`：本阶段 Turbopack 在普通和获准环境均因 PostCSS 辅助进程本地端口绑定被拒而失败；webpack 生产构建实际通过，失败日志保留在本地 Phase 03 证据目录。开发脚本与全局 Node/Java 不变。


## Phase 04 执行补充

沿用现有精确版本与锁文件，未新增依赖或改变全局 Node/Java。音频使用 HTMLAudioElement、IndexedDB 和浏览器原生 API；英文 token 对齐使用 Java 标准库。浏览器脚本继续固定 Playwright CLI 0.1.22，写入型用例要求实际连接隔离测试库。实际编译、测试、浏览器版本和限制见 `docs/progress/PHASE_04.md`。


## Edge 语音评测工具（可选）

2026-10-22实际使用edge-tts7.3.1，依据PyPI同版本发布页及上游README；完整隔离环境依赖锁在 `scripts/tts-evaluation-requirements.txt`。工具仅用于显式在线生成课程素材，学习时仍读本地MP3，不添加Python服务/Key作为应用依赖。技术与授权边界见 `docs/TTS_EDGE_EVALUATION.md`。

## Phase 05 执行补充

沿用现有 Node22 / Java21 与全部锁定依赖，未添加产品或测试依赖。词条、阅读题来自冻结内容包，经 Flyway V005 和内容播种建立关联；收藏存 MySQL，待确认阅读命令复用既有 IndexedDB outbox。浏览器继续使用固定 Playwright CLI 0.1.22，验证范围及环境失败记录见 `docs/progress/PHASE_05.md`。
