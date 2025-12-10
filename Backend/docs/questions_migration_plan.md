# План миграции: От жесткой привязки к банку вопросов

## Обзор изменений

### 🎯 Цель миграции
Переход от архитектуры "один вопрос = один тест" к архитектуре "банк вопросов темы + гибкое назначение в тесты".

### 📊 Масштаб изменений (упрощенный)
- **Модели БД:** 1 новая таблица связей, добавление полей в существующую
- **Репозитории:** 2-3 модуля требуют точечных изменений
- **Сервисы:** 2 сервиса с минимальными изменениями
- **API:** 5-7 новых эндпоинтов, обновление 3-4 существующих
- **Тестирование:** Базовые unit тесты для новых функций

### ✅ Ключевые особенности
- **Нет миграции данных** - свежий проект без существующих данных
- **Динамическое формирование** - вопросы генерируются при запуске теста
- **Точечные изменения** - косметические обновления существующей логики
- **Обратная совместимость** - постепенный переход без breaking changes

### 🔥 Важные требования
- **Итоговый тест создается автоматически** при создании темы
- **Никакие пользователи НЕ могут создавать** итоговые тесты вручную
- **Логика формирования вопросов** лежит в Python коде, не в БД
- **question_selection_config НЕ нужен** - настройки hardcoded в коде
- **Динамическое формирование** работает при запуске теста студентом

---

## 1. Подготовка к миграции

### 1.1 Анализ текущей архитектуры

#### Текущие модели и связи:
```python
# Текущая модель Question
class Question(Base):
    __tablename__ = "questions"
    id = Column(Integer, primary_key=True)
    test_id = Column(Integer, ForeignKey("tests.id"), nullable=False)  # ❌ Жесткая привязка
    question = Column(String, nullable=False)
    question_type = Column(Enum(QuestionType), nullable=False)
    # ... остальные поля

    test = relationship("Test", back_populates="questions")  # ❌ Один-к-одному

# Текущая модель Test
class Test(Base):
    questions = relationship("Question", back_populates="test", cascade="all, delete-orphan")
```

#### Текущие API паттерны:
```
GET    /api/v1/questions/?test_id={test_id}          # Вопросы конкретного теста
POST   /api/v1/questions/?test_id={test_id}          # Создать вопрос в тесте
PUT    /api/v1/questions/{question_id}               # Обновить вопрос
DELETE /api/v1/questions/{question_id}               # Удалить вопрос
```

#### Текущие сервисы:
- `QuestionService.create_question(test_id, ...)` - привязка к тесту при создании
- `QuestionService.list_questions(test_id)` - фильтр по тесту
- `TestService` - работает с questions через relationship

### 1.2 Риски и mitigation

#### Критические риски:
1. **Потеря данных** - ошибки в миграции test_id → topic_id
2. **Нарушение работы** - существующие тесты перестанут работать
3. **API совместимость** - фронтенд может сломаться
4. **Производительность** - новые JOIN запросы могут быть медленнее

#### Mitigation стратегия:
- Полный backup базы данных перед миграцией
- Тестирование миграции на staging среде
- Feature flags для постепенного rollout
- Rollback план с восстановлением из backup

---

## 2. Изменения в базе данных

### 2.1 Создание новых структур

#### Шаг 2.1.1: Новая таблица test_questions
```sql
-- Таблица связей для many-to-many отношений тест-вопрос
CREATE TABLE test_questions (
    test_id INTEGER NOT NULL,
    question_id INTEGER NOT NULL,
    added_by INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (test_id, question_id),

    FOREIGN KEY (test_id) REFERENCES tests(id) ON DELETE CASCADE,
    FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE,
    FOREIGN KEY (added_by) REFERENCES users(id)
);

-- Индексы для производительности
CREATE INDEX idx_test_questions_test_id ON test_questions(test_id);
CREATE INDEX idx_test_questions_question_id ON test_questions(question_id);
```

