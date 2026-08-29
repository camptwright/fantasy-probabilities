"""Team Elo ratings - the honest-baseline model.

Revision ID: 0004_team_ratings
Revises: 0003_sport_dimension
"""
from alembic import op
import sqlalchemy as sa

revision = "0004_team_ratings"
down_revision = "0003_sport_dimension"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "team_ratings",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("team_id", sa.UUID(), nullable=False),
        sa.Column("sport", sa.String(length=8), nullable=False),
        sa.Column("rating", sa.Float(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("team_id", name="uq_team_ratings_team_id"),
    )
    op.create_index("ix_team_ratings_sport", "team_ratings", ["sport"])


def downgrade():
    op.drop_index("ix_team_ratings_sport", table_name="team_ratings")
    op.drop_table("team_ratings")
