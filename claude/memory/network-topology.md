# network-topology.md — 网络拓扑统一视图
## 最后更新: 2026-06-02 | 自动生成: port-allocator.sh

---

## 一、三层接入体系（按优先级）

### 第1优先：Tailscale（内网直连/VPN）
- **本机 IP**: 100.119.174.25 (nixos-1)
- **Tailnet**: w422417869@github
- **在线设备**: ace-5-pro-3(100.108.28.44), win-s2d8gp89fu1(100.91.93.99)
- **Tailscale Serve**: nixos-1.tail60cff7.ts.net:4096 (OpenCode)
- **优势**: 零配置、直连延迟低、自动NAT穿透
- **劣势**: iOS/安卓后台被杀、需要安装客户端

### 第2优先：FRP 公网穿透（VPS中转）
- **DNS**: charlie1990.duckdns.org
- **VPS IP**: 125.110.221.37
- **FRPS 端口**: 7000 (bindPort), 7500 (Dashboard admin/frp@charlie2026)
- **FRPS Token**: frp-token-charlie-2026
- **FRPS 配置**: ~/ai-deploy/frps.toml
- **优势**: 公网可达、不需客户端
- **劣势**: 依赖VPS、延迟高、需配置白名单

### 第3优先：路由器端口转发（直连公网）
- **路由器**: 192.168.123.1 (Padavan)
- **NixOS 内网 IP**: 192.168.123.209
- **完整规则**: memory/router-infra.md（22条规则，自动快照）

---

## 二、端口分配决策树（死规则 — AI 必须逐步执行）

```
新增外部访问端口：
├─ 第1步：查 frps.toml 白名单
│   └─ grep "start = PORT" ~/ai-deploy/frps.toml → 命中=可用白名单端口，未命中=需新增
├─ 第2步：查路由器端口转发
│   └─ grep "PORT" memory/router-infra.md → 已配置/未配置
├─ 第3步：选最优接入方式
│   ├─ 仅Tailscale设备用 → Tailscale Serve (零配置)
│   ├─ 需要公网访问 → FRP (需在白名单内)
│   ├─ 低延迟大流量 → 路由器直连 (Padavan配置)
│   └─ 三选一，禁止同时配三套
├─ 第4步：执行配置
│   ├─ FRP: 编辑 frps.toml 加 allowPorts → restart frps
│   ├─ 路由器: 登录 192.168.123.1 加规则
│   └─ Tailscale: tailscale serve 命令
└─ 第5步：验证
    └─ curl -s http://charlie1990.duckdns.org:PORT → 200
```

---

## 三、FRP 白名单完整列表（来源：frps.toml）

| 端口/范围 | 用途 |
|-----------|------|
| 2222 | NixOS SSH备用 |
| 2223 | NixOS SSH主 |
| 2224 | SSH预留 |
| 3000 | OpenCode控制台 |
| 3389 | Windows RDP |
| 8022 | SSH预留 |
| 15555 | 手机ADB(WiFi) |
| 15556-15557 | 手机ADB预留 |
| 17698 | Windows AI |
| 17699 | NixOS AI |
| 17700 | AI预留 |
| 18090-18091 | OpenCode Sisyphus |
| 18093 | 预留 |
| 18300 | Sisyphus |
| 18420 | 预留 |
| 18700 | OpenAgents Net |
| 19890-19893 | Sisyphus备用 |
| 24801 | ydotool |
| 42111 | Sisyphus |
| 47980 | 预留 |
| 47994 | 预留 |
| 47999 | 预留 |
| 48020 | 预留 |
| 60000-60002 | 预留大区间 |
| 60003-60005 | 预留大区间 |

---

## 四、常见连接场景速查

| 场景 | 方案 | 命令 |
|------|------|------|
| 手机SSH NixOS | Tailscale: `ssh charlie@100.119.174.25` | 优先 |
| 手机SSH NixOS(无Tailscale) | FRP: `ssh charlie@charlie1990.duckdns.org -p 2223` | 降级 |
| 手机ADB | Tailscale: `adb connect 100.108.28.44:5555` | 优先 |
| 手机ADB(无Tailscale) | SSH Windows: `ssh G@192.168.2.36` → `adb` | 降级 |
| 公网访问OpenCode | http://charlie1990.duckdns.org:18090 | FRP |
| Tailscale设备访问OpenCode | http://100.119.174.25:4096 | Tailscale Serve |
| 公网SSH(无FRP) | 路由器直连 port 2222→22 | 最低延迟 |

---

## 五、VPS 信息

- **IP**: 125.110.221.37
- **SSH**: root@125.110.221.37
- **FRPS路径**: ~/ai-deploy/frps.toml
- **FRPS日志**: /var/log/frps/frps.log (maxDays=7)

## 六、已封装的工具

- `port-allocator.sh PORT 用途` — 自动预检+分配端口
- `memory/router-infra.md` — 路由器端口转发快照（自动更新）
- `phone-tailscale-guard` skill — 手机Tailscale保活
- `android-tailscale-keepalive` skill — Android Doze白名单