主记忆保持约1200/2200字符；>=1500自动归档，path实时检查和5分钟timer兜底。大段经验用 ~/.local/bin/hermes-submemory add --category ops --text 保存；检索用 hermes-submemory search。分类库含归档，重生成前先收录新写入，禁止因容量反复丢记忆。
§
当前家庭网为OpenWrt 192.168.5.0/24；Fedora .144，手机 .211。网络任务先读 ~/.ai-context/runbooks/hermes-network-evidence.md；不能以代理出口更新DuckDNS，不能用路由器本机curl代替手机5G验收；保留PKR/Fedora原生代理及路由器旁路。
§
本机 flatpak 安装大 runtime 会卡死：下载走 IPv6 到 flathub CDN(2a04:4e42:68::347) 后持续 0 字节增长，curl -4/aria2c 同源却有 1.3MB/s。装 app 用 `env -u http_proxy -u https_proxy -u HTTP_PROXY -u HTTPS_PROXY -u all_proxy -u ALL_PROXY flatpak install -y --noninteractive --system --no-deps flathub <app>`（--no-deps 跳过用不到的 nvidia runtime；remote 冲突时--system必填）。KeePassXC/Thunderbird 已在 2026-10-24 用 AppImage+Flatpak(--no-deps) 装通，勿再重跑安装。
§
Matrix公网入口(2026-10-24)：http://charlie1990.duckdns.org:24804 已通，经路由器DNAT 24804->192.168.123.71:24804，frpc映射fedora-matrix-8008本地8008->远程24804，Synapse正常。DuckDNS的80/443未映射，https://charlie1990.duckdns.org 当前不通。
§
冷记忆检索（本条不在上面即按需查）：分类库 `~/.hermes/memories/categories/*.md`[ops(18) user-preference(9) network(7)]；语义检索 `~/.hermes/memories/vector_memory.db`；归档 `archive/<id>.json`；会话史用 session_search。
