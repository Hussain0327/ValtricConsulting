"""create conversations and messages

Revision ID: 8c77d2f2ac12
Revises: a63b5eec1725
Create Date: 2025-10-17 16:27:52.257073

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8c77d2f2ac12'
down_revision: Union[str, None] = 'a63b5eec1725'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
