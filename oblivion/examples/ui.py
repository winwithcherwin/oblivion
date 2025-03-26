from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Input, Static
from textual.containers import Container, Vertical, ScrollableContainer
from textual.reactive import reactive
from rich.panel import Panel

class ChatBubble(Static):
    def __init__(self, sender: str, message: str, style: str = "white"):
        content = f"[{style}]{sender}:[/] {message}"
        super().__init__(content, expand=False)

class LogOutput(ScrollableContainer):
    def __init__(self):
        super().__init__()
        self.lines = []
    def write(self, line: str):
        self.lines.append(line)
        self.update("\n".join(self.lines))
        self.scroll_end(animate=False)

class ObChat(App):
    CSS_PATH = None
    BINDINGS = [
        ("ctrl+c", "quit", "Quit"),
        ("f2", "switch_client", "Switch Client"),
    ]
    input_text: reactive[str] = reactive("")

    def compose(self) -> ComposeResult:
        yield Header()
        with Container():
            with Vertical():
                self.chat_window = ScrollableContainer()
                yield self.chat_window
                self.log_output = LogOutput()
                self.log_output.styles.height = 10
                yield self.log_output
        yield Input(placeholder="Type a command...", id="chat_input")
        yield Footer()

    def on_mount(self) -> None:
        self.input = self.query_one("#chat_input", Input)
        # focus is now synchronous in Textual 2.x
        self.input.focus()
        self.chat("oblivion", "Welcome to Oblivion CLI. How can I help?")

    def chat(self, sender: str, message: str, style: str = "cyan"):
        bubble = ChatBubble(sender, message, style)
        self.chat_window.mount(bubble)
        self.chat_window.scroll_end(animate=False)

    async def on_input_submitted(self, message: Input.Submitted) -> None:
        prompt = message.value.strip()
        if not prompt:
            return
        self.input.value = ""
        self.chat("you", prompt, style="green")
        await self.process_prompt(prompt)

    async def process_prompt(self, prompt: str):
        from asyncio import sleep
        self.chat("oblivion", f"Processing: '{prompt}'...", style="cyan")
        for i in range(5):
            self.log_output.write(f"[task] Step {i+1}/5: doing something...")
            await sleep(0.4)
        self.chat("oblivion", "Done. Node wg-04 provisioned successfully.", style="cyan")
        self.log_output.write("[✓] Complete.")

if __name__ == "__main__":
    ObChat().run()

