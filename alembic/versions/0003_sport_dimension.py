"""Add a sport dimension to teams, players, and games.

Revision ID: 0003_sport_dimension
Revises: 0002_sleeper

Deliberate override of the NFL-only data-foundation plan's global
constraint ("No sport column, no multi-sport branching anywhere"),
approved 2026-08-29 to add real NCAAF support. See CLAUDE.md.

ESPN's numeric team ids are scoped per sport (an NFL team id and an NCAAF
team id can collide), so the old bare-column uniques on teams.espn_id and
teams.nflverse_abbr are replaced with (sport, espn_id) / (sport,
nflverse_abbr) composites rather than just adding a column alongside them.
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_sport_dimension"
down_revision = "0002_sleeper"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "teams",
        sa.Column("sport", sa.String(length=8), nullable=False, server_default="nfl"),
    )
    op.drop_constraint("teams_espn_id_key", "teams", type_="unique")
    op.drop_constraint("teams_nflverse_abbr_key", "teams", type_="unique")
    op.create_unique_constraint("uq_teams_sport_espn_id", "teams", ["sport", "espn_id"])
    op.create_unique_constraint("uq_teams_sport_abbr", "teams", ["sport", "nflverse_abbr"])

    op.add_column(
        "players",
        sa.Column("sport", sa.String(length=8), nullable=False, server_default="nfl"),
    )

    op.add_column(
        "games",
        sa.Column("sport", sa.String(length=8), nullable=False, server_default="nfl"),
    )
    op.create_index("ix_games_sport", "games", ["sport"])


def downgrade():
    op.drop_index("ix_games_sport", table_name="games")
    op.drop_column("games", "sport")
    op.drop_column("players", "sport")
    op.drop_constraint("uq_teams_sport_abbr", "teams", type_="unique")
    op.drop_constraint("uq_teams_sport_espn_id", "teams", type_="unique")
    op.create_unique_constraint("teams_espn_id_key", "teams", ["espn_id"])
    op.create_unique_constraint("teams_nflverse_abbr_key", "teams", ["nflverse_abbr"])
    op.drop_column("teams", "sport")
