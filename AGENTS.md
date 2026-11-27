# Universe Atlas repository guidance

## Current direction (2026-11-27)

Chronicles is a budget-constrained story atlas built on free and local models. A user names a world and one arc; agents find and fetch sources from user-approved sites, read them, and draft a story pack the user reviews. It must work for any story, with no story-specific code. Existing research, canonical-promotion and arc pipelines below are legacy: do not extend them, and remove them only after the new path is proven and a caller audit is approved.

- Model chain: Groq (`GROQ_API_KEY_1`), then Gemini (`GEMINI_API_KEY_1`), then local Ollama. One key per provider. Never rotate keys or accounts to get past a limit.
- Fetch only from sites the user approved for that world; respect robots rules and terms, keep source links and licence notes, and send text to a cloud model only when that site is allowed for it.
- Story sources, caches and images live in git-ignored folders; never commit third-party text or art.
- Every drafted item cites a saved source. Drafts are never presented as verified.

## Git workflow preference

The user has authorized small commits at meaningful checkpoints and explicitly requires pushing whenever a commit is created. Follow this standing instruction without asking again. Use `main` for completed milestones and report the commit and push result. Run relevant checks and keep credentials/local environment files out of commits.

Implement only the scope requested. Phase 1 provides a read-only local graph; Phase 2 provides the continuous frontend atlas. Neither implements AI research. Never present curated seed content as discovered or verified by an agent. Do not deploy or push without explicit user instructions.

## Layout and dependency direction

- Python package: `services/intelligence/src`; run backend commands from `services/intelligence`.
- Domain imports only the Python standard library and other domain modules.
- Application depends on domain and repository Protocols in `application/ports`.
- Infrastructure implements ports structurally and maps ORM rows to domain entities.
- Presentation composes concrete repositories with FastAPI Depends and converts application results to dedicated API schemas.
- Next.js lives in `apps/web`. Server-only API client is `src/lib/api.ts`; transport types are `src/lib/contracts.ts`; graph implementation is in `src/features/graph/`, with `src/components/Atlas.tsx` retained as a compatibility export.

Use constructor injection, explicit meaningful Protocols, composition, Python type hints and strict TypeScript. Do not introduce BaseService/BaseAgent, generic repository frameworks, microservices, external auth, cloud storage, or unused future dependencies.

## Graph semantics

Universes are graphs, never trees. IDs are UUIDs. Slugs are lowercase hyphenated value objects. `None` continuity means explicitly shared knowledge; it is not a license to merge adaptations. Before persisting a relationship, call `validate_endpoints` with the actual nodes. Two scoped endpoints must share a continuity, and a scoped endpoint requires its edge to use that continuity. Cross-universe relationships are prohibited and defended by composite database foreign keys. New write use cases must validate these rules within their transaction.

Enums are application vocabulary stored as strings, not native PostgreSQL enums. Add enum members deliberately in domain and transport contracts; handle unknown historical values explicitly in any future import pipeline. Never silently coerce an unknown type to a different meaning.

## Persistence

Use SQLAlchemy async APIs; one session and transaction per request, closed through a yield dependency. Repositories never commit. Do not share an AsyncSession between concurrent tasks. Caller owns seed transactions. Backend Alembic migrations are the only runtime schema mechanism; do not call `create_all` at startup. Migration files must remain self-contained and never import mutable current ORM metadata. Add indexes and downgrade behavior for schema changes.

Seed IDs are deterministic, illustrative, and limited to early Re:Zero anime content. Preserve existing data and user edits. Run seeds serially. Never erase or reset developer volumes to fix a routine configuration issue.

## Checks

Backend (from `services/intelligence`, using root `.venv`):

```powershell
..\..\.venv\Scripts\python -m ruff check .
..\..\.venv\Scripts\python -m ruff format --check .
..\..\.venv\Scripts\python -m mypy -p src
..\..\.venv\Scripts\python -m pytest -q
```

Frontend (from root): `npm run lint --prefix apps/web`, `npm run typecheck --prefix apps/web`, `npm run build --prefix apps/web`.

Default tests use in-memory SQLite or fake repositories. PostgreSQL tests require an explicit `TEST_DATABASE_URL` ending in `_test` and a unique schema; never fall back to `DATABASE_URL`. Verify actual migration upgrade/downgrade and `alembic check` when touching persistence. Backend dependency resolution is recorded in `requirements-dev.lock`; npm versions are locked in `package-lock.json`. Update locks intentionally after meaningful checks.

Keep credentials out of Git. Local `.env` files are ignored; update examples when settings change. Maintain loading, error, empty, not-found, keyboard and responsive states. Do not embed sample data in React. The exploration store is per-experience Zustand state. Keep per-frame updates out of the full React tree.

Report exact checks, failures and blockers. Consult `docs/verification.md` for the last implementation verification; rerun only relevant checks for subsequent changes.

## Phase 2 frontend

