# 问题速查表

| 症状 | 根因 | 修复步骤 |
|:-----|:-----|:---------|
| **VSCode 每次重启要重新登录 / Roo Code API 请求失败** | 系统 keyring 服务未运行（KWallet 或 gnome-keyring），VSCode 无法存储 API token。Roo Code 日志显示 `CloudService not ready` / `changeState: logged-out` | **临时方案（立即生效）**：`echo '{"password-store":"basic"}' > ~/.config/Code/User/argv.json`，然后重启 VSCode。**永久方案（需重启系统）**：在 `/etc/nixos/modules/desktop.nix` 中添加 `security.pam.services.kwallet = { name = "kwallet"; enableKwallet = true; };` + `programs.dconf.enable = true;`，然后 `sudo nixos-rebuild switch` + 重启系统。**验证**：`pgrep -a kwalletd6`（应该看到进程），重启 VSCode 后不再要求登录 |
| 症状 | 根因 | 修复步骤 |
|:-----|:-----|:---------|
| 定时器从未触发、服务占用内存但无负载 | letta-sync-obsidian.timer、proxy-free-refresh.timer 配置错误；ModemManager/geoclue/ollama/waydroid 等服务启用但未实际使用 | 检查 timer 配置：`systemctl cat <timer>`；禁用非必要服务：`sudo systemctl disable --now ModemManager geoclue`；停止未使用服务：`sudo systemctl stop ollama waydroid-container` |
| KWin 截图失败："not authorized to take a screenshot" | **Wayland 安全模型**：spectacle `-b`（后台模式）无法触发授权对话框，需要用户交互授权 | 修复：`spectacle -g`（GUI 模式）首次授权 → 点击"截图"→ 完成授权后关闭；验证：`spectacle -b -f -o /tmp/test.png`；原生工具：`grim /tmp/screenshot.png` 或 `grim -g "$(slurp)" /tmp/screenshot.png"`（需先在 NixOS 安装 grim/slurp）；快捷键方式：Meta+Shift+S（绕过命令行授权问题） |
| 預設 Generation 開機黑屏，掉進 `grub>` 命令行 | EFI 分區 252MB 爆滿（95%），GRUB 寫入不完整 | LiveCD 進入 → 手動選 Gen 64 → 重寫 GRUB |
| qwen3/deepseek-r1 的 thinking mode 导致 content 为空 | Ollama OpenAI 兼容端點不支持 `think: false`、LiteLLM 的 `merge_reasoning_content_in_choices` 在 streaming 模式下無效、Continue 的 `requestOptions.extraBodyProperties` 無法正確傳遞 `think: false` | Continue 用原生 Ollama provider 直連（繞過 LiteLLM） |
| 全系統斷網 | mihomo TUN + clash-verge-rev 雙引擎互搶流量 | 移除 clash-verge-rev、關閉 TUN 模式，改為手動代理 port 7890 |
| 屏幕冻住/黑屏，鼠标键盘无响应，无法唤醒，只能按电源键强制关机 | NVIDIA 驱动无法为显示渲染分配 GPU 显存（NVKMS/GEM 对象），导致整个显示子系统挂死 | # 1. 停止崩溃循环的服务
systemctl --user stop hyperchat.service
systemctl --user disable hyperchat.service

# 2. 重新开启 NVIDIA 持久化模式
sudo nvidia-smi -pm 1

# 3. 检查 GPU 显存使用
nvidia-smi |
| 屏幕冻住/黑屏，鼠标键盘无响应，无法唤醒，只能按电源键强制关机 | NVIDIA 驱动无法为显示渲染分配 GPU 显存（NVKMS/GEM 对象），导致整个显示子系统挂死 | # 1. 停止崩溃循环的服务
systemctl --user stop hyperchat.service
systemctl --user disable hyperchat.service

# 2. 重新开启 NVIDIA 持久化模式
sudo nvidia-smi -pm 1

