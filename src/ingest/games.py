"""Single resolution layer for Game identity, mirroring resolve_team/resolve_player.

nflverse and ESPN each find-or-create a Game keyed on their own external id
(nflverse_game_id / espn_event_id) with no reconciliation between them -
this is what stops that from creating two rows for one real fixture.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.facts import Game


async def resolve_game(
    db: AsyncSession,
    *,
    home_team_id: uuid.UUID,
    away_team_id: uuid.UUID,
    kickoff: datetime | None,
    nflverse_id: str | None = None,
    espn_id: str | None = None,
) -> Game:
    """Find the Game this fixture already has a row for, by whichever
    external id is provided, falling back to team-pair + kickoff-window
    matching so the OTHER source's id can be backfilled onto the same row
    rather than creating a second one.
    """
    if nflverse_id:
        existing = await db.scalar(select(Game).where(Game.nflverse_game_id == nflverse_id))
        if existing is not None:
            if espn_id and not existing.espn_event_id:
                existing.espn_event_id = espn_id
            return existing
    if espn_id:
        existing = await db.scalar(select(Game).where(Game.espn_event_id == espn_id))
        if existing is not None:
            if nflverse_id and not existing.nflverse_game_id:
                existing.nflverse_game_id = nflverse_id
            return existing

    # Neither external id matched. Try team-pair + kickoff window before
    # creating a new row - this is what lets nflverse's historically-seeded
    # row and ESPN's live-synced row for the SAME real game converge onto
    # one Game instead of two.
    if kickoff is not None:
        candidates = list(
            (
                await db.execute(
                    select(Game).where(
                        Game.home_team_id == home_team_id,
                        Game.away_team_id == away_team_id,
                    )
                )
            ).scalars()
        )
        for candidate in candidates:
            if candidate.game_time is not None and abs(
                (candidate.game_time - kickoff).total_seconds()
            ) < 86400:
                if nflverse_id and not candidate.nflverse_game_id:
                    candidate.nflverse_game_id = nflverse_id
                if espn_id and not candidate.espn_event_id:
                    candidate.espn_event_id = espn_id
                return candidate

    # Deliberately NOT flushed here: `Game.season` is NOT NULL and this
    # brand-new row has no season yet - that's set by the caller
    # immediately afterward (both nflverse.py and espn.py already flush
    # once, after every field is assigned, exactly as they did before this
    # function existed). Flushing this bare row here would hit the same
    # premature-INSERT NOT NULL violation documented in both callers'
    # docstrings. SQLAlchemy's autoflush still sees this pending row for
    # any SELECT issued later in the same session (e.g. this function's own
    # team-pair candidate search on a later record), so nothing is lost by
    # deferring the flush to the caller.
    game = Game(nflverse_game_id=nflverse_id, espn_event_id=espn_id)
    db.add(game)
    return game
