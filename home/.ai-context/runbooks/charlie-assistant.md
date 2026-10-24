# 知伴独立私人助理

实证日期：2026-10-24。用户要求保留19976，另建Muse式私人助理、公网网页、私人手机App及跨AI记忆。

## 当前入口与隔离

- HTTPS： https://charlie1990.duckdns.org:19984/
- `charlie-assistant-https.service`：专用Caddy，19984 -> loopback18446。
- `charlie-assistant.service`：FastAPI、SQLite持久队列、单任务执行器、确定性定时维护。
- 源码：`~/workspace/charlie-assistant/`；git仓库只存源码，不存运行状态和密钥。
- 状态：`~/.local/share/charlie-assistant/`，0700；数据库assistant.db，0600。
- Hermes home：状态目录下`hermes/`；模型凭据仅在该目录`.env`，0600。
- 工作与交付：状态目录下`workspace/<job-id>/`；每任务独立文件夹，只发布本任务交付文件。
- 私人访问口令：状态目录`首次登录.txt`，0600。不得写入网页源码、APK、日志、记忆或公开文档。
- 手机PKR110已安装`com.charlie.assistant/.MainActivity`，最新版1.0.1 / 2026102402；独立WebView客户端，不包含供应商密钥。配对经一次性token在页面内POST，已消费；不得导出Cookie。
- iPhone提供Safari“添加到主屏幕”的网页App，本次没有构建或安装原生iOS包。
- 应用状态隔离，不是独立OS/VM沙箱；任务本机执行，不能声称等同Meta全部能力。

## 公网链路

DuckDNS:19984 -> ZXHN F650 `CharlieAssistant19984` TCP19984 -> OpenWrt WAN192.168.1.4:19984 -> UCI `firewall.charlie_assistant` -> Fedora192.168.5.144:19984。
FedoraWorkstation zone已运行时及永久放行19984/tcp。
专用配置`~/.config/caddy/assistant.Caddyfile`；复用现有可信域名证书，未改19976/8787/8648映射。
acme.sh域名已有DNS-01配置；已补`--install-cert`到Caddy证书路径及`try-restart charlie-assistant-https.service`续期reload hook，现有每日acme cron timer负责检查。私钥、DuckDNS token及其他域名DNS密钥均不记录在此。

## 对话与后台任务

- chat：Step 3.7 Flash，轻量上下文；auto由同一次响应决定直接回复或后台任务，task明确转执行器。
- 执行：独立子进程runner.py，Step 5 Preview，35次工具循环/30min上限，checkpoint、持久任务与阶段结果。
- 关闭页面不中止任务；取消发送进程组TERM。重启后running/waiting标记interrupted，需用户点继续，避免重放外部动作。
- 进度、clarify回复、结果、文件和用量回原对话；同request_key幂等。
- 背景提醒不调用LLM。ntfy helper用位置参数`ntfy-send actions <title> <message>`，不是`--topic/--title`；提醒发送失败不标已提醒，会再试。
- 登录为口令+HttpOnly/Secure/SameSite Cookie；私有API/文件未登录401；来源校验/客户端header限制CSRF。没有把浏览器调试口暴露到公网。

## 记忆来源与范围

`memory.py`显式注册根目录、只读读取、过滤凭据行、分段检索；每10min确定性刷新。原始文件不被新助理覆盖。

- Hermes主记忆及所有有身份配置的profiles；空profile按空显示。
- `~/.shared-agent/memory`、共享SKILL.md、`~/.hermes/a2a/knowledge`、系统runbooks。
- Claude的既有memory目录；Codex共享经验及各账号`memories_1.sqlite`只读stage1_outputs（本次原生表为空）；OpenHands的真实路径是`~/.openhands/memory.md`软链；OpenCode规则入口及共享事实引擎。
- `~/.local/share/memory-engine/memory.db`，只读facts表；本次表有4698条，过滤敏感键后索引。不要为读取此SQLite启动或重启整套Letta/容器。
- Letta :8283本次连接失败；不声称已接入其不可读取数据。未授权/未导出的远程云AI隐式记忆不可凭空获得。
- 只索引可读记忆与沉淀经验，不把完整工具日志和全部账户数据库灌进提示词。召回去重，保留来源，历史推测需核验。
- 注意来源ID：主记忆用`hermes-main`；跳过profiles/default空残留目录；所有ID必须唯一。此前发现同名default覆盖主源状态，已修并加回归测试。

