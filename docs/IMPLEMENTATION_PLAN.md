# Northstar English 实施计划

日期：2026-10-22（Asia/Shanghai）。执行更新（2026-10-23）：**Phase 05 精读词汇、阅读证据题与收藏已实施，结果见 `docs/progress/PHASE_05.md`；Phase 06–09 未开始。素材正式发布仍受来源授权审查阻塞。**

以下规划正文保留实施前的只读快照，原“本轮未初始化/未启动”等描述指规划轮次；当前执行事实以上述阶段报告为准。

本轮只分析与规划，仅更新本文件。未初始化 Git、安装依赖、创建数据库/容器、执行迁移、启动开发服务或编写正式业务代码。当前会话没有可调用的 Plan 模式切换能力，按用户要求保持规划边界；保存文档不代表批准实施。

本文替代原六阶段计划，按现有启动包的九个阶段重新编排。产品“一期”是完整原创单课闭环，工程 Phase 01–09 是其交付步骤，不能混用编号。所有拟建路径、表、接口、命令均为设计，不代表已经实现或测试通过。

## 1. 只读检查与输入依据

### 1.1 工作区现状

- cwd：`<project-root>`。
- 已阅读根目录 `AGENTS.md`、`README.md`、原有 `docs/IMPLEMENTATION_PLAN.md`。`docs/progress/` 不存在，没有最近阶段报告可读。
- `git status --short` 返回 `fatal: not a git repository`；未发现当前目录或参考包内 `.git`。本轮不能提供 Git diff、分支或提交结论，也未执行 `git init`。
- 未发现正式应用源码、`package.json`、`pom.xml`、锁文件、数据库迁移或测试工程。已有资产是原型、文档、图片和启动提示词；没有需要迁移的正式前后端架构。
- 根目录 `references/phase1/` 不存在，完整资料实际位于 **`Northstar_English_Codex/references/phase1/`**；已搜索后确认，未把路径差异报告为材料缺失。
- 另阅读 `Northstar_English_Codex/00_START_HERE.md` 及 `prompts/01_PHASE.md`–`09_PHASE.md`，仅用于阶段编排，其中“已批准”文字不是本轮执行授权。
- 本轮不移动、改写任何原始参考资产；开发获批后再归档到根目录 `references/phase1/`，逐文件校验 hash，避免覆盖同名异版。

### 1.2 已阅读的参考材料与版本差异

以下路径均相对 `Northstar_English_Codex/references/phase1/`：

| 材料 | 本轮核查 | 用途 |
| --- | --- | --- |
| `english_lab_desktop_prototype.html` | 347,330 字节、55 行，读 CSS、数据和交互脚本，未执行整块脚本 | 组件和交互输入；不是生产实现 |
| `Northstar_English_Phase1_桌面Web详细设计与验收.md` | 已读全文，含 P01–P11、原创课、AC-01–18 | 一期范围与验收依据 |
| `新概念英语_AI学习网站_竞品与PRD_V1.md` | 已读全文 | 长期方向；不把账号/全教材/ASR/云同步扩进一期 |
| `Northstar_English_首页预览.png` | 已查看 | 导航、Hero、统计卡、学习路径 |
| `Northstar_English_课文工作台预览.png` | 已查看 | 六个 Tab、正文、助教、固定播放器 |
| `Northstar_English_精听交互预览.png` | 已查看 | 听写目标、输入区、助教遮挡 |

冻结候选：以完整参考包为内容/交互依据，根目录副本保留不覆盖。HTML SHA-256 为 `0debbd92494b34f9905e38386fe57fc833170c8dfd2ed50e1fa1cc5a4623306f`；根目录 HTML 为 `b0cee141e187a50ac3741e62aea2a033ce7795386088f769f65eda84b66364c3`，347,704 字节。两者原创台词和音频数据相同，差别在 CSS、句子列表、听写按钮与词卡布局（行 2、23、24、27）。根目录额外修过听写选中态，实施时作为可借鉴修正，不整块覆盖参考包。

详细规范两份 hash 相同：`abe8a8a22a9c86f4bce3a8e4b8d6f7ab2b8703bd3f4ecaf89d347cf78713eb77`。首页/工作台截图两处相同，精听截图不同，应分别保留来源。参考图为 1512×900，正式验收仍以规范 **1440×900** 为主，并复核 1512×900。

### 1.3 环境要求与运行边界（公开版）

为保护隐私，原始机器环境清单、其他项目监听端口与容器详情只保留在本地；这里保留复现本项目必需的信息。

- 项目级 Node22 / npm10，Java21；不能覆盖机器已有全局版本。规划时Java21尚未就绪，Phase01的取得及实际测试结果见阶段报告。
- Maven Wrapper固定Maven3.9.9；MySQL8.4使用本项目独立容器、卷与账号，启动前核对Docker权限、资源与端口。
- Web `127.0.0.1:3100`，API `127.0.0.1:8085`，MySQL `127.0.0.1:3308`。若冲突，只为本项目选择空闲端口并写入本地配置，不终止占用进程。
- 浏览器origin确定后尽量保持不变，改端口前处理未同步IndexedDB数据；本项目不依赖其他本地项目的数据库、缓存或配置。

### 1.4 原创内容与 MP3 核查

唯一可学课：**Demo 01 / The Neighborhood Garden**，Mia 与 Leo 的原创对话。不是《新概念英语》任一正式课。

| 句序 | 说话者 | 原文 | MP3估计时长/秒 |
| --- | --- | --- | --- |
| 01 | Mia | Good morning. Is this the community garden? | 3.579 |
| 02 | Leo | Yes, it is. Are you here to help? | 3.631 |
| 03 | Mia | I am. My name is Mia. | 2.717 |
| 04 | Leo | Nice to meet you, Mia. I am Leo. | 3.553 |
| 05 | Mia | Where should I put these small plants? | 2.900 |
| 06 | Leo | Please put them beside the blue bench. | 3.135 |
| 07 | Mia | Do they need water now? | 2.168 |
| 08 | Leo | Just a little. The soil is still wet. | 3.500 |
| 09 | Mia | I can bring a watering can. | 2.482 |
| 10 | Leo | That would be great. Thank you! | 2.952 |

每句都有中文、人工讲解、focus。另有5个词/语块：community garden、beside、bench、soil、watering can；1道阅读题；3道选择题；花园场景2–3句写作任务，目标 please/beside/I can。

本轮以 JSON 解析提取课程和音频数组，没有 eval 原型。10段 `audio/mpeg` Base64 均可严格解码，总216,564字节；临时文件经 macOS `afinfo` 读取均退出0，检查后由临时目录上下文自动清除。总时长约30.616秒，只是独立文件时长之和，**不是整课连续时间轴**。无外部 src/href 音源。未做浏览器真实播放、听感或发音质量验收。

材料声明文本/讲解原创、音频本地合成用于功能测试；生成引擎、声音授权凭据和生成参数尚不充分。Phase02需补来源记录，未知项标 unknown/pending_review，不伪造授权文件或专业音源资格；若无法确认许可范围，阻塞该素材正式发布，不抓取替代教材。

### 1.5 原型复用边界与已知缺陷

| 范围 | 可以参考/复用的设计 | 必须重写的实现或修正 |
| --- | --- | --- |
| 页面壳 | 深蓝侧栏、浅背景、绿色操作、Hero、卡片、导航层次 | 可测试 React 组件、语义化布局和状态；禁止iframe、整块innerHTML、整块粘贴单页JS |
| 工作台 | 六Tab、句子选择、助教上下文、底部播放器 | URL路由、组件生命周期、正式API和持久化 |
| 播放 | 单句、顺播、倍速、单句/全列表循环、Space/J/K/R | `state.sentence` 混合选句/播句，播放中选别句导致文字/循环错位；异步play竞态、错误状态和资源清理 |
| 盲听 | `tutor()` 已隐藏盲听及提交前听写讲解 | 规范“右栏仍剧透”已落后；播放器仍显示英文，须遮挡所有展示面和辅助属性 |
| 听写 | 先听→非空提交→对照→回听→错句复习 | 单草稿换句清空、无尝试历史、按位置比较造成连锁误差；逐句草稿和token编辑路径重写 |
| 精读 | 5词语境、阅读题、跳第6句证据 | 选择结果不持久化，错读题未自动入复习；正式保存attempt和证据 |
| 录音 | 请求权限→录制→回放→人工自评/跳过 | 只保留Blob URL，不能跨刷新；存在旧录音可误用于新句，“完成”仅检URL，不验证本句回放；需固定目标、持久化、删除和权限状态机 |
| 写作 | 草稿→V1→修改→V2→回载 | 无稳定ID/完整日期/来源句/并发控制/diff；回载旧稿未立即保存；规则只数句/查目标表达 |
| 测验 | 3题交卷、错题回流、重做 | 只留最近结果，答案选择未即时保存；数组索引和skill标签不能作为长期ID或真实技能测量 |
| 复习 | 回忆→翻卡→自评、简单延时 | 只按句去重、单一why、无反馈历史；来源与知识点需结构化，调度版本化 |
| 进度/报告 | 行为证据、无虚构能力曲线的方向 | completed/skipped数组可并存，浏览按钮可算完成；固定38%侧栏条和任意计数条不能当学习成果 |
| 存储/设置 | 字幕、速度偏好可延续 | localStorage错误被吞；不保存页/Tab/句/位置/阅读选择/录音；showHints无实际教学开关效果 |
| 无障碍/输入 | 焦点样式和快捷键意图 | 可点击div嵌按钮、Enter/Space、IME/contenteditable、进度子元素点击、全量render丢焦点需重做 |
| 助教 | 原创解释、例句、预置提问意图 | 明示“本地预置讲解”；开放AI、ASR、发音分数均未实现，不能伪造 |

