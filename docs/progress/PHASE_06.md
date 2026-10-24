# Phase 06｜口语跟读录音、写作草稿与历史版本

日期：2026-10-23（Asia/Shanghai）。用户授权“现在开始实施第六阶段，先看下这个阶段的提示词，再进行实施”，中途明确“继续”。已读 AGENTS、实施计划、`Northstar_English_Codex/prompts/06_PHASE.md`、Phase05 最新报告、根参考归档的 P06/P07 与 AC09/10。开始时工作区已有第五阶段未提交改动，均保留；未提交/推送 Git，未进入 Phase07–09。

**结论：本地自动化验收 PASS_WITH_NOTES，等待本阶段审核。真实麦克风/操作系统权限和 Safari 仍待人工验收；素材正式发布仍为 BLOCKED。** 假设备测试不代替真人听感或专业语音评测。

## 1. 改动文件与关键设计

- `apps/api/src/main/resources/db/migration/V006__recordings_and_writing_revisions.sql`：添加 writing_task/source/draft/revision、personal_recording、recording_observation、practice_progress；扩展 learning_evidence 的排他来源，旧 attempt 证据保留。版本/课/句子通过外键和服务端上下文校验绑定。
- `apps/api/src/main/java/local/northstar/practice/{PracticeCommands,RecordingController,WritingController}.java`：复用 command_receipt 的 UUID/负载哈希/事务幂等规则。录音上传不产生练习证据，ready 本句文件的客户端回放观察才产生 evidence；可选人工自评，明确不是发音分。暂停/跳过不删除历史，不能直接上报 practiced。
- 录音 JSON/Base64 上传（沿用既有本地写入/CSRF过滤），解码32字节至8MiB，时长250ms至2分钟；MIME和容器头校验，不声称服务端完整解码或语音分析。原始 MIME、哈希、字节数、客户端录制时长/时间与服务端时间均可追溯。
- 私人文件默认 `~/Library/Application Support/NorthstarEnglish/recordings/<schema>/`，子目录0700、文件0600；可用 Java `--northstar.recording-root=<absolute-path>` 配置，未改变全局环境或 `.env` 秘密。测试库独立子目录。文件先临时写入、force与原子rename，再提交pending元信息，最后ready；文件/SQL不是跨介质原子事务。启动校验哈希，识别pending/缺失/孤儿，孤儿与partial只记录数量并保留待人工处理，不做危险清理。删除先提交墓碑再unlink，重试可继续；重放旧上传不复活删除文件。
- `ContentSeeder.java`：两份冻结课版本各播种一个原创写作任务及第5/6/9句来源，已有内容包和音频不改写。每个 revision 通过不可变 task/source 关联多句，无默认句占位。
- 写作草稿乐观版本控制；正式提交必须匹配草稿内容/版本，行锁分配单调版本号，父版本须属于同任务。并发不同event生成不同编号，同event只产生一版。运行账号无权改写历史版本。正式版本不提供覆盖/删除接口，回载只改草稿，再保存生成新版本。
- `common/ApiProblems.java`：安全返回本阶段可预期领域错误；`health/HealthController.java` / `scripts/api-smoke.py` / OpenAPI 更新能力阶段为06，AI/ASR/专业评分仍false。
- `apps/web/src/lib/media/recorder.ts`：idle/requesting_permission/recording/processing/ready/failed/denied，实际协商MIME；权限拒绝、无设备、设备占用、格式不支持和断开提示；2分钟自动停止，dispose处理迟到权限并释放轨道。
- `components/exercises/RecorderPanel.tsx`：目标句、示范音、录制/停止/重录、多段可回放记录、人工自评、下载失败上传缓冲、确认删除/确认丢弃本机缓冲。Blob+原eventId先写IndexedDB，上传失败刷新可重试；存储配额失败保留内存下载入口并明确报错。下载对象URL及时撤销。未停止即离页会取消当前录制，不虚构已保存。
- `LessonWorkspace.tsx` / `lib/media/MediaProvider.tsx`：替换跟读/写作占位，录音期间暂停示范音、禁用换句/Tab、播放器fieldset+inert与快捷键保护；回放互斥。原桌面侧栏、主区/助教和底部播放器保留。
- `WritingEditor.tsx` / `RevisionHistory.tsx` / `RevisionDiff.tsx` / `lib/api/practice.ts`：IndexedDB先落草稿、650ms防抖同步；草稿冲突保留两份供选择，明确412拒绝后可重新生成提交，未知回执保留原UUID；V1/V2列表、整段前后增删色比较、确认回载。句数/目标表达仅基础规则提示，明确非AI语法校对，不提供完整范文或能力分。旧占位编辑器的localStorage原值未删除，不自动提升为正式版本。
- `globals.css`：沿用现有视觉变量/边框，录音列表、版本列表和窄屏比较区。无新依赖、无锁文件/全局Node/Java版本变化。
- 新增后端 `PracticeIntegrationTest.java`、前端 `tests/recorder.test.ts` 与 `scripts/practice{,-failure}-browser-smoke.js` / `practice-browser-smoke.sh`。更新 README、DEPENDENCIES、DESIGN_DEVIATIONS、实施计划、OpenAPI及本报告；`grant-study.py`仅追加V006最小写权限。

## 2. 实际命令与验证

证据根目录：`docs/evidence/phase-06/`，沿用既有Git忽略规则；日志不输出凭据。运行Node22.23.2 / Java21.0.12.1 / 专属MySQL8.4，原服务端口3100/8085/3308保持。浏览器为已安装 Chromium 148.0.0.0，使用缓存 Playwright CLI 0.1.22，不新装依赖/浏览器。

