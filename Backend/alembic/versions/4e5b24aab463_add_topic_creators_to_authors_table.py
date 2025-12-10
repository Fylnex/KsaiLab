"""add_topic_creators_to_authors_table

Revision ID: 4e5b24aab463
Revises: e283aa54cab0
Create Date: 2025-11-10 12:00:58.742765

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "4e5b24aab463"
down_revision: Union[str, Sequence[str], None] = "ebc44ab8c0f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Добавить создателей тем в таблицу topic_authors."""
    # Получить connection для выполнения raw SQL
    connection = op.get_bind()

    # 1. Добавить создателей тем, которые ещё не являются авторами
    connection.execute(
        sa.text(
            """
        INSERT INTO topic_authors (topic_id, user_id, added_by, is_archived)
        SELECT
            t.id as topic_id,
            t.creator_id as user_id,
            t.creator_id as added_by,
            FALSE as is_archived
        FROM topics t
        WHERE t.creator_id IS NOT NULL
        AND NOT EXISTS (
            SELECT 1 FROM topic_authors ta
            WHERE ta.topic_id = t.id AND ta.user_id = t.creator_id
        )
    """
        )
    )

    # 2. Добавить индексы для производительности (если отсутствуют)
    op.create_index(
        "ix_topic_authors_user_id",
        "topic_authors",
        ["user_id"],
        unique=False,
        if_not_exists=True,
    )

    op.create_index(
        "ix_topic_authors_topic_user_archived",
        "topic_authors",
        ["topic_id", "user_id", "is_archived"],
        unique=False,
        if_not_exists=True,
    )

    # 3. Проверить корректность миграции
    validate_migration()


def validate_migration():
    """Проверить корректность миграции."""
    connection = op.get_bind()

    # 1. Все темы с creator_id имеют запись в topic_authors
    result = connection.execute(
        sa.text(
            """
        SELECT COUNT(*) FROM topics t
        WHERE t.creator_id IS NOT NULL
        AND t.is_archived = FALSE
        AND NOT EXISTS (
            SELECT 1 FROM topic_authors ta
            WHERE ta.topic_id = t.id AND ta.user_id = t.creator_id
        )
    """
        )
    )

    missing_count = result.scalar()
    if missing_count > 0:
        raise Exception(
            f"Миграция не удалась: {missing_count} создателей не добавлены в topic_authors"
        )

    # 2. Нет дублированных записей
    result = connection.execute(
        sa.text(
            """
        SELECT COUNT(*) FROM (
            SELECT topic_id, user_id, COUNT(*) as cnt
            FROM topic_authors
            GROUP BY topic_id, user_id
            HAVING COUNT(*) > 1
        ) duplicates
    """
        )
    )

    duplicate_count = result.scalar()
    if duplicate_count > 0:
        raise Exception(
            f"Миграция не удалась: обнаружены {duplicate_count} дублированных записей"
        )

    print("Миграция прошла успешно")


def downgrade() -> None:
    """Удалить записи создателей из topic_authors."""
    # Получить connection для выполнения raw SQL
    connection = op.get_bind()

    # Удалить только те записи, где added_by = user_id (авто-добавленные создатели)
    connection.execute(
        sa.text(
            """
        DELETE FROM topic_authors
        WHERE added_by = user_id
        AND topic_id IN (
            SELECT id FROM topics WHERE creator_id = topic_authors.user_id
        )
    """
        )
    )

    # Удалить индексы (если существуют)
    op.drop_index(
        "ix_topic_authors_topic_user_archived", "topic_authors", if_exists=True
    )
    op.drop_index("ix_topic_authors_user_id", "topic_authors", if_exists=True)
