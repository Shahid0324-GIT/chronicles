# Chronicles: a story atlas on free and local models

Chronicles turns one story arc into an explorable atlas: events, causes and consequences,
characters, places, deep entry pages and lore, each tied to a source. It is a
**budget-constrained** project: it is built to run on free cloud allowances and a model on
your own PC, localhost only, with no authentication, cloud storage or deployment.

## Direction

`name a world and arc -> find sources -> read -> build the atlas -> you review -> explore`

| Step | State |
|---|---|
| Model chain: Groq, then Gemini, then local Ollama | working |
| Draft worlds read as a cited arc article with a timeline, plus the story map, built from a reviewed story pack | working ([story packs](docs/story-packs.md)) |
| File-based story library, many arcs per world | working |
| Agent that finds and saves an arc's pages from wikis you approve | working, tried on one wiki ([story packs](docs/story-packs.md)) |
| Images with credit, arc-focused screens, later-fact lookups | planned |
| Game lore scattered across books and items | planned |

AI-drafted content is labelled as a draft and is never presented as verified. Quality
depends on the sources and on your review.

## Model providers

Put one key per provider in the root `.env`: `GROQ_API_KEY_1` with `GROQ_MODEL`, and
`GEMINI_API_KEY_1` with `GEMINI_MODEL`. When a provider reaches its limit the next one takes
over, ending with local Ollama. Keys are never rotated to get past a provider's limit; do
not add several accounts for that purpose. Text goes to a cloud provider only with
`AI_CLOUD_CONTENT_ALLOWED=true` and permission for its source. Free tiers may use submitted
text to improve their products.

## Earlier research engine

The graph API, research worker and arc research from earlier phases remain in the code and
are documented in `docs/` (see [verification history](docs/verification.md) and the
[source registry and retrieval notes](docs/phase-3-increment-3.md)). The new direction does
not build on them, and they will be removed only after it is proven.

## Prerequisites

- Windows 11, PowerShell, Python 3.11+, Node.js 20.9+ (Node 24 LTS recommended), npm, Docker Desktop using Linux containers.
- Docker Desktop must be running. Ports 5432, 8000 and 3000 must be free.
- Internet is needed for installation and public-source research. Graph browsing and local Ollama work offline. Groq and Gemini are optional and require explicit cloud-content permission.
- Verified versions and check results are in [verification.md](docs/verification.md).

## Install

From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r services/intelligence/requirements-dev.lock
.\.venv\Scripts\python -m pip install --no-deps -e services/intelligence
npm ci --prefix apps/web
Copy-Item .env.example services/intelligence/.env
Copy-Item apps/web/.env.example apps/web/.env.local
```

The lock file captures the verified backend dependency set. To intentionally upgrade dependencies, install `-e './services/intelligence[dev]'`, run all checks, and regenerate the lock. Frontend exact versions and `package-lock.json` capture npm resolution. No global tools are required. Activating the virtual environment is optional; these instructions use its Python directly.

## Database, migration, and illustrative sample

```powershell
docker compose up -d --wait
Set-Location services/intelligence
..\..\.venv\Scripts\python -m alembic upgrade head
..\..\.venv\Scripts\python -m src.infrastructure.persistence.seed
```

Run the seed again safely. It inserts missing deterministic IDs, preserves existing rows and user edits, and uses one transaction. Run one seed process at a time. A conflicting pre-existing `re-zero` slug aborts the operation.

The sample contains one universe, one anime continuity, 15 nodes and 25 edges. It is hand-curated **illustrative data**, limited to the original TV anime's opening three episodes, with early-story spoilers. It does not claim exhaustive or researched coverage. Reference: [official first-season story guide](https://re-zero-anime.jp/tv/story/tv1r.html) (the guide includes later episodes; the seed excludes them). No adaptation is assumed equivalent to another.

`compose.yaml` binds PostgreSQL to loopback and stores data in a named volume. The supplied credentials are for local development. `docker compose stop` stops it without removing data. Backend owns all schema changes; frontend never connects to PostgreSQL.

## Run

Terminal 1, from `services/intelligence`:

```powershell
..\..\.venv\Scripts\python -m uvicorn src.main:app --reload --host 127.0.0.1 --port 8000
```

Terminal 2, from the repository root:

```powershell
npm run dev --prefix apps/web
```

Open [the atlas](http://127.0.0.1:3000) and [API documentation](http://127.0.0.1:8000/docs). Next.js server components fetch FastAPI through server-only `API_BASE_URL`; the browser receives a continuous illustrated atlas. Universe switching uses a same-origin forwarding route, and selection, camera, filters and relationship traversal use shared exploration state.

Backend settings read process environment, the repository-root `.env`, and then `.env` in the current directory (process environment wins). `DATABASE_URL` must use `postgresql+asyncpg://`. Frontend `.env.local` sets `API_BASE_URL`; it is not a `NEXT_PUBLIC_` variable. Restart services after changing settings. CORS origins are an explicit JSON list for future direct browser API clients; the current frontend fetches server-side.

