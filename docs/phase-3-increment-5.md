# Phase 3, Increment 5 — connected knowledge presentations

Implemented November 13–14, 2026. See [executed verification and limits](phase-3-increment-5-verification.md), [actual persisted results](phase-3-increment-5-demo.json), and [changed files](phase-3-increment-5-files.txt). The engine works end to end; the current local research remains a partial story guide, not a complete encyclopedia or polished full recap.

## Three layers

1. Canonical graph and archived evidence retain identity, scope, accepted assertions, original names, passages and retraction history. Presentations never replace this layer.
2. `StoryStructureOrganizer` deterministically groups the same anchored action and resolved participant context. Different occurrences, routes, attempts and uncertain order remain distinct. `KnowledgeAtlas` selects eligible facts and explicit relationships for the requested continuity and source boundary.
3. `RecapComposer` writes English presentations referencing supplied fact IDs and established names. Deterministic checks and a targeted entailment assessment can withhold the result. Model assessment is not independent verification. `EncyclopediaEntryBuilder` exposes supported sections through one reusable contract. Arc overviews assemble already grounded milestone sentences; they do not introduce a new free-form rewrite.

## Categories and connections

Typed metadata describes characters, places, organizations, objects, artifacts, documents, books, letters, inscriptions, lore, powers, history, worldbuilding, events, story structures and mysteries within the existing eight graph types. Unsupported sections are omitted. Epistemic classification is separate from operational verification: sourced hypotheses and interpretations remain separately labelled and cannot be promoted as established facts.

Character history uses eligible facts and accepted event relationships. `PARTICIPATED_IN` is checked against actual event roles and endpoints; merely mentioning someone does not establish participation. Causes and consequences require explicit accepted `CAUSED` edges. Source position supplies a supporting boundary, not chronology or a guaranteed first reveal. No additional causal facts were invented for this demonstration.

Encyclopedia extraction asks for indexed sentence references. The backend copies exact archived text and passage IDs instead of trusting model-authored quote punctuation or UUIDs. Publication still runs the existing transactional scope, evidence, identity, contradiction and independent-source checks.

## Persistence and generation

Self-contained migration `30c500000005` follows `2694c0a70004` and adds `knowledge_presentations`, its composite scope foreign key and indexes, with downgrade. Canonical tables and existing records are preserved. Artifacts record resource ID, evidence revision, language, policy, status, provider provenance and timestamp. Current presentation policy is `grounded-english-v8`; deterministic arc assembly adds `arc-assembly-v4`.

Cache identity includes exact eligible facts and policy. Arc identity additionally includes its current child presentations. A cached milestone can supply the corresponding event entry without another model call. The service rechecks source dependencies before saving. Repositories never commit, and no archive transaction spans network or model calls.

GET requests never invoke inference. Explicit rebuild jobs use the existing independent worker, persisted budget reservations, deadlines, cancellation and local model lease. The router has presentation and presentation-verification stages. Malformed output is bounded and may withhold one resource while allowing others to proceed; provider failures remain distinct. No future-agent stubs were introduced.

## API and existing reader

Universe API extensions include `encyclopedia`, `entries/{id}`, `connections`, `story-arcs`, `journeys/{id}`, `lore`, `mysteries` and `interpretations`. English is the supported display language; original names and citations remain available separately. `POST /api/universes/{slug}/presentations/rebuild` accepts continuity, optional episode boundary, resource IDs and explicit `retry_withheld`, and queues a presentation-only job without research.

The existing narrative provider and resolver consume the new optional overview and entry index. Existing panels show English profiles, history, aliases and citations. A small entry selector and source-boundary input provide navigation without replacing the canvas. Inspection preserves the journey bookmark. Bounded reads immediately clear stale content, prune graph/search/traversal, and never fall back to a broader curated catalog on failure. Generated regions use their own accepted edges. Responsive header, source-control and panel stacking retain keyboard access.

No image discovery, visual redesign, advanced choreography, SSE, cloud deployment or new infrastructure was added. See the verification report for actual model usage and remaining semantic gaps.
