- [2026-04-25] [GLM] 场景：用户偏好 — 创建agent/工作流前必须先搜索互联网已有开源方案，推荐给用户参考后再讨论决策。用户明确说"不要闭门造车"。触发信号：创建agent、设计工作流、选型技术方案。写入 CLAUDE.md AGENT_RESEARCH_FIRST 死规则。- [2026-04-25] [GLM-Z-Flash] 场景：plasmashell崩溃导致任务栏消失。根因：opencode job(marketing-scan/discord-butler/glm-knowledge-writer)连续失败触发大量进程，内存压力致plasmashell崩溃。修复：`systemctl --user restart plasma-plasmashell`。预防：Plasma 6 已有自动重启机制但不够快，可通过 plasma-panel-restart.timer 定时检查。
- [2026-04-25] [Sonnet] 场景：Ghostty终端整个窗口出现一堆数字乱码（第2次，情况3=全窗口）。症状：整个窗口到处都是数字。根因：**不是GPU渲染问题**，日志明确显示 `Pango: failed to create cairo scaled font, offending font 'Noto Sans 81.75', file not found`。是 Ghostty 1.3.1 + libadwaita 请求了不存在的大小变体字体。**GSK_RENDERER=ngl 无效，renderer=software 无效**。正确修复：升级 Ghostty 到 1.4+（修复了 GTK 字体问题），或降级 noto-fonts。临时方案：先用 Konsole 替代。配置：`~/.config/ghostty/config`，快捷命令：`kill-ghostty`。

### 会话摘要 [2026-04-25] [Sonnet/自动]
- 对话轮次: 128 | 被纠正: 1次
  - 用户纠正: 】我不要换模型。你执行1和三。但是以前约束过 没生效吗。

### 会话摘要 [2026-04-25] [Sonnet/自动]
- 对话轮次: 130 | 被纠正: 1次
  - 用户纠正: 】我不要换模型。你执行1和三。但是以前约束过 没生效吗。

### 会话摘要 [2026-04-25] [Sonnet/自动]
- 对话轮次: 128 | 被纠正: 1次
  - 用户纠正: 】我不要换模型。你执行1和三。但是以前约束过 没生效吗。

### 会话摘要 [2026-04-25] [Sonnet/自动]
- 对话轮次: 117 | 被纠正: 1次
  - 用户纠正: 】我不要换模型。你执行1和三。但是以前约束过 没生效吗。

### 会话摘要 [2026-04-25] [Sonnet/自动]
- 对话轮次: 110 | 被纠正: 1次
  - 用户纠正: 】我不要换模型。你执行1和三。但是以前约束过 没生效吗。
