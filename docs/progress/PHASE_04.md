# Phase 04｜真实音频、句内 A–B 与精听听写

日期：2026-10-22（Asia/Shanghai）。用户明确授权“开始实施第四阶段，先看提示词”，并在途中要求继续。已读根 AGENTS、实施计划、Phase 03 报告、`Northstar_English_Codex/prompts/04_PHASE.md`、根参考归档中适用播放/听写/验收规范；工作区开始时 Git 干净。

**结论：本地功能验收 PASS_WITH_NOTES，等待用户阶段审核；素材正式发布仍为 BLOCKED。**

本阶段只实施 Phase 04，未开展 Phase 05–09；没有 Git 提交、推送或公开发布。素材来源及合成声音授权继续 pending_review，只作已授权本地功能测试。

## 1. 改动文件与关键决定

- `apps/web/src/lib/media/{AudioController.ts,MediaProvider.tsx}`：单一 HTMLAudioElement，idle/loading/playing/paused/ended/error；查看句、真实播放句与听写目标分开。加载命令 token 隔离旧 play Promise；换句解除旧监听与 A–B，Tab 切换暂停，卸载清资源。播放器/快捷键读取真实 paused，避免快速切句时 React 快照滞后。
- `components/player/PlayerBar.tsx`、`components/lesson/LessonWorkspace.tsx`、`app/globals.css`：十句实播、暂停、上/下句、顺序连播、句循环/列表循环、0.75/1/1.25/1.5速度、真实本句seek；Space/J/K/R忽略输入、可操作元素、IME与修饰键。保留桌面76px底栏，A–B在上方展开；窄屏可换行。
- A–B从媒体真实时长与currentTime取点，校验 `0 <= A < B <= duration`，优先于句/列表循环；使用帧检查和timeupdate兜底，不提供伪波形或跨句连续轴。后台节流不保证采样级边界。
- `components/exercises/DictationEditor.tsx`、`lib/persistence/{db,outbox}.ts`：按课/版本/句子保存草稿；IndexedDB事务完成后才报本机成功，再约500ms防抖同步MySQL。各页面有独立缓存副本；If-Match冲突/不确定回执暂停覆盖，展示两份稿供明确处理。兼容读取Phase03旧localStorage听写草稿，写作未提前升级。
- 正式命令先以UUID持久化到outbox；添加为原子add，避免另一页面覆盖待提交命令；清除时核对eventId，旧回执不会清掉新命令。失败保留原文、目标与UUID，刷新后手动重试同一次提交；不依赖beforeunload保存。
- `apps/api/.../exercise/{ExerciseController,TokenAligner}.java`：服务端英文token编辑距离对齐，大小写/标点容忍，明确equal/omit/insert/replace和词位；原始输入独立保留，同义词不判准确。规范化版本为english_token_v1。
- `V004__attempts_evidence_drafts_review_sources.sql`：听写exercise、不可变attempt/evidence/study_event、command_receipt、草稿、当前状态投影、复习项目/追加来源；复合FK约束课/版本/句/题目与来源对应。只有实际提交才增加practice_count；skip/pause/start不产生证据。
- 同一个数据库事务写入唯一回执、作答、证据、练习次数和错误来源。并发相同eventId由唯一约束裁决，返回原资源；相同ID异操作或payload返回409。空白、非英文token、未播放、跨内容绑定和不可用音源不产生证据；后端独立校验音源状态、大小和SHA-256。
- `study/StudyController.java`、`lib/state/LessonProvider.tsx`、`lib/api/catalog.ts`：恢复点增加实际播放句及句内毫秒位置；恢复为暂停。保存与页面上下文分别归属，仍使用原版本检查；不把恢复点当作作答。
- `components/exercises/ReviewSources.tsx`、`app/review/page.tsx`：展示真实错误来源、原文/标准句、课/版本/句/attemptId与回源重练入口；不提前做Phase07翻卡、评级和调度。首页/报告只修正过时占位文案，不提前计算报告。
- `scripts/grant-study.py`：校验本项目容器/卷/schema身份及成功V004后，才授权新表最小写权限。运行账号不能改内容、设置、历史作答/证据，也没有DELETE权限。
- 测试：`apps/web/tests/media.test.ts`、`apps/api/src/test/.../exercise/`、既有健康/恢复测试；新增`dictation-browser-smoke.{js,sh}`及`player-recovery-browser-smoke.js`。写入型E2E启动前与页面内均检查健康响应中依据实际 `SELECT DATABASE()` 返回的测试库标记；主库拒绝运行。
- 文档：README、实施计划、OpenAPI 0.4.0、DEPENDENCIES、DESIGN_DEVIATIONS和本报告。未新增依赖或改锁文件、全局Node/Java、密码与既有卷。