# 3. 检查 GPU 显存使用
nvidia-smi |
| 遇到403错误 | settings.json中的env字段覆盖了OAuth | 检查并修改settings.json中的env设置，或使用正确的认证方式 |
| mihomo已停用 | 香港节点被Anthropic封 | TUN模式已移除避免断网 |
| GLM API timeout | daemon超时被杀 | 改为90s |
| LiteLLM routing_strategy不尊重priority | 配置错误 | 检查priority配置并确保正确设置 |
| content为空 | qwen3/deepseek-r1 thinking mode导致内容为空 | 直连Ollama绕过 |
| GNOME覆盖IM为ibus | GNOME默认设置覆盖输入法配置 | 通过extraGSettingsOverrides进行修复 |
| host.docker.internal解析错误 |  | 改用Docker网关IP |
| 余额不足返回429 | 账户余额不足导致API调用被限制 | 补充账户余额或检查账户状态 |
| 书签栏、cookies、登录状态全部消失 | Floorp 从 `/mnt/pool/home-offload/auto-migrate/` 迁移到 `~/.floorp/` 时，NixOS 重建（system-67）创建了新空 profile `rw7f0w9p.default`，旧数据留在 `tj4l1osg.default` | 从旧 profile 复制 `places.sqlite`（书签）、`cookies.sqlite`（cookies）到当前活跃 profile |
| Docker 无法启动，报错 `error while opening volume store metadata database: timeout` | NTFS3 文件系统不支持 Docker 所需的文件锁机制（flock） | 改为本地 ext4/btrfs/xfs 分区（如 `/var/lib/docker`），临时 workaround：AGI Brain 可以在无 Docker 的情况下运行（使用规则引擎 fallback） |
| NixOS VS Code --extensions-dir 写入目录必须使用 `--extensions-dir` 参数，CC GUI 安装到可写目录可能无法识别扩展 | CC GUI 安装到可写目录导致扩展无法识别 | 使用 `--extensions-dir /home/charlie/.vscode/extensions/` 启动 |
| urllib.parse.quote / urlencode 对 %3A 等已编码字符二次编码导致 422 错误 | urllib 编码函数对已编码字符进行二次编码，使服务器无法正确解析请求参数 | 手动预编码 query 参数，用 %3A%3E 替代 :>，并限制关键词数量在 3 个以内；示例：q = f"pushed%3A%3E{since}+stars%3A%3E100+%28{query}%29" |
| tech-digest-viewer 服务被 TERM 杀死后未自恢复 | 服务配置为 enabled，但缺少 Restart=on-failure 配置导致 inactive(dead) 后未自动重启 | 手动执行 `systemctl --user start tech-digest-viewer` 命令启动服务，并检查服务配置是否添加了 Restart=on-failure 以实现自动重启 |
| HTTPServer 单线程处理 /sse GET 长连接时阻塞所有 POST /mcp 请求 | 单线程处理长连接导致阻塞 | 引入 ThreadingMixIn 改为 ThreadingHTTPServer，每个连接独立线程 |
| 微信 Wayland 下 fcitx5 候选框不显示 | WeChat UOS 的 Wayland text-input 协议 cap=72（仅基础文本），不支持 preedit/candidate | 强制 `QT_QPA_PLATFORM=xcb` 使用 XWayland，候选框通过 X11 IM 模块显示；修改文件：`wechat-uos-scaled.desktop`、`wechat-launcher.sh`；需重启微信才能生效 |
| 微信输入法完全不工作（fcitx5） | fcitx5.service 缺少 DISPLAY/WAYLAND_DISPLAY 环境变量 → XIM 未在 XWayland 注册 → xcb 模式的微信无法连接输入法 | 1. fcitx5.service 添加 `PassEnvironment=DISPLAY WAYLAND_DISPLAY XDG_SESSION_TYPE` 2. wechat-uos.desktop（autostart）添加 `QT_QPA_PLATFORM=xcb QT_IM_MODULE=fcitx XMODIFIERS=@im=fcitx` 3. `systemctl --user daemon-reload && systemctl --user restart fcitx5` 4. 重启微信 |
| Bash 竞态条件：grep 检查 + echo 追加非原子，多进程并发时会重复处理 | grep 检查 + echo 追加非原子 | 用 flock + double-check locking 模式。示例：`flock -x 200; grep再检查; echo追加; 200>lockfile` |
| Python JSON 解析失败，LLM返回数据包含markdown代码块或格式异常 | LLM返回的数据包含markdown代码块或格式异常导致JSON解析失败 | 1. 提取代码块 2. 提取花括号 3. try-except捕获JSONDecodeError 4. 记录原始输出 5. 回退备用策略 |
| Floorp代理设置无效，需修复 | 代理配置未正确设置 | 添加 network.proxy.type=1 和 http/https/socks 代理设置后重启浏览器；使用 kwriteconfig6 --file kioslaverc --group "Proxy Settings" 配置 KDE 系统代理 |
| tg-push 未找到（exit 127） | systemd service 环境 PATH 不包含 ~/.local/bin | 1. service 文件添加 Environment="HTTPS_PROXY=http://127.0.0.1:7890" 2. 脚本使用绝对路径 /home/charlie/.local/bin/tg-push 3. 优化逻辑：Telegram 成功时不回退桌面通知，只有失败且 CRITICAL 才弹窗 |
| 3 个 systemd 服务失败 | ~/.cache → /mnt/pcache symlink I/O 异常，导致 tee 写入 Invalid argument | 迁移日志路径至 ~/.local/state/letta/；sync 脚本改为直接 python3；health-check/monitor 退出码改为检测到问题时 exit 0 |
| Meta+Space冲突 | evdev模式不支持字母键，KDE应用启动器占用快捷键，Plasma 6移除khotkeys导致配置失效 | 禁用evdev改用KDE手动配置+Toggle模式，或通过ScrollLock长按模式（push_to_talk）替代 |
| 快照冲突 `AlreadyExists: target snapshot`、blob 文件丢失 `blob not found` | 系统异常关机/磁盘满/Docker 更新失败导致 metadata 不一致 | 停止 Docker → 删除 `/path/to/docker/containerd/daemon/io.containerd.metadata.v1.bolt/meta.db` → 重启 Docker |
| Floorp 配置迁移到 ext4 分区 | NTFS3 分区文件系统损坏导致 Floorp 配置损坏 | /tmp/reset-floorp.sh 脚本重置配置到 ~/.floorp (ext4)，禁用硬件加速 layers.acceleration.disabled: true |
| Telegram Bot 输出格式与 Power User Protocol 2026 不一致 | 输出格式未遵循协议规范 | 重构输出格式：状态前缀使用[OK]/[RUNNING]/[FAILED]/[WARN]，添加---分割线，限制每段≤3行，新增/goals命令 |
| LLM 思考环 100% 超时 (20s)，回退到规则决策 | Groq 免费层日 token 限制 10 万耗尽 → 429；LiteLLM 内部 fallback 链 → GLM 模型余额不足 + 速率限制 | 主模型切换为 free/groq-llama4-scout；Fallback 模型更换为 free/mistral-small；使用 subprocess+curl 绕过 httpx 兼容性问题；精简 system prompt 至 200 token；think.py 自行管理 fallback 链 |
| litellm docs 重复 fetch 导致 Floorp 反复打开同一 URL | CLAUDE.md '联网验证'规则触发每次涉及 litellm 重新 fetch | CLAUDE.md 新增'禁止重复 fetch 规则'，同一 URL 每会话只允许一次 |
| 没有服务端记忆功能，无法跨会话保持上下文 | 使用第三方API代理（2233.ai）而非官方订阅 | 1. 订阅官方Claude Code Pro/Max计划
2. 删除ANTHROPIC_BASE_URL环境变量
3. 使用官方API key或登录账号
4. 重启Claude Code服务 |
| 会话历史丢失，无法通过API代理保存记忆 | 第三方API代理（2233.ai）无服务端记忆功能，属于API设计特性 | 创建sync-session-to-letta脚本强制同步会话到Letta archival memory，通过Letta实现外部记忆系统 |
| http://127.0.0.1:8080/gallery/ 打不开 | 端口 8080 无服务监听，实际 open-webui 运行在端口 3001 | 访问 http://127.0.0.1:3001/ 或启动服务：`cd /mnt/ai/ai-cluster/open-webui && docker compose up -d` |
| Letta 启动卡死在 "Checking NLTK data availability..." | nltk.download() 通过 HTTPS_PROXY(mihomo) 联网验证版本超时，即使本地数据已存在 | (1) 创建 entrypoint.sh sed 替换 nltk.download 为 no-op (2) 挂载 NLTK 数据 volume (3) docker-compose 自定义 entrypoint |

