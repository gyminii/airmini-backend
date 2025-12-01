# test_db_connection.py
import asyncio
from psycopg_pool import AsyncConnectionPool

from app.config import get_settings

settings = get_settings()


async def test_connection():
    db_uri = settings["database_url"]
    print(f"Testing connection to: {db_uri}")

    try:
        async with AsyncConnectionPool(db_uri, min_size=1, max_size=1) as pool:
            async with pool.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("SELECT 1")
                    result = await cur.fetchone()
                    print(f"Success! Result: {result}")
    except Exception as e:
        print(f"Failed: {e}")


asyncio.run(test_connection())
