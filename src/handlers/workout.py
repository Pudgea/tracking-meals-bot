import html
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
from src.db.queries import (
    delete_workout_template,
    get_daily_meals,
    get_profile,
    get_workout_template_by_id,
    get_workout_templates,
    save_workout,
    save_workout_template,
)
from src.services.gemini import GeminiClient

router = Router()


class WorkoutCallback(CallbackData, prefix="wkt"):
    action: str
    template_id: int = 0


def _templates_keyboard(templates: list) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(
            text=t["name"],
            callback_data=WorkoutCallback(action="select", template_id=t["id"]).pack(),
        )]
        for t in templates
    ]
    buttons.append([
        InlineKeyboardButton(
            text="✏️ Другое",
            callback_data=WorkoutCallback(action="other").pack(),
        )
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def _advise_after_workout(
    gemini: GeminiClient,
    user_id: int,
    username: str | None,
    chat_id: int,
    description: str,
) -> str:
    pool = get_pool()
    today = date.today()

    await save_workout(pool, user_id=user_id, username=username, chat_id=chat_id, description=description)

    profile_row = await get_profile(pool, user_id=user_id, chat_id=chat_id)
    profile = {}
    if profile_row:
        profile["height_cm"] = profile_row["height_cm"]
        profile["goal"] = profile_row["goal"]

    meals_rows = await get_daily_meals(pool, user_id=user_id, chat_id=chat_id, day=today)
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

    return await gemini.get_workout_advice(
        profile=profile,
        meals_today=meals_today,
        workout_description=description,
    )


@router.message(Command("workout"))
async def handle_workout(message: Message, gemini: GeminiClient) -> None:
    user = message.from_user
    if not user:
        return

    parts = (message.text or "").split(maxsplit=1)

    if len(parts) < 2:
        templates = await get_workout_templates(get_pool(), user_id=user.id, chat_id=message.chat.id)
        if not templates:
            await message.reply(
                "Нет сохранённых шаблонов.\n"
                "Запишите тренировку: /workout <описание>\n"
                "Сохраните шаблон: /save\\_workout <название> | <описание>"
            )
            return
        await message.reply("Выберите тренировку:", reply_markup=_templates_keyboard(templates))
        return

    description = parts[1]
    status = await message.reply("Записываю тренировку...")
    try:
        advice = await _advise_after_workout(gemini, user.id, user.username, message.chat.id, description)
    except Exception as exc:
        await status.edit_text(f"Ошибка: {exc}")
        return

    await status.edit_text(f"🏋️ <b>Тренировка записана</b>\n\n{html.escape(advice)}", parse_mode="HTML")


@router.callback_query(WorkoutCallback.filter(F.action == "select"))
async def handle_template_selected(
    callback: CallbackQuery,
    callback_data: WorkoutCallback,
    gemini: GeminiClient,
) -> None:
    user = callback.from_user
    if not user or not callback.message:
        await callback.answer()
        return

    template = await get_workout_template_by_id(
        get_pool(),
        template_id=callback_data.template_id,
        user_id=user.id,
        chat_id=callback.message.chat.id,
    )
    if not template:
        await callback.answer("Шаблон не найден.", show_alert=True)
        return

    await callback.answer()
    await callback.message.edit_text(
        f"🏋️ <b>{html.escape(template['name'])}</b>\nЗаписываю...", parse_mode="HTML"
    )

    try:
        advice = await _advise_after_workout(
            gemini, user.id, user.username, callback.message.chat.id, template["description"]
        )
    except Exception as exc:
        await callback.message.edit_text(f"Ошибка: {exc}")
        return

    await callback.message.edit_text(
        f"🏋️ <b>{html.escape(template['name'])}</b>\n\n{html.escape(advice)}", parse_mode="HTML"
    )


@router.callback_query(WorkoutCallback.filter(F.action == "other"))
async def handle_workout_other(callback: CallbackQuery) -> None:
    await callback.answer()
    if callback.message:
        await callback.message.edit_text(
            "Опишите тренировку командой:\n<code>/workout &lt;описание&gt;</code>",
            parse_mode="HTML",
        )


@router.message(Command("save_workout"))
async def handle_save_workout(message: Message) -> None:
    user = message.from_user
    if not user:
        return

    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2 or "|" not in parts[1]:
        await message.reply(
            "Использование: /save\\_workout <название> | <описание>\n"
            "Пример: /save\\_workout Грудь + плечи | жим 3x12, разводка...",
            parse_mode="Markdown",
        )
        return

    raw = parts[1]
    name, _, description = raw.partition("|")
    name = name.strip()
    description = description.strip()

    if not name or not description:
        await message.reply("Укажите и название, и описание тренировки.")
        return

    await save_workout_template(
        get_pool(),
        user_id=user.id,
        chat_id=message.chat.id,
        name=name,
        description=description,
    )
    await message.reply(f"✅ Шаблон *{name}* сохранён.", parse_mode="Markdown")


@router.message(Command("my_workouts"))
async def handle_my_workouts(message: Message) -> None:
    user = message.from_user
    if not user:
        return

    templates = await get_workout_templates(get_pool(), user_id=user.id, chat_id=message.chat.id)
    if not templates:
        await message.reply("Нет сохранённых шаблонов.")
        return

    lines = ["📋 *Мои шаблоны тренировок:*\n"]
    for t in templates:
        preview = t["description"][:80] + ("..." if len(t["description"]) > 80 else "")
        lines.append(f"*{t['id']}. {t['name']}*\n{preview}\n")

    lines.append("Удалить: /del\\_workout <id>")
    await message.reply("\n".join(lines), parse_mode="Markdown")


@router.message(Command("del_workout"))
async def handle_delete_workout(message: Message) -> None:
    user = message.from_user
    if not user:
        return

    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        await message.reply("Использование: /del\\_workout <id>", parse_mode="Markdown")
        return

    try:
        template_id = int(parts[1].strip())
    except ValueError:
        await message.reply("ID должен быть числом.")
        return

    deleted = await delete_workout_template(
        get_pool(),
        template_id=template_id,
        user_id=user.id,
        chat_id=message.chat.id,
    )

    if deleted:
        await message.reply(f"✅ Шаблон #{template_id} удалён.")
    else:
        await message.reply("Шаблон не найден или не принадлежит вам.")
