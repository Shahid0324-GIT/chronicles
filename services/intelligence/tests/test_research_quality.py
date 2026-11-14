"""Owned material: regressions for information loss and unsafe publication shortcuts."""

import json
from uuid import uuid4

import pytest

from src.application.evidence_dossier import EvidenceDossierBuilder
from src.application.research_policy import ResearchPolicy
from src.domain.entities import now
from src.domain.knowledge import direct_primary_claim
from src.domain.research import SourceDocument, digest, passages_for, scope_structure
from src.infrastructure.document_structure import html_document
from src.infrastructure.sources import PublicDocumentFetcher, PublicSourcePolicy, SourceRejected


def test_depth_presets_allow_explicit_overrides_and_frozen_round_trip():
    quick, focused, deep = (ResearchPolicy(depth=d) for d in ["quick", "focused", "deep"])
    assert quick.max_requests < focused.max_requests < deep.max_requests
    assert quick.dossier_tokens < focused.dossier_tokens < deep.dossier_tokens
    policy = ResearchPolicy(depth="deep", max_documents=7, max_tokens=12345)
    assert policy.max_documents == 7 and policy.max_tokens == 12345
    assert ResearchPolicy.model_validate(policy.model_dump()) == policy


def test_research_dossier_ignores_metadata_words_and_unrelated_facts():
    facts = [
        {"id": "a", "payload": {"type": "CHARACTER", "name": "Ron", "description": "A giant."}},
        {
            "id": "b",
            "payload": {"type": "CHARACTER", "name": "Mira", "description": "Mira helped Ron."},
        },
    ]
    dossier = EvidenceDossierBuilder().select(facts, "Mira character", 1000, require_relevance=True)
    assert [fact["id"] for fact in dossier["facts"]] == ["b"]
    # A recap whose eligible resources were already explicitly scoped can retain all of them.
    assert len(EvidenceDossierBuilder().select(facts, "recap", 1000)["facts"]) == 2


async def test_retry_after_stops_repeated_host_requests(monkeypatch):
    calls = []

    def request(url, policy, maximum):
        calls.append(url)
        return 429, {"retry-after": "120"}, b"slow down"

    monkeypatch.setattr("src.infrastructure.sources.pinned_request", request)
    fetcher = PublicDocumentFetcher(PublicSourcePolicy(["owned.example"]), 10000, 10000)
    for _ in range(2):
        with pytest.raises(SourceRejected) as failure:
            await fetcher._request("https://owned.example/document")
        assert str(failure.value) == "source_rate_limited"
        assert 0 < failure.value.retry_after <= 120
    assert len(calls) == 1


def test_exact_registry_grant_does_not_authorize_other_paths_or_private_urls():
    fetcher = PublicDocumentFetcher(PublicSourcePolicy([]), 10000, 10000)
    fetcher.authorize_registered(["https://new.example/permitted"])
    assert fetcher.policy.is_approved("https://new.example/permitted#section")
    assert fetcher.policy.is_approved("https://new.example/robots.txt")
    assert not fetcher.policy.is_approved("https://new.example/private")
    fetcher.authorize_registered([])
    assert not fetcher.policy.is_approved("https://new.example/permitted")
    for url in [
        "http://127.0.0.1/",
        "http://169.254.169.254/",
        "http://[::1]/",
        "http://x.local/a",
    ]:
        assert not PublicSourcePolicy.public_url(url)


def test_primary_shortcut_requires_literal_correct_subject_and_noninterpretive_claim():
    quote = "Mira is a courier. Ron is a giant. Mira helped Ron."
    evidence = [{"quote": quote, "public_web": True, "provenance": {"authority": "primary"}}]
    assert direct_primary_claim({"name": "Mira", "description": "Mira is a courier."}, evidence)
    assert not direct_primary_claim({"name": "Mira", "description": "Mira is a giant."}, evidence)
    assert not direct_primary_claim({"name": "Mira", "description": "Ron is a giant."}, evidence)
    assert not direct_primary_claim(
        {"name": "Mira", "description": "Mira might be a courier."}, evidence
    )
    assert not direct_primary_claim(
        {"name": "Mira", "description": "Mira is a courier."},
        [{**evidence[0], "provenance": {"authority": "unverified"}}],
    )


