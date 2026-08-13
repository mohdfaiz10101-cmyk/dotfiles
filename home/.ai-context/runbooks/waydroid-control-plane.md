# Waydroid Control Plane

最后更新：2026-08-01 17:08 CST

目标：把 Waydroid 当成“可被 AI/CLI 调度的 Android 节点”，而不是长期视频投屏对象。

## 当前设计

- 人工/脚本入口：`~/.local/bin/waydroidctl`
- AI/MCP 入口：`~/.local/bin/waydroid-mcp`
- Hermes MCP 名称：`waydroid`
- Telegram 快速入口：`/waydroid ...`，由 `opencode-telegram-gateway.service` 调用 `waydroidctl --json`
- 可视化兜底入口：`ws-scrcpy-web.service` / `:18082`，只用于人工看屏或低频操作，不是最终主控制面
- 手机低流量 Web/API 入口：`waydroid-control-web.service` / `:18083`，Workbench `/go/waydroid`
  指向这里；`:18082` 只保留为视频兜底 `/go/waydroid-video`
- 手机可视化推荐入口：先运行 `~/.local/bin/waydroid-visible-ensure`，再用手机
  Moonlight 连接 Sunshine 看 Fedora 桌面上的 Waydroid 窗口。
- 手机 Moonlight 专用入口：Sunshine apps 里有 `Waydroid 手机`，调用
  `~/.local/bin/moonlight-launch waydroid` -> `~/.local/bin/moonlight-waydroid-only`。
  该入口会切手机分辨率、确保 Waydroid session、尝试显示 Waydroid、再把 Waydroid
  移到专用 workspace 8 并全屏。注意 Sunshine/Linux 不是稳定 per-window capture；
  这里的可靠模型是“专用 workspace/专用显示器只放 Waydroid”，不是直接抓单窗口。
- 默认策略：先用 `status/focus/ui-dump/input`，只有必要时才回退到视频镜像

## 核心原则

- 低流量优先：`UI dump / dumpsys / app launch / input` > 截图 > 视频
- 主控制面在 Fedora/Hermes，不把真实手机算力浪费在持续推理或持续投屏
- 不依赖单一路径：Waydroid shell、Waydroid app、必要时 ADB/scrcpy 都是备用层
- headless 持久化优先用 `tmux` 启 `waydroid session start`，避免 session 很快自动停掉

## 常用命令

```bash
waydroidctl --json status
waydroidctl --json ensure-session
waydroidctl --json app-list
waydroidctl --json package-list
waydroidctl --json current-focus
waydroidctl --json ui-dump
waydroidctl --json launch com.android.settings
waydroidctl --json stop-app com.android.settings
waydroidctl --json tap 540 1200
waydroidctl --json text "hello world"
waydroidctl --json key HOME
waydroidctl --json shell -- sh -lc 'getprop ro.build.version.release'
waydroid-visible-ensure
```

手机/浏览器低流量入口：

```text
http://127.0.0.1:18083/
http://192.168.123.71:18083/
http://100.87.171.39:18083/
http://charlie1990.duckdns.org:19888/go/waydroid?device=w19900422
```

`waydroid-control-web.service` API：

```text
GET  /api/status
GET  /api/ensure-session
GET  /api/current-focus
GET  /api/ui-dump
GET  /api/snapshot
GET  /api/app-list
GET  /api/package-list
GET  /api/key/HOME
GET  /api/launch/<package>
POST /api/text  {"text":"..."}
POST /api/tap   {"x":540,"y":1200}
```

Telegram 同等入口：

```text
/waydroid status
/waydroid ensure
/waydroid apps
/waydroid focus
/waydroid launch com.android.settings
/waydroid key HOME
/waydroid tap 540 1200
/waydroid shell getprop ro.build.version.release
```

## MCP 能力

`waydroid-mcp` 暴露：

- `waydroid_status`
- `waydroid_ensure_session`
- `waydroid_stop_session`
- `waydroid_list_apps`
- `waydroid_list_packages`
- `waydroid_launch_app`
- `waydroid_stop_app`
- `waydroid_current_focus`
- `waydroid_ui_dump`
- `waydroid_input_tap`
- `waydroid_input_swipe`
- `waydroid_input_text`
- `waydroid_keyevent`
- `waydroid_shell`
- `waydroid_snapshot`

## 推荐 agent 工作流

1. `waydroid_ensure_session`
2. `waydroid_snapshot`
3. 如果已知包名：`waydroid_launch_app`
4. 读 `waydroid_ui_dump`
5. 再决定 `tap/text/key/swipe`
6. 需要诊断时才用 `waydroid_shell`

## Telegram 工作流

