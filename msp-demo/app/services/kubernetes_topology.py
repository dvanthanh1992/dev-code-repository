from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from typing import Any

from app.config import Settings


class KubernetesTopology:
    """Read-only Kubernetes view of rollout pods in the current namespace."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._core_api: Any | None = None
        self._custom_api: Any | None = None
        self._api_exception_type: type[Exception] = Exception
        self._started = False
        self._start_error: str | None = None
        self._cache: dict[str, Any] | None = None
        self._cache_at = 0.0
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        if not self.settings.kubernetes_discovery_enabled:
            self._start_error = "Kubernetes discovery is disabled"
            return
        try:
            await asyncio.to_thread(self._configure_sync)
            self._started = True
            self._start_error = None
        except Exception as exc:  # Kubernetes client exposes several config errors.
            self._started = False
            self._start_error = str(exc)

    def _configure_sync(self) -> None:
        from kubernetes import client, config
        from kubernetes.client.exceptions import ApiException
        from kubernetes.config.config_exception import ConfigException

        try:
            config.load_incluster_config()
        except ConfigException:
            if not self.settings.kubeconfig_fallback:
                raise
            config.load_kube_config()

        self._core_api = client.CoreV1Api()
        self._custom_api = client.CustomObjectsApi()
        self._api_exception_type = ApiException

    async def snapshot(self, force: bool = False) -> dict[str, Any]:
        now = time.monotonic()
        if (
            not force
            and self._cache is not None
            and now - self._cache_at < self.settings.topology_cache_seconds
        ):
            return self._cache

        async with self._lock:
            now = time.monotonic()
            if (
                not force
                and self._cache is not None
                and now - self._cache_at < self.settings.topology_cache_seconds
            ):
                return self._cache

            if not self._started:
                result = self._fallback_snapshot(self._start_error)
            else:
                try:
                    result = await asyncio.to_thread(self._fetch_sync)
                except Exception as exc:
                    result = self._fallback_snapshot(str(exc))

            self._cache = result
            self._cache_at = time.monotonic()
            return result

    def _fetch_sync(self) -> dict[str, Any]:
        assert self._core_api is not None
        pods_response = self._core_api.list_namespaced_pod(
            namespace=self.settings.pod_namespace,
            label_selector=self.settings.pod_label_selector,
            timeout_seconds=3,
        )
        pods = [self._pod_to_dict(item) for item in pods_response.items]
        pods.sort(
            key=lambda item: (
                item["terminating"],
                item["role"],
                item["version"],
                item["name"],
            )
        )

        rollout: dict[str, Any] | None = None
        if self.settings.rollout_name and self._custom_api is not None:
            try:
                raw_rollout = self._custom_api.get_namespaced_custom_object(
                    group="argoproj.io",
                    version="v1alpha1",
                    namespace=self.settings.pod_namespace,
                    plural="rollouts",
                    name=self.settings.rollout_name,
                )
                rollout = self._rollout_to_dict(raw_rollout)
            except self._api_exception_type as exc:
                status = getattr(exc, "status", None)
                if status != 404:
                    raise

        ready = sum(1 for pod in pods if pod["ready"] and not pod["terminating"])
        terminating = sum(1 for pod in pods if pod["terminating"])
        revisions = len({pod["revision"] for pod in pods if pod["revision"]})

        return {
            "available": True,
            "source": "kubernetes-api",
            "namespace": self.settings.pod_namespace,
            "selector": self.settings.pod_label_selector,
            "observed_at_unix_ms": int(time.time() * 1000),
            "summary": {
                "pods": len(pods),
                "ready": ready,
                "terminating": terminating,
                "revisions": revisions,
            },
            "rollout": rollout,
            "pods": pods,
            "error": None,
        }

    def _pod_to_dict(self, pod: Any) -> dict[str, Any]:
        labels = pod.metadata.labels or {}
        conditions = {
            condition.type: condition.status
            for condition in (pod.status.conditions or [])
        }
        ready = conditions.get("Ready") == "True"
        terminating = pod.metadata.deletion_timestamp is not None
        phase = pod.status.phase or "Unknown"

        if terminating:
            display_status = "Terminating"
        elif ready:
            display_status = "Ready"
        elif phase == "Running":
            display_status = "Starting"
        else:
            display_status = phase

        revision = (
            labels.get("rollouts-pod-template-hash")
            or labels.get("pod-template-hash")
            or "unknown"
        )
        version = labels.get(self.settings.pod_version_label) or revision[:10]
        color = labels.get(self.settings.pod_color_label) or version
        role = (
            labels.get(self.settings.pod_role_label)
            or labels.get("role")
            or labels.get("app.kubernetes.io/component")
            or "unclassified"
        )
        restarts = sum(
            int(status.restart_count or 0)
            for status in (pod.status.container_statuses or [])
        )
        owner = ""
        for reference in pod.metadata.owner_references or []:
            if reference.controller:
                owner = reference.name
                break

        return {
            "name": pod.metadata.name,
            "namespace": pod.metadata.namespace,
            "uid": pod.metadata.uid,
            "version": version,
            "color": color,
            "role": role,
            "revision": revision,
            "owner": owner,
            "phase": phase,
            "status": display_status,
            "ready": ready,
            "serving": ready and not terminating,
            "terminating": terminating,
            "pod_ip": pod.status.pod_ip or "",
            "node": pod.spec.node_name or "",
            "restarts": restarts,
            "created_at": self._iso(pod.metadata.creation_timestamp),
            "deletion_at": self._iso(pod.metadata.deletion_timestamp),
        }

    @staticmethod
    def _rollout_to_dict(raw: dict[str, Any]) -> dict[str, Any]:
        spec = raw.get("spec", {})
        status = raw.get("status", {})
        return {
            "name": raw.get("metadata", {}).get("name", ""),
            "desired_replicas": int(spec.get("replicas", 1) or 1),
            "replicas": int(status.get("replicas", 0) or 0),
            "ready_replicas": int(status.get("readyReplicas", 0) or 0),
            "available_replicas": int(
                status.get("availableReplicas", 0) or 0
            ),
            "updated_replicas": int(status.get("updatedReplicas", 0) or 0),
            "stable_revision": status.get("stableRS", ""),
            "current_revision": status.get("currentPodHash", ""),
            "phase": status.get("phase", "Unknown"),
            "message": status.get("message", ""),
            "current_step_index": int(status.get("currentStepIndex", 0) or 0),
        }

    def _fallback_snapshot(self, error: str | None) -> dict[str, Any]:
        pod = {
            "name": self.settings.hostname,
            "namespace": self.settings.pod_namespace,
            "uid": "local-fallback",
            "version": self.settings.app_version,
            "color": self.settings.app_color,
            "role": self.settings.app_track or "active",
            "revision": "local",
            "owner": "",
            "phase": "Running",
            "status": "Ready",
            "ready": True,
            "serving": True,
            "terminating": False,
            "pod_ip": "",
            "node": "",
            "restarts": 0,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "deletion_at": "",
        }
        return {
            "available": False,
            "source": "local-fallback",
            "namespace": self.settings.pod_namespace,
            "selector": self.settings.pod_label_selector,
            "observed_at_unix_ms": int(time.time() * 1000),
            "summary": {
                "pods": 1,
                "ready": 1,
                "terminating": 0,
                "revisions": 1,
            },
            "rollout": None,
            "pods": [pod],
            "error": error or "Kubernetes API unavailable",
        }

    @staticmethod
    def _iso(value: Any | None) -> str:
        if value is None:
            return ""
        if hasattr(value, "isoformat"):
            return value.isoformat()
        return str(value)
