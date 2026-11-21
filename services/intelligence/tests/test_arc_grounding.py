"""Owned supported/adversarial examples; injected reviews are not live research."""

import pytest

from src.application.arc_contracts import (
    ArcSectionDraft,
    ArcSemanticReview,
    ArcUnderstanding,
    DevelopmentOmission,
)
from src.application.arc_grounding import (
    CALIBRATION,
    ground_understanding,
    qualify_reviewer,
    review_ok,
    validate_claims,
)


def fact(identifier, text, name="Mira"):
    return {"id": identifier, "payload": {"type": "CHARACTER", "name": name, "description": text}}


def draft(text, refs):
    return ArcSectionDraft(
        heading="Arrival at the observatory",
        paragraphs=[{"text": text, "fact_ids": refs, "claims": [{"text": text, "fact_ids": refs}]}],
    )


def test_capitalized_common_words_and_explicit_unary_time_are_not_new_entities_or_edges():
    facts = [fact("a", "After lunch, Mira entered the observatory.")]
    validate_claims(draft("After lunch, Mira entered the observatory.", ["a"]), facts, facts)
    validate_claims(draft("Mira entered the observatory.", ["a"]), facts, facts)


def test_explicit_causal_assertion_does_not_require_an_additional_event_edge():
    facts = [fact("a", "Mira stayed because the gate was locked.")]
    validate_claims(draft("Mira stayed because the gate was locked.", ["a"]), facts, facts)


def test_unknown_claim_references_and_mismatched_paragraph_citations_are_rejected():
    facts = [fact("a", "Mira entered the observatory.")]
    with pytest.raises(ValueError, match="Unlicensed"):
        validate_claims(draft("Mira entered the observatory.", ["unknown"]), facts, facts)
    with pytest.raises(ValueError, match="Paragraph citations"):
        ArcSectionDraft(
            heading="Arrival at the observatory",
            paragraphs=[
                dict(
                    fact_ids=["another"],
                    claims=[dict(text="Mira entered the observatory.", fact_ids=["a"])],
                )
            ],
        )


def test_paragraph_text_and_citations_are_derived_from_individually_grounded_claims():
    result = ArcSectionDraft(
        heading="Arrival at the observatory",
        paragraphs=[
            dict(
                claims=[
                    dict(text="Mira entered the observatory.", fact_ids=["a"]),
                    dict(text="Mira stayed inside.", fact_ids=["b", "a"]),
                ]
            )
        ],
    )
    paragraph = result.paragraphs[0]
    assert paragraph.fact_ids == ["a", "b"]
    assert paragraph.text == "Mira entered the observatory. Mira stayed inside."
    paragraph.claims[0].fact_ids = ["c"]
    assert paragraph.fact_ids == ["c", "b", "a"]
    schema = ArcSectionDraft.model_json_schema()
    assert "fact_ids" not in schema["$defs"]["ArcParagraph"]["properties"]


async def test_reviewer_that_blindly_approves_adversarial_claims_cannot_qualify():
    async def approve(prompt, schema, task):
        return ArcSemanticReview(
            claims=[
                {"index": i, "verdict": "supported", "reason": "Blind approval"} for i in range(6)
            ],
            paragraphs_faithful=True,
            coherent=True,
        )

    passed, _ = await qualify_reviewer(approve)
    assert not passed


async def test_qualification_rejects_a_missing_adversarial_verdict_hidden_by_duplicate():
    async def incomplete(prompt, schema, task):
        claims = [
            dict(
                index=i,
                verdict="supported" if c["expected"] else "unsupported",
                reason="Owned case",
            )
            for i, c in enumerate(CALIBRATION)
        ]
        claims[-1] = dict(claims[2])
        return ArcSemanticReview(claims=claims, paragraphs_faithful=True, coherent=True)

    passed, _ = await qualify_reviewer(incomplete)
    assert not passed


def test_missing_or_duplicate_semantic_verdicts_do_not_validate_prose():
    review = ArcSemanticReview(
        claims=[{"index": 0, "verdict": "supported", "reason": "Exact assertion"}],
        paragraphs_faithful=True,
        coherent=True,
    )
    assert review_ok(review, 1)
    assert not review_ok(review, 2)
    review.claims.append(review.claims[0])
    assert not review_ok(review, 2)


def test_organization_cannot_silently_drop_contextual_developments():
    facts = [
        fact("a", "Mira entered the observatory."),
        fact("b", "Ron unlocked the door for Mira."),
    ]
    understanding = ArcUnderstanding(
        bindings=[dict(section_key="entry", facet="action", fact_ids=["1"])]
    )
    with pytest.raises(ValueError, match="Every input assertion"):
        ground_understanding(understanding, facts, {"entry"})
    understanding.omissions = [
        DevelopmentOmission(
            fact_ids=["2"],
            reason="insufficient_context",
            explanation="Owned explicit missing context test",
        )
    ]
    ground_understanding(understanding, facts, {"entry"})
    assert understanding.omissions[0].fact_ids == ["b"]
