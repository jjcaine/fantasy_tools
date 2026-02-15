"""Data Refresh screen — runs the 5-step collection pipeline with live logging."""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

from textual.app import ComposeResult
from textual.widgets import Button, Footer, Header, RichLog, Static
from textual import work

from src.tui.screens.base import BaseScreen
from src.tui.screens.help import HelpScreen

DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data"

DATA_FILES = [
    ("a10_standings.json", "NCAA Standings"),
    ("a10_players.json", "Player Stats"),
    ("a10_schedule.json", "Schedule"),
    ("fantrax_rosters.json", "FanTrax Rosters"),
    ("fantrax_all_matchups.json", "Matchup History"),
    ("fantrax_free_agents.json", "Free Agents"),
]

HELP_TEXT = """\
Data Refresh Screen

Runs the full data collection pipeline:
  1. NCAA standings from NCAA API
  2. Player box scores (incremental)
  3. A-10 schedule scan
  4. FanTrax league data (rosters, matchups, FAs)
  5. Data validation checks

After collection, data quality checks run automatically:
  - Player data quality (games, stats completeness)
  - Roster matching quality (FanTrax → NCAA)
  - Matchup data quality (period coverage)
  - Schedule data quality (A-10 teams scheduled)

Keybindings:
  Enter  Start collection
  ?      Show this help
  Esc    Return to previous screen

Notes:
  - FanTrax step requires valid credentials in .env
  - A failure in one step does not block the rest
  - Data freshness shows file modification times
"""


class DataRefreshScreen(BaseScreen):
    """Screen for refreshing cached data files."""

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(self._freshness_text(), id="data-freshness")
        yield Button("Start Collection", id="start-collection", variant="primary")
        yield RichLog(highlight=True, markup=True, id="refresh-log")
        yield Footer()

    def _freshness_text(self) -> str:
        parts = []
        for filename, label in DATA_FILES:
            path = DATA_DIR / filename
            if path.exists():
                mtime = datetime.fromtimestamp(os.path.getmtime(path))
                age = datetime.now() - mtime
                if age.days > 0:
                    age_str = f"{age.days}d ago"
                elif age.seconds > 3600:
                    age_str = f"{age.seconds // 3600}h ago"
                else:
                    age_str = f"{age.seconds // 60}m ago"
                parts.append(f"{label}: {age_str}")
            else:
                parts.append(f"{label}: [red]missing[/red]")
        return " | ".join(parts)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "start-collection":
            event.button.disabled = True
            self._run_collection()

    @work(exclusive=True, thread=True)
    def _run_collection(self) -> None:
        log = self.query_one("#refresh-log", RichLog)

        def log_fn(msg: str) -> None:
            self.app.call_from_thread(log.write, msg)

        steps = [
            ("NCAA Standings", self._step_ncaa_standings),
            ("Player Stats (Box Scores)", self._step_player_stats),
            ("A-10 Schedule", self._step_schedule),
            ("FanTrax Data", self._step_fantrax),
            ("Validation", self._step_validation),
        ]

        log_fn("[bold]Starting data collection...[/bold]")
        for name, step_fn in steps:
            log_fn(f"\n[bold blue]>>> {name}[/bold blue]")
            try:
                step_fn(log_fn)
                log_fn(f"[green]  ✓ {name} complete[/green]")
            except Exception as e:
                log_fn(f"[red]  ✗ {name} failed: {e}[/red]")

        log_fn("\n[bold green]Collection finished.[/bold green]")

        # Run data quality checks
        log_fn("\n[bold blue]>>> Data Quality Checks[/bold blue]")
        self._run_quality_checks(log_fn)

        self.app.call_from_thread(self._on_collection_done)

    def _run_quality_checks(self, log_fn) -> None:
        """Run all data quality checks and log results."""
        try:
            from src.fantasy_math import (
                load_a10_players, load_fantrax_rosters, load_schedule,
                load_matchup_history, build_player_lookup,
                run_player_data_quality, run_roster_match_quality,
                run_matchup_data_quality, run_schedule_data_quality,
            )
        except ImportError as e:
            log_fn(f"[red]  Could not import quality checks: {e}[/red]")
            return

        checks = []

        try:
            players = load_a10_players()
            report = run_player_data_quality(players)
            checks.append(("Player Data", report))
        except Exception as e:
            log_fn(f"[red]  Player data quality check failed: {e}[/red]")

        try:
            players = load_a10_players()
            rosters = load_fantrax_rosters()
            lookup = build_player_lookup(players)
            report = run_roster_match_quality(rosters, players, lookup)
            checks.append(("Roster Match", report))
        except Exception as e:
            log_fn(f"[red]  Roster match quality check failed: {e}[/red]")

        try:
            matchups = load_matchup_history()
            report = run_matchup_data_quality(matchups)
            checks.append(("Matchup Data", report))
        except Exception as e:
            log_fn(f"[red]  Matchup data quality check failed: {e}[/red]")

        try:
            schedule = load_schedule()
            report = run_schedule_data_quality(schedule)
            checks.append(("Schedule", report))
        except Exception as e:
            log_fn(f"[red]  Schedule data quality check failed: {e}[/red]")

        for name, report in checks:
            if report.all_passed:
                log_fn(f"[green]  ✓ {name}: all checks passed[/green]")
            else:
                log_fn(f"[yellow]  ⚠ {name}: {report.summary}[/yellow]")
                for check in report.checks:
                    status = "[green]✓[/green]" if check["passed"] else "[red]✗[/red]"
                    log_fn(f"    {status} {check['name']}: {check.get('detail', '')}")

    def _on_collection_done(self) -> None:
        btn = self.query_one("#start-collection", Button)
        btn.disabled = False
        freshness = self.query_one("#data-freshness", Static)
        freshness.update(self._freshness_text())
        self.notify("Data collection complete", severity="information")

    def _step_ncaa_standings(self, log_fn):
        from src.collect_data import collect_ncaa_standings
        collect_ncaa_standings(log=log_fn)

    def _step_player_stats(self, log_fn):
        from src.collect_data import collect_player_stats
        collect_player_stats(log=log_fn)

    def _step_schedule(self, log_fn):
        from src.schedule_scanner import scan_all_periods
        scan_all_periods()
        log_fn("  Schedule scan complete")

    def _step_fantrax(self, log_fn):
        from src.collect_data import collect_fantrax_data
        collect_fantrax_data(log=log_fn)

    def _step_validation(self, log_fn):
        from src.validation import run_validation
        run_validation()
        log_fn("  Validation complete")

    def action_show_help(self) -> None:
        self.app.push_screen(HelpScreen("Data Refresh Help", HELP_TEXT))
