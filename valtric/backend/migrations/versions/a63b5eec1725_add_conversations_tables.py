"""add conversations tables

Revision ID: a63b5eec1725
Revises: 2c844178c916
Create Date: 2025-10-17 16:25:56.626433

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a63b5eec1725'
down_revision: Union[str, None] = '2c844178c916'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
