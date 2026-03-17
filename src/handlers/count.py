from aiogram import Bot, Router
from aiogram.filters import Command
from aiogram.types import Message

from src.db.connection import get_pool
from src.db.queries import save_meal
from src.services.gemini import GeminiClient, NutritionData

router = Router()


def _format_reply(nutrition: NutritionData, username: str | None) -> str:
    name = f"@{username}" if username else "Неизвестный"
    return (
        f"✅ *{name}* — {nutrition.description}\n\n"
        f"🔥 Калории: *{nutrition.calories}* ккал\n"
        f"🥩 Белки: *{nutrition.protein}* г\n"
        f"🧈 Жиры: *{nutrition.fat}* г\n"
        f"🍞 Углеводы: *{nutrition.carbs}* г\n"
        f"🌿 Клетчатка: *{nutrition.fiber}* г"
    )


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
        await status.edit_text(f"Ошибка при анализе: {exc}")
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
        parse_mode="Markdown",
    )
