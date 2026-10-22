import json
import urllib.error
import urllib.request
from typing import Any, Protocol

from ks.config import Env


class PlaneError(Exception):
    def __init__(self, status: int, path: str, body: str = ""):
        super().__init__(status, path, body)
        self.status = status
        self.path = path
        self.body = body

    def __str__(self) -> str:
        return f"{self.status} on {self.path}: {self.body[:200]}"


class Http(Protocol):
    def request(self, method: str, path: str, body: dict | None = None) -> tuple[int, Any]: ...


class UrlHttp:
    def __init__(self, env: Env):
        self._base = env.base_url + "/api/v1"
        self._key = env.api_key

    def request(self, method: str, path: str, body: dict | None = None) -> tuple[int, Any]:
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(
            self._base + path,
            data=data,
            method=method,
            headers={"x-api-key": self._key, "Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                status, raw = resp.status, resp.read()
        except urllib.error.HTTPError as e:
            raise PlaneError(e.code, path, e.read().decode("utf-8", "replace")) from None
        if status >= 400:
            raise PlaneError(status, path, raw.decode("utf-8", "replace"))
        return status, (json.loads(raw) if raw else None)
