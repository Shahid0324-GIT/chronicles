# Universe Atlas repository guidance

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
