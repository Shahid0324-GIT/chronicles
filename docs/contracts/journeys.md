# Explicit journey ordering

Graph relationships, response-array order, discovery arrival and graph traversal are not chronological evidence.

The frontend supports this optional future convention in an EVENT node's existing metadata:

    {
      "journey": {
        "id": "a-stable-sequence-id",
        "title": "A sourced journey",
        "order": 0,
        "source": "https://example.org/an-authoritative-sequence",
        "order_verified": true
      }
    }

This is a producer contract example, not sample content or a claim that the example URL verifies a story. The Re:Zero seed has no journey metadata.

Validation requires one selected continuity, at least two EVENT nodes within it, unique nonnegative integer order values, consistent title/source, an HTTP(S) source reference, and an explicit verified-order flag. Every consecutive pair must also be connected by a relationship scoped to that continuity. Edges establish connectivity; sourced metadata establishes ordering. The first valid group by stable ID is used in this prototype.

If validation fails, Guided mode has an informative unavailable state, without artificial Previous/Next progression. Valid data initializes the first event, clamps Previous/Next at sequence boundaries, focuses the camera and updates the context panel. Arbitrary selection returns to Explore mode. Changing continuity reevaluates the sequence.

Before ingestion, replace the flag convention with a backend-owned sequence resource carrying evidence, spoiler scope, ordering basis (publication versus in-world order), revision and reviewer status. Add a sequence chooser when multiple journeys exist. Never fabricate ordering to demonstrate controls.