### 盲听与学习真实性

提交前原文、译文、讲解和播放器文本不挂载，辅助属性不包含标准答案；提交后只展示本次目标的反馈。换句/换Tab重置反馈。课文可主动查看；浏览器保守记录同版本已暴露目标，反馈展示也标记暴露，改写/重试不伪装成独立听写。当前不计算“独立听写正确率”，此标记不是防作弊保证。

首次输入记录in_progress，可显式开始/恢复、暂停、跳过；practiced表示真实作答，答错也算练习，不表示掌握。界面分别显示当前轮状态与累计真实尝试；读取失败时不显示未确认次数。浏览器的audioPlayed是客户端播放观察，不能证明用户确实听到或理解，更不是专业评测。

## 2. 实际验证

原始证据保存在被忽略的 `docs/evidence/phase-04/`；截图与日志不会自动公开分发素材。

| 检查 | 实际结果/证据 |
| --- | --- |
| 项目运行时/身份 | Node22.23.2、npm10.9.8、Java21.0.12.1；专属MySQL8.4、端口3100/8085/3308；doctor.log |
| 前端类型、lint、单元与生产构建 | PASS，12项Node单测；包含媒体边界、旧Promise、真实seek/速度、pending切换暂停。typecheck-delivery.log、lint-delivery.log、web-tests-final.log、web-build-delivery.log |
| Java21 + 真实MySQL集成 | 15项、0失败/错误/跳过；api-db-tests-release.log；V003→V004升级和重复迁移0条 |
| 接口语义 | 并发同事件只生成1 attempt/1 evidence/1 source；不同payload409；缺/旧草稿revision428/412；跨绑定422；未播放/空白422；音源missing503且回执回滚；跳过/暂停不增加次数；同上日志 |
| 既有Python脚本 | 8项全部通过，script-tests.log |
| API健康与安全回归 | PASS，真实状态/no-store/404/405/Host及Origin403、无通配CORS；api-smoke.log |
| 核心Playwright闭环 | PASS，browser-suite-final.log：十MP3真实解码/currentTime推进、四速度、seek、A–B回跳、逐句/刷新草稿、第6句beside→behind精确定位、原文保留、幂等重放、响应丢失后刷新重试、音源故障/重试、复习来源；pageErrors=[] |
| 专项恢复与最终脚本入口 | PASS，`python3 scripts/local.py exec sh scripts/dictation-browser-smoke.sh` 顺序完成两个套件，均passed:true、pageErrors=[]。恢复套件覆盖位置暂停恢复、快速切句、四快捷键、三种真实ended循环、断网草稿、多页冲突跨刷新及存储禁用；browser-suite-final.log |
| 真实记录跨服务重启 | PASS，隔离库阶段/真实错误来源/第9句草稿/完整播放恢复点重启前后相同；test-restart.log |
| 主库迁移与数据安全 | PASS，迁移前快照`.local/backups/phase04-main-before.sql.gz`；V004成功，原设置/恢复点与4册1课10句不变，主库attempt/evidence/review_source均0，未混入E2E；main-before.tsv/main-after.tsv/main-state.tsv/runtime-closeout.log |
| 主库写入E2E防护 | PASS，实际主库标记false时脚本在打开浏览器前拒绝执行，原数据再次核对无变化；e2e-main-guard.log |
| OpenAPI/Git空白检查 | YAML解析15个实际路径；git diff --check通过 |

## 3. 验证发现与修正