## Muse已验证路径

- 已登录专用Chromium，CDP仅127.0.0.1:9231。读取前确认登录与界面；不读Cookie或auth存储。
- 设置 -> 数据控制 -> 下载你的智能体数据 -> 确认下载。
- 官方zip含manifest.json turns和工作区文件；仅选择性读取，不解压任意路径，不把原始归档放公网或全量索引。
- 本次得到117条消息的官方导出，并请求Muse自述可访问长期记忆；已导入两类资料，标为归纳/自述，不能当完整内部记忆或已验证事实。
- 默认后续流程：网页“我记得的事” -> “同步 / 导入” -> “从Muse同步”；对应`python3 ~/workspace/charlie-assistant/muse_sync.py`。
- 脚本clean_turns过滤纯密码回复/敏感行；按清洗后的turns哈希增量，没变化不再次调用整理模型。已实测第二次状态“资料没有变化，已确认最新（117条消息）”。
- 浏览器退出、登录失效或Muse正在执行任务时明确显示未完成，不自动建号、不更改账号、不中断Muse现有任务。
- 私有原始归档：状态目录`muse-private-export/`；发布用摘要：`imports/muse/`；状态`muse-sync-status.json`。

## 构建、安装与核查

```sh
cd ~/workspace/charlie-assistant
python3 -m unittest discover -s tests -q
python3 -m py_compile *.py
node --check static/app.js
bash -n build-android.sh install-android.sh
bash build-android.sh
bash install-android.sh <当前可用serial>
```

Java原生壳没有外部依赖；默认用已安装Android SDK的aapt2/javac/d8/zipalign/apksigner构建。Gradle离线曾缺kotlin-reflect，不要反复重试缓存或清整个Gradle库。
APK导出默认Documents/私人助理体系-2026-10-24，版本文件有覆盖保护；新代码发布需同步提高版本。
ColorOS首次安装会显示底部“安装”，必须按真实截图/控件坐标确认；本机截图1080x2376，不能照缩放后的显示坐标点击。更新安装本次pm install -r成功，保留登录数据。
WebView文件保存走认证同源下载bridge+MediaStore，不能依赖CDP下可能不触发的DownloadListener；已手机实测42字节验收文件，SHA256与服务器一致。

## 验证证据

- 8个回归测试通过：鉴权、CSRF、幂等/取消、来源ID、秘密过滤、Muse纯密码过滤、文件目录越界、提醒持久化。
- 桌面1440与手机390布局无横向溢出/JS错误；安卓App已登录实际聊天，轻量一轮317总tokens（其中192 cached input），不能推广为固定成本。
- 后台实际创建并回读`知伴验收.md`；手机保存文件SHA256：4949a59ec2623153b378ede012abd971fd0f210a7debcf8ab6731cdc47156e83。
- 手机蜂窝源100.96.77.60 -> 公网125.110.234.23:19984，HTTP200，ssl_verify_result=0；这次不是Fedora loopback替代验收。
- 服务重启后任务completed与对话保留；原19976与8787根路径HTTP200。
- 证据目录：状态目录`evidence/`。注意证据图可能含用户文字，只本机保存。
- CodeGraph list和限定本仓库update均遇既有Kuzu shadow缺失，未做home-wide refresh或重装；本次以直接源码检查和上述验证为准。

## 常规操作与回退

```sh
systemctl --user status charlie-assistant.service charlie-assistant-https.service --no-pager
curl --noproxy '*' http://127.0.0.1:18446/api/health
systemctl --user restart charlie-assistant.service
```

