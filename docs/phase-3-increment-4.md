# Increment 4: reliable research and live atlas integration

The existing illustrated atlas now consumes generated PostgreSQL-backed journeys through `NarrativeDataProvider`. A small research control queues work, follows persisted status, displays accepted discoveries and refreshes the graph/catalog. The independent worker remains separate from HTTP clients. No frontend redesign, new agent hierarchy, image discovery, external authentication or deployment is included.

See [diagnosis](phase-3-increment-4-diagnosis.md), [executed verification](phase-3-increment-4-verification.md), [actual audit](phase-3-increment-4-demo.json) and [changed files](phase-3-increment-4-files.txt). Earlier increment reports remain historical; curated fixtures are never relabeled research.

## Structured inference and budgets

`InferenceRouter` retains privacy-first Ollama/optional Groq routing. `LangChainProvider` supplies structured schemas to the installed model. A schema must represent an object. Validation failures carry bounded field-location/error-type diagnostics, excluding values, unexpected input field names, raw responses and prompts. Provider availability/failure and exhausted structured validation have distinct sanitized codes.

Invalid output receives a bounded corrective prompt describing the schema failures and required fields; it does not receive an unchanged retry. Identity-specific repair instructions are restricted to identity tasks. `AI_MAX_ATTEMPTS` includes the initial attempt. A compared identity missing a target is handled once as unresolved by the resolver rather than through a redundant cross-field Pydantic validator that the JSON schema could not express.

Production defaults:

| Limit | Configuration / default |
| --- | --- |
| Actual provider invocations per job | `AGENT_MAX_MODEL_CALLS=48` |
| Calls by task | `AGENT_STAGE_MODEL_CALLS`: planning 3, extraction 8, identity resolution 16, relationship analysis 3, verification 24 |
| Attempts per structured request | Existing `AI_MAX_ATTEMPTS=2`; at most one corrective retry by default |
| Source acquisitions | Existing `AGENT_MAX_SOURCES=20`, shared across workflow iterations; cache hits do not consume acquisitions |
| Follow-up/refinement | Existing `AGENT_MAX_ITERATIONS=3`, query/source budgets and relationship-analysis task cap |
| Job deadline | `AGENT_MAX_JOB_SECONDS=900`, persisted at first worker claim and retained across resumes |
| Local inference concurrency | Existing `AI_MAX_CONCURRENT_INFERENCES=1`, with the shared PostgreSQL local-model lease |

Total limits include failed provider invocations and repairs. Successful cache reads and availability probes are not new model calls. Before inference, a short transaction persists an `inference.started` reservation. Completed usage closes the reservation by ID. Unfinished reservations remain charged conservatively after interruption, so restarting a worker cannot replenish its budget. No archive transaction spans the model request. Budget blocks become persisted sanitized events and unresolved/partial results; unrelated supported findings can still be published.

The first claim establishes an absolute deadline in the job checkpoint. Workflow checks and the worker timeout enforce the remaining time. Resuming an expired job does not reset its clock; a genuinely new job requires a refreshed request. Cooperative cancellation and terminal events remain independent of browser connections. A process killed during a request may leave a reserved attempt whose actual completion is unknowable; telemetry identifies it as incomplete rather than inventing a response.

## Safe reuse and persistence

`InferenceCache` is a narrow application Protocol implemented by `SqlInferenceCache`. It stores only validated extraction and exact-context verification results for up to 24 hours. Keys hash the provider, model, installed model digest, system instruction, complete prompt, full schema and public-content boundary. Source passage IDs and exact text are inside that hash input; scope and source versions cannot silently cross-match. Prompts are not stored in the cache or telemetry. Payloads remain local research data subject to the existing source policy.

`StoredInferenceCache` owns these short transactions through an injected cache-transaction Protocol. The SQL repository accepts one session, performs queries/upserts and never commits. Runtime composition supplies transaction factories; no session is shared between concurrent requests.

Every read is validated against the requested Pydantic schema. Changing the model digest, schema, source context or objective produces a different key. Expired rows are removed during writes; concurrent writes use a database upsert. Cloud results without a stable model revision are not cached. Verification keys retain the claim and complete supplied evidence context; they are not an evergreen truth cache. Canonical publication always repeats current graph/evidence/scope/retraction checks, including for cached inference.

Migration `2694c0a70004`, after `184914a50063`, creates `research_inference_cache` and its timestamp index. It adds no canonical graph columns and resets no data. Downgrade removes only the new table/index. Existing archive events and checkpoint JSON store reservations, deadline and telemetry, avoiding duplicate job tables. No new package dependencies or lock changes were needed.

## Event and relationship quality

Frames distinguish ACTUAL, INTENDED, HYPOTHETICAL, DENIED, REPORTED and UNCERTAIN (lowercase transport values). Reported assertions are not converted automatically into actual occurrences. Classified nonactual candidates remain in the archive without generated participation edges; identity/verification skip unnecessary model calls for them. Publication independently blocks explicitly nonactual metadata. A separate, sufficiently supported actual assertion can be evaluated normally; there is no automatic reported-to-actual promotion.

Participants use compact typed `{name, role}` entries: actor, recipient, witness, opponent or mentioned. This replaces a split name list/arbitrary dictionary that the real 4B model filled inconsistently. Materialization requires a literal name in attached evidence. Mentioned people never become automatic participants. The publication transaction also checks role constraints against bound canonical identities and accepted current event frames, so a model's supported assessment cannot make a mentioned beneficiary a participant.

