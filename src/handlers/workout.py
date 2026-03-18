from datetime import date

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from src.db.connection import get_pool
from src.db.queries import get_daily_meals, get_profile, save_workout
from src.services.gemini import GeminiClient

router = Router()


@router.message(Command("workout"))
async def handle_workout(message: Message, gemini: GeminiClient) -> None:
    user = message.from_user
    if not user:
        return

    text = (message.text or "").strip()
    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        await message.reply(
            "Напишите, что делали на тренировке.\n"
            "Пример: /workout Бег 5 км, силовая 40 мин"
        )
        return

    workout_description = parts[1]

    pool = get_pool()
    profile_row = await get_profile(pool, user_id=user.id, chat_id=message.chat.id)
    profile = {}
    if profile_row:
        profile["height_cm"] = profile_row["height_cm"]
        profile["goal"] = profile_row["goal"]

    today = date.today()
    meals_rows = await get_daily_meals(
        pool,
        user_id=user.id,
        chat_id=message.chat.id,
        day=today,
    )
    meals_today = [
        {
            "description": r["description"] or "",
            "calories": r["calories"],
            "protein": r["protein"],
            "fat": r["fat"],
            "carbs": r["carbs"],
            "logged_at": r["logged_at"],
        }
        for r in meals_rows
    ]

    await save_workout(
        pool,
        user_id=user.id,
        username=user.username,
        chat_id=message.chat.id,
        description=workout_description,
    )

    status = await message.reply("Готовлю рекомендации...")

    try:
        advice = await gemini.get_workout_advice(
            profile=profile,
            meals_today=meals_today,
            workout_description=workout_description,
        )
    except Exception as exc:
        await status.edit_text(f"Ошибка: {exc}")
        return

    await status.edit_text(f"🏋️ *После тренировки*\n\n{advice}" or "Не удалось получить совет.")
