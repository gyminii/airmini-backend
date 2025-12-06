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


# graph initializer
async def initialize_graph():
    global _graph_instance, _pool_instance

    db_uri = settings["database_url"]
    print(f"Initializing graph with database...")

    _pool_instance = AsyncConnectionPool(
        conninfo=db_uri,
        min_size=2,
        max_size=10,
        kwargs=CONNECTION_KWARGS,
        open=False,
    )
    # Explicit calling instead of auto opening
    # as we want to open on the lifespan
    await _pool_instance.open()
    print("Pool opened")

    checkpointer = AsyncPostgresSaver(_pool_instance)
    print("Setting up checkpointer...")
    await checkpointer.setup()
    print("Checkpointer ready")

    _graph_instance = workflow.compile(checkpointer=checkpointer)
    mermaid_code = _graph_instance.get_graph().draw_mermaid()
    #  mermaid_code = _graph_instance.get_graph().draw_mermaid_png(
    #     output_file_path="graph.png"
    # )
    print(mermaid_code)
    print("Graph compiled successfully!")


# Closing graph
async def shutdown_graph():
    global _pool_instance
    if _pool_instance:
        await _pool_instance.close()
        print("Connection pool closed")


def get_graph():
    if _graph_instance is None:
        raise RuntimeError("Graph not initialized. Call initialize_graph() first.")
    return _graph_instance