Keep exploration on the same canvas; entities and universes use state changes. Dynamically import Sigma with SSR disabled. Preserve deterministic type clusters and backend IDs. GSAP owns interruptible camera/presentation tweens; Sigma owns graph rendering. Clean up subscriptions, listeners, WebGL resources and tweens. Respect reduced motion. Follow docs/contracts/journeys.md; never infer chronology from traversal. Media registry entries are presentation assets, never graph data. No fake SSE or AI producer.

Run npm run test --prefix apps/web for graph/state/ordering tests. npm run test:e2e --prefix apps/web uses real seeded services and installed Chrome, without database resets. See docs/phase-2-atlas.md.

## Phase 2.5A narrative

Narrative contracts, fixtures, resolver and injectable provider live in `apps/web/src/features/narrative/`; history/progress live in `src/stores/narrative-state.ts`. Keep canonical entities in the API graph. Use sourced broadcast presentation order, never inferred chronology. Layout strategies belong in `features/graph/layout-strategies.ts`; focus changes must not rearrange nodes. Preserve journey position across inspection and lore branches. See docs/phase-2-5a-narrative.md and docs/contracts/narrative-api.md; proposed narrative endpoints are not implemented.

## Phase 2.5B Pass 1

The default is the dedicated horizontal illustrated canvas in `features/chronicle/`, not a timeline above Sigma. Sigma remains the Free graph view. Theme/motion/spine settings live in `chronicle/design.ts`; visual dimensions/typography live in `src/app/chronicle.css`. Derive causes/consequences only from explicit scoped `CAUSED` edges, never sequence adjacency. Existing seed has no such edges; show missing causal knowledge honestly. Keep branch origin and journey progress visible. Target desktop 1920×1080. See docs/phase-2-5b-pass-1.md. Stop before advanced Pass 2 choreography or agents unless requested.

## Phase 3 research increment 2

Production research extends `src/orchestration/research_workflow.py` with identity resolution, relationship analysis and automatic promotion. Archive-only four-role callers remain supported. Keep jobs, documents, passages, candidate claims and evidence separate from canonical records until `CanonicalGraphPromotionService` validates and publishes them transactionally. A supported model assessment alone is not canon or independent verification. Never present fake inference tests or curated seeds as real research. Do not add future-agent stubs.

Research ports live in `application/ports/research.py` and `application/ports/knowledge.py`; `infrastructure/research_runtime.py` composes concrete dependencies. Keep LLM/network calls outside short transactions. Publication rechecks exact evidence, current scope, actual endpoints, aliases, contradictions and independent-source policy under scope/job locks. Repositories never commit. Preserve retraction history, seed records, user edits and unrelated support during correction. Source groups may merge derivative publishers but cannot inflate corroboration. Imported reference URLs provide attribution, never cloud-sharing permission. Sensitive aliases are excluded from ordinary reads; caller-supplied source boundaries govern spoiler-fenced reads.

The independent worker owns node-boundary snapshots, cooperative cancellation and a PostgreSQL advisory lock; do not claim native LangGraph checkpointing or SSE. Respect source policy and the default cloud-content boundary; never rotate credentials to bypass a rate limit. User instructions authorize committing and immediately pushing milestones to `main`; deployment remains outside scope.

## Phase 3 research increment 3

Source registry, local embeddinggemma/pgvector hybrid retrieval and NarrativeBuilder are implemented; see `docs/phase-3-increment-3.md` and its verification report. Keep registry discovery priority distinct from authority and navigational discovery distinct from retrieval permission. Select exact source sections before truncation. Preserve normalized evidence offsets and derivative-source groups. Embedding identity includes measured dimensions and installed digest; reuse unchanged hashes and never mix model versions. Local chat/embedding work shares a PostgreSQL session advisory lease outside archive transactions.

Events use source-anchored literal triggers and resolved participant context. Uncertain cross-source identity and endpoints remain unresolved. Narrative text comes from eligible publication assertions, not unfiltered edited summaries. Broadcast source positions are supporting boundaries, not inferred chronology or guaranteed first reveal. Preserve unordered milestones and explicit gaps. Stable milestone UUIDs derive from event IDs. The frontend provider remains local; the catalog API is implemented, but frontend wiring, image discovery and advanced choreography remain outside this increment.

## Phase 3 research increment 4

The frontend now uses `BackendNarrativeDataProvider`, nested decoding, the existing resolver and an identified complete curated fallback. Generated event regions must use only their accepted relationship hints; never silently merge fixture edges. Refresh the graph before resolving a new catalog, preserve selection by stable milestone ID and retain valid branch state. Research controls use scoped, versioned session job IDs and bounded summary polling; the independent worker is required. SSE is not implemented.

Frames retain actual/intended/hypothetical/denied/reported/uncertain candidates and typed participant `{name, role}` entries. Mentioned/nonactual candidates do not supply automatic participation. Publication checks roles and actual canonical endpoints; reported claims never automatically become actual facts. Scoped event reuse may normalize uniquely known aliases over the same source action span, not fuzzy similarity or repeated occurrences.

