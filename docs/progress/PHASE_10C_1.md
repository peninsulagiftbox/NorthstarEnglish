# Phase 10C-1｜整课音频、逐句时间轴与播放器升级

> 2026-10-30 最终补验更新：见 [C01最终签收报告](PHASE_10C_1_R_C01.md)。**C01 PASS；C04 PASS（隔离范围）。** 最终Web候选`Edw1XDPIpdFsMA_rF8fLp`完成240/240次有效声学测量：最大绝对误差52ms（含附加周期检查），p95=38ms，最大不确定度29.276042ms。实测发现并修复跨文件load()重置倍速的一行缺陷；36项前端回归、类型/lint/隔离构建及原音轨E2E通过。新原生后台两模式PASS，原音轨15句人工听查PASS（用户自报）。原JAR/SQL不改，个人API仍009.15；不进入10C-2，不部署个人数据库。R3及以下实施事实按其当时状态保留。

日期：2026-10-29–30（Asia/Shanghai）。工程功能/迁移/恢复的既有结论保留；最新C01声学、人工听查、原生后台签收及最小倍速修复见上述最终报告。签收范围限已记录的固定本机浏览器数字输出路径，不外推实体回路或其他设备。不进入10C-2，不部署个人学习库，不自动commit/push。

## 1. Git、实际部署和数据库基线

- HEAD始终为 `49239c61f53caed0a996dbce9156c7c6db259dc7`；前置核验开始时干净，此后仅本阶段源码/测试/工具/文档有改动，未提交。已批准计划见 `docs/phase10/10C_1_IMPLEMENTATION_PLAN.md`。
- 已阅读 AGENTS/README、IMPLEMENTATION_PLAN及一期适用规范、phase10的04/05/07/08、10B-3开发/部署报告，核查实际Java/TS/SQL/测试。原部署129份输入与开发前工作区逐文件一致，不仅依赖Git提交名。
- 个人实际环境：Web3100/API8085/MySQL3308，回环绑定；MySQL8.4.9，43表，Flyway末条009.15且history全部成功。运行Java PID83359 / Web PID83589，cwd分别为apps/api、apps/web，监督进程83358/83588。
- 个人JAR始终为 `c4243bca0b7062e2c94bbe6e78fe7e5603791173c615959a4819a5f6ecdfc310`，个人Web BUILD_ID=`udzk9U3KedJsnKrExMKWg`。收尾重新GET/SELECT/SHOW确认仍UP/009.15，history与起点逐行一致，个人JAR不含V010；未写个人库、停写、重启或替换运行构建。
- 已有009.05部署前备份31文件重新核对全部通过，清单SHA-256=`baff2afa47cd7270681f0dc39ecac3a2285dfb522e8eb73791cebcbdd12ba4c2`。它不是当前个人009.15新鲜快照。本阶段用它在隔离目标重建009.15基线，**不声称覆盖备份之后的个人新增数据**。
- 个人20份登记句音频大小/hash收尾仍匹配；录音目录只做存在/数量核验。旧录音的实际文件/状态与HTTP回放字节检查来自隔离恢复副本，不将其冒称为当前个人全量录音的新备份。

前置及收尾证据：`preflight-local.json`、`personal-final-readonly.json`、`delivery-audit.json`（均在本地证据目录）。

## 2. 修改文件与实现

| 范围 | 文件与变化 |
| --- | --- |
| 模型/媒体 | 新增catalog/AudioIntervals.java、AudioProbe.java；修改ContentPackage、CatalogController、ContentPublication；区间统一、实际解码、去重清单、主音轨与媒体降级 |
| 恢复/证据 | StudyController新增显式坐标及一致性验证；ExerciseController在事务内拒绝坏媒体/非法区间，保留原事件哈希/幂等语义；ExportController将两张新表纳入不可变内容分类 |
| SQL | 新增V010.01–.06六个单元；V001–009.15共23份与HEAD字节完全一致；29份迁移首次实施后均冻结 |
| 前端 | lib/api/catalog.ts、lib/state/LessonProvider.tsx、lib/media/AudioController.ts、MediaProvider.tsx、timeline.ts、components/player/PlayerBar.tsx、PlayerSettings.tsx |
| 测试 | 新增AudioIntervalsTest、AudioIntegrationTest；更新CatalogIntegrationTest/MultiCourseIntegrationTest的缺媒体降级契约，保留503媒体/安全断言；扩展media/catalog前端测试及data-transfer脚本测试 |
| 工具 | scripts/phase10c1.py、phase10c1_isolated.py、phase10c1_audio.py、phase10c1_browser.py、phase10c1_audit.py及三份phase10c1浏览器脚本（播放器/切版/捕获）；data-transfer.py增010.06及专用隔离模式；full-learning-loop.js只补关闭已上线目录弹窗 |
| 文档 | README、OpenAPI、已批准计划、本报告及phase10c1证据入口/.gitignore |