| 验证 | 实际结果与日志 |
| --- | --- |
| 类型、lint、生产构建 | `python3 scripts/local.py exec npm run typecheck` / `lint` / `build`，PASS；`logs/{typecheck,lint,build}-release.log` |
| 前端单测 | `python3 scripts/local.py exec npm test`，21项PASS、0失败/跳过；`logs/web-tests-release.log`。新增迟到权限释放与拒绝/不支持浏览器不生成录音 |
| 真实MySQL与Java21 | `python3 scripts/local.py db-test`，17项PASS、0失败/错误/跳过；`logs/api-db-release.log`。新增并发重复event、递增编号、旧稿不变、只追加权限、草稿冲突、跨版本/跨句拒绝、上传不计证据、回放幂等、跳过保留历史、重启pending恢复、缺失文件、孤儿保留、确认删除/不复活、未知录音404 |
| 跟读与写作E2E | `python3 scripts/local.py exec sh scripts/practice-browser-smoke.sh`，两套均passed=true、pageErrors=[]；`logs/browser-release.log`。本次通过环境变量指定缓存CLI与已安装浏览器，脚本默认仍可用npx CLI。脚本先检查隔离库标记 |
| 浏览器主流程 | 真MediaRecorder假麦克风→真实文件/API→可解码回放→人工观察证据；上传前无证据、未回听拒绝、换句隔离、录制锁目标、权限拒绝/跳过不增记录、上传回执丢失后刷新重试同UUID、确认删除。写作草稿单独同步、V1/V2刷新、丢回执幂等、diff/确认回载生成V3、1440/375无横向溢出 |
| 浏览器故障/冲突 | 真实第二写入者制造草稿CAS冲突、提交瞬间冲突后恢复；空白版本禁用。故障注入无设备/不支持MIME/设备断开、轨道释放且不保存，API503列表禁录制并可重新读取；注入场景明确不冒充真实硬件故障 |
| 服务重启真实媒体 | 停止并重启自有隔离API/Web后，之前浏览器生成的真实录音仍能解码且currentTime推进，7个写作版本可读；`logs/restart-browser.log` passed=true、pageErrors=[]。验证拦截所有写接口 |
| 既有功能回归 | 听写、播放器恢复、阅读3套均passed=true、pageErrors=[]；`logs/regression.log`。含十音源、快捷键、逐句草稿、幂等、复习来源及词卡/证据题 |
| 脚本单测 | `python3 -m unittest discover -s scripts/tests`，8项PASS；`logs/script-tests.log`。其临时env生成发生在测试目录，没有替换项目.env |
| API健康/安全 | `python3 scripts/local.py exec python3 scripts/api-smoke.py`，隔离及最终主实例PASS；`logs/api-smoke{,-main}.log`。真实DB/阶段06、no-store、404/405、Host/Origin拒绝、无通配CORS |
| 主库备份/迁移 | `.local/backups/phase06-main-before.sql.gz`（0600），迁移前25表原列哈希；主库V005→V006后25表比较无差异；扩表按迁移前列投影比较，Flyway只比较原记录。`logs/main-before.log` / `main-after.log` / `main-delivery.log` |
| 主库数据保护 | 新增2写作任务/6来源；recording/observation/draft/revision/progress均0。既有4 attempts、4 evidence、1 review_source原样保留。所有写入E2E均只在隔离库 |
| OpenAPI/空白检查 | Ruby解析27条路径；`logs/openapi.log`；`git diff --check` PASS |

## 3. 失败与修正记录

1. 普通沙箱Docker socket拒绝、Mockito自附加失败：初始 `doctor.log` / `api-initial.log`不是通过证据；所需权限获准后真实DB的17项全通过。
2. 误以为既有 `local.py down` 只停Web/API，实际也停了本项目MySQL。已向用户说明，立即用原Compose服务启动同一容器/卷；未删除或重建数据，未停止其他项目。后续停机严格核对本轮PID/cwd，仅停止自有API/Web。
3. npx镜像网络/离线缓存索引不可用；缓存CLI默认期望的浏览器版本未安装。改为显式使用已安装Chromium可执行文件，没有下载或更换全局环境。
4. 首次上传丢回执测试过早读取计数，未等服务器接受/前端错误。修正等待后通过；`browser-initial.log` / `browser-second.log`保留。
5. 重跑浏览器时隔离库已有相同草稿，填相同值不触发change，测试错误等待“已同步”。改用每轮不同文本，最终完整通过；保留 `browser-final.log` / `browser-third.log`，通过以 `browser-release.log` 为准。
6. 收尾补上显式412提交冲突恢复、回放按真实时间推进累计并在已接受观察后清零、未知录音404、孤儿识别和旧上传不可复活删除文件，全部重新验证。

## 4. 验收结果与人工步骤

| 验收条目 | 结果 |
| --- | --- |
| 授权后的录制/停止/回放/重录、跨刷新与服务重启持久访问 | 自动化PASS（Chromium假设备，真实编码与文件/API） |
| 权限拒绝可跳过，不生成practiced；旧句录音不让新句完成 | PASS（权限拒绝为明确浏览器API故障注入） |
| 私人文件查询/确认删除、上传中断恢复、轨道释放 | PASS；崩溃中间状态集成测试覆盖，无硬关机/磁盘断电测试 |
| 写作非空草稿自动存、V1/V2不可变、并发安全、比较与回载 | PASS |
| 无模型评分、规则与人工自评边界、五种当前状态/累计证据分离 | PASS；未开始由空投影表示，开始/暂停/跳过与证据分离 |
| 真实Mac麦克风许可/系统隐私/真实断开、Safari/Firefox媒体兼容 | **未测，待人工** |
| 素材/合成声音正式发布授权 | **仍BLOCKED，本阶段不改变授权状态** |

