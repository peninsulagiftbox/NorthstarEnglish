# Phase 10C-1 实施计划（已获准实施）

日期：2026-10-29（Asia/Shanghai）。用户已明确要求“根据实施计划开始实施”；下文保留原审核计划与起始基线，实际结果见阶段报告。无个人库迁移/部署授权，不进入 10C-2。

## 1. 输入与实时基线

已核查 AGENTS、README、IMPLEMENTATION_PLAN、一期桌面规范中适用的音频/状态/布局条目、phase10 的 04/05/07/08、10B-3 开发及部署报告，并查看音频/发布/恢复的 Java、TypeScript、历史迁移和相关测试。

| 项目 | 本轮实际结果 |
| --- | --- |
| 部署后 HEAD / 工作区 | `49239c61f53caed0a996dbce9156c7c6db259dc7`；核验开始时干净 |
| 部署关系 | 原构建 HEAD 为 `2a4079f96830d7b9ae16ed0a8800d677ec8555be`；后续部署文档及已上线目录弹窗提交解释差异；129 份构建输入逐文件 SHA-256 与当前工作区一致 |
| 运行实例 | Java PID 83359，cwd 为 apps/api；Web PID 83589，cwd 为 apps/web；监督进程分别为 83358/83588 |
| JAR | 运行命令指向 apps/api/target/northstar-api-0.1.0-SNAPSHOT.jar；磁盘 SHA-256 为 `c4243bca0b7062e2c94bbe6e78fe7e5603791173c615959a4819a5f6ecdfc310`，与部署记录一致；JAR 内迁移文件与源码逐份一致 |
| Web | BUILD_ID=`udzk9U3KedJsnKrExMKWg`，与部署记录一致 |
| API / Web / MySQL | 回环 8085/3100/3308；两路健康 UP，project 正确，migrationVersion=009.15 |
| 实际数据库 | MySQL 8.4.9 / northstar_english；容器、卷、端口及项目身份吻合；43 表；history 含原 baseline 行，V001–009.15 均 success=1，末条 009.15 |
| 音频与目录 | 运行 content-root 为仓库 content；20 份登记音频大小/SHA-256 全匹配；录音根为用户 Library/Application Support/NorthstarEnglish/recordings，目录存在、11 文件；本轮不宣称录音逐值/逐文件对账已完成 |
| 已有备份 | `.local/phase10b3-release/20261029T144934/backup/` 的31份文件重新校验通过；清单 SHA-256=`baff2afa47cd7270681f0dc39ecac3a2285dfb522e8eb73791cebcbdd12ba4c2`；它是升级前009.05备份，不能称为当前009.15快照 |

实时核验时间约17:29。未重启、停写、迁移、启动新应用或向个人学习接口写入；历史隔离 PASS 仅作工具参考。原始 DDL/history/命令说明见 `docs/handoff/evidence/phase10c1/`。

## 2. 已确认的最小修改范围

- 实际 sentence 存在 `uq_sentence_audio(audio_asset_id)`、`sentence_chk_1(start_ms=0)`；复合 FK `sentence_ibfk_2(audio_asset_id,lesson_version_id)` 已有非唯一支持索引 `audio_asset_id(audio_asset_id,lesson_version_id)`。未发现其他表外键引用这条音频唯一键；执行前仍需对隔离目标重新断言，不能仅据名称 DROP。
- ContentPublication 仍要求 assets.size=sentences.size 且 start=0；CatalogController 按句重复验证资源，任何坏音频导致整课失败；AudioResources 已有清单键/realpath/流式大小与哈希保护，必须保留。
- AudioController 的 Track 仅 id/uri；每次切句均重设 src，句结束依赖文件 ended。MediaProvider 把文件 currentTime 写回 positionMs，尚无可见性暂停策略。
- StudyController 使用 positionMs≤600000 及 end_ms≥positionMs，非零 start 时上界错误。前端 Sentence 未声明 start/end，校验器只接受 audio.status=ready；PlayerBar 用文件时长作句长，词点只兼容 Demo。
- 现有媒体单元用 FakeAudio，路径单元包含任意测试字节；继续用于逻辑/安全测试，但不能用这些材料证明真实可解码或可听边界。

不改动态测验/题量/报告分母、跨课知识点、PDF/导入流水线、教学编排、全局运行时或现有 Demo 文件。保留六 Tab、224px 侧栏、2:1 学习区和76px播放器；新增控件沿用现有样式。

## 3. 数据模型与新增迁移

以 V010_01 起的新连续单元作为候选编号，最终按实际独立恢复单元拆分并冻结 SHA-256；不修改 V009.15 或更早字节。