完整变更路径及最终SHA-256见本地证据final-source-manifest.json。

沿用Next/React/Java21/MySQL/Flyway；无新增npm/Maven依赖、锁文件修改或全局运行时调整。实际项目Node22.23.2、Java21.0.12.1。媒体校验使用本机系统afconvert；测试编码复用已有隔离lameenc1.8.5环境，不安装全局依赖。

### 2.1 音频模型与发布

- AudioAsset仍为不可变文件，同版多句可引用；句子保存整数毫秒 `[startMs,endMs)`，保留同版复合FK。按音轨句序单调、不重叠，允许相邻半开区间和静音间隙；end不得超过资产时长。跨行/跨表条件由发布及读取防御校验，未宣称单行CHECK能查询其他行。
- `lesson_audio(version_id,asset_id)`绑定可选主音轨；同版复合FK拒绝错版。`audio_alignment`保存音轨/转录hash、资产毫秒时基、工具/参数/状态/审校元数据，具备PK、唯一及同版FK。旧Demo无须回填两张表。
- 新 `northstar.local.audio.v1`发布profile支持共享/独立/主音轨，要求实际解码时长与声明相符（仅1ms整数化容差），按transcript-v1校验覆盖文本hash，并冻结主音轨及审校关系。0.5ms等非整数payload拒绝，不能用asInt截断后通过。
- 旧 `northstar.local.basic.v1`和Demo兼容，旧发布快照不因本次新增表改变。未实现强制对齐模型、导入器或教学profile。测试中的verified/审核人是**显式合成规则夹具**，parameters中humanReviewed=false，不能当真人听查签名。
- AudioResources原清单键、路径/realpath、大小/hash保护保留。共享资产每次课程读取只查验一次；解码结果按路径/hash/文件身份/mtime/size作有界缓存，校验文件hash仍在每次访问执行，篡改不会因缓存被信任。系统解码器不可用时媒体失败关闭，合法文本仍可读。

### 2.2 API与学习兼容

lesson新增去重audioAssets、fullAudioAssetId及每句assetId/startMs/endMs，保留audioAssetId和audio结构。合法文本缺媒体时200且audio.status=unavailable/code=AUDIO_UNAVAILABLE；媒体端点503，撤回410，Range200/206/416保留。非法区间/关联仍拒绝。听写坏音频失败未产生attempt/evidence/receipt半条记录；播放、浏览、跳过仍不计practiced。

`/study/resume.positionMs`永久为句内偏移，上界改为end-start；移除十分钟硬阈值。可选playbackCoordinate=segment_offset_v1、playbackMode=segment/full、fullAssetId、assetPositionMs独立存储；同版主音轨、绝对范围及所选播放句的坐标一致性均校验。无新字段按旧协议，If-Match/412/428保留。迁移不回填、不重写旧Demo恢复点/row_version/updated_at。

### 2.3 播放器坐标和异步边界

`assetTimeMs = startMs + segmentOffsetMs`；`segmentDurationMs = endMs-startMs`。内部显式毫秒，HTMLAudioElement边界转换秒；兼容UI的time/duration在句模式为句内秒，在full模式为整轨秒，不按速率缩放存储坐标。

保留单元素：同资产切句复用src；异资产等待metadata/seeked，generation淘汰旧请求，intent取消加载中暂停/旧play回调。前台rAF/timeupdate统一一次性endSegment，文件ended只是兜底；单句/顺序/单句循环/列表循环及整课模式均实现。A/B只用句内偏移，换句清空；四档速度及preservesPitch保留。完整音轨保留片头/间隙，未匹配句子时playingSentenceId为空，阅读焦点独立。整轨末尾位置有明确上界，避免超末尾恢复点。

刷新默认暂停；句尾恢复再播重置；换版不套用旧坐标。同标签页新版读取恢复点前等待已发送的旧版保存完成，避免自发CAS冲突；外部页面412不自动覆盖。词点仍要求Demo版本/hash/边界匹配，新音轨无词点不伪造波形。逐句后台策略为visibilitychange暂停、返回手动恢复；首次自动化验收受限的历史见第6节，最终原生Chrome验收见补验报告§7.1。

## 3. 新迁移SHA-256及DDL边界