人工验收（尚未执行，不记为通过）：

1. 使用Chrome打开本地跟读第5句；在macOS与浏览器允许麦克风，先听示范、开始录制、说出目标句、停止。核对系统麦克风指示关闭，再回听并人工自评；确认没有发音分。录制期间换句/Tab/播放器应不可操作。
2. 刷新、关浏览器重开；用已核对PID的本项目服务重启方式重启Web/API（不要调用危险清理/删卷），确认此录音仍可回放，写作V1/V2内容不变。SQL备份不包含媒体，文件目录需另备份；导出/一键备份工作流留后续阶段。
3. 新浏览器权限配置中拒绝麦克风，再点录音；应提示原因，可重试或跳过。跳过不新增回放证据。检查macOS拒绝、无设备、设备占用/拔出时的实际提示及资源释放。
4. 在Safari重复录音/停止/回放/刷新，核对实际MIME是否支持；若格式不支持应明确失败并可继续其他学习。真实设备听感、Safari/Firefox与触控本次未验收。
5. 仅在明确要删除的私人录音上点删除，第一次不应删除；确认后文件不可播放，旧证据不被改写。对待上传缓冲先下载所需副本，确认丢弃只影响浏览器缓冲。

截图在 `docs/evidence/phase-06/screenshots/`：`recording-1440.png`、`permission-denied-1440.png`、`writing-{1440,375}.png`、`recording-375.png`、`device-failed-375.png`、最终主库空态 `production-{speaking,writing}-1440.png`。实际查看桌面跟读/写作、375px录音/故障图；不声称像素级一致或完整无障碍合规。

## 5. 本地交付与下一步

最终主Web/API/MySQL保留回环地址运行，口语入口 `http://127.0.0.1:3100/lesson/demo-01?version=demo-01-v2&tab=speaking&sentence=demo-01-v2-s05`，同页可切写作。最终主API/Web监督PID为29679/29756；隔离测试实例和本轮浏览器均关闭。最终主浏览器验证拦截全部写请求，结果见 `logs/production.log`，主库再次哈希见 `logs/main-delivery.log`。

本阶段等待用户审核；真实麦克风人工项与素材授权仍待补齐，不自动进入Phase07，不提交或推送Git。工作区继续保留用户此前第五阶段及其他既有改动。

### 用户追加：播放自动计次及录音按钮间距（2026-10-23）

用户指出原生音频已播放完但“已回放”仍为0，且自评区与删除按钮贴在一起。根因是原实现只在手动“记录本句回放”或自评时提交观察；删除按钮直接接在toolbar后没有纵向间距。本节取代前文“回放后显式记录才入库”的交互。

- `RecorderPanel.tsx`：真实播放累计达到250ms后自动发送幂等回放观察，每次play周期最多一次；seek跳跃不当回听，暂停后继续或重播需再次实际回听才加一次。移除手动计次按钮，计数以服务端回执刷新；未确认/失败操作保留原outbox UUID，可刷新重试，不显示虚假成功。
- `RecordingController.java`：新增 `/recordings/{id}/ratings`，校验课/版本/句子及已存在的本录音playbackEventId，自评作为不可变command_receipt保存，关联原回放；不增加recording_observation或learning_evidence。旧回放/自评历史保持原样，无数据库迁移或新依赖。
- `globals.css`：自评区上方12px，删除区与自评区间16px；自评按钮仍沿用toolbar的8px换行间距。
- 同步 README、OpenAPI、`PracticeIntegrationTest.java`、既有 `practice-browser-smoke.js`，新增 `scripts/recording-playback-browser-smoke.js`。

证据 `docs/evidence/recording-playback/`：typecheck、lint、生产build、21项前端单测、17项真实MySQL后端测试、API安全契约和git diff --check均通过。新增后端断言验证自评重复UUID/跨句拒绝，且不增加回放或证据。浏览器专项passed=true、pageErrors=[]，实际原生音频解码→自动加一、连续timeupdate/ended只计一次、重播再加一、seek不计数、自评不加次数、刷新计数恢复、服务端接受后丢回执/刷新原UUID重试不重复；1440/375px实测删除区间隔16px、无横向溢出，已查看375px截图。日志 `logs/browser.log`，截图 `screenshots/buttons-{1440,375}.png`。完整跟读/写作浏览器回归亦passed=true、pageErrors=[]，见 `logs/practice-regression.log`。

写入测试仅在隔离数据库与既有假麦克风录音上进行，没有回放或操作用户主库私人录音。主库32张表部署前后全表哈希一致（`logs/main-data.json`），原有录音/学习数据完整保留。本项目主API/Web已更新，监督PID34145/34232；MySQL保持运行，测试浏览器与隔离实例已关闭。本次未重测真实麦克风/Safari/Firefox，未提交Git或进入下一阶段。

### 用户追加：时间戳统一北京时间（2026-10-23）

