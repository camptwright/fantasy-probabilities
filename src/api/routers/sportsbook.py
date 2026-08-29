"""The sportsbook API surface homelab-dashboard's Fantasy tile already
expects (src/tiles/fantasy/client.ts there, "verified against the real
deployed API" 2026-08-03, before this repo's NFL rebuild removed it).

This was never part of the rebuild's own written plan - Plan 2 (model, API,
parlays) was deferred and never authored (see
docs/superpowers/specs/2026-08-20-fantasy-edge-nfl-rebuild-design.md in
homelab-master). Built here against the existing data-foundation schema
(team_market_lines, player_prop_lines, games) plus the new Elo baseline in
src/services/elo.py, shaped to match the dashboard client's documented
PropLine/Signal interfaces field-for-field.

Constraint #7 (CLAUDE.md): every list endpoint here uses PostgreSQL
DISTINCT ON to return only the latest observation per identity key - the
same discipline props_agent/props ingestion already enforces at write time,
now enforced again at read time so duplicate/stale rows never reach a
client.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import get_settings
from src.db.client import get_db
from src.models.facts import Game, PlayerPropLine, TeamMarketLine
from src.models.identity import Player, Team
from src.models.ratings import TeamRating
from src.services.elo import moneyline_probability, spread_cover_probability
from src.utils.normalize import normalize_player_name
from src.utils.odds_math import (
    american_to_decimal,
    american_to_implied,
    expected_value_percent,
    remove_vig_two_way,
)

router = APIRouter()

# Markets a rating-only baseline can honestly speak to. Totals need a points
# model this Elo baseline does not provide - omitted rather than faked.
_MODELED_MARKETS = ("moneyline", "spread")


async def _team_lookup(db: AsyncSession, team_ids: set[uuid.UUID]) -> dict[uuid.UUID, Team]:
    if not team_ids:
        return {}
    rows = (await db.execute(select(Team).where(Team.id.in_(team_ids)))).scalars()
    return {team.id: team for team in rows}


async def _rating_lookup(db: AsyncSession, team_ids: set[uuid.UUID]) -> dict[uuid.UUID, float]:
    if not team_ids:
        return {}
    rows = (
        await db.execute(select(TeamRating).where(TeamRating.team_id.in_(team_ids)))
    ).scalars()
    return {rating.team_id: rating.rating for rating in rows}


@router.get("/props")
async def props(sport: str | None = Query(default=None), db: AsyncSession = Depends(get_db)) -> list[dict[str, Any]]:
    stmt = select(PlayerPropLine, Player).join(Player, PlayerPropLine.player_id == Player.id)
    if sport is not None:
        stmt = stmt.where(Player.sport == sport)
    stmt = stmt.distinct(
        PlayerPropLine.player_id, PlayerPropLine.stat_type, PlayerPropLine.source
    ).order_by(
        PlayerPropLine.player_id,
        PlayerPropLine.stat_type,
        PlayerPropLine.source,
        PlayerPropLine.observed_at.desc(),
    )
    rows = (await db.execute(stmt)).all()

    team_ids = {row.Player.current_team_id for row in rows if row.Player.current_team_id}
    teams = await _team_lookup(db, team_ids)

    return [
        {
            "id": str(prop.id),
            "sport": player.sport,
            "source": prop.source,
            "player_name": player.full_name,
            "normalized_name": normalize_player_name(player.full_name),
            "player_id": str(player.id),
            # Underdog's payload carries no team array (constraint #17), so
            # game_id is never resolved at ingest time - always null today,
            # not a bug in this endpoint.
            "game_id": str(prop.game_id) if prop.game_id else None,
            "team_name": teams[player.current_team_id].name if player.current_team_id in teams else None,
            "opponent_name": None,
            "stat_type": prop.stat_type,
            "line": prop.line,
            "over_price_american": prop.over_price_american,
            "under_price_american": prop.under_price_american,
            # No player-projection pipeline yet (docs/nfl-modeling.md) -
            # null, not fabricated, until one exists.
            "projection": None,
            "edge_percent": None,
            "captured_at": prop.observed_at.isoformat(),
        }
        for prop, player in rows
    ]


@router.get("/props/best")
async def props_best() -> dict[str, Any]:
    """edge_percent has no producer yet (see /props), so there is no honest
    way to rank "best" props. Returns the gap explicitly rather than a
    fabricated ordering."""
    return {"items": [], "note": "no player-projection pipeline yet - edge_percent is not populated"}


async def _signal_rows(db: AsyncSession, sport: str | None) -> list[dict[str, Any]]:
    stmt = (
        select(TeamMarketLine, Game)
        .join(Game, TeamMarketLine.game_id == Game.id)
        .where(TeamMarketLine.market.in_(_MODELED_MARKETS))
    )
    if sport is not None:
        stmt = stmt.where(Game.sport == sport)
    stmt = stmt.distinct(
        TeamMarketLine.game_id, TeamMarketLine.market, TeamMarketLine.side, TeamMarketLine.source
    ).order_by(
        TeamMarketLine.game_id,
        TeamMarketLine.market,
        TeamMarketLine.side,
        TeamMarketLine.source,
        TeamMarketLine.observed_at.desc(),
    )
    rows = (await db.execute(stmt)).all()

    team_ids = {g.home_team_id for _, g in rows if g.home_team_id} | {
        g.away_team_id for _, g in rows if g.away_team_id
    }
    teams = await _team_lookup(db, team_ids)
    ratings = await _rating_lookup(db, team_ids)

    # Vig removal needs both sides of the same (game, market, source) quote
    # together (remove_vig_two_way), so group before emitting rows rather
    # than processing each side independently.
    paired: dict[tuple, dict[str, tuple[TeamMarketLine, Game]]] = {}
    for line, game in rows:
        key = (line.game_id, line.market, line.source)
        paired.setdefault(key, {})[line.side] = (line, game)

    out = []
    for (_, market, source), sides in paired.items():
        home_entry = sides.get("home")
        away_entry = sides.get("away")
        if home_entry is None or away_entry is None:
            # Only one side observed so far (e.g. the other side's poll
            # hasn't landed yet) - nothing to pair against, skip until both
            # exist rather than emit a one-sided fair probability.
            continue
        home_line, game = home_entry
        away_line, _ = away_entry

        if game.home_team_id not in ratings or game.away_team_id not in ratings:
            # No Elo history for one side yet (brand-new team, or the
            # sport's bootstrap hasn't run) - omit rather than assume the
            # 1500 default means something.
            continue
        home_rating, away_rating = ratings[game.home_team_id], ratings[game.away_team_id]
        home_name = teams[game.home_team_id].name if game.home_team_id in teams else "Home"
        away_name = teams[game.away_team_id].name if game.away_team_id in teams else "Away"
        matchup = f"{away_name} @ {home_name}"

        if market == "moneyline":
            home_model_prob = moneyline_probability(home_rating, away_rating)
            home_selection, away_selection = f"{home_name} ML", f"{away_name} ML"
        else:  # spread
            home_model_prob = spread_cover_probability(
                home_rating, away_rating, home_line.line or 0.0, game.sport
            )
            home_selection = f"{home_name} {home_line.line:+.1f}" if home_line.line is not None else home_name
            away_selection = f"{away_name} {away_line.line:+.1f}" if away_line.line is not None else away_name

        fair_home, fair_away = None, None
        if home_line.price_american is not None and away_line.price_american is not None:
            fair_home, fair_away = remove_vig_two_way(home_line.price_american, away_line.price_american)

        for line, model_prob, selection, fair_prob in (
            (home_line, home_model_prob, home_selection, fair_home),
            (away_line, 1.0 - home_model_prob, away_selection, fair_away),
        ):
            implied_prob = american_to_implied(line.price_american) if line.price_american is not None else None
            ev_percent = (
                expected_value_percent(model_prob, line.price_american)
                if line.price_american is not None
                else None
            )
            kelly = None
            if line.price_american is not None:
                b = american_to_decimal(line.price_american) - 1.0
                edge = model_prob * (b + 1.0) - 1.0
                full_kelly = max(0.0, edge / b) if b > 0 else 0.0
                kelly = round(full_kelly * get_settings().kelly_fraction_cap, 4)

            out.append(
                {
                    "id": str(line.id),
                    "sport": game.sport,
                    "market": market,
                    "selection": selection,
                    "bookmaker": source,
                    "price_american": line.price_american,
                    "model_probability": round(model_prob, 4),
                    "fair_probability": round(fair_prob, 4) if fair_prob is not None else None,
                    "implied_probability": round(implied_prob, 4) if implied_prob is not None else None,
                    "ev_percent": round(ev_percent, 2) if ev_percent is not None else 0.0,
                    "kelly_fraction": kelly,
                    # No credit/staking system yet (deferred contest system)
                    # - null rather than an invented unit size.
                    "stake_units": None,
                    "confidence": None,
                    "tier": None,
                    # No settlement/grading system yet (same deferral) -
                    # null until a real contest engine can grade this leg.
                    "result": None,
                    "created_at": line.observed_at.isoformat(),
                    "matchup": matchup,
                    "game_time": game.game_time.isoformat() if game.game_time else None,
                    "game_status": game.status,
                }
            )
    return out


@router.get("/signals")
async def signals(sport: str | None = Query(default=None), db: AsyncSession = Depends(get_db)) -> list[dict[str, Any]]:
    return await _signal_rows(db, sport)


@router.get("/rankings/{sport}")
async def rankings(sport: str, db: AsyncSession = Depends(get_db)) -> list[dict[str, Any]]:
    if sport not in get_settings().supported_sports:
        raise HTTPException(status_code=404, detail=f"unsupported sport {sport!r}")
    rows = (
        await db.execute(
            select(TeamRating, Team)
            .join(Team, TeamRating.team_id == Team.id)
            .where(TeamRating.sport == sport)
            .order_by(TeamRating.rating.desc())
        )
    ).all()
    return [
        {
            "team_id": str(team.id),
            "team_name": team.name,
            "sport": sport,
            "rating": round(rating.rating, 1),
            "updated_at": rating.updated_at.isoformat(),
        }
        for rating, team in rows
    ]


@router.get("/parlays")
async def parlays(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """A single suggested parlay from the current top-EV legs.

    Legs are combined assuming INDEPENDENCE - explicitly a simplification.
    The rebuild design's correlated joint-distribution model (so a moneyline
    and its matching spread aren't priced as if unrelated) is real future
    work, deferred alongside the rest of the contest system; faking
    correlation awareness here would be worse than being explicit about not
    having it yet.
    """
    all_signals = await _signal_rows(db, sport=None)
    legs = sorted(
        (s for s in all_signals if s["price_american"] is not None),
        key=lambda s: s["ev_percent"],
        reverse=True,
    )[:3]
    if not legs:
        return {"legs": [], "combined_probability": None, "note": "no priced signals available yet"}

    combined_probability = 1.0
    for leg in legs:
        combined_probability *= leg["model_probability"]

    return {
        "legs": legs,
        "combined_probability": round(combined_probability, 4),
        "independent_legs_assumption": True,
        "note": "legs assumed independent - no correlated joint-distribution model yet",
    }
