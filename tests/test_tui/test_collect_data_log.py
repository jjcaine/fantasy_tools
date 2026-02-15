"""Tests for collect_data.py log parameter — Phase 1 completion criteria."""

from unittest.mock import patch, MagicMock

from src.collect_data import collect_ncaa_standings


def test_collect_ncaa_standings_accepts_log():
    """collect_ncaa_standings(log=mock_log) invokes mock_log."""
    mock_log = MagicMock()
    with patch("src.collect_data.ncaa_client.get_standings", return_value=[{"team": "Dayton"}]):
        with patch("src.collect_data.save_json"):
            collect_ncaa_standings(log=mock_log)
    assert mock_log.call_count >= 1
    # Check it logged something about standings
    calls = [str(c) for c in mock_log.call_args_list]
    assert any("standings" in c.lower() or "Collecting" in c for c in calls)


def test_collect_ncaa_standings_defaults_to_print(capsys):
    """Without log, collect_ncaa_standings uses print (default behavior)."""
    with patch("src.collect_data.ncaa_client.get_standings", return_value=[]):
        with patch("src.collect_data.save_json"):
            collect_ncaa_standings()
    captured = capsys.readouterr()
    assert "standings" in captured.out.lower()