## Floorp 浏览器 - 后台标签页无法弹窗

**症状**: 网页在后台标签页时，无法通过 JavaScript 打开新窗口

**原因**: Floorp 默认阻止后台标签页的弹窗，防止恶意广告

**快速修复**:
```bash
floorp-popup-fix
```

**手动修复**:
1. 在 Floorp 地址栏输入 `about:config`
2. 搜索并修改以下配置：
   - `dom.disable_open_during_load` → `false`
   - `dom.popup_maximum` → `50`
   - `privacy.popups.showBrowserMessage` → `false`
   - `dom.allow_scripts_to_close_windows` → `true`
3. 重启 Floorp

**针对特定网站**:
1. 访问网站 → 地址栏 🔒 锁图标
2. 更多信息 → 权限 → 打开弹出式窗口 → 允许

**恢复默认**:
```bash
# 使用备份恢复
cp ~/.floorp/rw7f0w9p.default/prefs.js.backup-* ~/.floorp/rw7f0w9p.default/prefs.js
```

**详细文档**: `/tmp/floorp-popup-fix.md`

---

## 浏览器反复自动打开某个 URL

**症状**：某个 URL 每隔几分钟在 Floorp 中被自动打开，清理浏览器历史/session 后仍复发

**排查步骤**：
1. 创建 `~/.local/bin/floorp` wrapper 拦截并记录所有调用（含 ppid/cgroup/INVOCATION_ID）
2. 从 INVOCATION_ID 定位触发来源的 systemd service（`systemctl --user show '*' --property=InvocationID,Id | paste - - | grep <id>`）
3. 检查该 service 的 PATH 是否包含 `~/.local/bin`（`tr '\0' '\n' < /proc/<pid>/environ | grep PATH`）
4. 如果 PATH 缺少 wrapper 目录，在 service 文件中添加 `Environment=PATH=...`

