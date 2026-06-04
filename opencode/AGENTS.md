# OpenCode Global Rules (compiled from CLAUDE.md)

<!-- compiled: 2026-06-04 16:27 -->

## 语言规则
- MUST 始终使用中文回复，代码注释可用英文
- 系统通知（notify-send、Telegram、日志）MUST 中文，禁止英文状态码

## 输出格式
- **R1** 零废话：禁止寒暄前缀、第一人称动作描述、过渡句
- **R2** 指令式语态：`动作 → 结果 → 下一步`
- **R3** 状态标记：只用 `[OK]` `[FAIL]` `[SKIP]`
- **R4** 紧凑布局：段落不超3行
- **R5** 加粗节制：每段最多1个
- **R6** 代码限制：单块≤15行
- **R7** 并行执行：能并行一定并行
- **R8** 装饰预算：≤10%
- **R9** 思考总结：每次 think 结束后 MUST 输出 `[思考] {一句话结论}`，即使 thinking 被折叠也能看到推理结果

## NixOS 专项
- 路径禁令：NEVER 硬编码 `/nix/store/xxx/bin/xxx`，用 `/run/current-system/sw/bin/xxx`
- NEVER TOUCH：不得随意修改 `/etc/nixos/`，除非用户明确要求且先验证
- **REBUILD_SAFE（死规则）**：rebuild 前 MUST 执行 `nixos-rebuild-safe`（构建VM→测试→通过才写boot），禁止直接 `switch` 后 `reboot`
- 常用命令：

## 自动验证
- 涉及第三方工具/API 先 WebSearch 验证最新用法
- **搜索年份**：MUST 包含当前年份（2026）
- 绝对禁止打开 `docs.litellm.ai/docs/providers`
- 修改服务代码后 MUST：重启 → curl测试 → 检查日志 → 验证前端

## 工作模式
- 批量并行 | 自主决策先做后报告 | 复杂问题 think hard
- NixOS/Flake 问题必须先 Read 实际配置
- 出错不重复同样方法，连续失败2次 /clear

---
Source: ~/CLAUDE.md | Auto-compiled