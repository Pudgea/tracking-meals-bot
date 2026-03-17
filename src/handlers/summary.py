from datetime import date

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from src.db.connection import get_pool
from src.db.queries import get_daily_summary

router = Router()


@router.message(Command("summary"))
async def handle_summary(message: Message) -> None:
    user = message.from_user
    if not user:
        return

    today = date.today()
    summary = await get_daily_summary(
        get_pool(),
        user_id=user.id,
        chat_id=message.chat.id,
        day=today,
    )

    if not summary or not summary["meals"]:
        await message.reply("Сегодня нет записей о питании.")
        return

    name = f"@{user.username}" if user.username else user.full_name

    await message.reply(
        f"📋 *{name}* — сводка за {today.strftime('%d.%m.%Y')}:\n\n"
        f"🍽 Приёмов пищи: *{summary['meals']}*\n"
        f"🔥 Калории: *{summary['calories'] or 0:.1f}* ккал\n"
        f"🥩 Белки: *{summary['protein'] or 0:.1f}* г\n"
        f"🧈 Жиры: *{summary['fat'] or 0:.1f}* г\n"
        f"🍞 Углеводы: *{summary['carbs'] or 0:.1f}* г\n"
        f"🌿 Клетчатка: *{summary['fiber'] or 0:.1f}* г",
        parse_mode="Markdown",
    )