| 新文件 | SHA-256 |
| --- | --- |
| `V010_01__sentence_audio_support_index.sql` | `7bc1fa8d6922d0ec7da5664207ab8e46e2d556fa684a4f41fe8cd1585bdda4ff` |
| `V010_02__shared_sentence_audio.sql` | `0ac726507959edc2dc00e6e0bff260295c339fbeb2d55af0ae4a2df95f51a67a` |
| `V010_03__nonzero_sentence_interval.sql` | `5baee0d899d1a3bca327fe0c6b42ee220ca978eac3a7ce814c3b100fa99c85f8` |
| `V010_04__lesson_main_audio.sql` | `41389882ef45462ffdb51acfc62fd63cc7e275c9e436a0e571a36e522ca7cec4` |
| `V010_05__audio_alignment_review.sql` | `b119897658fddc176f4398ef41c274a2526fc03c2be52c46be2b302e0950de1c` |
| `V010_06__explicit_playback_resume.sql` | `30573cd3b6618a13a15cd50fb4ed7816de5dd0ce4e322b203c096a7504f484f4` |

.01确认/准备外键非唯一支持索引；.02解除音频唯一；.03按真实CHECK表达式定位start=0并在单个ALTER替换为start≥0；.04主音轨；.05审校；.06仅新增可空恢复字段及同版FK/CHECK。实施前实际sentence已有复合非唯一索引，FK未删除。每个单元由Flyway独立登记，不假设多条MySQL DDL整体事务回滚。

## 4. 隔离升级、历史对账和恢复

命名空间 `northstar-phase10c1-20261029a`，7个新容器/卷、独立账号/媒体；写入前检查容器ID/标签/挂载/回环端口及独立UUID，拒绝个人3308/UUID。构建始终在.local/phase10c1/source，不覆盖个人JAR/.next。

| 路径/场景 | 实际结果 |
| --- | --- |
| 009.05备份恢复→冻结009.15→010.06 | PASS；38表原列→43表原列逐PK逐值保留，最终45表；两次候选启动一致 |
| 独立009.15基线→新增六条 | PASS；由上述备份升级出的可复现基线，不是当前个人库快照 |
| 空库V001→010.06 | PASS；完整链及显式Demo初始化；未复制history/伪造baseline；两次启动45表一致 |
| 唯一索引DDL提交后注错 | PASS；uq已解除、history仍旧单元，原行值不变，失败库保留 |
| start CHECK替换后注错 | PASS；新CHECK存在但history未前进，原行值不变，失败库保留 |
| 主音轨表DDL成功/history INSERT失败 | PASS；表存在/history未登记，识别并保留，不repair/改history |
| 备份恢复到另一个新目标 | PASS；旧009.15 JAR真实读取、原录音HTTP字节/hash、实际作文续学幂等、旧版重启，再升级候选/两次启动与媒体对账 |
| 实际data-transfer backup/restore | PASS；新命名northstar_restore副本45表逐值/结构一致，主音轨/审校/生成列/外键保留；内容媒体独立复制 |
| 最终候选在新恢复目标 | PASS；用备份内容真实读取，两次启动45表一致；实际新增作文、幂等重试、再重启保留全部数据 |

没有清理库/卷、repair、修改history或在个人库运行新Spring/Flyway。旧PK/正文/hash、事件回执、尝试/草稿、作文父链、复习到期/版本与已备份录音状态均由原列比较保护；续学产生的增量单独记录。

原始证据见migrations下upgrade/empty/fault-*/recovery acceptance、actual-backup-restore及最新restored-runtime-acceptance JSON；私人快照/SQL位于.local，不进公开报告。

## 5. 真实音频材料与hash

12句原创文本由本机Samantha合成，加入自制PCM标记与静音；两个不可变共享版本、三份独立句音频及660秒自制信号。长轨是可解码信号测试，未冒称十分钟朗读。所有成功材料均实际解码，空语音首轮失败不纳入验收。

