from contextlib import asynccontextmanager

from psycopg_pool import AsyncConnectionPool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from app.config import get_settings
from app.lib.graph import workflow

settings = get_settings()

CONNECTION_KWARGS = {
    "autocommit": True,
    "prepare_threshold": 0,
}


@asynccontextmanager
async def get_graph():
    db_uri = settings["database_url"]

    print(f"Connecting to: {db_uri}")
    try:
        async with AsyncConnectionPool(
            conninfo=db_uri,
            min_size=1,
            max_size=2,
            kwargs=CONNECTION_KWARGS,
        ) as pool:
            checkpointer = AsyncPostgresSaver(pool)
            print("⚙️  Running checkpointer.setup()...")
            await checkpointer.setup()
            print("Checkpointer ready, compiling graph...")
            graph = workflow.compile(checkpointer=checkpointer)
            print("Graph compiled successfully!")
            yield graph
    except Exception as e:
        print(f"Error creating graph: {e}")
        raise
