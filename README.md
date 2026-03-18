# Diet Bot

Telegram-бот для группового дневника питания. Анализирует фото и описания блюд через Gemini, считает КБЖУ и клетчатку, сохраняет в PostgreSQL.

## Команды

| Команда | Описание |
|---|---|
| `/count` | Ответить на сообщение с едой — бот отправит фото/текст в Gemini и сохранит КБЖУ |
| `/summary` | Сводка по калориям и БЖУ за сегодня |
| `/analyze` | Анализ дня по питанию и профилю: что улучшить (использовать после /summary) |
| `/profile` | Показать свой профиль (рост, цель) |
| `/set_profile <рост_см> [цель]` | Задать рост и цель. Пример: `/set_profile 180 Похудеть до 75 кг` |
| `/workout <описание>` | Записать тренировку; бот даст совет по питанию/восстановлению по профилю и приёмам пищи за день |
| `/weight <кг>` | Записать вес на сегодня. Пример: `/weight 74.2` |
| `/weight_stats` | История веса за последние 30 дней с трендом |

## Запуск

```bash
cp .env.example .env
# Заполнить BOT_TOKEN, GEMINI_API_KEY, POSTGRES_PASSWORD в .env

docker compose up --build -d
```

## Переменные окружения

| Переменная | Описание |
|---|---|
| `BOT_TOKEN` | Токен бота от @BotFather |
| `GEMINI_API_KEY` | API-ключ Google Gemini |
| `DATABASE_URL` | Строка подключения к PostgreSQL |
| `POSTGRES_PASSWORD` | Пароль для postgres-контейнера |

Получить ключ Gemini: https://aistudio.google.com/app/apikey
# tracking-meals-bot
