# Phase 3 increment 3: source intelligence, local retrieval and narrative construction

This increment extends the existing research worker. The atlas frontend and curated graph remain intact. See the [diagnosis](phase-3-increment-3-diagnosis.md), [executed verification](phase-3-increment-3-verification.md), [live audit](phase-3-increment-3-demo.json) and [file manifest](phase-3-increment-3-files.txt). Model assessments remain fallible; publication means the deterministic evidence and scope policy passed, not independent confirmation of fictional canon.

## Source registry and access

`SourceRegistration` separates discovery priority from factual authority. Configuration includes universe, continuity, media, category, topic coverage, access method, explicit permission basis, attribution, optional section boundaries, revision/derivative family and episode source position. `SqlSourceRegistry` persists configuration separately from health and last successful network retrieval. IDs derive from the universe, normalized URL and section selectors. Multiple bounded episode sections can share a physical page without merging documents.

`SourceSelector` uses deterministic topic overlap, authority, health and priority after enforcing universe, continuity and retrieval permission. Media declarations must cover the continuity. Topic matching is lexical; it does not understand arbitrary arc boundaries. Configure bounded sections and presentation positions explicitly. Cache reuse is in acquisition, not a claim that stale material was fetched again.

Adapters support permitted HTML, one-page MediaWiki extracts/revisions, single-object official JSON API summaries, explicit URLs and the existing permitted imported-text path. HTML selection happens before truncation. Failed selections, robots denial, disallowed hosts, TLS errors, private-network destinations and byte limits remain failures. Source provenance retains normalized text version, content hash, passage offsets, registry ID, page/revision metadata when supplied, retrieval job and scope. A navigational URL never grants ingestion permission.

For an unknown registry, optional SearXNG discovery runs at most two bounded searches and retains one reference per domain. Results are cached as **navigation-only, unverified references**. A configured permission/host approval is still necessary for ingestion. The implementation does not autonomously determine site terms, grant permissions or assert that a search result is official. No live SearXNG service was configured for this demonstration. In registry mode, retrieval is restricted to configured permitted entries; unresolved claims do not silently launch unrestricted follow-up crawling. The existing explicit-source research path retains its bounded follow-up search.

## Local RAG

`EvidenceRetrieval` depends on `EmbeddingProvider` and `EvidenceIndexTransaction` Protocols. `OllamaEmbeddings` implements the former; `SqlEvidenceIndex` implements the latter. A Protocol describes the operations the application needs; it does not force inheritance or create a generic repository framework. Constructor injection lets tests substitute explicitly fake embeddings and lets production compose real adapters in `research_runtime.py`.

Passages have deterministic IDs and normalized offsets. Embedding identity includes the Ollama model name, installed digest, **measured** dimensions and passage version. The installed `embeddinggemma:latest` produced 768-dimensional finite vectors. Batches contain at most four texts. Unchanged passage/model hashes skip generation; identical content in a new revision reuses a scoped existing vector. A changed digest uses a separate index identity, never mixes dimensions, and does not overwrite the prior model's vectors.

PostgreSQL executes pgvector cosine distance. Exact-name/keyword rankings and semantic rankings are combined using reciprocal rank fusion, hash deduplication and a maximum of three passages per document. Queries filter universe, continuity, authority, allowed sources, current registry permission and source-position boundary before returning evidence. Unknown source positions are excluded when a spoiler boundary is supplied. The current corpus is bounded to 600 passages and uses exact scans, not an approximate index. Selection is evidence retrieval, not a truth score.

The worker pins up to eight retrieved passages and 6,000 characters for downstream roles. It excludes profiles/discussions from the event-call budget while keeping their identity evidence. Source selection priority and a round-robin first passage per document prevent one verbose article from consuming all event calls. This remains a bounded context window; it can miss useful sentences.

`LocalModelLease` uses a PostgreSQL session advisory lock to serialize Ollama work across API and worker processes. No archive transaction is held during model/network calls. Both chat and embedding requests unload their model after use. The existing privacy-aware router retains optional Groq fallback, rate-limit behavior and credentials; cloud content remains disabled by default. This increment's real runs used Ollama only.

## Events, identity and publication

`extract_events` asks for bounded event frames over exact sentence units. The frame includes literal action trigger, participants, location, arc, chronology/reveal hints, preconditions, outcomes and uncertainty. Event labels and descriptions derive from the exact supporting text instead of trusting generated translations. The trigger's document ID and absolute normalized offsets anchor occurrence identity. Different repeated occurrences can have identical labels.

Named participants and locations become evidenced endpoint candidates before relationship publication. The existing vocabulary is retained: participation, occurrence location, precedence, cause/enabling, revelation and other relationships are distinct types. Indexed sentence and endpoint references avoid model-generated UUIDs and approximate quotations. The analyst may propose additional relationships; publication still validates actual endpoints and their scope in one transaction.

Actuality and participant roles are explicit frame fields. Intended/hypothetical/uncertain frames are omitted, and mentioned people do not automatically become participants. Publication additionally rejects explicitly nonactual event metadata. These checks were added after an observed live false positive, which was retracted with its evidence history retained. They reduce errors but do not turn model-generated role classifications into independent verification.