以上缺陷来自源码和静态截图核查。本轮没有执行原型全流程，不把旧README中的自动化声明当作本轮验收。

## 2. 单仓库、运行方案与依赖

### 2.1 目标结构：沿用当前根目录，按阶段创建

```text
NorthstarEnglish/
├── AGENTS.md                           # 保留并经审核增补
├── README.md / .gitignore / .env.example
├── .node-version / package.json / package-lock.json
├── apps/
│   ├── web/
│   │   ├── package.json / next.config.ts / tsconfig.json
│   │   ├── src/app/{dashboard,courses,lesson/[lessonId],review,reports,settings}/
│   │   ├── src/components/{shell,lesson,player,exercises,feedback}/
│   │   ├── src/lib/{api,state,persistence,media}/
│   │   └── tests/ / e2e/ / playwright.config.ts
│   └── api/
│       ├── pom.xml / mvnw / mvnw.cmd / .mvn/wrapper/
│       ├── src/main/java/.../{common,catalog,study,exercise,recording,writing,review,report}/
│       ├── src/main/resources/application.yml / db/migration/
│       └── src/test/java/.../
├── infra/compose.local.yml
├── content/demo-01/v1/{lesson.json,manifest.json,audio/}
├── references/phase1/                   # 审核后从现有参考包校验归档
├── scripts/{doctor,dev-up,dev-down,backup,restore}.sh
├── scripts/{extract-demo,validate-content}.py
└── docs/
    ├── IMPLEMENTATION_PLAN.md / DEPENDENCIES.md / CONTENT_MANIFEST.md
    ├── openapi.yaml / ACCEPTANCE_MATRIX.md / DESIGN_DEVIATIONS.md
    ├── BACKUP_RESTORE.md / TEST_REPORT.md / RELEASE_CHECKLIST.md
    ├── progress/PHASE_01.md ... PHASE_09.md
    └── evidence/phase-XX/{logs,screenshots,traces}/
```

原型包保持只读输入，不成为生产运行时依赖。根 npm workspace 只编排 `apps/web`，Java由wrapper独立构建；不引入Turborepo/Nx或空的共享业务包。包锁放根目录，避免多份互相漂移。

数据库专属Docker卷、录音/暂存/日志/备份放项目外专属数据目录，建议 `~/Library/Application Support/NorthstarEnglish/`。原创静态10段音频体积小，可随审核内容包版本管理；用户录音、DB、秘密和构建输出不得进Git。

### 2.2 拟采用的兼容基线

| 层 | 建议 | 固定与验证方式 |
| --- | --- | --- |
| Java | **Java21**，项目级定位 | 先找已有安装；无则另审独立下载位置和校验。只对本项目命令设JAVA_HOME，不改全局Java17 |
| 后端 | Spring Boot **4.1稳定线**，Spring MVC、Bean Validation、Spring JDBC/JdbcClient | 当前官方文档4.1.1覆盖Java21和Maven3.9；精确补丁实施时复核维护状态后锁pom，BOM管理传递版本 |
| 数据迁移 | Flyway core + MySQL模块；Connector/J | 与Boot BOM和MySQL8.4组合实际集成验证，禁止ddl-auto=update/自动建库 |
| Node | 首选现有 **22.23.2 LTS**，项目约束`>=22 <23` | `.node-version`、engines、doctor与命令路径一致；支持窗口结束前单独评审升级24，不靠全局26运行 |
| Web | **Next.js16稳定线** + 匹配peer依赖的React、TypeScript strict、Tailwind4、ESLint | 官方页面本轮显示16.4.2和Node最低20.9；版本下限兼容不代表构建已通过 |
| 包管理 | 配套npm10.9.8，根workspace与package-lock.json | 精确记录packageManager；安装后提交锁文件，重现用npm ci；不运行npx latest模板覆盖现有文件 |
| Maven | Maven Wrapper固定3.9.9及distribution校验 | 现有mvn版本满足最低要求，正式构建用`apps/api/mvnw`并核对实际Java21 |
| MySQL | **8.4 LTS**专属实例、InnoDB、utf8mb4 | 仍属于MySQL8；锁精确补丁与镜像digest，独立卷/网络/账号；不升级已有实例 |
| 前端状态 | fetch + Context/useReducer + IndexedDB薄封装 | 单课规模不先加Zustand/Redux/查询缓存库；不把HTMLAudioElement序列化 |
| 测试 | Vitest/Testing Library、JUnit/Spring测试、MySQL Testcontainers、Playwright | 跟功能阶段引入；不用H2假冒MySQL验证，不为可逆文案写镜像实现测试 |
| 不引入 | Redis、微服务、队列、云存储、账号、多租户、支付、向量库 | 当前闭环无此依赖；不先建空接口层和空表 |