1. Node22 strip-only单测不接受TypeScript构造函数参数属性，改成显式字段，未加转译依赖；早期失败保留在web-tests-initial.log。
2. 普通沙箱Docker socket/Java附加代理权限失败；获准环境真实15项后端测试通过。原api-compile-initial.log/doctor-initial.log保留，不把环境失败冒称通过。
3. 修正草稿同步回执和新输入竞争、多页缓存互相覆盖风险，以及旧回执删除新命令风险。服务端版本不确定时保留文本、停止自动覆盖。
4. 浏览器专项发现快速切句后Space可读到旧React状态，统一使用controller音频元素真实paused，新增对应单测并复验。
5. 测试脚本初期误用句子sID匹配音频aID、固定累计次数、过早检查异步投影/Tab/新目标编辑器、仅匹配“音频”而最终提示为“音源”；逐项改成实际资源/基线/明确状态等待。失败日志完整保留。

## 4. 截图、限制与下一阶段

主要截图：`dictation-protected-1440x900.png`、`dictation-diff-1440x900.png`、`ab-loop-1440x900.png`、`audio-error-1440x900.png`、`review-sources-1440x900.png`、`player-{1440,1280,979,375}x900.png`及草稿冲突截图。已实际查看桌面错词反馈、375px播放器和草稿冲突截图，不宣称像素级一致或完整WCAG合规。

尚未验证真实Safari/Firefox、屏幕阅读器、真实声音听感和OS后台节流边界；麦克风/ASR/发音分数不属于本阶段。A–B不是采样级精确剪辑，原AC-18的波形/跨句部分继续延期；素材来源授权阻塞正式发布。当前采用后端乐观锁发现多页冲突，没有额外BroadcastChannel即时通知；已有页面可缓冲草稿和命令，但没有Service Worker，不承诺冷启动离线。

Phase05需用户审核本阶段后才能启动；下一步才是精读词汇、证据题和知识点关联。本轮交付后停止，不自动提交、推送或进入下一阶段。


### 交付运行状态与手工补验

最终Web/API/MySQL保持运行，入口 `http://127.0.0.1:3100/lesson/demo-01?tab=dictation`，API8085、MySQL3308。已关闭测试Playwright浏览器并切回主学习库；自有PID/cwd、健康迁移004与数据未变核对见 `logs/final-runtime.json`。停止仍使用 `sh scripts/dev-down.sh`，不会删除卷或学习数据。

人工补验建议：使用Safari打开第6句，实际听取四速度及A–B；切到其他应用再回来检查后台边界与恢复；使用系统真实音频输出确认听感。以上人工项目本轮未测，不能由Chromium媒体状态断言替代。麦克风权限验收留Phase06。


### 后续经授权的语音对比与更换

2026-10-22，用户另行要求评测免费Edge TTS并在更好时更换，随后试听明确选择英式Sonia/Ryan。已据此新增不可变v2和显式旧版入口，不覆盖本报告交付时的v1与学习记录。最新实施/验收以 `docs/TTS_EDGE_EVALUATION.md` 为准；本次没有进入Phase05。

TTS最终验收：主学习库默认v2、旧版可访问、10句HTTP音频哈希及14组原数据哈希核对通过；前端13项、后端15项、脚本8项测试通过，v2核心/恢复与跨版本浏览器套件通过。主库验证日志见 `docs/evidence/tts-edge/logs/main-verification.log`，详细结论和限制见上述TTS报告。


### 用户追加：参考图播放栏与词句标记（2026-10-22，历史整课版；已由下节单句修正替代）

**结果：已更新正式Web并通过本轮验证；没有进入Phase05。**

- 设计基准：用户提供的横向参考图；保留固定76px底栏。深绿52px圆形播放按钮、左右时间、4px轨道和20px白色手柄；单词点5px、句子点10px；终点为22px红色“终”。右侧保留循环、速度和设置，原上/下句、模式与A–B移入设置面板。
- 文件：`PlayerBar.tsx`、`globals.css`、`lib/api/catalog.ts`、`lib/media/{AudioController,timeline}.ts`、`demo-word-timings.json`；新增`build-playback-timings.py`、`player-timeline-browser-smoke.js`和定向单测，既有两套浏览器脚本适配折叠设置；README与内容清单同步说明。
- 数据：同批英式MP3的WordBoundary提供68个单词起点；10个句子起点使用逐段累计位置。每段词数据绑定版本、SHA256和时长，生成脚本核对原文词序与音频。v1无词点，明确降级为句点；未覆盖冻结课包、数据库schema或历史作答。
- 交互：进度条可拖动/键盘定位，标记可跳转；跨文件跳转等待新音源metadata后定位，保留暂停/播放意图并清除旧A–B。点击“终”在列表循环中仍停于最后音频末尾。盲听时不通过标记title/aria泄漏英文；单纯播放不产生练习证据。

