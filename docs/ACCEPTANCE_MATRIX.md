# Phase 09-R 验收矩阵

2026-10-26（Asia/Shanghai）。唯一验收候选：`phase-09r-rc1` / `dd9e3f47a1a5c12296532846f676bb1fcbec7569`。
本表仅表示本次实际执行。旧Phase09结果、失败与退出码未知记录仍在原报告及historical目录，不替换为本次PASS。
命令ID对应[原始命令、cwd、退出码及日志索引](handoff/evidence/phase09r/commands.jsonl)；[环境](handoff/evidence/phase09r/environment.json)、[候选哈希](handoff/evidence/phase09r/candidate.json)。

| 项目 | 本次状态 | 证据/边界 |
|---|---|---|
| Java主源码/测试交付 | PASS | 19主源码+13测试，无数量变化；工作区/快照/ZIP路径集合和逐文件哈希一致；另含1个验收Java探针 |
| ZIP、逐文件SHA、秘密/路径排除 | PASS | freeze_sources/package_handoff/verify_packages与最终包装校验日志；仅证明包装范围 |
| 固定候选/源码完整性 | PASS | 本地commit/tag，candidate-code-integrity与final-candidate-code-integrity；apps/scripts/infra/content等无漂移 |
| Node单测 | PASS | web-unit，25项，0失败/跳过 |
| Python单测 | PASS | python-unit，15项；prefreeze-python的2个沙箱权限Error保留 |
| 类型检查/Lint | PASS | web-typecheck、web-lint，退出0 |
| 前端生产构建 | PASS | web-production-build与restore-web-build；独立副本，未覆盖主站构建 |
| 后端编译/Java与MySQL集成 | PASS | java-compile、java-mysql-integration；20项，0失败/错误/跳过，真实专用MySQL8.4.9 |
| 内容校验 | PASS | content-v1/v2；原本地冻结音频哈希，不代表素材授权通过 |
| 新库/零记录浏览器 | PASS | source-bootstrap、browser-fresh-chrome；9条Flyway记录含baseline+001–008；首次报告零值，10句Demo/四册仅目录 |
| 完整学习闭环 | PASS | browser-full-loop；真实音频、听写提交、阅读错答证据、作文V1/V2、错误测验、翻卡自评、刷新草稿 |
| eventId重放幂等 | PASS | full-learning-loop、release-continue、Java集成；相同attempt回执、恢复续学仅增加1次 |
| 跳过≠完成 | PASS | Java集成、source-report-counts；speaking skipped投影与真实回放证据分别计量 |
| 草稿离线/刷新恢复 | PASS | release-boundaries与full-learning-loop；真实浏览器offline、恢复连接后同步 |
| 缺音源/API500/导出失败 | PASS | release-boundaries；受控故障注入及解除后真实重试 |
| 播放拒绝/重试 | PASS | playback-rejection-and-real-retry-v2；真实产品错误UI、无作答计数、恢复原生play后实播；v1定位超时保留 |
| 录音/人工自评边界 | PASS | 虚拟麦克风真实MediaRecorder上传/解码/轨道释放；回放前拒绝自评，回放后自评；无ASR/专业评分 |
| 学习报告真实计数 | PASS | source-report-counts、restore-counts-after-continuation、Java ReportExportIntegrationTest；SQL对应提交/阅读/作文/测验/录音/自评，不把曝光答案样本当独立成绩 |
| 新浏览器/应用重启恢复 | PASS | source-new-browser-after-reinit、restore-new-browser-after-reboot；服务端草稿、历史、复习与录音解码 |
| 重复初始化 | PASS | repeated-source-db-init/migrations、repeated-init-exact-tables-media；37表逐值+1份媒体不变，无清库 |
| SQL+录音恢复 | PASS | restore-sql-media、restore-exact-tables-media；全新第二实例/日期库，37表逐列逐值和1份媒体大小/SHA相同 |
| 恢复后真实练习/幂等 | PASS | restored-real-browser-continuation；原第10句实播→真实UI听写→重放；计数1→2 |
| DB停机/重启持久化 | PASS | restore-db-down-503、restore-after-restart-exact、restore-final-exact；503后重启，37表/媒体与续学后快照相同 |
| 损坏/缺媒体/已存在目标拒绝 | PASS | restore-rejection-checks-file；原始预期退出1，新失败目标未创建；外层断言退出0 |
| 安全检查 | PASS | source-security、隔离守卫单测；来源/Host/MIME/CORS、回环监听、浏览器构建及日志秘密扫描；非全面渗透或漏洞清零证明 |
| V008真实库元数据/迁移一致性 | PASS | real-metadata-readonly：checksum=-1543956184、success=1；recording_enabled tinyint(1) NOT NULL DEFAULT 1；只读Flyway validate 9记录；未启动主站或写历史 |
| 真实库全量数据前后完全一致 | NOT VERIFIED | 本轮仅批准并查询元数据，没有读取/导出私人学习行，不声称已逐值验证全库未变 |
| 1440/375布局/标签/抽样对比度 | CONDITIONAL PASS | browser-ui-audit与选定截图；抽样通过，不是像素级原型还原、完整WCAG或所有页面状态证明 |
| Chrome/Safari实体麦克风 | NOT VERIFIED | 本机Chrome自动化使用虚拟设备；不替代物理录音、系统权限和Safari编解码 |
| Safari/Firefox完整闭环 | NOT VERIFIED | 本次仅Chrome155.0.8059.85 |
| 另一台全新机器安装/恢复 | NOT VERIFIED | 两个新MySQL实例均在同一台机器；不是另机验收 |
| 源码ZIP独立启动音频闭环 | CONDITIONAL PASS | 完整Java已补齐；ZIP继续排除待审MP3，需合法取得原哈希素材才能启动 |
| 内容/合成声音公开分发授权 | FAIL | manifest仍pending_review/releaseReady=false；素材公开发布门禁未满足 |
| 全平台正式发布验收 | NOT VERIFIED | 实体设备/另机/其他浏览器未测，不得声称全平台发布通过 |

本地已测核心工程范围：PASS。公开发布授权门禁：FAIL。当前建议仅限个人本地、有合法素材条件下的有限使用；不批准公开素材或全平台发布。