用户要求截图中的写作版本时间格式化。按完整年月日时分秒 `yyyy-MM-dd HH:mm:ss` 实现。新增 `apps/web/src/lib/formatTime.ts`，将API约定的无偏移UTC时间显式解析为UTC，再固定 `Asia/Shanghai`、24小时制与补零，不随浏览器所在地变化；带Z或明确偏移的时间不重复追加Z，无效值显示“时间未知”。`RevisionHistory.tsx` 的版本列表与比较选择框、`RecorderPanel.tsx` 的录音日期统一复用，保留语义化time/dateTime与“北京时间”title。示例：`2026-10-23T10:16:16.637` → `2026-10-23 18:16:16`。不改变API或数据库时间。

验证：typecheck、lint、生产构建、23项前端单测和git diff --check通过；新增格式测试涵盖无偏移UTC、Z、+08:00、跨日/跨年/午夜及无效时间。证据 `docs/evidence/beijing-time/logs/`。Playwright明确模拟两条写作历史，在浏览器时区America/New_York仍显示正确北京时间（含跨年00:00:00），列表/选择框一致，1440/375px无横向溢出、pageErrors=[]；截图 `time-{1440,375}.png`，已查看375px图。该浏览器测试拦截所有写请求，未修改学习数据，不冒充本轮真实提交验证。

已仅重启本项目Web（监督PID36507），API/MySQL保持运行；无后端或迁移改动，因此本次未重复Java/数据库业务测试。未测Safari/Firefox，未提交Git或进入下一阶段。

### 用户追加：四个Tab切换时页面抽动（2026-10-23）

先按用户“为什么”只读诊断，随后获得“解决一下”授权。逐帧复现发现旧Tab卸载、新Tab加载提示过矮：精读卡先217px再1477px；有滚动时会触发浏览器滚动范围修正，出现180→56→180或180→0。录音/写作组件卸载还负责轨道释放、草稿与迟到回执保护，因此最终采用布局层最小修正，不引入组件缓存或改变这些生命周期。

仅修改 `apps/web/src/app/globals.css`：html增加scrollbar-gutter:stable，预留非覆盖式滚动条空间；lesson-card增加min-height:calc(100dvh - 120px)，使短内容/加载状态保持工作区高度，Tab仍在视口内时不因整页变短强制改变滚动位置；长内容继续自然增长。新增 `scripts/tab-switch-browser-smoke.js`，更新本报告，无依赖、API或数据库改动。

lint、生产构建、git diff --check通过；证据 `docs/evidence/tab-jump/logs/{lint,build,browser-final}.log`。Playwright对reading/writing/recordings读取明确延迟400ms，检查1440/1280/979/375px、0/120/180滚动位置的11组四Tab切换（375px为0/180）：逐帧记录的scrollDrift/gridDrift/xDrift全部0，无横向溢出、pageErrors=[]。所有写请求拦截（实际4次浏览位置写被阻止），未改主库学习数据。已查看 `quiz-stable-1440.png`；另存 `vocabulary-stable-1440.png`。加载数据仍会刷新，但不会将页面短暂缩至一屏而拉动整个工作区。

仅重启核对PID/cwd的本项目Web，最终监督PID38721；API/MySQL保持运行，诊断浏览器已关闭。纯CSS改动未重复业务单测或后端测试；Safari/Firefox、非覆盖式系统滚动条本次未实机验证，不将预留滚动条规则描述为跨浏览器实测通过。未提交Git或进入下一阶段。

### 用户追加：点击录音播放时抽动（2026-10-23）

已按精确时间提取并查看用户提供的6.209秒录屏，确认是口语Tab的原生录音回放按钮。根因与前一节Tab加载高度不同：自动回放观察入队后，pending立即有值，原UI不区分正在请求还是失败，正常保存过程中就在录音列表上方插入“重试待确认操作”，成功后再移除。隔离API延迟回执800ms的修复前逐帧复现：按钮false→true→false，列表文档坐标714.4375→764.4375→714.4375，位移50px，见 `docs/evidence/play-jump/logs/before-reproduced.log`。

`RecorderPanel.tsx`仅将重试按钮显示条件改为pending && !busy：请求进行中不插入额外行；失败/刷新恢复待确认事件后仍显示重试入口，不改变幂等事件、自动计次或录音生命周期。新增 `scripts/playback-layout-browser-smoke.js` 和本报告，无API/SQL/依赖修改。

typecheck、lint、生产build与git diff --check通过。专项浏览器通过真实原生audio按钮点击，在1440/375px逐帧验证800ms延迟成功回执期间cardDrift=0、scrollDrift=0、retryFlashed=false，自动次数各增加1；服务端接受后丢回执、刷新、原eventId重试均正常且不重复计数，pageErrors=[]。证据 `docs/evidence/play-jump/logs/{typecheck,lint,build,browser-final}.log`，截图 `playing-stable-{1440,375}.png`（已查看375px）。全部业务API请求均转发至已验证的隔离测试API8086，仅回放既有假麦克风录音；未回放、修改用户主库私人录音。

本轮恢复时原Web/API未监听，初次探针connection refused不记通过。已启动/更新本项目主实例（监督PID Web21841、API22271），MySQL保持运行。主库32表在恢复主API前后全表哈希一致（`logs/main-data.json`），API健康/安全检查PASS。额外测试API20624及两次诊断浏览器已关闭。原始视频未改动，解码输出仅在忽略的证据目录。首次视频解码受工具格式支持/沙箱限制，使用获准的系统AVFoundation精确取帧后完成检查。

本次未重复Java或其他业务单测，未测Safari/Firefox；未提交Git或进入下一阶段。

### 用户追加：再次录屏中的点击闪动（2026-10-23）

