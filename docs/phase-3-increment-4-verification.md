# Increment 4 verification — 13 November 2026

The research-to-atlas path was demonstrated with real public sources, Ollama inference, local semantic retrieval, automatic publication, PostgreSQL-backed narrative generation and the production frontend in installed Chrome. The result is **partial story knowledge**, not independently verified fictional canon. No seed fixture or fake inference output is presented as research. See the [quotation-free actual audit](phase-3-increment-4-demo.json), [diagnosis](phase-3-increment-4-diagnosis.md), [architecture/runbook](phase-3-increment-4.md) and [file manifest](phase-3-increment-4-files.txt).

## Executed checks

| Check | Result |
| --- | --- |
| Backend Ruff | Passed |
| Backend format check | 100 files already formatted |
| Mypy | Passed, 70 source files |
| Backend pytest with explicit PostgreSQL test URL | **137 passed**, including seven PostgreSQL tests |
| Actual Alembic upgrade/downgrade integration | Passed in unique test schemas |
| `alembic current` | `2694c0a70004` head |
| `alembic check` | No new upgrade operations |
| `pip check` | No broken requirements |
| Frontend ESLint/typecheck/Prettier | Passed |
| Frontend unit tests | **53 passed**, eight files |
| Next production build | Passed, including narrative and limited research proxy routes |
| Ordinary Playwright suite against real services | **10 passed**, one explicitly opt-in real-inference test skipped |
| Opt-in real research Playwright test | **1 passed**, approximately 4.7 minutes; creates a real job, reloads the page, follows the persisted job, refreshes the atlas |
| Final production UI/source-provenance screenshot check | Passed; actual API revision and milestone references checked, **zero page errors** |

Backend commands ran from `services/intelligence` using the root venv. PostgreSQL tests used an explicit `TEST_DATABASE_URL` ending in `universe_atlas_test`; fixtures created unique schemas and cleaned up only those schemas. Default unit tests use SQLite or fake repositories/providers. The full verified run above includes the opt-in PostgreSQL tests. Actual Ollama runs are separately identified below and are not unit-test fixtures.

Seven PostgreSQL tests cover migrations/API preservation, concurrent publication, shared-support rollback, real pgvector queries/dimension separation, model-lease coordination and concurrent cache upserts. Focused new tests cover six event states, beneficiary roles, promotion enforcement, explicit publicity/location rejection, unique-alias event matching, repair prompts, typed redacted diagnostics, retry termination, cached-context/model-revision separation, task/job budgets, interrupted-call reservations, persisted deadlines and telemetry.

Frontend checks cover generated retrieval/decoding, complete curated fallback, malformed responses, cancellation, stable milestone/branch refresh, graph refresh without scope reset, generated-edge isolation, origin checks, job initiation, summary validation and versioned scoped session restoration. Legacy browser cases explicitly select the curated fallback; separate integration cases use the actual backend catalog. The small synthetic HTTP control test is labeled synthetic and is not included as real research evidence.

The suite prints 13 upstream LangSmith/Python-3.14 deprecation warnings. Playwright prints the environment's NO_COLOR/FORCE_COLOR warning. An initial cold browser navigation timed out, then recovered using the existing tab. Browser checks exposed an unbound native fetch and a local-origin proxy rejection; both were fixed and the production flow passed. Frontend formatting initially flagged an existing transport-union layout; it was formatted without changing vocabulary. No final check failures remain.

## Migration, environment and provider use

Applied migration `2694c0a70004` adds only the validated inference-cache table and timestamp index. Existing PostgreSQL/pgvector data and developer volume were retained. Upgrade/downgrade was exercised; no database reset, reseeding or runtime `create_all` was used. No new dependency was installed and neither dependency lock changed.

All real model calls used **Ollama `qwen3.5:4b`**. Semantic retrieval used **`embeddinggemma:latest`**, measured at **768 dimensions**, installed digest `85462619ee721b466c5927d109d4cb765861907d5417b9109caebc4e614679f1`. The existing versioned passage index was reused. **Groq was not used**; all three existing Groq environment values and local environment files were preserved. Cloud-content sharing remains disabled. Local model work stays sequential under the shared PostgreSQL lease.

The final services were left running locally: FastAPI on 8000, the production frontend on 3000 and the independent research worker. New UI jobs are queued in PostgreSQL and depend on that worker; they do not execute inside a browser request. Nothing was deployed.

## Real source acquisition and semantic retrieval