**修复**：
- 在目标 service 的 `.service` 文件中添加 `Environment=PATH=/home/charlie/.local/bin:$PATH`
- 多层 wrapper 防御：xdg-open → kde-open → floorp
- 重启 service 使 PATH 生效

**关键点**：systemd user service 的 PATH ≠ login shell 的 PATH
| systemd service ModuleNotFoundError (Python) | service 环境 Python 缺少模块，user shell 环境有但 systemd 隔离环境无 | 方式1：path 添加 `(pkgs.python3.withPackages (ps: [ ps.模块名 ]))`；方式2：ExecStart 改用 `${pkgs.python3.withPackages (ps: [ ps.模块名 ])}/bin/python3` |
| NTFS3 MFT 序列号错误（~/.cache 读写失败） | NTFS 分区元数据损坏，多个服务（browser-cookie-sync/paperclip-auto-sync）失败，~/.cache 部分文件无法读写删 | 1. Windows 侧：`chkdsk D: /f`（需重启）；2. Linux 侧（卸载后）：`sudo umount /dev/sdb1 && sudo ntfsfix /dev/sdb1`；3. 修复后重新挂载和重启相关服务 |
| NixOS systemd service 路径错误（/bin/bash / /usr/bin/python 不存在） | NixOS 无 FHS 标准路径，所有二进制文件在 /nix/store | 1. ExecStart 改用 `${pkgs.bash}/bin/bash` 或 `/run/current-system/sw/bin/bash`；2. path 添加依赖包（如 `path = [ pkgs.bash pkgs.coreutils ... ]`）；3. nixos-rebuild switch 应用 |
| 根分区使用率高（78%+） | nix store 长期未清理，旧 generation 占用空间 | 1. `nix-collect-garbage -d`（删除所有旧 generation）；2. `nix-store --gc`（深度清理）；3. `nix-store --optimise`（硬链接去重）；4. 定期执行（建议每月） |
| VSCode 无法启动（缓存目录创建失败） | `~/.config/Code` 是悬空符号链接，指向不存在的 `/mnt/ai/home-offload/.config/Code`（可能是之前磁盘清理迁移留下的残留链接）| `rm ~/.config/Code && mkdir -p ~/.config/Code`，删除符号链接后 VSCode 会在本地重建配置 |
| 微信命令行启动窗口不显示 | Claude Code 会话缺少 DISPLAY/WAYLAND_DISPLAY 环境变量，命令行启动的图形应用无法正确连接到 Wayland 显示服务器 | **最可靠方案**：从 KDE 应用启动器打开（Meta 键搜索"微信"）；**备选方案**：双击桌面快捷方式 `~/Desktop/wechat.desktop`；**命令行方案**：`systemd-run --user --scope wechat-uos` 或从 plasmashell 继承环境变量；**不要用**：直接执行 `wechat-uos` 不会显示窗口 |
| 微信启动失败（从 CLI 启动） | 双重根因：(1) .xwechat 符号链接指向 NTFS 分区，NTFS 有 MFT 损坏导致 36+ 文件 Invalid argument (2) bwrap --die-with-parent 导致 CLI 退出时微信被杀 | (1) rsync --ignore-errors 将 .xwechat 迁移到本地 ext4（1.6G）(2) 创建修改版启动脚本去掉 --die-with-parent：sed 's/--die-with-parent//' "$WRAPPER" > tmpscript (3) 脚本位置 ~/.local/bin/start-wechat |
| KDE 截图快捷键无反应 | (1) 脚本缺失：快捷键指向的脚本文件不存在（khotkeys 无报错）；(2) Wayland 授权缺失：spectacle 后台模式需首次 GUI 授权；(3) 服务状态误判：plasma-kglobalaccel 按需启动设计，inactive 状态正常 | 1. 检查脚本存在性：`ls /etc/nixos/scripts/screenshot-pin`（如缺失重建）；2. 重启 khotkeys：`qdbus org.kde.kded6 /kded reconfigure`；3. 首次授权：`spectacle -g` 点击授权对话框"允许"；4. 测试快捷键（Scroll Lock / Pause Break / Meta+Shift+S） |
| Wayland 截图授权反复失败（命令行/脚本/快捷键） | KWin Wayland 截图 API 强制要求用户交互授权，每次截图都需在 GUI 中手动确认，命令行调用无法触发授权对话框 | **彻底方案**：切换到 X11 会话（注销 → 登录界面选择 'Plasma (X11)'）；**临时方案1**：双击桌面快捷方式 `~/Desktop/screenshot.desktop`；**临时方案2**：运行 `~/.local/bin/screenshot-now`；**临时方案3**：在 Spectacle 窗口中点击 'Take Screenshot' 按钮 |
| 自动登出/回到登录界面，输入密码无法登录 | (1) 密码错误：实际密码存储在 `/etc/nixos/secrets/secrets.yaml`（sops 加密管理），不是用户以为的 123456；(2) baloo_file_extractor 大量崩溃（SIGABRT）导致 KDE 桌面不稳定；(3) 根分区空间 88% 已用，kwin 无法写入缓存触发桌面崩溃 | 1. 临时重置密码：`sudo passwd charlie`（设置新密码）；2. 禁用 baloo 索引：`balooctl6 disable`；3. 清理磁盘空间：`sudo nix-collect-garbage -d` |