Model budgets restore from persisted usage plus incomplete pre-call reservations. Preserve job deadlines across restarts and do not replenish budgets on resume. Invalid output gets bounded schema-specific repair with redacted diagnostics; provider errors remain distinct. Validated inference reuse hashes complete context, schema and installed model digest. `StoredInferenceCache` owns injected short transactions; SQL repositories never commit. No archive transaction spans model/network calls. See `docs/phase-3-increment-4.md` and its verification report for actual results and remaining semantic limits. Do not begin visual redesign, image discovery or advanced GSAP work automatically.

## Phase 3 research increment 5

Knowledge categories, shared encyclopedia contracts and persisted grounded English presentations extend the existing graph. Keep canonical evidence, deterministic organization and presentation separate. GET reads perform no inference. Indexed extraction maps sentence IDs to exact archived text; never trust model-authored quotation punctuation or passage UUIDs. `KnowledgeAtlas` fences facts, names and accepted relationships by current continuity/source boundaries; unknown positions fail bounded reads. Participation requires actual roles, not mentions.

`StoryStructureOrganizer` groups exact action contexts, retains underlying UUIDs, routes/attempts and ordering gaps. Arc overviews deterministically assemble current grounded child presentations; cache identity includes those children and assembly policy. Do not invent official arcs, chronology, causality or missing English names. Rebuilds run through the independent worker with existing budgets/deadlines. Model entailment assessment is not independent verification.

Reader entries and source controls preserve journey bookmarks and prune graph/search/traversal on bounded reads. Never use broader curated fallback after a bounded failure. See docs/phase-3-increment-5.md and its verification report: real coverage remains sparse, some recaps withheld, and documents/deep lore are not demonstrated real discoveries. Image discovery, visual redesign and advanced choreography remain outside scope.

## Phase 3 research increment 5.1

The default depth is a configurable `ResearchPolicy` (`focused-v1`), not a fixed successful page count. Freeze effective policies, deadlines and reservations per job. Reconcile completed token usage; retain unknown/incomplete reservations. Research profiles configure medium-aware source strategy without granting retrieval, host or cloud permission. Check current source/continuity/cloud policy on archive reuse.

Persist unfinished questions through `ResearchFrontierService`, including beyond-depth discoveries, near-duplicate variants, available sources and stop reasons. New bounded jobs can continue the same objective; resuming an old job does not reset its budget. `last_checked_at` renews unchanged-source freshness while preserving first retrieval time, hashes and evidence. Hybrid retrieval must not restrict semantic eligibility to the newest passage window.

Dossier-based arc synthesis has its own cache and grounding checks; the legacy deterministic assembly path is not evidence of successful cohesive synthesis. GETs perform no inference. See docs/phase-3-increment-5-1.md and its verification report: the actual benchmark remains partial, original-source references are mostly navigation-only, Groq was not exercised, and rejected recaps must stay withheld. No visual redesign or image discovery is authorized by this increment.

## Phase 3 research increment 5.4

`relationship_subjects` enables the connected investigation path in the existing workflow. Query aliases are not identity proof. Evidence bundles retain exact source/passages, revisions, offsets, current permissions, explicit sections and bounded context. Preserve actual/intended/hypothetical/reported/denied distinctions and related participants; never infer chronology or causality from adjacency.

Atomic assertions must pass literal subject/predicate/object/direction binding and semantic assessment, then repeat the existing transactional publication invariants. Ordinary direct primary evidence may suffice; hidden identity and causality retain stronger requirements. Models cannot override deterministic rejection. Do not turn an entire supporting quotation into additional accepted facts.

Investigations and partial identity/verification progress use existing job checkpoints and frontier records. Reuse only under current scope, source/permission/revision, policy and relevant contradiction-context fingerprints. Preserve old deadlines and incomplete reservations. The configurable verification reserve protects calls and tokens; never replenish an old job on resume.

Inference dossiers omit full archive navigation metadata, preserving citation identities and hashes. Reader composition uses accepted atomic clauses and direct graph connections, preserves joint roles, and keeps failed grounding withheld even on cache reuse. GETs perform no inference. See `docs/phase-3-increment-5-4.md` and the real-run audit: the benchmark publishes three interactions as seven nodes/eight edges, but one reader draft remains withheld and broader questions/chronology remain unresolved. Owned tests are not live research. No automatic frontend redesign or image work.

## Story packs (draft worlds)

The product is an all-in-one story atlas: events with causes, cast, places, deep entry pages and lore. Story packs (`application/story_pack.py`, `story_pack_builder.py`, `docs/story-packs.md`) are AI-drafted, user-reviewed files loaded only into `-draft` universes. They are never canonical, never presented as verified, and must not write into other universes. Keep citations, the chapter boundary and the explicit-cause rule.

## Journey page (draft worlds)

A told arc opens as the journey page in `apps/web/src/features/article/`: React Flow draws the
stop-and-moment tree (pure layout in `journey.ts`), and `application/story_theme.py` gives each
story a contrast-checked look served in the catalog. No story-specific colours, layouts or code.

## New story builds

`/new` drives `application/story_jobs.py` through `/api/builds`. Nothing is fetched before the
reader checks a site, and no build starts without their terms confirmation; cloud sharing is a
separate choice. Keep the local-header check on every write and the page-review pause.