The focused objective concerned the original introductory anime episode 1: summoning, the immediate street encounter, direct participants and any supported in-world location, while withholding unsupported intentions, chronology and causality. All three jobs used the same objective and source ceiling 1.

Two existing permitted registry entries were selected, not newly discovered by an agent:

| Source | Archived source UUID | Notes |
| --- | --- | --- |
| [Official first-season episode-1 synopsis](https://re-zero-anime.jp/tv/story/tv1r.html) | `63d644ac-6513-5385-94d5-d02fb7590a7c` | Exact bounded Japanese episode section, primary authority |
| [TVmaze episode-1 summary](https://www.tvmaze.com/episodes/660417/rezero-starting-life-in-another-world-1x01-the-end-of-the-beginning-and-the-beginning-of-the-end) | `be6632a9-3e0f-5915-a0e6-61e6c4735bdd` | Public API, page ID 660417, secondary/derivative summary |

The diagnostic worker used a zero-hour source cache to perform two real network acquisitions. Both documents were unchanged, so their stable document IDs and two embeddings were reused. The repaired and final repeat workers used the normal source cache: zero network reacquisitions, two source documents and two embeddings reused, zero generated vectors. Each workflow performed actual semantic/lexical retrieval over those scoped archived passages. The final audit also includes a real evidence-API query with source IDs, hashes, offsets, provenance and cosine distances, omitting source bodies.

TVmaze API access retains the previously documented public-HTTP transport limitation, CC BY-SA attribution and original episode URL. TLS verification was never disabled. The official and derivative summaries are conservatively grouped as one underlying publisher family; they do not inflate independent corroboration. Later/unpositioned registry entries were excluded by the episode-source ceiling. Existing accepted aliases were reused; no later biography was ingested to force a name match.

## Actual jobs, failures and measured repair

All three jobs ended `partial` with no terminal worker error. Their actual IDs and measurements are:

| Job | Model calls | Cached extraction responses | Validation failures / repairs | Unique links accepted by that job |
| --- | ---: | ---: | ---: | ---: |
| `bea5eae3-976d-46ba-93e5-6292fa2b3f18` — diagnostic, started in the UI | 18 | 0 | 3 / 2 | 0 |
| `8fd5bc32-b319-45ec-a70a-831942b3b49b` — repaired typed participant contract, started in the UI | 36 | 0 | 0 / 0 | 2 |
| `9cc9e81c-68de-4d5f-99e2-9aed9e68c0f6` — production-browser repeat | 34 | 2 | 0 / 0 | 1, reusing an existing edge |

The diagnostic extraction populated participant names but left the separate role dictionary empty. Strict materialization withheld participation rather than guessing roles. Typed `{name, role}` entries fixed that schema mismatch. Redundant cross-field identity validation caused the three root-level failures; the equivalent deterministic unresolved-target check remains in the resolver without redundant provider retries.

The repaired run performed one planning, two extraction, nine identity, one relationship and 23 verification calls. The repeat performed one planning, eight identity, one relationship and 24 verification calls; both extraction results were reused. The two runs took approximately 322 and 278 seconds respectively, including job overhead. Different successful/unsuccessful semantic assessments still occurred despite identical extracted frames. These measurements demonstrate bounded reuse and fewer redundant extraction calls, **not a deterministic or universally more accurate model**. The 18-call diagnostic did less useful work, so fewer calls alone would be a misleading success criterion.

Default job budget was 48, with the configured task limits. The final repeat used all 24 permitted verification calls and stayed below its total budget. No cloud fallback was needed. Later hardening persisted incomplete call reservations and the absolute deadline; restart/expiration enforcement is covered by focused tests. The live jobs completed within their deadline and did not deliberately crash or time out. The final deadline and transaction-ownership cleanup was tested without running another full inference job.

## Source-backed findings and canonical changes

The following are editorial paraphrases of the retained source evidence. Actual claim IDs, exact evidence offsets/hashes, decisions and publications are in the audit.

- The official introductory synopsis describes Subaru being harassed in the street and then being beaten. Distinct action spans were retained as events `3cc13390-aa77-51a8-9fc0-38ab93aae46c` and `56769ce6-f699-50fe-8515-9640345429d5`.
- Subaru participates as the **recipient** of the street harassment. Edge `fea25aba-6435-5cec-9942-a508a21682b7` connects existing Subaru `f974ad2b-7275-5dfa-8f3d-27bf2b40c03d` to event `3cc13390-aa77-51a8-9fc0-38ab93aae46c`.
- The repaired run also published Subaru's participation in the girl's appearance scene. Edge `83aa89f1-7390-515e-bb22-7406f5cecf20` connects the same Subaru to existing appearance event `78ecf3cb-cbf6-5287-94f8-ab11ef90bdde`. The typed frame did not establish a named Subaru role for that scene; the stricter final role constraint withheld new support for it on the repeat. Its earlier support record is retained, not presented as a newly verified witness role or a causal claim.
- Japanese and English Subaru references reused that existing character UUID. The appearance event also reused its existing UUID. No duplicate character was created to manufacture endpoints.

Across this increment, the graph changed from 22 nodes / 29 edges to **24 nodes / 31 edges**: two distinct source-anchored event records and two participation edges. The final repeat added **zero nodes and zero edges**. Multiple support claims for an existing edge remain separate audit records; the UI summary now deduplicates canonical discoveries and the accepted-link count uses unique IDs.

The original curated **15 nodes and 25 edges** were compared field-for-field to the stored baseline: none was missing or modified. All pre-repeat milestone IDs remain unchanged, including milestones outside the ordered representatives. No duplicate relationship fingerprint `(source, target, type, continuity)` exists in the final graph.

No new location, affiliation, chronology, causal, revelation or lore relationship is claimed as accepted in this demonstration. A proposed causal link was disputed because sequence did not establish causation. Missing endpoints, unsupported comparisons, role ambiguity and stronger source requirements remain noncanonical. The repeat's one accepted link does not revoke the repaired run's separate earlier supported edge; support history is preserved rather than overwritten by a later model response.

## Backend narrative and production UI proof

Journey `ad7696ea-d4ba-5e0c-9100-e5156067bfa5` is read from the backend catalog, not a curated fixture. It exposes **three source-boundary representatives and five unordered milestones**, with ordering gaps visible. Its first displayed event is the researched street encounter; the character branch shows Subaru with the recipient role. Existing later-source milestones remain available because the atlas is showing its accepted continuity catalog; the research form's ceiling bounds new research, not the viewer's entire pre-existing archive.

Cause, consequence and location panels remain empty where no qualifying edge exists. Supporting episode labels do not assert exact in-world order or first reveal. The larger art/design system is unchanged; new events honestly use the existing uncatalogued-artwork fallback. No image-discovery agent or fabricated art provenance was introduced.

The browser checked the actual same-origin narrative response revision and milestone IDs, the generated availability indicator, selected-event details and accepted character branch. A real job was created through the form, the page reloaded while work continued, session restoration resumed following the same job UUID, and its partial summary appeared. The atlas was then explicitly refreshed. The final screenshot check restored only that known real job ID to exercise the same persisted-session read path; it mocked no API responses and ran no additional research.

Screenshots from the production frontend:

- [Generated story spine](phase-3-increment-4-generated-spine.png)
- [Selected researched event](phase-3-increment-4-selected-event.png)
- [Accepted participation and role](phase-3-increment-4-relationships.png)
- [Real completed research summary](phase-3-increment-4-research-summary.png)

The final capture recorded zero browser page errors. UI polling uses persisted summaries, not a fake progress producer. Existing curated fallback, graph exploration, lore detours, keyboard navigation, reduced motion and narrow-viewport browser cases also passed.

## Remaining limits

- Semantic assessments still vary between runs. Zero parser failures does not establish semantic correctness; mistaken actuality/roles and cross-source identity remain possible. Evidence gates and correction history remain necessary.
- Some event labels remain literal Japanese action fragments. Translation, editorial polishing and artwork were deliberately not invented to improve presentation.
- Reported/nonactual candidates are withheld; automated corroboration that upgrades reports to actual events is not implemented. Cross-source event matching remains conservative.
- No newly accepted chronology, location or causal/lore links were demonstrated. The existing analyst supports their vocabulary, but a complete story understanding has not been established.
- The spine shows available source-boundary representatives. The API retains unordered milestones; detailed UI navigation for all unordered events and certified first-reveal order remain unfinished.
- Polling replaces SSE. It pauses after bounded failures/time; Check status resumes it. Session restoration works within the browser session. Cross-session job history, notifications and automatic background atlas updates are not included.
- Live unknown-universe discovery/Fandom permission evaluation remains outside the demonstrated path; these runs used the existing permitted registry.
- No visual redesign, image discovery, advanced GSAP work, external authentication or deployment was performed.

All implementation milestones were committed and immediately pushed to `main`; the final completion message reports the final commit hash.
