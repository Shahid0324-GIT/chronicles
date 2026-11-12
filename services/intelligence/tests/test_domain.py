from dataclasses import replace
from uuid import uuid4

import pytest

from src.domain.entities import Continuity, GraphNode, GraphRelationship, Universe
from src.domain.exceptions import DomainError
from src.domain.value_objects import NodeType, RelationshipType, Slug
from src.infrastructure.persistence.seed import sample_graph


def test_domain_construction():
    universe = Universe(slug=Slug("a-world"), title="A world", description="")
    assert universe.created_at.tzinfo is not None
    assert universe.id != Universe(slug=Slug("other"), title="Other", description="").id
    continuity = Continuity(universe_id=universe.id, name="Anime", medium="ANIME", description="")
    node = GraphNode(
        universe_id=universe.id,
        continuity_id=continuity.id,
        type=NodeType.CHARACTER,
        title="A",
        summary="",
    )
    assert node.metadata == {}


@pytest.mark.parametrize("value", ["", "Bad Slug", "two--words", "../world", "trailing-"])
def test_invalid_slug(value):
    with pytest.raises(DomainError):
        Slug(value)


def test_blank_title_and_unknown_types():
    with pytest.raises(DomainError):
        Universe(slug=Slug("world"), title=" ", description="")
    with pytest.raises(DomainError):
        GraphNode(universe_id=uuid4(), type="UNKNOWN", title="A", summary="")


def test_relationship_invariants():
    _, _, nodes, edges = sample_graph()
    edge = edges[0]
    source = next(n for n in nodes if n.id == edge.source_node_id)
    target = next(n for n in nodes if n.id == edge.target_node_id)
    edge.validate_endpoints(source, target)
    with pytest.raises(DomainError, match="same universe"):
        edge.validate_endpoints(source, replace(target, universe_id=uuid4()))
    with pytest.raises(DomainError, match="endpoints"):
        edge.validate_endpoints(target, source)
    with pytest.raises(DomainError, match="continuities"):
        edge.validate_endpoints(source, replace(target, continuity_id=uuid4()))
    with pytest.raises(DomainError, match="continuities"):
        replace(edge, continuity_id=None).validate_endpoints(source, target)
    edge.validate_endpoints(replace(source, continuity_id=None), target)
    replace(edge, continuity_id=None).validate_endpoints(
        replace(source, continuity_id=None), replace(target, continuity_id=None)
    )


def test_cycles_are_allowed():
    universe = uuid4()
    a = GraphNode(universe_id=universe, type=NodeType.LORE, title="A", summary="")
    b = GraphNode(universe_id=universe, type=NodeType.LORE, title="B", summary="")
    for source, target in [(a, b), (b, a)]:
        GraphRelationship(
            universe_id=universe,
            source_node_id=source.id,
            target_node_id=target.id,
            relationship_type=RelationshipType.CONNECTED_TO,
            description="Linked",
        ).validate_endpoints(source, target)
