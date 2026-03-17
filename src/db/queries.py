from datetime import date
from decimal import Decimal

import asyncpg
from asyncpg import Pool, Record


async def save_meal(
    pool: Pool,
    *,
    user_id: int,
    username: str | None,
    chat_id: int,
    message_id: int | None,
    description: str,
    calories: Decimal,
    protein: Decimal,
    fat: Decimal,
    carbs: Decimal,
    fiber: Decimal,
) -> None:
    await pool.execute(
        """
        INSERT INTO meal_logs
            (user_id, username, chat_id, message_id, description, calories, protein, fat, carbs, fiber)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
        """,
        user_id, username, chat_id, message_id, description,
        calories, protein, fat, carbs, fiber,
    )


async def get_daily_summary(
    pool: Pool,
    *,
    user_id: int,
    chat_id: int,
    day: date,
) -> Record | None:
    return await pool.fetchrow(
        """
        SELECT
            COUNT(*)        AS meals,
            SUM(calories)   AS calories,
            SUM(protein)    AS protein,
            SUM(fat)        AS fat,
            SUM(carbs)      AS carbs,
            SUM(fiber)      AS fiber
        FROM meal_logs
        WHERE user_id = $1 AND chat_id = $2 AND logged_at::date = $3
        """,
        user_id, chat_id, day,
    )


async def save_weight(
    pool: Pool,
    *,
    user_id: int,
    username: str | None,
    chat_id: int,
    weight: Decimal,
    day: date,
) -> None:
    await pool.execute(
        """
        INSERT INTO weight_logs (user_id, username, chat_id, weight, date)
        VALUES ($1, $2, $3, $4, $5)
        ON CONFLICT (user_id, chat_id, date)
        DO UPDATE SET weight = EXCLUDED.weight, logged_at = NOW()
        """,
        user_id, username, chat_id, weight, day,
    )


async def get_weight_history(
    pool: Pool,
    *,
    user_id: int,
    chat_id: int,
    limit: int = 30,
) -> list[Record]:
    return await pool.fetch(
        """
        SELECT weight, date
        FROM weight_logs
        WHERE user_id = $1 AND chat_id = $2
        ORDER BY date DESC
        LIMIT $3
        """,
        user_id, chat_id, limit,
    )
