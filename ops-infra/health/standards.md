# Ops-Infra 健康检查标准

## 深度等级定义

| Level | 名称 | 检测内容 | 示例 | 故障检测能力 |
|-------|------|---------|------|-------------|
| L0 | 进程存活 | systemctl is-active / docker ps | 服务是否在运行 | 进程崩溃 |
| L1 | 端口监听 | ss -tlnp / netstat | 端口是否绑定 | 启动失败/端口冲突 |
| L2 | HTTP响应 | curl -s http://host:port/health | API是否返回200 | 应用层崩溃 |
| L3 | 数据完整性 | GET内容验证(非空/有预期字段) | 数据是否可读 | 数据库/缓存故障 |
| L4 | 事务完整性 | 写→读→删完整链路 | API是否真正工作 | 静默故障(今天Letta坑) |

## 健康评分公式

```
score = (passed_levels / tested_levels) * 100
```

- 100分: L0-L4全部通过
- 80分: 缺L4但L0-L3通过
- 60分: L0-L2通过
- 40分: L0-L1通过
- 20分: 仅L0通过
- 0分: 进程down

## 评分等级

| 分数 | 等级 | 含义 |
|------|------|------|
| 100 | 🟢 优秀 | 全链路健康 |
| 75-99 | 🟡 良好 | 核心功能正常 |
| 50-74 | 🟠 警告 | 部分降级，需关注 |
| 25-49 | 🔴 危险 | 严重降级，立即修复 |
| 0-24 | 💀 死亡 | 服务不可用 |

## 新增服务检查清单

1. 复制 `template.sh` → `{service}-health.sh`
2. 实现 `check_l0` → `check_l4` 函数
3. 注册到 `~/.local/bin/`
4. 添加到 `scorer.sh` 的 SERVICE_LIST
5. 验证: `scorer.sh --service {service}`