版本依据于2026-10-21查阅官方资料：[Node发布与LTS](https://nodejs.org/en/about/previous-releases)、[Node发布日程](https://github.com/nodejs/Release)、[Next安装要求](https://nextjs.org/docs/app/getting-started/installation)、[Spring Boot系统要求](https://docs.spring.io/spring-boot/system-requirements.html)、[MySQL8.4发布模型](https://dev.mysql.com/doc/refman/8.4/en/mysql-releases.html)、[Flyway MySQL独立依赖](https://documentation.red-gate.com/fd/mysql-277579322.html)、[Tailwind浏览器兼容](https://tailwindcss.com/docs/compatibility)。

Node22当前为维护期LTS，官方日程EOL为2027-04-30；26到2026-10-28才计划进入LTS，因此不能因默认26可运行就将其作为本轮LTS选择。精确依赖安装、审计和编译属于Phase01，届时写 `docs/DEPENDENCIES.md`；当前不声称已锁定全部补丁组合。Tailwind4至少核对Safari16.4/Chrome111/Firefox128的支持边界，实际验收记录浏览器版本。

### 2.3 最小可运行方案与实施依赖

```text
浏览器（localhost:3100，固定origin）
  Next.js布局/客户端媒体/IndexedDB恢复缓冲
       ↓ 同源 /api/v1 转发，业务只在Java
  Spring Boot（127.0.0.1:8085，模块化单体）
       ├─ JDBC事务 → MySQL8.4（127.0.0.1:3308，专属持久卷）
       └─ 本地文件 → 教材MP3、用户录音、暂存、备份
```

- Phase01最小运行：真实健康页→API→专属MySQL连通检查；重启保留探针记录/设置，无课程训练业务。
- Phase02–04首个学习切片：数据库发布Demo→10句API→正式组件→第一句真实播放→第6句听写提交→attempt/evidence/待复习项持久化。避免先铺满全部模拟页面。
- 开发与本地生产均同源转发；私有学习数据和媒体状态不被Next静态缓存。没有Redis或云服务也可完成所有必需功能。
- 应用和数据库仅绑定loopback；校验Host/Origin，写操作采用同源CSRF令牌，自定义头+严格Origin检查，禁止通配CORS。无账号不等于允许任意网页修改本地学习数据。
- `.env`仅后端/脚本读取，`.env.example`只含占位；不向前端公开DB密码/模型Key。迁移与运行账号权限分开。
- doctor验证版本、目录、端口、数据库身份；启停只操作记录了PID/cwd/实例标记的自有进程和Compose项目，不按端口杀进程。

## 3. 学习状态与证据不变量

1. 五种状态必须可区分：`not_started`未开始、`in_progress`正在尝试、`practiced`有正式练习证据、`skipped`明确跳过、`paused`暂停未完成任务。会话另外有active/paused/ended生命周期。
2. 阶段首次编辑/开始任务进入in_progress；用户暂停该未完成任务进入paused，恢复回in_progress；明确跳过进入skipped；收到服务端有效提交回执才可practiced。暂停/跳过不删除草稿和历史证据。
3. 已有practiced证据时，再次跳过或暂停新一轮不抹掉历史。界面分别展示累计练习事实和当前轮状态；投影可由不可变记录重建，不能只存一个lesson.completed。
4. 错误作答也是真实练习，可标practiced，但与correct/掌握分开。跳过、播放、浏览、收藏或“下一步”点击都不能产生有效作答。
5. 六Tab不等于六项练习：保留六步路径和视觉布局，课文只显示“已浏览/浏览中”，训练统计以听写、阅读、跟读、写作、测验 **5项** 为分母；不把浏览算practiced凑6/6。此文案差异写入设计偏差记录。
6. 所有作答/听写/测验/复习都有lessonId和lessonVersion；涉及句子/知识点/题目时必须指向该版本对应对象，服务端校验同课，不能拿默认第1句填空字段。写作通过任务来源句关联多句。
7. 正式attempt、版本、复习结果不可被草稿覆盖。重做产生新记录；禁止前端自报correct/mastered后直接入账。
8. 录音仅证明文件与回放行为，不证明发音正确；写作规则不证明语法正确；复习“记住了”是self_rating，不是客观延时复测通过。

| 训练 | practiced最低证据 | 仍不能推出 |
| --- | --- | --- |
| 听写 | 可用音源对应句的一次非空正式提交及服务端比较结果 | 听懂全课、同义语义正确 |
| 阅读 | 一次证据题正式作答，有题目及源句 | 阅读能力等级 |
| 跟读 | 本句有效录音已持久保存且发生本句回放观察 | 正确发音、音素分数 |
| 写作 | 一条非空不可变版本，关联写作任务和来源句 | 写作质量达标 |
| 测验 | 一轮3道必答题全部提交，每题独立attempt | 听说读写综合掌握 |

## 4. 数据模型草图

### 4.1 通用约定

此处是关系设计，不执行DDL。UUID主键用 `CHAR(36)` ASCII binary比较，API字符串；实体表有id及created_at，单例设置和关系表使用下文指定的业务/联合主键，快照另有updated_at、row_version。时间使用 `DATETIME(3)` UTC、JDBC连接UTC。JSON只存经Schema校验的题面/答案/diff，不替代外键和查询索引。

单人固定 `owner_key=local`，由服务端解析，不建注册/身份表。用户录音与教材音频分表。内容版本由 `lesson_version` 保存不可变快照，稳定课ID与版本ID分离；句子/题目ID属于具体版本。所有引用旧版本的历史保留，FK默认RESTRICT，不级联删历史。

下表“必需”字段默认非空；`?`明确可空。每个FK建普通索引；需要跨对象同课约束时，使用 `(对象id, lesson_version_id)` 候选唯一键和复合FK，课ID与版本也做同属校验。CHECK/服务端共同校验枚举及范围；至少一个子项由应用事务和集成测试保证，普通FK不能保证子项数量。

### 4.2 用户要求的13类核心对象

| 对象 / 首次阶段 | 必需字段与可空项 | FK / 唯一性 / 主要索引 | 状态与边界 |
| --- | --- | --- | --- |
| `content_license` / 02 | id、source_type、owner、source_ref、rights_scope、medium、territory、review_status；proof_ref?、expires_at?、generator?、voice? | UNIQUE(source_ref,source_type)；INDEX(review_status,expires_at)；由内容/音频引用 | original/licensed；pending_review/confirmed/rejected/expired；未知合成信息显式记录，不能编证据 |
| `book` / 02 | id、catalog_key、sequence、title、edition_label、availability、metadata_source；declared_lesson_count? | UNIQUE(catalog_key,edition_label)、UNIQUE(edition_label,sequence) | 四册全部catalog_only；不展开348条虚假课文；Demo不归入已授权教材 |
| `lesson` / 02 | id、slug、kind、availability；book_id?、current_version_id? | FK book；UNIQUE(slug)；INDEX(book_id,availability)；当前版本复合FK保证属于本课 | kind=original_demo/licensed；draft/available/withdrawn；Demo book_id为空 |
| `sentence` / 02 | id、lesson_id、lesson_version_id、stable_key、sequence、speaker、text、translation、explanation、focus、audio_asset_id、start_ms、end_ms | FK lesson/version/audio；UNIQUE(version,sequence)、UNIQUE(version,stable_key)、UNIQUE(id,version) | Demo局部区间0..duration；随发布版本冻结；无词级时戳不造词级对齐 |
| `audio_asset` / 02 | id、license_id、source_kind、storage_key、mime_type、byte_size、duration_ms、sha256、status；generator/voice信息? | FK license；UNIQUE(storage_key)；INDEX(sha256)；引用资源检查范围 | original_tts/licensed_audio；pending/ready/missing/withdrawn；十句各自一文件，sha不独占以允许合法复用 |
| `knowledge_point` / 05 | id、lesson_id、lesson_version_id、stable_key、kind、term、meaning、explanation、content_source；pos?、ipa? | FK version；UNIQUE(version,stable_key)、UNIQUE(id,version)；通过point_sentence关联源句 | vocabulary/phrase/grammar；draft/published随版本；先录5个词语块及必要句型，不建全词典 |
| `exercise` / 04 | id、lesson_id、lesson_version_id、stable_key、kind、prompt、answer_schema、answer_key、scoring_version、required；options_json? | FK version；UNIQUE(version,stable_key)、UNIQUE(id,version)；exercise_sentence/point关系；INDEX(version,kind) | dictation/reading_choice/writing_prompt/quiz_choice；draft/published；答案仅判分接口返回 |
| `attempt` / 04 | id、owner_key、event_id、exercise_id、lesson_id、lesson_version_id、raw_answer、result、scoring_version、answer_exposed、submitted_at；sentence_id?、knowledge_point_id?、quiz_run_id? | FK exercise/version/目标句/点；UNIQUE(event_id)；INDEX(owner,exercise,submitted_at,id)；测验UNIQUE(run,exercise) | submitted/evaluated/invalidated；result=correct/incorrect/submitted/uncertain，原始答案不变；不把draft当attempt |
| `study_session` / 03 | id、owner_key、lesson_id、lesson_version_id、started_at、last_active_at、status、last_tab、position_ms、row_version；selected_sentence_id?、playing_sentence_id?、ended_at? | FK version及两类句子；INDEX(owner,last_active_at,id)、INDEX(owner,version,status) | active/paused/ended；恢复总是暂停；不把心跳或页面停留直接当学习时长 |
| `learning_evidence` / 04 | id、event_id、command_event_id、owner_key、lesson_id、lesson_version_id、event_type、origin、result、occurred_at、recorded_at、schema_version；session_id?、attempt_id?、recording_id?、writing_revision_id?、exercise_id?、sentence_id?、knowledge_point_id?、detail_json? | UNIQUE(event_id)；FK所有适用来源及同课关系；INDEX(owner,version,recorded_at,id)、INDEX(attempt_id)；多句由evidence_sentence关联 | append-only；origin=server_derived/client_observed/self_rating；类型约束规定哪些来源必填，skipped/observed不算成功 |
| `review_item` / 04 | id、owner_key、lesson_id、lesson_version_id、sentence_id、target_key、card_kind、status、due_at、scheduler_version、reps、row_version；knowledge_point_id?、last_result? | FK version/句/点；UNIQUE(owner,version,target_key,card_kind)；INDEX(owner,status,due_at,id) | active/suspended/archived；due是时间谓词；target_key使用确定的句/知识点键，避免NULL唯一约束漏去重 |
| `writing_revision` / 06 | id、owner_key、lesson_id、lesson_version_id、exercise_id、event_id、version_no、text、source_draft_id、created_at；parent_revision_id? | FK version/任务/草稿/父版本；UNIQUE(owner,version,exercise,version_no)、UNIQUE(event_id)；写作来源句关联表 | 不可变submitted版本；回载只改草稿，再提交生成新版本；行锁分配版本号，不裸MAX+1 |
| `user_setting` / 01 | owner_key(PK)、timezone、default_speed、show_translation、show_hints、shortcut_enabled、recording_retention、row_version、updated_at | 单例owner_key=local；无需额外索引 | 偏好与学习证据分开；速度白名单、IANA时区验证；不储API Key |

### 4.3 必须的支撑对象，按阶段出现

| 对象 / 阶段 | 关键字段与约束 |
| --- | --- |
| `lesson_version` / 02 | id、lesson_id FK、version_no、title、license_id FK、content_hash、publish_status、published_at?；UNIQUE(lesson,version_no)、UNIQUE(id,lesson_id)；draft/reviewed/published/withdrawn；发布后不可原地更新 |
| `study_resume` / 03 | owner_key PK、session_id FK、row_version；当前恢复点指向真实session，避免各课竞争最后位置 |
| `study_draft` / 04 | id、owner、version FK、kind、target_key、payload、row_version；UNIQUE(owner,version,kind,target_key)；听写target=sentenceId，写作target=exerciseId，测验target=quizRunId；updated_at索引；active/submitted快照，提交不删除历史版本 |
| `command_receipt` / 04 | event_id PK、owner、operation、request_hash、response_json、created_at；与业务同事务。所有写命令幂等，草稿也可带命令ID，但不因此生成学习证据 |
| `stage_progress` / 04 | owner、version、stage、status、last_evidence_id?、row_version；UNIQUE(owner,version,stage)；五状态，可重建；浏览阶段不能靠点击进入practiced |
| `exercise_sentence / point_sentence / evidence_sentence / writing_revision_sentence` / 对应阶段 | 业务id+version+sentence_id+role联合PK/唯一约束，双方复合FK同版本；写作/多句任务来源至少一行，单句听写恰好目标一句 |
| `exercise_point` / 05 | exercise_id+version+point_id联合PK/FK，保证错误可追到具体知识点；不把整份JSON当约束 |
| `recording` / 06 | id、owner、version FK、sentence FK、event_id唯一、storage_key唯一、mime、bytes、duration、sha256、status、created_at、deleted_at?；INDEX(owner,version,created_at)；pending/ready/failed/deleted；用户自有数据，不冒用教材许可 |
| `quiz_run / quiz_run_item` / 07 | run保存owner/version/paper_version/status/开始提交时间，draft/submitted；item固定题目id/顺序快照，UNIQUE(run,exercise)、UNIQUE(run,sequence)；一轮每题一个attempt，重做另开run |
| `review_source` / 04 | item_id FK、evidence_id FK、reason；UNIQUE(item,evidence,reason)，保留同卡多次错误、收藏来源，跨课拒绝 |
| `review_result` / 07 | id、item FK、event_id唯一、rating、due_before/after、scheduler_version、occurred_at；INDEX(item,occurred_at,id)；again/good/self_rating，不覆盖上一条 |

每条正式学习证据都以一个或多个真实源对象为依据；类型校验禁止“所有来源字段都空”的无意义记录。作文版本和证据的循环引用通过顺序插入+证据引用版本完成，版本只存event_id逻辑键而不反向FK到尚未插入的证据。

### 4.4 明确不提前建的对象

不建账号/租户/角色/支付、完整教材Edition/Unit/LessonPair/Paragraph树、词典全库、知识图谱、AI对话/生成任务/模型反馈、ASR/音素分数、S3签名上传、向量库、报表仓库、FSRS参数。未来取得许可或接入真实服务再建对应对象；当前保留字段和模块边界即可，不批量创建空表。

### 4.5 迁移与数据安全

- 拟分批：V001设置与环境标记（01）；V002内容与版本（02）；V003会话恢复（03）；V004练习/草稿/回执/证据/阶段/复习来源（04）；V005知识点与关联（05）；V006录音与写作（06）；V007测验轮次与复习结果（07）。文件名最终随实际顺序固定，不修改已执行迁移。
- Phase02先导入内容和媒体元信息；题目答案等保留在内容包，等相应表出现再幂等导入；不为了种子一次性创建后续业务全表。
- 表草图表示一期最终关系：指向后续才出现的知识点、录音、作文、测验轮次等可空列及FK，在对应阶段通过新迁移加入；早期迁移不得引用尚不存在的表，也不提前建空业务表凑依赖。
- Flyway `cleanDisabled=true`、`baselineOnMigrate=false`；启动核对schema/项目环境标记。数据库必须为已批准的本项目实例；应用不自动创建数据库。
- 空库迁移、重复启动和上阶段快照升级分别测试。MySQL DDL不能承诺全事务回滚；失败保留日志、停止继续写入，检查部分结果后用修正迁移/专属备份恢复，不盲目repair/clean。
- 原型completedTabs无真实作答证据，不导入为practiced；如用户需要，另审原文草稿/收藏的legacy_import。切换file/localhost/origin前先导出；内存录音无法事后恢复。

## 5. API契约、幂等、版本与时间

### 5.1 协议草案

统一 `/api/v1`，JSON camelCase，ID字符串，成功直接返回资源或`{items,nextCursor}`，错误 `application/problem+json`。健康入口确定为 `/api/v1/health`，不并存多套别名；OpenAPI在Phase01起逐步维护。

| 方法/路径 | 输入/输出要点 | 首阶段 |
| --- | --- | --- |
| GET `/health`、`/capabilities` | 实际db连接与AI disabled/媒体支持边界，不泄露连接串；非只写硬编码UP | 01 |
| GET `/books`、`/lessons?availability=available` | 四册目录占位与独立Demo入口 | 02 |
| GET `/lessons/{id}?version=1` | lessonVersion、10句、音频映射、许可、已审核讲解；题目正确答案不在公开DTO | 02 |
| GET `/media/{assetId}` | 校验受控路径、MIME/长度/ETag、Range200/206、非法区间416 | 02 |
| POST `/study/sessions`；GET/PUT `/study/resume` | 会话、课/版本/Tab、选择句/播放句/局部位置、If-Match；返回恢复版本 | 03 |
| GET/PUT `/drafts/{draftKey}` | lesson/version/kind/target、原文或选项、revision；逐句独立、版本冲突保留双方 | 04 |
| POST `/study/events` | 白名单观察/收藏/skip/pause，eventId+lesson/version+适用目标；拒绝客户端自报correct/practiced | 04 |
| POST `/exercises/{id}/attempts` | eventId、lesson/version、原始答案、目标句、exposure；返回attempt/diff/标准答案/证据/待复习项 | 04/05 |
| GET `/reviews/items` | 到期或全部待复习项、来源课句与状态；Phase04可查，翻卡评级Phase07才开放 | 04 |
| GET `/lessons/{id}/knowledge-points` | 知识点、语境、源句和收藏关系 | 05 |
| POST `/recordings`；GET/DELETE `/recordings/{id}` | multipart+eventId+句/版本，大小/MIME/hash，pending/ready；删除确认范围 | 06 |
| POST `/recordings/{id}/playbacks` | 本句录音回放观察eventId，客户端观察明确标注；不据此算发音质量 | 06 |
| GET/POST `/writing/revisions` | exercise/版本/sourceSentenceIds/草稿版本/原文，后端分配Vn，历史不可变 | 06 |
| POST `/quiz-runs`；PUT `/quiz-runs/{id}/draft`；POST `/quiz-runs/{id}/submit` | 固定3题、选项ID、eventId、一次提交全题原子化；重做另开run | 07 |
| GET `/reviews/due`；POST `/reviews/{id}/results` | 先翻卡，再again/good+eventId+expectedVersion；返回dueAt和版本 | 07 |
| GET `/dashboard`、`/reports` | 真实聚合：分子/分母/样本量/时窗/metricVersion，空数据与样本不足 | 08 |
| GET/PUT `/settings` | 时区、字幕、速度、隐私设置、If-Match | 01基础/08完整 |
| GET `/exports/data`；POST `/imports/validate`；POST `/imports/{token}/apply` | schemaVersion、内容依赖、行数/hash、预览；apply须用户确认且目标隔离 | 08 |

不提供云版presign接口；本地录音直接上传Java。预置讲解直接由课程/知识点API提供；没有真实AI时不建伪聊天记录。未来真实模型接口另审，默认无Key也能完整学习。

请求示例（协议草图）：

```json
{
  "eventId": "客户端生成并持久化的UUID",
  "lessonId": "demo-01稳定ID",
  "lessonVersion": 1,
  "sentenceId": "第6句版本ID",
  "clientOccurredAt": "2026-10-21T08:00:00.000Z",
  "answer": {"text": "Please put them behind the blue bench."},
  "answerExposed": false
}
```

### 5.2 错误、并发与幂等

错误字段：`type,title,status,code,detail,instance,traceId,retryable,fieldErrors`；detail是面向用户的安全说明，不含SQL/密钥/完整第三方响应。典型code：VALIDATION_FAILED、CONTENT_VERSION_CONFLICT、IDEMPOTENCY_CONFLICT、DRAFT_VERSION_CONFLICT、AUDIO_UNAVAILABLE、MEDIA_PERMISSION_DENIED（客户端状态）、SERVICE_UNAVAILABLE。

HTTP：400格式、404未知资源、409事件内容冲突/内容版本不匹配、412 If-Match过期、413过大、415媒体不支持、422空作答/跨课绑定/无效区间、503暂不可用。数据库断开不会返回成功；“答错”是200/201的教学结果，不是HTTP500。

- 浏览器先将命令及UUID eventId写入IndexedDB outbox，确认后发送；响应丢失重发同ID，不能每次retry生成新ID。
- 服务端以eventId唯一回执+操作/规范化请求hash去重；同ID同内容返回原状态/原响应并标重放；同ID不同操作/内容409。先查历史回执再校验当前可变状态，旧成功命令不会因后来版本变化失去幂等语义。
- 单事务：receipt、attempt、learning_evidence、stage投影、review_source/item一起成功或回滚。并发重复请求由唯一约束裁决，不能靠先查再插无锁逻辑。
- 单提交一个业务event；测验一份命令产生3个attempt/证据时，用稳定派生子eventId（父eventId+题目ID）确保逐题唯一，父ID保留在command_event_id。真实重做用新父ID，历史不覆盖。
- 可变草稿/偏好/恢复点用ETag/If-Match；复习用rowVersion，行锁更新到期；作文版本用任务级行锁。相同提交已成功则先幂等重放，不能误判为新并发冲突。
- 录音上传ID稳定且带hash；DB/文件跨介质用pending→校验→原子rename→ready，不宣称一个SQL事务覆盖文件。启动reconciliation识别pending/缺失/孤儿，不立即危险清理。
- 回执不随意过期删除，防长期离线outbox重放变重复；如以后要清理，必须同时设计事件墓碑与保留策略。

### 5.3 内容版本与时区

- 已发布内容不可原地修改；题目、标准答案、规范化算法均保留版本。修订发布v2，v1作答/录音/作文仍引用v1。
- 草稿键含lessonVersion。新内容发布时保留旧稿，提示继续旧版或明确迁移；不能静默换标准句判旧稿。
- GET内容返回ETag/contentHash，媒体hash与版本固定。submit必须携带版本，跨课或版本错配拒绝。
- 服务器记录UTC的recordedAt用于调度和排序，同时保留不可信clientOccurredAt供排错；不按客户端时钟决定dueAt。
- user_setting.timezone默认Asia/Shanghai，可选择有效IANA时区；日统计以选定当地日期转换为UTC半开区间，DST用ZoneId测试。时区改变不重写历史UTC时间；“1天后”明确采用24小时策略，显示实际本地到期时间。

## 6. 音频与句子同步

### 6.1 真实媒体模型

- 一个共享HTMLAudioElement由根客户端Provider持有；跨课内Tab不卸载，不新建多播放器。
- 分开 `selectedSentenceId`（正在查看）、`playingSentenceId`（实际媒体）、`exerciseSentenceId`（题目目标）。底栏永远描述实际播放对象，练习播放按钮明确播放目标句。
- 每句MP3局部时间轴：startMs=0、endMs=已验证duration。列表连播是在ended后加载下一个文件，有短间隙，不标“无缝全文音轨”。不求和伪造可拖动整课轴，不用文本长度估时间。
- 高亮随实际playing/ended事件；选择另一句只更新查看/助教，点击播放才切音源。无逐词锚点不做逐词高亮。
- `idle/loading/playing/paused/ended/error`，loadedmetadata校验时长；每个播放命令带递增token/取消标记，旧play Promise/ended不能覆盖新句。
- timeupdate更新真实进度，必要时requestAnimationFrame辅助；真正seek改currentTime，加载后clamp。恢复课/句/位置但默认暂停，尊重autoplay限制。
- 0.75/1/1.25/1.5倍速，支持时preservesPitch；单句循环与列表循环互斥。音源丢失、解码失败、play拒绝显示可重试错误，不生成作答证据。

### 6.2 A–B复读的明确范围（Phase04必需）

只在**当前句音频内部**设A/B，单位为该文件毫秒，约束 `0 <= A < B <= durationMs`。提供设A、设B、清除、开启循环；未加载真实时长、区间无效时禁用并说明。循环优先级为AB > 单句 > 列表；换句自动清除AB，防把旧文件区间用于新文件。

到B前根据currentTime/倍速安排检查，playing时结合帧检查和timeupdate兜底，触发回到A；seek期间防重复触发，后台节流/系统负载下可能越过B，明确浏览器级复读不承诺采样级精度。测试不同倍速/短句/手动seek/切Tab/后台恢复；若发现可听跳出明显，记录限界并修正，不宣称专业精密切片。

首版用两个真实时间点和滑条，不伪造波形。未来波形只能由真实解码PCM生成；跨句AB/完整音轨和手工词级对齐另审。原AC-18拆分：句内真实AB纳入Phase04；波形拖动/跨句精确复读列延期，不能把整条AC-18标PASS。

### 6.3 录音与示范音频互斥

录音开始前暂停示范音和回放。创建recording时固定lesson/version/sentence，录音中换目标须先停止或取消；重录生成新对象，旧音不被绑定到新句。按MediaRecorder支持协商webm/opus或mp4等实际MIME，不改扩展名伪装格式。

状态：idle→requesting_permission→recording→processing→pending_upload→ready；denied/failed可恢复。服务端校验非空、大小、MIME和可解码时长；建议60秒/10MB可配置。轨道、监听器、对象URL在停止/失败/离开时释放，浏览器真实权限测试另列。

## 7. UI与跨Tab状态、防剧透、离线恢复

### 7.1 页面与组件

- 路由：`/dashboard`、`/courses`、`/lesson/[lessonId]?tab=overview|listen|read|speak|write|quiz`、`/review`、`/reports`、`/settings`。根路径跳dashboard。
- Shell：Sidebar、Topbar、PageFeedback、ConfirmDialog、Toast。Lesson：LessonHeader、LessonTabs、SentenceList/Row、TutorPanel、PlayerBar/Seek/ABControls。
- 训练：DictationEditor/Diff、VocabularyCard/ReadingQuestion、RecorderPanel、WritingEditor/RevisionHistory/Diff、QuizPanel、ReviewCard、EvidenceSummary。
- 1440×900：侧栏224px、正文/右栏约2:1、底栏约76px；原CSS实测77px作为容差记录。保留1512宽截图基准；1280×800复核，约980px以下助教折叠抽屉。给底部内容留足padding，末句/按钮不被遮。
- loading/success/error/empty四态；媒体permission/loading/error与教学incorrect分别反馈。未实现Tab标“阶段待开发”，不能做可点无反应按钮或假报告。
- 使用语义button/aria-tab/focus，输入不全量重建DOM。快捷键忽略input/textarea/select/contenteditable、IME组合、修饰键；不抢可操作元素默认Space/Enter。

### 7.2 状态归属

| 数据 | 权威/存放位置 | 恢复规则 |
| --- | --- | --- |
| 当前课/Tab | URL | 刷新/浏览器前进后退一致，非法Tab回退并提示 |
| 查看句/播放句/局部位置 | Provider瞬时状态；服务端session/resume快照 | 按版本验证后恢复为暂停；选择不等于播放 |
| 作答/写作/测验草稿 | IndexedDB先落地，再防抖同步MySQL | key=owner+lessonVersion+kind+target；逐句保留，不靠组件挂载存活 |
| 正式attempt/版本/卡片/结果 | MySQL | API回执后才记正式成功，前端不改完成计数 |
| 设置 | MySQL，浏览器缓存 | 服务端版本冲突有提示，不静默覆盖 |
| 未上传录音 | IndexedDB Blob + outbox | 上传ready后才清缓冲；刷新可重试，容量不足给下载/明确失败 |
| 已保存录音 | 专属私有文件+MySQL元信息 | 服务重启可查可播；删除可追踪，备份包含文件 |

自动保存：输入后先提交本地IndexedDB事务，成功才显示“已保存到本机”；约500ms同步后端，回执后“已保存到服务端”。切Tab/失焦主动flush，beforeunload/sendBeacon不能作为唯一保障。BroadcastChannel通知多Tab，最终仍由If-Match裁决；冲突保留双方，不静默last-write-wins。

网络失败后保留原文、命令和目标，显示待同步/重试；退避重试有限频率。API503不会擦除本地稿。存储配额/禁用时显示真实失败，允许复制/下载；服务器备份不包含尚未同步的浏览器内容。首版不做Service Worker/PWA，不承诺首次冷启动完全离线；已打开且课程缓存仍在的页面可编辑和排队。

### 7.3 盲听/答案暴露策略

统一visibilityPolicy，所有组件读取同一策略。听写未提交和盲听时隐藏：当前工作区原文/译文、右栏解释/例句/聊天残留、底栏英文、tooltip/title/aria-label、折叠抽屉内容、搜索摘要及媒体元信息中的台词。渲染时不挂载答案节点，不只用CSS隐藏。

播放器此时显示“第6句·正在播放”，音频文件名和标签使用不含答案的稳定ID。切回听写或换题时重置本题结果展示，不能保留上一句正确答案；提交后仅解锁对应attempt反馈。复习翻卡前也不显示答案。

用户可以主动切课文查看答案，记录该目标/当前轮answerExposed；该次不纳入“独立听写”统计。课程API本身包含可阅读文本，自学工具不承诺防开发者工具/跨设备作弊。盲听开关不能通过恢复旧tutorReply意外泄漏；跨页面底栏、浏览器MediaSession元信息也遵守策略。

## 8. 从第一句到报告的纵向切片

| 顺序 | 用户可运行行为 | 必须形成的真实记录/结果 | 对应阶段 |
| --- | --- | --- | --- |
| 1 | 首访零数据→两次点击内进入Demo→播第一句 | 真实10句/音源；浏览/播放仅观察，会话可恢复，不计practiced | 02–04 |
| 2 | 第6句听写把beside写成behind→提交→查看差异→回听 | 原文保留；attempt+evidence+review_source原子提交；token替换定位，不伪造AI | 04 |
| 3 | 点beside词卡→阅读题错答→跳第6句 | point/exercise/attempt/evidence均同课；追加错读来源，刷新可查 | 05 |
| 4 | 播第5句→授权录音→停止→回放，或拒绝后跳过 | 本句录音持久化和回放观察；拒绝仅skipped，不增已练 | 06 |
| 5 | 花园任务写2句→存V1→修改→存V2→比较 | 任务来源第5/6/9句明确；不可变原文/版本/UTC时间；规则检查清楚标注 | 06 |
| 6 | 3题至少错1题→交卷→重做 | 一轮3个attempt；第二轮新run，来源保留，不覆盖第一轮 | 07 |
| 7 | 到期卡→先回忆→翻卡→again/good→回源句；另做客观复测 | self_rating历史与dueAt；真正复测另attempt，不把自评当正确率 | 07 |
| 8 | 首页/报告→关闭浏览器/重启自有服务→继续 | 统计来自DB；稿、版本、卡片、录音可恢复；样本不足无能力曲线 | 08–09 |

复习最小表/API在Phase04随听写出现，用于查看真实待复习来源；完整翻卡和调度在Phase07落地。听写使用确定的英文token规范化和最短编辑路径（S/D/I/N、WER可超过1），保存算法版本；同义词不当作准确听写，开放写作不套听写评分。

调度先 `simple_v1`：新错误/收藏立即到期，again=服务端现在+1分钟，good=+24小时；同卡重复错误追加来源并提前dueAt，不抹历史次数。卡按句+知识点目标+卡型去重；多个真实错误保留多个来源，命令重试不增加来源。禁止冒称FSRS/SM-2。

报告先做尝试数/完全匹配数、阅读正确题数/总题数、有效录音与回放次数、作文版本数、测验正确/总题、到期卡和复习次数。每项返回定义、样本量、时间窗；首答与重做分列；独立听写排除已暴露答案。无测量不报CEFR、音素/复述完整度、写作语法准确率或迁移能力分。

## 9. 导出、备份与恢复方案

1. 应用JSON导出：export/schema/app版本、导出时间、时区、内容版本/hash依赖、会话、逐句草稿、attempt/evidence、作文版本、复习项/来源/结果、设置、媒体manifest。明确JSON不含录音二进制；可另打包录音文件，不能只导路径声称音频已备份。
2. 全量备份：维护模式阻止新写入和上传/删除，确认事务结束；兼容目标服务器版本的mysqldump对本项目InnoDB执行single-transaction，复制被引用的ready媒体，生成行数/文件sha256清单后解除维护。凭据不出现在命令行日志。
3. 浏览器outbox先同步或单独导出本地恢复包；未同步内容未入服务器备份须明示。同盘副本不防磁盘故障，建议异盘/Time Machine第二副本；保留策略先最近7份+4份周备份，获批后配置，不本轮创建任务。
4. 导入先校验格式/最大大小/版本/重复ID/外键/内容hash、拒绝路径穿越和不可信SQL，返回新增/重复/冲突预览。相同ID相同内容跳过，异内容拒绝，不重写现有记录。
5. Phase08“应用导入”和Phase09“完整SQL+媒体恢复”均先在独立新实例/数据目录演练；默认不提供对现有库的覆盖导入。需要替换当前数据时另行明确批准，先备份目标，不删除或重建已有卷。
6. 恢复核对schema/content版本、行数、eventId唯一性、来源链、ready媒体hash、V1/V2原文、dueAt与实际播放；验证后才考虑切换配置，旧实例保留。RPO=最近成功备份；RTO要实测，不能先承诺。
7. 录音是私人数据，默认只在本地专属目录保存，依赖文件权限/用户FileVault，不声称应用已加密。下载/删除有范围说明和确认；删除保留事件墓碑并重算“当前可用录音”，不篡改曾发生的尝试。

## 10. 测试矩阵与验收证据

所有下列测试均为计划；本轮只做静态/环境/音频元数据检查，**没有应用编译、单元/集成或E2E通过结论**。

| 场景 | 层次/方法 | 预期不变量 | 首次/最终阶段 |
| --- | --- | --- | --- |
| 首访/零数据 | API集成+Playwright | 首页零记录、两次点击可进入、四册catalog_only、无假百分比 | 02–03/09 |
| 编译与依赖 | Java21 wrapper verify、npm ci/typecheck/lint/build | 正确运行时、无密钥进包、锁文件可重现 | 01起/09 |
| DB启动/迁移 | 目标MySQL8.4集成/Testcontainers | 空库迁移、重复迁移不变、升级保历史，错误实例拒绝 | 01起/09 |
| 版权/内容/音频 | 内容校验+API/浏览器 | 正好10句10MP3、hash/许可/ID映射、错误资源清晰失败 | 02/09 |
| 刷新/Tab/浏览器返回 | 组件+E2E | 每句草稿/当前课句恢复，正式结果不覆盖，暂停恢复无autoplay | 03–04/09 |
| 音频/快速切句 | 单元状态机+真实浏览器 | 旧Promise不抢状态、选句与播句分离、速度/seek/循环正确 | 04/09 |
| A-B边界 | 单元+浏览器媒体 | A<B<=duration；换句清空、速率变化有效、无假整课轴 | 04/09 |
| 防剧透 | 组件+E2E DOM/可访问性树 | 提交前正文/助教/底栏/title/aria无答案，暴露后统计排除 | 04/09 |
| 听写差异 | 纯函数/后端 | 忽略大小写标点、漏词插词替换准确、重复词/空白/WER>1合理 | 04/09 |
| 幂等/响应丢失 | MySQL并发集成+E2E | 同event重复无新增，异payload409，事务失败无半张卡 | 04/09 |
| 跳过/暂停/补练 | 单元+API+E2E | skipped/paused不增practiced；历史正确，补练保留草稿 | 04/09 |
| 断网/API500/DB中断 | 路由故障注入+集成 | 原文不丢、待同步可见、恢复重放一次；不显示假保存成功 | 04/09 |
| IndexedDB配额/多Tab | 组件+双页E2E | 配额失败真实提示，冲突保留双方、不静默覆盖 | 04/09 |
| 阅读/错课关联 | API+E2E/复合FK | 词卡定位第6句、错读生成来源、跨课/版本请求拒绝 | 05/09 |
| 录音权限/媒体故障 | Chromium假设备+真实Mac手工 | allow/deny/no device/unplug/unsupported MIME，重录/刷新可恢复或明确失败，释放轨道 | 06/09 |
| 文件/DB中途故障 | 集成/临时隔离目录 | pending可恢复，ready必须文件可读、无越权路径和无限孤儿 | 06/09 |
| 写作版本/并发 | MySQL集成+E2E | V1/V2不变、回载另建V3、并发版本无冲突、空白不提交 | 06/09 |
| 测验/复习 | JUnit Clock+MySQL+E2E | 固定3题轮次、重做历史、卡去重保来源、自评与客观复测区分 | 07/09 |
| 时区/跨日 | 可注入Clock、Asia/Shanghai及DST时区 | UTC排序、当地日界正确、dueAt服务器计算、改时区不改历史 | 07–08/09 |
| 重启服务 | 仅重启测试专属资源+E2E | DB/媒体/恢复点/版本/卡保留，不碰其他服务 | 01/06/09 |
| 数据导出/恢复 | 隔离实例/目录演练 | manifest/hash/来源/原文/媒体一致，重复导入不复制，不覆盖现库 | 08–09 |
| XSS/Origin/隐私 | API+E2E | 特殊字符纯文本、外来Origin写入拒绝、无密钥/正文日志泄露 | 各阶段/09 |
| 桌面/无障碍 | 截图+键盘/E2E+手工 | 1440×900/1512×900/1280×800、约980折叠；底栏不遮、焦点/IME可用 | 03起/09 |
| AI缺失/超时 | disabled能力测试；未来真实适配另审 | 显示本地预置讲解，学习/录音/写作不依赖外部模型 | 03/08–09 |

测试数据库和文件目录必须与开发/现有项目隔离；Docker受限时MySQL集成标BLOCKED，不降为H2后宣称已通过。假麦克风只能证明流程，真设备音质和权限体验另列未测；WebKit自动化不等于真实Safari。

原规范追踪：AC01/15→02–03；AC02/03/04/05/06→04；AC07/08→05；AC09/10→06；AC11/12→07；AC13/14→03–09分项增强；AC16→默认AI未启用；AC17跨设备账号同步不在一期；AC18按句内AB与未来波形分项验收。最终AC01–16必须有实际证据，部分通过不能把整项标绿。

建议执行入口（创建后才可运行）：根 `npm ci`、`npm run typecheck --workspace apps/web`、`npm run lint --workspace apps/web`、`npm run test --workspace apps/web`、`npm run build --workspace apps/web`、`./apps/api/mvnw -f apps/api/pom.xml verify`、`npm run test:e2e --workspace apps/web`。每阶段先跑相关目标，Phase09跑完整必需回归；失败保留exit/log/trace，不反复扩大无关测试。

手工媒体步骤：用固定localhost来源打开→准许麦克风→录第5句→停止回放→刷新/重启后再回放→删除；在浏览器设置撤销权限→重试→拒绝→跳过，核对无practiced；测试录制中切目标/设备断开/离开页后指示灯关闭；Chrome/Safari分别记录版本与结果。此轮未执行。

## 11. 九阶段交付清单

依赖：**计划审核 → 01 → 02 → 03 → 04 → 05 → 06 → 07 → 08 → 09**。每次只授权一个阶段；验收后写 `docs/progress/PHASE_XX.md`，列文件/设计/实际命令结果/通过与未通过条目/问题/截图/后续依赖，汇报后停止。没有审核不得提前开发下一阶段。

### Phase 01｜工程骨架、专属数据库与可启动健康页

- 前置：批准目录/运行时/数据库隔离方案，确认JDK21可用与Docker读写权限；复检Git和端口。此时才可初始化Git，先只建本阶段文件。
- 文件：根 `.gitignore/.env.example/.node-version/package.json/package-lock.json`；`apps/web/package.json/src/app/layout.tsx/page.tsx/src/lib/api/client.ts`；`apps/api/pom.xml/mvnw/.mvn/wrapper/`、应用入口/common错误/health/config、`V001__local_settings_and_environment.sql`；`infra/compose.local.yml`；`scripts/doctor.sh/dev-up.sh/dev-down.sh`；`README.md/docs/DEPENDENCIES.md/docs/openapi.yaml`。
- 可运行交付：Web显示真实API/数据库状态；MySQL独立持久化，前后端环回绑定；正式训练模块尚未开放。
- 验证/验收：Java21编译与JUnit健康测试；npm类型/lint/build；真实DB连通、Flyway重复启动无变化；重启本项目DB设置仍在；最小Playwright健康页；既有服务端口/资源保持不动。错误配置给明确失败而非模拟UP。
- 风险：JDK21缺口、Docker权限/镜像下载、包网络与Boot依赖兼容，任一阻塞即报告，不改全局Java或拿17降级通过。

### Phase 02｜合法原创内容入库与课程/媒体API

- 依赖：01审核通过。
- 文件：`scripts/extract-demo.py/validate-content.py`；`content/demo-01/v1/lesson.json/manifest.json/audio/01.mp3...10.mp3`；`docs/CONTENT_MANIFEST.md`；`references/phase1/`校验归档；`apps/api/.../catalog/`、`V002__catalog_content_versions.sql`；`docs/openapi.yaml`。
- 可运行交付：四册目录catalog_only、独立Demo、稳定ID/版本、10句文本/译文/预置讲解/音频和授权查询；Range媒体读取。提取数据不执行HTML eval。
- 验证/验收：恰好10句10音频及hash/时长/MIME；种子执行两次不增加记录；未知课404、缺音源明确失败、非法Range416/路径穿越拒绝；实际浏览器请求播放10段音源冒烟；目标MySQL集成通过。
- 风险：合成来源证明不足须补录/阻塞发布；不能将读到MP3元数据等同真实播放合格。无授权四册正文不导入。

### Phase 03｜桌面组件、路由与可恢复工作台

- 依赖：02审核通过。
- 文件：`apps/web/src/app/{dashboard,courses,lesson/[lessonId],review,reports,settings}/page.tsx`；`src/components/shell/`、`lesson/{LessonHeader,LessonTabs,SentenceList,TutorPanel}.tsx`、`player/PlayerBar.tsx`容器；`src/lib/state/LessonProvider.tsx`；`apps/api/.../study/`与`V003__study_session_resume.sql`；`docs/DESIGN_DEVIATIONS.md`。
- 可运行交付：真实课程浏览、六Tab切换、句子/助教同课联动、URL与服务端恢复点；尚未实现训练显示明确待开发；首页报告空数据来自API事实。
- 验证/验收：1440×900对照截图、1512/1280宽检查，无横溢出/底栏遮挡；刷新与前进后退恢复Tab/句；非法lesson/Tab处理；预置助教切句不串课；类型/lint/build和路由E2E。
- 风险：原图与规范尺寸差异、过早展示假训练按钮；此阶段播放器仅容器，不声称完整音频功能完成。

### Phase 04｜音频引擎、句内AB、听写及错误来源切片

- 依赖：03审核通过。
- 文件：`apps/web/src/lib/media/AudioController.ts`、`player/{PlayerBar,SeekBar,ABControls}.tsx`、`exercises/{DictationEditor,TokenDiff}.tsx`；`src/lib/persistence/{db,outbox,drafts}.ts`；`apps/api/.../{exercise,study,review}/`；`V004__attempts_evidence_drafts_review_sources.sql`；对应单元/集成/E2E；OpenAPI更新。
- 可运行交付：10句播放/暂停/顺播/速度/循环/真实seek/句内AB；第6句听写错词定位；逐句自动保存；服务端attempt/evidence/待复习来源；跳过/暂停区别明确。
- 验证/验收：故意beside→behind定位；按eventId重复/并发/响应丢失不重复；空白/无音源拒绝；换句草稿恢复；盲听全展示面无答案；输入焦点快捷键不抢；快速切句媒体一致；A/B有效边界；后端事务/MySQL测试和浏览器音源E2E实测。
- 风险：媒体Promise竞态、AB后台节流、存储配额、DB和页面状态不一致；不承诺波形/词级或整课连续轴。复习此时可查来源，翻卡调度尚待07。

### Phase 05｜精读词汇、证据题与知识点关联

- 依赖：04审核通过。
- 文件：`apps/web/.../exercises/{VocabularyPanel,ReadingQuestion}.tsx`、`lesson/EvidenceLink.tsx`；`apps/api/.../catalog/knowledge/`、reading评分策略；`V005__knowledge_points_and_exercise_links.sql`；内容包补5词/题目映射；OpenAPI与测试。
- 可运行交付：5词卡语境/源句、收藏、阅读题提交/反馈、第6句跳转，错误追加到真实复习来源。
- 验证/验收：题目Where should Mia put the small plants?答案Next to the blue bench.；对错都有attempt，错误来源可追；跨课/版本点拒绝；刷新收藏/作答保留；仅浏览不practiced；MySQL集成与阅读E2E。
- 风险：把词条点击当掌握、证据点错绑；词性/音标未知则不编造词典信息。

### Phase 06｜录音持久化与写作不可变版本

- 依赖：05审核通过。
- 文件：`apps/web/.../exercises/{RecorderPanel,WritingEditor,RevisionHistory,RevisionDiff}.tsx`；`src/lib/media/recorder.ts`及待上传缓冲；`apps/api/.../{recording,writing}/`；`V006__recordings_and_writing_revisions.sql`；媒体reconciliation、私有目录配置、OpenAPI与测试。
- 可运行交付：真实录制/停止/回放/重录/删除，跨刷新和服务重启可访问；写作草稿自动存、V1/V2/diff/回载再提交；明确录音回放/人工自评与规则提示。
- 验证/验收：本句录音ready且回放才有训练证据；旧录音不可让新句完成；拒绝权限可跳过；pending上传故障可恢复；V1/V2不覆盖、并发编号安全；Chrome假设备E2E+Mac真权限手工项分别记录，未测不通过。
- 风险：Safari MIME、设备断开、文件DB一致性、配额；无ASR/音素评分；不把文件长度当发音质量。

### Phase 07｜测验轮次、复习历史与简化调度

- 依赖：06审核通过。
- 文件：`apps/web/.../exercises/QuizPanel.tsx`、`review/ReviewCard.tsx`、`app/review/page.tsx`；`apps/api/.../{exercise/quiz,review}/`；`V007__quiz_runs_and_review_results.sql`；固定题目配置、Clock测试、OpenAPI与E2E。
- 可运行交付：3题完整交卷/重做历史，错题→卡→回忆翻卡→again/good→源句→客观重练；报告暂不造趋势。
- 验证/验收：至少错1题，卡片新增或追加来源；重复命令不新增、不重复推迟；过期rowVersion冲突；时间跨午夜/时区；服务重启dueAt和历史仍在；重做保留两轮、同卡不同点合理区分。
- 风险：把自评记住当客观通过、同时多Tab复习、刷新重置到期；simple_v1不冒充FSRS。

### Phase 08｜真实首页/报告、设置与导出备份

- 依赖：07审核通过。
- 文件：`apps/web/src/app/{dashboard,reports,settings}/page.tsx`正式数据视图；`apps/api/.../{report,settings,exportimport}/`；按实际需要新增迁移；`scripts/backup.sh/restore.sh`初版；`docs/BACKUP_RESTORE.md`、指标定义/OpenAPI与导入预检/E2E。
- 可运行交付：恢复入口、五训练真实状态与独立浏览状态、分子分母/样本量、偏好持久化、JSON+媒体manifest导出，隔离目标导入演练；无模型Key时完整可学。
- 验证/验收：零数据空态、真实正确数/题数与SQL一致、排除跳过/浏览/暴露答案；作文版本/卡/录音清单导出一致；同包重复导入不增、冲突包拒绝；隔离恢复能继续学习；错误/无权限导出明确失败。
- 风险：导出范围遗漏未同步缓冲、媒体文件缺失、指标口径混淆、恢复覆盖现库。真实AI为独立可选子任务，需用户另行批准供应商/预算/数据外发；一期验收不依赖Key，不在此阶段自动接入。

### Phase 09｜集成回归、本地发布与完整恢复演练

- 依赖：08审核通过；不新增未经评审业务模块。
- 文件：完善`README.md/.env.example/scripts/{doctor,dev-up,dev-down,backup,restore}.sh`；`apps/web/e2e/full-learning-loop.spec.ts`及故障恢复用例；`docs/RELEASE_CHECKLIST.md/TEST_REPORT.md/DESIGN_DEVIATIONS.md/progress/PHASE_09.md`；证据logs/screenshots/traces。
- 可运行交付：按文档从前置运行时到启动/停止/升级/备份/恢复的本地一期产品，原创单课完整闭环与发布阻塞清单。
- 验证/验收：Java21生产构建/后端测试/目标MySQL集成；npm ci/typecheck/lint/test/build；Playwright全闭环；1440×900对照；只重启自有服务；SQL+媒体恢复到独立实例并校验原文/事件/来源/音频；手工Chrome/Safari麦克风结果单列；XSS/Origin/隐私/资源释放检查。
- 风险：首次全新复现、镜像/依赖变化、真设备覆盖不全；结果逐项PASS/PASS_WITH_NOTES/FAIL/BLOCKED，未完成核心数据恢复或持久化不能签完整发布通过。AC17及波形部分AC18明确延期。

每阶段报告都要写下一阶段依赖，区分源码实现、构建、数据库、浏览器、真设备和恢复演练证据。阶段内只完成批准范围；“一阶段一提交范围”不等于允许自动提交/推送，Git操作按届时授权。

## 12. 建议增补到根AGENTS.md的长期规则（本轮不改写）

现有AGENTS已覆盖技术栈、版权、真实证据、本地安全与阶段审核，建议只补以下反复出现的具体约束：

1. 参考资产先核对实际路径/hash；同名异版保留来源，不覆盖。当前来源为Northstar_English_Codex/references/phase1，审核归档后才更新路径；原型禁止成为生产运行时依赖。
2. 选择句、实际播放句、练习目标独立；逐句MP3只使用局部时间轴，句内AB不可宣传为整课连续波形。
3. 发布内容不可变；attempt/录音/作文/复习始终锁定课版本和适用源句/知识点/练习，复合FK与应用事务共同保证同课。
4. eventId在客户端持久化后生成一次，重试沿用；同ID异payload拒绝；作答/证据/复习来源/回执同事务，禁止前端直接上报practiced。
5. 草稿按课版本+任务目标独立保存，服务端乐观锁；本地缓存成功与服务端成功分开显示，存储异常不可吞，多Tab冲突保留两份。
6. 五状态统一语义；浏览/播放/收藏/跳过不计训练完成，自评不算客观通过；六Tab中课文浏览与5项训练统计分开。
7. 盲听遮挡覆盖正文、助教、底栏、提示/可访问性属性与媒体元信息；主动看答案标记暴露，不纳入独立听写。
8. 所有测试用独立DB/媒体目录；恢复先到隔离新实例，禁用Flyway clean/隐式DDL/清卷；真实媒体权限与模拟设备测试分开报告。
9. 新依赖精确版本/依据/锁文件一并提交；运行时仅项目级指定，禁改其他项目全局环境；启停核对自有PID/cwd/Compose身份。

## 13. 审核决策与下一步边界

需要用户审核的5项：

| 决策 | 推荐 | 影响 |
| --- | --- | --- |
| 1. 结构与素材基线 | 当前根目录初始化单仓库，apps/web+apps/api+infra；完整参考包校验归档references，保留根副本差异记录 | 不另起重复工程，避免素材异版覆盖 |
| 2. 运行时/版本 | 现有项目级Node22.23.2+配套npm，Java21独立定位/安装，Next16稳定线+Boot4.1稳定线，Phase01锁精确补丁和Wrapper | 不改默认Node26/Java17；JDK21未就绪是实施前置 |
| 3. 数据隔离与保存 | 新建专属MySQL8.4实例/卷，候选3308；Web3100/API8085；私人录音存项目外本地目录，IndexedDB仅作缓冲 | 不复用/重建现有库卷；需要Docker权限和磁盘空间，当前未操作 |
| 4. 验收范围/诚实指标 | 原创10句唯一可学；六Tab、5项有证据训练+浏览分列；Phase04做句内AB，波形/跨句轴/账号同步/真实AI另审 | 不以浏览凑完成，不把预置讲解或自评包装为能力评分 |
| 5. 阶段授权与恢复安全 | 接受九阶段顺序，每次仅一个阶段；后续明确批准Phase01才动工程；备份/导入先隔离演练、不覆盖现库 | 计划获批不等于九阶段一次性授权；阶段报告后等待审核 |

主要未解决项：JDK21定位/取得方式；Docker daemon权限和可用资源；合成音频具体来源证明；实际框架精确补丁构建验证；真实Chrome/Safari麦克风与恢复演练。均已安排到相应阶段，不模拟通过。

Phase01 结果见 `docs/progress/PHASE_01.md`。Phase02 已按提示词实施，结果见 `docs/progress/PHASE_02.md`；后续用户授权实施 Phase03，结果见 `docs/progress/PHASE_03.md`。用户已授权将 Phase02、Phase03 按阶段分别提交并推送 GitHub；第四阶段已由用户单独授权实施，结果见 `docs/progress/PHASE_04.md`；不自动进入 Phase05，素材来源和声音授权仍待补齐。 用户随后授权并实施 Phase05，结果见 `docs/progress/PHASE_05.md`。
