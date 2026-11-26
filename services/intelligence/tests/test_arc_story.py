import json
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from uuid import uuid4

from src.application.arc_contracts import ArcOutline, DevelopmentEvidence
from src.application.arc_grounding import word_spans
from src.application.arc_story import (
    ArcAccount,
    GroupReading,
    PropositionAudit,
    SectionRepair,
    StoryParagraph,
    StorySectionDraft,
    build_arc_story,
    reading_groups,
    render_markdown,
    verify,
)
from src.application.evidence_dossier import token_estimate
from src.application.ports.retrieval import ArcPassageSet, ArcSource, EvidenceHit
from src.application.research_contracts import InferenceFailure
from src.application.retrieval import EvidenceRetrieval
from src.domain.research import SourceDocument, SourcePassage

SCENES = {
    1: [
        "Mira left the harbor village at dawn.",
        "Her brother Tobin had vanished into the marsh a year earlier.",
    ],
    2: [
        "Tobin's lantern hung from a post at the marsh edge.",
        "The keeper told Mira the marsh floods every spring.",
    ],
    3: [
        "Mira crossed the marsh and found Tobin alive in a fisher's hut.",
        "Tobin had been hiding from the tax collector.",
    ],
}


def passage_set() -> ArcPassageSet:
    sources, sentences = [], []
    offset = 0
    for position, texts in SCENES.items():
        source_id, passage_id = uuid4(), uuid4()
        sources.append(
            ArcSource(source_id, f"Chapter {position}", position, "manga-chapter", None, "g", True)
        )
        for text in texts:
            sentences.append(
                DevelopmentEvidence(
                    id=f"e{offset}",
                    source_id=source_id,
                    source_hash="h",
                    passage_id=passage_id,
                    passage_hash="p",
                    passage_start=0,
                    start=offset,
                    end=offset + len(text),
                    text=text,
                    source_group="g",
                )
            )
            offset += len(text) + 1
    return ArcPassageSet(sentences, sources, [])


def payload(prompt):
    return json.loads(prompt[prompt.rindex("\n") + 1 :])


def script(*, drop_third=True, bad_cause=True, outage=False, log=None):
    state = {"synth": 0, "audit": 0}
    log = log if log is not None else []

    async def infer(prompt, schema, task):
        data = payload(prompt)
        log.append((schema.__name__, data))
        if schema is GroupReading:
            blocks = [[int(n) for n in block["sentences"]] for block in data["excerpts"]]
            last = blocks[-1][-1]
            return schema.model_validate(
                {
                    "scenes": [
                        {
                            "summary": f"Scene built from excerpts {b[0]} to {b[-1]}.",
                            "sentences": [*b, 999],
                        }
                        for b in blocks
                    ],
                    "participants": ["Mira", "Tobin"],
                    "carried_state": f"State after excerpts up to {last}.",
                }
            )
        if schema is ArcAccount:
            state["synth"] += 1
            scenes = [s for r in data["readings"] for s in r["scenes"]]
            keep = scenes[:2] if drop_third and state["synth"] == 1 else scenes
            return schema.model_validate(
                {
                    "paragraphs": [
                        {
                            "text": "Mira set out to find her missing brother, and "
                            + f"the account continues through scene {i}.",
                            "sentences": s["sentences"],
                        }
                        for i, s in enumerate(keep, 1)
                    ],
                    "threads": ["Mira's search"],
                }
            )
        if schema is ArcOutline:
            count = len(data)
            return schema.model_validate(
                {
                    "sections": [
                        {"heading": "The search for Tobin", "paragraphs": list(range(1, count + 1))}
                    ]
                }
            )
        if schema is StorySectionDraft:
            return schema.model_validate(
                {
                    "heading": data["heading"],
                    "paragraphs": [
                        {
                            "text": "Mira left the village because Tobin owed her money, and "
                            "she crossed the marsh to find him.",
                            "sentences": [1, 2, 5, 6],
                        }
                    ],
                }
            )
        if schema is PropositionAudit:
            if outage:
                raise InferenceFailure("rate_limited")
            state["audit"] += 1
            text = data["paragraphs"][0]["text"]
            bad = bad_cause and "owed her money" in text
            return schema.model_validate(
                {
                    "findings": [
                        {
                            "paragraph": 0,
                            "proposition": "Tobin owed Mira money",
                            "kind": "motivation",
                            "verdict": "unsupported" if bad else "supported",
                            "reason": "The excerpts give no such reason",
                        }
                    ]
                }
            )
        if schema is SectionRepair:
            return schema.model_validate(
                {
                    "paragraphs": [
                        {
                            "index": 0,
                            "text": "Mira left the village at dawn to search for Tobin, who had "
                            "vanished into the marsh a year earlier; the sources give no other "
                            "reason, and she later found him hiding from the tax collector.",
                            "sentences": [1, 2, 5, 6],
                        }
                    ]
                }
            )
        raise AssertionError(schema)

    return infer, log


