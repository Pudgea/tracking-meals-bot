import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from src.config import load_config
from src.db.connection import create_pool
from src.db.migrations import run_migrations
from src.handlers.analyze import router as analyze_router
from src.handlers.count import router as count_router
from src.handlers.profile import router as profile_router
from src.handlers.summary import router as summary_router
from src.handlers.weight import router as weight_router
from src.handlers.workout import router as workout_router
from src.services.gemini import GeminiClient

logging.basicConfig(level=logging.INFO)


async def main() -> None:
    config = load_config()

    pool = await create_pool(config.database_url)
    await run_migrations(pool)

    gemini = GeminiClient(config.gemini_api_key, config.gemini_model)

    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
    )

    dp = Dispatcher()
    dp.include_router(count_router)
    dp.include_router(summary_router)
    dp.include_router(analyze_router)
    dp.include_router(profile_router)
    dp.include_router(workout_router)
    dp.include_router(weight_router)

    await dp.start_polling(bot, gemini=gemini)


if __name__ == "__main__":
    asyncio.run(main())
