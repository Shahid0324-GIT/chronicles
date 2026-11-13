"""Source-grounded name forms and event identity, using owned fake-model fixtures."""

from uuid import uuid4

import pytest

from src.application.identity import IdentityResolver
from src.application.knowledge_contracts import EventIdentityComparison, IdentityComparison
from src.domain.entities import now
from src.domain.research import SourceDocument, digest, passages_for


@pytest.mark.parametrize(
    "name,text,others,expected",
    [
        ("Natsuki Subaru", "Natsuki Subaru arrived in the owned synthetic scene.", [], True),
        (
            "Subaru",
            "Natsuki Subaru arrived. Subaru participated in the owned synthetic arrival.",
            [],
            True,
        ),
        (
            "Vale",
            "Mira Vale arrived. Vale participated in the owned synthetic arrival.",
            ["Ren Vale"],
            False,
        ),
    ],
)
async def test_name_order_and_short_forms_need_context_and_unique_scoped_identity(
    name, text, others, expected
):
    scope, universe, target = uuid4(), uuid4(), uuid4()
    canonical = "Mira Vale" if name == "Vale" else "Subaru Natsuki"
    document = SourceDocument(
        uuid4(),
        universe,
        scope,
        "local:owned",
        "Owned",
        "Owned",
        text,
        digest(text),
        now(),
        "Owned test permission",
        "Owned continuity",
        False,
        False,
    )
    passage = passages_for(document)[0]
    evidence = [{"passage_id": str(passage.id), "quote": text}]
    candidate = {
        "id": str(uuid4()),
        "payload": {"name": name, "type": "CHARACTER", "description": text, "evidence": evidence},
    }
    catalog = [
        {
            "id": str(target),
            "name": canonical,
            "type": "CHARACTER",
            "aliases": [],
            "description": "Owned synthetic identity",
        }
    ]
    catalog.extend(
        {
            "id": str(uuid4()),
            "name": other,
            "type": "CHARACTER",
            "aliases": [],
            "description": "Separate owned synthetic identity",
        }
        for other in others
    )

    async def compare(prompt, schema):
        return IdentityComparison(
            decision="SAME_ENTITY",
            target_id=target,
            entity_type_valid=True,
            reason="Owned structured semantic comparison.",
            evidence=evidence,
        )

    resolution = await IdentityResolver().resolve(candidate, catalog, [passage], compare, scope)
    assert resolution["accepted"] == expected


@pytest.mark.parametrize(
    "granularity,actor_matches,expected",
    [(True, True, True), (False, True, False), (True, False, False)],
)
async def test_event_match_needs_precise_occurrence_and_existing_participant_context(
    granularity, actor_matches, expected
):
    universe, scope, actor, target = uuid4(), uuid4(), uuid4(), uuid4()
    text = "Mira Vale entered the observatory during this owned synthetic occurrence."
    source = SourceDocument(
        uuid4(),
        universe,
        scope,
        "local:owned",
        "Owned",
        "Owned",
        text,
        digest(text),
        now(),
        "Owned test permission",
        "Owned continuity",
        False,
        False,
    )
    p = passages_for(source)[0]
    evidence = [{"passage_id": str(p.id), "quote": text}]
    candidate = {
        "id": str(uuid4()),
        "payload": {
            "name": "entered",
            "type": "EVENT",
            "description": text,
            "evidence": evidence,
            "event": {
                "participants": ["Mira Vale"],
                "trigger": "entered",
                "identity_anchor": digest(f"{source.id}:{text.find('entered')}:entered"),
            },
        },
    }
    catalog = [
        {
            "id": str(target),
            "name": "Arrival",
            "type": "EVENT",
            "description": text,
            "aliases": [],
            "relationships": [
                {"source": str(actor), "target": str(target), "type": "PARTICIPATED_IN"}
            ],
        },
        {
            "id": str(actor),
            "name": "Mira Vale",
            "type": "CHARACTER",
            "description": "Owned character",
            "aliases": [],
        },
    ]

    async def compare(prompt, schema):
        return EventIdentityComparison(
            decision="SAME_ENTITY",
            target_index=0,
            entity_type_valid=True,
            reason="Owned precise occurrence comparison.",
            evidence_indices=[0],
            same_occurrence=True,
            same_granularity=granularity,
            repeated_occurrence_excluded=True,
        )

    resolution = await IdentityResolver().resolve(
        candidate,
        catalog,
        [p],
        compare,
        scope,
        indexed_evidence=True,
        participant_ids=[str(actor if actor_matches else uuid4())],
    )
    assert resolution["accepted"] == expected
