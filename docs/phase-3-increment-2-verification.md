# Phase 3, increment 2: executed verification

Verified on 13 November 2026, Asia/Calcutta. Real research was performed on 12–13 November. The implementation is functional, but the requested live relationship demonstration remains partial. Passing synthetic tests do not establish real research quality.

## Checks

| Executed check | Result |
| --- | --- |
| Backend `python -m ruff check .` | Passed |
| Backend `python -m ruff format --check .` | Passed: 70 files |
| Backend `python -m mypy -p src` | Passed: 49 source files |
| Backend `python -m pytest -q` with explicit `TEST_DATABASE_URL` | 81 passed |
| Earlier default backend suite, before final failure-isolation test | 76 passed, 4 PostgreSQL tests skipped |
| Backend `python -m alembic check` | No new upgrade operations detected |
| Backend `python -m pip check` | No broken requirements found |
| Frontend `npm run lint --prefix apps/web` | Passed |
| Frontend `npm run typecheck --prefix apps/web` | Passed |
| Frontend `npm run test --prefix apps/web` | 42 passed across 7 files |
| Frontend `npm run build --prefix apps/web` | Production build passed |
| Frontend `npm run test:e2e --prefix apps/web` | Final full run: 8 passed |
| Real publication replay | Same records, 17 nodes / 25 edges before and after |
| Original graph comparison | All original 15 nodes and 25 edges retained, with no field differences |

Backend commands use the root venv from `services/intelligence`. The explicit PostgreSQL test URL targets `universe_atlas_test`. Tests create unique schemas, apply the actual migration chain, exercise concurrent publication, downgrade and remove their own schemas. Neither development data nor volumes were reset. The second additive migration was applied to development; schema drift check passed. Dependencies and lock files were not changed.

The suite covers normalization and bilingual identity evidence, shared surnames, ambiguous identities, wrong scope/type, source-copy deduplication, causal direction and negation, stronger source thresholds, supported synthetic participation and causality, immutable provenance, atomic failure rollback, repeated/concurrent publication, shared support, user-edit/reference preservation, retractions, privacy routing, extended workflow ordering/resume, source selection/import attribution and API source fences. A final test confirms one unavailable verifier does not block other atomic claims. These inference fixtures are explicitly synthetic and owned by tests.

The first browser run had seven passes and one mobile keyboard-focus failure on a cold load. The isolated failed test passed, followed by all eight tests passing together; no frontend workaround was added. The intermittent failure remains recorded. Playwright also reports the existing NO_COLOR/FORCE_COLOR environment warning. Thirteen backend warnings concern LangSmith's deprecated `asyncio.iscoroutinefunction` use on Python 3.14.

## Actual providers and source material

Real calls used local Ollama `qwen3.5:4b` and `qwen2.5-coder:7b`, sequentially. The latter uses local memory/CPU offload as needed; it is not a guarantee of fully GPU-resident inference on 6 GB VRAM. Groq was not called: cloud-content sharing remained disabled. Hybrid/privacy/rate-limit routing has fake-provider test coverage, not a successful live Groq demonstration. No embeddings, semantic RAG, SearXNG search, SSE or native LangGraph checkpoint service was used.

