from __future__ import annotations

import json
from typing import Iterable, Mapping, Sequence

import httpx
import structlog

from app.settings import settings


logger = structlog.get_logger(__name__)

HTTP_TIMEOUT = httpx.Timeout(connect=3.0, read=25.0, write=10.0, pool=3.0)
HTTP_LIMITS = httpx.Limits(max_connections=100, max_keepalive_connections=20)


def get_supabase_client() -> "SupabaseClient | None":
    if not settings.supabase_url or not settings.supabase_service_role_key:
        return None
    return SupabaseClient(
        base_url=settings.supabase_url,
        service_role_key=settings.supabase_service_role_key,
    )


class SupabaseClient:
    def __init__(self, base_url: str, service_role_key: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = service_role_key
        self._headers = {
            "apikey": self.api_key,
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def bulk_upsert(
        self,
        table: str,
        rows: Sequence[Mapping[str, object]],
        *,
        on_conflict: str = "id",
        chunk_size: int = 100,
    ) -> None:
        if not rows:
            return

        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, limits=HTTP_LIMITS) as client:
            for start in range(0, len(rows), chunk_size):
                batch = rows[start : start + chunk_size]
                resp = await client.post(
                    f"{self.base_url}/rest/v1/{table}",
                    params={"on_conflict": on_conflict},
                    headers={
                        **self._headers,
                        "Prefer": "resolution=merge-duplicates,return=representation",
                    },
                    content=json.dumps(batch),
                )
                try:
                    resp.raise_for_status()
                except httpx.HTTPStatusError as exc:
                    logger.error(
                        "supabase_upsert_failed",
                        table=table,
                        status=exc.response.status_code,
                        body=exc.response.text,
                    )
                    raise

    async def call_function(
        self,
        name: str,
        *,
        payload: Mapping[str, object],
    ) -> list[dict[str, object]]:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, limits=HTTP_LIMITS) as client:
            resp = await client.post(
                f"{self.base_url}/rest/v1/rpc/{name}",
                headers=self._headers,
                content=json.dumps(payload),
            )
            resp.raise_for_status()

        data = resp.json()
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return data.get("results", [])
        return []


def vector_to_pg(values: Iterable[float]) -> str:
    # pgvector expects a string literal like "[0.1,0.2]"
    return "[" + ",".join(_format_float(v) for v in values) + "]"


def _format_float(value: float) -> str:
    return f"{value:.12g}"