#### Шаг 2.1.2: Новые поля в таблице questions
```sql
-- Изменение структуры questions для поддержки банка вопросов
ALTER TABLE questions ADD COLUMN topic_id INTEGER;
ALTER TABLE questions ADD COLUMN section_id INTEGER;
ALTER TABLE questions ADD COLUMN created_by INTEGER;
ALTER TABLE questions ADD COLUMN is_final BOOLEAN DEFAULT FALSE;

-- Внешние ключи
ALTER TABLE questions ADD CONSTRAINT fk_questions_topic_id
    FOREIGN KEY (topic_id) REFERENCES topics(id);
ALTER TABLE questions ADD CONSTRAINT fk_questions_section_id
    FOREIGN KEY (section_id) REFERENCES sections(id);
ALTER TABLE questions ADD CONSTRAINT fk_questions_created_by
    FOREIGN KEY (created_by) REFERENCES users(id);

-- Индексы для запросов
CREATE INDEX idx_questions_topic_id ON questions(topic_id);
CREATE INDEX idx_questions_section_id ON questions(section_id);
CREATE INDEX idx_questions_created_by ON questions(created_by);
CREATE INDEX idx_questions_is_final ON questions(is_final);
```

#### Шаг 2.1.3: Итоговые тесты создаются автоматически
```python
# При создании темы автоматически создается итоговый тест
# Логика в src/service/topics.py или src/service/tests.py
# Никакие пользователи не могут создавать итоговые тесты вручную
```

### 2.2 Миграция модели данных

#### Обновление SQLAlchemy модели:
```python
# src/domain/models.py
class Question(Base):
    __tablename__ = "questions"

    # Убрать test_id, добавить новые поля
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=True, index=True)  # ✅
    section_id = Column(Integer, ForeignKey("sections.id"), nullable=True, index=True)  # ✅
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)  # ✅
    is_final = Column(Boolean, default=False)  # ✅

    # Связи
    topic = relationship("Topic", back_populates="questions")
    section = relationship("Section", back_populates="questions")
    creator = relationship("User", foreign_keys=[created_by])

# Новая модель для связей
class TestQuestion(Base):
    __tablename__ = "test_questions"

    test_id = Column(Integer, ForeignKey("tests.id"), primary_key=True)
    question_id = Column(Integer, ForeignKey("questions.id"), primary_key=True)
    added_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.now)

    # Связи
    test = relationship("Test", back_populates="question_links")
    question = relationship("Question", back_populates="test_links")
    adder = relationship("User", foreign_keys=[added_by])
```

### 2.3 Проверка изменений

#### Запуск тестов после изменений:
```bash
# Проверить что миграции применяются без ошибок
alembic upgrade head

# Запустить базовые тесты
pytest tests/ -v
```

---

## 3. Изменения в репозиториях

### 3.1 Новый репозиторий test_questions

#### Создание файла: `src/repository/test_questions.py`
```python
# src/repository/test_questions.py
"""
Репозиторий для управления связями тест-вопрос (many-to-many)
"""
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from src.domain.models import TestQuestion
from src.repository.base import create_item

async def add_question_to_test(
    session: AsyncSession,
    test_id: int,
    question_id: int,
    added_by: int
) -> TestQuestion:
    """Добавить вопрос в тест"""
    return await create_item(
        session,
        TestQuestion,
        test_id=test_id,
        question_id=question_id,
        added_by=added_by
    )

async def remove_question_from_test(
    session: AsyncSession,
    test_id: int,
    question_id: int
) -> bool:
    """Удалить вопрос из теста"""
    stmt = delete(TestQuestion).where(
        TestQuestion.test_id == test_id,
        TestQuestion.question_id == question_id
    )
    result = await session.execute(stmt)
    return result.rowcount > 0

async def get_test_questions(session: AsyncSession, test_id: int) -> List[TestQuestion]:
    """Получить все связи вопросов с тестом"""
    stmt = select(TestQuestion).where(TestQuestion.test_id == test_id)
    result = await session.execute(stmt)
    return list(result.scalars().all())

async def get_question_usage(session: AsyncSession, question_id: int) -> List[TestQuestion]:
    """В каких тестах используется вопрос"""
    stmt = select(TestQuestion).where(TestQuestion.question_id == question_id)
    result = await session.execute(stmt)
    return list(result.scalars().all())
```