## Checks

From `services/intelligence`:

```powershell
..\..\.venv\Scripts\python -m ruff check .
..\..\.venv\Scripts\python -m ruff format --check .
..\..\.venv\Scripts\python -m mypy -p src
..\..\.venv\Scripts\python -m pytest -q
..\..\.venv\Scripts\python -m alembic check
```

Default tests use **in-memory SQLite with foreign keys enabled** or fake repositories. They do not read `DATABASE_URL`, connect to development PostgreSQL, or require Docker. The PostgreSQL test is explicitly skipped unless configured. SQLite tests validate adapters and API behavior; they do not replace PostgreSQL migration verification.

For the opt-in test, start Docker and create a separate database **once**, from the root:

```powershell
docker compose exec -T postgres createdb -U atlas chronicles_test
$env:TEST_DATABASE_URL = 'postgresql+asyncpg://atlas:atlas_local@127.0.0.1:5432/chronicles_test'
Set-Location services/intelligence
..\..\.venv\Scripts\python -m pytest -q
Remove-Item Env:TEST_DATABASE_URL
```

The test rejects database names without `_test`, creates a uniquely named schema, runs the actual Alembic upgrade, seeds twice, reads through API dependencies, downgrades, and removes only that schema. It never uses the normal database URL. If the test database already exists, reuse it; do not rerun `createdb`.

From the root:

```powershell
npm run lint --prefix apps/web
npm run typecheck --prefix apps/web
npm run build --prefix apps/web
```

For a production-mode local frontend, run `npm run start --prefix apps/web` after building. FastAPI and PostgreSQL must be running when requesting pages; compilation itself does not require them.

## API contracts

| Route | Response |
| --- | --- |
| `GET /api/health` | `{status: "ok", database: "ready"}` after `SELECT 1` |
| `GET /api/universes` | Universe array, sorted by title |
| `GET /api/universes/{slug}` | Universe metadata |
| `GET /api/universes/{slug}/graph` | `{universe, continuities, nodes, edges}` |
| `GET /api/nodes/{id}` | `{node, edges}` with incoming and outgoing edges |
| `GET /api/universes/{slug}/arcs/{arc_id}` | Arc dossier and available article for a required `continuity_id`, with optional `spoiler_position` and `allowed_source_id` filters |

IDs are UUID strings; timestamps are ISO 8601. Graph edges expose `id`, `source`, `target`, `relationship_type`, `description`, `universe_id`, and nullable `continuity_id`. Nodes have IDs and typed attributes but no layout coordinates. The frontend Sigma adapter owns layout. Errors use `{code, message}` for missing records (404), invalid parameters (422), and unavailable persistence (503). Empty catalog and graph results are valid successful responses. The health endpoint checks connectivity, not schema revision; use `alembic current`/`alembic check` for migrations.

## Architecture and scope

See [architecture](docs/architecture/overview.md), [backend ADR](docs/adr/0001-backend-architecture.md), [persistence ADR](docs/adr/0002-persistence.md), and [repository guidance](AGENTS.md).

- `services/intelligence/src/domain`: entities, graph invariants, enums, slug value object; no framework imports.
- `application`: repository Protocols, constructor-injected use cases, transport-independent DTOs.
- `infrastructure`: settings, SQLAlchemy models, async repositories and explicit mappings.
- `presentation`: API schemas, routes and FastAPI dependency composition.
- `apps/web`: Next.js App Router, strict TypeScript, Tailwind, Atlas rendering boundary.

The research worker uses LangGraph and injected Ollama/Groq inference. Permitted URL and text ingestion preserves evidence in PostgreSQL. Local retrieval combines lexical and pgvector search, and optional SearXNG provides discovery. The worker can promote verified claims and relationships into the canonical graph through guarded, reversible transactions. The atlas reads through the API and uses Sigma, Graphology, GSAP, and Zustand for exploration. [Source registry and retrieval](docs/phase-3-increment-3.md) · [Research-backed journeys](docs/phase-3-increment-4.md)

