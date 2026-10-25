from __future__ import annotations

import http.client
import json
import threading
from contextlib import contextmanager
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

from intake_watcher.config import IntakeConfig
from intake_watcher.origin_guard import origin_allowed, parse_origin_list, request_allowed
from intake_watcher.server import IntakeWatcherRequestHandler, RunCoordinator


@pytest.mark.parametrize(
    "origin",
    [
        "http://127.0.0.1:8091",
        "http://localhost:5173",
        "https://localhost",
        "http://[::1]:8091",
        "HTTP://LOCALHOST:8091/",
    ],
)
def test_loopback_origins_are_allowed(origin: str) -> None:
    assert origin_allowed(origin)


@pytest.mark.parametrize(
    "origin",
    [
        "https://evil.example",
        "http://127.0.0.1.evil.example",
        "http://localhost.evil.example:8091",
        "http://127.0.0.1@evil.example",
        "http://evil.example#@127.0.0.1",
        "http://192.168.1.50:8091",
        "null",
        "file://",
        "ftp://127.0.0.1",
        "http://127.0.0.1:8091/path",
        "",
    ],
)
def test_other_origins_are_rejected(origin: str) -> None:
    assert not origin_allowed(origin)


def test_listed_origins_are_allowed_exactly() -> None:
    extra = parse_origin_list("http://192.168.1.50:8091/, https://nas.example.ts.net")
    assert origin_allowed("http://192.168.1.50:8091", extra)
    assert origin_allowed("https://NAS.example.ts.net", extra)
    assert not origin_allowed("http://192.168.1.50:9999", extra)
    assert not origin_allowed("http://192.168.1.51:8091", extra)


def test_only_changing_methods_are_checked() -> None:
    assert request_allowed("GET", "https://evil.example", None) == (True, "")
    assert request_allowed("OPTIONS", "https://evil.example", None) == (True, "")
    for method in ("POST", "PUT", "PATCH", "DELETE"):
        allowed, reason = request_allowed(method, "https://evil.example", None)
        assert not allowed and "Origin not allowed" in reason


def test_requests_without_origin_pass_unless_the_browser_says_cross_site() -> None:
    assert request_allowed("POST", None, None) == (True, "")
    assert request_allowed("POST", None, "same-origin") == (True, "")
    assert request_allowed("POST", None, "none") == (True, "")
    allowed, _ = request_allowed("POST", None, "cross-site")
    assert not allowed


@contextmanager
def running_server(config: IntakeConfig):
    server = ThreadingHTTPServer(("127.0.0.1", 0), IntakeWatcherRequestHandler)
    server.config = config  # type: ignore[attr-defined]
    server.coordinator = RunCoordinator(config)  # type: ignore[attr-defined]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_address[1]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def post(port: int, path: str, headers: dict[str, str] | None = None) -> tuple[int, dict]:
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    try:
        connection.request("POST", path, body=b"", headers=headers or {})
        response = connection.getresponse()
        return response.status, json.loads(response.read() or b"{}")
    finally:
        connection.close()


def make_config(tmp_path: Path, **overrides) -> IntakeConfig:
    return IntakeConfig(data_root=tmp_path / "nas-data", stability_seconds=0, **overrides)


def test_server_rejects_a_post_from_another_site_and_does_nothing(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    with running_server(config) as port:
        status, payload = post(port, "/api/run-once", {"Origin": "https://evil.example"})
        assert status == 403
        assert payload["status"] == "error"
        status, _ = post(port, "/api/events/clear", {"Origin": "null"})
        assert status == 403
    assert not config.state_path.exists()
    assert not config.log_path.exists()


def test_server_accepts_its_own_dashboard_and_plain_clients(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    with running_server(config) as port:
        status, payload = post(port, "/api/run-once", {"Origin": f"http://127.0.0.1:{port}"})
        assert status == 200 and payload["status"] == "ok"
        status, _ = post(port, "/api/run-once")
        assert status == 200
        status, _ = post(port, "/api/run-once", {"Origin": "http://localhost:5173"})
        assert status == 200


def test_server_accepts_a_listed_lan_origin(tmp_path: Path) -> None:
    config = make_config(tmp_path, allowed_origins=parse_origin_list("http://192.168.1.50:8091"))
    with running_server(config) as port:
        status, _ = post(port, "/api/run-once", {"Origin": "http://192.168.1.50:8091"})
        assert status == 200
        status, _ = post(port, "/api/run-once", {"Origin": "http://192.168.1.51:8091"})
        assert status == 403


def test_allowed_origins_setting_is_read_from_the_environment(monkeypatch) -> None:
    monkeypatch.setenv("ALLOWED_ORIGINS", "http://192.168.1.50:8091, https://nas.example.ts.net/")
    monkeypatch.chdir(Path(__file__).parent)
    config = IntakeConfig.from_env()
    assert config.allowed_origins == ("http://192.168.1.50:8091", "https://nas.example.ts.net")
