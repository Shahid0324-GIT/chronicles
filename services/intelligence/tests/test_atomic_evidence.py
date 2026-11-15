"""Adversarial owned assertions: a supporting fake model cannot override argument binding."""

import pytest

from src.application.atomic_verification import (
    candidate_assessment,
    context_fingerprint,
    related_evidence,
)
from src.application.connected_extraction import compile_connected
from src.application.evidence_bundles import EvidenceBundleBuilder
from src.application.relationship_contracts import ConnectedAssertions
from src.domain.atomic_evidence import (
    atomic_payload_support,
    atomic_support,
    split_compound_assertion,
)

from .test_relationship_bundles import SUBJECTS, evidence


@pytest.mark.parametrize(
    "subject,predicate,target",
    [
        ("Ron", "helped", "Mira"),
        ("Mira", "is", "a giant"),
        ("Mira", "joined", "the guild"),
        ("Mira", "knew", "Ron's secret identity"),
        ("Mira", "caused", "Ron's victory"),
        ("Mira", "helped", "Ron because she knew his secret identity"),
    ],
)
def test_unsupported_direction_attributes_motives_identity_and_causality(
    subject, predicate, target
):
    atom = {"subject": subject, "predicate": predicate, "object": target}
    assert not atomic_support(
        atom, ["Mira helped Ron. Ron is a giant. The guild arrived."]
    ).supported


@pytest.mark.parametrize("status", ["intended", "hypothetical", "reported", "denied", "uncertain"])
def test_nonactual_actions_never_supply_actual_participation(status):
    assert not atomic_support(
        {"subject": "Mira", "predicate": "helped", "object": "Ron", "occurrence_status": status},
        ["Mira helped Ron."],
    ).supported


def test_compound_assertion_has_separately_rejectable_motive_and_causal_link():
    pieces = split_compound_assertion("Mira helped Ron because Mira knew Ron's secret identity.")
    assert len(pieces) == 3 and pieces[-1]["kind"] == "causality"
    assert pieces[0]["statement"] == "Mira helped Ron"
    assert atomic_support(
        {"subject": "Mira", "predicate": "helped", "object": "Ron"}, ["Mira helped Ron."]
    ).supported
    assert not atomic_support(
        {"subject": "Mira", "predicate": "knew", "object": "Ron's secret identity"},
        ["Mira helped Ron."],
    ).supported


def connected_fixture():
    hit = evidence(
        "Mira and Ron became partners. Mira and Taro started training for magic. "
        "Mira invented Ember Shield."
    )
    bundle = EvidenceBundleBuilder().build(
        [hit], SUBJECTS, "Mira and Ron", hit.source.continuity_id, None, 1000
    )[0]
    answer = ConnectedAssertions.model_validate(
        {
            "assertions": [
                {
                    "subject": "Mira",
                    "predicate": "became partners",
                    "object": "Ron",
                    "sentence_ids": [0],
                },
                {
                    "subject": "Mira",
                    "predicate": "started training for magic",
                    "object": "Taro",
                    "sentence_ids": [1],
                },
                {
                    "subject": "Mira",
                    "predicate": "invented",
                    "object": "Ember Shield",
                    "object_type": "LORE",
                    "sentence_ids": [2],
                },
            ]
        }
    )
    return hit, bundle, answer


def test_connected_compilation_retains_companion_lore_roles_and_exact_event_anchor():
    hit, bundle, answer = connected_fixture()
    extraction, hypotheses = compile_connected(bundle, answer)
    assert all(h["supported_literal_binding"] for h in hypotheses)
    assert {e.name for e in extraction.entities if e.type.value == "CHARACTER"} == {
        "Mira",
        "Ron",
        "Taro",
    }
    assert {e.name for e in extraction.entities if e.type.value == "LORE"} == {"Ember Shield"}
    events = [e for e in extraction.entities if e.type.value == "EVENT"]
    assert len(events) == 3 and len(extraction.relationships) == 8
    for event in events:
        assert (
            hit.passage.text[event.event["trigger_start"] : event.event["trigger_end"]]
            == event.event["trigger"]
        )
        assert event.event["occurrence_status"] == "actual"
    assert all(
        atomic_payload_support(r.model_dump(mode="json"), [c.quote for c in r.evidence]).supported
        for r in extraction.relationships
    )


def test_literal_joint_actions_survive_model_omission_and_pronoun_guess_is_rejected():
    _, bundle, answer = connected_fixture()
    incomplete = ConnectedAssertions(assertions=[answer.assertions[-1]])
    extraction, _ = compile_connected(bundle, incomplete)
    assert {e.name for e in extraction.entities if e.type.value == "CHARACTER"} == {
        "Mira",
        "Ron",
        "Taro",
    }
    assert len([e for e in extraction.entities if e.type.value == "EVENT"]) == 3
    assert not atomic_support(
        {"subject": "Mira", "predicate": "consulted", "object": "Ron"}, ["Mira consulted him."]
    ).supported


def test_malformed_binding_cannot_raise_or_become_canonical():
    assert not atomic_payload_support(
        {
            "name": "Mira",
            "type": "CHARACTER",
            "description": "Mira helped Ron",
            "atomic": {"subject": "Mira", "predicate": "helped", "object": "Ron"},
        },
        ["Mira helped Ron."],
    ).supported


def test_new_contradictory_context_invalidates_the_completed_assessment_identity():
    from dataclasses import replace

    _, bundle, answer = connected_fixture()
    extraction, _ = compile_connected(bundle, answer)
    atom = extraction.relationships[0].atomic
    contrary = replace(
        evidence("Mira and Ron did not become partners."),
        source=replace(evidence("Owned").source, continuity_id=bundle.continuity_id),
    )
    other = EvidenceBundleBuilder().build(
        [contrary], SUBJECTS, "Mira and Ron", bundle.continuity_id, None, 1000
    )[0]
    assert related_evidence(atom, [bundle, other]) == [other]
    assert context_fingerprint(atom, [bundle]) != context_fingerprint(atom, [bundle, other])


def test_supporting_fake_model_cannot_accept_reverse_direction_or_mention_participation():
    _, bundle, answer = connected_fixture()
    extraction, _ = compile_connected(bundle, answer)
    payload = extraction.relationships[0].model_dump(mode="json")
    verdict = dict.fromkeys(
        [
            "subject_supported",
            "predicate_supported",
            "object_supported",
            "direction_valid",
            "subject_type_valid",
            "object_type_valid",
            "actual_occurrence",
            "in_universe",
            "continuity_matches",
        ],
        True,
    )
    verdict["material_conflict"] = False
    assert (
        candidate_assessment(payload, verdict, [payload["evidence"][0]["quote"]])["decision"]
        == "supported"
    )
    payload["source_name"] = "Taro"
    assert (
        candidate_assessment(payload, verdict, [payload["evidence"][0]["quote"]])["decision"]
        == "insufficient"
    )
    payload = extraction.relationships[0].model_dump(mode="json")
    verdict["material_conflict"] = True
    assert (
        candidate_assessment(payload, verdict, [payload["evidence"][0]["quote"]])["decision"]
        == "insufficient"
    )
