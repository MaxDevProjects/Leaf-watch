"""FastAPI application factory."""

from __future__ import annotations

from fastapi import Depends, FastAPI

from .database import init_db
from .schemas import HealthResponse, HookResponse
from .services import IngestionService, TelegramNotifier


async def get_ingestion_service() -> IngestionService:
    service = IngestionService()
    try:
        yield service
    finally:
        await service.close()


async def get_telegram_notifier() -> TelegramNotifier:
    notifier = TelegramNotifier()
    try:
        yield notifier
    finally:
        await notifier.close()


def create_app() -> FastAPI:
    app = FastAPI(title="WebWatcher API", version="0.1.0")

    @app.on_event("startup")
    async def _startup() -> None:
        await init_db()

    @app.get("/api/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse()

    @app.post("/api/hook/run", response_model=HookResponse)
    async def hook(
        ingestion: IngestionService = Depends(get_ingestion_service),
        telegram: TelegramNotifier = Depends(get_telegram_notifier),
    ) -> HookResponse:
        ingested, items = await ingestion.ingest_all()
        notified = await telegram.notify(items)
        return HookResponse(ingested=ingested, notified=notified)

    return app


app = create_app()
