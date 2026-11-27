"""Approved public-source retrieval with DNS pinning and per-redirect policy checks."""

import asyncio
import http.client
import ipaddress
import json
import math
import socket
import ssl
import time
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import urlencode, urljoin, urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser

import certifi
import httpx
from bs4 import BeautifulSoup

from src.application.ports.research import SearchResult
from src.application.research import FetchedDocument, SourceRejected
from src.application.research_contracts import InferenceFailure
from src.domain.research import normalize
from src.infrastructure.document_structure import html_document

USER_AGENT = "ChroniclesResearch/0.1"


class PublicSourcePolicy:
    def __init__(self, allowed_hosts: list[str], allowed_urls: list[str] | None = None) -> None:
        self.hosts = {host.lower() for host in allowed_hosts}
        self.urls = {self.locator(url) for url in (allowed_urls or [])}

    @staticmethod
    def locator(url: str) -> str:
        p = urlsplit(url)
        return urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path or "/", p.query, ""))

    @staticmethod
    def public_url(url: str) -> bool:
        try:
            p = urlsplit(url)
            host = (p.hostname or "").lower()
            if (
                p.scheme not in {"http", "https"}
                or not host
                or p.username
                or p.password
                or p.port not in {None, 80, 443}
                or host in {"localhost", "localhost.localdomain"}
                or host.endswith((".localhost", ".local", ".internal"))
            ):
                return False
            try:
                return PublicSourcePolicy.public_ip(host)
            except ValueError:
                return True  # DNS is resolved and pinned at request time, never here.
        except ValueError:
            return False

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
            not self.public_url(url)
            or (host not in self.hosts and self.locator(url) not in self.urls)
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
            # The Mozilla bundle: some systems hold an expired chain for valid sites.
            ssl.create_default_context(cafile=certifi.where()).wrap_socket(
                raw, server_hostname=host
            )
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
                "Accept": "text/html,text/plain,application/json",
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
        self.cooldowns: dict[str, float] = {}
        self.delays: dict[str, float] = {}
        self.rules: dict[str, RobotFileParser] = {}
        self.reserve_bytes: Callable[[int], Awaitable[None]] | None = None
        self.complete_bytes: Callable[[int, int], Awaitable[None]] | None = None

    def authorize_registered(self, urls: list[str]) -> None:
        """Exact current registry grants; no domain-wide permission inheritance."""
        approved = [url for url in urls if PublicSourcePolicy.public_url(url)]
        robots = [urlunsplit((*urlsplit(url)[:2], "/robots.txt", "", "")) for url in approved]
        self.policy = PublicSourcePolicy(list(self.policy.hosts), [*approved, *robots])

    async def fetch_rendered(self, url: str) -> FetchedDocument:
        from src.infrastructure.browser_extraction import ControlledBrowserExtractor

        self.policy.validate(url)
        origin = urlsplit(url)[:2]

        async def read(target: str) -> tuple[int, dict[str, str], bytes]:
            if urlsplit(target)[:2] != origin:
                raise SourceRejected("source_browser_origin_rejected")
            # Explicit rendered-document permission covers its same-origin GET resources.
            self.authorize_registered([url, target])
            await self._robots(target)
            return await self._request(target)

        return await ControlledBrowserExtractor(self.max_bytes).extract(url, read)

    async def discover_mediawiki(self, endpoint: str, query: str, limit: int) -> list[SearchResult]:
        self.policy.validate(endpoint)
        target = (
            endpoint
            + "?"
            + urlencode(
                {
                    "action": "query",
                    "generator": "search",
                    "gsrsearch": query,
                    "gsrlimit": min(max(limit, 1), 20),
                    "prop": "info",
                    "inprop": "url",
                    "format": "json",
                    "formatversion": 2,
                }
            )
        )
        self.authorize_registered([endpoint, target])
        await self._robots(target)
        code, headers, body = await self._request(target)
        if code != 200 or "json" not in headers.get("content-type", ""):
            raise SourceRejected("source_search_api_unavailable")
        data = json.loads(body)
        if "error" in data:
            raise SourceRejected("source_search_api_rejected")
        return [
            SearchResult(p["fullurl"], p.get("title", ""), "MediaWiki search result")
            for p in data.get("query", {}).get("pages", [])
            if p.get("fullurl") and PublicSourcePolicy.public_url(p["fullurl"])
        ]

    def budget_requests(
        self,
        reserve: Callable[[int], Awaitable[None]] | None,
        complete: Callable[[int, int], Awaitable[None]] | None,
    ) -> None:
        self.reserve_bytes, self.complete_bytes = reserve, complete

    async def _request(self, url: str) -> tuple[int, dict[str, str], bytes]:
        _, host, _, _ = self.policy.validate(url)
        async with self.lock:
            remaining = self.cooldowns.get(host, 0) - time.monotonic()
            if remaining > 0:
                raise SourceRejected("source_rate_limited", remaining)
            interval = self.delays.get(host, 1.0)
            delay = interval - (time.monotonic() - self.last.get(host, 0))
            if delay > 0:
                await asyncio.sleep(delay)
            try:
                # Reserve the bounded response read, including its oversize detection byte.
                # A crash or unknown partial response retains its reservation.
                if self.reserve_bytes:
                    await self.reserve_bytes(self.max_bytes + 1)
                try:
                    result = await asyncio.to_thread(
                        pinned_request, url, self.policy, self.max_bytes
                    )
                except ssl.SSLCertVerificationError:
                    raise SourceRejected("source_tls_validation_failed") from None
                if self.complete_bytes:
                    await self.complete_bytes(self.max_bytes + 1, len(result[2]))
                if result[0] == 429:
                    raw_retry = result[1].get("retry-after", "60")
                    try:
                        seconds = float(raw_retry)
                    except ValueError:
                        try:
                            seconds = (
                                parsedate_to_datetime(raw_retry) - datetime.now(UTC)
                            ).total_seconds()
                        except (ValueError, TypeError):
                            seconds = 60
                    seconds = max(1, seconds) if math.isfinite(seconds) else 60
                    self.cooldowns[host] = time.monotonic() + seconds
                    raise SourceRejected("source_rate_limited", seconds)
                if "html" in result[1].get("content-type", "") and any(
                    marker in result[2][:20000].lower()
                    for marker in (b"cf-chl-", b"verify you are human", b"captcha challenge")
                ):
                    raise SourceRejected("source_access_challenge")
                return result
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
        if code == 429:
            raise SourceRejected("source_rate_limited")
        if code in {404, 410}:
            return
        if code != 200:
            raise SourceRejected("robots_unavailable")
        robots = RobotFileParser()
        robots.parse(body.decode("utf-8", errors="replace").splitlines())
        self.rules[parsed.netloc] = robots
        # A site that asks for slower reading gets it.
        asked = robots.crawl_delay(USER_AGENT)
        if asked:
            host = (parsed.hostname or "").lower()
            self.delays[host] = min(60.0, max(1.0, float(asked)))
        if not robots.can_fetch(USER_AGENT, url):
            raise SourceRejected("robots_disallowed")

    async def _allowed(self, url: str, kind: str) -> tuple[bytes, str]:
        """One approved reply of a content kind. One robots reading covers later ones."""
        for _ in range(4):
            self.policy.validate(url)
            known = self.rules.get(urlsplit(url).netloc)
            if known is None:
                await self._robots(url)
            elif not known.can_fetch(USER_AGENT, url):
                raise SourceRejected("robots_disallowed")
            code, headers, body = await self._request(url)
            if code in {301, 302, 303, 307, 308}:
                url = urljoin(url, headers.get("location", ""))
                continue
            if code != 200 or kind not in headers.get("content-type", ""):
                raise SourceRejected("source_response_rejected")
            return body, url
        raise SourceRejected("too_many_source_redirects")

    async def get_json(self, url: str) -> dict[str, Any]:
        body, _ = await self._allowed(url, "json")
        try:
            data = json.loads(body)
        except ValueError:
            raise SourceRejected("source_response_rejected") from None
        if not isinstance(data, dict):
            raise SourceRejected("source_response_rejected")
        return data

    async def get_html(self, url: str) -> tuple[str, str]:
        """The page text and the address it finally came from."""
        body, final = await self._allowed(url, "html")
        return body.decode("utf-8", errors="replace"), final

    async def fetch(self, url: str) -> FetchedDocument:
        return await self._fetch(url, True)

    async def fetch_api(self, url: str, method: str) -> FetchedDocument:
        if method not in {"mediawiki", "official-api"}:
            raise SourceRejected("source_api_method_not_allowed")
        for _ in range(4):
            self.policy.validate(url)
            await self._robots(url)
            code, headers, body = await self._request(url)
            if code in {301, 302, 303, 307, 308}:
                url = urljoin(url, headers.get("location", ""))
                continue
            if code == 429:
                raise SourceRejected("source_rate_limited")
            if code != 200 or "json" not in headers.get("content-type", ""):
                raise SourceRejected("source_api_response_rejected")
            data = json.loads(body)
            metadata = {"extraction_version": "api-text-v1"}
            if method == "mediawiki":
                pages = data.get("query", {}).get("pages", {})
                values = list(pages.values()) if isinstance(pages, dict) else pages
                if len(values) != 1:
                    raise SourceRejected("source_api_requires_one_page")
                page = values[0]
                text = page.get("extract", "")
                title = page.get("title", url)
                metadata["page_id"] = str(page.get("pageid", ""))
                revisions = page.get("revisions", [])
                if revisions:
                    metadata["revision_id"] = str(revisions[0].get("revid", ""))
            else:
                text = data.get("summary", data.get("description", data.get("text", "")))
                title = data.get("title", data.get("name", url))
                metadata["page_id"] = str(data.get("id", ""))
                metadata["revision_id"] = str(data.get("revision", data.get("updated", "")))
                attribution = str(data.get("url", url))
                parsed_attribution = urlsplit(attribution)
                metadata["attribution_url"] = (
                    attribution
                    if parsed_attribution.scheme in {"http", "https"}
                    and parsed_attribution.hostname
                    and not parsed_attribution.username
                    and not parsed_attribution.password
                    else url
                )
                if isinstance(data.get("number"), int):
                    metadata["episode_number"] = str(data["number"])
                    metadata["season_number"] = str(data.get("season", ""))
            if not isinstance(text, str):
                raise SourceRejected("source_api_schema_unsupported")
            text = normalize(BeautifulSoup(text, "html.parser").get_text(" ", strip=True))
            if len(text) < 30:
                raise SourceRejected("source_has_no_usable_text")
            return FetchedDocument(
                url=url,
                title=str(title)[:300],
                publisher=urlsplit(url).hostname or "",
                text=text,
                truncated=False,
                metadata=metadata,
            )
        raise SourceRejected("too_many_source_redirects")

    async def fetch_complete(self, url: str) -> FetchedDocument:
        return await self._fetch(url, False)

    async def _fetch(self, url: str, cap: bool) -> FetchedDocument:
        try:
            for _ in range(4):
                self.policy.validate(url)
                await self._robots(url)
                code, headers, body = await self._request(url)
                if any(
                    marker in body[:20000].lower()
                    for marker in (b"cf-chl-", b"verify you are human", b"captcha challenge")
                ):
                    raise SourceRejected("source_access_challenge")
                if code in {301, 302, 303, 307, 308}:
                    url = urljoin(url, headers.get("location", ""))
                    continue
                if code != 200:
                    raise SourceRejected("source_http_error")
                kind = headers.get("content-type", "").split(";")[0].lower()
                if kind not in {"text/html", "application/xhtml+xml", "text/plain"}:
                    raise SourceRejected("source_content_type_not_allowed")
                if kind == "text/plain":
                    text = body.decode("utf-8", errors="replace")
                    document = FetchedDocument(
                        url=url,
                        title=urlsplit(url).hostname or "Source",
                        publisher=urlsplit(url).hostname or "",
                        text=text,
                        truncated=False,
                        metadata={"extraction_version": "plain-text-v1"},
                    )
                else:
                    document = html_document(body, url)
                    text = document.text
                text = normalize(text)
                if len(text) < 30:
                    if document.metadata.get("links_json") not in {None, "[]"}:
                        document.metadata["document_role"] = "navigation-index"
                    else:
                        raise SourceRejected("source_has_no_usable_text")
                return document.model_copy(
                    update={
                        "text": text[: self.max_chars] if cap else text,
                        "truncated": cap and len(text) > self.max_chars,
                    }
                )
            raise SourceRejected("too_many_source_redirects")
        except (SourceRejected, InferenceFailure):
            raise
        except ssl.SSLCertVerificationError:
            raise SourceRejected("source_tls_validation_failed") from None
        except Exception:
            raise SourceRejected("source_fetch_failed") from None


