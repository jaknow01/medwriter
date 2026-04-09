"""Add message_type and summary columns to messages table.

Safe to run multiple times — uses IF NOT EXISTS.

Usage:
    python -m scripts.migrate_add_message_columns
"""

import asyncio
import os

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


async def migrate():
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://medwriter:password@localhost:5432/medwriter_db",
    )

    engine = create_async_engine(database_url)

    async with engine.begin() as conn:
        await conn.execute(text(
            "ALTER TABLE messages ADD COLUMN IF NOT EXISTS "
            "message_type VARCHAR(20) DEFAULT 'simple'"
        ))
        await conn.execute(text(
            "ALTER TABLE messages ADD COLUMN IF NOT EXISTS "
            "summary TEXT"
        ))
        print("Migration complete: message_type and summary columns added.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(migrate())
