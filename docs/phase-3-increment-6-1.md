# Increment 6.1 — evidence-backed story reconstruction

Implementation and real benchmark: 2026-11-16. Baseline: `7873bf3`. The user subsequently authorized committing this milestone and pushing it to `main`. Deployment remains outside scope.

## Result and limits

Romance Dawn now has three reader-facing verified segments sharing Luffy: Shanks saves Luffy; Luffy and Koby arrive at a naval base; Luffy recruits his first crewmate, Roronoa Zoro. Each has archived evidence, accepted assertions and a validated milestone presentation. These are discoveries from selected public secondary commentary, **not ingested original manga or a complete reconstructed arc**.

The important reconstruction result is **three verified segments, two unexplained transitions, zero accepted precedence links and zero causal links**. Chapter-source boundaries 1, 3 and 7 support a reading arrangement, not first-reveal guarantees, in-world chronology or an explanation of how one event leads to another. A shared Luffy thread makes these segments connected and explorable without manufacturing their transitions. The full story-context objective remains partial.

The graph grew from two nodes/zero relationships/one event to six nodes/five relationships/three events. The existing arrival UUID `dd6117bb-b626-5ead-b888-0ae7ac12c265` was reused when Luffy's participation was accepted. The other events are `541a9375-7b31-5d93-8de8-d094dfc95dee` (rescue) and `1e3c5f5d-1c55-529b-afd3-345bd56a2e12` (recruitment). Luffy and Shanks are accepted characters. Koby and Zoro remain unresolved as canonical character identities under the current independent-family policy; their names remain in licensed action assertions. No Orange Town research was started.

## Existing pipeline strengthened

The workflow now runs an evidence-backed reconstruction service after publication and before prose generation. It reuses the existing organizer, knowledge scope, canonical assertions, relationship graph, presentation dependencies, persisted job checkpoints and research frontier. There is no additional agent, schema migration or frontend rewrite.

The reconstruction projects exact event groups, actual participant roles, explicit locations, actions, supported state/relationship assertions, source boundaries and accepted event links. State and lore connections require an assertion actually tied to the event; a second assertion sharing the same character edge cannot leak into it. Mere mentions do not become actual participants. Unavailable locations and outcomes stay absent.

Explicit source descriptions of major story segments are archived with passage IDs, revisions, exact offsets and permission fingerprints. They are labeled `reference_description_not_canon`. Current source/section permissions and revisions are checked again on reads. The benchmark review describes three parts: the origin, departure/Koby background, and recruitment/Morgan conflict. The first two remain unverified outline coverage; the third is only partially supported by the accepted recruitment assertion. The rest of a quotation is not automatically published.

The narrative catalog exposes `reconstruction` and per-arc `reconstructions`, including segments, transitions, character threads, reference outline, gaps and measured coverage. The reader has an expandable progression disclosure. Partial milestones remain usable while an arc draft is unavailable. GET requests perform no inference.

Missing-transition questions are persisted before presentation inference. A real bounded continuation investigated the dynamically generated rescue-to-arrival gap, using names found in the existing arrival evidence. It recovered Luffy's joint participation in the original arrival event, but **did not establish the missing transition or causation**. Unfinished leads and previous failures remain in the frontier.

Other fixes include medium-aware source ranking, independent eligible literal corroboration, preserving distinct assertions, middle-initial sentence handling, grounded identity proposals, current-claim identity rebinding, exact binding across any supporting quotation, a single charged complement repair, joint coactor verification, all-bundle cloud permission checks and excluding resolved frontier questions. Verification caches are versioned when their input contract changes. Budgets/deadlines are never replenished on old jobs.

Arc synthesis now receives a balanced dossier containing licensed events from each segment and only accepted transition links. Its current policy is `grounded-story-v2`. Deterministic checks reject temporal or causal bridges across unexplained transitions even if a model approves them. An older artifact containing “later … then” is preserved for audit but is ineligible for current publication. Failed grounding remains withheld, with diagnostic reasons retained. Generic sentence starters do not become invented-name errors.

## Actual source evidence

| Source | Selected material / result |
| --- | --- |
| [Uchiha Luffy chapter 1](https://uchihaluffy.com/chapter-1/) | Key Events section; rescue support, manga chapter 1 |
| [Healthy Dose of Anime chapter 1](https://healthydoseofanime.blogspot.com/2018/10/one-piece-chapter-1-review-romance-dawn.html) | Selected story text before comments; independent rescue support, manga chapter 1 |
| [Uchiha Luffy chapter 3](https://uchihaluffy.com/one-piece-chapter-3/) | Existing selected arrival commentary; current run adds actual Luffy participation without duplicating the event |
| [Aaron Ngo chapters 1–7](https://www.aaronngo.com/blogthread/2021/2/5/one-piece-east-blue-saga-romance-dawn-arc-chapters-1-through-7-manga-review) | Selected summary before personal commentary; recruitment and noncanonical reference outline; boundary 7 is not an exact occurrence chapter |

There are seven archived documents total, including the earlier official volume metadata, Binder introduction and Grandline index. Those three are not additional narrative witnesses. Uchiha chapters 1 and 3 share one publisher family. The official volume summary extends through chapter 8 and stays excluded from the chapter-7 reader. The three newly selected sections received the user's explicit cloud opt-in; unrelated sources did not.

Original manga ingestion remains unavailable through the inspected permitted readers. Fandom/other robots failures, reader shells and TLS/access failures are source limitations, not successful retrieval. No access restriction was bypassed. SearXNG discovery was exercised; some jobs retained discovery-unavailable diagnostics and reused eligible archives rather than pretending new retrieval occurred.

## Audit and verification

The [machine-readable audit](phase-3-increment-6-1-results.json) retains every real run, provider usage, failed/partial outcomes, canonical records, exact source references/offsets, frontier questions, promotion decisions, presentation artifacts and chapter-1/chapter-7 API projections. The [baseline diagnosis](phase-3-increment-6-1-baseline.md) records the prior bottlenecks. Groq uses `openai/gpt-oss-120b`; Ollama uses `qwen3.5:4b`, with local embeddinggemma retrieval. Cache reuse and deterministic tests are not real inference calls. Returned token totals exclude unknown usage on invalid/error responses; incomplete reservations remain retained.

Owned deterministic tests cover atomic publication, identity, corroboration, repair bounds, source revocation, role filtering, balanced reconstruction, temporal rejection, source-order/causality separation and incremental reader propagation. The mandatory propagation test exercises workflow → canonical publication → presentation regeneration → FastAPI → Next.js → installed Chrome without manually inserting reader content. It is fixture-based verification, separate from the real One Piece browser screenshots.

Across all eleven attempts, including diagnostics and the failed finalization, this increment recorded **99 actual model calls and 157,993 returned tokens**: Groq 41 calls/65,339 tokens; Ollama 58 calls/92,654 tokens. Health checks with `model_call=false` are excluded. This is not a demonstrated overall cost reduction over the 98-call baseline; the extra reconstruction work and failed drafts are included rather than cherry-picked. There are 76 persisted frontier records, including earlier naming variants and unfinished questions; that is not 76 answered questions.

| Real job prefix | Status | Calls | Returned tokens | Result / diagnosis |
| --- | --- | ---: | ---: | --- |
| a040a036 | partial | 2 | 2,812 | Passage ranking missed the rescue action |
| ff5d6b9f | partial | 6 | 10,269 | Incorrect fanfiction assessment; missing human continuity/source context fixed |
| 6a2f1055 | partial | 21 | 29,041 | Rescue and character publication; quotation-order binding fixed before bounded promotion retry |
| 10ba4a38 | partial | 2 | 6,049 | Recruitment complement omitted; literal binding rejected it |
| d1399a9e | partial | 21 | 26,429 | Bounded complement repair; recruitment and Luffy participation published |
| 84860b96 | partial | 18 | 34,350 | Missing-transition investigation; joint coactor misclassification diagnosed |
| 76495d02 | partial | 18 | 24,583 | Existing arrival reused; Luffy role published, transition still unknown |
| 3885cb75 | partial | 2 | 8,516 | Unsupported simultaneity in arc draft withheld |
| 985ddee0 | failed | 4 | 4,908 | Missing coverage-outcome finalization defect fixed; obsolete unsafe-order artifact excluded by policy |
| 346df085 | partial | 1 | 3,303 | Generic sentence starter falsely treated as a name; draft withheld |
| f25737cc | partial | 4 | 7,733 | Current partial arc presentation validated; transient Groq health failures and charged local repair retained |

The current partial recap reads: “Shanks saves Luffy. Luffy and Koby arrived at a naval base, which was controlled by Marine captain Axe-Hand Morgan. Luffy recruits Roronoa Zoro, establishing Zoro as his first crewmate.” This is model-written prose licensed by the accepted dossier. It remains a short multi-event overview: **a cohesive explanation of the complete story and its transitions has not been achieved**. The reconstruction disclosure explicitly states that source boundaries do not prove narrative order, chronology or causation.

| Executed check | Result |
| --- | --- |
| Backend `python -m ruff check .` / `ruff format --check .` | Passed; 143 files formatted |
| Backend `python -m mypy -p src` | Passed; 94 modules |
| Backend `python -m pytest -q --tb=short` | **269 passed**, 13 upstream LangSmith/Python deprecation warnings |
| Backend `python -m alembic check` | No new upgrade operations |
| Frontend `npm run lint --prefix apps/web` | Passed |
| Frontend `npm run typecheck --prefix apps/web` | Passed |
| Frontend `npm run test --prefix apps/web` | **60 passed**, 9 files |
| Frontend `npm run format:check --prefix apps/web` | Passed |
| Frontend `npm run build --prefix apps/web` | Passed, including production TypeScript |
| Frontend `npm run test:e2e --prefix apps/web` | **13 passed, 1 skipped**, installed Chrome |
| `git diff --check` | Passed |

The backend used the root venv, explicit `TEST_DATABASE_URL` ending in `_test`, unique PostgreSQL test schemas and `CHRONICLES_TEST_BROWSER=1`. The mandatory fixture test passed publication, reader regeneration and incremental enrichment through Chrome. No schema/dependency changes or volume resets were made. The first final backend run encountered a stopped PostgreSQL service (265 passes, one connection failure, three setup errors); the recovered complete run passed. Existing containers and API/web servers were restarted with their data preserved. No continuous research worker was started. Playwright's NO_COLOR/FORCE_COLOR warning is environmental.

## Browser evidence

All four current captures were inspected at 1920×1080. Story moments, entry content, source links, chapter filter and progression disclosure are usable. Artwork remains honestly uncatalogued; visual redesign/image discovery is deferred. Existing historical fixture images were preserved.

- [Before: Increment 6.0 real One Piece reader](evidence/increment-6-0/real-one-piece.png).
- [After: three real researched moments](evidence/increment-6-1/real-one-piece.png).
- [Reconstruction: supported thread and unexplained transitions](evidence/increment-6-1/real-reconstruction.png).
- [Recruitment entry with exact archived evidence and graph connection](evidence/increment-6-1/real-one-piece-entry.png).
- [Chapter-1-fenced Luffy entry and Shanks connection](evidence/increment-6-1/real-character.png).

Remaining gaps include the origin/departure outline segments, rescue-to-arrival and arrival-to-recruitment transitions, canonical Koby/Zoro identities, accepted event locations/outcomes, state progression, conflicts and deeper lore. These remain research questions, not inferred canonical content. Unknown order remains unknown; no accepted relation currently explains why one benchmark event causes the next.