已精确解码并查看用户21.125秒新录屏，覆盖暂停、跳过、原生播放/音量/菜单操作。上一轮只检查了几何位移，没有检查按钮外观变化，验证范围不足。本次独立复现确认：布局坐标不变、audio/button DOM节点保留，但command共用的busy/pending把整块录音区按钮native disabled同时切换，触发全局button:disabled的opacity 1→0.55→1，造成整体闪动。800ms延迟回执下，未点击的示范音/新录音/自评/删除按钮也会变灰，证据 `docs/evidence/recording-click/logs/before.log`。

- `RecorderPanel.tsx`：新增仅组件内使用的RecorderAction，将短暂请求等待改为aria-disabled+点击保护；鼠标与键盘触发都由守卫阻止，command同步锁保留。未具备录音条件、录制期间等真正不可用状态继续用原生disabled。请求期间不再把整组按钮的透明度改变；没有用CSS全局覆盖disabled样式。
- 自评成功反馈复用Toast，4秒自动消失；`globals.css`只给录音区Toast增加固定定位，避免原成功Message在列表上方新增一行。其他页面Toast样式不受影响。
- 新增 `scripts/recording-controls-browser-smoke.js`；无后端、数据库、依赖或录音持久化策略改动。

验证：typecheck、lint、生产构建、23项前端单测和git diff --check通过，日志 `docs/evidence/recording-click/logs/`。专项Playwright在1440/375px、800ms真实隔离API回执延迟下，分别覆盖暂停、跳过、原生播放自动计次、自评Toast出现/消失，共8组：buttonOpacityChanged=false，disabledMutations=0，cardDrift/scrollDrift/buttonDrift=0，audioSameNode=true，extraLoads=0；额外检查等待期间DOM点击删除不弹窗、Enter触发冲突操作不提交，重复/键盘保护通过。自评不加回放次数，pageErrors=[]，见 `browser-final.log`。既有 `playback-layout-browser-smoke.js` 的回执丢失/刷新/原eventId幂等重试回归同样通过，见 `retry-regression.log`。

截图 `feedback-{1440,375}.png` 已实际查看：自评反馈浮在播放器上方，列表不重排。测试全部应用API请求仅转发已验证的隔离API8086，只使用假麦克风测试录音，未操作用户主库私人音频。原生音量滑条/菜单本身的浏览器内部交互没有替换；本次没有把其展开宽度当作页面布局位移。未实测Safari/Firefox或真实设备GPU绘制，不宣称跨浏览器全部视觉问题均已验证。

仅重启本项目Web加载改动，最终监督PID26578；主API22271/MySQL保持运行，主API健康/安全检查通过。三个测试浏览器和额外隔离API24991已关闭；原视频未改动，所有提取帧只在忽略的证据目录。未重复Java测试，未提交Git或进入下一阶段。

### 用户追加：统一弹窗和按钮视觉（2026-10-23）

沿用现有深蓝/绿色风格，统一所有 Modal（删除录音、丢弃上传缓冲、回载写作历史、内容来源及移动端助教抽屉）：标题图标 + 标题 + 轻量关闭图标、独立滚动正文、底部分隔操作区。桌面宽500px/圆角18px，手机宽度随视口收缩，正文溢出内部滚动，底部操作保持可见；无新增动画、依赖或业务接口。

共享 Button 增加 secondary/primary/danger 语义，保留原有 className 用法；常规按钮统一36px最低高度、10px圆角、600字重，弹窗操作40px高/12px间距，取消描边、确认绿色 #087f70、危险操作红色 #b43c3c，统一悬停/按下/禁用状态；播放器设置主按钮同步绿色和圆角。专用播放/时间轴控件仍沿用其交互尺寸。删除说明拆为结果与不可撤销提示，默认聚焦取消，删除请求中禁止关闭/重复提交，失败信息在弹窗内部可见。所有弹窗具有唯一标题ID、Tab/Shift+Tab首尾循环、Esc/遮罩关闭、关闭后无滚动焦点返回；修正点击弹窗内部空白也触发关闭的问题。

涉及：`apps/web/src/components/ui/Primitives.tsx`、`apps/web/src/app/globals.css`、`apps/web/src/components/exercises/{RecorderPanel,WritingEditor}.tsx`、`apps/web/src/components/lesson/LessonWorkspace.tsx`、`scripts/modal-browser-smoke.js`、本报告。未修改API/SQL/依赖。

验证：`python3 scripts/local.py exec npm run typecheck --workspace @northstar/web`、lint、生产build、单测23/23以及 `git diff --check` 通过。Playwright专项覆盖1440/375/320px删除弹窗尺寸、危险按钮颜色、取消初始焦点、Tab焦点循环和返回、Esc/取消/X/遮罩关闭、内部边缘不误关；模拟800ms删除请求验证等待态及完成关闭；写作取消保留草稿、缓冲取消保留录音、内容来源确认、375px助教抽屉通过。375×400矮屏验证正文内部滚动且底部按钮可见。pageErrors=[]。初次原生Tab循环检查失败后补显式边界约束，最终全部复测通过。

证据 `docs/evidence/modal-redesign/logs/{typecheck,lint,build,unit,browser}.log`，截图 `delete-{1440,375,320}.png`、`discard-320.png`、`writing-1440.png`、`source-1440.png`、`source-short.png`、`drawer-375.png`；已实际查看桌面删除、320px缓冲及矮屏内容来源截图。浏览器使用隔离上下文、模拟录音/写作GET数据和浏览器内缓冲，所有写请求拦截（最终5次），未回放或删除用户私人录音；因此不将本轮结果描述为真实删除入库验证。Safari/Firefox及真手机未测。

