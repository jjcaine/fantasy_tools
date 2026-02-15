"""Reusable help modal overlay for TUI screens."""

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Static


class HelpScreen(ModalScreen[None]):
    """A modal help overlay that closes on Escape or button click."""

    BINDINGS = [("escape", "dismiss", "Close")]

    DEFAULT_CSS = """
    HelpScreen {
        align: center middle;
    }
    #help-dialog {
        width: 60;
        height: auto;
        max-height: 80%;
        border: thick $primary;
        background: $surface;
        padding: 1 2;
    }
    #help-title {
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
    }
    #help-close {
        width: 100%;
        margin-top: 1;
    }
    """

    def __init__(self, title: str, body: str) -> None:
        super().__init__()
        self._title = title
        self._body = body

    def compose(self) -> ComposeResult:
        with Vertical(id="help-dialog"):
            yield Static(self._title, id="help-title")
            yield Static(self._body)
            yield Button("Close [Esc]", id="help-close", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "help-close":
            self.dismiss()