Sources were the [official character profiles](https://re-zero-anime.jp/tv/character/), [official first-season episode summaries](https://re-zero-anime.jp/tv/story/tv1r.html), and [TV Tokyo's opening synopsis](https://www.tv-tokyo.co.jp/anime/re-zero/story/). Exact markers restricted selected material to introductory profiles and episodes 1–3. The original pages contain later material and promotional navigation; the selection boundary matters.

English-source fetching through the backend failed TLS certificate validation for attempted domains. Validation was not disabled. A web-tool retrieval of the [TVmaze season episode guide](https://www.tvmaze.com/seasons/38865/rezero-starting-life-in-another-world-season-1/episodeguide) supplied three short episode-3 fragments, 24 quoted words in total, imported with attribution and a permission/scope statement. This was an explicitly imported excerpt, not a successful backend fetch or an autonomous search discovery. Its source group conservatively matches the official synopsis family, so a likely translated/derived account does not manufacture an independent confirmation. The isolated place fragment cannot establish an event's location.

Source bodies and inference prompts remain local and ignored by Git. The committed [audit JSON](phase-3-increment-2-demo.json) contains identifiers, names, decision categories, source URLs, hashes and offsets, without source-body republication or credentials. Model reasoning strings are intentionally omitted from the artifact because they can reproduce source prose and are not proof.

## Observed findings and corrections

| Real result | Status and evidence |
| --- | --- |
| `ナツキ・スバル` / Subaru Natsuki | Reused original canonical UUID `f974ad2b-7275-5dfa-8f3d-27bf2b40c03d`; official bilingual profile evidence |
| `エミリア` / Emilia | Reused original canonical UUID `a13997f9-a7a5-5468-85dc-130e52b12db3`; official bilingual profile evidence |
| Other-world location (`異世界`) | New research-owned location accepted from introductory synopsis material |
| Attack occurrence | New event accepted from the attributed episode-3 fragment; a later job reused the same canonical target |
| Purchase attempt / arrival | Extracted candidates, not reliably accepted in the initial bounded live runs |
| Mana-loss event / disappearance causal question | Narrow official-source run extracted a mana-loss candidate; identity/type checks left it unresolved, with no accepted causal edge |
| Character participation | Proposed in live runs, but invalid endpoints/insufficient grounding prevented acceptance; synthetic positive tests are separate |
| Felt | Existing character reused in the 13 November follow-up, supported by the short purchase excerpt |

Important job IDs:

- `a5a6d60d-e41e-48c9-9eee-e80e131d120b`: two accepted bilingual character identities; a third character candidate remained unresolved despite a supported model assessment.
- `4718a3c7-8433-46bd-9c17-50b638890b97`: narrow causal inquiry, no publication.
- `57ab3dea-db19-4666-a366-6ae37b7f73c9`: partial; six candidates, three active entity publications (Subaru, Emilia, attack), three unresolved, no accepted relationship. Application-service publication replay reused all three records unchanged.
- `a898e47c-f77d-43cc-a981-3b21cced376e`: partial follow-up; Felt accepted, unsupported location description withdrawn through targeted correction, new-character candidates failed the stronger source threshold, malformed participation remained unresolved.
- `7cc042e9-63d7-48b6-9919-3727bbd89bc4`: final focused run with local `qwen3.5:4b`; extracted purchase-attempt and attack candidates plus a character reference, but all three remained insufficient and nothing was published. Successful structured calls were not counted as successful research. The committed audit records the actual outcomes.

Both 13 November follow-ups recorded `source_unavailable` for the shortened official-profile selection and acquired only the attributed English import. The error is sanitized and does not distinguish marker failure from network failure. They therefore did not actually provide a fresh bilingual heading to the model; that acquisition limitation is part of their partial result, not evidence that bilingual reconciliation succeeded in those jobs. The earlier complete-profile job did demonstrate reconciliation.

Earlier mistakes were corrected through the application's audit mechanism, not hidden by editing the database: a person mislabeled as an event was removed through whole-job rollback; a real-world Shibuya promotional-cafe location was withdrawn individually; a new Satella identity was withdrawn rather than treating a name mention as proof of a distinct or hidden identity; an unsupported Loot House event-location description was withdrawn while preserving the original curated location. These runs motivated stronger type/in-world checks and the two-source requirement for new character identities. Original seed records were not replaced.

## Replay and visibility

Replaying job `57ab3dea-db19-4666-a366-6ae37b7f73c9` through `CanonicalGraphPromotionService.publish` compared graph counts and complete publication records before/after: both were 17 nodes / 25 edges and the records were identical. Posting the identical request again also returned the same job UUID within the existing 24-hour deduplication window. Comparing the current graph against the saved pre-increment graph found zero field differences for every original node and edge. Later reuse of existing targets does not imply creation of additional graph nodes. Final audited counts remain 17 nodes / 25 edges.

The API tests exercise `curated_only=true`, allowed-source graph/node views, nonexistent source boundaries, active alias support and targeted rollback. Sensitive aliases are omitted from ordinary reads. There is no per-user spoiler profile; callers must pass a suitable source boundary. The existing frontend's browser tests use the real API and preserved development graph, without database resets.

## Remaining acceptance gaps

The live evidence does not yet demonstrate dependable extraction and publication of character participation, two accepted story events, or a properly grounded candidate causal relationship. A model-supported but invalid causal/relationship assertion is not counted as success. The audit distinguishes candidates, accepted entity publications, rejected/insufficient findings and retractions.

The core typed relationship and transaction path works under synthetic owned fixtures, including a supported participation edge and a two-source causal edge. This does not substitute for the missing real demonstration. Small local models still misclassify entities, alter quotes or overstate fragments. Automatic publication therefore remains fallible and requires reversible provenance and continued evaluation. The software milestone is implemented and verified; the full research-quality acceptance target remains unfinished.

Live Groq routing, automatic general transliteration, cross-adaptation shared-identity reconciliation, comprehensive spoiler enforcement, semantic event deduplication, large-graph performance and frontend research controls remain unimplemented or unverified. The next increment should evaluate and improve grounded event/relationship extraction on permitted short sources before adding more agents.