async def test_reading_synthesis_coverage_repair_and_markdown():
    passages = passage_set()
    infer, log = script()
    story = await build_arc_story("The Marsh", passages, None, infer)
    names = [name for name, _ in log]
    # Three position groups are not required; a single budgeted group may hold them all,
    # but the first synthesis omitted position 3, so exactly one coverage rewrite follows.
    assert names.count("ArcAccount") == 2
    rewrite = [d for n, d in log if n == "ArcAccount"][1]
    assert "previous_draft" in rewrite and rewrite["required_positions"] == [1, 2, 3]
    assert all(count > 0 for count in story.coverage.values())
    # Unknown sentence number 999 was dropped, never resolved.
    assert all(999 not in p.sentences for p in story.account.paragraphs)
    section = story.sections[0]
    assert section.status == "verified" and section.repairs == 1
    assert "owed her money" not in section.paragraphs[0].text
    assert "later found him hiding" in section.paragraphs[0].text
    repair = [d for n, d in log if n == "SectionRepair"][0]
    target = repair["targets"][0]
    assert target["problems"][0]["proposition"] == "Tobin owed Mira money"
    assert "owed her money" in target["text"]
    assert story.understanding.status == "verified"
    assert "Tobin had been hiding from the tax collector." in repair["excerpts"].values()
    markdown = render_markdown(story)
    assert "## Arc Understanding Document" in markdown and "## Article" in markdown
    assert '"Mira crossed the marsh and found Tobin alive in a fisher\'s hut."' in markdown
    assert "Position 3" in markdown


async def test_reading_carries_story_state_across_position_groups():
    passages = passage_set()
    numbered = {i: s for i, s in enumerate(passages.sentences, 1)}
    # Within budget, groups break where the source position changes.
    sizes = [token_estimate(s.text) for s in numbered.values()]
    budget = max(sum(sizes[i : i + 2]) for i in range(0, 6, 2))
    assert reading_groups(passages, numbered, budget) == [[1, 2], [3, 4], [5, 6]]
    # A single position larger than the budget is still split.
    assert all(len(g) == 1 for g in reading_groups(passages, numbered, budget=1))
    log = []
    infer, _ = script(log=log)
    await build_arc_story("The Marsh", passages, None, infer)
    reads = [d for n, d in log if n == "GroupReading"]
    assert len(reads) == 1  # default budget keeps this short arc together


async def test_verification_outage_never_discards_prose():
    infer, _ = script(outage=True, drop_third=False)
    story = await build_arc_story("The Marsh", passage_set(), None, infer)
    section = story.sections[0]
    assert section.status == "unverified" and section.note == "rate_limited"
    assert section.paragraphs and "owed her money" in section.paragraphs[0].text
    assert any("unverified" in issue for issue in story.issues)


class FakeIndex:
    def __init__(self, metadata, hits):
        self.metadata, self.hits = metadata, hits

    async def source_metadata(self, universe, continuity, source_ids=None):
        return self.metadata

    async def passages(self, universe, continuity, source_ids=None, query=None):
        return [h for h in self.hits if source_ids is None or h.source.id in source_ids]


def archived(universe, continuity, title, position, text, **meta):
    source = SourceDocument(
        id=uuid4(),
        universe_id=universe,
        continuity_id=continuity,
        url=f"https://example.test/{title}",
        title=title,
        publisher="Example",
        text=text,
        content_hash=f"hash-{title}",
        retrieved_at=datetime.now(UTC),
        permission_basis="test",
        source_scope="test",
        public_web=True,
        truncated=False,
    )
    passage = SourcePassage(uuid4(), source.id, 0, 0, len(text), text, f"p-{title}")
    provenance = {
        "position_basis": "manga-chapter",
        "presentation_position": position,
        "content_hash": source.content_hash,
        "public_web": True,
        "cloud_content_allowed": meta.pop("cloud", True),
        **meta,
    }
    return source, passage, provenance