只有后端代码改动需测试后重启charlie-assistant；静态网页刷新即可。不要重启原Hermes。
停用新体系：disable --now这两个新service；如需撤公网再删除专属OpenWrt redirect和光猫19984映射，仅针对新条目。保留SQLite与工作目录，不能清空手机App数据或删除原记忆。


## Muse自动导出与手机/网页同步（2026-10-24续）

- 用户明确要求：电脑或root手机的Muse资料自动导出到知伴，手机App与19984网页共用最新资料。
- 默认调度已改为`charlie-assistant-muse-sync.timer`：开机5min后检查，随后每次结束约1h再检查，最多2min随机延迟。
- `charlie-assistant-muse-sync.service`调用既有muse_sync.py；依赖已登录的meta-account-browser。已补磁盘上的同名浏览器unit，当前transient运行实例保持不动，重启后可由同步服务按需启动永久unit。
- 导出在同一已登录浏览器context的新后台页进行，不复制Cookie、不改用户当前标签；结束只关闭自己的标签。网络/界面异常有界重试一次；正在执行工作时跳过；登录失效时保留旧记忆并显示失败。
- CLI、网页手动同步和timer共用`muse-sync.lock`的flock，防止并发覆盖。状态JSON原子替换；失败不清除last_success；无变化不调用整理模型。
- `muse-auto-sync.json`给前端显示每小时自动检查；状态API明确shared_data=true。前台2秒刷新，手机App与网页直接访问同一个19984后端/数据库，不另存两套聊天或记忆。
- 自动service本次完成：Result=success、ExecMainStatus=0，官方导出118条消息，已更新摘要；11项回归测试通过。
- 双端实证：网页新建的临时对话立即能被手机App读取；两个客户端JS SHA256一致、shared backend配置一致、自动同步enabled一致、Muse updated一致。临时对话验证后已清理。证据`~/.local/share/charlie-assistant/evidence/cloud-sync-verification.json`。

### root手机读取的真实范围

- 通过adb-record与su确认PKR110 root可用。仅检查Muse包com.facebook.aura的databases/files/spaces，没有读取认证prefs或导出登录态。
- 本地`hatch_offline_conversation.db`连WAL做私有临时副本；SQLite quick_check=ok。offline_messages122行、offline_threads5行，122个json BLOB均非可直接解析的JSON；存在offline_keys/wrapped_key表。
- 官方已缓存APK中的DEX确认HatchOfflineConversationCipher及Keystore unusable/offline cache disabled相关符号，支持本地缓存被加密的判断。没有提取wrapped key或伪造解密成功。
- 这是离线聊天缓存，不是已确认完整长期记忆。手机缓存与网页官方导出条数不同，不能直接推断数据丢失或声称全部一致。
- 临时DB/WAL/SHM本机副本和手机staging已清理，只保留不含消息/密钥的检查报告`muse-phone-storage-status.json`。不把完整App数据库写入日志或知识库。
- 自动链路为Muse官方可导出资料→知伴服务器→手机/网页，不自动反向写回Muse。root不能直接读取云端未公开的内部记忆。

### 检查和暂停

```sh
systemctl --user list-timers charlie-assistant-muse-sync.timer --no-pager
systemctl --user show charlie-assistant-muse-sync.service -p Result -p ExecMainStatus
# 立即检查（无需重启主助理）
systemctl --user start charlie-assistant-muse-sync.service
# 仅暂停自动导出，知伴仍可正常使用
systemctl --user disable --now charlie-assistant-muse-sync.timer
```

主机是用户电脑充当的私人服务器，必须在线才能访问App/19984；没有将服务迁到第三方云。原19976保持独立。

## 五端共同学习层（2026-10-24）

不需要重新训练模型。使用共同档案、带来源的经验记录和任务前检索。五个入口实际是多个模型系统；账号模型内部记忆并非同一数据库。