### Claude CLI 403 + 代理自断网
**症状**: 修改 proxy.nix 后 rebuild，Claude 连接中断返回 403
**原因**: nixos-rebuild switch 重启 xray/mihomo 服务，代理瞬断；如果 VPS DNS 解析失败则长时间不可用
**修复**:
1. 先运行 `~/launcher/glm-proxy-fix.sh` 打开 GLM 应急窗口
2. 确认 xray 状态：`systemctl status xray`，端口：`ss -tlnp | grep 7890`
3. 测试连通性：`curl -x socks5h://127.0.0.1:7891 https://www.google.com`
4. 如需 rebuild：先 `nixos-rebuild build` 验证，再 `switch`
**预防**: proxy.nix 已包含 anthropic.com 显式路由规则，避免依赖 geolocation-!cn 兜底

## Roo Code 每次启动需要重填 API 配置
**症状**：每次打开 VSCode 都需要重新选择/输入 API Provider
**原因**：API keys 存储在 Secret Storage，settings.json 中的 apiProfiles 无效
**修复步骤**：
1. Roo Code 侧边栏 → ⚙️ → Export → 保存 `~/roo-code-settings.json`
2. settings.json 添加：`"roo-cline.autoImportSettingsPath": "~/roo-code-settings.json"`
3. 重启 VSCode 验证自动导入（会弹通知）
**验证**：启动后应显示 "Successfully imported settings from roo-code-settings.json"

- [2026-04-12] [RooCode] 禁用KDE ScrollLock热键绑定，解决语音输入按键冲突问题

- [2026-04-12] [RooCode] 分析AnyIn.1 APK的WhatsApp集成问题：发现APK硬编码了web.whatsapp.com（桌面网页版），导致用户打开的是WhatsApp Web而非手机原生应用
  AnyIn.1 APK是WebView+Xray代理的万能浏览器，WhatsApp URL硬编码在classes3.dex中为https://web.whatsapp.com，需要改为Intent调用原生WhatsApp或使用移动端友好的URL
## USB Tethering 自动切换失败（平板网络共享）
**症状**：插入平板 USB 后，系统未自动切换到平板代理 (192.168.80.242:7890)
**多层根因**：
- **P0 用户侧**：平板 USB 模式为 "仅充电+ADB"，未开启 "USB 网络共享" → 无 RNDIS 网络接口
- **P1 系统侧**：NixOS 配置缺少 USB 网络驱动 (`rndis_host`, `cdc_ether`) → 即使平板开启共享也无法识别
- **P2 配置侧**：`/etc/NetworkManager/dispatcher.d/99-tablet-proxy` 脚本丢失 → 即使接口启动也不会触发代理切换

**诊断步骤**：
```bash
# 检查 USB 设备连接
lsusb | grep -i xiaomi         # 应显示 18d1:4ee7 Redmi K80
adb devices                    # 应显示设备在线

# 检查 USB 网络接口（关键）
ip link show | grep -E 'enp.*u'  # 应出现类似 enp0s20f0u4 的接口
                                 # 如无此接口 → P0/P1 未解决

# 检查 192.168.80.242 可达性
ping -c 1 192.168.80.242       # 应 ping 通
nc -zw3 192.168.80.242 7890    # 代理端口应可达

# 检查 dispatcher 脚本
ls /etc/NetworkManager/dispatcher.d/99-tablet-proxy  # 应存在且可执行

# 检查切换日志
tail -20 /var/log/tablet-proxy.log  # 应有最新切换记录
```

