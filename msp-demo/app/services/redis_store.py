from __future__ import annotations

import json
import time
from typing import Any

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.config import Settings


class RedisStore:
    """Shared state used to prove continuity while application pods are replaced."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            password=settings.redis_password,
            ssl=settings.redis_ssl,
            decode_responses=True,
            socket_connect_timeout=1.5,
            socket_timeout=2.0,
            health_check_interval=15,
        )
        self.last_error: str | None = None

    def key(self, suffix: str) -> str:
        return f"{self.settings.redis_key_prefix}:{suffix}"

    async def ping(self) -> bool:
        try:
            result = await self.client.ping()
            self.last_error = None
            return bool(result)
        except RedisError as exc:
            self.last_error = str(exc)
            return False

    async def record_request(self, event: dict[str, Any]) -> dict[str, Any]:
        now_ms = int(time.time() * 1000)
        stored_event = {
            "request_id": str(event.get("request_id", "")),
            "ok": bool(event.get("ok", False)),
            "version": str(event.get("version", "unknown")),
            "hostname": str(event.get("hostname", "unknown")),
            "source": str(event.get("source", "active")),
            "server_time_unix_ms": now_ms,
        }

        try:
            pipe = self.client.pipeline(transaction=True)
            pipe.incr(self.key("sequence"))
            pipe.hincrby(self.key("stats"), "total_requests", 1)
            pipe.hincrby(
                self.key("stats"),
                "errors",
                0 if stored_event["ok"] else 1,
            )
            pipe.hsetnx(self.key("stats"), "first_seen_unix_ms", now_ms)
            pipe.hset(
                self.key("stats"),
                mapping={
                    "last_seen_unix_ms": now_ms,
                    "last_writer_pod": stored_event["hostname"],
                    "last_writer_version": stored_event["version"],
                    "last_request_id": stored_event["request_id"],
                },
            )
            pipe.sadd(self.key("writers"), stored_event["hostname"])
            pipe.hincrby(
                self.key("versions"),
                stored_event["version"],
                1,
            )
            pipe.lpush(
                self.key("events"),
                json.dumps(stored_event, separators=(",", ":")),
            )
            pipe.ltrim(
                self.key("events"),
                0,
                self.settings.redis_max_events - 1,
            )
            results = await pipe.execute()
            self.last_error = None
            return {
                "connected": True,
                "sequence": int(results[0]),
                "total_requests": int(results[1]),
                "writer_pod": stored_event["hostname"],
                "writer_version": stored_event["version"],
            }
        except RedisError as exc:
            self.last_error = str(exc)
            return {
                "connected": False,
                "sequence": None,
                "total_requests": None,
                "writer_pod": stored_event["hostname"],
                "writer_version": stored_event["version"],
                "error": self.last_error,
            }

    async def snapshot(self, event_limit: int = 8) -> dict[str, Any]:
        event_limit = max(1, min(event_limit, 50))
        try:
            pipe = self.client.pipeline(transaction=False)
            pipe.get(self.key("sequence"))
            pipe.hgetall(self.key("stats"))
            pipe.scard(self.key("writers"))
            pipe.llen(self.key("events"))
            pipe.hgetall(self.key("versions"))
            pipe.hgetall(self.key("demo-value"))
            pipe.lrange(self.key("events"), 0, event_limit - 1)
            (
                sequence,
                stats,
                writer_count,
                stored_event_count,
                versions,
                demo_value,
                raw_events,
            ) = await pipe.execute()

            events: list[dict[str, Any]] = []
            for raw_event in raw_events:
                try:
                    parsed = json.loads(raw_event)
                    if isinstance(parsed, dict):
                        events.append(parsed)
                except (TypeError, json.JSONDecodeError):
                    continue

            self.last_error = None
            return {
                "connected": True,
                "sequence": int(sequence or 0),
                "stats": {
                    "total_requests": int(stats.get("total_requests", 0)),
                    "errors": int(stats.get("errors", 0)),
                    "first_seen_unix_ms": int(
                        stats.get("first_seen_unix_ms", 0)
                    ),
                    "last_seen_unix_ms": int(stats.get("last_seen_unix_ms", 0)),
                    "last_writer_pod": stats.get("last_writer_pod", ""),
                    "last_writer_version": stats.get(
                        "last_writer_version", ""
                    ),
                    "last_request_id": stats.get("last_request_id", ""),
                },
                "writer_pods": int(writer_count or 0),
                "stored_events": int(stored_event_count or 0),
                "versions": {
                    key: int(value) for key, value in versions.items()
                },
                "demo_value": {
                    "value": demo_value.get("value", ""),
                    "updated_at_unix_ms": int(
                        demo_value.get("updated_at_unix_ms", 0)
                    ),
                    "writer_pod": demo_value.get("writer_pod", ""),
                    "writer_version": demo_value.get("writer_version", ""),
                },
                "events": events,
            }
        except RedisError as exc:
            self.last_error = str(exc)
            return {
                "connected": False,
                "sequence": None,
                "stats": {},
                "writer_pods": 0,
                "stored_events": 0,
                "versions": {},
                "demo_value": {},
                "events": [],
                "error": self.last_error,
            }

    async def set_demo_value(
        self,
        value: str,
        *,
        writer_pod: str,
        writer_version: str,
    ) -> dict[str, Any]:
        now_ms = int(time.time() * 1000)
        try:
            await self.client.hset(
                self.key("demo-value"),
                mapping={
                    "value": value,
                    "updated_at_unix_ms": now_ms,
                    "writer_pod": writer_pod,
                    "writer_version": writer_version,
                },
            )
            self.last_error = None
            return {
                "connected": True,
                "value": value,
                "updated_at_unix_ms": now_ms,
                "writer_pod": writer_pod,
                "writer_version": writer_version,
            }
        except RedisError as exc:
            self.last_error = str(exc)
            return {
                "connected": False,
                "value": value,
                "error": self.last_error,
            }

    async def close(self) -> None:
        await self.client.aclose()
