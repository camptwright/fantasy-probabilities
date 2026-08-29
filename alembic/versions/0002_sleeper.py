"""Sleeper league snapshots.

Revision ID: 0002_sleeper
Revises: 0001_nfl_foundation
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002_sleeper"
down_revision = "0001_nfl_foundation"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("sleeper_leagues", sa.Column("league_id", sa.String(32), primary_key=True), sa.Column("name", sa.String(160), nullable=False), sa.Column("season", sa.String(8), nullable=False), sa.Column("status", sa.String(32), nullable=False), sa.Column("roster_positions", postgresql.JSONB(), nullable=False), sa.Column("settings", postgresql.JSONB(), nullable=False), sa.Column("scoring_settings", postgresql.JSONB(), nullable=False), sa.Column("raw", postgresql.JSONB(), nullable=False), sa.Column("synced_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("sleeper_rosters", sa.Column("league_id", sa.String(32), primary_key=True), sa.Column("roster_id", sa.Integer(), primary_key=True), sa.Column("owner_id", sa.String(32)), sa.Column("starters", postgresql.JSONB(), nullable=False), sa.Column("players", postgresql.JSONB(), nullable=False), sa.Column("settings", postgresql.JSONB(), nullable=False), sa.Column("synced_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("sleeper_league_snapshots", sa.Column("league_id", sa.String(32), primary_key=True), sa.Column("week", sa.Integer(), primary_key=True), sa.Column("kind", sa.String(24), primary_key=True), sa.Column("payload", postgresql.JSONB(), nullable=False), sa.Column("synced_at", sa.DateTime(timezone=True), nullable=False))


def downgrade():
    op.drop_table("sleeper_league_snapshots")
    op.drop_table("sleeper_rosters")
    op.drop_table("sleeper_leagues")
