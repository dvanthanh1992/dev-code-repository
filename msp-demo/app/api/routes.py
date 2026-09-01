from __future__ import annotations

import asyncio
import random
import time
import uuid

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse

from app.config import Settings
from app.models import DemoValueRequest
from app.services.kubernetes_topology import KubernetesTopology
from app.services.redis_store import RedisStore


router = APIRouter()

NO_CACHE_HEADERS = {
    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
    "Pragma": "no-cache",
    "Expires": "0",
}


def settings_from(request: Request) -> Settings:
    return request.app.state.settings


def redis_from(request: Request) -> RedisStore:
    return request.app.state.redis_store


def topology_from(request: Request) -> KubernetesTopology:
    return request.app.state.topology


@router.get("/api/config")
async def public_config(request: Request) -> JSONResponse:
    return JSONResponse(
        settings_from(request).public_config(),
        headers=NO_CACHE_HEADERS,
    )


@router.get("/api/ping")
async def ping(
    request: Request,
    source: str = Query(default="active", max_length=32),
) -> JSONResponse:
    settings = settings_from(request)
    delay_ms = random.randint(settings.min_latency_ms, settings.max_latency_ms)
    if delay_ms:
        await asyncio.sleep(delay_ms / 1000)

    failed = random.random() < settings.failure_rate
    request_id = uuid.uuid4().hex[:10]
    server_time_ms = int(time.time() * 1000)
    base_event = {
        "request_id": request_id,
        "ok": not failed,
        "version": settings.app_version,
        "hostname": settings.hostname,
        "source": source,
    }
    redis_result = await redis_from(request).record_request(base_event)

    payload = {
        **base_event,
        "color": settings.app_color,
        "commit": settings.app_commit,
        "message": settings.app_message,
        "environment": settings.app_environment,
        "track": settings.app_track,
        "simulated_latency_ms": delay_ms,
        "server_time_unix_ms": server_time_ms,
        "redis": redis_result,
    }
    headers = {
        **NO_CACHE_HEADERS,
        "X-App-Version": settings.app_version,
        "X-App-Color": settings.app_color,
        "X-Pod-Hostname": settings.hostname,
    }
    return JSONResponse(
        payload,
        status_code=503 if failed else 200,
        headers=headers,
    )


@router.get("/api/info")
async def info(request: Request) -> JSONResponse:
    settings = settings_from(request)
    return JSONResponse(
        {
            "version": settings.app_version,
            "color": settings.app_color,
            "hostname": settings.hostname,
            "commit": settings.app_commit,
            "message": settings.app_message,
            "environment": settings.app_environment,
            "track": settings.app_track,
            "rollout_mode": settings.rollout_mode,
            "preview_url_configured": bool(settings.preview_url),
            "failure_rate": settings.failure_rate,
            "latency_ms": {
                "min": settings.min_latency_ms,
                "max": settings.max_latency_ms,
            },
            "pod_discovery": {
                "enabled": settings.kubernetes_discovery_enabled,
                "namespace": settings.pod_namespace,
                "selector": settings.pod_label_selector,
                "rollout": settings.rollout_name,
            },
            "redis": {
                "host": settings.redis_host,
                "port": settings.redis_port,
                "db": settings.redis_db,
                "key_prefix": settings.redis_key_prefix,
                "required": settings.require_redis,
            },
        },
        headers=NO_CACHE_HEADERS,
    )


@router.get("/api/topology")
async def topology(request: Request) -> JSONResponse:
    data = await topology_from(request).snapshot()
    return JSONResponse(data, headers=NO_CACHE_HEADERS)


@router.get("/api/redis/state")
async def redis_state(request: Request) -> JSONResponse:
    data = await redis_from(request).snapshot()
    return JSONResponse(data, headers=NO_CACHE_HEADERS)


@router.put("/api/redis/value")
async def save_demo_value(
    body: DemoValueRequest,
    request: Request,
) -> JSONResponse:
    settings = settings_from(request)
    result = await redis_from(request).set_demo_value(
        body.value,
        writer_pod=settings.hostname,
        writer_version=settings.app_version,
    )
    status_code = 200 if result.get("connected") else 503
    return JSONResponse(
        result,
        status_code=status_code,
        headers=NO_CACHE_HEADERS,
    )


@router.get("/healthz")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/readyz")
async def ready(request: Request) -> JSONResponse:
    settings = settings_from(request)
    if settings.require_redis:
        redis_ok = await redis_from(request).ping()
        if not redis_ok:
            return JSONResponse(
                {
                    "status": "not-ready",
                    "dependency": "redis",
                    "error": redis_from(request).last_error,
                },
                status_code=503,
                headers=NO_CACHE_HEADERS,
            )
    return JSONResponse({"status": "ready"}, headers=NO_CACHE_HEADERS)
