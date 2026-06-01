import json
import logging
import os
from typing import Optional

import httpx

from config import Config

logger = logging.getLogger(__name__)


class TokenManager:
    def __init__(self, config: Config):
        self.config = config
        self._token: Optional[str] = None
        self._site_url: Optional[str] = None
        self._site_id: Optional[str] = None

    @property
    def site_url(self) -> str:
        return self._site_url or self.config.procare_site_url

    @property
    def site_id(self) -> Optional[str]:
        return self._site_id or self.config.procare_site_id

    def get_token(self) -> str:
        if self.config.procare_auth_token:
            self._token = self.config.procare_auth_token
            return self._token

        cached = self._load_cache()
        if cached:
            self._token = cached["token"]
            self._site_url = cached.get("site_url")
            self._site_id = cached.get("site_id")
            logger.info("Loaded token from cache")
            return self._token

        return self._login()

    def refresh_token(self) -> str:
        logger.info("Refreshing token...")
        cache_path = self.config.token_cache_path
        if os.path.exists(cache_path):
            try:
                os.remove(cache_path)
            except OSError:
                pass
        self._token = None
        return self._login()

    def _login(self) -> str:
        if not self.config.procare_email or not self.config.procare_password:
            raise ValueError("Cannot login: PROCARE_EMAIL and PROCARE_PASSWORD are required")

        payload = {
            "email": self.config.procare_email,
            "password": self.config.procare_password,
            "role": "carer",
            "platform": "web",
            "preserve_sites": True,
        }
        logger.info("Authenticating with Procare as %s", self.config.procare_email)
        resp = httpx.post(self.config.procare_auth_url, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        token = data.get("auth_token")
        if not token:
            raise ValueError("No auth_token in login response")

        sites = data.get("sites", [])
        if sites:
            first = sites[0]
            self._site_url = first.get("base_url") or self.config.procare_site_url
            self._site_id = first.get("id") or self.config.procare_site_id
        else:
            self._site_url = self.config.procare_site_url
            self._site_id = self.config.procare_site_id

        self._token = token
        self._save_cache(token, self._site_url, self._site_id)
        logger.info("Authenticated successfully")
        return token

    def _save_cache(self, token: str, site_url: Optional[str], site_id: Optional[str]):
        cache_path = self.config.token_cache_path
        cache_dir = os.path.dirname(cache_path)
        if cache_dir:
            os.makedirs(cache_dir, exist_ok=True)
        try:
            with open(cache_path, "w") as f:
                json.dump({"token": token, "site_url": site_url, "site_id": site_id}, f)
            logger.debug("Token cached to %s", cache_path)
        except OSError as e:
            logger.warning("Could not write token cache: %s", e)

    def _load_cache(self) -> Optional[dict]:
        cache_path = self.config.token_cache_path
        if not os.path.exists(cache_path):
            return None
        try:
            with open(cache_path) as f:
                data = json.load(f)
            if data.get("token"):
                return data
        except (OSError, json.JSONDecodeError) as e:
            logger.warning("Could not read token cache: %s", e)
        return None
