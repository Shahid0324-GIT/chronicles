# Phase 3, Increment 5 — connected knowledge presentations

Implementation is in progress. Live quality verification and reader integration are not yet complete.

Canonical nodes, relationships and original evidence remain separate from reader presentations.
`KnowledgeAtlas` selects active, scoped publication assertions; `StoryStructureOrganizer` groups
identical anchored encounter contexts without inferring chronology. `EncyclopediaEntryBuilder`
uses one contract and omits unsupported sections. `RecapComposer` generates English text with
fact references, followed by deterministic checks and a targeted entailment assessment.
Model assessment is not independent verification. Unavailable translations use neutral English.

Migration `30c500000005` adds `knowledge_presentations`, a composite continuity/universe foreign
key and scope index. No canonical tables or existing records are replaced. Artifacts retain
resource ID, evidence revision, language, policy, validation status, provider usage and timestamp.
Exact relevant evidence determines cache identity; unchanged evidence can be reused across
spoiler boundaries. Page reads perform no inference. Explicit rebuild jobs use the independent
worker and its existing cancellation, deadline, budget and local model lease mechanisms.

Typed category metadata covers characters, places, organizations, objects, documents, lore,
story structures and mysteries using the existing eight graph types. Epistemic classifications
are separate from operational verification and noncanonical interpretations cannot be promoted
as established facts. Indexed encyclopedia extraction maps integer sentence references to exact
archive passages, preventing model-authored quotation punctuation and passage UUIDs.

Read APIs extend the existing universe routes with encyclopedia entries, scoped connections,
story guides, journeys, lore, mysteries and separately labelled sourced interpretations. English
is currently the only display language. Original names and quotation languages remain available.
`POST /api/universes/{slug}/presentations/rebuild` queues a rebuild without research. It accepts
continuity, optional episode boundary, optional resource IDs and an explicit withheld-output retry.

At the backend checkpoint, Ruff and mypy passed (76 source files); all 149 tests passed,
including the seven opt-in PostgreSQL tests using unique schemas in `universe_atlas_test`.
Those tests execute actual migration upgrade/downgrade. Local migration upgrade succeeded and
`alembic check` reported no new operations. Ordinary tests use owned fixtures/fake inference.

Live runs are diagnostic until the final verification report: initial 4B presentation generation
produced inconsistent names and untranslated text, demonstrating the limits of model-only
assessment. Subsequent policy adds source-backed name checks and conservative withholding.
Two lore attempts failed exact evidence validation and published no new lore. A genuine indexed
extraction and presentation run with the already installed local 7B model is under verification.
No cloud inference or changes to local credential files are authorized by these operations.