- 网关服务：`opencode-telegram-gateway.service`
- 健康检查：`curl --noproxy '*' -fsS http://127.0.0.1:9811/health`
- Telegram `/waydroid shell ...` 只给 owner 使用，命令通过 `execFile` 调 `~/.local/bin/waydroidctl --json`，不要改成裸 shell 拼接。
- 适合手机端快速操作：启动 app、按键、tap、输入文本、查包名、查属性、跑短 shell。

## 已知坑

- `waydroid status` 显示 `STOPPED` 时，不要直接判断整条链不可用；先 `ensure-session`
- `waydroid --details-to-stdout shell ...` 退出时可能把 LXC 容器重新 `FROZEN`；调试
  `:18082`、ADB 或 scrcpy 前先确认/执行：
  `sudo -n lxc-unfreeze -P /var/lib/waydroid/lxc -n waydroid`。容器 frozen 会让
  ADB 显示 `offline`、`adb push` 返回 `closed`，以及 `ws-scrcpy` Connect 黑屏后关闭。
- `waydroid adb connect` 不等于容器内 adbd 一定真在监听 TCP；优先走 `waydroid shell`
- 对这个主机，ws-scrcpy-web 不是 Waydroid 自动化主路径；它更适合人工兜底可视化
- 不要把 `:18082` 当“最终版本”。最终控制面是 CLI/MCP/Telegram；`:18082` 只是人工可视化补层。
- 2026-08-01 后，Workbench 的默认 Waydroid 卡片必须走 `:18083` 控制面；
  不要把 `/go/waydroid` 改回 `:18082`。如果需要看屏，新增/使用
  `/go/waydroid-video`。
- `ws-scrcpy` web client 仍可能只兼容自己的 bundled scrcpy protocol。不要为了“4.1”单独替换 server；需要 client/server 同步升级。
- 2026-08-01 GitHub/source 核验结论：
  - 官方 `scrcpy 4.1` 已包含 VP8/VP9、encoder size constraints、`--ignore-video-encoder-constraints`
    等改进，但本机 `ws-scrcpy-web` 仍是 `3.3.4` 协议，不能只把
    `dependencies/scrcpy-server/scrcpy-server` 换成 4.1。
  - 本机官方 `scrcpy 4.1` 位于 `~/.local/bin/scrcpy`，用干净 ADB server
    `ANDROID_ADB_SERVER_PORT=5041` 直连 `192.168.240.112:5555` 可以成功 `adb push`
    并列出 encoder：`h264`、`vp8`、`vp9`。
  - 但 Waydroid 当前镜像的 display capture 仍会在 Android `media.codec`
    软编码器失败：`android.media.MediaCodec$CodecException: Error 0x80001001`，
    tombstone abort 为
    `SoftVideoEncoderOMXComponent.cpp:408 CHECK(mColorFormat == OMX_COLOR_FormatYUV420Planar || ... YUV420SemiPlanar) failed`。
    `--video-codec=vp8` 和 `--video-codec-options=color-format:int=21` 均不能修复；
    后者会在 `MediaCodec.createInputSurface()` 失败。结论：这是 Waydroid 镜像
    MediaCodec/Surface 输入限制，不是手机浏览器、端口或 `ws-scrcpy` 单独配置问题。
  - 因此当前主路径应保持 `waydroidctl`/MCP/Telegram 低流量控制；如果必须视觉化，
    优先用 Sunshine/Moonlight 看 Fedora 桌面上的 Waydroid 窗口，或做截图/周期截图/HTML 控制面。
    只有升级整套 web client 到支持 scrcpy 4.1 且验证 Waydroid 镜像编码器可用后，才替换视频入口。
- 2026-08-01 16:15 CST 复验：
  - `waydroid-visible-ensure` 已落地，会自动 `ensure-session`、`lxc-unfreeze`、
    重建 `ANDROID_ADB_SERVER_PORT=5039` 的独立 ADB server、连接 `127.0.0.1:15556`、
    `waydroid show-full-ui`，并按需启动 `sunshine.service`。
  - 验证通过：Waydroid `RUNNING`，IP `192.168.240.112`，
    ADB `127.0.0.1:15556 device`，Sunshine `active`，端口 `47984/47989/48010` 监听。
  - 官方 scrcpy 4.1 在绑定可用 ADB server 后可以 push server，但视频仍失败：
    `android.media.MediaCodec$CodecException: Error 0x80001001`。
    因此当前“手机看 Waydroid”主线是 Sunshine/Moonlight，不是 scrcpy/ws-scrcpy。
