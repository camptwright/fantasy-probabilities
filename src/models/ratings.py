"""Team Elo ratings - the "honest baseline" model.

Not the full market-anchored/market-independent joint-distribution model the
original rebuild design deferred to an unwritten Plan 2 (see
docs/superpowers/specs/2026-08-20-fantasy-edge-nfl-rebuild-design.md in
homelab-master). This is deliberately a simple, transparent rating updated
after each final score, in the spirit already stated in
docs/nfl-modeling.md: a baseline predictor, not a claim of calibrated
probability. See src/services/elo.py for the update/probability math.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, UUIDPrimaryKey, utcnow

STARTING_RATING = 1500.0


class TeamRating(Base, UUIDPrimaryKey):
    __tablename__ = "team_ratings"
    __table_args__ = (UniqueConstraint("team_id", name="uq_team_ratings_team_id"),)

    team_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False
    )
    # Denormalized from teams.sport, same rationale as games.sport - every
    # /rankings/{sport} query filters directly rather than joining teams.
    sport: Mapped[str] = mapped_column(String(8), nullable=False)
    rating: Mapped[float] = mapped_column(Float, nullable=False, default=STARTING_RATING)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )
