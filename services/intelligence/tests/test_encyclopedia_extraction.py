"""Owned synthetic encyclopedia evidence. No live model calls."""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from src.application.encyclopedia_extraction import EncyclopediaClaims, extract_encyclopedia
from src.application.research_contracts import CandidateEntity
from src.domain.research import SourcePassage, digest
from src.domain.value_objects import NodeType


async def test_indexed_encyclopedia_uses_exact_stored_sentence_and_typed_document_metadata():
    text = "The Glass Journal records the observatory's measurements. Its author is unknown."
    passage = SourcePassage(uuid4(), uuid4(), 0, 0, len(text), text, digest(text))

    async def infer(prompt, schema):
        return EncyclopediaClaims.model_validate(
            {
                "entities": [
                    {
                        "name": "Glass Journal",
                        "type": "OBJECT",
                        "description": "The Glass Journal records the observatory's measurements.",
                        "knowledge": {"category": "book", "section": "contents"},
                        "sentence_ids": [0],
                    }
                ]
            }
        )

    result = await extract_encyclopedia(
        [passage], "Research this named fictional document", infer, [NodeType.OBJECT]
    )
    entity = result.entities[0]
    assert entity.evidence[0].passage_id == passage.id
    assert entity.evidence[0].quote == text.split(". ")[0] + "."
    assert entity.knowledge.category == "book"
    assert not result.relationships


async def test_unknown_indexes_names_and_unrequested_types_are_not_materialized():
    text = "The Glass Journal records the observatory's measurements."
    passage = SourcePassage(uuid4(), uuid4(), 0, 0, len(text), text, digest(text))

    async def infer(prompt, schema):
        return EncyclopediaClaims.model_validate(
            {
                "entities": [
                    {
                        "name": "Glass Journal",
                        "type": "OBJECT",
                        "description": text,
                        "sentence_ids": [99],
                    },
                    {
                        "name": "Invented journal",
                        "type": "OBJECT",
                        "description": text,
                        "sentence_ids": [0],
                    },
                ]
            }
        )

    assert not (
        await extract_encyclopedia([passage], "Research the document", infer, [NodeType.OBJECT])
    ).entities


def test_category_mismatch_fails_inside_the_provider_schema():
    invalid = {
        "name": "Owned document",
        "type": "EVENT",
        "description": "Owned document content.",
        "knowledge": {"category": "book"},
        "sentence_ids": [0],
    }
    with pytest.raises(ValidationError):
        EncyclopediaClaims.model_validate({"entities": [invalid]})
    with pytest.raises(ValidationError):
        CandidateEntity.model_validate(
            {
                **{k: v for k, v in invalid.items() if k != "sentence_ids"},
                "evidence": [{"passage_id": str(uuid4()), "quote": "Owned document content."}],
            }
        )
