"""add operator password verifier

Revision ID: 0002_operator_authentication
Revises: 0001_production_baseline
Create Date: 2026-07-14
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0002_operator_authentication"
down_revision: Union[str, Sequence[str], None] = "0001_production_baseline"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Existing installations remain deliberately uninitialized until bootstrap
    # or the local recovery flow stores a valid versioned verifier.
    op.add_column("operator_principals", sa.Column("password_hash", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("operator_principals", "password_hash")
