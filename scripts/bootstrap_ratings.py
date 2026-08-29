"""Offline Elo bootstrap. Runs on the training host, not reekserver-1.

NFL: nflverse historical games (already ingested via scripts/ingest_history.py
into the `games` table) never pass through src/ingest/espn.py's live-sync Elo
hook, so this walks them chronologically and applies the same
update_ratings_after_game() directly.

NCAAF: there is no nflverse-equivalent historical source (see
docs/nfl-modeling.md), so this instead re-runs sync_scoreboard() against past
season dates - the same insert-on-change path live sync uses, which already
carries the Elo hook, so NCAAF ratings build as a side effect of the backfill
itself rather than a second code path.
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import date, timedelta

from sqlalchemy import select

from src.db.client import get_worker_db
from src.ingest.espn import sync_scoreboard
from src.models.facts import Game
from src.services.elo import update_ratings_after_game


async def _bootstrap_nfl(seasons: list[int]) -> int:
    updated = 0
    async with get_worker_db() as db:
        games = (
            await db.execute(
                select(Game)
                .where(
                    Game.sport == "nfl",
                    Game.season.in_(seasons),
                    Game.home_score.isnot(None),
                    Game.away_score.isnot(None),
                )
                .order_by(Game.game_time.asc().nulls_last())
            )
        ).scalars()
        for game in games:
            await update_ratings_after_game(db, game)
            updated += 1
        await db.commit()
    return updated


async def _bootstrap_ncaaf(seasons: list[int]) -> None:
    """Weekly date windows, not one season-wide range - see sync_scoreboard's
    own docstring on why. Regular season runs late August through early
    December; conference championships and bowls run through early January
    of the following year."""
    async with get_worker_db() as db:
        for season in seasons:
            start = date(season, 8, 20)
            end = date(season + 1, 1, 20)
            current = start
            while current <= end:
                await sync_scoreboard(db, sport="ncaaf", dates=f"{current:%Y%m%d}")
                current += timedelta(days=7)


async def _run(seasons: list[int]) -> None:
    nfl_updated = await _bootstrap_nfl(seasons)
    print(f"applied {nfl_updated} NFL Elo updates across seasons {seasons}")

    await _bootstrap_ncaaf(seasons)
    print(f"backfilled NCAAF scoreboard (and Elo) across seasons {seasons}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seasons", type=int, nargs="+", required=True)
    args = parser.parse_args()
    asyncio.run(_run(args.seasons))


if __name__ == "__main__":
    main()
