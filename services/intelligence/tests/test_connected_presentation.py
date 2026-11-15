"""Owned reader facts: deterministic checks must override an overconfident fake verifier."""

from uuid import uuid4

from src.application.evidence_dossier import EvidenceDossierBuilder
from src.application.knowledge_presentation import RecapComposer


def resource(two_actions=False):
    identifier = str(uuid4())
    facts = [
        {
            "id": "role-fact",
            "kind": "entity",
            "target_id": identifier,
            "payload": {
                "name": "Mira",
                "type": "CHARACTER",
                "description": "Mira and Ron became captain and pilot.",
                "atomic": {
                    "id": "roles",
                    "subject": "Mira",
                    "object": "Ron",
                    "predicate": "became captain and pilot",
                },
            },
            "sources": [
                {
                    "id": "owned",
                    "quote": "Mira and Ron became captain and pilot.",
                    "provenance": {"category": "official"},
                }
            ],
        }
    ]
    if two_actions:
        facts.append(
            {
                "id": "invention-fact",
                "kind": "entity",
                "target_id": identifier,
                "payload": {
                    "name": "Mira",
                    "type": "CHARACTER",
                    "description": "Mira invented Dawn Shield.",
                    "atomic": {
                        "id": "invention",
                        "subject": "Mira",
                        "object": "Dawn Shield",
                        "predicate": "invented",
                    },
                },
                "sources": [
                    {
                        "id": "owned",
                        "quote": "Mira invented Dawn Shield.",
                        "provenance": {"category": "official"},
                    }
                ],
            }
        )
    return {
        "id": identifier,
        "kind": "entry",
        "graph_type": "CHARACTER",
        "facts": facts,
        "names": [{"id": identifier, "english": "Mira", "aliases": ["Mira"]}],
    }


async def test_one_character_cannot_silently_receive_both_joint_roles():
    calls = []

    async def infer(prompt, schema, task):
        calls.append(task)
        assert task == "presentation"  # A model verifier never gets to override this guard.
        return schema.model_validate(
            {
                "display_title": "Mira",
                "short_summary": "Mira became captain and pilot alongside Ron.",
                "statements": [
                    {"text": "Mira became captain and pilot alongside Ron.", "fact_ids": ["1"]}
                ],
            }
        )

    _, status = await RecapComposer().compose(resource(), infer)
    assert status == "withheld_joint_role_binding"
    assert len(calls) == 2  # One targeted repair, no unbounded loop.


async def test_ambiguous_summary_reuses_grounded_statement_and_is_verified_again():
    calls = []

    async def infer(prompt, schema, task):
        calls.append(task)
        if task == "presentation_verification":
            assert "Mira became captain and pilot alongside Ron" not in prompt
            return schema.model_validate(
                {
                    "entailed": True,
                    "english": True,
                    "names_consistent": True,
                    "agency_and_tense_preserved": True,
                    "unsupported_relationships": False,
                    "reason": "Owned complete draft is grounded.",
                }
            )
        return schema.model_validate(
            {
                "display_title": "Mira",
                "short_summary": "Mira became captain and pilot alongside Ron.",
                "statements": [
                    {"text": "Mira and Ron became captain and pilot.", "fact_ids": ["1"]}
                ],
            }
        )

    draft, status = await RecapComposer().compose(resource(), infer)
    assert status == "validated"
    assert draft["short_summary"] == "Mira and Ron became captain and pilot."
    assert calls == ["presentation", "presentation_verification"]


async def test_connected_explanation_cannot_omit_an_accepted_action():
    calls = []

    async def infer(prompt, schema, task):
        calls.append(task)
        assert task == "presentation"
        return schema.model_validate(
            {
                "display_title": "Mira",
                "short_summary": "Mira and Ron became captain and pilot.",
                "statements": [
                    {"text": "Mira and Ron became captain and pilot.", "fact_ids": ["1"]}
                ],
            }
        )

    _, status = await RecapComposer().compose(resource(True), infer)
    assert status == "withheld_connected_coverage" and len(calls) == 2


def test_archive_navigation_does_not_consume_the_inference_dossier_allowance():
    facts = resource(True)["facts"]
    for fact in facts:
        source = fact["sources"][0]
        source.update(
            content_hash="unchanged-revision",
            passage_id="owned-passage",
            quote_start=7,
            quote_end=48,
        )
        source["provenance"].update(links_json="x" * 30000, sections_json="x" * 30000)
    dossier = EvidenceDossierBuilder().select(facts, "Mira relationships", 1500)
    assert len(dossier["facts"]) == 2
    source = dossier["facts"][0]["sources"][0]
    assert source["content_hash"] == "unchanged-revision" and source["quote_start"] == 7
    assert "links_json" not in source["provenance"]
    assert len(facts[0]["sources"][0]["provenance"]["links_json"]) == 30000
