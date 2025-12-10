# Система трекинга активности студентов в подразделах

## 📋 Обзор

Документ содержит анализ и предложения по реализации системы трекинга времени, проведенного студентами в подразделах образовательной платформы.

## 🎯 Цели системы

1. **Отслеживание реального времени** изучения материала студентами
2. **Предотвращение накрутки** прогресса через автоматизированные запросы
3. **Валидация активности** пользователя на странице
4. **Аналитика** времени обучения для преподавателей

## 🏗️ Архитектура решения

### 1. Структура данных

#### Модель `Subsection` (дополнение)
```python
class Subsection(Base):
    # ... существующие поля ...
    
    # Новые поля
    required_time_minutes = Column(Integer, nullable=True)  # Рекомендуемое время прохождения в минутах
    min_time_seconds = Column(Integer, default=30)  # Минимальное время для засчитывания прогресса
```

#### Модель `SubsectionProgress` (расширение)
```python
class SubsectionProgress(Base):
    # ... существующие поля ...
    
    # Новые поля для трекинга
    time_spent_seconds = Column(Integer, default=0)  # Общее время просмотра в секундах
    last_activity_at = Column(DateTime, nullable=True)  # Последняя активность
    session_start_at = Column(DateTime, nullable=True)  # Начало текущей сессии
    is_completed = Column(Boolean, default=False)  # Завершен ли подраздел
    completion_percentage = Column(Float, default=0.0)  # Процент прохождения (0-100)
    activity_sessions = Column(JSON, nullable=True)  # История сессий [{start, end, duration}]
```

### 2. Методы трекинга активности

#### Вариант A: Ping-based tracking (Рекомендуемый)

**Принцип работы:**
- Frontend отправляет "ping" запросы каждые N секунд (рекомендуется 15-30 секунд)
- Backend проверяет валидность активности и обновляет счетчик времени
- Используется throttling для защиты от спама

**Преимущества:**
- ✅ Простота реализации
- ✅ Низкая нагрузка на сервер
- ✅ Возможность валидации активности
- ✅ Гибкая настройка интервалов

**Недостатки:**
- ❌ Возможны небольшие погрешности при сбоях связи
- ❌ Требует постоянного соединения

**Реализация:**

```python
# Эндпоинт для трекинга активности
@router.post("/subsections/progress/{subsection_id}/track-activity")
@limiter.limit("4/minute")  # Максимум 4 запроса в минуту (каждые 15 секунд)
async def track_subsection_activity(
    subsection_id: int,
    request: Request,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
) -> ActivityTrackResponse:
    """
    Трекинг активности студента в подразделе.
    
    Вызывается каждые 15-30 секунд пока студент активен на странице.
    """
    user_id = int(current_user["sub"])
    
    # Получаем или создаем прогресс
    progress = await get_or_create_subsection_progress(session, user_id, subsection_id)
    
    # Валидация активности
    if not await validate_activity(progress, session):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Suspicious activity detected"
        )
    
    # Обновляем время
    await update_activity_time(progress, session)
    
    return ActivityTrackResponse(
        time_spent_seconds=progress.time_spent_seconds,
        completion_percentage=progress.completion_percentage,
        is_completed=progress.is_completed
    )
```

#### Вариант B: Session-based tracking

**Принцип работы:**
- При открытии страницы создается сессия с уникальным токеном
- Frontend отправляет heartbeat каждые N секунд с токеном сессии
- При закрытии страницы отправляется финальный запрос с общим временем

**Преимущества:**
- ✅ Более точный учет времени
- ✅ Лучшая защита от накрутки (токен сессии)
- ✅ Меньше запросов к БД

**Недостатки:**
- ❌ Сложнее в реализации
- ❌ Требует управления сессиями
- ❌ Может терять данные при внезапном закрытии

#### Вариант C: Event-based tracking

**Принцип работы:**
- Отслеживание конкретных событий: scroll, click, focus, blur
- Отправка агрегированных данных о событиях

**Преимущества:**
- ✅ Более точное определение реальной активности
- ✅ Богатая аналитика поведения

**Недостатки:**
- ❌ Сложная реализация
- ❌ Большой объем данных
- ❌ Высокая нагрузка на сервер

### 3. Защита от накрутки и спама

#### 3.1 Rate Limiting (Обязательно)

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

# Ограничение запросов
@router.post("/subsections/progress/{subsection_id}/track-activity")
@limiter.limit("4/minute")  # 4 запроса в минуту = каждые 15 секунд
async def track_activity(...):
    pass