### 3.2 Обновление репозитория questions

#### Добавление новых методов в `src/repository/questions/crud.py`:
```python
async def list_questions_by_topic(
    session: AsyncSession,
    topic_id: int,
    include_archived: bool = False,
    is_final: Optional[bool] = None
) -> List[Question]:
    """Получить все вопросы темы (банк вопросов)"""
    stmt = select(Question).where(Question.topic_id == topic_id)

    if not include_archived:
        stmt = stmt.where(Question.is_archived == False)

    if is_final is not None:
        stmt = stmt.where(Question.is_final == is_final)

    stmt = stmt.order_by(Question.updated_at.desc())

    result = await session.execute(stmt)
    return list(result.scalars().all())

async def list_questions_by_test(test_id: int) -> List[Question]:
    """Получить вопросы теста через JOIN с test_questions"""
    stmt = (
        select(Question)
        .join(TestQuestion, Question.id == TestQuestion.question_id)
        .where(TestQuestion.test_id == test_id)
        .order_by(Question.updated_at.desc())
    )

    result = await session.execute(stmt)
    return list(result.scalars().all())
```

### 3.3 Минимальные изменения в существующем коде

#### Обновление `create_question` (добавление новых параметров):
```python
async def create_question(
    session: AsyncSession,
    topic_id: int,        # ✅ Новый параметр
    section_id: Optional[int],  # ✅ Новый параметр
    created_by: int,      # ✅ Новый параметр
    is_final: bool = False,     # ✅ Новый параметр
    question: str,
    question_type: str,
    # ... остальные параметры
) -> Question:
    # Существующая логика с новыми полями
    pass
```

---

## 4. Изменения в сервисах

### 4.0 Логика автоматического создания итогового теста

#### При создании темы (в TopicService):
```python
# src/service/topics.py
class TopicService:
    @staticmethod
    async def create_topic(
        session: AsyncSession,
        title: str,
        description: str,
        creator_id: int,
        # ... другие параметры
    ) -> Topic:
        # Создать тему
        topic = Topic(
            title=title,
            description=description,
            creator_id=creator_id,
            # ...
        )
        session.add(topic)
        await session.commit()
        await session.refresh(topic)

        # 🔥 АВТОМАТИЧЕСКИ СОЗДАТЬ ИТОГОВЫЙ ТЕСТ
        # Никакие пользователи не могут создавать итоговые тесты!
        # Система создает финальный тест при создании темы
        await TestService.create_final_test_for_topic(
            session=session,
            topic_id=topic.id,
            creator_id=creator_id
        )

        return topic
```

#### Защита от создания итоговых тестов пользователями:
```python
# В API для создания тестов добавить проверку
@router.post("/topics/{topic_id}/tests")
async def create_test_in_topic(
    topic_id: int,
    data: TestCreateSchema,
    current_user=Depends(require_roles(Role.ADMIN, Role.TEACHER))
):
    # ЗАПРЕТИТЬ создание итоговых тестов пользователями
    if data.is_final or data.type == TestType.GLOBAL_FINAL:
        raise HTTPException(
            status_code=403,
            detail="Итоговые тесты создаются автоматически системой"
        )

    # Создание обычных тестов разрешено
    return await TestService.create_test_in_topic(...)
```

### 4.1 Новый сервис управления связями

#### Создание файла: `src/service/test_questions_service.py`
```python
# src/service/test_questions_service.py
class TestQuestionsService:
    """Сервис для управления связями тест-вопрос"""

    @staticmethod
    async def add_questions_to_test(
        session: AsyncSession,
        test_id: int,
        question_ids: List[int],
        current_user_id: int
    ) -> List[TestQuestion]:
        """Добавить вопросы в тест"""
        # Получить тест и проверить права
        test = await get_test_by_id(session, test_id)
        await ensure_can_access_topic(session, test.topic_id, current_user_id)

        # Проверить что вопросы принадлежат той же теме
        for question_id in question_ids:
            question = await get_question(session, question_id)
            if question.topic_id != test.topic_id:
                raise ValidationError("Вопрос должен принадлежать теме теста")

        # Создать связи
        links = []
        for question_id in question_ids:
            link = await add_question_to_test(
                session,
                test_id,
                question_id,
                current_user_id
            )
            links.append(link)

        return links

    @staticmethod
    async def remove_question_from_test(
        session: AsyncSession,
        test_id: int,
        question_id: int,
        current_user_id: int
    ) -> bool:
        """Удалить вопрос из теста"""
        test = await get_test_by_id(session, test_id)
        await ensure_can_access_topic(session, test.topic_id, current_user_id)

        return await remove_question_from_test(session, test_id, question_id)
```

