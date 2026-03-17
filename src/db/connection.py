import asyncpg
from asyncpg import Pool

_pool: Pool | None = None


async def create_pool(database_url: str) -> Pool:
    global _pool
    _pool = await asyncpg.create_pool(database_url)
    return _pool


def get_pool() -> Pool:
    if _pool is None:
        raise RuntimeError("Database pool is not initialized")
    return _pool