```

**Настройки:**
- Максимум 4 запроса в минуту (каждые 15 секунд)
- Блокировка на 5 минут при превышении лимита
- Белый список для тестирования (отключаемый)

#### 3.2 Валидация временных интервалов

```python
async def validate_activity(
    progress: SubsectionProgress,
    session: AsyncSession
) -> bool:
    """
    Валидация активности пользователя.
    
    Проверяет:
    - Интервалы между запросами (должны быть 10-60 секунд)
    - Аномальные паттерны (слишком регулярные запросы)
    - Множественные параллельные сессии
    """
    now = datetime.utcnow()
    
    # Проверка 1: Минимальный интервал между запросами
    if progress.last_activity_at:
        time_diff = (now - progress.last_activity_at).total_seconds()
        
        # Слишком частые запросы
        if time_diff < 10:
            logger.warning(f"Too frequent requests: {time_diff}s for user {progress.user_id}")
            return False
        
        # Подозрительно регулярные запросы (ровно каждые N секунд)
        if 14.9 <= time_diff <= 15.1:
            # Проверяем историю - если все запросы ровно через 15 секунд, это подозрительно
            recent_intervals = await get_recent_activity_intervals(session, progress.id)
            if all(14.9 <= interval <= 15.1 for interval in recent_intervals):
                logger.warning(f"Suspicious regular pattern for user {progress.user_id}")
                return False
    
    # Проверка 2: Множественные параллельные сессии
    active_sessions = await count_active_sessions(session, progress.user_id)
    if active_sessions > 3:
        logger.warning(f"Too many active sessions: {active_sessions} for user {progress.user_id}")
        return False
    
    # Проверка 3: Максимальное время без перерыва
    if progress.session_start_at:
        session_duration = (now - progress.session_start_at).total_seconds()
        if session_duration > 7200:  # 2 часа без перерыва
            logger.warning(f"Session too long: {session_duration}s for user {progress.user_id}")
            # Сбрасываем сессию
            progress.session_start_at = now
            return True
    
    return True
```

#### 3.3 Детекция ботов

```python
async def detect_bot_activity(
    user_id: int,
    subsection_id: int,
    session: AsyncSession
) -> bool:
    """
    Детекция автоматизированной активности.
    
    Признаки бота:
    - Идеально регулярные интервалы запросов
    - Отсутствие других действий (только трекинг)
    - Одновременная активность в нескольких подразделах
    - Активность 24/7 без перерывов
    """
    # Анализ паттернов за последний час
    recent_activities = await get_user_recent_activities(session, user_id, hours=1)
    
    if len(recent_activities) < 10:
        return False  # Недостаточно данных
    
    # Проверка регулярности интервалов
    intervals = [
        (activities[i+1].created_at - activities[i].created_at).total_seconds()
        for i in range(len(recent_activities) - 1)
    ]
    
    # Стандартное отклонение интервалов
    std_dev = statistics.stdev(intervals) if len(intervals) > 1 else 0
    
    # Если стандартное отклонение < 1 секунда, это подозрительно
    if std_dev < 1.0:
        logger.warning(f"Bot-like behavior detected for user {user_id}: std_dev={std_dev}")
        return True
    
    return False
```

#### 3.4 CAPTCHA для подозрительной активности

```python
async def require_captcha_verification(
    user_id: int,
    session: AsyncSession
) -> bool:
    """
    Проверка, требуется ли CAPTCHA для пользователя.
    """
    # Проверяем флаг в кэше
    cache_key = f"captcha_required:{user_id}"
    captcha_required = await cache.get(cache_key)
    
    if captcha_required:
        return True
    
    # Анализируем активность за последние 24 часа
    suspicious_activity = await detect_bot_activity(user_id, None, session)
    
    if suspicious_activity:
        # Устанавливаем флаг на 1 час
        await cache.setex(cache_key, 3600, "1")
        return True
    
    return False
```

### 4. Определение завершенности подраздела

```python
async def calculate_subsection_completion(
    progress: SubsectionProgress,
    subsection: Subsection
) -> float:
    """
    Расчет процента завершенности подраздела.
    
    Критерии:
    - Минимальное время просмотра (min_time_seconds)
    - Рекомендуемое время прохождения (required_time_minutes)
    - Для PDF/Video: процент просмотренного контента
    """
    if not subsection.required_time_minutes:
        # Если время не установлено, используем минимальное
        min_time = subsection.min_time_seconds or 30
        if progress.time_spent_seconds >= min_time:
            return 100.0
        return (progress.time_spent_seconds / min_time) * 100.0
    
    # Расчет на основе рекомендуемого времени
    required_seconds = subsection.required_time_minutes * 60
    completion = (progress.time_spent_seconds / required_seconds) * 100.0
    
    # Ограничиваем 100%
    return min(completion, 100.0)
