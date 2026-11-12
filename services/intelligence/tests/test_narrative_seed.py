import re
from pathlib import Path

from src.domain.value_objects import NodeType
from src.infrastructure.persistence.seed import identity, sample_graph


def test_narrative_references_resolve_to_real_seed_graph_records():
    universe, continuity, nodes, edges = sample_graph()
    references = (
        Path(__file__).parents[3] / "apps/web/src/features/narrative/fixtures/re-zero-ids.ts"
    )
    referenced_ids = set(re.findall(r'"([a-f0-9-]{36})"', references.read_text(encoding="utf-8")))
    available_ids = {str(item.id) for item in [universe, continuity, *nodes, *edges]}
    assert referenced_ids and referenced_ids <= available_ids
    event_ids = {identity(key) for key in ["arrival", "search", "first-return", "recognition"]}
    assert event_ids <= {node.id for node in nodes if node.type == NodeType.EVENT}
    for edge in edges:
        lookup = {node.id: node for node in nodes}
        edge.validate_endpoints(lookup[edge.source_node_id], lookup[edge.target_node_id])