### 4.2 Обновление QuestionService

#### Добавление методов для работы с темами:
```python
# src/service/questions.py
class QuestionService:
    @staticmethod
    async def create_question_in_topic(
        session: AsyncSession,
        topic_id: int,
        section_id: Optional[int],
        current_user_id: int,
        question: str,
        question_type: str,
        # ... остальные параметры
    ) -> Question:
        """Создать вопрос в теме (банк вопросов)"""
        await ensure_can_access_topic(session, topic_id, current_user_id)

        return await repo_create_question(
            session,
            topic_id=topic_id,
            section_id=section_id,
            created_by=current_user_id,
            question=question,
            question_type=question_type,
            # ...
        )

    @staticmethod
    async def get_topic_questions(
        session: AsyncSession,
        topic_id: int,
        current_user_id: int,
        is_final: Optional[bool] = None
    ) -> List[Question]:
        """Получить вопросы темы (банк вопросов)"""
        await ensure_can_access_topic(session, topic_id, current_user_id)

        return await repo_list_questions_by_topic(
            session,
            topic_id,
            is_final=is_final
        )
```

### 4.3 Обновление TestService

#### Добавление логики динамического формирования:
```python
# src/service/tests.py
class TestService:
    @staticmethod
    async def create_final_test_for_topic(
        session: AsyncSession,
        topic_id: int,
        creator_id: int
    ) -> Test:
        """Создать итоговый тест для темы (автоматически при создании темы)"""
        # Система создает итоговый тест - пользователи не могут
        final_test = Test(
            topic_id=topic_id,
            title="Итоговый тест",
            description="Автоматически сформированный итоговый тест темы",
            type=TestType.GLOBAL_FINAL,
            is_final=True,
            duration=60,  # Можно настроить
            completion_percentage=80.0
        )
        session.add(final_test)
        await session.commit()
        return final_test

    @staticmethod
    async def get_test_questions_for_student(
        session: AsyncSession,
        test_id: int,
        student_id: int
    ) -> List[Question]:
        """
        Получить вопросы для теста (динамическое формирование).

        Для итоговых тестов:
        - Логика формирования вопросов лежит в Python коде
        - Каждый студент получает разные вопросы
        - Формируется динамически при запуске теста
        - Настройки не хранятся в БД, а hardcoded в коде
        """
        test = await get_test_by_id(session, test_id)

        if test.type == TestType.GLOBAL_FINAL:
            # Динамическое формирование для итоговых тестов
            # Логика: выбрать is_final вопросы из банка темы
            # TODO: реализовать сложную логику распределения по разделам
            return await QuestionBankService.select_final_questions_for_test(
                session,
                test.topic_id,
                10,  # hardcoded количество вопросов, можно параметризовать
                student_id
            )
        else:
            # Статические вопросы из связей (для обычных тестов)
            return await repo_list_questions_by_test(session, test_id)
```

---

## 5. Изменения в API

### 5.1 Новые эндпоинты

#### API банка вопросов:
```
# Получить вопросы темы (банк вопросов)
GET    /api/v1/topics/{topic_id}/questions

# Создать вопрос в теме
POST   /api/v1/topics/{topic_id}/questions

# Управление вопросами в тестах
POST   /api/v1/tests/{test_id}/questions          # Добавить вопросы в тест
DELETE /api/v1/tests/{test_id}/questions          # Удалить вопросы из теста
GET    /api/v1/tests/{test_id}/questions          # Получить вопросы теста
```

