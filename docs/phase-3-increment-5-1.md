# Increment 5.1 — focused adaptive research

The **focused policy and persistent frontier are implemented**. The live Re:Zero benchmark remains partial; a cohesive arc recap did not pass grounding. See [executed verification](phase-3-increment-5-1-verification.md), [actual audit](phase-3-increment-5-1-demo.json), [diagnosis](phase-3-increment-5-1-diagnosis.md) and [file manifest](phase-3-increment-5-1-files.txt).

## Configuration

`RESEARCH_FOCUSED_POLICY` accepts the `ResearchPolicy` JSON contract. A job can provide `research_policy` overrides. The API persists the effective policy, and execution freezes it in the checkpoint. The depth label is `focused`; it does not mean a fixed source count. Per-job document/query/call/byte/token/time/pass/depth ceilings control effort. Required facets, relevant-fact count, source-family coverage, unanswered leads and unresolved findings control sufficiency. Existing deployment-level limits remain upper bounds; raise them intentionally together with the policy when more effort is appropriate.

```json
{
  "depth": "focused",
  "max_passes": 3,
  "max_follow_up_depth": 2,
  "max_documents": 12,
  "max_queries": 8,
  "max_model_calls": 48,
  "max_bytes": 2000000,
  "max_tokens": 150000,
  "max_seconds": 900,
  "dossier_tokens": 3500,
  "required_facets": ["identity", "events", "connections"]
}
```

These are adjustable resource defaults, not minimum or sufficient numbers of pages. A new bounded job can extend the same archive/frontier. A resumed job retains its original deadline, usage, reservations and acquisition counters. `adaptive_research=false` retains the legacy archive pipeline for callers that need it. Presentation-only jobs still perform no research.

Token reservations conservatively include prompt/schema estimates, repair allowance and bounded output. Completed calls reconcile against reported tokens; unknown/interrupted calls keep their reservations. This is an estimated token allowance, not a model-specific exact tokenizer. Network body reads reserve their bounded maximum before work, then account for known response sizes; unknown failed reads keep the reservation. Robots and redirects also pass through the byte ledger. Retrieval remains serial with source timeouts, per-host pacing, content-size limits, DNS pinning and redirect checks.

## Profiles and source strategy

`PUT/GET /api/universes/{slug}/research/profile` configures original medium, actual continuity media, source categories, publishers, authorized/reference sites, APIs, aliases, story structure, priorities, methods and boundary notes. The profile grants no host, retrieval or cloud permission. Declared media must match actual continuity records. Unknown universes use an explicitly unknown profile context rather than an invented medium.

The existing registry remains authoritative about retrieval permission. Ranking combines objective/plan relevance, authority, configured category priority, health and source-family diversity. Already inspected registry entries do not occupy every later pass. Permitted sources are allocated across the remaining pass allowance; page count never establishes coverage. Current host policy is checked before acquisition. Discovered references remain navigation-only and unverified until access and continuity are established. Lightweight URL classification helps organize candidates; it is not factual authority.

Adaptive discovery can run even when a registry exists. The planner's questions and diversified queries replace the old episode-guide-only discovery bias. Queries can include profile aliases, original-language names and relevant source categories, with near-duplicate suppression. Search reservations are persisted before search. Autonomous external search still requires configured loopback SearXNG; the benchmark's extra references were separately identified by the operator and labelled accordingly.

## Durable research memory

`ResearchFrontierService` stores questions independently of jobs, scoped by universe, continuity, source boundary and normalized objective. Leads retain origin, topic, priority/value/cost estimates, available sources, accepted evidence and entity IDs, missing evidence, depth, attempts, timestamps and stop reason. Exact/near duplicate questions retain their variants. Beyond-depth questions are saved for later work, not discarded. Terminal job handling returns unfinished work to queued/partial/blocked states; it does not permanently exhaust a universe.

`GET /api/universes/{slug}/research/frontier?continuity_id=...` reads the frontier; an optional spoiler position selects that exact boundary. Source-filtered reads exclude leads without established support within the supplied sources. Questions from a broader boundary are not silently exposed in narrower reads. Reusing an objective in a new job revisits its persisted frontier; related objectives are not automatically treated as identical.

Migration `315100000006` adds research profiles and leads with composite scope foreign keys and an index. Migration `315100000007` adds `source_documents.last_checked_at` and an index. It backfills existing first retrieval times, preserving evidence and original retrieval dates. Revalidation of unchanged content renews freshness without duplicating passages, embeddings or canonical nodes.

## Evidence and workflow

The existing LangGraph roles remain. Planning inspects accepted local knowledge and hybrid archive evidence before new discovery. The first pass respects the requested story/encyclopedia focus; later passes can adapt. The official-source exclusion was removed from event extraction. Existing extraction schemas still bound individual calls; multiple passes and the frontier carry unfinished research rather than claiming those batches are exhaustive.

`EvidenceDossierBuilder` chooses atomic accepted facts under a token estimate, using relevance and relationship context instead of insertion-order first-N limits. Quotations, exact offsets, provenance and canonical IDs remain attached. Narrative participants, source position boundaries, aliases, local semantic retrieval and accepted graph relationships supply context. Semantic search now uses eligible source metadata across the archive, not only the newest 600 passages. Lexical candidates are relevance-ranked before their bounded window; older evidence remains reachable.

Coverage review uses integer lead/fact references mapped by Python back to accepted IDs. Invalid optional review output preserves partial progress; provider and budget errors remain distinct. Outcomes separate sufficiency, partial coverage, blocked access, exhausted effort and insufficient evidence. Coverage is model-assisted and conservative, not independent verification or a complete global contradiction audit. Canonical promotion still runs existing transactional evidence, endpoint, continuity, alias and contradiction checks.

## Presentations and providers

The current reader is preserved. English entries reuse source-grounded facts and omit empty sections. New arc synthesis is a separately cached, validated model composition from an evidence dossier and existing English glosses, not a newly concatenated paragraph. The older deterministic assembly path remains for legacy callers; it is not evidence that cohesive synthesis succeeded. Failed synthesis is withheld. GETs never invoke inference.

Ollama remains local by default. Eligible complex tasks can route to optional Groq, while source-level `cloud_content_allowed` and global `AI_CLOUD_CONTENT_ALLOWED` must both permit the actual context. Cached retrieval rechecks current source/continuity/cloud policy. Identity context containing user edits remains local. Existing credential names are unchanged. Rate-limit handling honors retry/reset headers and shared cooldown without switching keys to evade limits. Live Groq and account-specific quota calibration were not exercised.

No frontend redesign, image discovery, new agent framework, future-agent stubs, cloud storage or deployment was introduced.