async def test_arc_passages_fence_range_spoilers_permissions_and_order():
    universe, continuity = uuid4(), uuid4()
    rows = [
        archived(universe, continuity, "later", 5, "Mira reached the sea. It was calm."),
        archived(universe, continuity, "first", 1, "Mira left home. She walked north."),
        archived(universe, continuity, "outside", 9, "A stranger arrived. Nobody knew him."),
        archived(
            universe, continuity, "local-only", 2, "Mira rested a day. She ate bread.", cloud=False
        ),
        archived(universe, continuity, "copy-of-first", 1, "Mira left home. She walked north."),
        archived(
            universe,
            continuity,
            "other-basis",
            3,
            "Mira sailed away. It rained.",
            position_basis="broadcast-presentation",
        ),
    ]
    metadata = {s.id: meta for s, _, meta in rows}
    hits = [EvidenceHit(p, s) for s, p, _ in rows]

    @asynccontextmanager
    async def transactions():
        yield FakeIndex(metadata, hits)

    retrieval = EvidenceRetrieval(transactions, embeddings=None)
    result = await retrieval.arc_passages(
        universe,
        continuity,
        first_position=1,
        last_position=7,
        position_basis="manga-chapter",
        spoiler_position=5,
    )
    assert [s.label for s in result.sources] == ["copy-of-first", "local-only", "later"]
    assert [s.text for s in result.sentences][:2] == ["Mira left home.", "She walked north."]
    assert all("stranger" not in s.text and "sailed" not in s.text for s in result.sentences)
    texts = [s.text for s in result.sentences]
    assert len(texts) == len(set(texts))  # the re-archived page adds nothing
    assert result.cloud_eligible is False  # one permitted source is local-only
    bounded = await retrieval.arc_passages(
        universe,
        continuity,
        first_position=1,
        last_position=7,
        position_basis="manga-chapter",
        spoiler_position=2,
    )
    assert [s.label for s in bounded.sources] == ["copy-of-first", "local-only"]


async def test_copied_wording_is_rewritten_from_facts_without_showing_the_prose():
    passages = passage_set()
    numbered = {i: s for i, s in enumerate(passages.sentences, 1)}
    copied_text = " ".join(s.text for s in passages.sentences[:3])
    paragraphs = [
        StoryParagraph(text="An untouched paragraph about the harbor village.", sentences=[1]),
        StoryParagraph(text=copied_text, sentences=[1, 2, 3]),
    ]
    copied = set().union(*(word_spans(s.text, 18) for s in numbered.values()))
    copied |= word_spans(copied_text, 18)
    repairs = []

    async def infer(prompt, schema, task):
        data = payload(prompt)
        if schema is PropositionAudit:
            return schema.model_validate(
                {
                    "findings": [
                        {
                            "paragraph": p["index"],
                            "proposition": f"Fact in paragraph {p['index']}",
                            "kind": "event",
                            "verdict": "supported",
                            "reason": "Stated",
                        }
                        for p in data["paragraphs"]
                    ]
                }
            )
        repairs.append(data)
        return schema.model_validate(
            {
                "paragraphs": [
                    {
                        "index": 1,
                        "text": "At daybreak Mira set out, a year after losing her brother [2, 3].",
                        "sentences": [1],
                    },
                    {
                        "index": 0,
                        "text": "An unrequested change to a paragraph that already passed.",
                        "sentences": [1],
                    },
                ]
            }
        )

    section = await verify("Marsh", paragraphs, numbered, set(), copied, {}, {}, infer)
    target = repairs[0]["targets"][0]
    assert "text" not in target
    assert target["facts_to_express_in_new_words"] == ["Fact in paragraph 1"]
    assert section.paragraphs[0] == paragraphs[0]
    assert "[" not in section.paragraphs[1].text
    assert section.paragraphs[1].sentences == [1, 2, 3]
    assert len(section.paragraphs) == 2
