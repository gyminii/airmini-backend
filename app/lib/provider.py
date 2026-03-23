import asyncio

from psycopg_pool import AsyncConnectionPool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from app.config import get_settings
from app.lib.graph import workflow

settings = get_settings()

# Neon closes idle connections after ~5 min. Keep everything under 4 min.
_NEON_IDLE_TIMEOUT = 240  # seconds

CONNECTION_KWARGS = {
    "autocommit": True,
    "prepare_threshold": 0,
    "keepalives": 1,
    "keepalives_idle": 30,
    "keepalives_interval": 10,
    "keepalives_count": 5,
}

_graph_instance = None
_pool_instance = None
_ping_task = None


async def _keep_pool_alive():
    """Ping the pool every 4 min so Neon never sees a 5-min idle connection."""
    while True:
        await asyncio.sleep(_NEON_IDLE_TIMEOUT)
        if _pool_instance:
            try:
                await _pool_instance.check()
            except Exception as e:
                print(f"Pool health check failed: {e}")


# graph initializer
async def initialize_graph():
    global _graph_instance, _pool_instance, _ping_task

    db_uri = settings["database_url"]
    print(f"Initializing graph with database...")

    _pool_instance = AsyncConnectionPool(
        conninfo=db_uri,
        min_size=1,
        max_size=10,
        kwargs=CONNECTION_KWARGS,
        max_idle=_NEON_IDLE_TIMEOUT,  # recycle before Neon kills them
        reconnect_timeout=10,
        open=False,
    )
    await _pool_instance.open()
    print("Pool opened")

    _ping_task = asyncio.create_task(_keep_pool_alive())

    checkpointer = AsyncPostgresSaver(_pool_instance)
    print("Setting up checkpointer...")
    await checkpointer.setup()
    print("Checkpointer ready")

    _graph_instance = workflow.compile(checkpointer=checkpointer)
    mermaid_code = _graph_instance.get_graph().draw_mermaid()
    print(mermaid_code)
    print("Graph compiled successfully!")


# Closing graph
async def shutdown_graph():
    global _pool_instance, _ping_task
    if _ping_task:
        _ping_task.cancel()
    if _pool_instance:
        await _pool_instance.close()
        print("Connection pool closed")


def get_graph():
    if _graph_instance is None:
        raise RuntimeError("Graph not initialized. Call initialize_graph() first.")
    return _graph_instance
