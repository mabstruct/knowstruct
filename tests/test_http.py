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