Identity reuse first checks uniquely known scoped aliases or a validated occurrence anchor. A wording variation over the same document's overlapping action span can reuse an occurrence when participants resolve through unique existing aliases and location context agrees. Ambiguous aliases and separate spans/sources do not establish sameness. Cross-source semantic comparisons remain bounded and fallible. Publication repeats deterministic occurrence and actual-endpoint checks inside its transaction.

Chronology, causality and location remain separate semantics. Episode/page order cannot manufacture PRECEDES or CAUSED edges. Existing explicit marker/direction, source-family, contradiction and continuity rules remain enforced. Publication rejects explicit advertising/promotional venues and publisher addresses as story locations. The model must still assess in-world content. The analyst can propose existing affiliation/lore/revelation types; no relationship is created merely to populate a panel.

## Telemetry and job execution

Observed LangGraph nodes persist stage starts, completions/failures, active stage and elapsed times. Node-boundary checkpoints remain the resume mechanism; this is not native LangGraph checkpoint storage. Usage retains provider/model, task, retry index, sanitized validation diagnostics, token counts where returned and reservation ID. The API summary includes calls/cache hits/retries/validation failures, source/acquisition and embedding counts, candidates, unique accepted links, unresolved findings, active stage, elapsed times and accepted canonical discovery IDs. It omits prompts, source quotations and credentials.

`GET /api/research/jobs/{id}/summary` is the compact read contract. Existing job, findings, knowledge, events, cancellation and correction endpoints remain available. Stage completion is not proof of complete knowledge: partial jobs and missing links remain explicit.

Run the backend, frontend and worker in separate local terminals after upgrading migrations:

```powershell
# Repository root; Docker and Ollama must already be running.
docker compose up -d --wait
.\.venv\Scripts\python -m pip install -r services/intelligence/requirements-dev.lock
Set-Location services/intelligence
..\..\.venv\Scripts\python -m alembic upgrade head
..\..\.venv\Scripts\python -m uvicorn src.main:app --host 127.0.0.1 --port 8000
```

In another terminal, from `services/intelligence`: `..\..\.venv\Scripts\python -m src.research_worker`. From the root in a third terminal: `npm run dev --prefix apps/web` (or build then start for production verification). Closing the page does not stop the worker. A queued job waits if no worker is running.

Install/use local `qwen3.5:4b` and `embeddinggemma:latest`. Existing `GROQ_API_KEY_PRIMARY`, `GROQ_API_KEY_SECONDARY` and `GROQ_MODEL` remain unchanged and optional. No cloud model name is hardcoded. Cloud content remains disabled by default, and all real runs in this increment used Ollama. Keep local credentials out of Git.

Register explicitly permitted sources through the existing registry API before starting UI research. The demonstration reuses the official introductory episode sections and licensed TVmaze episode summaries from Increment 3. Include `api.tvmaze.com` in the process allowlist when using that configured adapter and preserve its CC BY-SA credit. A host allowlist does not grant processing permission. Episode source boundaries filter acquisition and retrieval; unknown/later positions are excluded from a bounded request.

## Backend-to-atlas contract

`BackendNarrativeDataProvider` fetches the catalog through a same-origin Next route. Server-only code retains the FastAPI base URL. The proxy exposes deliberately limited narrative, job-creation and summary paths; it does not accept an arbitrary destination URL or forward credentials. Job creation validates the local request origin, including Next's localhost/127.0.0.1 adapter normalization, and rejects cross-site submissions.

The decoder checks nested catalog fields, IDs, hints, citations and ordering. The existing resolver then verifies graph references and continuity. Generated catalogs carry revision, provenance availability and partial-order metadata. The API also supplies source-backed identity names/aliases and participant roles where accepted evidence supports them. The frontend shows roles on character branches. ENABLED edges are labeled enabling conditions; neither adjacency nor an empty panel becomes causality.

Generated event regions use only relationship IDs explicitly included in that catalog's scoped presentation hints. They do not silently combine the generated journey with unrelated curated graph edges. Curated fallback is one complete, explicitly identified catalog when the service is unavailable, malformed or has no supported journey. Loading cancellation never becomes a fallback response. The availability indicator and source notes distinguish model research from manual notes; neither claims independent verification.

Refresh loads a current graph without clearing exploration state, then reloads the catalog through the provider. Selected milestones reconcile by stable step ID, with a bounded fallback when a selected step disappears. Universe/continuity guards reject stale responses. Branch expansion and valid journey position survive ordinary refresh; source corrections can legitimately remove/reclassify a milestone. Existing progress/history remain per-experience Zustand state, and the larger visual system is unchanged.

The source boundary is not an assertion of exact in-world chronology or first reveal. The spine remains a partial outline over supporting episode sources, with ambiguous events retained in the API's unordered collection and a visible gap indicator. It does not invent a total order. Detailed unordered-event navigation and certified first-reveal order remain outside this milestone.

## Minimal research controls and polling

The header's Research button opens a compact panel. Confirm the active universe/continuity, enter an objective, optionally set an episode-source ceiling, and start a job. The UI uses the existing registry-backed job API without granting new source permissions. It follows status and accepted discoveries, then offers an explicit Refresh story atlas action. The map remains dominant.

Polling runs every three seconds, at most 300 polls, and pauses after four consecutive read failures. Check status resumes it. Abort controllers and timer cleanup stop obsolete scope/unmounted requests. A versioned session-storage record contains only the scoped job UUID; a page reload can resume following it. Objectives and source content are not stored in browser storage. If storage is unavailable, the current page still follows the in-memory ID.

SSE was deliberately not added. Polling reads persisted status/events indirectly through the summary and preserves independent execution and terminal results. It avoids a long-lived database session per client and the added reconnect/backpressure infrastructure. There is no fake stream. Job history across browser sessions, notifications and automatic background atlas refresh are not implemented.