**修复步骤**：

**1. 用户侧（必须）** — 开启平板 USB 网络共享
- 在平板 **设置 → 开发者选项 → 默认 USB 配置** → 选择 **"USB 网络共享"** 或 **"RNDIS (USB Ethernet)"**
- 或在 **设置 → 连接与共享 → USB 网络共享** 手动开启
- 保持 USB 连接，等待 3-5 秒后执行 `ip link show` 验证 `enp*u*` 接口出现

**2. 系统侧（推荐）** — 添加 USB 网络驱动
编辑 `/etc/nixos/modules/networking.nix` 添加：
```nix
boot.kernelModules = [ "rndis_host" "cdc_ether" "cdc_subset" ];
```
执行：
```bash
sudo nixos-rebuild switch
lsmod | grep -E 'rndis|cdc_ether'  # 验证模块加载
```

**3. 配置侧** — 重新部署 dispatcher 脚本
```bash
sudo nixos-rebuild switch  # 确保 tablet-proxy.nix 生效
ls -l /etc/NetworkManager/dispatcher.d/99-tablet-proxy  # 验证脚本存在
```

**验证清单**（平板开启共享后执行）：
```bash
ip link show | grep -E 'enp.*u'           # ✅ 应出现 USB 网络接口
ping -c 1 192.168.80.242                  # ✅ 应 ping 通
nc -zw3 192.168.80.242 7890               # ✅ 代理端口可达
tail /var/log/tablet-proxy.log            # ✅ 应出现新切换日志
env | grep http_proxy                      # ✅ 新 shell 应显示平板代理
curl -x http://192.168.80.242:7890 https://www.google.com  # ✅ 应返回 HTML
```

**历史成功案例** (2026-04-11 01:00:11)：
- 日志记录自动切换到平板代理
- 当时条件：平板开启 USB Tethering + dispatcher 脚本正常 + 192.168.80.242:7890 可达

**防复发**：
- 创建快捷脚本 `~/.local/bin/enable-tablet-tethering`（通过 adb shell 自动开启平板 USB 共享）
- NetworkManager dispatcher 日志改为 journald（方便跨会话追溯）
- 每次 nixos-rebuild 后检查：`ls /etc/NetworkManager/dispatcher.d/99-tablet-proxy`
- 测试命令：`sudo /etc/NetworkManager/dispatcher.d/99-tablet-proxy <接口名> up`

- [2026-04-12] [RooCode] 微信任务栏图标不显示问题诊断与修复
  微信在 KDE Plasma 6 下任务栏图标不显示，但 StatusNotifierItem 已注册且 Active。根因：微信的 Qt 系统托盘图标在 Wayland + XWayland 环境下可能因缺少 libdbus-1.so.3 或 Qt 插件路径问题导致图标渲染失败。修复：确保 FHS 环境包含 dbus 库，重启 plasmashell 可临时恢复。
- [2026-04-12] [RooCode] 微信任务栏图标不显示问题根因与修复方案
  微信任务栏图标不显示的根本原因是：微信的 StatusNotifierItem 注册成功（`org.kde.StatusNotifierItem-152701-1`），但 plasmashell 的系统托盘组件未正确读取图标数据。可能由于 FHS 环境缺少 dbus 库或 Qt 插件路径问题。重启 plasmashell 可临时恢复，但需要修改 wechat-uos.nix 添加 dbus 依赖。

## Roo Code 模式选择器只显示 5 个模式（而非 7 个）

**症状**: Roo Code UI 的模式选择器只显示 Code、Architect、Ask、Debug 4 个模式，缺失 Review、Optimize、Doc。

**根本原因**: Roo Code 采用"项目级覆盖全局级"的加载策略。当项目的 `.roo` 目录存在时，Roo Code 只加载该目录中定义的 `rules-{mode-slug}/` 子目录对应的模式。缺失的 rules-review/、rules-optimize/、rules-doc/ 导致这 3 个模式无法显示。

**关键点**:
- 全局配置 (custom_modes.yaml) 中的 7 个模式都定义正确
- 项目级配置 (cline-workspace/.roo/) 中只有 5 个 rules-* 目录
- UI 加载优先级: 项目级 > 全局级

**修复步骤**:
1. 在 `cline-workspace/.roo/` 中创建缺失的目录:
   ```bash
   mkdir -p {rules-review,rules-optimize,rules-doc}
   ```
2. 在每个目录中创建 system.md 文件，定义该模式的规则
3. 重新加载 VSCode 窗口 (Ctrl+R)

**验证**: 重载后模式选择器应显示完整的 7 个模式。

**参考**: https://docs.roocode.com/features/custom-modes

