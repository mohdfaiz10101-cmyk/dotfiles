"""
macg TUI 演示 — 运行看效果
用法：python3 macg_tui_demo.py
退出：q 或 Ctrl+C
"""
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Input, RichLog, Static, Label
from textual.containers import Horizontal, Vertical, ScrollableContainer
from textual.reactive import reactive
from rich.text import Text
from rich.panel import Panel
from rich.syntax import Syntax
import asyncio, time

DEMO_MESSAGES = [
    ("你", "查看一下服务状态", "user"),
    ("Supervisor", "→ 路由: GLM | 系统感知查询", "supervisor"),
    ("GLM", """[OK] LiteLLM   localhost:4000  在线
[OK] Letta     localhost:8283  在线
[OK] AGI-GW    localhost:9900  在线
[--] Paperclip localhost:3100  已停用""", "glm"),
    ("你", "帮我重构 macg.py 的 supervisor_node", "user"),
    ("Supervisor", "→ 路由: Claude | 代码重构任务", "supervisor"),
    ("Claude", """def supervisor_node(state, model) -> AgentState:
    \"\"\"路由决策节点\"\"\"
    last = get_last_user_msg(state)
    decision = model.invoke([
        SystemMessage(SUPERVISOR_PROMPT),
        HumanMessage(last.content)
    ])
    route, reason = parse_decision(decision.content)
    return {**state, "next": route, "route_reason": reason}""", "claude"),
]

class MessageBubble(Static):
    def __init__(self, role: str, content: str, kind: str):
        self.role = role
        self.content = content
        self.kind = kind
        super().__init__()

    def render(self):
        colors = {
            "user": "bold white on #1a1a2e",
            "supervisor": "bold yellow",
            "glm": "bold cyan",
            "claude": "bold magenta",
        }
        role_labels = {
            "user": "▸ 你",
            "supervisor": "⚡ Supervisor",
            "glm": "🐉 GLM-5",
            "claude": "🧠 Claude",
        }
        label = role_labels.get(self.kind, self.role)
        color = colors.get(self.kind, "white")

        if self.kind == "claude" and "def " in self.content:
            from rich.syntax import Syntax
            return Panel(
                Syntax(self.content, "python", theme="monokai", line_numbers=False),
                title=f"[{color}]{label}[/]",
                border_style="magenta",
            )
        elif self.kind == "glm":
            return Panel(
                Text(self.content),
                title=f"[{color}]{label}[/]",
                border_style="cyan",
            )
        elif self.kind == "supervisor":
            return Text(f"  [{color}]{label}: {self.content}[/]")
        else:
            return Panel(
                Text(self.content),
                title=f"[{color}]{label}[/]",
                border_style="white",
            )


class MacgTUI(App):
    CSS = """
    Screen {
        background: #0d1117;
    }
    #sidebar {
        width: 22;
        border: solid #30363d;
        background: #161b22;
        padding: 1;
    }
    #chat-area {
        border: solid #30363d;
        background: #0d1117;
    }
    #input-bar {
        height: 3;
        border: solid #30363d;
        background: #161b22;
    }
    #status-bar {
        height: 1;
        background: #21262d;
        color: #8b949e;
        padding: 0 1;
    }
    Input {
        background: #0d1117;
        border: none;
        color: white;
    }
    MessageBubble {
        margin: 0 1;
        padding: 0;
    }
    #sidebar-title {
        color: #58a6ff;
        text-style: bold;
    }
    """

    BINDINGS = [("q", "quit", "退出"), ("ctrl+l", "clear", "清空")]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal():
            with Vertical(id="sidebar"):
                yield Label("MACG 系统", id="sidebar-title")
                yield Static("─" * 18)
                yield Static("🐉 GLM-5    [green]●[/]")
                yield Static("🧠 Claude  [green]●[/]")
                yield Static("🔧 Letta   [green]●[/]")
                yield Static("⚡ LiteLLM [green]●[/]")
                yield Static("─" * 18)
                yield Static("[yellow]会话[/]: default")
                yield Static("[cyan]路由[/]: GLM优先")
                yield Static("─" * 18)
                yield Static("[dim]今日操作: 12次[/]")
                yield Static("[dim]GLM: 9 Claude: 3[/]")
            with Vertical():
                yield ScrollableContainer(id="chat-area")
                with Horizontal(id="input-bar"):
                    yield Input(placeholder="输入消息... (q退出)", id="input")
        yield Static("▸ MACG v2  |  Letta[OK]  LiteLLM[OK]  |  GLM免费模式", id="status-bar")
        yield Footer()

    async def on_mount(self):
        self.title = "MACG — Multi-Agent CLI"
        self.sub_title = "GLM + Claude + Letta"
        # 播放演示消息
        asyncio.create_task(self._play_demo())

    async def _play_demo(self):
        await asyncio.sleep(0.5)
        chat = self.query_one("#chat-area")
        for role, content, kind in DEMO_MESSAGES:
            bubble = MessageBubble(role, content, kind)
            await chat.mount(bubble)
            chat.scroll_end(animate=False)
            await asyncio.sleep(0.8 if kind != "user" else 0.3)

    async def on_input_submitted(self, event: Input.Submitted):
        if not event.value.strip():
            return
        chat = self.query_one("#chat-area")
        await chat.mount(MessageBubble("你", event.value, "user"))
        chat.scroll_end(animate=False)
        event.input.value = ""
        # 模拟路由响应
        await asyncio.sleep(0.3)
        await chat.mount(MessageBubble("Supervisor", "→ 路由: GLM | 分析中...", "supervisor"))
        chat.scroll_end(animate=False)

    def action_clear(self):
        self.query_one("#chat-area").remove_children()

if __name__ == "__main__":
    MacgTUI().run()
