import re
from dataclasses import dataclass
from enum import StrEnum

from src.domain.exceptions import DomainError


@dataclass(frozen=True)
class Slug:
    value: str

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", self.value):
            raise DomainError("Slug must contain lowercase words separated by hyphens")

    def __str__(self) -> str:
        return self.value


class NodeType(StrEnum):
    CHARACTER = "CHARACTER"
    EVENT = "EVENT"
    LOCATION = "LOCATION"
    LORE = "LORE"
    FACTION = "FACTION"
    OBJECT = "OBJECT"
    STORY_ARC = "STORY_ARC"
    MYSTERY = "MYSTERY"


class RelationshipType(StrEnum):
    PARTICIPATED_IN = "PARTICIPATED_IN"
    OCCURRED_AT = "OCCURRED_AT"
    CAUSED = "CAUSED"
    REVEALED = "REVEALED"
    BELONGS_TO = "BELONGS_TO"
    CONNECTED_TO = "CONNECTED_TO"
    FORESHADOWS = "FORESHADOWS"
    ALLIED_WITH = "ALLIED_WITH"
    CONTRADICTS = "CONTRADICTS"
    OPPOSED = "OPPOSED"
    MEMBER_OF = "MEMBER_OF"
    RELATED_TO = "RELATED_TO"
    PRECEDES = "PRECEDES"
    ENABLED = "ENABLED"