已核查本机安装许可2.F，范围限本个人项目的非商业本地使用；系统声音及生成音频不公开分发，不作为商用素材授权。安装许可路径/hash及使用范围在audio-license-review.json，公开许可入口见[Apple SLA](https://www.apple.com/legal/sla/)。

| 材料 | 实际解码时长ms | MP3 SHA-256 |
| --- | --- | --- |
| shared-v1 | 36984 | `30f9a6e0a3e6ca267d6c3d4d1b996be6c4b3ae30dfcbfb32b5ae8d248308390c` |
| shared-v2 | 37296 | `c2df36685f9dfe95921c41adc93e2b9e93772cf7ec16474169b7e181bc4ebe54` |
| independent-1 | 2352 | `fc8115f6d79fe667cc0c7100d4a2e4467ab0ddb68af0a8cb3c30a777ea27f677` |
| independent-6 | 2352 | `b4e811bf24565e00f158b66386f38725207a888b5f27ceaffc82e7414df5ef14` |
| independent-12 | 2592 | `272bc0694b739de203c41bc92fd164deea2e6431fbe2b611d9ed1b0778dad275` |
| long-660s | 660048 | `8d073b1f019a8d3b272c1f56938376931d13b969437a82a616e7219133d79561` |

源PCM/解码PCM哈希、24kHz采样率、标记样本位置、原句/区间和编码参数见audio-fixtures.json；原件保留.local/phase10c1/audio。MP3编码延迟未完成量化校准，源PCM标记不直接冒充已审核MP3可听边界。

## 6. 验证、命令与验收矩阵

所有命令经项目Node22/Java21环境。execution-commands.jsonl记录精确argv/cwd/实际退出码/log hash；migrations/commands.jsonl及私人日志记录真实SQL/UUID门禁。最终审计重算85份执行日志和6952条隔离操作原始日志哈希；131份API/Web构建输入与工作区完全一致。

| 命令/检查 | 实际结果 |
| --- | --- |
| phase10c1.py run ... npm test | 36项通过，0失败/跳过；含非零坐标、同源复用、四速率每速率10轮状态机、20次切句、迟到拒绝、暂停、整轨末尾 |
| npm run typecheck / lint / build | 最终候选各退出0；独立构建代理8155 |
| Maven verify -Dtest=*Test,!*IntegrationTest | 最终15项单元通过，0失败/错误/跳过 |
| 隔离Java回归12项 | 5项单元重复验证+7项真实Demo/API集成通过，不重复累计 |
| MultiCourse/ContentPublication | 6项真实DB测试通过，0跳过；CAS/来源/稳定身份回归 |
| DatabaseIntegrationTest | 1项真实MySQL健康/迁移/持久化/来源防护通过 |
| AudioIntegrationTest三个场景 | 共享/独立/长轨综合1项、非整数负例1项、解码时长正反例1项，各在真实隔离DB通过；合计17项不同DB集成，连同单元覆盖32个不同Java测试 |
| Python unittest discover | 15项通过，退出0；含010.06备份支持及原守卫 |
| phase10c1-browser-smoke.js | passed=true、pageErrors=[]；共享首中末、同src、顺播/列表回首、20次同轨+20次异文件选择、四速率、实际1.5x单句10轮、A/B至少3轮、完整音轨间隙/切版/刷新、645秒绝对位置恢复 |
| phase10c1-navigation-smoke.js | passed=true；延迟真实旧版PUT、实际版本链接切换，无自发412；原外部CAS保护保留 |
| full-learning-loop.js | 最终passed=true；Demo真实听写/错误来源、阅读、跳过不计完成、两版作文、测验/复习、自评与草稿刷新；无AI |
| OpenAPI/脚本/空白 | Ruby YAML解析、Python语法、git diff --check通过 |

Java覆盖按上述分批命令统计；后期整数/时长门禁有各自真实DB定向正反例，未声称所有早期回归在最后一份JAR上再次全量执行。最终JAR另完成恢复副本实读/续学/重启及Demo浏览器闭环。

**C04 PASS（隔离范围）**：200/206/416，文件hash篡改、缺失、匹配元数据但损坏的媒体、穿越/编码路径/软链接、跨版、越界/重叠/逆序、撤回410；文本降级且听写无假记录；>10min恢复实测645000ms与5000ms分开。Demo原句文件/旧行值兼容，不迁移旧恢复点。

**C01最新PASS，历史诊断如下**：早期前台元素循环10次，保留1609条performance/currentTime诊断；它们不用于声学PASS。最新签收依据最终修复候选240次实际PCM测量、逐次≤30ms预算及原生冻结事件，详见`PHASE_10C_1_R_C01.md`。

输出捕获探测实际保存11902字节WebM/Opus并解码37440帧、48kHz、0.78秒，说明捕获功能存在。但未完成设备固定输出延迟、MP3/Opus延迟与标记映射校准，无法证明≤30ms测量不确定度。**未执行240次合格声学签收采样，未得出最大绝对误差/p95**。boundary-acceptance.json以空测量数组/null统计明确记录NOT VERIFIED；不把已有元素日志或截图换算成虚假PASS。用户实际听查共享轨1–12句及独立轨1–3句后确认无异常，人工听查子项PASS；证据包不含声音，该结论为用户自报。

原生后台子项PASS：最终通过用户原生Chrome的真实标签切换取得单句停止与单句循环两种模式的hidden→pause→visible→手动play事件，全部`isTrusted=true`，没有合成visibilitychange，详见补验报告§7.1。首次有头/无头尝试无法触发hidden的历史失败保留，不作为最终结论。Safari、实体麦克风、其他设备/系统同样未测。

截图：output/playwright/phase10c1/full-track-1440.png、long-track-1440.png及phase10c1-demo；已查看整轨和长轨截图。保留224px侧栏、76px底栏及原工作区布局，无iframe/整块innerHTML。

## 7. 失败及修正记录

- 初始Node测试因参数属性不支持strip-only失败；改显式类字段后通过。普通Java/Python沙箱分别阻止Mockito附加、ps/临时socket；同范围获准重跑通过，原日志保留，门控skip不算集成通过。
- 原生音频沙箱返回0帧语音/解码错误，未使用；同范围放行后六份材料真实生成并解码通过。
- 隔离故障恢复与浏览器最初共用8155，恢复启动被空闲端口守卫拒绝；恢复改用8161，未停止端口占用者。重复续学证据同名被工具拒绝，改追加证据子目录，旧文件保留后完成重启对账。
- 旧Demo脚本未关闭已上线课程弹窗，首轮被遮挡；只补关闭步骤后闭环通过。
- 长轨首次保存等待失败，保留截图/日志；补同标签页待发写屏障及延迟真实请求测试，同时硬导航脚本先等待已确认保存，防止测试主动丢弃未确认请求。外部CAS仍不自动重试。
- 资源复用断言最初假设首次一定loadstart=1，已恢复资源可能在监听前加载；改为记录首句后的计数，仅断言后续切句无新增loadstart。
- 旧只读核验脚本错误要求个人旧JAR包含本轮V010，KeyError后修正为仅比对已部署迁移并单独确认V010缺席；最终个人环境核验通过。原生后台两次等待失败作为历史失败保留，后续真实标签切换验收最终PASS，见补验报告§7.1。

## 8. 最终候选、风险与停止点

- 最终隔离JAR SHA-256：`458a2030d69dc891e5f1e167ca8f810de73ea40188d968e768f885193116c605`；前端BUILD_ID=`Q_h4D_Trpz4GP7urTBwqG`。这是未提交工作区候选，以逐文件hash绑定；不等同个人已部署版本。
- 7个本轮容器均exited、卷保留；8155/8161/8162/3175/8098无监听，专用浏览器会话关闭。个人前后端和MySQL仍运行009.15，原构建/媒体/备份保留。
- 当前解码依赖macOS系统工具；其他平台媒体验证失败关闭、文本可读。临时解码有超时及有界缓存，不承诺其他平台或采样级剪辑能力。
- 首次阶段的声学缺口现已补齐：最终倍速修复候选重新完成240/240次，最大绝对误差52ms、最大预算29.276042ms；旧候选数据及失败记录保留。人工听查绑定未改的原音轨15句，新候选原生后台与受影响回归已通过。完整条件、刺激材料、数字捕获范围与逐组统计见最终C01报告。
- 10C-2仅可在本阶段审核后另行开展；不得把本次音频profile当动态测验、跨课知识点或完整教学验收。本轮以最终固定候选交付独立复核，停止后续开发。
- 本轮已停止。个人部署必须另报固定候选、当前新鲜备份、维护窗口/风险/恢复方案并获明确授权；不能在个人.env下启动此新JAR来“验证”。

## 9. 独立验收证据交接

2026-10-30追加，仅整理、脱敏和校验既有材料，不修改业务代码、不启动或部署服务、不运行迁移、不连接个人库写入、不进入10C-2。完整交接说明见[PHASE_10C_1_REVIEW.md](../handoff/PHASE_10C_1_REVIEW.md)。

指定交付为`output/review/northstar-phase10c1-sanitized-evidence.zip`，**本报告以`docs/progress/PHASE_10C_1.md`原路径包含在包内**，同时包含实际实施计划、Java/TS/SQL/测试及依赖、HEAD基线原文/差异/hash、C01测量和原生/人工记录、C04脱敏摘要及带真实退出码的历史失败/成功日志。私人SQL/学习正文/录音、语音素材和私人浏览器截图排除；纯数学噪声校准原始信号可分享。没有专门的A/B截图或录屏，原有E2E源码及日志保留。

本次交接不新增运行验收结论。源码和候选身份、测试批次及包内可复算范围分开说明；个人009.15版本依据原只读证据，不冒称本轮新查询。白名单、完整性、秘密扫描和引用检查由`phase10c1_handoff.py`执行，旧同名ZIP按hash保留后再替换，等待ChatGPT独立复核。
