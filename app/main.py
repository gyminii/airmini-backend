from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.lib.provider import initialize_graph, shutdown_graph
from app.routers import api_router


@asynccontextmanager
async def lifespan(_app: FastAPI):
    print("Application startup")
    await initialize_graph()

    yield

    print("Application shutdown")
    await shutdown_graph()


app = FastAPI(title="Airmini API", version="1.0.0", lifespan=lifespan)

# uv run uvicorn app.main:app --reload
# https://rudaks.tistory.com/entry/langgraph-%EA%B7%B8%EB%9E%98%ED%94%84%EB%A5%BC-%EB%B9%84%EB%8F%99%EA%B8%B0%EB%A1%9C-%EC%8B%A4%ED%96%89%ED%95%98%EB%8A%94-%EB%B0%A9%EB%B2%95
# cors
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Binding all routers
app.include_router(api_router)


@app.get("/")
async def root():
    return {"message": "Airmini API", "version": "1.0.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}
