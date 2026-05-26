# OpenCode Global Rules (compiled from CLAUDE.md)

<!-- compiled: 2026-05-25 21:32 | sections: 22/16 -->

## 规则分层说明
- **L1**（本文件）：始终生效的核心规则，~15 条
- **L2**（rules-secondary.md 上半）：会话启动 + 任务执行时加载
- **L3**（rules-secondary.md 下半）：特定场景查询时参考

## 语言规则
- MUST 始终使用中文回复，代码注释可用英文
- 系统通知（notify-send、Telegram、日志）MUST 中文，禁止英文状态码

## 输出格式（R1-R9）
- **R1** 零废话：禁止寒暄前缀、第一人称动作描述、过渡句
- **R2** 指令式语态：`动作 → 结果 → 下一步`
- **R3** 状态标记：只用 `[OK]` `[FAIL]` `[SKIP]`
- **R4** 紧凑布局：段落不超3行
- **R5** 加粗节制：每段最多1个
- **R6** 代码限制：单块≤15行
- **R7** 并行执行：能并行一定并行
- **R8** 装饰预算：≤10%
- **R9** 思考总结：每次 think 结束后 MUST 输出 `[思考] {一句话结论}`，即使 thinking 被折叠也能看到推理结果

**模型标识**（仅首行）：`▸ {emoji} {模型} | {路由原因}`
**已执行标记**：修改文件/重启服务 → `► 标记`
**回复结尾**：有文件写入 → `► 写入: 文件名` | 纯对话 → 无尾注

## NTFS 封杀（NTFS_BAN — 死规则）
禁止在 NTFS 上运行：npm/bun/cargo/git clone/Docker build
检测：`df -T . | grep -i ntfs` → 命中则拒绝

## 磁盘分配规则（DISK_ALLOCATION — 死规则）
| 分区 | 用途 | 限制 |
|------|------|


## 记忆系统状态（自动注入 2026-05-26 12:17）
| 指标 | 值 |
|------|-----|
| KG实体/关系 | N/A / N/A |
| Letta MCP | active |
| lessons-learned条目 | 21 |
| 历史会话数 | 0
0 |

### 高频主题（最近）


> 以上由 memory-bootstrap.sh 自动注入，每小时更新

---
