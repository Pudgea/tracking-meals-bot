import html
from decimal import Decimal

from aiogram import Bot, Router
from aiogram.filters import Command
from aiogram.types import Message

from src.db.connection import get_pool
from src.db.queries import save_meal
from src.services.gemini import GeminiClient, NutritionData, NutritionItem

router = Router()


def _breakdown_line(
    emoji: str,
    label: str,
    total: Decimal,
    field: str,
    items: tuple[NutritionItem, ...],
) -> str:
    line = f"{emoji} {label}: <b>{total}</b> г"
    contributors = [i for i in items if getattr(i, field) > 0]
    if len(contributors) > 1:
        parts = ", ".join(
            f"{html.escape(i.name)}: {getattr(i, field)}г" for i in contributors
        )
        line += f"\n   ↳ {parts}"
    return line


def _format_reply(nutrition: NutritionData, username: str | None) -> str:
    name = f"@{html.escape(username)}" if username else "Неизвестный"
    items = nutrition.breakdown

    cal_line = f"🔥 Калории: <b>{nutrition.calories}</b> ккал"
    if len(items) > 1:
        cal_parts = ", ".join(
            f"{html.escape(i.name)}: {i.calories}ккал" for i in items if i.calories > 0
        )
        cal_line += f"\n   ↳ {cal_parts}"

    lines = [
        f"✅ <b>{name}</b> — {html.escape(nutrition.description)}\n",
        cal_line,
        _breakdown_line("🥩", "Белки", nutrition.protein, "protein", items),
        _breakdown_line("🧈", "Жиры", nutrition.fat, "fat", items),
        _breakdown_line("🍞", "Углеводы", nutrition.carbs, "carbs", items),
        _breakdown_line("🌿", "Клетчатка", nutrition.fiber, "fiber", items),
    ]
    return "\n".join(lines)


@router.message(Command("count"))
async def handle_count(message: Message, bot: Bot, gemini: GeminiClient) -> None:
    replied = message.reply_to_message
    if not replied:
        await message.reply("Ответьте командой /count на сообщение с едой.")
        return

    image_bytes: bytes | None = None
    if replied.photo:
        largest_photo = replied.photo[-1]
        file = await bot.get_file(largest_photo.file_id)
        downloaded = await bot.download_file(file.file_path)
        image_bytes = downloaded.read()

    text = replied.caption or replied.text

    if not image_bytes and not text:
        await message.reply("В сообщении нет ни фото, ни текста для анализа.")
        return

    status = await message.reply("Анализирую...")

    try:
        nutrition = await gemini.analyze_meal(image_bytes, text)
    except Exception as exc:
        await status.edit_text(
            f"Ошибка при анализе: <code>{html.escape(str(exc))}</code>",
            parse_mode="HTML",
        )
        return

    meal_author = replied.from_user
    if not meal_author:
        await status.edit_text("Не удалось определить автора сообщения.")
        return

    await save_meal(
        get_pool(),
        user_id=meal_author.id,
        username=meal_author.username,
        chat_id=message.chat.id,
        message_id=replied.message_id,
        description=nutrition.description,
        calories=nutrition.calories,
        protein=nutrition.protein,
        fat=nutrition.fat,
        carbs=nutrition.carbs,
        fiber=nutrition.fiber,
    )

    await status.edit_text(
        _format_reply(nutrition, meal_author.username),
        parse_mode="HTML",
    )
