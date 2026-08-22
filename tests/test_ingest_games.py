"""resolve_game(): the single reconciliation layer for Game identity.

nflverse and ESPN each find-or-create a Game keyed on their own external id
with no reconciliation between them. This proves the fix: an nflverse-seeded
row for a real fixture is found and backfilled by a later ESPN poll for the
SAME fixture (same team pair, kickoff within 24h), rather than a duplicate
Game being created.
"""

from __future__ import annotations

from sqlalchemy import func, select

from src.ingest.espn import _upsert_event
from src.ingest.nflverse import ingest_games
from src.models.facts import Game
from src.models.governance import IngestionRun


async def test_espn_converges_onto_an_nflverse_seeded_game(db):
    # Seed via the nflverse path only - real 2025 season data, same fixture
    # used to pin the Eastern->UTC kickoff fix (test_ingest_nflverse.py):
    # 2025_01_DAL_PHI, DAL @ PHI, kickoff 2025-09-05T00:20:00Z.
    await ingest_games(db, seasons=[2025])

    seeded = await db.scalar(
        select(Game).where(Game.nflverse_game_id == "2025_01_DAL_PHI")
    )
    assert seeded is not None
    assert seeded.espn_event_id is None, "test setup: no ESPN id yet"
    assert seeded.game_time is not None

    before = await db.scalar(select(func.count()).select_from(Game))

    # Now run the ESPN path for the same real fixture - same team pair, a
    # kickoff well within the 24h matching window (identical instant here,
    # expressed as ESPN's own UTC ISO-8601-with-Z format).
    event = {
        "id": "espn-dal-phi-2025-opener",
        "date": "2025-09-05T00:20Z",
        "season": {"year": 2025},
        "week": {"number": 1},
        "competitions": [
            {
                "status": {"type": {"state": "pre"}},
                "competitors": [
                    {
                        "homeAway": "home",
                        "score": "0",
                        "team": {"displayName": "Philadelphia Eagles"},
                    },
                    {
                        "homeAway": "away",
                        "score": "0",
                        "team": {"displayName": "Dallas Cowboys"},
                    },
                ],
            }
        ],
    }
    run = IngestionRun(source="espn")

    result = await _upsert_event(db, event, run)

    assert result is not None
    assert result.id == seeded.id, "must converge onto the SAME Game row, not create a new one"
    assert result.nflverse_game_id == "2025_01_DAL_PHI"
    assert result.espn_event_id == "espn-dal-phi-2025-opener"

    after = await db.scalar(select(func.count()).select_from(Game))
    assert after == before, "no duplicate Game row should have been created"
