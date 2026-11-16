# Increment 6.0 — research-to-reader integration

Verified implementation and partial live benchmark, 2026-11-16. Changes were initially held locally; the user subsequently authorized committing and pushing this milestone to `main`. Deployment remains outside scope.

## Reproduced pending-content failures

The existing Re:Zero light-novel catalog returned **zero journeys and three unordered accepted events**, all titled `Story account pending`. This was not evidence that the canonical graph was empty. The catalog required a current validated reader artifact and overwrote accepted assertions with an undifferentiated placeholder. The frontend discarded unordered milestones entirely, and both its provider and resolver required at least two ordered steps. A generated empty catalog also fell through into the free graph after loading.

Relationship jobs selected focal character resources for rebuilding, leaving their event/milestone/arc dependencies out. A later live One Piece job exposed another instance: a published non-focal location was excluded by the subject-name presentation filter. These are software defects, distinct from inaccessible sources or inadequate research coverage.

Changes preserve accepted assertions, expose actual presentation states, retain unplaced events without inventing chronology, allow one valid milestone, show generated empty/partial reader states, and rebuild resources affected by published targets. Milestone cache dependencies include accepted adjacent relationships; arc dependencies include eligible current child artifacts. GETs do not infer. Completed research controls refresh the existing graph/provider flow, preserving stable reading IDs and bookmarks.

`before-pending.png` captures the original backend placeholder output exposed by the initial unordered-event UI fix. It is a diagnostic intermediate baseline, not a screenshot of the fully unchanged 5.4 UI. The initial loading-only screenshot was discarded as uninformative.

## Manga configuration and scope

`python -m src.infrastructure.persistence.configure_one_piece` idempotently creates research configuration, not story seed content. It preserves an existing matching universe/profile and refuses a conflicting universe identity. Original manga, anime, films and games are never assumed equivalent.