仅重启核对PID/cwd的本项目Web加载最终生产构建（监督PID30432，127.0.0.1:3100），原API/MySQL保留。诊断浏览器关闭；无Git提交、未进入下一阶段，等待本轮视觉审核。

### 用户追加：左右栏独立滚动、左栏填满可视高度（2026-10-23）

已解码并查看用户6.417秒录屏的6张关键帧：约第3秒左栏品牌顶部被带出、底缘露白。修复前 Chromium 正常滚轮未复现左栏位移，但确认窗口整体滚动：windowY 0→649、documentHeight1549、右侧mainScroll始终0（1440×900）；这表明旧版 sticky 左栏仍依赖整页滚动，不能提供左右独立滚动边界。不将录屏中的边缘回弹成因描述为 Chromium 完整实测复现。

最小修改：`apps/web/src/app/globals.css` 将html/body限制为可视区域、外壳100dvh且网格行允许收缩；左栏高度100%、内部overflow-y:auto、子项不压缩；右侧main-shell独立overflow-y:auto并预留稳定滚动条。两侧overscroll-behavior-y:contain阻断边界滚动传播。窄屏延续顶部导航，内容使用剩余高度独立滚动；顶部导航上限40dvh，极矮窗口可内部滚动。底部播放器仍固定于视口。`apps/web/src/components/shell/AppShell.tsx` 仅增加右侧ref及pathname改变后回到顶部，课内Tab/query改变不重置滚动。

新增 `scripts/independent-scroll-browser-smoke.js`：1440×900、1280×600、979×400、375×900、375×500五组均通过真实滚轮验证右侧mainScroll增加600、windowScroll=0、左栏坐标/滚动不变，滚到底继续滚动不传播。桌面左栏高度等于视口；左侧滚轮不改变右侧滚动，矮屏左栏内容可内部滚动；播放器底部始终等于视口高度，无横向溢出。额外验证课内Tab保留右侧位置、跨页导航归零。pageErrors=[]，全部写请求拦截5次，未写学习数据或访问私人录音。`scripts/modal-browser-smoke.js` 回归通过全部弹窗、焦点循环、关闭方式、移动抽屉、矮屏、模拟删除加载态（其写请求同样拦截）。

typecheck、lint、生产build、git diff --check通过；未重复无关后端/业务单测。证据 `docs/evidence/independent-scroll/logs/{video,before,typecheck,lint,build,browser,modal-regression}.log`、`frames/frame-00..05.png`、`scroll-{width}-{height}.png`；已查看桌面、979×400及375×500最终截图。原生Safari/Firefox、真机触摸板回弹未实测，当前结论为Chromium滚动边界与布局行为通过。

仅重启核对PID/cwd的本项目Web（监督PID31882，127.0.0.1:3100）加载构建，API/MySQL保持运行；隔离诊断浏览器关闭。无Git提交、未进入下一阶段，等待审核。

### 用户追加：收藏按钮保持圆角正方形（2026-10-23）

定位到共享.button的min-height:36px覆盖收藏按钮原height:32px，使32px宽按钮被撑成36px高。仅修改 `apps/web/src/app/globals.css` 的 `.vocabulary-favorite`，明确宽高及min/max均32px、aspect-ratio:1、圆角10px，保持各页面宽度及收藏状态下为固定正方形；不更改收藏逻辑。

生产build（含TypeScript）和git diff --check通过。隔离Chromium覆盖1440/1280/979/375/320px，全部词卡收藏按钮实际尺寸32×32px、圆角10px；模拟收藏切换后尺寸不变，pageErrors=[]。全部5次收藏写请求模拟，未修改用户收藏数据。证据 `docs/evidence/favorite-square/logs/{build,browser}.log`、`square-{1440,320}.png`，已查看320px截图。临时验证脚本 `.local/favorite-square.js`；本次纯CSS改动未重复业务单测或后端检查。

仅重启本项目Web（监督PID33704）加载生产构建，API/MySQL保持原状，诊断浏览器关闭。无Git提交，未进入下一阶段；Safari/Firefox未测。

### 用户追加：悬停覆盖选中背景、全页面同类检查（2026-10-23）

修复前浏览器实际复现：写作Tab选中句号03背景 rgb(8,127,112) 在hover变为 rgb(240,250,246)，白色文字保持不变；首页深色横幅次按钮从透明背景变为同一浅色背景，原浅色文字保持不变。根因为通用 `.button:hover:not(:disabled)` 的高选择器优先级覆盖了 `.sentence-picker button[aria-pressed=true]` 及 `.hero-secondary` 组件基色。

仅修改 `apps/web/src/app/globals.css`：通用hover/active使用`:where`降低优先级，让组件基色/持久选中态优先生效；保留普通按钮的浅绿悬停反馈，并为深色横幅次按钮明确半透明白hover/active背景与白字，避免变成浅底浅字。未堆叠important、未逐个复制五个学习Tab样式，未更改业务逻辑/接口/依赖。

新增 `scripts/hover-state-browser-smoke.js`，真实鼠标悬停/按下验证1440/375px两组共22个页面/Tab组合：学习首页、课程、复习、报告、设置及课文/听写/精读/口语/写作/测验。覆盖选中Tab、选中句子/句号、可见且启用的标准操作按钮、播放按钮、已展开播放器设置、已收藏按钮、删除弹窗危险及取消按钮；检查不透明按钮文字对比不少于4.5，选中背景及文字在hover/active保持（播放器按下允许已有深绿反馈）。全部通过，pageErrors=[]，写入12次均拦截或模拟，写作/录音使用固定GET测试数据，未改变用户草稿、学习数据、私人音频或收藏。模拟业务回执只用于交互样式验证，不代表业务持久化测试。

