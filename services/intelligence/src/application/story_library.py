"""A file-based story library: any story's saved sources become ordered, citable sentences."""

from datetime import UTC, datetime
from uuid import NAMESPACE_URL, uuid5

from pydantic import Field, model_validator

from src.application.arc_contracts import DevelopmentEvidence
from src.application.event_extraction import evidence_units
from src.application.ports.retrieval import ArcPassageSet, ArcSource, EvidenceHit
from src.application.research_contracts import StructuredModel
from src.application.retrieval import sentence_evidence
from src.domain.research import SourceDocument, digest, passages_for

SLUG = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"


class LibraryArc(StructuredModel):
    key: str = Field(pattern=SLUG, max_length=80)
    title: str = Field(min_length=1, max_length=100)
    # Story headings for this arc, when a page covers several stories.
    sections: list[str] = Field(default_factory=list, max_length=20)
    # Move return visits and endings to where they happen; off for sources already
    # told in order.
    reorder: bool = True


class LibrarySite(StructuredModel):
    """A wiki you approved for this world.

    Give ``api`` (its MediaWiki api.php), or ``pages`` (the address article titles
    are added to) when the site's robots rules allow pages but not the API.
    """

    api: str = Field(default="", pattern=r"^(https://[^?#]+api\.php)?$", max_length=300)
    pages: str = Field(default="", pattern=r"^(https://[^?#]+/)?$", max_length=300)
    cloud_allowed: bool = False
    # Headings whose text tells the story.
    sections: list[str] = Field(
        default_factory=lambda: ["plot", "story", "synopsis", "summary"], max_length=20
    )

    @model_validator(mode="after")
    def one_way_in(self) -> "LibrarySite":
        if bool(self.api) == bool(self.pages):
            raise ValueError("A site needs either its api address or its pages address")
        return self

    @property
    def address(self) -> str:
        return self.api or self.pages


class LibraryWorld(StructuredModel):
    """``world.json``: what a story is called and how its positions are named."""

    slug: str = Field(pattern=SLUG, max_length=90)
    title: str = Field(min_length=1, max_length=180)
    medium: str = Field(min_length=1, max_length=40)
    position_word: str = Field(default="chapter", pattern=r"^[a-z][a-z -]{0,30}$")
    arcs: list[LibraryArc] = Field(min_length=1, max_length=200)
    sites: list[LibrarySite] = Field(default_factory=list, max_length=8)

    @model_validator(mode="after")
    def distinct_arcs(self) -> "LibraryWorld":
        if len({a.key for a in self.arcs}) != len(self.arcs):
            raise ValueError("Arc keys must be distinct")
        return self


class LibrarySource(StructuredModel):
    """One saved page. ``cloud_allowed`` stays false unless its site permits sharing."""

    url: str = Field(pattern=r"^https?://", max_length=1000)
    title: str = Field(min_length=1, max_length=300)
    position: int = Field(default=1, ge=1, le=100000)
    text: str = Field(min_length=30, max_length=500_000)
    licence: str = Field(default="", max_length=300)
    cloud_allowed: bool = False


def page_order(source: LibrarySource) -> tuple[int, int, str, str]:
    return source.position, -len(source.text), source.title, source.url


def library_passages(
    world: LibraryWorld, sources: list[LibrarySource], *, ordered: bool = False
) -> ArcPassageSet:
    """Sentences in page order, or as given when already in story order.

    A sentence already read is not repeated.
    """
    universe = uuid5(NAMESPACE_URL, f"chronicles:library:{world.slug}")
    continuity = uuid5(universe, world.medium)
    listed: list[ArcSource] = []
    sentences: list[DevelopmentEvidence] = []
    seen: set[str] = set()
    for page in sources if ordered else sorted(sources, key=page_order):
        document = SourceDocument(
            id=uuid5(universe, f"{page.url}:{digest(page.text)}"),
            universe_id=universe,
            continuity_id=continuity,
            url=page.url,
            title=page.title,
            publisher=page.url.split("/")[2],
            text=page.text,
            content_hash=digest(page.text),
            retrieved_at=datetime.now(UTC),
            permission_basis=page.licence or "Saved for private local use",
            source_scope=world.medium,
            public_web=True,
            truncated=False,
        )
        meta = {"presentation_position": page.position, "position_basis": world.position_word}
        fresh: list[DevelopmentEvidence] = []
        for passage in passages_for(document):
            for unit in evidence_units([passage]):
                evidence = sentence_evidence(EvidenceHit(passage, document), unit, meta)
                if evidence is None:
                    continue
                key = " ".join(evidence.text.casefold().split())
                if key not in seen:
                    seen.add(key)
                    fresh.append(evidence)
        if not fresh:
            continue
        sentences += fresh
        listed.append(
            ArcSource(
                id=document.id,
                label=page.title,
                position=page.position,
                position_basis=world.position_word,
                authority=None,
                source_group=document.publisher,
                cloud_eligible=page.cloud_allowed,
                url=page.url,
            )
        )
    issues = [] if listed else ["no_readable_sources"]
    return ArcPassageSet(sentences, listed, issues)
