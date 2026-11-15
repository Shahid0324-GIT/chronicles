"""Owned synthetic evidence: never represented as live fictional-universe research."""

from dataclasses import replace
from uuid import uuid4

from src.application.evidence_bundles import EvidenceBundleBuilder, connection_score
from src.application.ports.retrieval import EvidenceHit
from src.application.relationship_contracts import InvestigationSubject
from src.domain.entities import now
from src.domain.research import SourceDocument, SourcePassage, digest


def evidence(text, *, source=None, ordinal=0, start=0, section="Interactions"):
    source = source or SourceDocument(
        uuid4(),
        uuid4(),
        uuid4(),
        "https://owned.example/story",
        "Owned",
        "Owned",
        text,
        digest(text),
        now(),
        "Owned permitted test",
        "Owned test continuity",
        True,
        False,
        "owned-primary",
        {"authority": "primary", "language": "en", "cloud_content_allowed": False},
    )
    passage = SourcePassage(
        uuid4(), source.id, ordinal, start, start + len(text), text, digest(text), section
    )
    return EvidenceHit(passage, source)


SUBJECTS = [
    InvestigationSubject(name="Mira", aliases=["ミラ", "Mira Vale"]),
    InvestigationSubject(name="Ron", aliases=["ロン", "Ron Stone"]),
]


def test_connected_action_outranks_alias_rich_mentions_and_author_production():
    action = "Mira and Ron became partners. Mira helped Ron build the observatory."
    profile = "Mira ミラ Mira Vale Ron ロン Ron Stone are names on this page."
    production = "I am writing the story of Mira helping Ron to rescue another person."
    assert connection_score(action, SUBJECTS, "Investigate Mira and Ron") > max(
        connection_score(profile, SUBJECTS, "Investigate Mira and Ron"),
        connection_score(production, SUBJECTS, "Investigate Mira and Ron"),
    )
    hits = [evidence(profile), evidence(action)]
    hits[1] = replace(
        hits[1], source=replace(hits[1].source, continuity_id=hits[0].source.continuity_id)
    )
    bundles = EvidenceBundleBuilder().build(
        hits, SUBJECTS, "Mira and Ron", hits[0].source.continuity_id, None, 100
    )
    assert bundles[0].anchor_passage_id == hits[1].passage.id


def test_bundle_preserves_exact_context_offsets_deduplication_and_scope():
    first = evidence("Mira met Ron.", start=700, ordinal=0)
    action = evidence("Mira helped Ron.", source=first.source, start=713, ordinal=1)
    after = evidence("Ron thanked Mira.", source=first.source, start=728, ordinal=2)
    other_scope = evidence("Mira helped Ron in another adaptation.")
    other_section = evidence(
        "Mira harmed Ron.", source=first.source, ordinal=2, start=800, section="Animation"
    )
    hits = [action, first, after, other_scope, other_section, action]
    bundles = EvidenceBundleBuilder().build(
        hits, SUBJECTS, "Mira and Ron", first.source.continuity_id, None, 500
    )
    bundle = bundles[0]
    assert bundle.anchor_passage_id == action.passage.id
    assert len(bundle.passages) == 3
    assert {p.start for p in bundle.passages} == {700, 713, 728}
    assert all(p.source_revision == first.source.content_hash for p in bundle.passages)
    assert not any(p.cloud_allowed for p in bundle.passages)
    assert (
        EvidenceBundleBuilder().build(
            hits, SUBJECTS, "Mira and Ron", first.source.continuity_id, 3, 500
        )
        == []
    )
    changed = [replace(h, source=replace(h.source, content_hash="new revision")) for h in hits]
    assert (
        EvidenceBundleBuilder()
        .build(changed, SUBJECTS, "Mira and Ron", first.source.continuity_id, None, 500)[0]
        .id
        != bundle.id
    )