Character references resolve before events. Resolution supports explicit bilingual annotations, source-grounded full-name order changes and unique short references. Shared surnames and mere co-occurrence cannot establish identity. Event comparison considers occurrence, granularity, repeated-attempt exclusion, source anchor, source position, resolved participants, location and descriptions. Uncertain comparisons remain unresolved. An exact source anchor and canonical IDs provide deterministic replay protection; cross-source semantic event matching still depends on the small model and is not guaranteed complete.

Promotion retains the existing independent-family requirements, exact evidence checks, contradiction handling, scope locks, immutable provenance, idempotency and reversible support records. Derivative summaries are conservatively grouped with their underlying source. New characters, causality and sensitive revelations still require stronger corroboration. No policy was weakened merely to increase publication counts. Model output classifies fictional story content separately from publication/publicity facts; supported assessments alone cannot bypass publication gates.

## Workflow and narrative

The production LangGraph is Planner → Researcher → ResearchContext → Extractor → IdentityResolver → RelationshipAnalyst → Verifier → PromotionPolicy → NarrativeBuilder, with bounded conditional follow-up. These are working workflow functions, not a family of placeholder agent classes. LangChain adapts provider calls and structured schemas; LangGraph controls transitions over typed state. The independent worker persists node-boundary snapshots, cooperative cancellation and single-job locking. This is not native LangGraph checkpoint storage or SSE.

Terminal jobs with frozen extraction can retry a downstream stage with a reason, at most twice. `refresh: true` creates a genuinely fresh execution of the same objective; it does not merely return the previous job from request deduplication. Retrying after identity changes preserves evidence and candidates instead of pretending to reacquire sources.

`NarrativeBuilder` projects active publications and actual graph UUIDs into schema-version-1 `NarrativeCatalog`. Stable journey and milestone IDs derive from continuity/event IDs. Participation, location and cause/consequence references come only from accepted typed edges. Only eligible source-backed assertion payloads supply text; later edits to a canonical summary cannot leak into an earlier projection. The projection is persisted with a content revision and source/spoiler boundary.

The default basis remains broadcast presentation. A step labeled **By episode N** means the earliest supporting episode source in the archive, not proof of first reveal or in-world chronology: synopses can recap earlier occurrences. Accepted PRECEDES edges can establish within-episode order. Otherwise one connected representative is shown for that episode and other milestones remain unordered with explicit gaps. Selection ties use stable IDs, never invented story order. Unknown positions remain unordered. Causes and consequences are empty when no qualifying accepted edge exists.

The backend offers a compatible catalog endpoint. The frontend provider remains unchanged and does not yet fetch this endpoint automatically. The real returned catalog was checked through the existing TypeScript resolver against the live graph. Lore/discovery projections are supported for accepted lore/mystery records, but the demonstration did not establish new lore, historical-context or mystery links.

## Migration and operation

Migration `184914a50063`, following `a133bb90a692`, creates `source_registry`, `passage_embeddings` and `narrative_projections`, and adds document provenance. It creates pgvector in `public`; vector columns allow varying dimensions, with model/dimension filters preventing mixing. Downgrade removes increment tables/column but preserves the shared extension. Migration files remain self-contained.

Compose uses `pgvector/pgvector:0.8.7-pg18-trixie`, retaining the existing PostgreSQL volume. Back up before changing an existing database image. Never reset volumes. Install the updated lock, start Compose and run Alembic upgrade from `services/intelligence`:

```powershell
docker compose up -d --wait
Set-Location services/intelligence
..\..\.venv\Scripts\python -m alembic upgrade head
..\..\.venv\Scripts\python -m uvicorn src.main:app --host 127.0.0.1 --port 8000
```

Pull/install `qwen3.5:4b` and `embeddinggemma:latest` in Ollama. Set `OLLAMA_EMBEDDING_MODEL` when selecting another installed model. Preserve existing Groq values. For the licensed TVmaze example, explicitly include `api.tvmaze.com` in the process's `RESEARCH_ALLOWED_HOSTS`; the default example remains conservative. TVmaze documents public HTTP API access and CC BY-SA licensing. This environment rejected HTTPS certificate validation; the demo used documented HTTP for public non-secret episode summaries, retained credit and did not disable TLS verification.

Working APIs:

| Route | Purpose |
| --- | --- |
| `POST /api/research/sources` | Register source configuration and declared permission |
| `GET /api/universes/{slug}/research/sources` | Inspect registry and optional scoped/topic selection |
| `POST /api/research/sources/discover` | Bounded cached navigational discovery |
| `POST /api/research/evidence/query` | Scoped hybrid retrieval; optional archive indexing |
| `POST /api/research/jobs` | Queue research, with `use_registry`, `narrative_research`, `spoiler_position`, optional `refresh` |
| `POST /api/research/jobs/{id}/retry` | Bounded downstream retry over frozen extraction |
| `GET /api/universes/{slug}/narrative` | Generated catalog; required `continuity_id`, optional `spoiler_position`, repeated `allowed_source_id` |

Registration does not start research. After queuing a job, run `python -m src.research_worker --once --job-id <UUID>` from the backend directory using the root venv. Inspect job/findings/events/knowledge endpoints for progress and publication evidence. No deployment, frontend redesign or image-discovery work is included.