lint、生产build（含TypeScript）、git diff --check通过。证据 `docs/evidence/hover-states/logs/{before,after,lint,build,browser}.log`、`writing-{1440,375}.png`；已查看1440px选中03悬停截图。初次回归脚本把播放器正常的按下深绿反馈误判为选中色变化，另一次按下测试在弹窗外松鼠标误触遮罩；校正预期并在目标内部释放且阻止实际点击后完成全部复测，无需改动播放器/弹窗逻辑。本轮纯CSS未重复无关业务单测/后端检查；未覆盖Safari/Firefox或不存在的Phase07/08功能。

本项目Web已重启加载最终构建（监督PID36438），API/MySQL未改，诊断浏览器关闭。无Git提交、未进入下一阶段，等待审核。

### 用户授权按阶段提交 GitHub（2026-10-24）

用户明确要求分阶段提交当前代码。基线为Phase04提交a357e20；远程origin/main在开始时与本地基线一致。分成两个提交：Phase05精读词汇、阅读、V005及相邻听写修复（82c5b55）；Phase06录音、写作、V006及本阶段追加的回放/反馈、北京时间、弹窗、滚动、收藏按钮与悬停修复。通过暂存区分离共享文件，不回退工作目录，不改写已有远程历史。同步README当前阶段/功能及设计偏差中的自动回放观察说明；旧报告的“未提交”保留为当时状态记录。

Phase05独立快照位于被忽略的 `.local/git-closeout-20261024/phase05/`：typecheck、lint、19项前端单测、Next生产build及Java21 Maven package -DskipTests全部通过；其中后端仅编译与测试编译，不描述为数据库集成测试通过。只修正快照CSS末尾空行后纳入同一Phase05提交。Phase06最终工作区本轮typecheck、23项前端单测通过；当前CSS的lint/build及跨页Playwright结果见前节（无后续代码改动），本轮不重复描述为重跑浏览器。后端Maven test在沙箱内因Mockito自附加失败，允许本机附加后重跑BUILD SUCCESS：17项、0失败、0错误、6项数据库条件测试跳过，即11项实际执行通过；本轮没有重跑真实MySQL套件，既有集成验收证据仍见前文。

阶段拆分逐文件比对：除README、设计说明与阶段归档记录的定向更新外，代码工作文件内容保持不变。56个候选文件未发现本地.env密码、令牌、私钥、机器绝对路径或大型二进制（最大文件约65KB）；阶段暂存blob再次检查大小/秘密/空白，并确认.env、.local、docs/evidence和课程音频仍忽略。未提交私人录音、数据库、原型媒体、日志、截图和构建产物。详细归档验证日志与路径清单留在 `.local/git-closeout-20261024/`，不上传。

本轮仅Git归档及定向文档修订，不迁移/重建数据库、不重启服务、不进入Phase07。推送操作采用普通fast-forward，推送后核对本地与origin/main引用和工作区状态。

### 用户追加：听写连续切句仍闪烁（2026-10-24）

已查看用户10秒新录屏并以8fps精确提取80帧，重点查看切句前后帧018/019/020；录屏主要为精听听写01→10切换。第020帧新目标出现时，开始/恢复、暂停、跳过整组变灰，随后恢复。修复前600ms延迟实际草稿/状态读取，requestAnimationFrame测得操作按钮opacity 1→0.55且native disabled false→true，输入框也被短暂disabled；不是布局位移或悬停覆盖。此前修复覆盖了回放/悬停等路径，未覆盖该独立加载路径。

本轮修改：
- `DictationEditor.tsx` 新增局部DictationAction，用aria-disabled和点击守卫保护短暂加载/请求；input改为只读+aria-busy，读取完成前拒绝修改，不再改变原生禁用外观。保留每句独立key，避免晚到结果/保存串句；不通过保留旧句草稿伪装新目标完成加载。
- 操作区在请求时继续保留，不再被待确认Message替换；只有失败/恢复待确认事件时出现重试入口。空答案、尚未成功播放音频及暴露状态异常等真正不可提交条件仍native disabled。加入同步actionLock，防止React更新前重复提交。
- `RecorderPanel.tsx` 同步修正新目标读取期间“开始新录音”的临时disabled变灰，移入既有waiting守卫；录制期间/有上传缓冲的真实不可用状态不变。
- 新增 `scripts/dictation-switch-browser-smoke.js`；已有dictation-browser与dictation-skip测试改为等待textarea非readOnly/按钮非aria-disabled，避免把视觉启用当作业务已就绪。

验证：typecheck、lint、23项前端单测、生产build与git diff --check通过，日志 `docs/evidence/switch-flicker/logs/`。专项浏览器在1440/375px，草稿/状态读取延迟600ms、提交延迟650ms，覆盖20次听写切句、2次暂停请求、4次口语切句，共26组逐帧检查：操作按钮opacity始终1、无短暂native disabled、输入框白底保持、工具栏不断开、成功请求不闪重试块、外壳/播放器坐标稳定；等待中DOM点击/真实Enter均不提交，失败刷新后重试保留原eventId，快速2→3→4→1的晚回执不覆盖最终目标，切句未产生草稿写入，pageErrors=[]。这些写请求均模拟，不能当作真实MySQL回执测试。

