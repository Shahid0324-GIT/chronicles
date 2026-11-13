# Increment 3 verification — 13 November 2026

This is a working backend milestone with a **partial live research result**. Connected participation and a source-backed catalog were produced. Reliable automatic location reconciliation, chronological edges, causality and complete story understanding were not demonstrated. The [audit JSON](phase-3-increment-3-demo.json) contains actual job, claim, passage, source, canonical and publication UUIDs, evidence hashes/offsets, model usage, retractions and repeat checks. It omits source bodies, quotations, credentials and raw model prose. Synthetic tests are separate from real inference.

## Executed checks

Backend commands ran from `services/intelligence` using the root venv. PostgreSQL tests used an explicitly supplied `TEST_DATABASE_URL` for `universe_atlas_test`; fixtures used unique schemas and cleaned up only their own schemas.

| Check | Actual result |
| --- | --- |
| `python -m ruff check .` | Passed |
| `python -m ruff format --check .` | 93 files already formatted |
| `python -m mypy -p src` | Passed, 65 source files |
| `python -m pytest -q` with explicit test DB | **115 passed**, including six opt-in PostgreSQL tests |
| Migration upgrade/downgrade | Passed in the actual PostgreSQL migration test |
| `python -m alembic check` | No new upgrade operations |
| `python -m pip check` | No broken requirements |
| Frontend lint/typecheck | Passed; frontend source unchanged |
| Frontend unit suite | **42 passed**, seven files |
| Frontend production build | Passed |
| `npm run test:e2e --prefix apps/web` | **8 passed**, installed Chrome, existing real services, no data reset |
| Existing TS `resolveNarrative` over live catalog + graph | One three-step journey accepted, **zero reference issues** |
| Actual local-model resource lease | PostgreSQL integration checked cross-session exclusion and release |
| Actual pgvector query | SQL cosine query exercised; dimension isolation and Python-float serialization checked |

Unit tests use owned synthetic text and explicitly fake models/embeddings. PostgreSQL integration tests use fake vectors to isolate SQL, schema, concurrency and rollback behavior. The live jobs below independently used actual Ollama, real embeddinggemma and public source retrieval. The suite prints 13 upstream LangSmith/Python-3.14 deprecation warnings. Browser tests print the environment's NO_COLOR/FORCE_COLOR warning. The one-off Node TypeScript resolver check prints a module-type warning; no package metadata was changed just to suppress it.

Focused checks initially exposed fixture assumptions about continuity media case and the selected seeded event; these were corrected. A real HTTP request exposed NumPy distance serialization, subsequently fixed and retested. No failures remain in the final checks. The frontend browser run preceded the final backend actuality/serialization fixes; those changes do not alter its existing graph routes or frontend source.

## Database and providers

The existing PostgreSQL 18 installation was inspected and backed up locally before moving Compose to `pgvector/pgvector:0.8.7-pg18-trixie`. The same developer volume was retained. Migration `184914a50063` was applied after `a133bb90a692`; its upgrade/downgrade and metadata consistency were tested. No `create_all` startup path or volume reset was introduced.

Actual inference used **Ollama `qwen3.5:4b`**. Embeddings used **`embeddinggemma:latest`**, measured at **768 dimensions**, digest `85462619ee721b466c5927d109d4cb765861907d5417b9109caebc4e614679f1`. The model key also contains `passage-v2`. Groq was not used. Existing Groq environment values and local environment files were preserved. Cloud content remains disabled.

## Source registry and acquisition

Eight entries were configured and successfully retrieved. They were inspected/registered for this demonstration, **not autonomously discovered by an agent**. No SearXNG service was configured. The bounded discovery path is covered with synthetic search responses; live unknown-universe discovery remains unverified.

