import logging
import time
from typing import Any, Generator, Optional

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from auth import TokenManager
from config import Config

logger = logging.getLogger(__name__)


class ProcareClient:
    def __init__(self, config: Config, token_manager: TokenManager):
        self.config = config
        self.token_manager = token_manager
        self._http = httpx.Client(timeout=30)

    def _auth_headers(self, token: str) -> dict:
        return {"Authorization": token}

    @retry(
        retry=retry_if_exception_type((httpx.NetworkError, httpx.TimeoutException)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2, max=8),
        reraise=True,
    )
    def get(self, path: str, params: Optional[dict] = None) -> Any:
        token = self.token_manager.get_token()
        base = self.token_manager.site_url.rstrip("/")
        url = f"{base}{path}"

        resp = self._http.get(url, headers=self._auth_headers(token), params=params)

        if resp.status_code == 401:
            logger.warning("Got 401, refreshing token and retrying...")
            token = self.token_manager.refresh_token()
            resp = self._http.get(url, headers=self._auth_headers(token), params=params)

        if resp.status_code == 429:
            retry_after = int(resp.headers.get("Retry-After", "5"))
            logger.warning("Rate limited, sleeping %ds", retry_after)
            time.sleep(retry_after)
            resp = self._http.get(url, headers=self._auth_headers(token), params=params)

        resp.raise_for_status()
        return resp.json()

    def paginate(self, path: str, extra_params: Optional[dict] = None) -> Generator[list, None, None]:
        page = 1
        while True:
            params = {"page": page, "per_page": self.config.page_size}
            if extra_params:
                params.update(extra_params)

            data = self.get(path, params=params)
            records = self._extract_records(data, path)

            if not records:
                break

            yield records

            if len(records) < self.config.page_size:
                break

            page += 1

    def _extract_records(self, data: Any, path: str) -> list:
        if isinstance(data, list):
            return data

        if isinstance(data, dict):
            segments = [s for s in path.strip("/").split("/") if s]
            if segments:
                last = segments[-1]
                if last in data:
                    val = data[last]
                    if isinstance(val, list):
                        return val

            if "data" in data and isinstance(data["data"], list):
                return data["data"]

            for v in data.values():
                if isinstance(v, list):
                    return v

        return []

    def close(self):
        self._http.close()