验证日志目录：`docs/evidence/player-timeline/logs/`。

| 检查 | 实际结果 |
| --- | --- |
| 时间点生成/音源绑定 | 10段、68词；同次缓存与已发布MP3哈希匹配；无网络 |
| 类型检查/ESLint/生产构建 | PASS；`typecheck-final.log`、`lint-final.log`、`build.log` |
| 前端单测 | 16项，0失败/跳过；`unit-final.log` |
| 新时间轴浏览器专项 | PASS，pageErrors=[]；实际词点/句点、真实鼠标拖动、键盘定位、四速度、模式、A–B回绕、终点暂停、旧版降级、盲听保护、不产生练习证据；`browser-final.log` |
| 既有核心与恢复回归 | 两套均passed=true、pageErrors=[]，独立测试库；`dictation-browser-smoke.log`、`player-recovery-browser-smoke.log` |
| UI验收 | 查看实际截图；1440/979/640/375宽度保持76px单行、页面不横向溢出，设置可开关/Escape关闭 |
| 正式运行核对 | 主库健康标识false、68词点/10句点实际加载；`production-browser.log`。仅重启自有Web（PID4679），原主API保持运行，独立测试服务已停止 |

实际查看的截图：`initial-1440.png`、`player-375.png`、`settings-375.png`、`player-production.png`；另存`player-{1440,979,640,375}.png`和`workspace-production-1440.png`，均在`docs/evidence/player-timeline/`。

失败与修正：首次单测暴露累计秒浮点误差，改为累计毫秒；另一断言漏处理感叹号，修正测试归一化。首次浏览器键盘断言过早读取React值，改为等待实际媒体位置；正式截图脚本首次使用无baseURL的相对请求，改为绝对URL。初始日志保留，不冒称首次全部通过。Next dev自动生成的AGENTS和临时类型入口在停预览/生产构建后清理恢复。

限制：词点是合成服务自动对齐，未人工逐词校正；仍非波形/采样级精剪。窄屏词点密集，可用键盘或设置内句进度定位；Safari/Firefox和实际设备触控、屏幕阅读器本轮未测。没有新增运行依赖、改动音频、自动提交或推送。


### 播放栏范围修正：仅当前单句（2026-10-22）

用户澄清要求每个单句，上一版整课聚合属于范围误解。本节取代上节关于累计时间轴、68词同时展示和10句点同时展示的交付说明。

- `PlayerBar.tsx`仅取当前播放句：一个0秒起点、本句词边界、本句红色“终”；左右时间及拖动范围只对应该句实际音频时长，尚未加载时以该句manifest时长显示。切换播放句时更新点位、时长和计时，不聚合其他句子。
- 保留参考图布局、真实词时间戳、速度/模式和A–B。句内seek保留A/B配置，启用循环期间主动定位会停止循环；“终”只暂停到本句末尾，列表循环模式也不跳到其他句。
- 移除`timeline.ts`中的整课累计/跨句定位函数及相应测试；单句和旧版降级验证更新到`player-timeline-browser-smoke.js`。去掉设置面板内重复进度条，原核心脚本显式打开设置后操作A–B。
- README和CONTENT_MANIFEST已按单句语义更正；未改音频、课包、数据库或运行依赖。

本轮证据目录`docs/evidence/player-sentence/`：typecheck、lint和16项单测通过；十句各自词数/句点/实际duration、词点点击、真实鼠标拖动与键盘句内定位、A–B、本句终点暂停、下一句重置、四宽度无横向溢出、听写遮挡与旧版降级全部通过；既有听写核心及恢复专项通过，三套浏览器结果均passed=true、pageErrors=[]。日志在`logs/`；实际查看了`player-1440.png`。词时间戳尚未经人工逐词校正，Safari/Firefox等设备限制沿用前述说明。

