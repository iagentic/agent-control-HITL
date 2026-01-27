"""
Revision ID: b7c9d8e1f2a3
Revises: ff13d775aa5a
Create Date: 2026-01-27 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "b7c9d8e1f2a3"
down_revision = "ff13d775aa5a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "evaluator_configs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=True),
        sa.Column("plugin", sa.String(length=255), nullable=False),
        sa.Column(
            "config",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(
        op.f("ix_evaluator_configs_plugin"),
        "evaluator_configs",
        ["plugin"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_evaluator_configs_plugin"), table_name="evaluator_configs")
    op.drop_table("evaluator_configs")
