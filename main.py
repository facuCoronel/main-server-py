import contextlib
import logging
from collections.abc import AsyncGenerator

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings
from src.api.routes.business_chat import router as business_chat_router
from src.infrastructure.persistence.postgres import connection as pg_conn

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings = get_settings()
    logger.info("Starting main-server-py")
    logger.info("PostgreSQL: %s:%s/%s", settings.postgres.host, settings.postgres.port, settings.postgres.database)

    pg_conn.get_engine()

    yield

    logger.info("Shutting down — disposing DB engines")
    await pg_conn.dispose_engine()


def create_app() -> FastAPI:
    app = FastAPI(
        title="main-server-py",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    app.include_router(business_chat_router)

    return app


app = create_app()

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