| 重启后 nixos-rebuild switch 改动全部失效（回到旧系统） | GRUB 的 `bootPath=/boot` 写 grub.cfg 到 rootfs `/boot/grub/`，但 GRUB EFI 从 `/boot/efi/grub/` 读取（EFI FAT32），两个文件不同步 | 临时：`sudo cp /boot/grub/grub.cfg /boot/efi/grub/grub.cfg`；验证：`cat /proc/cmdline` 对比 `readlink /nix/var/nix/profiles/system`，init 路径应匹配；永久修复待定（调整 bootPath 或添加 post-rebuild hook） |

| WeChat 每次 reboot 后 SIGABRT 崩溃 | xdg-autostart 启动太早（5s），crashinfo 残留旧 store path → crashpad abort | 专用 systemd service `wechat-uos.service`（After=graphical-session, sleep 8, Restart=on-failure）+ `wechat-uos-safe` 启动脚本清理 crashinfo + 等待 D-Bus。禁用 autostart desktop |

| 系统通知弹出 "HTTP 000000 请检查网络" | `proxy-403-monitor` 的 curl 超时仅 5 秒，代理节点偶尔慢响应时返回 `000`（网络层超时），触发误报告警 | 增大 `--max-time` 到 10 秒，或在脚本中过滤 `000` 状态码不触发告警 |

| Letta agent 创建后 LLM 调用报 "Failed to connect to OpenAI" | `model_endpoint` 设成 `localhost:4000`，Letta 在 Docker 内无法访问宿主机 localhost | 改为 `http://172.19.0.1:4000/v1`（Docker bridge IP） |

| Desktop Entry 点击报 "无法找到程序 /nix/store/xxx" | NixOS 升级后 store hash 变化，旧路径失效 | 替换为 `/run/current-system/sw/bin/xxx`（自动跟踪当前 generation） |

| Nix Store 路径禁令 | 用户空间文件（desktop entry、systemd service、脚本）硬编码 `/nix/store/xxxx/bin/xxx` | 必须用 `/run/current-system/sw/bin/xxx` 符号链接。硬编码路径在 nixos-rebuild 升级或 nix-collect-garbage 后必然断链 |
| hyperchat.service 自动重启 | `WantedBy=default.target` 导致即使 disable 也在全局 scope 自动启动 | (1) 注释 `[Install] WantedBy=default.target` (2) `systemctl --user disable --now hyperchat.service` (3) 验证 `systemctl --user status hyperchat.service` 应显示 inactive(dead) |
| voxtype 崩溃 (File exists error 17) | `~/.local/share/voxtype` 是指向不存在 NTFS 路径的悬空符号链接 | `rm ~/.local/share/voxtype && mkdir -p ~/.local/share/voxtype`，然后下载模型：`voxtype setup` 或手动下载 ggml-base.bin 到 `~/.local/share/voxtype/models/` |
| opencode-stt 插件 numpy ImportError | Python venv 缺少 `libstdc++.so.6`（NixOS 无标准 FHS 路径）+ PortAudio 缺失 | 用 nix-shell 启动 opencode 或 venv 中设置 `LD_LIBRARY_PATH=$(nix eval nixpkgs#gcc.cc.lib)/lib` |

## [2026-04-17] 纸杯包装机 HS 编码查询

**查询时间**：2026-04-17
**任务**：查询纸杯包装机（Paper Cup Packing Machine）的 HS 海关编码

**主要发现**：
1. **纸浆、纸或纸板制品模制成型机器**：HS 8441400000
   - 适用：纸杯机、纸杯成型机、纸杯贴面机、纸杯水线机
   - 无海关监管条件，无检验检疫要求
   - 申报要素：品牌、型号、用途等

2. **纸杯机（具体）**：HS 8441309000
   - 适用：全自动纸杯制造机、超声波纸杯成型机
   - Made-in-China 实际出口产品使用此编码

3. **独立包装机**：HS 84223030.90
   - 适用：纯包装功能的机器（非制造）

**申报建议**：
- 纸杯制造/成型 → 8441309000 或 8441400000
- 纸杯包装（独立功能）→ 84223030.90
- 必须提供品牌、型号、用途等申报要素

**外贸操作**：
- 出口报关无需许可证（8441400000）
- 中国进口关税约 5%-10%，增值税 13%
- 准备设备说明书、技术参数、品牌型号证明

**参考文件**：~/Desktop/外贸知识/纸杯包装机HS编码查询-2026-04-17.md

**相关查询**：
- 纸杯（成品）：48236910（一次性纸杯）、48236990（纸杯盖）
- 纸杯机配件：84419090.00

---

## [2026-04-18] 成本审计服务不可用