```

### 5. API Эндпоинты

#### 5.1 Начало просмотра подраздела

```python
@router.post("/subsections/progress/{subsection_id}/start")
async def start_subsection_viewing(
    subsection_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
) -> SubsectionSessionResponse:
    """
    Начать просмотр подраздела.
    
    Создает новую сессию просмотра.
    """
    user_id = int(current_user["sub"])
    
    # Получаем или создаем прогресс
    progress = await get_or_create_subsection_progress(session, user_id, subsection_id)
    
    # Начинаем новую сессию
    progress.session_start_at = datetime.utcnow()
    
    await session.commit()
    
    return SubsectionSessionResponse(
        session_id=progress.id,
        subsection_id=subsection_id,
        started_at=progress.session_start_at,
        time_spent_seconds=progress.time_spent_seconds,
        completion_percentage=progress.completion_percentage
    )
```

#### 5.2 Трекинг активности (heartbeat)

```python
@router.post("/subsections/progress/{subsection_id}/heartbeat")
@limiter.limit("4/minute")
async def subsection_heartbeat(
    subsection_id: int,
    request: Request,
    payload: HeartbeatPayload,  # Optional: может содержать дополнительные данные
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
) -> HeartbeatResponse:
    """
    Heartbeat запрос для трекинга активности.
    
    Должен вызываться каждые 15-30 секунд пока пользователь активен.
    """
    user_id = int(current_user["sub"])
    
    # Проверка на бота
    if await detect_bot_activity(user_id, subsection_id, session):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Suspicious activity detected. Please verify you are human."
        )
    
    # Получаем прогресс
    progress = await get_subsection_progress(session, user_id, subsection_id)
    if not progress:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found. Please start viewing the subsection first."
        )
    
    # Валидация активности
    if not await validate_activity(progress, session):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please slow down."
        )
    
    # Обновляем время и активность
    now = datetime.utcnow()
    time_increment = 15  # Засчитываем 15 секунд
    
    if progress.last_activity_at:
        # Проверяем реальный интервал
        actual_interval = (now - progress.last_activity_at).total_seconds()
        time_increment = min(actual_interval, 60)  # Максимум 60 секунд за раз
    
    progress.time_spent_seconds += int(time_increment)
    progress.last_activity_at = now
    
    # Обновляем процент завершенности
    subsection = await get_subsection(session, subsection_id)
    progress.completion_percentage = await calculate_subsection_completion(progress, subsection)
    
    # Проверяем завершенность
    if progress.completion_percentage >= 100.0 and not progress.is_completed:
        progress.is_completed = True
        progress.is_viewed = True
        progress.viewed_at = now
        
        # Обновляем прогресс раздела и темы
        await update_section_progress(session, user_id, subsection.section_id)
        await update_topic_progress(session, user_id, subsection.section.topic_id)
    
    await session.commit()
    
    return HeartbeatResponse(
        time_spent_seconds=progress.time_spent_seconds,
        completion_percentage=progress.completion_percentage,
        is_completed=progress.is_completed,
        next_heartbeat_in_seconds=15  # Когда отправить следующий heartbeat
    )
```

#### 5.3 Завершение просмотра

```python
@router.post("/subsections/progress/{subsection_id}/complete")
async def complete_subsection_viewing(
    subsection_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
) -> SubsectionProgressRead:
    """
    Завершить просмотр подраздела.
    
    Вызывается при закрытии страницы или переходе к следующему подразделу.
    """
    user_id = int(current_user["sub"])
    
    progress = await get_subsection_progress(session, user_id, subsection_id)
    if not progress:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Progress not found"
        )
    
    # Сохраняем сессию в историю
    if progress.session_start_at:
        session_duration = (datetime.utcnow() - progress.session_start_at).total_seconds()
        
        # Добавляем в историю сессий
        if not progress.activity_sessions:
            progress.activity_sessions = []
        
        progress.activity_sessions.append({
            "start": progress.session_start_at.isoformat(),
            "end": datetime.utcnow().isoformat(),
            "duration": int(session_duration)
        })
        
        progress.session_start_at = None
    
    await session.commit()
    
    return SubsectionProgressRead.model_validate(progress)
