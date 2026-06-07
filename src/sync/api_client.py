import logging
from typing import Any, Iterable

import httpx

logger = logging.getLogger(__name__)


class ApiClient:
    def __init__(self, base_url: str, ingest_token: str, timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self._client = httpx.Client(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {ingest_token}"},
            timeout=timeout,
        )

    def close(self) -> None:
        self._client.close()

    def post_ingest(self, entity: str, rows: list[dict[str, Any]], batch_size: int = 200) -> int:
        total = 0
        for i in range(0, len(rows), batch_size):
            chunk = rows[i:i + batch_size]
            r = self._client.post(f"/ingest/{entity}", json=chunk)
            r.raise_for_status()
            data = r.json()
            total += int(data.get("upserted", 0))
        return total

    def post_alert(self, *, severity: str, code: str, entity: str | None, message: str, details: dict | None = None) -> None:
        payload = {"severity": severity, "code": code, "entity": entity, "message": message, "details": details}
        try:
            r = self._client.post("/ingest/alerts", json=payload)
            r.raise_for_status()
        except Exception as e:
            logger.error("failed to post alert (%s): %s", code, e)

    def list_active_kid_ids(self) -> list[str]:
        out: list[str] = []
        offset = 0
        limit = 500
        while True:
            r = self._client.get("/kids", params={"limit": limit, "offset": offset, "status": "active"})
            if r.status_code == 404:
                return out
            r.raise_for_status()
            data = r.json()
            items = data.get("items", [])
            out.extend([item["id"] for item in items if item.get("id")])
            if len(items) < limit:
                break
            offset += limit
        return out