另外在核验测试库标记的隔离API8086执行真实 `dictation-skip-browser-smoke.js`：跳过后只前进一句、暂停旧音频、保留原稿，失败/丢回执/刷新复用原事件，不确定回执不前进，晚回执不抢手工选句、最后一句不回绕、练习次数与复习来源不增加，全部通过。精读 `reading-feedback-browser-smoke.js` 同样通过1440/375px外观/几何/重复保护/原事件重试回归，其写请求模拟。主库学习记录和私人音频未操作，API/数据库业务实现未因本轮修改。

证据：`logs/{video,before,typecheck,lint,unit,build,browser-final,skip-regression,reading-regression}.log`、`frames/frame-000..079.png`、`contact-{0,40}.jpg`、`stable-{1440,375}.png`；已查看关键帧和最终两种尺寸截图。初次探针路径漏掉/api/v1导致延迟未生效，修正后才记复现；初次等待态测试使用Playwright click会自动等aria-disabled解除，改用DOM点击验证守卫，保留真实Enter检查，最终通过。

仅重启本项目Web加载生产构建（本轮监督PID86242）；额外测试API与两次隔离浏览器在验证后关闭，原主API/MySQL保留。本轮开始Git工作区干净；执行中发现另有测验/复习/V007相关并行改动，未改写/暂存/提交这些文件，当前结论不覆盖该并行功能。本轮未提交或推送Git。Safari/Firefox、真设备GPU绘制未实测，不宣称所有平台/所有不同加载路径的闪烁已全部消除。

### 用户明确圈出：次数标签与草稿状态闪烁（2026-10-24）

用户澄清闪烁区域为练习状态/次数标签及草稿常规状态文字，上轮按钮变灰验证没有对准这两处。本次按要求只显示“累计N次真实练习”，移除草稿读取/为空/保存中的常规状态行；真实同步错误、次数读取失败、草稿冲突继续明确显示。

`DictationEditor.tsx` 拆分稳定的整课次数/播放区与按句隔离的内部草稿编辑器；`LessonWorkspace.tsx` 只将外层听写组件key改为版本ID，内部仍使用draftKey保证草稿与异步回执目标隔离。进入听写时读取一次整课次数，切句从内存取对应数字；标签DOM不重建、仅数字文本变化，不再重复读次数或切换“练习状态待确认”等文案。暂停/跳过不重取次数，正式作答回执后重新读取；读取失败不虚构0，保留未知值/重试。数字等宽并预留两位宽度，避免0/12等数字长度影响标签。删除不再显示的草稿status状态及其更新，不用隐藏DOM保留无意义状态刷新。已有听写脚本改为等待实际保存响应/数字，保持暂停跳过的服务端行为验证。

验证：typecheck、lint、生产build通过；初次lint将async回调识别为effect同步状态更新，改用明确的请求then/catch回调后复测通过，无禁用规则。新增 `scripts/dictation-count-browser-smoke.js` 在1440/375px各切10句，均只有1次整课次数GET，标签同一节点、只显示有效数字且草稿状态行始终不存在；模拟正式提交后次数更新、暂停不读取，失败显示未知值/重试恢复，pageErrors=[]。所有写请求模拟，未写主库。既有 `dictation-switch-browser-smoke.js` 的26组逐帧、等待保护、失败刷新原UUID重试和快速切句草稿隔离回归同样通过。本轮未重复真实MySQL或无关后端测试。

证据 `docs/evidence/dictation-count/logs/{typecheck,lint,build,browser,switch-regression}.log`、`count-{1440,375}.png`，已查看桌面最终截图。仅更新Web加载生产构建（监督PID92537），API/MySQL保留，隔离验证浏览器关闭。测验/复习等并行改动保留，本轮未提交Git；Safari/Firefox未测。

### 用户确认：按学习场景显示内容控制（2026-10-24）

用户要求落实前轮分析：听写页强制盲听保护，共用的译文/盲听按钮不改变当前显示，却会修改其他Tab的共享偏好，属于不适用操作。本轮仅调整 `LessonWorkspace.tsx` 的显示条件：课文显示英文/译文控制（盲听时只提供恢复英文）；听写不显示二者，原答案保护不变；精读只在英文可见时显示源句译文控制，英文关闭时沿用页内“显示英文并开始精读”的恢复入口；跟读只显示能控制目标原文的盲听开关；写作/测验不显示这两个不控制题目/编辑内容的按钮。无可用控制时整个工具栏不渲染，不保留空容器。不强行改写用户显隐偏好，不改变答案暴露记录或测验业务。

typecheck、lint、生产build及定向git diff --check通过。新增 `scripts/context-controls-browser-smoke.js` 在1440/375px覆盖6Tab共12组按钮清单；实际点击验证课文英文/译文显隐、盲听后恢复英文仍保留原译文偏好、听写往返不修改偏好且右栏继续隐藏答案、精读源句译文显隐与英文恢复入口、跟读目标原文隐藏/恢复，全部通过；pageErrors=[]，无横向溢出。脚本拦截全部写接口并模拟录音/写作/测验GET，最终未发起写请求，未改用户学习数据。初次脚本在React URL状态尚未更新时即断言，改为等待实际DOM结果后通过。

证据 `docs/evidence/context-controls/logs/{typecheck,lint,build,browser}.log`、`dictation-{1440,375}.png`，已查看桌面最终截图。Web已更新（本轮监督PID72071），API/MySQL及既有Phase07改动保留；验证浏览器关闭。本轮未提交Git，纯条件渲染未重复业务单测或后端检查；Safari/Firefox未实测。