正式更新补验：生产构建通过（`player-sentence/logs/build.log`）；仅重启主Web为PID10801，主API PID96913保持运行，测试预览已停止。正式浏览器确认只有1个句子起点、当前句6个词点和3.432秒时长（`logs/production.log`）；截图`player-sentence/player-production.png`。已重新打开主工作台；`git diff --check`通过，未提交Git。


### 用户追加：句子间距、倍速循环、点击播放与终点重合（2026-10-22）

- `LessonWorkspace.tsx`、`globals.css`：句子卡片独立12px间隔；点击整句同步选择并从头播放，删除行尾播放按钮。3px绿条绑定selected而非playing，在暂停/结束后保留，并放在卡片自身内侧，修正旧li阴影的裁切。
- `PlayerBar.tsx`：原倍速下拉改为按钮，从1×开始按1→1.25→1.5→0.75→1循环，实际设置同一audio元素的playbackRate。
- 手柄改为与标记共享百分比坐标的可视手柄，轨道Pointer Capture负责鼠标/触控拖动；range保留可访问语义和键盘操作，Home/End精确定位，避免原生步长把3.432秒终点舍入为3.43秒。手柄与红色终点横纵中心差均小于0.1px，末尾不再露出偏左的白圈。
- 复用并更新三套浏览器脚本适配新按钮；未改后端、数据库、音源或依赖。README说明同步更新。

验证：typecheck、lint、16项单测通过；时间轴专项、听写核心与恢复专项三套均passed=true、pageErrors=[]。新增检查覆盖10句点击播放/局部时间轴、卡片间距、暂停后绿条、移除行尾按钮、倍速完整一轮及实际音频速度、终点重合与非整步时长、真实拖动、键盘、A–B、四宽度无溢出及盲听保护。日志在`docs/evidence/player-polish/logs/`。已实际查看`selected-paused-1440.png`与`endpoint-aligned.png`；其他响应式截图同目录。Safari/Firefox、真实触控设备本轮未验证。

正式发布到本地运行实例：生产构建通过（`player-polish/logs/build.log`），主Web更新为PID14625，主API PID96913保持运行。正式浏览器验证1x按钮、12px句间距、选中绿条和零行尾播放按钮（`logs/production.log`）；截图`production-1440.png`。隔离预览已停止，用户工作台已重新打开；本轮未提交或推送Git。


### 状态层级修正：选中高于悬停（2026-10-22）

用户指出循环按钮选中与hover过于相近。本次仅修改`apps/web/src/app/globals.css`，按状态职责覆盖通用按钮规则：默认透明；未选中hover为浅灰#f0f2f4；循环选中/设置展开为深绿#235c49配白图标，hover保持此颜色；选中按下为更深绿#173f32；键盘focus-visible使用独立3px外圈；禁用透明灰且降低透明度。单句循环数字徽标继承当前底色。句子卡片hover改为中性灰，选中保持浅绿底、4px绿条和深绿序号块，hover/active不覆盖持久选择。

验证：lint与生产构建通过；正式运行实例中的Chromium检查默认/hover/selected/selected+hover/pressed/focus-visible，以及设置展开、句子选择、375px无横向溢出全部通过，pageErrors=[]。禁用样式以临时DOM disabled标志模拟验证，并未制造后端故障。检查浏览器阻止1次恢复点PUT，避免为样式验收写入主库；未操作练习提交。本次CSS变化未重复业务单测。

证据`docs/evidence/player-states/`：日志`logs/{lint,build,browser}.log`；实际查看`hover.png`和`selected-hover.png`，另存`selected-focus.png`、`sentence-states-1440.png`及`selected-375.png`。仅重启自有主Web为PID16155，主API PID96913继续运行；无依赖/数据/播放逻辑改动。Safari/Firefox本轮未测。


### 修复：配音切换错误跳到听写（2026-10-22）

根因：`LessonWorkspace.tsx`内容来源弹窗的两个配音Link均写死`tab=dictation`，导航后resolveContext按显式URL优先，因此无论原Tab是什么都会进入听写；“知道了”原本不导航。

