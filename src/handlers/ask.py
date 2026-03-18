import html
from datetime import date

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from src.db.connection import get_pool
from src.db.queries import (
    get_daily_meals,
    get_daily_workouts,
    get_profile,
    get_weight_for_date,
)
from src.services.gemini import GeminiClient

router = Router()


@router.message(Command("ask"))
async def handle_ask(message: Message, gemini: GeminiClient) -> None:
    user = message.from_user
    if not user:
        return

    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        await message.reply(
            "Задайте вопрос о питании:\n\n"
            "/ask что мне лучше сейчас съесть?\n"
            "/ask если съем банан и 200г куриной грудки, сколько это калорий?\n"
            "/ask хватает ли мне белка за сегодня?"
        )
        return

    question = parts[1]
    pool = get_pool()
    today = date.today()

    profile_row = await get_profile(pool, user_id=user.id, chat_id=message.chat.id)
    profile = {}
    if profile_row:
        profile["height_cm"] = profile_row["height_cm"]
        profile["goal"] = profile_row["goal"]

    weight_row = await get_weight_for_date(
        pool, user_id=user.id, chat_id=message.chat.id, day=today
    )
    weight_kg = float(weight_row["weight"]) if weight_row and weight_row["weight"] is not None else None

    meals_rows = await get_daily_meals(pool, user_id=user.id, chat_id=message.chat.id, day=today)
    meals_today = [
        {
            "description": r["description"] or "",
            "calories": r["calories"],
            "protein": r["protein"],
            "fat": r["fat"],
            "carbs": r["carbs"],
            "fiber": r["fiber"],
            "logged_at": r["logged_at"],
        }
        for r in meals_rows
    ]

    workouts_rows = await get_daily_workouts(
        pool, user_id=user.id, chat_id=message.chat.id, day=today
    )
    workouts_today = [r["description"] for r in workouts_rows]

    status = await message.reply("Думаю...")

    try:
        answer = await gemini.ask_question(
            profile=profile,
            meals_today=meals_today,
            weight_kg=weight_kg,
            workouts_today=workouts_today,
            question=question,
        )
    except Exception as exc:
        await status.edit_text(f"Ошибка: {exc}")
        return

    await status.edit_text(f"💬 {html.escape(answer)}", parse_mode="HTML")
