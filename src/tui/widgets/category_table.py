"""Reusable category comparison DataTable for matchup display."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import DataTable

from src.fantasy_math import MatchupResult, PCT_CATS


def _fmt_val(category: str, value: float) -> str:
    """Format a category value for display."""
    if category in PCT_CATS:
        return f"{value:.3f}"
    return f"{value:.1f}"


class CategoryComparisonTable(Widget):
    """A DataTable showing 9-category H2H comparison between two teams."""

    DEFAULT_CSS = """
    CategoryComparisonTable {
        height: auto;
    }
    """

    def __init__(self, result: MatchupResult | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._result = result

    def compose(self) -> ComposeResult:
        yield DataTable(id="cat-table")

    def on_mount(self) -> None:
        table = self.query_one("#cat-table", DataTable)
        table.add_columns("Category", "Ours", "Theirs", "Winner", "Margin")
        if self._result is not None:
            self.update_result(self._result)

    def update_result(self, result: MatchupResult) -> None:
        """Populate or refresh the table with a new MatchupResult."""
        self._result = result
        table = self.query_one("#cat-table", DataTable)
        table.clear()
        for comp in result.comparisons:
            if comp.winner == "A":
                winner = f"[green]{result.team_a}[/green]"
                style = "green"
            elif comp.winner == "B":
                winner = f"[red]{result.team_b}[/red]"
                style = "red"
            else:
                winner = "[yellow]Tie[/yellow]"
                style = "yellow"

            our_val = _fmt_val(comp.category, comp.team_a_val)
            their_val = _fmt_val(comp.category, comp.team_b_val)
            margin = _fmt_val(comp.category, abs(comp.margin))

            cat_label = f"[{style}]{comp.category}[/{style}]"
            table.add_row(cat_label, our_val, their_val, winner, margin)
