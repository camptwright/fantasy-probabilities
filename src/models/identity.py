"""Canonical identity for teams and players.

Player identity is the highest-risk element of this schema. nflverse keys on
gsis_id, ESPN on its own numerics, Underdog on UUIDs, and Underdog's line
payload carries no team (constraint #17), so a player cannot be disambiguated
by roster from that response alone.

Name matching is unsafe: two active players are named Josh Allen - a
Jacksonville edge rusher and the Buffalo quarterback. A naive name join
attributes one player's props to the other's statistics and raises nothing.
PlayerExternalId is therefore a real table with per-source uniqueness.
"""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, CreatedAt, UUIDPrimaryKey

# Sport codes used throughout: "nfl", "ncaaf". Kept as a plain string rather
# than a DB enum so a third sport is a data change, not a migration.
DEFAULT_SPORT = "nfl"


class Team(Base, UUIDPrimaryKey, CreatedAt):
    __tablename__ = "teams"
    __table_args__ = (
        # ESPN's numeric team ids are scoped per sport, not globally unique -
        # NFL team id 2 (Buffalo Bills) and an NCAAF team id 2 are unrelated
        # schools. Global uniqueness on espn_id alone would collide the
        # moment a second sport is added, so both natural keys are scoped by
        # sport instead.
        UniqueConstraint("sport", "espn_id", name="uq_teams_sport_espn_id"),
        UniqueConstraint("sport", "nflverse_abbr", name="uq_teams_sport_abbr"),
    )

    sport: Mapped[str] = mapped_column(String(8), nullable=False, default=DEFAULT_SPORT)
    espn_id: Mapped[str] = mapped_column(String(16), nullable=False)
    # NFL: nflverse's own abbreviation. NCAAF has no nflverse equivalent, so
    # this holds ESPN's own team abbreviation instead - same role (the
    # alias file's lookup key) regardless of which source it came from.
    nflverse_abbr: Mapped[str] = mapped_column(String(8), nullable=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False)


class Player(Base, UUIDPrimaryKey, CreatedAt):
    __tablename__ = "players"

    # A player belongs to exactly one sport. Distinct from Team.sport being
    # scoped for identity uniqueness - this exists to keep NCAAF's much
    # larger name pool from widening the existing same-name collision risk
    # (two active "Josh Allen"s) across sports that share no roster overlap.
    sport: Mapped[str] = mapped_column(String(8), nullable=False, default=DEFAULT_SPORT)
    gsis_id: Mapped[str | None] = mapped_column(String(32), unique=True)
    full_name: Mapped[str] = mapped_column(String(128), nullable=False)
    position: Mapped[str | None] = mapped_column(String(8))
    current_team_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("teams.id", ondelete="SET NULL")
    )


class PlayerExternalId(Base, UUIDPrimaryKey, CreatedAt):
    __tablename__ = "player_external_ids"
    __table_args__ = (
        UniqueConstraint("source", "external_id", name="uq_player_external_source_id"),
    )

    player_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("players.id", ondelete="CASCADE"), nullable=False
    )
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    external_id: Mapped[str] = mapped_column(String(64), nullable=False)
