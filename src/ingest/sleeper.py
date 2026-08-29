"""Read-only, account-wide Sleeper sync. League IDs are always discovered."""

from __future__ import annotations

from datetime import datetime, timezone

import httpx
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import get_settings
from src.models.sleeper import SleeperLeague, SleeperLeagueSnapshot, SleeperRoster


async def sync_sleeper_account(db: AsyncSession) -> dict[str, int]:
    settings = get_settings()
    if not settings.sleeper_username:
        raise ValueError("SLEEPER_USERNAME is not configured")
    async with httpx.AsyncClient(base_url=settings.sleeper_base_url, timeout=20) as client:
        user = (await client.get(f"/user/{settings.sleeper_username.lstrip('@')}")).json()
        if not user.get("user_id"):
            raise ValueError("Sleeper username was not found")
        state = (await client.get("/state/nfl")).json()
        season = str(state["league_season"])
        leagues = (await client.get(f"/user/{user['user_id']}/leagues/nfl/{season}")).json()
        for league in leagues:
            league_id = league["league_id"]
            await _upsert_league(db, league)
            rosters = (await client.get(f"/league/{league_id}/rosters")).json()
            await _upsert_rosters(db, league_id, rosters)
            week = int(state.get("leg") or 1)
            matchups = (await client.get(f"/league/{league_id}/matchups/{week}")).json()
            transactions = (await client.get(f"/league/{league_id}/transactions/{week}")).json()
            await _snapshot(db, league_id, week, "matchups", matchups)
            await _snapshot(db, league_id, week, "transactions", transactions)
            await _snapshot(db, league_id, week, "account", user)
            projection_response = await client.get(
                f"/projections/nfl/{season}/{week}", params={"season_type": state.get("season_type", "regular")}
            )
            projection_response.raise_for_status()
            await _snapshot(db, league_id, week, "projections", projection_response.json())
        await db.commit()
    return {"leagues": len(leagues), "season": int(season), "week": int(state.get("leg") or 1)}


async def _upsert_league(db: AsyncSession, league: dict) -> None:
    values = {"league_id": league["league_id"], "name": league["name"], "season": league["season"], "status": league["status"], "roster_positions": league.get("roster_positions", []), "settings": league.get("settings", {}), "scoring_settings": league.get("scoring_settings", {}), "raw": league, "synced_at": datetime.now(timezone.utc)}
    await db.execute(insert(SleeperLeague).values(**values).on_conflict_do_update(index_elements=["league_id"], set_=values))


async def _upsert_rosters(db: AsyncSession, league_id: str, rosters: list[dict]) -> None:
    for roster in rosters:
        values = {"league_id": league_id, "roster_id": roster["roster_id"], "owner_id": roster.get("owner_id"), "starters": roster.get("starters") or [], "players": roster.get("players") or [], "settings": roster.get("settings") or {}, "synced_at": datetime.now(timezone.utc)}
        await db.execute(insert(SleeperRoster).values(**values).on_conflict_do_update(index_elements=["league_id", "roster_id"], set_=values))


async def _snapshot(db: AsyncSession, league_id: str, week: int, kind: str, payload: list | dict) -> None:
    values = {"league_id": league_id, "week": week, "kind": kind, "payload": payload, "synced_at": datetime.now(timezone.utc)}
    await db.execute(insert(SleeperLeagueSnapshot).values(**values).on_conflict_do_update(index_elements=["league_id", "week", "kind"], set_=values))