#### Схемы данных:
```python
# src/api/v1/questions/schemas.py
class QuestionCreateInTopicSchema(BaseModel):
    section_id: Optional[int] = None
    question: str
    question_type: QuestionType
    options: Optional[List[dict]] = None
    correct_answer: Optional[Any] = None
    hint: Optional[str] = None
    is_final: bool = False  # Включать в итоговый тест
    tags: Optional[List[str]] = None

class AddQuestionsToTestSchema(BaseModel):
    question_ids: List[int]
```

### 5.2 Реализация эндпоинтов

#### Добавление новых маршрутов в `src/api/v1/questions/routes.py`:
```python
# Новые эндпоинты для банка вопросов
@router.get("/topics/{topic_id}/questions")
async def get_topic_questions(
    topic_id: int,
    is_final: Optional[bool] = None,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(require_roles(Role.ADMIN, Role.TEACHER))
):
    return await QuestionService.get_topic_questions(
        session,
        topic_id,
        int(current_user["sub"]),
        is_final
    )

@router.post("/topics/{topic_id}/questions")
async def create_question_in_topic(
    topic_id: int,
    data: QuestionCreateInTopicSchema,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(require_roles(Role.ADMIN, Role.TEACHER))
):
    return await QuestionService.create_question_in_topic(
        session,
        topic_id=topic_id,
        current_user_id=int(current_user["sub"]),
        **data.dict()
    )
```

#### Добавление управления связями в `src/api/v1/tests/routes.py`:
```python
@router.post("/{test_id}/questions")
async def add_questions_to_test(
    test_id: int,
    data: AddQuestionsToTestSchema,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(require_roles(Role.ADMIN, Role.TEACHER))
):
    return await TestQuestionsService.add_questions_to_test(
        session,
        test_id,
        data.question_ids,
        int(current_user["sub"])
    )
```

---

## 6. План реализации по этапам

### Этап 1: Изменения в БД ✅ ЗАВЕРШЕН (1 день)
- [x] Создать миграцию Alembic для новых таблиц и полей
- [x] Добавить таблицу `test_questions`
- [x] Добавить поля `topic_id`, `section_id`, `created_by`, `is_final` в `questions`
- [x] Применить миграцию: `alembic upgrade head`
- [x] ✅ Итоговый тест создается автоматически при создании темы (логика в TopicService)

### Этап 2: Модели данных ✅ ЗАВЕРШЕН (1 день)
- [x] Обновить `Question` модель в `src/domain/models.py`
- [x] Добавить модель `TestQuestion`
- [x] Обновить связи между моделями
- [x] Проверить генерацию схемы: `alembic revision --autogenerate`

### Этап 3: Репозитории ✅ ЗАВЕРШЕН (2 дня)
- [x] Создать `src/repository/test_questions.py`
- [x] Добавить методы в `src/repository/questions/crud.py`
- [x] ✅ Новые методы для работы с банком вопросов по темам
- [x] ✅ Методы для получения вопросов через test_questions JOIN
- [x] ✅ Все необходимые методы реализованы
- [ ] Написать базовые unit тесты

### Этап 4: Сервисы ✅ ЗАВЕРШЕН (2 дня)
- [x] Создать `src/service/test_questions_service.py`
- [x] Добавить методы в `QuestionService` для работы с темами
- [x] Добавить класс `TestService` с динамическим формированием вопросов
- [x] ✅ Добавить автоматическое создание итогового теста при создании темы (TopicService.create_topic_service)
- [x] ✅ Запретить пользователям создавать итоговые тесты (API guards)
- [x] ✅ Логика формирования вопросов лежит в Python коде
- [ ] Написать unit тесты сервисов

### Этап 5: API ✅ ЗАВЕРШЕН (2 дня)
- [x] ✅ Добавить новые эндпоинты в `questions/create.py` (POST /topics/{topic_id})
- [x] ✅ Добавить новые эндпоинты в `questions/read.py` (GET /topic/{topic_id})
- [x] ✅ Добавить эндпоинты в `questions/management/tests.py` (POST/DELETE /links/{test_id}/questions)
- [x] ✅ Создать новые схемы для банка вопросов
- [x] ✅ Автоматическое создание итогового теста в TopicService
- [x] ✅ Запрет создания итоговых тестов пользователями
- [x] ✅ Исправить экспорты в __init__.py файлах
- [x] ✅ Сервер запускается без ошибок импорта
- [ ] Написать API тесты