| Entries | Material | Access and scope |
| --- | --- | --- |
| 3 | [Official first-season story page](https://re-zero-anime.jp/tv/story/tv1r.html) | Separate exact sections for original episodes 1, 2 and 3; primary authority |
| 1 | [Official character page](https://re-zero-anime.jp/tv/character/) | Bounded introductory Subaru/Emilia heading/profile section |
| 1 | Same official character page | Felt bilingual heading only; later biographical revelations excluded |
| 3 | [TVmaze episode API](https://www.tvmaze.com/api) | English summaries for original season 1 episodes 1–3, secondary authority, page IDs and episode metadata retained |

TVmaze show ID 14459 was obtained from the real public show-search response and checked for the intended adaptation; it is demonstration configuration, not Python universe knowledge. API episode page IDs were 660417, 677597 and 677598. The API documentation permits public HTTP access and requires CC BY-SA attribution. An HTTPS diagnostic failed certificate validation in this environment; the documented public HTTP API was used without credentials, and TLS verification was never disabled. This transport limitation is explicit. TVmaze credit, original episode links and ShareAlike requirements remain in registry metadata. Bodies are not republished in this report.

API summaries were conservatively marked derivative of the official franchise material. They improve English extraction but do **not** count as independent corroboration of the Japanese synopses. Navigation-only references never bypass access policy. The eight selected entries succeeded in the recorded final acquisitions; TLS/section-selection diagnostics before them are not falsely counted as successful job retrievals. The shorter Felt heading required a selection minimum consistent with the existing 12-character citation minimum.

## Actual research jobs and diagnosis

All four jobs ended `partial`, with no terminal worker exception. This status accurately reflects unresolved knowledge; it is not presented as proof of success.

| Job UUID | Findings and outcomes |
| --- | --- |
| `a73da6e9-a9f9-42f3-943f-da87fe5d7941` | Four sources indexed. 12 entity + 9 relationship candidates, zero publications. Fictional plot assessments incorrectly set `in_universe=false`; this established the need for explicit story/publicity classification. |
| `df94c81e-85f4-4e0e-a734-5185c6bebd18` | Four vectors reused, zero generated. 12 entity + 11 relationship candidates; one event published. Alias evidence indexing and event/proper-name confusion still blocked useful endpoints. |
| `11ce3eee-718b-4192-9260-6e0661204cbb` | Eight sources: four reused vectors + four newly generated. After a reasoned downstream retry over frozen extraction: 13 active publication records, including four event publications and four unique participation edges. Five accepted relationship claims share those four edge IDs; counts are not inflated. |
| `3c750648-5aaf-47d7-a53c-96dcec6a7023` | Fresh same-objective execution: eight vectors reused, zero generated, zero new vector rows. Three character-reference publications reused existing IDs. One new intended-outcome event and its beneficiary edge were later explicitly retracted after evidence review. |

The third job accumulated 82 actual model attempts across its original run and one downstream retry, including 12 invalid identity outputs. The fresh repeat made 46 attempts, including eight invalid identity outputs. Bounded failures remain unresolved instead of becoming fake successful inference. A downstream retry did not reacquire or reindex documents; its original index counters remain historical. Full per-task usage is in the audit.

The third job's archive contains 12 entity and 19 relationship findings across original and rewritten retry claims, not 31 simultaneous independent discoveries. Its 13 active publication records leave 18 findings unresolved. The repeat archive contains 12 entity and 12 relationship findings; after correction only three character-reference publication records remain active. Reversed publications are retained separately from accepted findings.

The repeated objective did less embedding/network work, but **not less total inference work in every stage**. Re-extraction produced different candidates. Small-model repeatability and cross-source equivalence remain limited. The fourth job's pre-correction narrative snapshot is historical; the catalog read after correction was rebuilt from active publications.

## Actual accepted findings and evidence

The descriptions below are editorial paraphrases of the archived evidence, not copied model conclusions. Publication signifies passing evidence policy, not independent verification.

| Finding | Canonical UUID / supporting source |
| --- | --- |
| Subaru's summoning is a distinct occurrence; Subaru participates | Event `48d3c6b3-2ec4-5536-9360-fe31c42b8d93`; [TVmaze episode 1](https://www.tvmaze.com/episodes/660417/rezero-starting-life-in-another-world-1x01-the-end-of-the-beginning-and-the-beginning-of-the-end) |
| The attempted insignia purchase involves Subaru and Felt | Event `3eb1995d-d0b7-584f-abec-14af61be2a45`; [official episode-3 section](https://re-zero-anime.jp/tv/story/tv1r.html) |
| An earlier attack on Subaru is recounted in the second episode's synopsis | Event `9507722f-4ff0-5332-b670-97427f67ce42`; [TVmaze episode 2](https://www.tvmaze.com/episodes/677597/rezero-starting-life-in-another-world-1x02-reunion-with-the-witch); source position does not establish the occurrence happened in episode 2 |
| A girl's appearance and a surrounding encounter were also retained as event records | Events `78ecf3cb-cbf6-5287-94f8-ab11ef90bdde` and `c3d03c54-0b61-5606-9f68-83b883d41cf7`; no additional accepted participation is claimed for them |

Resolved references reuse Subaru `f974ad2b-7275-5dfa-8f3d-27bf2b40c03d` and Felt `4dd188d1-64a3-5cc7-a76c-ce4ae222a8f7`, including Subaru/Natsuki Subaru/Japanese references and Felt's bilingual heading. Emilia, Elsa, Satella and Rom candidates were assessed in the archive, but this report does not call their uncertain or stronger-policy-blocked comparisons accepted findings.

Four unique accepted edges:

| Edge UUID | Actual endpoints | Evidence source ID |
| --- | --- | --- |
| `22766faa-d07e-5750-8080-501d30c43cbb` | Subaru → summoning, PARTICIPATED_IN | `be6632a9-3e0f-5915-a0e6-61e6c4735bdd` |
| `3025d0c5-7baf-51ce-bd98-8d647e0a4063` | Felt → purchase attempt, PARTICIPATED_IN | `c46d5515-36c4-5481-a462-cec2135519cf` |
| `acbf9e6e-fdcc-5666-a8ca-38887080f279` | Subaru → purchase attempt, PARTICIPATED_IN | `c46d5515-36c4-5481-a462-cec2135519cf` |
| `2e0ff34d-8790-5dfb-80ad-dee847f111b9` | Subaru → recounted attack, PARTICIPATED_IN | `ff448fb7-73ef-514f-9caa-e94a602fd3a7` |

Each publication's audit entry includes source/passages, exact quote offsets, document hashes and endpoint IDs. For example the summoning uses passage `f20157f0-f05a-5c2d-aebe-b85cb4951376`, source `be6632a9-3e0f-5915-a0e6-61e6c4735bdd`. There are location, OCCURRED_AT, PRECEDES and CAUSE candidates, but **no newly accepted location, chronology, causal or lore link is claimed**. Translation ambiguity, unresolved endpoints and insufficient independent support remain visible in decisions. The evidence was not weakened to force those links through.

## Live correction and repeated execution

The fourth run initially published an intended future-protection goal as an occurrence and treated Felt as a participant merely because her future fate was mentioned. Review found this unsupported. Event `6b8ed70b-d582-5d02-8a98-7f9721552527` and edge `6e57d1ba-2b08-5da7-8157-50c4b9f41a44` were reversed using existing correction APIs. Publication records `bf02161a-7378-5867-beb1-6ccfbb340929` and `709cc38b-724a-5198-85f4-684dc48c42b5` retain their evidence and correction reason. This was an explicit review correction, **not autonomous error detection**.

The implementation now separates actual/intended/hypothetical/uncertain frames and actor/recipient/witness/mentioned roles, and publication rejects explicitly nonactual frames. A targeted real Ollama extraction over the same problematic archived episode-2 passage returned zero events/edges after the fix. This validates conservative omission for that passage. It is **not another complete workflow run**, and general role accuracy remains a limitation.

After correction, the repeated run introduced no additional canonical node/edge IDs. All pre-repeat milestone UUIDs remained stable. Replaying publication over the same frozen repeat state left these counts identical:

| Storage | Before and after replay |
| --- | --- |
| Source documents / passages | 16 / 16, including prior research archive |
| Passage embeddings | 8 |
| Canonical nodes / edges | 22 / 29 |
| Publication support records | 35, including prior research and reversals |

This proves deterministic storage replay. It does not prove that arbitrary new wording or another model run will always resolve semantically duplicate events. The original **15 nodes and 25 edges** were compared field-for-field to the stored baseline: no missing or modified originals. No seed reset was run.

## Retrieval and generated narrative

The real evidence API queried Subaru/Felt/insignia context and returned eight scoped archived passages using the actual 768-dimensional embedding model and pgvector. The first returned passage was `8ad71cf8-bee1-5feb-a7bf-28fb5ddb56cc`, the English episode-3 summary. The audit retains source IDs, URLs, hashes, offsets and finite cosine distances. Distances measure retrieval similarity, not factual confidence.

Catalog endpoint: `/api/universes/re-zero/narrative?continuity_id=7f3e5d50-2c7a-5bf7-942c-04094052a639&spoiler_position=3`.

Journey `ad7696ea-d4ba-5e0c-9100-e5156067bfa5` returns three available supporting-source milestones: summoning by source episode 1, a recounted attack by source episode 2, and the purchase attempt by source episode 3. Two other milestones remain unordered. Causes, consequences and location lists remain empty where accepted evidence is absent. Ambiguous within-episode ordering is explicit. This is a **partial source-boundary outline**, not a completed in-world timeline or certified first-reveal ordering. The existing frontend resolver accepted all references without issues. The UI still uses its existing provider; automatic API provider wiring is not included.

## Remaining limitations

- Unknown-universe discovery records navigational references; it does not autonomously adjudicate permissions/terms or promote source authority. No live SearXNG discovery or real Fandom/MediaWiki ingestion was demonstrated.
- Local 4B identity output still fails structured validation in some comparisons. Ambiguous translation/location/event matches are withheld. Cross-source event equivalence and useful precise occurrence labels need further work.
- Explicit role/actuality checks are model-assisted and conservative. The observed false positive required review and correction; a single targeted post-fix extraction is not a broad quality evaluation.
- The bounded eight-passage context and four event calls may omit useful source sentences. Retrieval uses a bounded exact pgvector scan, not large-corpus indexing/performance guarantees.
- No accepted new location/chronology/causality/lore relationship was demonstrated. Complete reader reveal order, historical-context links and mystery traversal were not established.
- No frontend provider wiring, image discovery, frontend redesign, advanced GSAP work, SSE, native LangGraph checkpointing or deployment was implemented.

Implementation milestones were committed and immediately pushed to `main`. The final documentation/audit commit is reported in the completion message rather than embedding its own unknowable hash here.
