"""Offline (mocked, no network) coverage for src/ingest/underdog.py's sport
filter. Deliberately a separate file from test_ingest_underdog.py, whose
module-level `pytestmark = pytest.mark.live` would otherwise also exclude
this test from the default suite even though it never touches the network.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from src.ingest.underdog import ingest_props

_FAKE_PAYLOAD = {
    "players": [
        {"id": "p1", "first_name": "Nfl", "last_name": "Player", "sport_id": "NFL"},
        {"id": "p2", "first_name": "Cfb", "last_name": "Player", "sport_id": "CFB"},
    ],
    "appearances": [
        {"id": "a1", "player_id": "p1"},
        {"id": "a2", "player_id": "p2"},
    ],
    "over_under_lines": [
        {
            "over_under": {
                "category": "player_prop",
                "appearance_stat": {"appearance_id": "a1", "display_stat": "Passing Yards"},
            },
            "stat_value": 250.5,
            "options": [
                {"choice": "higher", "american_price": -110},
                {"choice": "lower", "american_price": -110},
            ],
        },
        {
            "over_under": {
                "category": "player_prop",
                "appearance_stat": {"appearance_id": "a2", "display_stat": "Rushing Yards"},
            },
            "stat_value": 80.5,
            "options": [
                {"choice": "higher", "american_price": -115},
                {"choice": "lower", "american_price": -105},
            ],
        },
    ],
}


async def test_ncaaf_rows_reach_resolution_instead_of_being_filtered_out(db):
    """Regression test for the sport filter in ingest_props: before
    supporting NCAAF, `if row["sport"] == "nfl"` silently dropped every CFB
    line before it ever reached resolve_player. With neither player seeded,
    both the NFL and the CFB line must now be attempted and parked - 1
    parked would mean the CFB row is still being filtered out upstream."""
    with patch(
        "src.ingest.underdog.get_over_under_lines",
        new=AsyncMock(return_value=_FAKE_PAYLOAD),
    ):
        written, parked = await ingest_props(db)

    assert written == 0, "neither player is seeded, so nothing should resolve"
    assert parked == 2, "both the NFL and the NCAAF line must be attempted, not just one"
