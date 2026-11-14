"""Clean Chrome context; every allowed request uses the pinned, policy-checked reader."""

import asyncio
from collections.abc import Awaitable, Callable
from urllib.parse import urlsplit

from playwright.async_api import Route, async_playwright

from src.application.research import FetchedDocument, SourceRejected
from src.infrastructure.document_structure import html_document

ResourceReader = Callable[[str], Awaitable[tuple[int, dict[str, str], bytes]]]


class ControlledBrowserExtractor:
    def __init__(self, max_bytes: int, timeout: float = 45, max_requests: int = 30) -> None:
        self.max_bytes, self.timeout, self.max_requests = max_bytes, timeout, max_requests

    async def extract(self, url: str, read: ResourceReader) -> FetchedDocument:
        origin = urlsplit(url)[:2]
        failures: list[str] = []
        requests = 0
        cache: dict[str, tuple[int, dict[str, str], bytes]] = {}
        async with asyncio.timeout(self.timeout), async_playwright() as runtime:
            browser = await runtime.chromium.launch(
                channel="chrome",
                headless=True,
                args=[
                    "--disable-background-networking",
                    "--disable-sync",
                    "--no-first-run",
                    "--disable-extensions",
                    "--js-flags=--max-old-space-size=128",
                ],
            )
            try:
                context = await browser.new_context(service_workers="block", accept_downloads=False)
                await context.route_web_socket("**/*", lambda socket: socket.close())
                await context.add_init_script(
                    "window.RTCPeerConnection=undefined;window.webkitRTCPeerConnection=undefined;"
                    "window.WebTransport=undefined;window.Worker=undefined;"
                )

                async def route_request(route: Route) -> None:
                    nonlocal requests
                    request = route.request
                    target = request.url.partition("#")[0]
                    if (
                        request.method != "GET"
                        or urlsplit(target)[:2] != origin
                        or request.resource_type not in {"document", "script", "fetch", "xhr"}
                        or request.resource_type == "document"
                        and target != url.partition("#")[0]
                    ):
                        await route.abort()
                        return
                    requests += 1
                    if requests > self.max_requests:
                        failures.append("source_browser_request_budget_exhausted")
                        await route.abort()
                        return
                    try:
                        if target not in cache:
                            cache[target] = await read(target)
                        code, headers, body = cache[target]
                        lower = body[:20000].lower()
                        if code != 200 or any(
                            marker in lower
                            for marker in (
                                b"cf-chl-",
                                b"verify you are human",
                                b"captcha challenge",
                            )
                        ):
                            raise SourceRejected("source_browser_access_rejected")
                        await route.fulfill(
                            status=code,
                            headers={
                                "content-type": headers.get(
                                    "content-type", "application/octet-stream"
                                )
                            },
                            body=body,
                        )
                    except SourceRejected as error:
                        failures.append(str(error))
                        await route.abort()

                await context.route("**/*", route_request)
                page = await context.new_page()
                await page.goto(
                    url, wait_until="domcontentloaded", timeout=int(self.timeout * 1000)
                )
                await page.wait_for_function(
                    "document.body && document.body.innerText.trim().length >= 30", timeout=10000
                )
                await page.wait_for_load_state("networkidle", timeout=10000)
                markup = await page.evaluate(
                    "maximum => document.documentElement.outerHTML.slice(0, maximum + 1)",
                    self.max_bytes,
                )
                if failures:
                    raise SourceRejected(failures[0])
                if len(markup.encode("utf-8")) > self.max_bytes:
                    raise SourceRejected("source_browser_document_too_large")
                document = html_document(markup, url, rendered=True)
                if len(document.text) < 30:
                    raise SourceRejected("source_has_no_usable_text")
                return document
            except SourceRejected:
                raise
            except Exception:
                raise SourceRejected(failures[0] if failures else "source_browser_failed") from None
            finally:
                await browser.close()
