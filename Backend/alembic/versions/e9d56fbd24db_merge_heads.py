"""merge_heads

Revision ID: e9d56fbd24db
Revises: 1c409b4aeb57, 4e5b24aab463
Create Date: 2025-11-11 09:48:53.357665

"""

from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = "e9d56fbd24db"
down_revision: Union[str, Sequence[str], None] = ("1c409b4aeb57", "4e5b24aab463")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
