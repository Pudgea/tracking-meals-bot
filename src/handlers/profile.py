from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from src.db.connection import get_pool
from src.db.queries import get_profile, set_profile

router = Router()


@router.message(Command("profile"))
async def handle_profile(message: Message) -> None:
    user = message.from_user
    if not user:
        return

    profile = await get_profile(
        get_pool(),
        user_id=user.id,
        chat_id=message.chat.id,
    )

    if not profile or (profile["height_cm"] is None and not profile["goal"]):
        await message.reply(
            "Профиль не заполнен. Используйте /set_profile <рост_см> <цель>\n"
            "Пример: /set_profile 180 Похудеть до 75 кг"
        )
        return

    height = f"{profile['height_cm']} см" if profile["height_cm"] else "—"
    goal = profile["goal"] or "—"
    name = f"@{user.username}" if user.username else user.full_name

    await message.reply(
        f"👤 *{name}* — профиль\n\n"
        f"Рост: *{height}*\n"
        f"Цель: *{goal}*",
        parse_mode="Markdown",
    )


@router.message(Command("set_profile"))
async def handle_set_profile(message: Message) -> None:
    user = message.from_user
    if not user:
        return

    text = (message.text or "").strip()
    parts = text.split(maxsplit=2)

    if len(parts) < 2:
        await message.reply(
            "Использование: /set_profile <рост_см> [цель]\n"
            "Пример: /set_profile 180 Похудеть до 75 кг"
        )
        return

    try:
        height_cm = int(parts[1])
    except ValueError:
        await message.reply("Рост должен быть числом (см). Пример: /set_profile 180 Цель")
        return

    if height_cm <= 0 or height_cm > 300:
        await message.reply("Укажите рост в см от 1 до 300.")
        return

    goal = parts[2].strip() if len(parts) > 2 else None
    if goal == "":
        goal = None

    await set_profile(
        get_pool(),
        user_id=user.id,
        chat_id=message.chat.id,
        height_cm=height_cm,
        goal=goal,
    )

    goal_text = f", цель: {goal}" if goal else ""
    await message.reply(f"✅ Профиль обновлён: рост {height_cm} см{goal_text}.")
