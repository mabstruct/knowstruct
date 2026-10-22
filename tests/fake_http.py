from typing import Any


class FakeHttp:
    """Test double for ks.http.Http. Routes keyed by (method, path)."""

    def __init__(self, routes: dict[tuple[str, str], Any]):
        self.routes = routes
        self._served: dict[tuple[str, str], int] = {}
        self.calls: list[tuple[str, str, dict | None]] = []

    def request(self, method: str, path: str, body: dict | None = None) -> tuple[int, Any]:
        self.calls.append((method, path, body))
        key = (method, path)
        if key not in self.routes:
            return 404, {"error": "Page not found."}
        value = self.routes[key]
        if isinstance(value, list):
            i = self._served.get(key, 0)
            self._served[key] = i + 1
            value = value[min(i, len(value) - 1)]
        if isinstance(value, tuple) and len(value) == 2 and isinstance(value[0], int):
            return value
        return 200, value
