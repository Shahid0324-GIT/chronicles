# Architecture overview

Phase 3 increment 3 adds a source registry, local embeddinggemma/pgvector hybrid evidence retrieval and a persisted narrative projection around the existing research/publication workflow. Constructor-injected application ports keep model calls, source adapters and database transactions separate. The [increment 3 architecture](../phase-3-increment-3.md) describes the working graph, source permissions, event identity, model resource lease, evidence gates, partial-order semantics and current limits. The existing frontend provider remains unchanged; generated catalogs are available through a backend read endpoint.

The continuous atlas flows from a Next.js server component to the local FastAPI API, through a constructor-injected application use case, through repository Protocols implemented by SQLAlchemy adapters, and into PostgreSQL. API schemas map domain values explicitly. Browser interaction uses the graph already retrieved from the backend.

```mermaid
flowchart LR
  Web[Next.js continuous atlas] --> API[FastAPI routers and schemas]
  API --> UseCases[Application use cases]
  UseCases --> Ports[Repository Protocols]
  Adapters[SQLAlchemy repositories] -. implements .-> Ports
  Adapters --> DB[(Local PostgreSQL)]
  UseCases --> Domain[Domain entities and value objects]
  API --> Composition[Depends composition root]
  Composition --> Adapters
```

## Domain

Universe is the top-level identity, not a tree root. Continuities identify adaptations or other explicitly separated bodies of knowledge. Nodes represent heterogeneous entities and edges retain both direction and semantic relationship type. A node may participate in arbitrarily many relationships, including cycles.

`Slug` validates URL-safe identifiers. Node and relationship enums provide a deliberate application vocabulary. Persisted type strings avoid native database enum evolution overhead; adding a type still requires a coordinated domain/contract change. Unknown persisted strings fail explicitly rather than being misclassified.

An edge validates endpoint identity and universe equality. Scoped endpoints must agree on continuity; the edge must retain that scope. Shared endpoints can connect within a specified continuity. Two explicitly shared endpoints may have a shared edge or a continuity-specific edge. Composite foreign keys enforce universe ownership in storage, including continuity ownership. Cross-adaptation compatibility remains domain policy; all future mutation paths must invoke endpoint validation. There is no mutation API in this phase.

## Application and composition

`UniverseRepository` and `GraphRepository` are the canonical graph ports. Phase 3 adds scoped archive, transaction, source-acquisition and search ports in `application/ports/research.py`, plus provider-independent inference contracts. Each is a meaningful persistence/test substitution boundary. ListUniverses, GetUniverse, GetUniverseGraph and GetNodeDetails receive their dependencies through constructors. Frozen result DTOs aggregate graph and detail responses without depending on HTTP.

FastAPI Depends providers are the composition root. The cached request session is shared by both repositories; its yield dependency opens a transaction, commits on success, rolls back on failure and closes. Graph reads are sequential because AsyncSession cannot be shared across concurrent tasks. Engine creation happens in application lifespan; shutdown disposes its pool. No engine is opened merely by importing domain or application modules.

## Persistence and API

Tables have UUID keys, timezone-aware timestamps, indexed graph access paths and JSONB node metadata. Alembic migrations are self-contained. Repositories perform explicit ORM-to-domain mapping; HTTP responses never serialize ORM objects.

Graph responses separate `nodes`, `edges`, `continuities`, and `universe`. Edge `source`/`target` attributes are adapter-friendly without making domain objects depend on Sigma. Layout belongs in the frontend. Current reads return a complete small graph; large-graph query bounds and paging are deferred.

The health endpoint probes database connectivity. Not-found, validation and unavailable persistence responses have stable error codes and messages. Unexpected failures remain server errors and are not misreported as successful data.

## Frontend

App Router server components fetch fresh local API data with a timeout and no persistent cache. `API_BASE_URL` stays server-only. The primary route is a full-viewport single-page atlas, with compatibility deep links, loading/error/not-found boundaries and empty states. Feature modules separate the Sigma/Graphology renderer, illustrated context panels, universe switching and explicit-order journeys. Per-experience Zustand state owns selection, filters, camera and mode; GSAP coordinates interruptible presentation/camera motion. See [Phase 2](../phase-2-atlas.md). There are no frontend sample records, remote fonts, paid assets or inference calls.

## Verification strategy

Domain and application tests run with pure values and fakes. API and repository tests use a fresh in-memory SQLite database with foreign keys enabled, proving serialization and DI without touching a developer database. An opt-in PostgreSQL test requires a clearly named test database, creates a random schema, applies actual Alembic migrations, seeds twice, exercises API retrieval, downgrades and removes the schema. Type checks and lint cover both languages; the frontend production build checks the App Router compilation.

## Autonomous research publication

Phase 3 increment 2 adds an injected identity resolver, relationship analyst and evidence-gated publication service to the existing LangGraph. Candidate claims remain separate until policy accepts them. `CanonicalGraphPromotionService` repeats current-state, scope, source and endpoint checks inside one transaction and records immutable provenance. Aliases, decisions and reversible publication history use additive PostgreSQL migrations. Source-fenced graph reads and correction APIs expose the result without a frontend redesign. See [architecture, policy, DI examples and limits](../phase-3-increment-2.md) and [executed live results](../phase-3-increment-2-verification.md).

## Historical increment 1 boundary

Phase 3 increment 1 implements injected Ollama/Groq inference, approved sources, persistent claim/evidence storage, a four-role LangGraph and an independent local PostgreSQL worker. Its archive is separate from the read-only canonical graph; a model-supported claim is not automatically canon. See [the research architecture and transaction/checkpoint boundaries](../phase-3-research.md). Embeddings, SSE, native LangGraph checkpointers, human promotion and frontend research integration remain deferred. No future-agent placeholder classes or fabricated production research results are included.
