import type { Plugin } from "@opencode-ai/plugin"

export const NotifyKDE: Plugin = async ({ $ }) => {
  return {
    "session.idle": async ({ session }) => {
      // 会话完成时发送 KDE 通知
      try {
        await $`kdialog --title "OpenCode" --msgbox "会话完成: ${session.task || '任务完成'}"`
      } catch {
        // kdialog 不可用，静默失败
      }
    },

    "session.error": async ({ session, error }) => {
      // 会话出错时发送 KDE 通知
      try {
        await $`kdialog --title "OpenCode 错误" --error "会话错误: ${error?.message || '未知错误'}"`
      } catch {
        // 静默失败
      }
    },

    "tool.execute.after": async (input, output) => {
      // 长时间运行的工具完成后通知
      if (input.tool === "bash" && output.duration > 10000) { // 10秒以上
        const cmd = input.args.command?.substring(0, 50) || "命令"
        try {
          await $`notify-send --app-name=OpenCode "命令完成" "${cmd} (${Math.round(output.duration / 1000)}s)"`
        } catch {
          // 静默失败
        }
      }
    },

    "todo.updated": async ({ todos }) => {
      // 任务状态变更时通知
      const completed = todos.filter(t => t.status === "completed").length
      const inProgress = todos.filter(t => t.status === "in_progress").length
      
      if (completed > 0 || inProgress === 0) {
        try {
          await $`notify-send --app-name=OpenCode "任务进度" "已完成: ${completed} | 进行中: ${inProgress}"`
        } catch {
          // 静默失败
        }
      }
    }
  }
}