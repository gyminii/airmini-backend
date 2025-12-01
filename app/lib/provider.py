from psycopg_pool import AsyncConnectionPool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from app.config import get_settings
from app.lib.graph import workflow

settings = get_settings()

CONNECTION_KWARGS = {
    "autocommit": True,
    "prepare_threshold": 0,
}

_graph_instance = None
_pool_instance = None


async def initialize_graph():
    """Initialize connection pool and compile graph"""
    global _graph_instance, _pool_instance

    db_uri = settings["database_url"]
    print(f"🔗 Initializing graph with database...")

    _pool_instance = AsyncConnectionPool(
        conninfo=db_uri,
        min_size=2,
        max_size=10,
        kwargs=CONNECTION_KWARGS,
        open=False,
    )
    #
    await _pool_instance.open()
    print("Pool opened")

    checkpointer = AsyncPostgresSaver(_pool_instance)
    print("Setting up checkpointer...")
    await checkpointer.setup()
    print("Checkpointer ready")

    _graph_instance = workflow.compile(checkpointer=checkpointer)
    print("Graph compiled successfully!")


async def shutdown_graph():
    """Close connection pool"""
    global _pool_instance
    if _pool_instance:
        await _pool_instance.close()
        print("Connection pool closed")


def get_graph():
    """Get the compiled graph instance"""
    if _graph_instance is None:
        raise RuntimeError("Graph not initialized. Call initialize_graph() first.")
    return _graph_instance
