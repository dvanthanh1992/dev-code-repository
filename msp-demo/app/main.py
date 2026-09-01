from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api.routes import NO_CACHE_HEADERS, router
from app.config import get_settings
from app.services.kubernetes_topology import KubernetesTopology
from app.services.redis_store import RedisStore


APP_DIR = Path(__file__).resolve().parent
TEMPLATES = Jinja2Templates(directory=str(APP_DIR / "templates"))


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    redis_store = RedisStore(settings)
    topology = KubernetesTopology(settings)

    app.state.settings = settings
    app.state.redis_store = redis_store
    app.state.topology = topology

    await redis_store.ping()
    await topology.start()
    try:
        yield
    finally:
        await redis_store.close()


app = FastAPI(
    title="Tony - ArgoCD Demo",
    version=get_settings().app_version,
    docs_url="/docs",
    redoc_url=None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "PUT", "OPTIONS"],
    allow_headers=["*"],
)

app.mount(
    "/static",
    StaticFiles(directory=str(APP_DIR / "static")),
    name="static",
)
app.include_router(router)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return TEMPLATES.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "title": "Tony - ArgoCD Demo",
        },
        headers=NO_CACHE_HEADERS,
    )