最小修复：弹窗使用`context.ts`新增`lessonVersionHref`复用既有URL序列化，保留当前Tab、英文/译文开关；根据冻结Demo已验证的版本前缀/稳定后缀ID映射同一句，例如v1-s06到v2-s06。不能确认前缀的陌生句ID不会传到目标版本，由现有加载器安全回退。版本按钮点击时关闭弹窗，同版本点击不改变URL；不复制草稿或练习记录到另一个版本。没有增加API、数据迁移或依赖。

验证：typecheck、lint、17项单测与生产构建通过（`docs/evidence/version-context/logs/`）。新增单测覆盖六Tab、两种英文/译文开关组合、双向版本及非法句子ID；真实Chromium逐项验证六Tab的v1→v2→v1后URL/选中Tab/对应第6句/显示开关保留，当前版本和“知道了”关闭弹窗且URL不变，pageErrors=[]。浏览器预设拦截恢复点PUT用于只读验收，本次实际触发0次；未提交任何练习。截图`source-dialog-text.png`、`after-switch-still-text.png`。

仅重启主Web为PID17882；主API PID96913及MySQL保持运行。未更改历史数据、提交或推送Git。


### 播放设置重设计与句子选中样式更正（2026-10-22）

设计：保持白底/深绿主题，设置面板收窄为480px，20px内边距和分组留白；播放模式与切句独立排列，A–B为按需展开的区间编辑，说明折叠到底部。去掉反复使用boundary样式带来的多道分隔线。A/B两个点各有时间读数和定位操作，底部只保留一个绿色循环主按钮及次要清除操作。

状态：未加载提供真实“加载本句”入口；加载中禁用重复操作；B点需在A点之后；有效区间方可循环；已开启但暂停与真正循环中分开表述。错误在面板内显示原错误和重试播放，避免与外部错误条重复；关闭/Escape恢复焦点。窄屏面板内部滚动，关闭按钮保留在头部。

用户进一步明确红框中的句子左侧绿条需要移除。本次将selected的inset shadow改为none，保留绿色底、统一细边框和序号高亮；未选中hover是浅灰，selected+hover仍保留绿色。此项取代之前交付中的竖条设计，不改变点击句子自动播放。

文件：新增`components/player/PlayerSettings.tsx`，`PlayerBar.tsx`仅负责传入当前媒体/句子和面板开关；`globals.css`新增面板局部样式并移除旧杂排规则；README与`player-timeline-browser-smoke.js`去除绿条的旧描述/断言，新增可复用`player-settings-browser-smoke.js`。无后端、音源、DB schema或依赖变化。

验证与证据：`docs/evidence/player-settings/`。

- 17项既有单测、最终typecheck/lint通过。
- 新设置专项通过：默认/未加载/加载中/已加载、有效/无效区间、实际音频A–B回绕、暂停时不假报正在循环、清除、帮助展开、979/640/375宽度边界、内部滚动、Escape焦点恢复、音源故障及真实重试；pageErrors=[]，`logs/settings-ui.log`。此专项使用隔离测试库，并在浏览器模拟空恢复点/拦截恢复点写入以控制初态。
- 原有时间轴、核心听写和恢复三套通过，均passed=true、pageErrors=[]；`logs/{timeline,dictation,recovery}.log`。
- 句子定向检查：点选底色rgb(224,241,235)、hover底色rgb(243,245,247)，shadow均none；selected+hover不覆盖选中；`logs/row-states.log`。
- 已实际查看`configured-1440.png`、`panel-375.png`、`selected-vs-hover-1440.png`；其他截图含default/unloaded/running/error与640/979尺寸。

过程记录：前一轮自动批准服务因用量限制未执行浏览器验证；恢复后重新打开被中断的测试浏览器继续。首次回归发现“播放模式”分组与select同名造成定位歧义，改为普通div而保留select标签，失败日志`timeline-label-initial.log`保留。没有绕过批准或将未执行测试标为通过。Safari/Firefox与真实触控设备未测；浏览器后台复读仍不保证采样级精度。

正式运行补验：生产构建通过，主Web已更新为PID85697，主API PID96913保持运行。正式浏览器确认句子shadow为none、hover与selected底色不同、新设置面板宽480px且帮助默认折叠（`player-settings/logs/production.log`）；测试预览已停止，用户工作台已打开。最终`git diff --check`通过，未提交Git。


