# Increment 5 verification — 2026-11-14

The connected presentation pipeline is implemented and verified end to end. The real dataset remains incomplete: this is a partial guide with grounded entries, not a complete cohesive retelling. [Architecture](phase-3-increment-5.md), [actual API/database audit](phase-3-increment-5-demo.json), [file manifest](phase-3-increment-5-files.txt).

## 1. Architectural changes

Canonical evidence, deterministic organization and reader presentation are separate. Scope filtering precedes generation and traversal. English presentation uses referenced facts, established entity names, bounded schema repair, deterministic validation and a model entailment assessment. Model support is not independent corroboration. Indexed extraction copies exact archive sentences. GETs do not call models. The independent worker owns generation, budgets, cancellation and deadlines. Arc overview text is a deterministic assembly of already grounded sentences, with inherited provenance explicitly marked upstream.

## 2. Files modified

The [complete manifest](phase-3-increment-5-files.txt) lists changes from Increment 4 (`ec361ef`). Main additions are application knowledge contracts, organizer/composer/entry builder, presentation port/repository/model/migration, scoped API projections and rebuild endpoint, existing LangGraph/router integration, reader decoding and entry panel integration, focused backend/frontend tests and these reports. Existing frontend composition is retained.

## 3. Database migration and preservation

`30c500000005` adds only presentation persistence and scope indexes/foreign keys. Actual PostgreSQL upgrade/downgrade tests and `alembic check` passed. The audit compares the original graph snapshot field-for-field: all 15 original nodes and 25 original edges remain identical. Current graph: 24 nodes and 31 edges. No reset or reseed was used.

## 4. Supported knowledge categories

44 typed categories cover characters, places/regions/nations, organizations/factions/civilizations/species, objects/artifacts/weapons/items, books/documents/letters/diaries/inscriptions/records/newspapers/prophecies, lore/abilities/mythology/religion/culture, events/history/eras, arcs/episodes/chapters/quests/sequences/subquests/turning points/routes/loops/flashbacks, mysteries/hidden lore/foreshadowing. They use the existing graph types. Empty unsupported sections are omitted. Category support has owned-fixture tests; this does not mean real research discovered a book or every category.

## 5. Story organization

Identical anchored action spans and resolved participant contexts may group; UUIDs of all underlying events remain available. The two existing harassment extractions group without creating a new canonical event. Alternate routes, repeated occurrences and loop attempts are conservative boundaries. Supporting episode positions do not establish exact chronology or first reveal. Two ordering gaps remain; unordered events are retained. The guide is named “A partial story guide,” rather than assigning an invented official arc. Only explicit accepted causal edges can supply causes/consequences; none were fabricated here.

## 6. Before and after recaps

Earlier extraction-style or Japanese event labels now yield an English title only when grounded; otherwise readers see “Story account pending.” The Japanese official episode-one action about a girl appearing becomes “A girl appears before Subaru,” with its original source reference retained. A supported episode-two moment is “Natsuki Subaru's Resurrection Cycle,” with a longer source-grounded account of returning after an attack. “Elsa attacks them” is another accepted localized moment. A purchase recap with swapped actor roles was withheld. Proper names lacking a reliable English bridge were withheld.

The arc paragraph reuses three grounded sentences. It is not a fresh LLM retelling. The prose remains sparse, contains an ambiguous source pronoun, and is not a polished continuous recap. Two primary spine slots remain pending while other grounded moments remain unordered. These are visible limitations, not completed narrative quality claims.

## 7. Actual generated entries and research

**Natsuki Subaru**, canonical UUID `f974ad2b-7275-5dfa-8f3d-27bf2b40c03d`: English background states he is transported to a parallel world while returning from a convenience store. A history section describes the encounter with punks and the absence of the powers he expected. Japanese/English names and evidence are separately accessible; no invented age or affiliation is added.

Real job `4a4effa2-9d0a-4975-9577-917f870a51e9` used Ollama `qwen3.5:4b`, three model calls, and published assertion `6f917d71-5f90-546f-9afc-07965343e5e8` against the existing Subaru ID. Its overall status is partial because narrative coverage is incomplete.

