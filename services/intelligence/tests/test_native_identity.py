"""Owned contextual references, not a table of real-character name mappings."""

from uuid import uuid4

from src.application.identity import IdentityResolver
from src.application.knowledge_contracts import ContextIdentityReview, IndexedIdentityComparison
from src.domain.identity_evidence import current_context_identity, sourced_identity_catalog
from src.domain.research import SourcePassage, digest


async def resolve_context(text, review):
    continuity, target = uuid4(), str(uuid4())
    passage = SourcePassage(uuid4(), uuid4(), 0, 0, len(text), text, digest(text))
    payload = {
        "name": "Roofi",
        "type": "CHARACTER",
        "description": "Roofi greeted the crew.",
        "evidence": [{"passage_id": str(passage.id), "quote": text}],
    }
    calls = []

    async def infer(prompt, schema):
        calls.append(schema)
        if schema is IndexedIdentityComparison:
            return schema(
                decision="SAME_ENTITY",
                target_index=0,
                entity_type_valid=True,
                reason="Proposed source-context reference",
                evidence_indices=[0],
                hidden_identity=False,
            )
        assert schema is ContextIdentityReview
        return schema(
            decision=review,
            evidence_indices=[0],
            alternative_status="distinguished" if review == "same" else "unresolved",
            hidden_identity=False,
            reason="Context supports the reference"
            if review == "same"
            else "No unique identifying context",
        )

    catalog = [
        {
            "id": target,
            "name": "Mira",
            "type": "CHARACTER",
            "aliases": [],
            "description": "Captain of the northern crew",
        }
    ]
    result = await IdentityResolver().resolve(
        {"id": str(uuid4()), "payload": payload},
        catalog,
        [passage],
        infer,
        continuity,
        indexed_evidence=True,
    )
    return result, payload, target, continuity, calls, catalog


async def test_contextual_reference_without_spelling_similarity_uses_native_review():
    text = "The northern captain arrived. Roofi greeted the crew she commanded."
    result, payload, target, continuity, calls, catalog = await resolve_context(text, "same")
    assert calls == [IndexedIdentityComparison, ContextIdentityReview]
    assert result["accepted"] and result["proof"] == "source_context_identity"
    assert current_context_identity(
        result, payload, target, "Mira", str(continuity), [text], catalog
    )
    assert not current_context_identity(
        result, payload, target, "Another captain", str(continuity), [text], catalog
    )
    assert not current_context_identity(
        result, payload, target, "Mira", str(continuity), ["Different evidence"], catalog
    )
    assert not current_context_identity(
        result, payload, target, "Mira", str(uuid4()), [text], catalog
    )
    changed = [{**catalog[0], "description": "A different identity context"}]
    assert not current_context_identity(
        result, payload, target, "Mira", str(continuity), [text], changed
    )
    changed = [{**catalog[0], "aliases": ["A newly assigned nickname"]}]
    assert not current_context_identity(
        result, payload, target, "Mira", str(continuity), [text], changed
    )


async def test_a_model_proposal_does_not_resolve_an_ambiguous_nickname():
    result, _, _, _, calls, _ = await resolve_context(
        "Roofi greeted a crew at the harbour.", "ambiguous"
    )
    assert len(calls) == 2
    assert not result["accepted"] and result["decision"] == "AMBIGUOUS"


async def test_none_supplied_review_cannot_ignore_an_actual_alternative():
    text = "The northern captain arrived. Roofi greeted her crew."
    result, payload, target, continuity, _, catalog = await resolve_context(text, "same")
    result["native_identity"]["review"]["alternative_status"] = "none_supplied"
    result["native_identity"]["alternative_count"] = 0
    assert current_context_identity(
        result, payload, target, "Mira", str(continuity), [text], catalog
    )
    alternative = {**catalog[0], "id": str(uuid4()), "name": "Another captain"}
    assert not current_context_identity(
        result, payload, target, "Mira", str(continuity), [text], [*catalog, alternative]
    )


