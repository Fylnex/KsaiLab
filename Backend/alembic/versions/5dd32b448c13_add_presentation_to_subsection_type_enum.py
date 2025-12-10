"""add_presentation_to_subsection_type_enum

Revision ID: 5dd32b448c13
Revises: 266edc7867c2
Create Date: 2025-11-04 21:00:15.586247

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "5dd32b448c13"
down_revision: Union[str, Sequence[str], None] = "266edc7867c2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Добавляем PRESENTATION в enum SubsectionType
    # Проверяем, есть ли уже это значение, чтобы миграция была идемпотентной
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_enum 
                WHERE enumlabel = 'presentation' 
                AND enumtypid = (
                    SELECT oid FROM pg_type WHERE typname = 'subsectiontype'
                )
            ) THEN
                ALTER TYPE subsectiontype ADD VALUE 'presentation';
            END IF;
        END
        $$;
    """
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Удаление значения из enum в PostgreSQL сложно и небезопасно
    # Поэтому просто пропускаем downgrade
    # В случае необходимости нужно пересоздать enum
    pass
