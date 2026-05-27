import type { Plugin } from "@opencode-ai/plugin"
import { readFile, access } from "fs/promises"
import { join } from "path"

export const CompactionEnhanced: Plugin = async ({ directory }) => {
  return {
    "experimental.session.compacting": async (input, output) => {
      // 收集 NixOS 上下文
      const nixosContext: string[] = []
      
      try {
        // 检查 /etc/nixos/CONTEXT.md
        await access("/etc/nixos/CONTEXT.md")
        const contextContent = await readFile("/etc/nixos/CONTEXT.md", "utf-8")
        nixosContext.push("## NixOS 系统上下文")
        nixosContext.push(contextContent.substring(0, 2000)) // 限制长度
      } catch {
        nixosContext.push("## NixOS 系统上下文 (未找到 CONTEXT.md)")
      }

      // 收集 memory/ 摘要
      const memoryContext: string[] = []
      const memoryPath = "/home/charlie/.claude/projects/-home-charlie/memory"
      
      try {
        const memoryFiles = ["MEMORY.md", "lessons-learned.md", "nixos-config.md", "troubleshooting.md"]
        for (const file of memoryFiles) {
          try {
            const content = await readFile(join(memoryPath, file), "utf-8")
            // 取最近 5 条记录
            const lines = content.split("\n").filter(l => l.trim())
            const recentLines = lines.slice(-10).join("\n")
            memoryContext.push(`### ${file}`)
            memoryContext.push(recentLines)
          } catch {
            // 文件不存在，跳过
          }
        }
      } catch (err) {
        memoryContext.push("## 记忆系统 (无法读取)")
      }

      // 注入到压缩上下文
      output.context.push(
        "## 系统上下文 (压缩时自动注入)",
        "以下信息应保留在压缩后的上下文中：",
        "",
        ...nixosContext,
        "",
        "## 近期记忆",
        "最近的操作和教训：",
        "",
        ...memoryContext,
        "",
        "## 重要提醒",
        "- 不要重复已经完成的操作",
        "- 保留跨会话待办事项 (pending-tasks.md)",
        "- 架构决策应持久化",
        "- 安全相关配置变更必须记录"
      )
    }
  }
}