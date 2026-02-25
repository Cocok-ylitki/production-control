from contextlib import asynccontextmanager

from fastapi import FastAPI
from src.api.v1.routers import analytics, batches, products, tasks, webhooks
from src.core.exceptions import NotFoundError

V1_PREFIX = "/api/v1"


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="Production Control", lifespan=lifespan)


@app.get("/health")
async def health():
    """Healthcheck для Docker и балансировщиков."""
    return {"status": "ok"}


@app.exception_handler(NotFoundError)
async def not_found_handler(request, exc: NotFoundError):
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=404, content={"detail": exc.message})


app.include_router(analytics.router, prefix=V1_PREFIX)
app.include_router(batches.router, prefix=V1_PREFIX)
app.include_router(products.router, prefix=V1_PREFIX)
app.include_router(tasks.router, prefix=V1_PREFIX)
app.include_router(webhooks.router, prefix=V1_PREFIX)