```

### 6. Frontend интеграция

#### 6.1 Composable для трекинга

```typescript
// app/composables/useSubsectionTracking.ts
export const useSubsectionTracking = (subsectionId: number) => {
  const isTracking = ref(false)
  const heartbeatInterval = ref<NodeJS.Timeout | null>(null)
  const progress = ref({
    timeSpentSeconds: 0,
    completionPercentage: 0,
    isCompleted: false
  })
  
  const startTracking = async () => {
    try {
      // Начинаем сессию
      const response = await $fetch(`/api/v1/subsections/progress/${subsectionId}/start`, {
        method: 'POST'
      })
      
      progress.value = {
        timeSpentSeconds: response.time_spent_seconds,
        completionPercentage: response.completion_percentage,
        isCompleted: response.is_completed
      }
      
      isTracking.value = true
      
      // Запускаем heartbeat каждые 15 секунд
      heartbeatInterval.value = setInterval(async () => {
        await sendHeartbeat()
      }, 15000)
      
    } catch (error) {
      console.error('Failed to start tracking:', error)
    }
  }
  
  const sendHeartbeat = async () => {
    if (!isTracking.value) return
    
    try {
      const response = await $fetch(`/api/v1/subsections/progress/${subsectionId}/heartbeat`, {
        method: 'POST'
      })
      
      progress.value = {
        timeSpentSeconds: response.time_spent_seconds,
        completionPercentage: response.completion_percentage,
        isCompleted: response.is_completed
      }
      
    } catch (error) {
      if (error.status === 429) {
        console.warn('Rate limit exceeded')
        // Увеличиваем интервал
        stopTracking()
        setTimeout(() => startTracking(), 30000)
      } else if (error.status === 403) {
        console.error('Suspicious activity detected')
        stopTracking()
        // Показать CAPTCHA
        showCaptchaDialog()
      }
    }
  }
  
  const stopTracking = async () => {
    if (heartbeatInterval.value) {
      clearInterval(heartbeatInterval.value)
      heartbeatInterval.value = null
    }
    
    if (isTracking.value) {
      try {
        await $fetch(`/api/v1/subsections/progress/${subsectionId}/complete`, {
          method: 'POST'
        })
      } catch (error) {
        console.error('Failed to complete tracking:', error)
      }
    }
    
    isTracking.value = false
  }
  
  // Автоматически останавливаем при размонтировании
  onUnmounted(() => {
    stopTracking()
  })
  
  // Обработка visibility change (вкладка скрыта/показана)
  const handleVisibilityChange = () => {
    if (document.hidden) {
      // Вкладка скрыта - останавливаем трекинг
      if (heartbeatInterval.value) {
        clearInterval(heartbeatInterval.value)
      }
    } else {
      // Вкладка активна - возобновляем трекинг
      if (isTracking.value && !heartbeatInterval.value) {
        heartbeatInterval.value = setInterval(() => sendHeartbeat(), 15000)
      }
    }
  }
  
  onMounted(() => {
    document.addEventListener('visibilitychange', handleVisibilityChange)
  })
  
  onUnmounted(() => {
    document.removeEventListener('visibilitychange', handleVisibilityChange)
  })
  
  return {
    progress: readonly(progress),
    isTracking: readonly(isTracking),
    startTracking,
    stopTracking
  }
}
```

#### 6.2 Использование в компоненте

```vue
<template>
  <div class="subsection-viewer">
    <div v-if="progress.completionPercentage < 100" class="progress-bar">
      <div class="progress-fill" :style="{ width: `${progress.completionPercentage}%` }"></div>
      <span class="progress-text">
        {{ Math.floor(progress.completionPercentage) }}% 
        ({{ formatTime(progress.timeSpentSeconds) }})
      </span>
    </div>
    
    <!-- Контент подраздела -->
    <div class="subsection-content" v-html="subsection.content"></div>
  </div>
</template>

<script setup lang="ts">
const props = defineProps<{
  subsectionId: number
}>()

const { progress, startTracking, stopTracking } = useSubsectionTracking(props.subsectionId)

onMounted(() => {
  startTracking()
})

onBeforeUnmount(() => {
  stopTracking()
})

