"""Ideas for where a story might be told. They are guesses until a site is checked."""

import json
from urllib.parse import urlsplit

from pydantic import Field

from src.application.knowledge_presentation import Infer
from src.application.research_contracts import StructuredModel

# Sites whose terms forbid automated reading, whatever their robots rules allow.
REFUSED = {"fandom.com": "Fandom's terms forbid automated reading (checked 2026-11-27)"}


class SiteIdea(StructuredModel):
    name: str
    url: str
    why: str = ""


class SiteIdeas(StructuredModel):
    sites: list[SiteIdea] = Field(default_factory=list, max_length=8)


def refusal(url: str) -> str:
    host = (urlsplit(url).hostname or "").casefold()
    return next(
        (why for domain, why in REFUSED.items() if host == domain or host.endswith("." + domain)),
        "",
    )


async def suggest_sites(story: str, arc: str, about: str, infer: Infer) -> list[SiteIdea]:
    reply = SiteIdeas.model_validate(
        await infer(
            "Suggest up to five independent MediaWiki wikis likely to tell this story arc "
            "in detail, such as community or publisher-independent wikis. Never suggest "
            "fandom.com. For each give the wiki's name, the full https address of the page "
            "about this story or arc, and one short reason.\n"
            'Return only JSON: {"sites":[{"name":"","url":"https://","why":""}]}\n'
            + json.dumps({"story": story, "arc": arc, "about": about}, ensure_ascii=False),
            SiteIdeas,
            "presentation",
        )
    )
    seen: set[str] = set()
    ideas: list[SiteIdea] = []
    for idea in reply.sites:
        host = urlsplit(idea.url).hostname or ""
        if idea.url.startswith("https://") and host and host not in seen and not refusal(idea.url):
            seen.add(host)
            ideas.append(SiteIdea(name=idea.name[:80], url=idea.url[:1000], why=idea.why[:200]))
    return ideas[:5]
