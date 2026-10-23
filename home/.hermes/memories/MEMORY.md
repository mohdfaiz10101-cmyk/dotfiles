主记忆保持约1200/2200字符；>=1500自动归档，path实时检查和5分钟timer兜底。大段经验用 ~/.local/bin/hermes-submemory add --category ops --text 保存；检索用 hermes-submemory search。分类库含归档，重生成前先收录新写入，禁止因容量反复丢记忆。
§
当前家庭网为OpenWrt 192.168.5.0/24；Fedora .144，手机 .211。网络任务先读 ~/.ai-context/runbooks/hermes-network-evidence.md；不能以代理出口更新DuckDNS，不能用路由器本机curl代替手机5G验收；保留PKR/Fedora原生代理及路由器旁路。
§
Deployment rule: 已有 skill 脚本时优先走 skill，不要绕过 `flexime-push.sh` / `install-to-phone.sh` 手跑 adb/pm install。
§
NetBird 模式：Fedora 本机连自己 NetBird IP 可能超时（发夹式路由）；手机侧 curl/MCP 探测 Fedora NetBird IP 才可信。本机接口名 `wt0`；`wt0` 不存在不直接等于 NetBird 故障。
§
2026-10-23会话c016a43ccbca复核：ZeroTier子网路由192.168.5.0/24必须via OpenWrt的ZT地址10.68.142.60；路由器本机curl不能验证手机VPN转发。402只证明该次API请求被套餐拒绝，不证明Android支持手工路由。当前验收与替代方案见~/.ai-context/runbooks/hermes-network-evidence.md。
§
冷记忆检索（本条不在上面即按需查）：分类库 `~/.hermes/memories/categories/*.md`[user-preference(9) ops(4) network(3)]；语义检索 `~/.hermes/memories/vector_memory.db`；归档 `archive/<id>.json`；会话史用 session_search。
