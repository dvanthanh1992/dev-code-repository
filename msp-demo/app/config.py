from __future__ import annotations

import os
import socket
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


_SERVICE_ACCOUNT_NAMESPACE = Path(
    "/var/run/secrets/kubernetes.io/serviceaccount/namespace"
)


def env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def env_int(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError:
        value = default
    return max(minimum, min(maximum, value))


def env_float(name: str, default: float, minimum: float, maximum: float) -> float:
    try:
        value = float(os.getenv(name, str(default)))
    except ValueError:
        value = default
    return max(minimum, min(maximum, value))


def normalize_mode(value: str) -> str:
    normalized = value.strip().lower().replace("_", "-")
    if normalized in {"bluegreen", "blue-green"}:
        return "bluegreen"
    return "canary"


def discover_namespace() -> str:
    explicit = os.getenv("POD_NAMESPACE", "").strip()
    if explicit:
        return explicit
    try:
        return _SERVICE_ACCOUNT_NAMESPACE.read_text(encoding="utf-8").strip()
    except OSError:
        return "default"


@dataclass(frozen=True, slots=True)
class Settings:
    app_version: str
    app_color: str
    app_commit: str
    app_message: str
    app_environment: str
    app_track: str
    rollout_mode: str
    preview_url: str
    traffic_rps: int
    preview_rps: int
    failure_rate: float
    min_latency_ms: int
    max_latency_ms: int
    hostname: str

    redis_host: str
    redis_port: int
    redis_db: int
    redis_password: str | None
    redis_ssl: bool
    redis_key_prefix: str
    redis_max_events: int
    require_redis: bool

    kubernetes_discovery_enabled: bool
    kubeconfig_fallback: bool
    pod_namespace: str
    pod_label_selector: str
    pod_version_label: str
    pod_color_label: str
    pod_role_label: str
    rollout_name: str
    topology_cache_seconds: float

    @classmethod
    def from_env(cls) -> "Settings":
        min_latency = env_int("MIN_LATENCY_MS", 15, 0, 30_000)
        max_latency = env_int(
            "MAX_LATENCY_MS",
            max(min_latency, 80),
            min_latency,
            30_000,
        )
        password = os.getenv("REDIS_PASSWORD")
        if password == "":
            password = None

        return cls(
            app_version=os.getenv("APP_VERSION", "v1"),
            app_color=os.getenv("APP_COLOR", "blue"),
            app_commit=os.getenv("APP_COMMIT", "local"),
            app_message=os.getenv("APP_MESSAGE", "Tony - ArgoCD Demo"),
            app_environment=os.getenv("APP_ENVIRONMENT", "demo"),
            app_track=os.getenv("APP_TRACK", ""),
            rollout_mode=normalize_mode(os.getenv("ROLLOUT_MODE", "canary")),
            preview_url=os.getenv("PREVIEW_URL", "").strip(),
            traffic_rps=env_int("TRAFFIC_RPS", 3, 1, 50),
            preview_rps=env_int("PREVIEW_RPS", 1, 1, 20),
            failure_rate=env_float("FAILURE_RATE", 0.0, 0.0, 1.0),
            min_latency_ms=min_latency,
            max_latency_ms=max_latency,
            hostname=socket.gethostname(),
            redis_host=os.getenv("REDIS_HOST", "redis"),
            redis_port=env_int("REDIS_PORT", 6379, 1, 65_535),
            redis_db=env_int("REDIS_DB", 0, 0, 15),
            redis_password=password,
            redis_ssl=env_bool("REDIS_SSL", False),
            redis_key_prefix=os.getenv("REDIS_KEY_PREFIX", "msp-demo").strip()
            or "msp-demo",
            redis_max_events=env_int("REDIS_MAX_EVENTS", 500, 10, 10_000),
            require_redis=env_bool("REQUIRE_REDIS", True),
            kubernetes_discovery_enabled=env_bool(
                "KUBERNETES_DISCOVERY_ENABLED", True
            ),
            kubeconfig_fallback=env_bool("KUBECONFIG_FALLBACK", True),
            pod_namespace=discover_namespace(),
            pod_label_selector=os.getenv(
                "POD_LABEL_SELECTOR",
                "app.kubernetes.io/name=msp-demo,app.kubernetes.io/component=app"
            ),
            pod_version_label=os.getenv(
                "POD_VERSION_LABEL", "app.kubernetes.io/version"
            ),
            pod_color_label=os.getenv(
                "POD_COLOR_LABEL", "demo.argoproj.io/color"
            ),
            pod_role_label=os.getenv(
                "POD_ROLE_LABEL", "demo.argoproj.io/role"
            ),
            rollout_name=os.getenv("ROLLOUT_NAME", "msp-demo").strip(),
            topology_cache_seconds=env_float(
                "TOPOLOGY_CACHE_SECONDS", 0.75, 0.1, 10.0
            ),
        )

    def public_config(self) -> dict[str, object]:
        return {
            "mode": self.rollout_mode,
            "previewUrl": self.preview_url,
            "trafficRps": self.traffic_rps,
            "previewRps": self.preview_rps,
            "environment": self.app_environment,
            "podNamespace": self.pod_namespace,
            "podLabelSelector": self.pod_label_selector,
            "rolloutName": self.rollout_name,
        }


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings.from_env()
