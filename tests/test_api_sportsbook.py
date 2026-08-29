"""The sportsbook API surface (src/api/routers/sportsbook.py) - the contract
homelab-dashboard's Fantasy tile already expects.

get_db is overridden to yield the `db` fixture's own session directly,
rather than a second pooled engine built from production-shaped settings -
this app's lifespan is never started, so src.db.client.get_api_engine() is
never touched by these tests at all.
"""

from __future__ import annotations

from datetime import datetime, timezone

from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from src.api.main import app
from src.db.client import get_db
from src.ingest.identity import resolve_team
from src.models.facts import Game, PlayerPropLine, TeamMarketLine
from src.models.identity import Player
from src.models.ratings import TeamRating


async def _client(db):
    async def _override_get_db():
        yield db

    app.dependency_overrides[get_db] = _override_get_db
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_props_returns_the_expected_shape_and_null_projection(db):
    home = await resolve_team(db, "Kansas City Chiefs")
    player = Player(sport="nfl", full_name="Test Player", current_team_id=home.id)
    db.add(player)
    await db.flush()
    db.add(
        PlayerPropLine(
            player_id=player.id,
            stat_type="passing_yards",
            line=250.5,
            over_price_american=-110,
            under_price_american=-110,
            source="underdog",
            observed_at=datetime.now(timezone.utc),
        )
    )
    await db.commit()

    client = await _client(db)
    try:
        response = await client.get("/props?sport=nfl")
        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        row = body[0]
        assert row["player_name"] == "Test Player"
        assert row["team_name"] == home.name
        assert row["stat_type"] == "passing_yards"
        # No player-projection pipeline yet - null, not fabricated.
        assert row["projection"] is None
        assert row["edge_percent"] is None
    finally:
        app.dependency_overrides.clear()


async def test_props_distinct_on_returns_only_the_latest_line(db):
    """Constraint #7: props list endpoints must return only the latest
    observation per (player, stat_type, source), never duplicates."""
    home = await resolve_team(db, "Kansas City Chiefs")
    player = Player(sport="nfl", full_name="Duplicate Test", current_team_id=home.id)
    db.add(player)
    await db.flush()
    db.add(
        PlayerPropLine(
            player_id=player.id, stat_type="rushing_yards", line=50.5,
            source="underdog", observed_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
    )
    db.add(
        PlayerPropLine(
            player_id=player.id, stat_type="rushing_yards", line=55.5,
            source="underdog", observed_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
        )
    )
    await db.commit()

    client = await _client(db)
    try:
        response = await client.get("/props?sport=nfl")
        body = response.json()
        assert len(body) == 1, "DISTINCT ON must collapse to one row per identity key"
        assert body[0]["line"] == 55.5, "the latest observation must win"
    finally:
        app.dependency_overrides.clear()


async def test_signals_and_rankings_reflect_elo_ratings(db):
    home = await resolve_team(db, "Kansas City Chiefs")
    away = await resolve_team(db, "Los Angeles Chargers")
    db.add(TeamRating(team_id=home.id, sport="nfl", rating=1600.0))
    db.add(TeamRating(team_id=away.id, sport="nfl", rating=1400.0))
    game = Game(
        sport="nfl", espn_event_id="signal-test-1", season=2026,
        home_team_id=home.id, away_team_id=away.id, status="scheduled",
    )
    db.add(game)
    await db.flush()
    now = datetime.now(timezone.utc)
    db.add(TeamMarketLine(game_id=game.id, market="moneyline", side="home", price_american=-150, source="theodds", line_type="live", observed_at=now))
    db.add(TeamMarketLine(game_id=game.id, market="moneyline", side="away", price_american=130, source="theodds", line_type="live", observed_at=now))
    await db.commit()

    client = await _client(db)
    try:
        response = await client.get("/signals?sport=nfl")
        assert response.status_code == 200
        signals = response.json()
        assert len(signals) == 2
        home_signal = next(s for s in signals if "Chiefs" in s["selection"])
        assert home_signal["model_probability"] > 0.5, "the higher-rated home team must be favored"
        assert home_signal["fair_probability"] is not None, "both sides are priced, so vig removal must run"

        rankings_response = await client.get("/rankings/nfl")
        rankings = rankings_response.json()
        assert rankings[0]["team_name"] == home.name, "rankings must sort by rating descending"
    finally:
        app.dependency_overrides.clear()


async def test_rankings_rejects_an_unsupported_sport(db):
    client = await _client(db)
    try:
        response = await client.get("/rankings/nhl")
        assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()
