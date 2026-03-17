import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Config:
    bot_token: str
    gemini_api_key: str
    database_url: str


def load_config() -> Config:
    return Config(
        bot_token=os.environ["BOT_TOKEN"],
        gemini_api_key=os.environ["GEMINI_API_KEY"],
        database_url=os.environ["DATABASE_URL"],
    )
