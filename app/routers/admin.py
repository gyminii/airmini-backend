from fastapi import APIRouter, BackgroundTasks

from app.lib.rag.ingestion.core import ingest_documents_batch
from app.lib.rag.vectorstore import get_ingested_sources

router = APIRouter()

_status = {"running": False, "last": None}


async def _run_ingestion(sources: list[dict]):
    global _status
    _status["running"] = True
    try:
        await ingest_documents_batch(sources)
        _status["last"] = "success"
    except Exception as e:
        _status["last"] = f"error: {e}"
    finally:
        _status["running"] = False


@router.post("/ingest")
async def trigger_ingestion(background_tasks: BackgroundTasks):
    """Start document ingestion in the background using the default source list"""
    from scripts.ingest_documents import SOURCES

    if _status["running"]:
        return {"status": "already_running"}

    background_tasks.add_task(_run_ingestion, SOURCES)
    return {"status": "started", "sources_count": len(SOURCES)}


@router.get("/ingest/status")
async def ingestion_status():
    """Check ingestion progress"""
    return _status


@router.get("/ingest/sources")
async def ingested_sources():
    """List all sources currently in the vector store"""
    sources = await get_ingested_sources()
    return {"count": len(sources), "sources": sorted(sources)}