| 入口 | 当前路径 | 更新方式和边界 |
|---|---|---|
| 知伴 App、19984 网页 | 同一个私人服务器和数据库 | 前台约2秒刷新；服务端每次回答读取共同档案与相关经验 |
| Codex | 各现有账号 AGENTS.md 指向共同档案 | 非简单任务前读取；偏好与结果写 agent-preference-record 后约5秒采集 |
| Hermes 19976 与各 profiles | 保留原配置、记忆和服务；SOUL增加共享入口；hermes-memory-brief包含共同摘要 | 已保存Markdown记忆约5秒采集；新任务召回可见；旧会话不会自动重写既有系统上下文 |
| Muse | 官方“导入记忆”和“下载你的智能体数据” | 两个约5分钟检查任务；反向导入不超过2000字的精选档案，无变化不重复提交；不是实时全量API |


- 实现：`~/workspace/charlie-assistant/learning.py`（5秒快照、来源与去重、短档案），`muse_push.py`（官方导入、哈希去重、共用Muse锁）。
- 服务：`charlie-assistant-learning.service`；Muse双向两个timer间隔5min。旧小时说明由本节取代；历史索引仍10min。
- 消费：知伴每次回答读learning.brief，任务结束写验证经验；Codex各账号AGENTS入口；Hermes SOUL及实际hermes-memory-brief载入。旧会话需主动召回。
- Muse外发只允许精选档案与记录器的正向明确偏好，排除Muse来源及完成自述；不宣称全部内部隐式记忆实时共享。2k字上限；无变化不提交。
- 出站接受与模型召回分开；当前聊天端口/名称召回已通过，但隔离新会话持久召回未证实。
- 入站最终路径：确定性清洗官方导出，按用户/助手角色标来源，分片每100000字符；不调用额外模型，既有摘要保留为历史参考。内容哈希无变化不重写；唯一文件名原始zip保留。原模型整理连续返回空内容，已从同步关键路径移除；147条导入通过。
- 验证：16测试、知伴真实模型召回、手机公网API、Muse当前聊天召回；证据在state/evidence/{phone-learning-check,muse-recall-check,assistant-learning-recall}.json。
- 文档：`/var/mnt/ai/xdg/文档/私人助理体系-2026-10-24/五端记忆同步说明.md`。

## Matrix消息管理（2026-10-24）

- `matrix_manager.py`使用现有charlie账号，仅在服务端读取凭据；不复制到浏览器/APK/Muse或共享记忆。API `/api/matrix/rooms`、`messages`、`drafts`、`drafts/{id}/send`沿用私人登录和CSRF约束。
- 账号API已验证693个joined_rooms。目录：先取得空房间sync游标，再在只读Synapse库按已授权房间加载元数据及最近事件；EXPLAIN验证events_room_stream索引，避免全量初次sync超时。普通增量sync由服务内独立线程轮询，约15-25秒。历史未读初值未核验，不自动发read receipt。
- UI：网页/App的“消息”；查阅、按房间检索、总结待办、保存本地草稿、完整正文核对后发送。固定zhiban-draftID事务支持超时幂等重试；进程重启时sending改为uncertain。加密房间不明文发信。
- 20测试通过；公网真实UI展示100房间、25消息、创建草稿成功；样例草稿已清理，未发送外部测试信。实际模型回复693房间。证据：state/evidence/{matrix-read-check,matrix-assistant-recall,matrix-web-ui-check}.json。
- 手机现有WiFi/FRP入口后续离线，USBunauthorized；手机新界面尚未验收。此前无线ADB文件往返SHA一致不替代手机UI证据。
- Muse当前可用连接器目录没有找到Matrix/自定义接入口，直连未完成；不要声称记忆快照赋予收发能力。Meta菜单本身也是dialog，须点其中“设置”按钮再访问设置分类。
- CSP测试：Playwright wait_for_function用()=>predicate，不为自动化加入unsafe-eval。
- 使用说明：`/var/mnt/ai/xdg/文档/私人助理体系-2026-10-24/WiFi传输与Matrix消息助理.md`。
