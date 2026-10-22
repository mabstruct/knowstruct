import json
import time
import urllib.error
import urllib.request
from typing import Any, Protocol

from devsys.config import Env


_sleep = time.sleep
MAX_ATTEMPTS = 5
MAX_RETRY_AFTER = 60


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
        for attempt in range(MAX_ATTEMPTS):
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    status, raw = resp.status, resp.read()
                break
            except urllib.error.HTTPError as e:
                try:
                    if e.code == 429 and attempt < MAX_ATTEMPTS - 1:
                        delay = _retry_delay(e, attempt)
                        retry = True
                    else:
                        err_body = e.read().decode("utf-8", "replace")
                        retry = False
                finally:
                    e.close()
                if retry:
                    _sleep(delay)
                    continue
                raise PlaneError(e.code, path, err_body) from None
        if status >= 400:
            raise PlaneError(status, path, raw.decode("utf-8", "replace"))
        return status, (json.loads(raw) if raw else None)


def _retry_delay(err: urllib.error.HTTPError, attempt: int) -> float:
    """Seconds to wait: Retry-After clamped to 0..MAX_RETRY_AFTER, else exponential backoff."""
    ra = err.headers.get("Retry-After") if err.headers else None
    try:
        if ra is not None:
            s = float(ra) if "." in ra else int(ra)
            return min(max(s, 0), MAX_RETRY_AFTER)
    except ValueError:
        pass
    return 2**attempt
