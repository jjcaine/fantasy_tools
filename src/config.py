"""Load league configuration from config.toml with hardcoded fallbacks."""

from datetime import date
from pathlib import Path

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # Python < 3.11

_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.toml"

_FALLBACK_PERIODS: dict[int, tuple[date, date]] = {
    14: (date(2026, 2, 9), date(2026, 2, 15)),
    15: (date(2026, 2, 16), date(2026, 2, 22)),
    16: (date(2026, 2, 23), date(2026, 3, 1)),
    17: (date(2026, 3, 2), date(2026, 3, 8)),
}

_FALLBACK_CATEGORIES = [
    "AdjFG%", "3PTM", "FT%", "PTS", "REB", "AST", "ST", "BLK", "TO"
]

_FALLBACK_TEAM = "Sick-Os Revenge"
_FALLBACK_GP_MAX = 15


def _load_config() -> dict:
    """Load and return the parsed config.toml, or empty dict if missing."""
    try:
        with open(_CONFIG_PATH, "rb") as f:
            return tomllib.load(f)
    except FileNotFoundError:
        return {}


def get_periods() -> dict[int, tuple[date, date]]:
    """Return mapping of period number to (start_date, end_date)."""
    cfg = _load_config()
    periods_cfg = cfg.get("periods", {})
    if not periods_cfg:
        return dict(_FALLBACK_PERIODS)
    result: dict[int, tuple[date, date]] = {}
    for key, val in periods_cfg.items():
        period_num = int(key)
        start = date.fromisoformat(val["start"])
        end = date.fromisoformat(val["end"])
        result[period_num] = (start, end)
    return result


def get_gp_max(period: int | None = None) -> int:
    """Return GP max for a period (period-specific override or default)."""
    cfg = _load_config()
    league = cfg.get("league", {})
    default = league.get("default_gp_max", _FALLBACK_GP_MAX)
    if period is not None:
        periods_cfg = cfg.get("periods", {})
        period_cfg = periods_cfg.get(str(period), {})
        return period_cfg.get("gp_max", default)
    return default


def get_my_team() -> str:
    """Return the user's team name."""
    cfg = _load_config()
    return cfg.get("league", {}).get("team", _FALLBACK_TEAM)


def get_categories() -> list[str]:
    """Return the list of scoring categories."""
    cfg = _load_config()
    return cfg.get("league", {}).get("categories", list(_FALLBACK_CATEGORIES))
