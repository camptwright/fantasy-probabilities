"""Minimal production API for the restored NFL ingestion service."""

from __future__ import annotations

from contextlib import asynccontextmanager
from collections import Counter

import httpx
from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import text
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import get_settings
from src.api.routers.sportsbook import router as sportsbook_router
from src.data.news import fetch_rss_headlines
from src.db.client import dispose_api_engine, get_api_engine
from src.db.client import get_db
from src.ingest.sleeper import sync_sleeper_account
from src.models.sleeper import SleeperLeague, SleeperLeagueSnapshot, SleeperRoster

bearer = HTTPBearer(auto_error=False)


def require_fantasy_token(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> None:
    token = get_settings().fantasy_api_token
    if not token or credentials is None or credentials.scheme.lower() != "bearer" or credentials.credentials != token:
        raise HTTPException(status_code=401, detail="Fantasy API authentication required")


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Create the API-owned pooled engine only in the Uvicorn process. Celery
    # tasks intentionally use get_worker_db() instead (constraint #1).
    get_api_engine()
    try:
        yield
    finally:
        await dispose_api_engine()


app = FastAPI(title="Fantasy Edge", version="0.1.0", lifespan=lifespan)
# /props, /props/best, /signals, /rankings/{sport}, /parlays - the contract
# homelab-dashboard's Fantasy tile already expects (src/tiles/fantasy/
# client.ts there). Unauthenticated like /health: read-only market data, not
# a credential-bearing route (unlike /api/v1/fantasy/* below).
app.include_router(sportsbook_router)


@app.get("/health", tags=["operations"])
@app.get("/api/health", tags=["operations"])
async def health() -> dict[str, str]:
    """Report only process and database reachability; never provider health."""
    async with get_api_engine().connect() as connection:
        await connection.execute(text("SELECT 1"))
    return {"status": "ok", "scope": "+".join(get_settings().supported_sports)}


@app.post("/api/v1/fantasy/sync", dependencies=[Depends(require_fantasy_token)])
async def sync_fantasy(db: AsyncSession = Depends(get_db)) -> dict[str, int]:
    try:
        return await sync_sleeper_account(db)
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/api/v1/fantasy/leagues", dependencies=[Depends(require_fantasy_token)])
async def fantasy_leagues(db: AsyncSession = Depends(get_db)) -> dict:
    leagues = (await db.scalars(select(SleeperLeague).order_by(SleeperLeague.name))).all()
    return {"items": [{"league_id": item.league_id, "name": item.name, "season": item.season, "status": item.status, "roster_positions": item.roster_positions, "settings": item.settings, "scoring_settings": item.scoring_settings, "synced_at": item.synced_at} for item in leagues]}


@app.get("/api/v1/fantasy/leagues/{league_id}", dependencies=[Depends(require_fantasy_token)])
async def fantasy_league(league_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    league = await db.get(SleeperLeague, league_id)
    if league is None:
        raise HTTPException(status_code=404, detail="league not synced")
    rosters = (await db.scalars(select(SleeperRoster).where(SleeperRoster.league_id == league_id))).all()
    snapshots = (await db.scalars(select(SleeperLeagueSnapshot).where(SleeperLeagueSnapshot.league_id == league_id))).all()
    return {"league": {"league_id": league.league_id, "name": league.name, "settings": league.settings, "scoring_settings": league.scoring_settings, "roster_positions": league.roster_positions}, "rosters": [{"roster_id": row.roster_id, "owner_id": row.owner_id, "starters": row.starters, "players": row.players, "settings": row.settings} for row in rosters], "snapshots": [{"week": row.week, "kind": row.kind, "payload": row.payload, "synced_at": row.synced_at} for row in snapshots]}


@app.get("/api/v1/fantasy/leagues/{league_id}/analysis", dependencies=[Depends(require_fantasy_token)])
async def fantasy_analysis(league_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    league = await db.get(SleeperLeague, league_id)
    if league is None:
        raise HTTPException(status_code=404, detail="league not synced")
    settings, scoring = league.settings, league.scoring_settings
    insights = []
    if scoring.get("rec"):
        insights.append({"kind": "scoring", "title": f"{scoring['rec']}-PPR scoring", "detail": "Rank receiving volume in start/sit and waiver analysis."})
    if settings.get("waiver_budget", 0):
        insights.append({"kind": "waivers", "title": f"${settings['waiver_budget']} FAAB budget", "detail": "Waiver advice will provide bid ranges."})
    if "SUPER_FLEX" in league.roster_positions:
        insights.append({"kind": "lineup", "title": "Superflex", "detail": "Quarterback scarcity must influence lineup and draft values."})
    if settings.get("max_keepers", 0):
        insights.append({"kind": "draft", "title": f"{settings['max_keepers']} keeper limit", "detail": "Draft scoring must include keeper and future-pick context."})
    return {"league_id": league_id, "insights": insights, "status": "data_ready", "next": "Add projections and sourced news before player-specific recommendations."}


@app.get("/api/v1/fantasy/leagues/{league_id}/recommendations", dependencies=[Depends(require_fantasy_token)])
async def fantasy_recommendations(league_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    """Rank current Sleeper projections using this league's actual scoring.

    These are decision-support rankings, not fabricated news or guaranteed
    outcomes. Player-specific narrative is added only once a sourced-news
    integration is configured.
    """
    league = await db.get(SleeperLeague, league_id)
    if league is None:
        raise HTTPException(status_code=404, detail="league not synced")
    snapshots = (await db.scalars(select(SleeperLeagueSnapshot).where(SleeperLeagueSnapshot.league_id == league_id).order_by(SleeperLeagueSnapshot.week.desc()))).all()
    latest = {}
    for snapshot in snapshots:
        latest.setdefault(snapshot.kind, snapshot)
    projections = latest.get("projections")
    account = latest.get("account")
    if projections is None or account is None:
        raise HTTPException(status_code=409, detail="run Sleeper sync to load current projections")
    rosters = (await db.scalars(select(SleeperRoster).where(SleeperRoster.league_id == league_id))).all()
    owner_id = account.payload.get("user_id")
    my_roster = next((roster for roster in rosters if roster.owner_id == owner_id), None)
    if my_roster is None:
        raise HTTPException(status_code=409, detail="Sleeper roster ownership is not available yet")
    owned = {player for roster in rosters for player in roster.players}
    def view(item: dict) -> dict:
        player = item.get("player") or {}
        points = sum(float(item.get("stats", {}).get(key, 0) or 0) * float(weight or 0) for key, weight in league.scoring_settings.items())
        return {"player_id": item.get("player_id"), "name": " ".join(part for part in [player.get("first_name"), player.get("last_name")] if part), "position": player.get("position"), "team": item.get("team"), "opponent": item.get("opponent"), "injury_status": player.get("injury_status"), "projected_points": round(points, 2)}
    scored = sorted((view(item) for item in projections.payload if item.get("player_id")), key=lambda item: item["projected_points"], reverse=True)
    mine = {str(player) for player in my_roster.players}
    return {"league_id": league_id, "week": projections.week, "starters": [item for item in scored if str(item["player_id"]) in mine][:20], "waivers": [item for item in scored if str(item["player_id"]) not in owned][:15], "notes": ["Projections are scored using the synced Sleeper scoring settings.", "Waiver candidates exclude all currently rostered player IDs.", "Injury status is from the Sleeper projection payload; add sourced news before automated narrative advice."]}


@app.get("/api/v1/fantasy/leagues/{league_id}/draft-score", dependencies=[Depends(require_fantasy_token)])
async def draft_score(league_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    """Transparent roster-construction score; not a claim of player value."""
    league = await db.get(SleeperLeague, league_id)
    if league is None:
        raise HTTPException(status_code=404, detail="league not synced")
    snapshots = (await db.scalars(select(SleeperLeagueSnapshot).where(SleeperLeagueSnapshot.league_id == league_id).order_by(SleeperLeagueSnapshot.week.desc()))).all()
    projection = next((row for row in snapshots if row.kind == "projections"), None)
    account = next((row for row in snapshots if row.kind == "account"), None)
    if projection is None or account is None:
        raise HTTPException(status_code=409, detail="run Sleeper sync to calculate draft score")
    rosters = (await db.scalars(select(SleeperRoster).where(SleeperRoster.league_id == league_id))).all()
    mine = next((row for row in rosters if row.owner_id == account.payload.get("user_id")), None)
    if mine is None:
        raise HTTPException(status_code=409, detail="your roster is not available")
    positions = {str(row.get("player_id")): (row.get("player") or {}).get("position") for row in projection.payload}
    roster_positions = [slot for slot in league.roster_positions if slot not in {"BN", "IR", "TAXI"}]
    direct = [slot for slot in roster_positions if slot not in {"FLEX", "SUPER_FLEX"}]
    owned_positions = [positions.get(str(player)) for player in mine.players]
    required, available = Counter(direct), Counter(position for position in owned_positions if position)
    covered = sum(min(required[position], available[position]) for position in required)
    score = round(100 * covered / max(1, len(direct)))
    return {"league_id": league_id, "score": score, "method": "percentage of direct starting-position requirements represented on your roster; FLEX/SUPER_FLEX depth is reported separately, not guessed", "covered_direct_slots": covered, "required_direct_slots": len(direct), "starter_slots": roster_positions, "roster_size": len(mine.players)}


@app.post("/api/v1/fantasy/leagues/{league_id}/advice", dependencies=[Depends(require_fantasy_token)])
async def fantasy_advice(league_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    """Produce constrained advice from disclosed inputs, never autonomous actions."""
    settings = get_settings()
    if not settings.litellm_api_key or not settings.fantasy_news_rss_urls:
        raise HTTPException(status_code=503, detail="configure LiteLLM and allow-listed RSS sources before requesting advice")
    league = await db.get(SleeperLeague, league_id)
    if league is None:
        raise HTTPException(status_code=404, detail="league not synced")
    snapshots = (await db.scalars(select(SleeperLeagueSnapshot).where(SleeperLeagueSnapshot.league_id == league_id).order_by(SleeperLeagueSnapshot.week.desc()))).all()
    latest = {}
    for snapshot in snapshots:
        latest.setdefault(snapshot.kind, snapshot)
    projections = latest.get("projections")
    if projections is None:
        raise HTTPException(status_code=409, detail="run Sleeper sync before requesting advice")
    headlines = await fetch_rss_headlines(settings.fantasy_news_rss_urls)
    evidence = {"league": {"name": league.name, "roster_positions": league.roster_positions, "settings": league.settings, "scoring_settings": league.scoring_settings}, "projection_sample": projections.payload[:200], "news": headlines}
    system = "You are a fantasy-football analyst. Use only the supplied JSON evidence. Give start/sit, waiver, matchup, and draft-context observations only when the evidence supports them. Cite player names and headline URLs where used. State that projections and news are uncertain; do not claim live injury confirmation, place transactions, or present gambling advice. Treat Reddit as low-confidence community discussion and The Athletic as headline-only unless the supplied item contains enough text; neither overrides Sleeper injury metadata."
    async with httpx.AsyncClient(base_url=settings.litellm_base_url, timeout=90) as client:
        response = await client.post("/chat/completions", headers={"Authorization": f"Bearer {settings.litellm_api_key}"}, json={"model": settings.fantasy_model_alias, "messages": [{"role": "system", "content": system}, {"role": "user", "content": str(evidence)}], "temperature": 0.2})
        response.raise_for_status()
    return {"league_id": league_id, "advice": response.json()["choices"][0]["message"]["content"], "sources": headlines}