- Universe: `db33dec2-5da5-53f2-9a1f-d43009d50dba`.
- Original manga continuity: `9110bdd8-a094-570f-827b-ad75793989cd`.
- Romance Dawn research scope: chapters **1–7**, an attributed reference segmentation, not an invented canonical arc fact.
- [Chapter index supporting that segmentation](https://grandlinewiki.net/eastbluearcM.html).
- [Official volume 1 index](https://one-piece.com/comics/o1/index.html) covers chapters **1–8**. The volume is not silently equated with Romance Dawn.

`manga-chapter` coordinates are distinct from `broadcast-presentation`. Unknown/mixed coordinate systems fail closed in bounded reads. Chapter evidence can establish a supporting source boundary; it does not establish every event in the chapter, within-chapter chronology, first reveal, or causality. Arc configuration has its own cited scope and actual manga-continuity validation. The existing API query and compatibility field `episodeLabel` are retained, but manga readers receive chapter wording. Other media use neutral source wording where appropriate.

## Live source feasibility and autonomous research

Real SearXNG queries returned relevant references. The existing policy-enforcing adapters, source registry, normalized document archive, embeddings, frontier and worker were used. Search snippets were not promoted as evidence.

| Source | Access/result | Role |
| --- | --- | --- |
| Official One Piece volume 1 page | Readable Japanese textual summary and index | Selected manga summary archived; conservatively bounded through chapter 8, therefore excluded from the chapter-7 reader |
| Uchiha Luffy chapter 3 commentary | Readable selected textual sections | Secondary evidence, with source limitations and unsupported claims withheld |
| Binder Pirates volume 1 reference | Readable selected Luffy/Zoro introduction metadata | Introduction/reference evidence, not a comprehensive story account; manga/anime mappings kept distinct |
| Grand Line Wiki manga index | Readable Romance Dawn subsection | Navigation/index only; chapter titles are not evidence of chapter events |
| One Piece Fandom arc page | Adapter returned `robots_unavailable` | Navigation only; no bypass |
| Wikipedia and the inspected alternative wiki | TLS validation failed | Not ingested; TLS verification was not disabled |
| Official VIZ chapter reader | Only a short HTML shell was available to the text adapter | No full manga page ingestion or claims inferred from its chapter title |
| Official English distributor page | HTTP acquisition failed | Reference retained; not imported through an alternate channel |

An additional chapter-reference inspection did not produce substantive early story prose and exposed later card metadata; that metadata was not added to the early reader. Unauthorized scan sites discovered in search were not ingested.

The first bounded job retrieved sources but extracted no candidates. Actual stored model calls returned empty event frames. Diagnosis found introduction metadata consuming an event slot before concrete action text. Generic action ranking now prioritizes concrete occurrences over alias-rich/index passages; it supplies no verification or chronology by itself. A continuation produced candidates but exposed withheld character identities, unsupported/conflicting relationship claims, and a grounded location. Adjacent source context for a pronoun-led event is now retained only under a narrow single-focal-actor rule; competing antecedents remain unresolved and semantic/publication guards still apply.

Automatic approval review initially rejected reusing the earlier Re:Zero cloud opt-in. The user subsequently explicitly approved the two selected public One Piece sections (chapter-3 commentary and introduction-reference metadata). Only those two registry entries became cloud-allowed. Later runs used real Groq `openai/gpt-oss-120b` and local Ollama `qwen3.5:4b`, with local EmbeddingGemma/pgvector retrieval. Groq rate limits were respected with local fallback, without credential rotation.

The paused job retained its original deadline and terminated as `partial / job_duration_exceeded` after resuming; a fresh bounded continuation did not replenish the old job. That continuation published an arrival event but failed in presentation storage: an introduced policy identifier exceeded the existing 40-character column. Compact versioned identifiers now fit the actual ORM column, with a regression test and no schema change. A production-worker rebuild then generated the location entry and partial arc recap, while withholding two drafts. GETs still perform no inference.

Legacy accepted assertions now constrain presentation input too: a longer archived supporting quotation does not license extra attributes in reader prose. Original quotations, hashes and offsets remain available as citations. This removed unaccepted descriptive embellishments from the location account.

## Mandatory fixture-based end-to-end verification

`tests/test_reader_propagation.py` is mandatory, with no opt-in skip. It uses owned synthetic Mira/Ron/Taro text and an explicitly fake inference provider in isolated SQLite. It runs the actual workflow, identity resolution, verification, transactional canonical promotion, presentation builder, FastAPI HTTP server, Next.js routes/provider/store and installed Chrome through Playwright. It inserts no canonical nodes, relationships or presentation artifacts by hand.

The test starts with an empty One Piece test configuration, publishes three synthetic interactions, checks validated partial arc/milestone output, opens a participating character, follows a supported connection, returns to the reading bookmark, and publishes a new synthetic action in a second job. The reader updates from three to four accepted events and retains the existing character ID and selected milestone; exactly one new event node is added. Screenshots are explicitly named `fixture-*` and are **not real One Piece research**.

The real-source Playwright case separately reads current One Piece API results, checks manga scope and absence of pending placeholders, opens the actual researched entry and its citations, and captures `real-one-piece*.png`. It does not substitute fixture content for a sparse benchmark.

## Visual review

Desktop captures use 1920×1080 and are inspected as images. The first fixture screenshots showed unplaced events displacing the main journey below the fold; that list was moved below the reading section. Stable publication-age selection keeps a new unplaced event from replacing the existing representative milestone; publication age is a UI selection policy, not story chronology. Body and encyclopedia prose were increased to readable sizes and long evidence text wraps. No artwork discovery or overall redesign was performed.

## Acceptance boundary

The software propagation path is verified with clearly identified deterministic fixtures. Real Romance Dawn coverage remains partial and must not be described as a complete reconstructed arc. Missing original-source access, sparse permitted references, model limitations and withheld identities/events are reported separately. Orange Town remains unopened.

## Actual reader content and graph

The chapter-7 bounded catalog contains one chapter-3 milestone and two encyclopedia entries, from real archived commentary evidence, with no manually inserted canonical content:

| Record | UUID | Current presentation |
| --- | --- | --- |
| Marine base courtyard (LOCATION) | `a6735b0c-c971-522d-8918-d82cf17fbfc0` | Validated entry: a character is shown tied to a post in the courtyard; no identity is inferred from the pronoun |
| arriving at a naval base (EVENT) | `dd6117bb-b626-5ead-b888-0ae7ac12c265` | Accepted arrival assertion and citation remain visible; expanded prose is withheld for grounding |
| Romance Dawn reader scope | `757483a7-667c-5caf-9e49-64f6d8772839` | Validated partial arc introduction and overview; one actual milestone, not invented minimum steps |

The partial recap reads: **“Luffy and Koby reach a naval base controlled by Axe-Hand Morgan.”** This is grounded secondary-reference coverage, not independent confirmation from ingested original manga. There are **zero accepted One Piece edges**. Luffy/Zoro identities, recruitment, causal links, broader lore, theories and a cohesive multi-event arc are not demonstrated. Sixteen unfinished frontier leads remain persisted.

The arrival citation is archived source `255333fa-631b-5110-9d04-8a79db2d3f31`, passage `7905bdc4-f12e-594f-935b-cd4b45a51388`, passage-local offsets `0:159`, normalized document offsets `0:342`. The location's action evidence uses passage `44c8331b-7f0d-5151-9b43-a9dc08804e89`, passage-local offsets `134:219`, normalized document offsets `847:1571`. Current revision hash: `14bec65ff018265c67242b44d56a90690b936cbcd519bc06e91a3c67efea3034`. Distinct evidence spans from the same document remain separate; citation deduplication no longer drops the action span.

All seven jobs, generated questions, exact source scopes, candidate/publication decisions, provider calls, reader artifacts and frontier records are in [the actual-run audit](phase-3-increment-6-0-results.json). Failed and diagnostic runs are retained, not relabeled successful. Their combined recorded provider usage is 98 calls and 149,158 returned input/output tokens; failed calls can have zero returned usage, so this is not a billing total. The final production rebuild (`ac359631-2f7e-4358-b5c5-2fd4dc365ef9`) is partial, with 8 calls / 8,035 returned tokens, two generated artifacts, one reused artifact and two withheld drafts.

## Executed checks

Backend commands ran from `services/intelligence`, using the root virtual environment:

| Command | Result |
| --- | --- |
| `..\..\.venv\Scripts\python -m ruff check .` | Passed |
| `..\..\.venv\Scripts\python -m ruff format --check .` | 140 files formatted |
| `..\..\.venv\Scripts\python -m mypy -p src` | Passed, 93 modules |
| `..\..\.venv\Scripts\python -m pytest -q` | **249 passed**, 13 existing LangSmith deprecation warnings |
| `..\..\.venv\Scripts\python -m alembic check` | No new upgrade operations |
| `npm run lint --prefix apps/web` | Passed |
| `npm run typecheck --prefix apps/web` | Passed |
| `npm run format:check --prefix apps/web` | Passed after formatting the edited CSS |
| `npm run test --prefix apps/web` | **59 passed**, 9 files |
| `npm run build --prefix apps/web` | Passed, including production TypeScript validation |
| `npm run test:e2e --prefix apps/web` | **12 passed, 1 skipped**; installed Chrome, real local API |
| `npm run test:e2e --prefix apps/web -- one-piece.spec.ts` | Passed again after clarifying accepted-event/account coverage wording |
| `git diff --check` | Passed |

The full backend run explicitly set `TEST_DATABASE_URL` to a disposable database ending in `_test` and `CHRONICLES_TEST_BROWSER=1`. PostgreSQL tests create unique schemas, upgrade/downgrade actual migrations and remove only their test schemas. The mandatory propagation test independently uses file-backed temporary SQLite and its own HTTP/Next ports. No developer volumes or existing graph data were reset. No schema/dependency changes were required.

After the full suite, the mandatory propagation test passed again with its checkpoint assertion strengthened to inspect the **second enrichment job**, rather than the first job. Ruff and mypy were rerun successfully. The final coverage-label change was checked in the live One Piece Chrome case, lint/typecheck and a second successful production build.

The first sandboxed async/backend and npm checks stalled and were stopped; identical checks completed outside the restrictive sandbox. An earlier production build hit a Turbopack CSS-worker panic; clearing only verified generated production cache directories (preserving `.next/dev`) resolved it. The final production build passed twice. These tool/runtime issues are distinct from research/source limitations.

## Browser evidence

All captures are 1920×1080, inspected as images. The pending-content baseline is the intermediate diagnostic described above; current Re:Zero data has since gained an accepted event, so the comparison is not a frozen database snapshot.

- [Before: pending prose hiding accepted knowledge](evidence/increment-6-0/before-pending.png).
- [After: accepted assertions and honest unresolved ordering](evidence/increment-6-0/after-pending.png).
- [Real One Piece partial reader](evidence/increment-6-0/real-one-piece.png).
- [Real location entry and distinct exact evidence spans](evidence/increment-6-0/real-one-piece-entry.png).
- [Owned fixture before research](evidence/increment-6-0/fixture-before.png).
- [Owned fixture after three accepted interactions](evidence/increment-6-0/fixture-after.png).
- [Owned fixture after fourth interaction with bookmark preserved](evidence/increment-6-0/fixture-enriched.png).

Artwork remains explicitly uncatalogued. The coverage counter distinguishes accepted events from validated event accounts; a separately validated arc overview does not inflate milestone-account counts. Full visual redesign and image discovery remain deferred.