1. 预检 schema/history/FK/索引/区间；确认并保留同版复合 FK 所需非唯一索引，不存在则先单独新增。
2. 单独解除音频唯一限制；将 start=0 替换为 start≥0，始终保留 end>start。各条 DDL 明确前置、后置、部分成功识别及恢复，不承诺整体事务回滚。
3. 增 `lesson_audio`：按版本绑定唯一主音轨，复合 FK 拒绝外版本资产；与句音频共存。AudioAsset 继续表示不可变文件，不覆盖旧 ID/hash/storage_key。
4. 增最小对齐审校元数据：音轨/规范转录 hash、媒体毫秒时基、工具/版本/参数及明确人工审校状态；不接入强制对齐模型，不伪造审核人/置信度。新 profile 纳入发布快照；保留旧 Demo/已发布版本校验兼容。
5. study_resume 只新增可选完整音轨字段：playbackCoordinate、playbackMode、fullAssetId、assetPositionMs 的持久化对应列及同版约束。旧 position_ms 不更新、不回填、不重写；无新字段按旧协议。按版恢复表留后续阶段，本阶段沿用单恢复入口。

服务层统一验证整数毫秒、0≤start<end≤真实解码时长、按同音轨句序单调且不重叠；允许首尾静音和句间空白，半开区间允许前句 end=后句 start。跨表/跨行条件由发布及读取防御校验，不伪称单行 CHECK 可跨表查时长。已发布内容不得原地替换；换音轨必须新版本。缺失/损坏媒体与非法内容结构分别处理。

## 4. API 与媒体降级

- lesson 新增去重 audioAssets、可选 fullAudioAssetId；每句显式 assetId/startMs/endMs，同时保留旧 audio 字段。前端同时补类型和运行校验，不只做 TS 断言。
- 合法文本即使媒体失效仍可读，audio 标记 unavailable/明确 code；音频端点维持明确 Problem 媒体错误。非法版本/区间/跨版结构仍拒绝，不以降级绕过完整性门禁。
- 听写继续检查源音频可用、对应句及真实播放证据语义；坏媒体提交拒绝且 attempt/evidence/receipt 等无半条新增。播放/浏览仍不计 practiced。
- 保留来源许可、撤回规则、路径和软链接越界防护、hash、200/206/416。共享资产每次课程读取至多验证一次；若需要跨请求缓存，必须按不可变 hash 及文件身份/mtime/size 失效并测试篡改，不能按 URI 永久信任。
- 完整解码验证与准确时长需要实际媒体工具/浏览器证据；不能用文件 hash 正确代替解码正确。先验证本机可用能力，再决定是否有必要引入项目级工具，不全局安装。

## 5. 播放器与恢复契约

内部明确区分整数毫秒：`assetTimeMs=startMs+segmentOffsetMs`，`segmentDurationMs=endMs-startMs`。与 HTMLAudioElement 交换时仅在边界换算秒；播放速率不用于除/乘存储坐标。

- 一个音频元素，Track 携带 assetId/uri/startMs/endMs；同资产切句复用 src，不同资产等待 metadata/seeked 后按最新意图播放。
- 递增 generation/token 覆盖 load/seek/play、事件回调和晚到 Promise；切句取消旧监听/帧/待播意图；播放意图与实际状态分开，加载中暂停也阻止后续自动播放。
- 前台 rAF + timeupdate 检查片段边界，统一一次性 endSegment，ended 只作文件末尾兜底；防重复回跳、连续结束和旧事件推进新句。
- 保留 single/sequence/sentence/list，新增显式整课播放模式；完整音轨保留片头/间隙，间隙 playingSentenceId=null，阅读焦点独立；无主音轨仅提供真实句序连播。
- A/B 永远为当前句内偏移，0≤A<B≤segmentDuration，换句清空；四档速度0.75/1/1.25/1.5与 preservesPitch 保持；词点需版本/hash/片段匹配，否则不显示。
- 后台片段模式自动暂停，返回前台由用户恢复；完整模式按已批准设计可由浏览器继续，不承诺后台精确循环；录音互斥和自动播放拒绝可恢复。
- `/study/resume.positionMs` 永远句内偏移，上界改为 end-start；完整模式另存 fullAssetId/assetPositionMs 并验证同版主音轨。保留 If-Match/CAS、412/428、草稿/outbox/eventId。
- 恢复默认暂停，句尾偏移允许等于句长，点击播放按明确模式重置/前进；切版不套用原音轨坐标。静音间隙可保存完整时间但不伪造播放句。

## 6. 隔离材料与数据库安全门禁

实施及构建使用独立源码/构建/媒体目录、隔离端口和独立 MySQL 容器/卷/账号；拒绝个人库 UUID/3308，避免测试打包覆盖运行 JAR/.next。复用并精确更新原隔离工具，不绕过身份守卫。