**症状**：成本审计巡检无法获取 LiteLLM 消耗数据和 Ollama 本地模型状态

**根因**：
1. **LiteLLM API 离线**：Docker 容器运行但健康检查失败（`curl -sf http://localhost:4000/health` 无响应）
2. **Ollama 服务未运行**：`curl -sf http://localhost:11434/api/tags` 无响应

**影响**：
- 无法追踪实际 API 消耗（预算 $10/月，70%🟡 / 100%🔴 告警失效）
- DeepSeek 模型不可用（硅基动力版已停用，依赖 LiteLLM 网关）
- 无法使用免费本地模型

**诊断步骤**：
```bash
# 检查容器运行状态
docker ps | grep -E "litellm|ollama"

# 检查健康状态
curl -sf http://localhost:4000/health || echo "LiteLLM 不可用"
curl -sf http://localhost:11434/api/tags || echo "Ollama 不可用"

# 查看日志
docker logs litellm --tail 50
systemctl status ollama
```

**修复步骤**：

**1. LiteLLM 修复**：
```bash
# 检查日志找错误
docker logs litellm --tail 100 | grep -i error

# 重启服务
docker restart litellm

# 如仍失败，检查配置
cat ~/.config/litellm/litellm_config.yaml

# 检查端口占用
ss -tlnp | grep 4000
```

**2. Ollama 修复**：
```bash
# 启动服务
systemctl start ollama

# 或用 Docker 运行
docker run -d --gpus all -p 11434:11434 --name ollama ollama/ollama

# 验证
curl -sf http://localhost:11434/api/tags | jq '.models | length'
```

**验证**：
- LiteLLM：`curl -sf http://localhost:4000/spend/tags | jq` 应返回消耗数据
- Ollama：`curl -sf http://localhost:11434/api/tags | jq '.models[] | .name'` 应列出模型

**预防**：
- 添加 systemd 服务监控 LiteLLM/Ollama 健康状态
- 定时任务重启失败服务
- 成本审计巡检在服务离线时自动告警（Telegram/notify-send）

**替代方案（应急）**：
- 临时使用 GLM 免费额度（已配置）
- Claude API 直接调用（无 LiteLLM 代理）
- 等待服务恢复后补充成本数据

| sudo 无法使用，报错 "必须属于用户 ID 0(的用户)并且设置 setuid 位" | NixOS sudo 配置错误，setuid 位未正确设置 | 检查 `/etc/nixos/configuration.nix` 中的 `security.sudo` 配置，重新构建系统：`sudo nixos-rebuild switch` |
| 防火墙无规则，系统完全暴露 | nftables 未启用或配置为空规则 | 在 `/etc/nixos/configuration.nix` 中启用防火墙：`networking.nftables.enable = true; networking.firewall.enable = true; networking.firewall.allowedTCPPorts = [ 22 80 443 ];` |

## KDE 任务栏/通知卡死（DrKonqi 堆积）
- **症状**：通知点不掉，任务栏点不动
- **根因**：多个 DrKonqi coredump-launcher 服务累积，plasmashell 冻结
- **修复**：在 Kitty 终端运行：`killall plasmashell && WAYLAND_DISPLAY=wayland-0 plasmashell &`
- **预防**：定期 `systemctl --user reset-failed 'drkonqi*'` 清除失败状态；coredump 积累超过 3 个时自动清理
## Alist 创建存储报 UNIQUE constraint failed
- **症状**：`/api/admin/storage/create` 返回 500 `UNIQUE constraint failed: x_storages.mount_path`
- **根因**：mount_path 已存在（可能之前创建过）
- **修复**：先查 `/api/admin/storages` 确认现有存储，若需更新用 `/api/admin/storage/update`；若字段名拼错（additional vs addition），Alist v3 用 `addition` 不是 `additional`

## Playwright 打开百度超时
- **症状**：`page.goto timeout 30000ms exceeded`
- **根因**：未配置代理，百度域名在国内需代理才能从NixOS访问
- **修复**：launch args 加 `--proxy-server=http://127.0.0.1:7890`，context 加 `proxy: { server: 'http://127.0.0.1:7890' }`
- [2026-05-08] [GLM] 症状→原因→状态: OP连接守护/service-nurse定时器停止运行→可能systemd timer被禁用或依赖链断裂→待修复
- [2026-05-08] [GLM] 症状:ai-config-guard反复exit-code 2→原因:INVALIDARGUMENT→状态:已知未修复
- [2026-05-08] [GLM] 症状→原因→状态: OP connection-guard日志停更于5月4日后断更，service-nurse日志停更于4月22日，推测相关timer已停止或service本身failed未恢复