**Return by Death**, canonical UUID `4948b221-369a-59a5-a943-9d4f443a7256`: definition and overview describe the source's returning-to-the-start ability. Real job `b63e55bc-5360-4e0e-937b-173f7059982a` used Ollama `qwen2.5-coder:7b`, three calls, and reused the existing lore node. Earlier lore attempts failed exact evidence checks and were not treated as discoveries. The entry is a narrow power definition, not deep world history.

These research jobs used existing permitted archived material and reused embeddings; they performed zero new source retrievals. Cached retrieval is real archived research input, not a newly fetched page. Curated seed content is not labelled agent-discovered.

## 8. Verified connections

The scoped API exposes accepted `PARTICIPATED_IN` edge `fea25aba-6435-5cec-9942-a508a21682b7` from Subaru to event `3cc13390-aa77-51a8-9fc0-38ab93aae46c`, with role recipient checked against actual event context. It supplies character-history traversal and preserves the journey bookmark. Merely being named in another event does not establish participation. No new unsupported causal, motive or event-to-power relationship was invented. Richer lore/event cross-references remain evidence-limited.

## 9. Evidence citations and API examples

Actual source references, passage hashes, quotation offsets and accepted relation UUIDs are in the [audit JSON](phase-3-increment-5-demo.json); source quotation bodies and prompts are omitted from that report.