- 2026-08-01 16:40 CST Moonlight/Sunshine 修复：
  - 当前 Fedora NetBird IP 是 `100.87.171.39`，不是旧的 `100.87.238.153`。
  - `wolf.service` 会占用 GameStream RTSP `48010/tcp`，导致 Sunshine 日志报
    `Couldn't bind RTSP server to port [48010]`，Moonlight host 连接失败。
    当前已 `sudo systemctl stop wolf.service` 并 `sudo systemctl mask wolf.service`，
    让 Sunshine 作为默认手机可视化 host。若以后明确要恢复 Wolf，用
    `sudo systemctl unmask wolf.service` 后再启动，但必须先停 Sunshine 或改端口。
  - Fedora LAN zone 需要放行 Sunshine/Moonlight 端口：`47984/tcp`、
    `47989/tcp`、`47990/tcp`、`48010/tcp`、`5353/udp`、`47998-48010/udp`。
    本次补齐并持久化了此前缺失的 `47984/tcp`、`5353/udp`、
    `47998-48010/udp`。
  - 2026-08-01 17:25 CST 更新：不要把手机 Moonlight 固定到 NetBird
    `100.87.171.39`。NetBird peer `100.87.37.3` 当前是 relay 路径，
    Sunshine 可开始 session/编码，但随后报 `Initial Ping Timeout` /
    `100.87.37.3: Ping Timeout`，表现为手机端 RTSP handshake error。
  - 5G/公网/随身 Wi-Fi 路径优先用 `charlie1990.duckdns.org:47989`。
    2026-08-01 17:37 CST，手机在随身 Wi-Fi `MIFI-C3BB`
    (`wlan0 192.168.100.100/24`) 时验证：DuckDNS `47989` 返回 `200`，
    但家里 LAN `192.168.123.71:47989` 和 NetBird `100.87.171.39:47989`
    均 timeout；Moonlight 报 `error 0` 时要避免它优先走 LAN/NetBird。
    当前手机 Moonlight `fedora` 的 `local` 和 `manual` 地址均设为
    `charlie1990.duckdns.org:47989`。只有明确在家里 Wi-Fi 且需要最低延迟时，
    才临时切回 `192.168.123.71:47989`。路由器已持久化转发
    Sunshine 必要端口：`47984/tcp`、`47989/tcp`、`48010/tcp`、
    `47998-48010/udp` 到 `192.168.123.71`。不要暴露 Sunshine Web UI
    `47990/tcp` 到公网。
  - 若手机 Moonlight 已保存旧 host，检查
    `/data/data/com.limelight/databases/computers4.db` 的 `Computers.Addresses`。
    在此手机上普通 `su -c` 可能因 namespace/策略无法写 `/data/data`；使用
    `su -mm -c` 才能访问/替换。保留 `ServerCert` 和 `UUID`，只修改
    `Addresses`，并恢复 `u0_a537:u0_a537`、`0660` 权限。
  - 2026-08-01 17:42 CST 更新：若 Moonlight 显示 `fedora` 离线，先查手机侧
    `http://charlie1990.duckdns.org:47989/serverinfo`。本次 Sunshine 曾返回
    `state=SUNSHINE_SERVER_BUSY` / `currentgame != 0`，重启
    `sunshine.service` 后恢复为 `SUNSHINE_SERVER_FREE` / `currentgame=0`。
    然后强停/重开 `com.limelight`，并把旧 app 列表缓存
    `/data/data/com.limelight/cache/applist/1379115E-D133-0E2A-499E-6E2D8CD9ECCF`
    移走。验证标准：手机侧 serverinfo `HTTP 200`，Moonlight 前台 activity 从
    `.PcView` 进入 `.AppView`，表示 host 已在线且 app list 已打开。
  - 2026-08-01 17:55 CST 更新：PKR110 上不要用无界 `dumpsys activity` 或
    `dumpsys window` 作为 Moonlight 前台状态主探针；它可能枚举大量 vendor
    service 并卡住或刷 `FAILED_TRANSACTION`。优先用手机侧 `serverinfo`、
    `pidof com.limelight`、必要时截图/轻量窗口字段，并给 dumpsys 类命令套
    `timeout`。
