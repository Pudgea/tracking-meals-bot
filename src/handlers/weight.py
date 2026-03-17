from datetime import date
from decimal import Decimal, InvalidOperation

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from src.db.connection import get_pool
from src.db.queries import get_weight_history, save_weight

router = Router()


@router.message(Command("weight"))
async def handle_weight(message: Message) -> None:
    user = message.from_user
    if not user:
        return

    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        await message.reply("Использование: /weight <значение>\nПример: /weight 75.5")
        return

    try:
        weight = Decimal(parts[1].replace(",", "."))
    except InvalidOperation:
        await message.reply("Неверный формат веса. Пример: /weight 75.5")
        return

    today = date.today()

    await save_weight(
        get_pool(),
        user_id=user.id,
        username=user.username,
        chat_id=message.chat.id,
        weight=weight,
        day=today,
    )

    await message.reply(
        f"✅ Вес *{weight}* кг записан на {today.strftime('%d.%m.%Y')}.",
        parse_mode="Markdown",
    )


@router.message(Command("weight_stats"))
async def handle_weight_stats(message: Message) -> None:
    user = message.from_user
    if not user:
        return

    records = await get_weight_history(
        get_pool(),
        user_id=user.id,
        chat_id=message.chat.id,
    )

    if not records:
        await message.reply("Нет записей о весе.")
        return

    records = list(reversed(records))

    name = f"@{user.username}" if user.username else user.full_name
    lines = [f"📊 *{name}* — история веса:\n"]

    for record in records:
        lines.append(f"{record['date'].strftime('%d.%m')} — *{record['weight']}* кг")

    weights = [float(r["weight"]) for r in records]
    avg = sum(weights) / len(weights)
    lines.append(f"\nСредний вес: *{avg:.1f}* кг")
    lines.append(f"Мин / Макс: *{min(weights):.1f}* / *{max(weights):.1f}* кг")

    if len(weights) >= 2:
        trend = weights[-1] - weights[0]
        arrow = "📈" if trend > 0 else "📉" if trend < 0 else "➡️"
        lines.append(f"Тренд: {arrow} {trend:+.1f} кг")

    await message.reply("\n".join(lines), parse_mode="Markdown")