def test_primary_subject_heading_binds_only_its_own_literal_statement():
    quote = "A courier who lives by the sea."
    evidence = [
        {
            "quote": quote,
            "public_web": True,
            "passage_start": 10,
            "quote_start": 0,
            "quote_end": len(quote),
            "provenance": {
                "authority": "primary",
                "sections_json": json.dumps(
                    [
                        {"title": "Mira", "start": 0, "end": 80},
                        {"title": "Ron", "start": 80, "end": 150},
                    ]
                ),
            },
        }
    ]
    assert direct_primary_claim({"name": "Mira", "description": quote}, evidence)
    assert not direct_primary_claim({"name": "Ron", "description": quote}, evidence)
    uncertain = [{**evidence[0], "quote": "I think Mira is a courier."}]
    assert not direct_primary_claim(
        {"name": "Mira", "description": "Mira is a courier."}, uncertain
    )


def test_related_interaction_requires_the_actual_named_pair_and_actuality():
    from src.domain.knowledge import relation_structure
    from src.domain.value_objects import NodeType, RelationshipType

    def related(text, a="Mira", b="Ron"):
        return relation_structure(
            RelationshipType.RELATED_TO, NodeType.CHARACTER, NodeType.CHARACTER, [text], a, b
        )

    assert related("Mira helped Ron.")
    assert not related("Mira would have helped Ron.")
    assert not related("Mira and Ron watched Cain rescue Dara.")
    assert related("Mira and Ron became master and knight, and Cain started training.")
    assert not related(
        "Mira and Ron became master and knight, and Cain started training.", "Ron", "Cain"
    )


def test_mixed_media_archive_preserves_every_section_but_indexes_only_explicit_scope():
    document = html_document(
        "<main><h1>Author Q&A</h1><p>１．【Anime】 Mira helped Ron in the adaptation.</p>"
        "<p>１６．【Novel – Character】 Mira and Ron became master and knight.</p>"
        "<p>１７．【Anime】 Ron becomes a different person in the adaptation.</p></main>",
        "https://owned.example/qa",
    )
    source = SourceDocument(
        uuid4(),
        uuid4(),
        uuid4(),
        document.url,
        document.title,
        document.publisher,
        document.text,
        digest(document.text),
        now(),
        "Owned test",
        "Novel only",
        True,
        False,
        provenance={**document.metadata, "eligible_section_terms": ["Novel"]},
    )
    passages = passages_for(source)
    assert len(passages) == 1 and "became master and knight" in passages[0].text
    assert "adaptation" not in passages[0].text
    assert "adaptation" in source.text
    assert source.text[passages[0].start : passages[0].end] == passages[0].text


def test_long_structure_and_late_evidence_survive_archive_chunking_and_excerpt_scope():
    html = '<html lang="en"><title>Owned</title><main><h1>Background</h1><p>'
    html += "Earlier unrelated material. " * 900
    html += "</p><h2>Relationship</h2><p>Mira helped Ron at the observatory.</p>"
    html += '<a href="/ron">Ron profile</a></main></html>'
    document = html_document(html, "https://owned.example/chronicle")
    assert len(document.text) > 12000 and not document.truncated
    sections = json.loads(document.metadata["sections_json"])
    late = next(s for s in sections if s["title"] == "Relationship")
    assert document.text[late["start"] :].startswith("Relationship")
    source = SourceDocument(
        uuid4(),
        uuid4(),
        uuid4(),
        document.url,
        document.title,
        document.publisher,
        document.text,
        digest(document.text),
        now(),
        "Owned test",
        "Test scope",
        False,
        False,
        provenance=document.metadata,
    )
    passages = passages_for(source)
    assert all(document.text[p.start : p.end] == p.text for p in passages)
    assert any("Mira helped Ron" in p.text for p in passages)
    scoped = scope_structure(document.metadata, late["start"], len(document.text))
    assert json.loads(scoped["links_json"])[0]["url"] == "https://owned.example/ron"
    assert all(s["title"] != "Background" for s in json.loads(scoped["sections_json"]))


async def test_permitted_long_document_is_complete_but_denied_robots_still_stop_fetch(monkeypatch):
    html = b"<main><h1>Evidence</h1><p>" + b"A useful archived sentence. " * 2000 + b"</p></main>"
    calls = []

    def request(url, policy, maximum):
        policy.validate(url)
        calls.append(url)
        if url.endswith("robots.txt"):
            return 200, {}, b"User-agent: *\nAllow: /"
        return 200, {"content-type": "text/html"}, html

    monkeypatch.setattr("src.infrastructure.sources.pinned_request", request)
    fetcher = PublicDocumentFetcher(PublicSourcePolicy([]), 200000, 12000)
    fetcher.authorize_registered(["https://new.example/document"])
    document = await fetcher.fetch_complete("https://new.example/document")
    assert len(document.text) > 12000 and not document.truncated
    assert calls[0].endswith("robots.txt")
    fetcher.authorize_registered([])
    with pytest.raises(SourceRejected):
        await fetcher.fetch_complete("https://new.example/document")
