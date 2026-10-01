from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import health, orders, webhooks
from app.repositories import orders as orders_repo


@asynccontextmanager
async def lifespan(_: FastAPI):
    await orders_repo.ensure_indexes()
    yield


app = FastAPI(title="RAYY take-home", lifespan=lifespan)

app.include_router(health.router)
app.include_router(orders.router)
app.include_router(webhooks.router)
