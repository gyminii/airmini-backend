# scripts/test_checkpointer.py
import asyncio
from psycopg_pool import AsyncConnectionPool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

CONNECTION_KWARGS = {
    "autocommit": True,
    "prepare_threshold": 0,
}


async def test():
    db_uri = "postgresql://airmini_dev:airmini_dev@localhost:5432/airmini_development"

    print(f"1. Testing basic pool connection...")
    async with AsyncConnectionPool(
        conninfo=db_uri,
        min_size=1,
        max_size=2,
        kwargs=CONNECTION_KWARGS,
    ) as pool:
        print("✅ Pool created")

        # Test a simple query
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT 1")
                result = await cur.fetchone()
                print(f"✅ Pool works, result: {result}")

        print("2. Testing checkpointer...")
        checkpointer = AsyncPostgresSaver(pool)

        print("3. Running setup with timeout...")
        try:
            await asyncio.wait_for(checkpointer.setup(), timeout=5.0)
            print("✅ Setup completed!")
        except asyncio.TimeoutError:
            print("❌ Setup timed out after 5 seconds")

            # Check what tables exist
            async with pool.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        """
                        SELECT tablename FROM pg_tables 
                        WHERE schemaname = 'public' 
                        AND tablename LIKE 'checkpoint%'
                    """
                    )
                    tables = await cur.fetchall()
                    print(f"Checkpoint tables: {tables}")


if __name__ == "__main__":
    asyncio.run(test())
