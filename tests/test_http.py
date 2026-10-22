import io
import json
import urllib.error

import pytest

from ks.config import Env
from ks.http import PlaneError, UrlHttp


def test_urlhttp_error_hides_key(monkeypatch):
    def boom(req, timeout=None):
        raise urllib.error.HTTPError(req.full_url, 401, "Unauthorized", {}, io.BytesIO(b'{"detail":"bad"}'))

    monkeypatch.setattr("ks.http.urllib.request.urlopen", boom)
    http = UrlHttp(Env("https://p.example", "SECRET-KEY"))
    with pytest.raises(PlaneError) as e:
        http.request("GET", "/users/me/")
    assert e.value.status == 401 and "/users/me/" in str(e.value) and "SECRET-KEY" not in str(e.value)


def test_urlhttp_sends_header_and_json(monkeypatch):
    seen = {}

    class Resp:
        status = 200

        def read(self):
            return json.dumps({"ok": True}).encode()

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def fake_open(req, timeout=None):
        seen["req"], seen["timeout"] = req, timeout
        return Resp()

    monkeypatch.setattr("ks.http.urllib.request.urlopen", fake_open)
    http = UrlHttp(Env("https://p.example", "k"))
    status, data = http.request("POST", "/workspaces/mabstruct/projects/", {"a": 1})
    req = seen["req"]
    assert (status, data) == (200, {"ok": True})
    assert req.get_header("X-api-key") == "k"
    assert req.get_header("Content-type") == "application/json"
    assert req.data == b'{"a": 1}'
    assert req.full_url == "https://p.example/api/v1/workspaces/mabstruct/projects/"
    assert req.get_method() == "POST" and seen["timeout"] == 30


def _seq_open(monkeypatch, outcomes):
    """outcomes: list of None (200) or (code, headers)."""
    calls = iter(outcomes)

    class Resp:
        status = 200

        def read(self):
            return b'{"ok": true}'

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def fake_open(req, timeout=None):
        o = next(calls)
        if o is None:
            return Resp()
        code, headers = o
        raise urllib.error.HTTPError(req.full_url, code, "x", headers, io.BytesIO(b"limited"))

    sleeps = []
    monkeypatch.setattr("ks.http.urllib.request.urlopen", fake_open)
    monkeypatch.setattr("ks.http._sleep", sleeps.append)
    return sleeps


def test_retry_429_backoff(monkeypatch):
    sleeps = _seq_open(monkeypatch, [(429, {}), (429, {}), None])
    http = UrlHttp(Env("https://p.example", "k"))
    assert http.request("GET", "/x/") == (200, {"ok": True})
    assert sleeps == [1, 2]


def test_retry_429_retry_after(monkeypatch):
    sleeps = _seq_open(monkeypatch, [(429, {"Retry-After": "3"}), None])
    http = UrlHttp(Env("https://p.example", "k"))
    assert http.request("GET", "/x/")[0] == 200
    assert sleeps == [3]


def test_retry_429_gives_up(monkeypatch):
    sleeps = _seq_open(monkeypatch, [(429, {})] * 5)
    http = UrlHttp(Env("https://p.example", "k"))
    with pytest.raises(PlaneError) as e:
        http.request("GET", "/x/")
    assert e.value.status == 429
    assert sleeps == [1, 2, 4, 8]


@pytest.mark.parametrize("header,expected", [("999", 60), ("-5", 0), ("2.5", 2.5)])
def test_retry_after_is_clamped(monkeypatch, header, expected):
    sleeps = _seq_open(monkeypatch, [(429, {"Retry-After": header}), None])
    http = UrlHttp(Env("https://p.example", "k"))
    assert http.request("GET", "/x/")[0] == 200
    assert sleeps == [expected]