材料全为原创/自有：A 为12句共享真实MP3，非零起点、句间静音、首中末与嵌入已知标记；B 为另一课独立句MP3；另建超过十分钟的真实可解码音轨、同课新版更换音轨及损坏/缺失副本。保留源PCM/编码参数/标记采样位置、许可声明、转录、实际时长和 SHA-256。语音逐句人工听查与测量标记分别用途；不使用教材原文、不用空文件或声明时长冒充实播。

升级路径均重新执行：

1. 已校验的009.05旧备份在新隔离目标恢复→冻结009.15→候选迁移；迁移前后旧表旧列逐PK逐值、媒体与录音/状态对账。
2. 建立独立009.15基线副本→仅新增迁移；先确认可用一致快照来源。已有旧备份可在隔离环境升级产生可复现009.15基线，但不能声称等于当前个人新增数据。若需当前个人009.15新鲜快照而必须停写，另提维护动作授权，本轮不做。
3. 空库从V001跑完整链，不复制history或baseline伪造；显式初始化 Demo、重复启动/初始化负例。
4. 新约束正反例、每个关键DDL部分失败、DDL成功/history登记失败；保留失败副本，在新目标从备份恢复，旧版读取/实际续学/重启后再对账；不clean/repair/改history。
5. 候选升级后真实学习闭环、备份/恢复工具支持新表及生成/外键字段，再次重启验证持久化；旧Demo恢复点及原媒体逐值不变。

所有数据库写测试仅在隔离目标。当前31文件备份通过只是备份字节核验，本轮未重新恢复，不等于上述新候选升级/恢复通过。

## 7. 验收、命令与证据

按改动先运行定向状态机/坐标/API/Java约束测试，再类型/lint/完整单元/build、真实MySQL和必要 Playwright；命令经项目环境入口，独立副本配置不得指向个人库。阶段检查包含 npm run typecheck/lint/test/build、Maven verify、Python unittest；实际DB测试不得将 gated skip 算通过。保留完整Demo闭环及来源/撤回/Range/草稿回执安全回归。

| 验收 | 必测项目 |
| --- | --- |
| C01 功能 | 完整/单句/顺序/循环；同音轨复用及跨音轨；四档速率；句内A/B；20次快速切句；至少10轮循环；晚到成功/拒绝/seek回调；暂停/恢复及后台策略 |
| C01 恢复 | 8400+1500=9900且保存1500；非零start、>10分钟绝对位置、句尾、静音间隙、切版和浏览器刷新；旧Demo不重写 |
| C04 | 200/206/416；hash篡改、缺失、损坏、非法路径/软链接、错版、越界/重叠/逆序/NaN、撤回；文本降级、听写零假证据 |
| 数据安全 | 两类恢复副本与空库全链、原列/媒体对账、部分DDL失败及新目标恢复、真实学习及重启 |

量化严格采用05第6.1节：实际输出捕获+已知标记，按四速率×独立/共享×首/中/末片段各连续10次（至少240次片段采样），另测loop回跳；分别记录内容对齐、播放器执行、固定输出延迟与倍速映射。保留带符号起止/回跳误差、源媒体/墙钟毫秒、最大绝对值、p95、丢样及测量不确定度。

只有全部有效实测最大绝对偏差≤150ms、不确定度≤30ms且逐句人工听查无截词/漏词，才可签量化PASS。当前仅发现 afinfo/say，PATH未发现 ffmpeg/ffprobe/sox；尚无已验证输出捕获路径，也未人工听查。优先评估现有浏览器捕获能力及本机条件；没有实际捕获条件即 NOT VERIFIED，不能拿 currentTime/日志/截图签通过。实现或预算失败如实报告并留待评审。

## 8. 交付与停止点

预计涉及 catalog 的 AudioResources/ContentPublication/CatalogController/CatalogReader、StudyController及必要听写守卫、V010新增迁移、catalog DTO、LessonProvider/context、AudioController/MediaProvider/timeline/PlayerBar、对应单元/集成/E2E/隔离与恢复工具、OpenAPI及阶段文档；按实际最小范围调整，不提前实现后续模块。

最终 `docs/progress/PHASE_10C_1.md` 记录基线、修改清单、迁移hash、模型/API/坐标、音频材料hash、逐命令退出码、原始边界数据、数据对账、隔离升级/恢复、Demo回归及FAIL/BLOCKED/NOT VERIFIED；证据归 `docs/handoff/evidence/phase10c1/`。10C-2仅列依赖建议，不自动开展。

计划审核已通过。实施授权不包含个人库迁移、部署、停写、替换运行构建或提交GitHub；如需部署，先另报固定候选/备份/风险/维护窗口/恢复方法并取得明确授权。
