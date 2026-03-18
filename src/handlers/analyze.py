from datetime import date

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from src.db.connection import get_pool
from src.db.queries import get_daily_summary, get_profile, get_weight_for_date
from src.services.gemini import GeminiClient

router = Router()


@router.message(Command("analyze"))
async def handle_analyze(message: Message, gemini: GeminiClient) -> None:
    user = message.from_user
    if not user:
        return

    pool = get_pool()
    today = date.today()

    summary_row = await get_daily_summary(
        pool,
        user_id=user.id,
        chat_id=message.chat.id,
        day=today,
    )

    if not summary_row or not summary_row["meals"]:
        await message.reply(
            "Сегодня нет записей о питании. Сначала добавьте приёмы пищи и используйте /count, "
            "затем /summary и после этого /analyze."
        )
        return

    profile_row = await get_profile(pool, user_id=user.id, chat_id=message.chat.id)
    profile = {}
    if profile_row:
        profile["height_cm"] = profile_row["height_cm"]
        profile["goal"] = profile_row["goal"]

    weight_row = await get_weight_for_date(
        pool,
        user_id=user.id,
        chat_id=message.chat.id,
        day=today,
    )
    weight_kg = float(weight_row["weight"]) if weight_row and weight_row["weight"] is not None else None

    summary = {
        "meals": summary_row["meals"],
        "calories": summary_row["calories"],
        "protein": summary_row["protein"],
        "fat": summary_row["fat"],
        "carbs": summary_row["carbs"],
        "fiber": summary_row["fiber"],
    }

    status = await message.reply("Анализирую день...")

    try:
        analysis = await gemini.get_day_analysis(
            profile=profile,
            summary=summary,
            weight_kg=weight_kg,
            date_str=today.strftime("%d.%m.%Y"),
        )
    except Exception as exc:
        await status.edit_text(f"Ошибка: {exc}")
        return

    await status.edit_text(f"📊 *Анализ дня*\n\n{analysis}" or "Не удалось получить анализ.")