- 2026-08-01 17:12 CST Moonlight `Waydroid 手机` 专用入口状态：
  - 已修正 `~/.local/bin/moonlight-waydroid-only`，不再硬编码旧
    `/run/user/1000/sway-ipc.*.sock`；启动时必须找到并连通 active Sway IPC。
  - 已修正 `app_id` 匹配：当前 Waydroid 窗口实际是 `app_id: "Waydroid"`，
    不能只用小写 `waydroid`。
  - 已修正 Waydroid floating 窗口检测：当前 Waydroid 可能在 Sway 树里是
    `type: "floating_con"`，不能只匹配 `type: "con"`，否则专用入口会误报
    `window-not-found`。
  - 已修正 `~/.local/bin/moonlight-display-mode`，同样必须验证 Sway IPC 可用。
  - Codex 沙箱内直接跑 `swaymsg` 可能因 namespace/IPC 限制返回
    `Unable to connect`；修桌面/Moonlight 时要用宿主权限验证，不要把沙箱内
    IPC 失败等同于真实 Sway 失败。
  - 2026-08-01 17:11 验证通过：`~/.local/bin/moonlight-waydroid-only`
    返回成功；Sway `current_workspace` 为 `8`；Waydroid 位于 workspace 8，
    `visible: true`、`focused: true`、`fullscreen_mode: 1`；`sunshine.service`
    和 `sway-workspace-controller.service` 均为 `active`。
  - 2026-08-01 17:29 CST 更新：手机 Moonlight 打开 host 后可能默认启动第一个
    Sunshine app 或上次 app；如果第一个 app 是“搜索电脑App/桌面”，用户会看到
    桌面而不是 Waydroid。当前 `~/.config/sunshine/apps.json` 的第一个 app
    必须是 `Waydroid 手机`，命令为
    `/var/home/charlie/.local/bin/moonlight-launch waydroid`，并重启
    `sunshine.service`。若用户仍看到旧入口，先让手机 Moonlight 断开后重新进入
    `fedora` host 以刷新 app 列表。
  - 2026-08-01 17:47 CST 菜单命名标准：手机 Moonlight 菜单保持短名、唯一名。
    当前顺序为 `Waydroid 手机`、`电脑浏览器`、`电脑终端`、`电脑文件`、
    `电脑监控`、`Steam 大屏幕`、`缺氧：安装或登录`、`缺氧：启动`、
    `电脑桌面`、`平板：搜索App`、`平板：浏览器`、`平板：终端`。不要再使用
    `Waydroid 手机 自动` 或重复的 `Waydroid 手机`。改名后重启
    `sunshine.service`，并可清理手机缓存：
    `su -mm -c 'rm -f /data/data/com.limelight/cache/applist/1379115E-D133-0E2A-499E-6E2D8CD9ECCF'`
    后重开 `com.limelight`。
- `:18082` 点击 Connect 后窗口关闭/无画面时，先查 Android framework 是否启动：`service check window`、`service check activity`、`getprop sys.boot_completed`、`journalctl --user` 里的 `system_server` crash loop。不要先反复改端口或替换 scrcpy-server。
- `service check window` / `activity` 不存在时，`ui-dump`、可视化和 app 自动化都会不稳定；先修复 Waydroid Android framework，再看 `ws-scrcpy`。
- 2026-08-01 发现 `system_server` crash root cause 是 inotify 上限过低：tombstone abort message 为 `Could not register INotify for /dev/input: Bad file descriptor`。已即时和持久化设置：
  - `/etc/sysctl.d/99-waydroid-inotify.conf`
  - `fs.inotify.max_user_instances = 8192`
  - `fs.inotify.max_user_watches = 1048576`
  - `fs.inotify.max_queued_events = 32768`
  修复后 `service check window` / `service check activity` 应为 `found`。
- 若 `ws-scrcpy` 仍无法连接，区分两层：
  - framework 层：`service check window`、`service check activity`、`ps -A | grep system_server`
  - ADB/visual 层：`/var/home/charlie/.local/share/WsScrcpyWeb/dependencies/adb/adb devices -l`
  当前已建 host 侧 netns proxy `waydroid-adb-netns-proxy.service`，监听 `127.0.0.1:15556` 转发到 Waydroid netns `127.0.0.1:5555`；若显示 `offline/unauthorized`，继续查 `/data/misc/adb/adb_keys`、adbd secure auth、init `adbd` 状态，不要回退到改 scrcpy 版本。
- `ws-scrcpy-web.service` 必须使用独立 ADB server，避免全局 `5037` 被真实手机 PKR110 / keepalive / mDNS 污染：
  - `ANDROID_ADB_SERVER_PORT=5039`
  - `ADB_MDNS_AUTO_CONNECT=0`
  - `ADB_SERIAL=127.0.0.1:15556`
  - `start-live.sh` 启动前 `kill-server`、`start-server`、`disconnect`、只 `connect 127.0.0.1:15556`
  验证命令：
  `ANDROID_ADB_SERVER_PORT=5039 ADB_MDNS_AUTO_CONNECT=0 /var/home/charlie/.local/share/WsScrcpyWeb/dependencies/adb/adb devices -l`
  应只看到 `127.0.0.1:15556 device ... waydroid_x86_64`。如果 18082 打开变慢或 Connect 黑屏 5 秒关闭，先查这个列表。
- `Clawdroid` 适合作为未来“Android 端本地 agent/节点”补层，不应替代 Fedora/Hermes 主控制面
