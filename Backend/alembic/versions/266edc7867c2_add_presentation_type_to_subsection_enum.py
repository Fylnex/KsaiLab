"""add_presentation_type_to_subsection_enum

Revision ID: 266edc7867c2
Revises: 9eceec2d410e
Create Date: 2025-11-04 20:34:23.261257

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "266edc7867c2"
down_revision: Union[str, Sequence[str], None] = "9eceec2d410e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Добавляем новое значение 'presentation' в enum subsectiontype
    op.execute("ALTER TYPE subsectiontype ADD VALUE IF NOT EXISTS 'presentation'")


def downgrade() -> None:
    """Downgrade schema."""
    # PostgreSQL не поддерживает удаление значений из enum напрямую
    # Для полного отката потребуется пересоздать enum и обновить таблицу
    pass
