# Future narrative API requirements — not implemented

The current provider is local. These proposed routes are not working endpoints. Existing FastAPI graph/node routes remain unchanged.

| Proposed read contract | Required response |
| --- | --- |
| `GET /api/universes/{slug}/journeys?continuity_id=…` | Journey summaries, stable IDs, scope, ordering basis, revision and step count |
| `GET /api/journeys/{id}/steps` | Explicitly ordered JourneyStep records with graph UUID references, evidence and PresentationHint |
| `GET /api/universes/{slug}/lore-threads?continuity_id=…` | LoreThread definitions, concept references, initial discovery and discovery IDs |
| `GET /api/discoveries/{id}` | Explanation, established/interpretation/unresolved classification, citations, graph refs and related discovery IDs |
| `GET /api/media?node_id=…` | Licensed asset URL, alt text, credit/license, focal point, interpretive/canonical designation and fallback metadata |
| `GET /api/universes/{slug}/graph?continuity_id=…&spoiler_scope=…` | Server-filtered graph consistent with the allowed scope |

An API-backed `NarrativeDataProvider` should assemble the same `NarrativeCatalog` from `apps/web/src/features/narrative/contracts.ts`. Components and navigation actions must not change. The provider owns HTTP errors, cancellation and response decoding; the resolver still rejects unresolved graph references. TypeScript interfaces alone are not runtime validation for untrusted JSON.

Every resource needs universe/continuity, spoiler scope, content revision, schema version, evidence locators and editorial review status. Graph and narrative responses need compatible revisions to prevent stale references. Cache keys include scope and revision. Use explicit empty/unavailable results, never substitute story events.

Ordering requires an explicit basis and evidence. The initial vocabulary supports broadcast presentation; publication or in-world chronology needs deliberate contract changes. Repeated attempts remain distinct and adaptations never merge implicitly. A CONNECTED_TO edge proves connectivity, not chronology.

Discovery classifications apply within a scope. Interpretations need attribution; mysteries remain unresolved there even if later material answers them. Related links and graph retrieval must enforce spoilers on the server before sending content. Shared continuity-null knowledge does not merge adaptations.

Use stable resource IDs, UUID graph IDs, deterministic ordering, provenance, pagination and explicit 404/422/503 errors. Version references and define behavior when evidence is removed. User progress persistence, auth and writes need separate design. Media metadata must never supply graph entities or relationships. Research and SSE remain outside this contract.
