"""SSRF guard of the media importer's URL fetch (#295): only public http(s)
hosts, every redirect target re-checked, body size capped."""

from __future__ import annotations

import socket

import httpx
import pytest

from dashboard_backend.tasks import media_extraction
from dashboard_backend.tasks.media_extraction import UnsafeUrlError, fetch_url_text

PUBLIC_IP = "93.184.216.34"

HOSTS = {
    "example.org": PUBLIC_IP,
    "redis": "172.18.0.5",
    "intranet.example": "10.1.2.3",
    "rebind.example": "127.0.0.1",
}


@pytest.fixture(autouse=True)
def fake_resolver(monkeypatch):
    def getaddrinfo(host, port, *args, **kwargs):
        try:
            address = HOSTS.get(host) or str(__import__("ipaddress").ip_address(host))
        except ValueError:
            raise socket.gaierror(f"unknown host {host}")
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (address, port))]

    monkeypatch.setattr(media_extraction.socket, "getaddrinfo", getaddrinfo)


def _transport(handler):
    calls = []

    def wrapped(request):
        calls.append(str(request.url))
        return handler(request)

    return httpx.MockTransport(wrapped), calls


def _ok(request):
    return httpx.Response(200, html="<html><body><p>Baubeginn 2027</p></body></html>")


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1:6379",
        "http://redis:6379",
        "http://169.254.169.254/latest/meta-data/",
        "http://10.0.0.8/",
        "http://intranet.example/",
        "http://[::1]/",
        "ftp://example.org/file",
        "file:///etc/passwd",
        "http://unknown.invalid/",
    ],
)
def test_blocked_urls_are_never_fetched(url):
    transport, calls = _transport(_ok)
    with pytest.raises(UnsafeUrlError):
        fetch_url_text(url, transport=transport)
    assert calls == []


def test_public_url_is_fetched():
    transport, calls = _transport(_ok)
    assert "Baubeginn 2027" in fetch_url_text("https://example.org/artikel", transport=transport)
    assert calls == ["https://example.org/artikel"]


def test_redirect_chain_to_private_address_is_blocked():
    def handler(request):
        if request.url.path == "/start":
            return httpx.Response(302, headers={"location": "/zwischen"})
        if request.url.path == "/zwischen":
            return httpx.Response(301, headers={"location": "http://rebind.example/"})
        return _ok(request)

    transport, calls = _transport(handler)
    with pytest.raises(UnsafeUrlError):
        fetch_url_text("https://example.org/start", transport=transport)
    assert calls == ["https://example.org/start", "https://example.org/zwischen"]


def test_public_redirect_is_followed():
    def handler(request):
        if request.url.path == "/alt":
            return httpx.Response(301, headers={"location": "https://example.org/neu"})
        return _ok(request)

    transport, calls = _transport(handler)
    assert "Baubeginn" in fetch_url_text("https://example.org/alt", transport=transport)
    assert calls == ["https://example.org/alt", "https://example.org/neu"]


def test_too_many_redirects_are_rejected():
    transport, _ = _transport(lambda request: httpx.Response(302, headers={"location": "/loop"}))
    with pytest.raises(UnsafeUrlError):
        fetch_url_text("https://example.org/loop", transport=transport)


def test_declared_oversize_body_is_rejected(monkeypatch):
    monkeypatch.setattr(media_extraction, "_MAX_RESPONSE_BYTES", 100)
    transport, _ = _transport(
        lambda request: httpx.Response(200, headers={"content-length": "1000"}, content=b"x" * 1000)
    )
    with pytest.raises(UnsafeUrlError):
        fetch_url_text("https://example.org/gross", transport=transport)


def test_streamed_oversize_body_is_rejected(monkeypatch):
    monkeypatch.setattr(media_extraction, "_MAX_RESPONSE_BYTES", 100)

    def chunks():
        for _ in range(10):
            yield b"x" * 50

    transport, _ = _transport(lambda request: httpx.Response(200, content=chunks()))
    with pytest.raises(UnsafeUrlError):
        fetch_url_text("https://example.org/gross", transport=transport)
