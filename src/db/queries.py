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


async def get_profile(
    pool: Pool,
    *,
    user_id: int,
    chat_id: int,
) -> Record | None:
    return await pool.fetchrow(
        "SELECT height_cm, goal FROM profiles WHERE user_id = $1 AND chat_id = $2",
        user_id, chat_id,
    )


async def set_profile(
    pool: Pool,
    *,
    user_id: int,
    chat_id: int,
    height_cm: int | None,
    goal: str | None,
) -> None:
    await pool.execute(
        """
        INSERT INTO profiles (user_id, chat_id, height_cm, goal)
        VALUES ($1, $2, $3, $4)
        ON CONFLICT (user_id, chat_id)
        DO UPDATE SET height_cm = COALESCE(EXCLUDED.height_cm, profiles.height_cm),
                      goal = COALESCE(EXCLUDED.goal, profiles.goal),
                      updated_at = NOW()
        """,
        user_id, chat_id, height_cm, goal,
    )


async def get_daily_meals(
    pool: Pool,
    *,
    user_id: int,
    chat_id: int,
    day: date,
) -> list[Record]:
    return await pool.fetch(
        """
        SELECT description, calories, protein, fat, carbs, fiber, logged_at
        FROM meal_logs
        WHERE user_id = $1 AND chat_id = $2 AND logged_at::date = $3
        ORDER BY logged_at
        """,
        user_id, chat_id, day,
    )


async def get_weight_for_date(
    pool: Pool,
    *,
    user_id: int,
    chat_id: int,
    day: date,
) -> Record | None:
    return await pool.fetchrow(
        "SELECT weight FROM weight_logs WHERE user_id = $1 AND chat_id = $2 AND date = $3",
        user_id, chat_id, day,
    )


async def save_workout(
    pool: Pool,
    *,
    user_id: int,
    username: str | None,
    chat_id: int,
    description: str,
) -> None:
    await pool.execute(
        """
        INSERT INTO workout_logs (user_id, username, chat_id, description)
        VALUES ($1, $2, $3, $4)
        """,
        user_id, username, chat_id, description,
    )


async def get_daily_workouts(
    pool: Pool,
    *,
    user_id: int,
    chat_id: int,
    day: date,
) -> list[Record]:
    return await pool.fetch(
        """
        SELECT description, logged_at
        FROM workout_logs
        WHERE user_id = $1 AND chat_id = $2 AND logged_at::date = $3
        ORDER BY logged_at
        """,
        user_id, chat_id, day,
    )


async def save_workout_template(
    pool: Pool,
    *,
    user_id: int,
    chat_id: int,
    name: str,
    description: str,
) -> None:
    await pool.execute(
        """
        INSERT INTO workout_templates (user_id, chat_id, name, description)
        VALUES ($1, $2, $3, $4)
        """,
        user_id, chat_id, name, description,
    )


async def get_workout_templates(
    pool: Pool,
    *,
    user_id: int,
    chat_id: int,
) -> list[Record]:
    return await pool.fetch(
        """
        SELECT id, name, description
        FROM workout_templates
        WHERE user_id = $1 AND chat_id = $2
        ORDER BY created_at
        """,
        user_id, chat_id,
    )


async def get_workout_template_by_id(
    pool: Pool,
    *,
    template_id: int,
    user_id: int,
    chat_id: int,
) -> Record | None:
    return await pool.fetchrow(
        """
        SELECT id, name, description
        FROM workout_templates
        WHERE id = $1 AND user_id = $2 AND chat_id = $3
        """,
        template_id, user_id, chat_id,
    )


async def delete_workout_template(
    pool: Pool,
    *,
    template_id: int,
    user_id: int,
    chat_id: int,
) -> bool:
    result = await pool.execute(
        """
        DELETE FROM workout_templates
        WHERE id = $1 AND user_id = $2 AND chat_id = $3
        """,
        template_id, user_id, chat_id,
    )
    return result.endswith("1")