class SearxngSearch:
    def __init__(
        self,
        base_url: str,
        policy: PublicSourcePolicy,
        *,
        navigation_only: bool = False,
        timeout: float = 20,
        interval: float = 1,
    ) -> None:
        parsed = urlsplit(base_url)
        if parsed.scheme != "http" or parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
            raise ValueError("SearXNG must be a trusted loopback endpoint")
        self.base_url, self.policy = base_url, policy
        self.navigation_only = navigation_only
        self.timeout, self.interval = timeout, interval
        self.gate = asyncio.Lock()
        self.last_search = 0.0

    async def search(self, query: str, limit: int) -> list[str]:
        return [result.url for result in await self.search_results(query, limit)]

    async def search_results(self, query: str, limit: int) -> list[SearchResult]:
        if limit <= 0:
            return []
        async with self.gate:
            delay = self.interval - (time.monotonic() - self.last_search)
            if delay > 0:
                await asyncio.sleep(delay)
            try:
                async with httpx.AsyncClient(timeout=self.timeout, trust_env=False) as client:
                    async with client.stream(
                        "GET",
                        self.base_url.rstrip("/") + "/search",
                        params={"q": query[:1500], "format": "json", "categories": "general"},
                    ) as response:
                        response.raise_for_status()
                        body = bytearray()
                        async for chunk in response.aiter_bytes():
                            body.extend(chunk)
                            if len(body) > 1_000_000:
                                raise SourceRejected("search_response_too_large")
                payload = json.loads(body)
                results = payload.get("results", [])
                if not isinstance(results, list):
                    raise SourceRejected("search_invalid_results")
                if not results and payload.get("unresponsive_engines"):
                    raise SourceRejected("search_upstream_unavailable")
            except SourceRejected:
                raise
            except (httpx.HTTPError, ValueError):
                raise SourceRejected("search_unavailable") from None
            finally:
                self.last_search = time.monotonic()
        accepted = []
        has_absolute_url = False
        seen: set[str] = set()
        for item in results:
            try:
                if not isinstance(item, dict) or not isinstance(item.get("url"), str):
                    continue
                parsed = urlsplit(item["url"])
                if parsed.scheme not in {"http", "https"} or not parsed.hostname:
                    continue
                has_absolute_url = True
                candidate_policy = self.policy
                if self.navigation_only:
                    host = parsed.hostname
                    if host in {"localhost", "localhost.localdomain"}:
                        continue
                    try:
                        if not self.policy.public_ip(host):
                            continue
                    except ValueError:
                        pass
                    candidate_policy = PublicSourcePolicy([host])
                candidate_policy.validate(item["url"])
                url = str(item["url"]).partition("#")[0]
                if url in seen:
                    continue
                seen.add(url)
                accepted.append(
                    SearchResult(
                        url, str(item.get("title", ""))[:300], str(item.get("content", ""))[:1000]
                    )
                )
                if len(accepted) >= min(limit, 20):
                    break
            except (SourceRejected, KeyError, ValueError):
                continue
        if results and not has_absolute_url:
            raise SourceRejected("search_result_urls_unusable")
        return accepted
