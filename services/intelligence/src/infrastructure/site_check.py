"""Whether the app may read a wiki, and how: its API, or its pages."""

from dataclasses import dataclass, field
from urllib.parse import quote, unquote, urlsplit

from src.application.research import SourceRejected
from src.application.scout import WikiSite
from src.application.site_suggest import refusal
from src.application.story_library import LibrarySite
from src.infrastructure.mediawiki import MediaWikiPages, MediaWikiSite
from src.infrastructure.sources import PublicDocumentFetcher, PublicSourcePolicy

MAX_PAGE_BYTES = 3_000_000
REASONS = {
    "robots_disallowed": "The site's crawl rules do not allow this to be read",
    "robots_unavailable": "The site would not share its crawl rules, so it is left alone",
    "source_access_challenge": (
        "The site shows a bot check. The app does not work around bot checks"
    ),
    "source_rate_limited": "The site asked the app to slow down; try again later",
    "source_url_not_approved": "That address is not a public web page",
    "non_public_source_address": "That address is not a public web page",
    "source_has_no_usable_text": "That page does not look like a wiki article",
    "source_too_large": "That page is too large to read",
    "source_tls_validation_failed": "The site's security certificate could not be checked",
}


@dataclass
class SiteReport:
    allowed: bool
    reason: str = ""
    name: str = ""
    licence: str = ""
    page: str = ""
    headings: list[str] = field(default_factory=list)
    site: LibrarySite | None = None


def _title(path: str, prefix: str) -> str:
    return unquote(path[len(prefix) :]).replace("_", " ").strip()


async def check_site(url: str) -> SiteReport:
    """Read the linked page the way the app would, and say what was found."""
    parsed = urlsplit(url.strip())
    host = (parsed.hostname or "").casefold()
    if parsed.scheme != "https" or not host or not PublicSourcePolicy.public_url(url):
        return SiteReport(False, "Give the full https address of a public wiki page")
    if why := refusal(url):
        return SiteReport(False, why)
    if parsed.path in ("", "/"):
        return SiteReport(False, "Paste the link to the page about your story, not the front page")
    fetcher = PublicDocumentFetcher(PublicSourcePolicy([host]), MAX_PAGE_BYTES, MAX_PAGE_BYTES)
    candidates: list[tuple[LibrarySite, str]] = []
    # The API first: it is the way MediaWiki offers to programs.
    for api in (f"https://{host}/w/api.php", f"https://{host}/api.php"):
        reader = MediaWikiSite(LibrarySite(api=api), fetcher)
        try:
            general = (await reader._site())["general"]
        except (SourceRejected, KeyError, ValueError) as error:
            if str(error) == "source_access_challenge":
                return SiteReport(False, REASONS[str(error)])
            continue
        prefix = str(general.get("articlepath", "/wiki/$1")).replace("$1", "")
        if parsed.path.startswith(prefix):
            candidates.append((LibrarySite(api=api), _title(parsed.path, prefix)))
        break
    if not candidates:
        prefix = "/wiki/" if parsed.path.startswith("/wiki/") else "/"
        base = f"https://{host}{quote(prefix)}"
        candidates.append((LibrarySite(pages=base), _title(parsed.path, prefix)))
    config, title = candidates[0]
    site: WikiSite = (MediaWikiSite if config.api else MediaWikiPages)(config, fetcher)
    try:
        page = await site.page(title)
        name, licence = await site.credit()
    except (SourceRejected, KeyError, ValueError) as error:
        return SiteReport(
            False, REASONS.get(str(error), "The app could not read that page as a wiki article")
        )
    headings = [s.heading for s in page.sections if s.heading]
    return SiteReport(
        True,
        name=name,
        licence=licence,
        page=page.title,
        headings=headings[:60],
        site=config,
    )
