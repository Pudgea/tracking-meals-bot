from datetime import date

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.filters.callback_data import CallbackData
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from src.db.connection import get_pool
from src.db.queries import get_daily_meals, get_daily_summary

router = Router()


class MealCallback(CallbackData, prefix="meal"):
    user_id: int
    index: int


def _meals_keyboard(user_id: int, count: int) -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(
            text=f"🍽 Приём {i + 1}",
            callback_data=MealCallback(user_id=user_id, index=i).pack(),
        )
        for i in range(count)
    ]
    rows = [buttons[i:i + 3] for i in range(0, len(buttons), 3)]
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.message(Command("summary"))
async def handle_summary(message: Message) -> None:
    user = message.from_user
    if not user:
        return

    today = date.today()
    pool = get_pool()

    summary = await get_daily_summary(pool, user_id=user.id, chat_id=message.chat.id, day=today)
    if not summary or not summary["meals"]:
        await message.reply("Сегодня нет записей о питании.")
        return

    count = int(summary["meals"])
    name = f"@{user.username}" if user.username else user.full_name

    await message.reply(
        f"📋 *{name}* — сводка за {today.strftime('%d.%m.%Y')}:\n\n"
        f"🍽 Приёмов пищи: *{count}*\n"
        f"🔥 Калории: *{summary['calories'] or 0:.1f}* ккал\n"
        f"🥩 Белки: *{summary['protein'] or 0:.1f}* г\n"
        f"🧈 Жиры: *{summary['fat'] or 0:.1f}* г\n"
        f"🍞 Углеводы: *{summary['carbs'] or 0:.1f}* г\n"
        f"🌿 Клетчатка: *{summary['fiber'] or 0:.1f}* г",
        parse_mode="Markdown",
        reply_markup=_meals_keyboard(user.id, count),
    )


@router.callback_query(MealCallback.filter())
async def handle_meal_detail(callback: CallbackQuery, callback_data: MealCallback) -> None:
    user = callback.from_user
    if not user or user.id != callback_data.user_id:
        await callback.answer("Это не ваша сводка.", show_alert=True)
        return

    if not callback.message:
        await callback.answer()
        return

    today = date.today()
    meals = await get_daily_meals(
        get_pool(),
        user_id=user.id,
        chat_id=callback.message.chat.id,
        day=today,
    )

    idx = callback_data.index
    if idx >= len(meals):
        await callback.answer("Приём пищи не найден.", show_alert=True)
        return

    meal = meals[idx]
    time_str = meal["logged_at"].strftime("%H:%M")

    await callback.answer()
    await callback.message.answer(
        f"🍽 *Приём {idx + 1}* — {time_str}\n\n"
        f"📝 {meal['description'] or '—'}\n\n"
        f"🔥 Калории: *{meal['calories'] or 0}* ккал\n"
        f"🥩 Белки: *{meal['protein'] or 0}* г\n"
        f"🧈 Жиры: *{meal['fat'] or 0}* г\n"
        f"🍞 Углеводы: *{meal['carbs'] or 0}* г\n"
        f"🌿 Клетчатка: *{meal['fiber'] or 0}* г",
        parse_mode="Markdown",
    )
