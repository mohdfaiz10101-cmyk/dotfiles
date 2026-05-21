---
name: Hyprland配置错误诊断规则
description: 遇到Hyprland配置报错时必须先用hyprctl configerrors，禁止盲猜语法
type: feedback
---

遇到 Hyprland 配置错误（红色覆盖层 / CHyprError）时，MUST 先执行：
```
hyprctl configerrors
```
该命令直接返回文件名、行号、具体错误原因，无需猜测。

**Why:** 之前盲猜语法三次才修对（windowrule→windowrulev2→windowrule块格式），浪费了大量来回。hyprctl configerrors 第一次就能给出准确信息。

**How to apply:** 任何涉及 hyprland.conf 修改报错的场景，第一步就是 `hyprctl configerrors`，输出结果决定下一步操作。

---

## Hyprland windowrule 语法版本对照（截至 0.54）

| 版本 | 语法 | 状态 |
|------|------|------|
| <0.42 | `windowrulev2 = float, class:^(name)$` | ❌ 废弃 |
| 0.42-0.53 | `windowrule = float, class:^(name)$` | ❌ 废弃 |
| 0.54+ | 块语法（见下） | ✅ 当前 |

```
windowrule {
  name = rule-name       # 必须第一行，作为标识符
  match:class = ^(name)$
  float = 1
  no_anim = 1            # 注意 no_anim 不是 noanim
}
```

- 诊断命令：`hyprctl configerrors`
- 配置修改后：`hyprctl reload` → `hyprctl configerrors`（输出为空=无错误）
