import asyncpg

_CREATE_MEAL_LOGS = """
CREATE TABLE IF NOT EXISTS meal_logs (
    id          SERIAL PRIMARY KEY,
    user_id     BIGINT NOT NULL,
    username    TEXT,
    chat_id     BIGINT NOT NULL,
    message_id  BIGINT,
    description TEXT,
    calories    NUMERIC(8, 2),
    protein     NUMERIC(6, 2),
    fat         NUMERIC(6, 2),
    carbs       NUMERIC(6, 2),
    fiber       NUMERIC(6, 2),
    logged_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""

_CREATE_WEIGHT_LOGS = """
CREATE TABLE IF NOT EXISTS weight_logs (
    id         SERIAL PRIMARY KEY,
    user_id    BIGINT NOT NULL,
    username   TEXT,
    chat_id    BIGINT NOT NULL,
    weight     NUMERIC(5, 2) NOT NULL,
    date       DATE NOT NULL DEFAULT CURRENT_DATE,
    logged_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, chat_id, date)
);
"""

_CREATE_PROFILES = """
CREATE TABLE IF NOT EXISTS profiles (
    user_id    BIGINT NOT NULL,
    chat_id    BIGINT NOT NULL,
    height_cm  INTEGER,
    goal       TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, chat_id)
);
"""

_CREATE_WORKOUT_LOGS = """
CREATE TABLE IF NOT EXISTS workout_logs (
    id          SERIAL PRIMARY KEY,
    user_id     BIGINT NOT NULL,
    username    TEXT,
    chat_id     BIGINT NOT NULL,
    description TEXT NOT NULL,
    logged_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""

_CREATE_WORKOUT_TEMPLATES = """
CREATE TABLE IF NOT EXISTS workout_templates (
    id          SERIAL PRIMARY KEY,
    user_id     BIGINT NOT NULL,
    chat_id     BIGINT NOT NULL,
    name        TEXT NOT NULL,
    description TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""


async def run_migrations(pool: asyncpg.Pool) -> None:
    async with pool.acquire() as conn:
        await conn.execute(_CREATE_MEAL_LOGS)
        await conn.execute(_CREATE_WEIGHT_LOGS)
        await conn.execute(_CREATE_PROFILES)
        await conn.execute(_CREATE_WORKOUT_LOGS)
        await conn.execute(_CREATE_WORKOUT_TEMPLATES)
