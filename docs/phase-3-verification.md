# Phase 3 increment 1 — executed verification, 2026-11-12

Story: a client submits a scoped job to FastAPI, the independent local worker runs the four-role LangGraph against permitted material, and PostgreSQL stores findings and inspectable evidence. The existing illustrated atlas continues reading its original canonical graph.

## Checks executed

Commands used root `.venv` Python from `services/intelligence` unless indicated otherwise.

| Check | Actual result |
| --- | --- |
| Editable install with development dependencies | Installed pinned LangChain/Ollama/Groq/LangGraph stack successfully |
| `python -m pip check` | No broken requirements |
| `python -m ruff check .` | Passed |
| `python -m ruff format --check .` | Passed |
| `python -m mypy -p src` | No issues, 40 source files |
| `python -m pytest -q` with explicit `TEST_DATABASE_URL` | 49 passed; 13 upstream LangSmith deprecation warnings |
| Default suite without test URL (earlier checkpoint, before final API test) | 41 passed, 1 explicitly skipped; no default development DB access |
| Actual Alembic upgrade/downgrade | Passed in unique schema in `universe_atlas_test`; seed twice retained 15 nodes/25 edges |
| Actual PostgreSQL archive | Source, passage, claim and evidence written/read; evidence with another continuity rejected by composite foreign keys |
| `python -m alembic upgrade head` on local development DB | Additive archive revision applied without graph resets |
| `python -m alembic check` | No new upgrade operations detected |
| `npm run test --prefix apps/web` | 42 passed across 7 files |
| `npm run test:e2e --prefix apps/web` | 8 passed in installed Chrome against real PostgreSQL/FastAPI and existing production Next server |
| Final live HTTP | Health/database ready; graph 15 nodes/25 edges; atlas HTTP 200; persisted research findings HTTP 200 after API restart |

The isolated PostgreSQL test never falls back to `DATABASE_URL`. It requires an explicit asyncpg URL whose database ends in `_test`, creates a unique schema, and drops only that schema. No developer volumes were erased. Frontend source and npm dependencies were unchanged; its lint/typecheck/build were not rerun for this backend increment. Existing browser tests cover desktop/mobile, keyboard controls, scoped branch detours, empty filters, missing art, normal/reduced motion and page errors. Playwright emitted its existing NO_COLOR/FORCE_COLOR environment warning.

Deterministic tests explicitly use **fake inference and synthetic owned source text**. They cover privacy modes, missing cloud configuration, bounded retries/timeouts, shared 429 cooldown without key rotation, a waiting request rechecking cooldown, concurrency, source policy/robots/redirect checks, text stripping/truncation, evidence hashes/offsets, fabricated quotations, disputed claims, resume, cancellation, query/source budgets, deduplication and API serialization. These tests are not the real research demonstration.

## Real inference and acquisition

An actual structured-output Ollama probe succeeded with installed `qwen3.5:4b`. Robots-aware fetch probes succeeded for TV Tokyo's introductory synopsis and the official first-season story guide. Only the former supplied the final demonstration's source. The first metadata print hit Windows CP1252 `UnicodeEncodeError` after retrieval succeeded; subsequent probes/reports used UTF-8 or escaped JSON.

Successful job: `edb37626-d8f7-4e8e-9437-70e56f46f719`.

| Boundary | Evidence |
| --- | --- |
| Request → queue | Real `POST /api/research/jobs` returned 202 and persisted the scoped objective |
| Worker → graph | Actual four-role LangGraph reached verifier, iteration 1, then job `completed` |
| Acquisition → archive | [TV Tokyo introductory synopsis](https://www.tv-tokyo.co.jp/anime/re-zero/story/) fetched at `2026-11-12T13:19:41.156703Z`; cache reused by later bounded runs |
| Provider → structured results | All four successful inference calls used Ollama `qwen3.5:4b`: planning, extraction, two individual verification calls |
| Evidence → findings | Two `supported` candidate claims, exact quotations and passage IDs/offsets persisted, both `canonical: false` |
| Restart → response | Findings remained readable after restarting FastAPI, with no new inference |
| Existing response → UI | Eight existing real-service browser tests passed; canonical graph retained 15 nodes/25 edges |

Recorded tokens: planning 363 input / 116 output; extraction 831 / 241; verification calls 436 / 97 and 440 / 121. Total **2,070 input / 575 output tokens**, provider-reported. Recorded inference time sums to **11,709 ms**; this is inference-call time, not total job elapsed time.

Source document ID: `8d6cf6bf-0c23-5b0c-b873-cb1c136b974d`. Passage ID: `0b7cb235-f642-5494-b732-7a76b5464f25`. Normalized stored text SHA-256: `319a549836c6500e2c0069083fc3683c43d8a9a7345b86ea52e50fb576b9181e`.

The findings, paraphrased for this report, are:

1. Natsuki Subaru is an ordinary high-school student who finds himself in another world while returning from a convenience store. Evidence characters `[507, 548)` in the stored passage.
2. Subaru is disoriented and at a loss in the unfamiliar world. Evidence characters `[549, 601)`.

The model emitted two name spellings for the same character as separate candidates. This run therefore demonstrates **two source-backed claims, not two resolved character identities**. No relationship was extracted in this successful run. Exact Japanese model output/evidence remains in the local findings API; the [committed audit JSON](phase-3-demo.json) deliberately omits full quotations and copied model prose. Its English paraphrases are editorial report text, not additional model findings.

Earlier live jobs `6283aa7c-6fa0-40f9-a6ee-2bad81a5cd7c` and `21ebfcb2-ff18-427a-b506-afc497e3bade` ended `partial`, with no supported findings. They exposed incomplete batch assessments, translated paraphrase overrejection, alias duplication and unsupported relationship vocabulary. Unsupported outputs stayed candidates and did not enter canon. Single-claim verification and source-language descriptions fixed the demonstrated assessment failures; identity resolution remains deferred.

Groq credentials/model are configured, but `AI_CLOUD_CONTENT_ALLOWED=false`. **No live Groq inference or model-health request was made.** Cloud routing, fallback and 429 behavior passed fake-provider tests; live cloud compatibility remains unverified. No SearXNG search or embedding generation was claimed or performed.

## Remaining limits and environment

See [architecture and runbook](phase-3-research.md) for deferred work: semantic RAG/embeddings, alias resolution, human promotion, native LangGraph checkpointer, restart-persistent rate coordination, SSE, media, narrative specialists and frontend research controls. Source scope declarations and model entailment assessments are not independent canon verification. Extraction and verification using the same small model can share errors.

Tested on Windows 11, Python 3.14 and local PostgreSQL 18. LangSmith currently emits a Python 3.16 removal warning for `asyncio.iscoroutinefunction`; checks still pass. Restricted sandbox socket operations initially failed; approved host execution ran the same local commands successfully. No credentials were committed or printed.

The API and existing frontend remain running locally for review. The demonstration worker used `--once` and exited normally; new queued jobs require starting the worker. Local milestone commits were created on `main`; **no remote push or deployment**, following the current Phase 3 specification.
