# Increment 5.1 diagnosis and bounded research design

The Increment 5 audit contains 169 diagnostic/demo calls, 24 nodes and 31 edges, a sparse character profile, one power definition, withheld recaps and a concatenated partial guide. It does not demonstrate full subject coverage.

Pipeline findings:

- Discovery returned immediately when any registry entries existed, so initial episode sources crowded out later source categories.
- Default discovery queries explicitly favored episode guides and wiki domains. Query variants were not driven by persistent gaps.
- Registry permission, media and continuity gates were correct and are retained. Authority and accessibility must stay separate.
- Extraction explicitly excluded the broad `official` category but retained episode-guide sources. This removed useful profiles and original official account context.
- Retrieval had an eight-passage/six-thousand-character selection; event calls used four passages and three frames each. These are per-call capacity limits, not universe coverage. Unprocessed information needs later passes.
- Focused extraction and presentation also used small first-N selections. Richer evidence needs relevance/token selection rather than globally raising all limits.
- Cached documents, content hashes, embeddings and inference reuse already existed. Reuse alone did not supply coverage or durable research questions.
- Refinement required ordinary web search and unresolved publication candidates; registry research explicitly disabled refinement. Successful publication could end research despite large topic gaps.
- The current arc paragraph joins accepted sentences. This is safe against invention but does not satisfy cohesive synthesis.

Implementation direction: retain LangGraph, the archive, pgvector, canonical promotion and reader contracts. Add a configurable versioned focused effort policy, universe source profiles, independently persisted scoped leads, local-first evidence dossiers, diversified query expansion, auditable source ranking and coverage outcomes. Documents/queries/calls/bytes/tokens/time/depth remain resource ceilings, never definitions of success. New jobs can extend the archive and unfinished frontier; resuming a job does not reset its budget.

Source profiles describe authority and useful material; they grant no host, retrieval or cloud permission. Discovered references default to navigation-only. Adaptation facts stay in their own continuity. The frontend visual design and image discovery remain outside scope.
