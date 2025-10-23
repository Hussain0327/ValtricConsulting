from contextlib import asynccontextmanager
import asyncio
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.settings import settings
from app.db import init_db
from app.routers import health as health_router
from app.routers import deals as deals_router
from app.routers import analyze as analyze_router
from app.routers import chat as chat_router
from app.routers import foundry as foundry_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="Valtric Consulting AI", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_deadline(request: Request, call_next):
    try:
        async with asyncio.timeout(settings.request_timeout_seconds):
            return await call_next(request)
    except TimeoutError:
        return JSONResponse({"error": "deadline_exceeded"}, status_code=504)

app.include_router(health_router.router)
app.include_router(deals_router.router)
app.include_router(analyze_router.router)
app.include_router(chat_router.router)
app.include_router(foundry_router.router)
