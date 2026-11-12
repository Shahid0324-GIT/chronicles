"""Approved public-source retrieval with DNS pinning and per-redirect policy checks."""

import asyncio
import http.client
import ipaddress
import socket
import ssl
import time
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser

import httpx
from bs4 import BeautifulSoup

from src.application.research import FetchedDocument
from src.domain.research import normalize

USER_AGENT = "ChroniclesResearch/0.1"


class SourceRejected(Exception):
    pass


class PublicSourcePolicy:
    def __init__(self, allowed_hosts: list[str]) -> None:
        self.hosts = {host.lower() for host in allowed_hosts}

    def is_approved(self, url: str) -> bool:
        try:
            self.validate(url)
            return True
        except (SourceRejected, ValueError):
            return False

    def validate(self, url: str) -> tuple[str, str, int, str]:
        parsed = urlsplit(url)
        host = (parsed.hostname or "").lower()
        if (
            parsed.scheme not in {"http", "https"}
            or host not in self.hosts
            or parsed.username
            or parsed.password
            or parsed.port not in {None, 80, 443}
        ):
            raise SourceRejected("source_url_not_approved")
        return (
            parsed.scheme,
            host,
            parsed.port or (443 if parsed.scheme == "https" else 80),
            urlunsplit(("", "", parsed.path or "/", parsed.query, "")),
        )

    @staticmethod
    def public_ip(address: str) -> bool:
        ip = ipaddress.ip_address(address)
        return ip.is_global and not ip.is_multicast


def pinned_request(
    url: str, policy: PublicSourcePolicy, maximum: int
) -> tuple[int, dict[str, str], bytes]:
    scheme, host, port, path = policy.validate(url)
    addresses = [
        str(item[4][0]) for item in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    ]
    if not addresses or not all(policy.public_ip(address) for address in addresses):
        raise SourceRejected("non_public_source_address")
    # Connect to the exact validated IP. TLS still verifies the original hostname.
    raw = socket.create_connection((addresses[0], port), timeout=20)
    connection = http.client.HTTPConnection(host, port, timeout=20)
    try:
        connection.sock = (
            ssl.create_default_context().wrap_socket(raw, server_hostname=host)
            if scheme == "https"
            else raw
        )
        connection.request(
            "GET",
            path,
            headers={
                "Host": host,
                "User-Agent": USER_AGENT,
                "Accept-Encoding": "identity",
                "Accept": "text/html,text/plain",
            },
        )
        response = connection.getresponse()
        headers = {key.lower(): value for key, value in response.getheaders()}
        body = response.read(maximum + 1)
        if len(body) > maximum:
            raise SourceRejected("source_too_large")
        if headers.get("content-encoding", "identity").lower() not in {"identity", ""}:
            raise SourceRejected("compressed_source_not_supported")
        return response.status, headers, body
    finally:
        connection.close()
        raw.close()


class PublicDocumentFetcher:
    def __init__(self, policy: PublicSourcePolicy, max_bytes: int, max_chars: int) -> None:
        self.policy, self.max_bytes, self.max_chars = policy, max_bytes, max_chars
        self.lock = asyncio.Lock()
        self.last: dict[str, float] = {}

    async def _request(self, url: str) -> tuple[int, dict[str, str], bytes]:
        _, host, _, _ = self.policy.validate(url)
        async with self.lock:
            delay = 1.0 - (time.monotonic() - self.last.get(host, 0))
            if delay > 0:
                await asyncio.sleep(delay)
            try:
                return await asyncio.to_thread(pinned_request, url, self.policy, self.max_bytes)
            finally:
                self.last[host] = time.monotonic()

    async def _robots(self, url: str) -> None:
        parsed = urlsplit(url)
        robots_url = urlunsplit((parsed.scheme, parsed.netloc, "/robots.txt", "", ""))
        code, headers, body = await self._request(robots_url)
        for _ in range(3):
            if code not in {301, 302, 303, 307, 308}:
                break
            target = urljoin(robots_url, headers.get("location", ""))
            if urlsplit(target).netloc != parsed.netloc:
                raise SourceRejected("robots_redirect_not_same_origin")
            robots_url = target
            code, headers, body = await self._request(target)
        if code in {404, 410}:
            return
        if code != 200:
            raise SourceRejected("robots_unavailable")
        robots = RobotFileParser()
        robots.parse(body.decode("utf-8", errors="replace").splitlines())
        if not robots.can_fetch(USER_AGENT, url):
            raise SourceRejected("robots_disallowed")

    async def fetch(self, url: str) -> FetchedDocument:
        try:
            for _ in range(4):
                self.policy.validate(url)
                await self._robots(url)
                code, headers, body = await self._request(url)
                if code in {301, 302, 303, 307, 308}:
                    url = urljoin(url, headers.get("location", ""))
                    continue
                if code != 200:
                    raise SourceRejected("source_http_error")
                kind = headers.get("content-type", "").split(";")[0].lower()
                if kind not in {"text/html", "application/xhtml+xml", "text/plain"}:
                    raise SourceRejected("source_content_type_not_allowed")
                soup = BeautifulSoup(body, "html.parser")
                title = (
                    normalize(soup.title.get_text())
                    if soup.title
                    else urlsplit(url).hostname or "Source"
                )
                if kind == "text/plain":
                    text = body.decode("utf-8", errors="replace")
                else:
                    for item in soup.select(
                        "script,style,nav,header,footer,aside,form,svg,noscript"
                    ):
                        item.decompose()
                    main = soup.select_one("main,article,#story,.story") or soup.body or soup
                    text = main.get_text(" ", strip=True)
                text = normalize(text)
                if len(text) < 30:
                    raise SourceRejected("source_has_no_usable_text")
                return FetchedDocument(
                    url=url,
                    title=title[:300],
                    publisher=urlsplit(url).hostname or "",
                    text=text[: self.max_chars],
                    truncated=len(text) > self.max_chars,
                )
            raise SourceRejected("too_many_source_redirects")
        except SourceRejected:
            raise
        except Exception:
            raise SourceRejected("source_fetch_failed") from None


class SearxngSearch:
    def __init__(self, base_url: str, policy: PublicSourcePolicy) -> None:
        parsed = urlsplit(base_url)
        if parsed.scheme != "http" or parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
            raise ValueError("SearXNG must be a trusted loopback endpoint")
        self.base_url, self.policy = base_url, policy

    async def search(self, query: str, limit: int) -> list[str]:
        async with httpx.AsyncClient(timeout=15, trust_env=False) as client:
            response = await client.get(
                self.base_url.rstrip("/") + "/search", params={"q": query, "format": "json"}
            )
            response.raise_for_status()
            results = response.json().get("results", [])
        accepted = []
        for item in results:
            try:
                self.policy.validate(item["url"])
                accepted.append(str(item["url"]))
            except (SourceRejected, KeyError):
                continue
        return list(dict.fromkeys(accepted))[:limit]
