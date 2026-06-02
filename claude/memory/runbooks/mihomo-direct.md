# Mihomo DIRECT Runbook

适用场景:
- 健康分数里显示代理走 `DIRECT`
- `9091` 可达，但选路异常

检查步骤:
1. `curl -s http://127.0.0.1:9091/proxies`
2. 检查 `GLOBAL.now`
3. 检查节点 `alive` 数量
4. 检查 DNS 与规则是否过于简化

修复方向:
- 补 DNS 控制项
- 补更细的规则分流
- 必要时切换到稳定节点组
