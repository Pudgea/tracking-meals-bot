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


async def run_migrations(pool: asyncpg.Pool) -> None:
    async with pool.acquire() as conn:
        await conn.execute(_CREATE_MEAL_LOGS)
        await conn.execute(_CREATE_WEIGHT_LOGS)