async def test_canonical_identity_context_requires_current_scoped_nonsensitive_support():
    text = "Mira is the northern captain. Roofi greeted the crew she commanded."
    result, payload, target, continuity, _, catalog = await resolve_context(text, "same")
    universe = str(uuid4())
    citation = payload["evidence"][0]
    record = {
        "id": str(uuid4()),
        "kind": "entity",
        "target_id": target,
        "universe_id": universe,
        "continuity_id": str(continuity),
        "reversed": False,
        "data": {"snapshot": {"name": "Mira"}, "resolution": {}, "evidence": [citation]},
    }
    contextual = sourced_identity_catalog(catalog, [record], [citation], universe, str(continuity))
    support = contextual[0]["source_identity_context"]
    assert support and support[0]["canonical_source_name"] == "Mira"
    result["native_identity"]["canonical_support_keys"] = [support[0]["support_key"]]
    assert current_context_identity(
        result, payload, target, "Mira", str(continuity), [text], contextual
    )
    record["reversed"] = True
    withdrawn = sourced_identity_catalog(catalog, [record], [citation], universe, str(continuity))
    assert not current_context_identity(
        result, payload, target, "Mira", str(continuity), [text], withdrawn
    )
    record["reversed"] = False
    record["data"]["resolution"]["hidden_identity"] = True
    assert not sourced_identity_catalog(catalog, [record], [citation], universe, str(continuity))[
        0
    ]["source_identity_context"]
    record["data"]["resolution"] = {}
    assert not sourced_identity_catalog(
        catalog, [record], [citation], str(uuid4()), str(continuity)
    )[0]["source_identity_context"]
    source = str(uuid4())
    record["data"]["evidence"][0].update(source_id=source, content_hash="original-revision")
    assert sourced_identity_catalog(
        catalog, [record], [citation], universe, str(continuity), {source: "original-revision"}
    )[0]["source_identity_context"]
    assert not sourced_identity_catalog(
        catalog, [record], [citation], universe, str(continuity), {source: "changed-revision"}
    )[0]["source_identity_context"]


async def test_source_only_identity_prompt_excludes_editable_titles_notes_and_aliases():
    import json

    continuity, target = uuid4(), str(uuid4())
    text = "Mira led the crew. The crew called her Roofi. Roofi greeted them."
    passage = SourcePassage(uuid4(), uuid4(), 0, 0, len(text), text, digest(text))
    context = {"canonical_source_name": "Mira", "quote": text, "support_key": "owned-support"}
    catalog = [
        {
            "id": target,
            "name": "PRIVATE_TITLE",
            "type": "CHARACTER",
            "description": "PRIVATE_NOTE",
            "aliases": ["Mira", "PRIVATE_ALIAS"],
            "source_identity_context": [context],
        }
    ]
    # Unattributed records must not exhaust the bounded source-only comparison window.
    catalog.extend(
        dict(
            id=f"00000000-0000-0000-0000-{i:012d}",
            name=f"Unrelated {i}",
            type="CHARACTER",
            aliases=[],
            description="Private unrelated record",
        )
        for i in range(1, 10)
    )
    prompts = []

    async def infer(prompt, schema):
        prompts.append(prompt)
        assert not any(
            s in prompt for s in ["PRIVATE_TITLE", "PRIVATE_NOTE", "PRIVATE_ALIAS", target]
        )
        if schema is IndexedIdentityComparison:
            return schema(
                decision="SAME_ENTITY",
                target_index=0,
                entity_type_valid=True,
                reason="Owned public reference",
                evidence_indices=[0],
                hidden_identity=False,
            )
        return schema(
            reason="Owned source links the nickname",
            decision="same",
            evidence_indices=[0],
            alternative_status="distinguished",
            hidden_identity=False,
        )

    payload = {
        "name": "Roofi",
        "type": "CHARACTER",
        "description": "PRIVATE_CLAIM_NOTE",
        "evidence": [{"passage_id": str(passage.id), "quote": text}],
    }
    result = await IdentityResolver().resolve(
        {"id": str(uuid4()), "payload": payload},
        catalog,
        [passage],
        infer,
        continuity,
        indexed_evidence=True,
        source_only=True,
    )
    assert result["accepted"] and result["canonical_id"] == target
    assert "PRIVATE_CLAIM_NOTE" not in json.dumps(prompts)
    assert current_context_identity(
        result, payload, target, "PRIVATE_TITLE", str(continuity), [text], catalog
    )
