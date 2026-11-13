"""Shared knowledge vocabulary, independent of model invocation contracts."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

KnowledgeCategory = Literal[
    "character",
    "place",
    "region",
    "nation",
    "organization",
    "faction",
    "civilization",
    "species",
    "object",
    "book",
    "document",
    "letter",
    "diary",
    "artifact",
    "weapon",
    "item",
    "inscription",
    "lore",
    "ability",
    "mythology",
    "religion",
    "culture",
    "event",
    "historical-event",
    "arc",
    "episode",
    "chapter",
    "quest",
    "sequence",
    "mystery",
    "subquest",
    "turning-point",
    "minor-event",
    "major-event",
    "alternate-route",
    "time-loop",
    "flashback",
    "historical-era",
    "race",
    "record",
    "newspaper",
    "prophecy",
    "hidden-lore",
    "foreshadowing",
]
EpistemicClass = Literal[
    "ESTABLISHED_CANON", "SUPPORTED_INTERPRETATION", "FAN_THEORY", "CONTRADICTED", "UNRESOLVED"
]


class KnowledgeMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")
    category: KnowledgeCategory
    section: Literal[
        "identity",
        "background",
        "origin",
        "affiliation",
        "ability",
        "history",
        "definition",
        "mechanics",
        "contents",
        "author",
        "appearance",
        "mystery",
    ] = "definition"
    classification: EpistemicClass = "ESTABLISHED_CANON"
    route_id: str | None = Field(default=None, max_length=100)
    attempt_id: str | None = Field(default=None, max_length=100)
