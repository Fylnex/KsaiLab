"""convert_subsectiontype_to_lowercase

Revision ID: 6993b9f2fa91
Revises: 90e9d75ab287
Create Date: 2025-11-04 21:58:17.879949

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "6993b9f2fa91"
down_revision: Union[str, Sequence[str], None] = "90e9d75ab287"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Конвертирует enum subsectiontype из uppercase в lowercase.

    Шаги:
    1. Добавляет lowercase значения в enum (text, video, pdf)
    2. Обновляет существующие записи в таблице subsections
    3. Пересоздает enum только с lowercase значениями
    """
    # Шаг 1: Добавляем lowercase значения в enum (если их еще нет)
    op.execute(
        """
        DO $$
        BEGIN
            -- Добавляем 'text' если его нет
            IF NOT EXISTS (
                SELECT 1 FROM pg_enum 
                WHERE enumlabel = 'text' 
                AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'subsectiontype')
            ) THEN
                ALTER TYPE subsectiontype ADD VALUE 'text';
            END IF;
            
            -- Добавляем 'video' если его нет
            IF NOT EXISTS (
                SELECT 1 FROM pg_enum 
                WHERE enumlabel = 'video' 
                AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'subsectiontype')
            ) THEN
                ALTER TYPE subsectiontype ADD VALUE 'video';
            END IF;
            
            -- Добавляем 'pdf' если его нет
            IF NOT EXISTS (
                SELECT 1 FROM pg_enum 
                WHERE enumlabel = 'pdf' 
                AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'subsectiontype')
            ) THEN
                ALTER TYPE subsectiontype ADD VALUE 'pdf';
            END IF;
        END
        $$;
    """
    )

    # Фиксируем добавление значений (иначе использование в UPDATE считает их "unsafe")
    op.execute("COMMIT")

    # Шаг 2: Конвертируем существующие данные в lowercase
    op.execute(
        """
        UPDATE subsections
        SET type = CASE type::text
            WHEN 'TEXT' THEN 'text'::subsectiontype
            WHEN 'VIDEO' THEN 'video'::subsectiontype
            WHEN 'PDF' THEN 'pdf'::subsectiontype
            WHEN 'PRESENTATION' THEN 'presentation'::subsectiontype
            ELSE type
        END
        WHERE type::text IN ('TEXT', 'VIDEO', 'PDF', 'PRESENTATION');
    """
    )

    # Шаг 3: Пересоздаем enum только с lowercase значениями
    # Это требует временного изменения типа колонки
    op.execute(
        """
        -- Создаем временный enum с правильными значениями
        CREATE TYPE subsectiontype_new AS ENUM ('text', 'video', 'pdf', 'presentation');
        
        -- Изменяем тип колонки на временный (данные уже в правильном формате)
        ALTER TABLE subsections 
            ALTER COLUMN type TYPE subsectiontype_new 
            USING (type::text::subsectiontype_new);
        
        -- Удаляем старый enum
        DROP TYPE subsectiontype;
        
        -- Переименовываем новый enum
        ALTER TYPE subsectiontype_new RENAME TO subsectiontype;
    """
    )


def downgrade() -> None:
    """
    Откат: конвертирует enum обратно в uppercase.

    ВНИМАНИЕ: Это может быть опасно если есть новые записи с lowercase значениями!
    """
    # Создаем enum с uppercase значениями
    op.execute(
        """
        -- Создаем временный enum с uppercase значениями
        CREATE TYPE subsectiontype_old AS ENUM ('TEXT', 'VIDEO', 'PDF', 'presentation');
        
        -- Конвертируем данные обратно в uppercase
        ALTER TABLE subsections 
            ALTER COLUMN type TYPE subsectiontype_old 
            USING (
                CASE type::text
                    WHEN 'text' THEN 'TEXT'::subsectiontype_old
                    WHEN 'video' THEN 'VIDEO'::subsectiontype_old
                    WHEN 'pdf' THEN 'PDF'::subsectiontype_old
                    ELSE type::text::subsectiontype_old
                END
            );
        
        -- Удаляем новый enum
        DROP TYPE subsectiontype;
        
        -- Переименовываем старый enum обратно
        ALTER TYPE subsectiontype_old RENAME TO subsectiontype;
    """
    )

    # Конвертируем данные обратно в uppercase
    op.execute(
        """
        UPDATE subsections
        SET type = CASE type::text
            WHEN 'text' THEN 'TEXT'::subsectiontype
            WHEN 'video' THEN 'VIDEO'::subsectiontype
            WHEN 'pdf' THEN 'PDF'::subsectiontype
            ELSE type
        END
        WHERE type::text IN ('text', 'video', 'pdf');
    """
    )