const formatTime = (seconds: number): string => {
  const minutes = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${minutes}:${secs.toString().padStart(2, '0')}`
}
</script>
```

## 📊 Схемы данных

### Pydantic схемы

```python
# schemas.py

class HeartbeatPayload(BaseModel):
    """Payload для heartbeat запроса."""
    # Можно добавить дополнительные данные, например:
    scroll_percentage: Optional[float] = None
    is_focused: Optional[bool] = None


class HeartbeatResponse(BaseModel):
    """Ответ на heartbeat запрос."""
    time_spent_seconds: int
    completion_percentage: float
    is_completed: bool
    next_heartbeat_in_seconds: int


class SubsectionSessionResponse(BaseModel):
    """Ответ при старте сессии."""
    session_id: int
    subsection_id: int
    started_at: datetime
    time_spent_seconds: int
    completion_percentage: float


class SubsectionProgressRead(BaseModel):
    """Расширенная схема прогресса подраздела."""
    id: int
    subsection_id: int
    user_id: int
    is_viewed: bool
    is_completed: bool
    viewed_at: Optional[datetime]
    time_spent_seconds: int
    completion_percentage: float
    last_activity_at: Optional[datetime]
    
    class Config:
        from_attributes = True
```

## 🔐 Безопасность

### Чек-лист безопасности

- [x] Rate limiting на всех эндпоинтах трекинга
- [x] Валидация временных интервалов
- [x] Детекция ботов и подозрительной активности
- [x] CAPTCHA для подозрительных пользователей
- [x] Логирование всех попыток накрутки
- [x] Максимальное время непрерывной активности
- [x] Проверка множественных параллельных сессий
- [x] Защита от replay атак (через timestamp)

## 📈 Мониторинг и аналитика

### Метрики для отслеживания

1. **Среднее время просмотра** подразделов разных типов
2. **Процент завершения** подразделов
3. **Паттерны активности** студентов (время дня, день недели)
4. **Выявление проблемных подразделов** (где студенты тратят слишком много времени)
5. **Детекция накрутки** (количество заблокированных запросов)

### Дашборд для преподавателей

```python
@router.get("/analytics/subsections/{subsection_id}/stats")
async def get_subsection_stats(
    subsection_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role([Role.TEACHER, Role.ADMIN]))
) -> SubsectionStatsResponse:
    """
    Получить статистику по подразделу.
    """
    stats = await calculate_subsection_stats(session, subsection_id)
    
    return SubsectionStatsResponse(
        subsection_id=subsection_id,
        total_students=stats['total_students'],
        completed_students=stats['completed_students'],
        average_time_seconds=stats['average_time'],
        median_time_seconds=stats['median_time'],
        completion_rate=stats['completion_rate'],
        time_distribution=stats['time_distribution']  # Гистограмма времени
    )
```

## 🚀 План внедрения

### Этап 1: Подготовка БД (1 день)
- [x] Добавить поля в модель `Subsection`
- [x] Добавить поля в модель `SubsectionProgress`
- [x] Создать и применить миграции

### Этап 2: Backend API (2-3 дня)
- [ ] Реализовать эндпоинты трекинга
- [ ] Добавить валидацию и защиту от спама
- [ ] Реализовать логику расчета завершенности
- [ ] Добавить rate limiting
- [ ] Написать тесты

### Этап 3: Frontend (2 дня)
- [ ] Создать composable для трекинга
- [ ] Интегрировать в компоненты просмотра подразделов
- [ ] Добавить UI для отображения прогресса
- [ ] Обработка ошибок и edge cases

### Этап 4: Тестирование (1-2 дня)
- [ ] Unit тесты для backend
- [ ] Integration тесты
- [ ] Тестирование защиты от спама
- [ ] Нагрузочное тестирование

### Этап 5: Мониторинг и аналитика (1 день)
- [ ] Добавить логирование
- [ ] Создать дашборд для преподавателей
- [ ] Настроить алерты для подозрительной активности

## 📝 Рекомендации

### Настройки по умолчанию

```python
# config/settings.py

SUBSECTION_TRACKING = {
    "HEARTBEAT_INTERVAL_SECONDS": 15,  # Интервал heartbeat
    "MIN_TIME_SECONDS": 30,  # Минимальное время для засчитывания
    "MAX_SESSION_DURATION_HOURS": 2,  # Максимальная длительность сессии
    "RATE_LIMIT_PER_MINUTE": 4,  # Максимум запросов в минуту
    "BOT_DETECTION_ENABLED": True,  # Включить детекцию ботов
    "CAPTCHA_THRESHOLD_VIOLATIONS": 3,  # Количество нарушений для CAPTCHA
}
```

### Типы подразделов

- **TEXT**: `required_time_minutes` = ~5 минут на страницу
- **VIDEO**: `required_time_minutes` = длительность видео
- **PDF**: `required_time_minutes` = ~2 минуты на страницу
- **INTERACTIVE**: `required_time_minutes` = определяется автором

## 🎯 Выводы

**Рекомендуемый подход:** Вариант A (Ping-based tracking) с усиленной защитой от спама.

**Преимущества:**
- ✅ Простота реализации и поддержки
- ✅ Надежная защита от накрутки
- ✅ Гибкость настроек
- ✅ Хорошая аналитика

**Следующие шаги:**
1. Добавить поля в модели и провести миграцию
2. Реализовать базовые эндпоинты трекинга
3. Добавить защиту от спама
4. Интегрировать на фронтенде
5. Тестирование и мониторинг