### 句末大点：定位最后单词的发音结束（2026-10-22）

用户要求单词起点之外显示完整句子的结束位置。`timeline.ts`新增`sentenceEndPoints`：将当前原文词序与已经校验的WordBoundary对齐，按 . / ? / ! 找句末，取该词startMs+durationMs；逗号不生成句末。词序不匹配或缺少词时间戳即不生成，不做等分或按文件总长猜测。

`PlayerBar.tsx`增加10px句末大点（原单词起点为5px），复用句内seek并保留暂停/播放意图；红色“终”仍是文件末尾，0秒音频起点保留。第4条“Nice to meet you, Mia. I am Leo.”分别在Mia的1.6875秒和Leo的3.3375秒显示大点，音频总长4.2秒；不是最后单词的起点。盲听title只显示句末序号与时间，不泄露答案词。

文件：`lib/media/timeline.ts`、`player/PlayerBar.tsx`、`player/PlayerSettings.tsx`、`globals.css`、`tests/timeline.test.ts`及README/内容清单。本次无后端/音源/数据/依赖改动。

验证：最终typecheck、lint、19项单测（0失败/跳过）和生产构建通过。新增单测验证逗号排除、文本不匹配降级、Mia/Leo的精确结束值及10条音频共16个句末。Chromium实际逐条播放验证标记数量，验证10px/5px尺寸、1.6875/3.3375秒真实定位、播放状态保留、独立红色文件终点、375px不溢出、盲听tooltip保护和v1无假标记，pageErrors=[]。UI测试浏览器模拟空恢复点并拦截恢复点PUT，未写入主库或提交练习。

证据：`docs/evidence/sentence-endpoints/logs/{typecheck,lint,unit,build,browser}.log`；截图`endpoints-at-start.png`、`endpoints-1440.png`、`workspace-1440.png`、`endpoints-375.png`。只重启主Web为PID87299，主API PID96913和MySQL保持运行。时间点来自同次合成的服务对齐结果，尚未人工逐词校正；Safari/Firefox本轮未测，未提交或推送Git。

### 听写状态标签垂直居中（2026-10-22）

红框标签偏上来自toolbar默认交叉轴stretch：标签被拉高至按钮高度，文字仍按原padding定位。仅给DictationEditor的播放/状态行增加dictation-playback局部类，行内align-items:center，标签使用flex居中和显式1.5行高；未修改其他toolbar/tag或练习逻辑。

文件：`apps/web/src/components/exercises/DictationEditor.tsx`、`apps/web/src/app/globals.css`及本报告。lint、生产构建、git diff --check通过。Chromium在1440/375px宽度实测按钮与标签中心Y差均为0px，标签高度24.5px、无水平溢出，pageErrors=[]；已查看桌面局部截图。证据：`docs/evidence/dictation-status-alignment/row-{1440,375}.png`与`logs/{lint,build,browser}.log`。UI验证拦截恢复点PUT，控制台对应ERR_FAILED为该拦截产生；未提交练习。外层日志检查首次因JSON空格假设失败，随后解析实际JSON确认passed=true，未重复业务操作。

只重启本项目主Web为PID89647，健康检查通过、测试库标志false；主API PID96913与MySQL保持运行。Safari/Firefox本轮未测，未提交或推送Git。

### 用户授权提交当前阶段源码（2026-10-22）

用户明确要求将当前改动提交到GitHub。本次提交范围为Phase04实现、英式Edge v2内容元数据/词时间戳/生成脚本/评测报告，以及后续已验收的播放器、内容版本切换、设置面板和听写状态居中修复；未开展后续阶段。检查origin/main与本地HEAD一致后提交，未改写历史。

提交前补验：TypeScript类型检查通过，19项前端单测全部通过；最近一次生产构建、lint及1440/375px实际UI居中验证见上一节。60个候选文件共约455KB，未发现本地.env密码、常见密钥模式或生成目录；git diff --check通过。源码提交不包含.local、.env、测试日志/截图、原型及合成MP3，沿用现有Git忽略边界；仅克隆公开仓库仍不具备完整音频内容，详见CONTENT_MANIFEST。本次Git操作不重启服务、不修改数据库。
