# НРИ-клуб — Telegram-бот

Production-ready бот для управления клубом настольных ролевых игр.

## Стек

- Python 3.12
- aiogram 3.x
- PostgreSQL + SQLAlchemy (async)
- APScheduler
- Alembic
- Docker Compose

## Быстрый старт (Docker)

1. Скопируйте `.env.example` в `.env` и укажите:
   - `BOT_TOKEN` — токен от [@BotFather](https://t.me/BotFather)
   - `ADMIN_TELEGRAM_IDS` — ваш Telegram ID (можно несколько через запятую)

2. Запуск:

```bash
docker compose up -d db
docker compose --profile migrate run --rm migrate
docker compose up -d bot
```

3. Напишите боту `/start` в Telegram.

## Локальный запуск

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
docker compose up -d db
alembic upgrade head
python -m bot.main
```

## Команды

| Команда | Описание |
|---------|----------|
| `/start` | Ближайшие игры |
| `/profile` | Профиль игрока |
| `/games` | Список игр |
| `/my_games` | Мои записи |
| `/rating` | Рейтинг по баллам |
| `/create_game` | Создать игру (мастер/админ) |
| `/admin` | Панель администратора |

## Роли

- **player** — запись на игры, профиль, баллы
- **master** — создание игр
- **admin** — управление ролями, играми, баллами, экспорт

Первый вход с ID из `ADMIN_TELEGRAM_IDS` получает роль admin.

## Архитектура

```
bot/           — конфиг, main, утилиты
handlers/      — обработчики команд и callback
services/      — бизнес-логика
repositories/  — доступ к БД
models/        — ORM-модели
keyboards/     — Inline/Reply клавиатуры
middlewares/   — сессия БД, пользователь, логи
scheduler/     — APScheduler (напоминания, старт/финиш игр)
database/      — подключение к PostgreSQL
alembic/       — миграции
```

## Планировщик

Каждую минуту: напоминания (за 1 день, 12 ч, 1 ч, старт) и запуск игр.  
Каждые 5 минут: завершение игр (4 ч после старта), архив, начисление баллов.

## Деплой на Railway

По логам контейнер падает, если **не заданы переменные окружения**. В проекте Railway → **Variables** добавьте:

| Переменная | Значение |
|------------|----------|
| `BOT_TOKEN` | Токен от [@BotFather](https://t.me/BotFather) |
| `DATABASE_URL` | URL PostgreSQL (см. ниже) |
| `ADMIN_TELEGRAM_IDS` | Ваш Telegram ID |
| `TIMEZONE` | `Europe/Moscow` (опционально) |

**Важно:** переменные на скриншоте у сервиса **Postgres** бот **не видит**.  
Нужно открыть сервис **bot** (ваш GitHub-репозиторий) → **Variables** → добавить:

- `BOT_TOKEN` — вручную
- `DATABASE_URL` — **Add Reference** → Postgres → `DATABASE_URL` (внутренний URL)
- `ADMIN_TELEGRAM_IDS` — **числовой** Telegram ID (не `@username`). Узнать: [@userinfobot](https://t.me/userinfobot)

**База данных:**

1. В проекте Railway добавьте сервис **PostgreSQL**.
2. В сервисе **бота** создайте `DATABASE_URL` через Reference на Postgres.
3. Railway выдаёт `postgresql://...` — бот сам преобразует в `postgresql+asyncpg://...`.

**После деплоя** выполните миграции (один раз), в Railway → Shell или отдельным одноразовым запуском:

```bash
alembic upgrade head
```

Или добавьте в **Start Command** перед ботом: `alembic upgrade head && python -m bot.main`

## Безопасность

- Не публикуйте `.env` и токен бота в репозитории.
- Если токен утёк — перевыпустите его в BotFather.