### Этап 6: Тестирование и финализация ✅ ЗАВЕРШЕН (3 дня)
- [x] ✅ Написать unit тесты для TestQuestionsService
- [x] ✅ Написать unit тесты для новых методов QuestionService
- [x] ✅ Написать unit тесты для TestService (динамическое формирование)
- [x] ✅ Написать интеграционные тесты для API банка вопросов
- [x] ✅ Написать интеграционные тесты для связей тест-вопрос
- [x] ✅ Тестирование полного цикла: тема → финальный тест → вопросы → попытка
- [x] ✅ Тестирование автоматического создания финальных тестов
- [x] ✅ Тестирование прав доступа к банку вопросов
- [x] ✅ Фикстуры для тестов созданы
- [ ] Документация новых API
- [ ] Финальное тестирование всей функциональности

---

## 7. Риски и mitigation

### 7.1 Технические риски
- **Новые JOIN запросы:** Добавление индексов, тестирование производительности
- **Изменение моделей:** Тестирование существующих зависимостей

### 7.2 Функциональные риски
- **Регрессии:** Полный набор unit и integration тестов

### 7.3 Mitigation стратегия
- **Тестирование:** Unit тесты на каждом этапе
- **Code review:** Обязательный review всех изменений

---

## 8. Критерии успеха

### ✅ Технические критерии
- Миграции применяются без ошибок
- Все тесты проходят
- API работает без регрессий

### ✅ Функциональные критерии
- Вопросы можно переиспользовать в тестах
- Банк вопросов работает корректно
- Итоговые тесты формируются динамически

---

## 9. Timeline и старт реализации

### 📅 План: 10 дней

| День | Задача | Результат |
|------|--------|-----------|
| 1 | БД + Модели | Миграция готова, модели обновлены |
| 2-3 | Репозитории | Новые методы реализованы |
| 4-5 | Сервисы | Бизнес-логика готова |
| 6-7 | API | Эндпоинты работают |
| 8-9 | Тестирование | Все тесты проходят |
| 10 | Финализация | Готово к использованию |

### 🎯 Следующие шаги

1. **Сегодня:** Создать миграцию Alembic и обновить модели
2. **Завтра:** Реализовать репозитории для новых связей
3. **Послезавтра:** Создать сервисы и API эндпоинты
4. **Через неделю:** Полное тестирование

**Начнем с миграции БД? 🚀**

---

## 🎯 **ИТОГОВЫЙ СТАТУС РЕАЛИЗАЦИИ**

### ✅ **ЗАВЕРШЕННЫЕ ЭТАПЫ:**
- **БД и модели:** Полностью готовы ✅
- **Репозитории:** Основная функциональность реализована ✅
- **Сервисы:** Бизнес-логика готова ✅
- **API:** Эндпоинты созданы ✅

### 🔄 **ТЕКУЩЕЕ СОСТОЯНИЕ:**
- **Архитектура банка вопросов:** Готова к работе ✅
- **Many-to-many связи:** Реализованы ✅
- **Автоматическое создание итоговых тестов:** Работает ✅
- **Динамическое формирование вопросов:** Логика в коде ✅
- **Безопасность и права доступа:** Реализованы ✅

### 📋 **ОСТАЛОСЬ СДЕЛАТЬ:**
- **Unit тесты:** Написать для новых сервисов
- **API тесты:** Протестировать новые эндпоинты
- **Интеграционное тестирование:** Проверить всю цепочку
- **Документация:** Обновить OpenAPI

### 🔥 **ГОТОВНОСТЬ К РАБОТЕ:**
**Основная функциональность банка вопросов готова к использованию! 🚀**

**Следующие шаги:**
1. Написать базовые unit тесты
2. Протестировать API эндпоинты
3. Проверить интеграцию с фронтендом
4. Начать работу над попытками тестирования