- [Official episode accounts](https://re-zero-anime.jp/tv/story/tv1r.html): archived episode-one action and Japanese proper names.
- [Official character page](https://re-zero-anime.jp/tv/character/): selected Subaru profile section, not an unrestricted whole-page import.
- [TVmaze episode one](http://api.tvmaze.com/shows/14459/episodebynumber?season=1&number=1): English origin/background support.
- [TVmaze episode two](http://api.tvmaze.com/shows/14459/episodebynumber?season=1&number=2): Return by Death definition and episode recap.
- [TVmaze episode three](http://api.tvmaze.com/shows/14459/episodebynumber?season=1&number=3): Elsa action.

TVmaze material is handled under its registered CC BY-SA permission. Derivative source groups are not counted as independent corroboration. Official attribution URLs do not grant cloud sharing. No cloud inference was used.

Read examples, with the running backend on port 8000:

```text
GET /api/universes/re-zero/entries/f974ad2b-7275-5dfa-8f3d-27bf2b40c03d?continuity_id=7f3e5d50-2c7a-5bf7-942c-04094052a639
GET /api/universes/re-zero/entries/f974ad2b-7275-5dfa-8f3d-27bf2b40c03d/connections?continuity_id=7f3e5d50-2c7a-5bf7-942c-04094052a639
GET /api/universes/re-zero/lore?continuity_id=7f3e5d50-2c7a-5bf7-942c-04094052a639
```

The audit contains actual returned entry and relationship examples rather than hand-written synthetic responses.

## 10. Spoiler results

Unbounded entry index: 13 entries; episode-one boundary: six. Return by Death is excluded at episode one. Unknown source positions do not pass bounded reads. Source permissions and continuity are rechecked, including explicitly shared nodes. Scope changes clear old display content; graph/search/relations are pruned. A failed bounded request never silently uses broader curated content. Browser checks covered setting and clearing the boundary and restoring the journey bookmark.

## 11. Providers, usage and caching

Local Ollama `qwen3.5:4b` performed character extraction and presentation work; installed digest `d8b0f5e9760cd1682034f292d7ef72ec46f432149be0df7574bf2d6e92e38c04`. Ollama `qwen2.5-coder:7b` performed the successful lore research. Embeddings used `embeddinggemma:latest`, measured 768 dimensions, digest `85462619ee721b466c5927d109d4cb765861907d5417b9109caebc4e614679f1`. Groq remains configured through existing injection/routing but was not exercised. No credentials were changed or printed.

All diagnostic and demonstration runs in the audit total **169 actual model calls**, including failed/invalid outputs; this is not a count of successful findings. Individual jobs retain their budgets/deadlines and reservations. No resumed budget was replenished.

Current-policy artifacts: nine validated, four withheld for grounding, three withheld for names, five missing. Artifact statuses are separate from canonical factual publication. Repeated catalog responses have equal revision/content. Arc assembly job `ab6d8489-409a-4c4a-a696-598f2043cdd2` completed with zero calls; repeat `87723334-7ce4-4051-a141-cf96bebdb14f` reused its artifact with zero calls. Event-entry reuse job `0cca91b8-8812-4fe5-a428-66681fb5caa0` reused six inputs and materialized three event presentations with zero calls. These deterministic operations are not claimed as new LLM research.

## 12. Actual browser evidence

Production Next.js, real FastAPI/PostgreSQL and installed Chrome were used. A separate unmocked capture checked English overview, selected event, character history, lore entry, source boundary and bookmark restoration; page errors: zero. Screenshots were inspected, including the actual incomplete story state. No image discovery assets are implied.

- [Journey](phase-3-increment-5-journey.png)
- [Selected event](phase-3-increment-5-selected-event.png)
- [Character entry](phase-3-increment-5-character-entry.png)
- [Lore entry](phase-3-increment-5-lore-entry.png)
- [Episode-one boundary](phase-3-increment-5-spoiler-boundary.png)

Initial browser runs exposed source-control/header and panel overlap. CSS stacking and narrow-screen offsets were corrected; the final complete suite passed.

## 13. Executed checks

| Check | Final result |
| --- | --- |
| Backend `python -m ruff check .` | Passed |
| Backend `python -m ruff format --check .` | Passed, 109 files |
| Backend `python -m mypy -p src` | Passed, 76 source files |
| Backend `python -m pytest -q` | 160 passed, including seven opt-in PostgreSQL tests |
| Migration upgrade/downgrade and `alembic check` | Passed; no new operations |
| `npm run lint --prefix apps/web` | Passed |
| `npm run typecheck --prefix apps/web` | Passed |
| `npm run test --prefix apps/web` | 57 passed |
| `npm run format:check --prefix apps/web` | Passed |
| `npm run build --prefix apps/web` | Passed |
| `npm run test:e2e --prefix apps/web` | 11 passed, one opt-in live inference test skipped |
| Separate real research / production browser capture | Actual persisted jobs and unmocked browser verified as above |

Backend checks run from `services/intelligence` with the root venv. PostgreSQL tests explicitly target `universe_atlas_test` and unique schemas; they never fall back to the developer URL. Ordinary inference tests use identified fake providers. Legacy fallback browser cases deliberately force a 503; the synthetic job-control test is labelled synthetic. Live catalog and encyclopedia cases use real persisted API results. The skipped repeated-inference browser test is not presented as passed. Warnings: LangSmith deprecation warnings and Playwright NO_COLOR/FORCE_COLOR environment warning, with no failing final checks.

## 14. Known limitations

English generation with the installed small local model is unreliable for some material. Conservative withholding leaves visible holes; nine validated artifacts do not mean all entries are complete. Neither the arc nor major-milestone selection yet delivers a consistently rich, flowing reader experience. Source pronouns can remain ambiguous. A model entailment assessment can still err; it is not an independent verifier or proof of canon.

The real demo has a limited character profile and one narrow lore concept. Documents/books, deep history, affiliations, and fan theories are structurally supported/tested but not demonstrated as new real discoveries. No richer supported event-to-lore edge was available. Unknown order stays unknown; no fuzzy identity or invented chronology fills gaps. Language detection is conservative for Japanese/English/CJK, not a general multilingual classifier. Only English display is exposed.

The frontend preserves its current artwork, layout and controls; missing media remains an explicit placeholder. Image discovery, visual redesign, advanced GSAP, SSE, external authentication and deployment remain outside this increment. Local frontend, API and independent worker are left running for inspection. Further research and quality work are required before calling the narrative experience complete.