## Troubleshooting

- **Docker pipe denied / connection failed:** start Docker Desktop, select Linux containers, and run `docker info`. This agent's sandbox required approved host access for Docker and local sockets.
- **Port 5432 occupied:** stop the conflicting service or change the Compose host port and `DATABASE_URL` together.
- **Database does not exist / authentication failed:** confirm `.env`, Compose settings, and existing volume credentials agree. Environment changes do not reset an initialized PostgreSQL volume. Preserve the volume and fix configuration.
- **Relation does not exist:** run `alembic upgrade head` from `services/intelligence`; there is no automatic schema creation at startup.
- **Atlas unavailable:** check `/api/health`, migrations, and frontend `API_BASE_URL`. An unknown slug produces a separate not-found page. The error view has a retry action.
- **`ensurepip` or temporary-directory permission failure:** set `$env:TEMP` and `$env:TMP` to an existing writable local directory. If the venv exists without pip, use system `python -m pip --python .\.venv\Scripts\python.exe install pip`, then install normally.
- **Package registry `ENOTFOUND`:** dependency installation needs permitted network/DNS access. This is distinct from application runtime, which requires no external services.
- **PowerShell activation policy:** invoke `.venv\Scripts\python` directly; changing execution policy is unnecessary.
- **Async tests stall under a restrictive Windows sandbox:** run the same tests in a normal local terminal; SQLite uses worker threads and PostgreSQL uses loopback sockets.

## Phase 2.5A narrative and lore

**Current visual experience:** [Phase 2.5B Pass 1](docs/phase-2-5b-pass-1.md) replaces the default graph presentation with a horizontal illustrated chronicle. Open a milestone, expand a character/lore/place branch and return to the saved story position. Free graph retains Sigma exploration. Desktop 1920×1080 is the primary target. [Visual review and checks](docs/phase-2-5b-verification.md).

The atlas opens a four-moment, manually curated Re:Zero introduction covering original anime episodes 1–2. Follow story moments, inspect a character, investigate Return by Death and return to the same step. Facts, interpretations and unresolved questions have distinct labels. Story order follows broadcast presentation, including repeated attempts; it is not inferred chronology.

Rerun the existing seed to add required graph records while preserving existing data: the illustrative atlas now has **15 nodes and 25 edges**. No migration is required. Notes reference API UUIDs through an injectable local provider; React contains no canonical graph fixtures. Progress/history stay in the current session.

See [the original architecture and limitations](docs/phase-2-5a-narrative.md), [narrative API contracts](docs/contracts/narrative-api.md), and [verification](docs/verification.md). The atlas now reads the backend narrative catalog, with the curated introduction available as an identified fallback. [Backend integration](docs/phase-3-increment-4.md)

## Phase 2 frontend

See [the continuous atlas guide](docs/phase-2-atlas.md) for architecture, interaction, limitations and future contracts. Open `/` to explore without route changes.

```powershell
npm run test --prefix apps/web
npm run test:e2e --prefix apps/web
```

Unit tests need no backend. Playwright requires real seeded PostgreSQL/FastAPI at port 8000 and installed Google Chrome; the runner starts or reuses Next.js on port 3000. Use `/` to search, Tab/Enter for map entities, arrows to pan the focused map, +/- to zoom, and Home or the full-map control to reset. Guided mode never invents chronology for unordered data.

## Phase 3 increment 1: research engine

See [the architecture, API and worker runbook](docs/phase-3-research.md), [actual research findings and provider audit](docs/phase-3-demo.json), and [executed checks and limitations](docs/phase-3-verification.md). This is an incremental implementation, not every agent in the overall Phase 3 specification.

From `services/intelligence`, apply `alembic upgrade head`, start the API as above, and start the independent worker with:

```powershell
..\..\.venv\Scripts\python -m src.research_worker
```

Submit jobs through [local Swagger](http://127.0.0.1:8000/docs). The worker runs Planner → Researcher → Extractor → Verifier and persists exact evidence and candidate decisions. The default `AI_CLOUD_CONTENT_ALLOWED=false` keeps model context local. Ollama must already be running with the configured chat model. No seed content is presented as agent-discovered.
