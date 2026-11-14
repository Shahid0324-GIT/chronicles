# Increment 5.1 verification — 2026-11-14

Focused bounded research and durable unfinished leads are operational. **The complete deep-research/product benchmark is not achieved:** Emilia coverage remains partial and the cohesive arc drafts were withheld. [Architecture/configuration](phase-3-increment-5-1.md), [actual persisted audit](phase-3-increment-5-1-demo.json), [changed files](phase-3-increment-5-1-files.txt).

## Root causes and fixes

The [diagnosis](phase-3-increment-5-1-diagnosis.md) traces the existing source → registry → retrieval → extraction → verification → promotion → narrative → encyclopedia flow. Key issues were discovery stopping after the first registry population; episode-centric discovery; official sources excluded from event calls; refinement disabled for registry jobs; small per-call windows treated as coverage; and no persistent questions.

Live execution also found and fixed excessive token reservation charging, planner override of initial encyclopedia focus, unchanged-document freshness never renewing, repeated attempts against blocked hosts, optional coverage-format failure discarding a completed execution status, a recent-600-passage retrieval ceiling, and an arc-name false positive on an ordinary English adverb. The final arc still failed grounding; that failure was not bypassed.

## Source strategy and real inputs

The saved profile identifies the original web-novel medium and keeps the current anime continuity separate from novel comparisons. It names relevant profiles, original-source references, publishers and categories without granting ingestion permission.

Registry before: eight entries, mostly episode guides. After: 13 entries across episode guides, official material, character profiles, chapter index, novel reference and dedicated wiki. Four additional references are **navigation-only**. They are not four ingested original sources or four corroborating publishers.

- [Official anime character source](https://re-zero-anime.jp/tv/character/): one new exact Emilia section, 154 normalized characters, ending before the next character heading. Its first-reveal position is unknown, so it is excluded from bounded reads. Earlier official Subaru/profile and episode material was reused/revalidated.
- [Official original-novel character reference](https://re-zero.com/character/): discovered as comparative metadata; no automatic ingestion or continuity merging.
- [Author web-novel index](https://ncode.syosetu.com/n2267be/): discovery metadata; the operator lookup returned HTTP 403. No bypass or chapter download.
- [Licensed publisher volume-one reference](https://yenpress.com/titles/9780316315302-re-zero-starting-life-in-another-world-vol-1-light-novel): lookup unavailable through the discovery tool; retained as navigation-only.
- [Dedicated wiki candidate](https://rezero.fandom.com/wiki/Arc_1): attributed candidate metadata; automated retrieval permission remains unresolved. No ingestion is claimed.

Autonomous SearXNG search was not configured. Operator discovery and engine-generated queries are distinguished in the audit. The engine did execute registry selection, permitted retrieval, indexing, extraction, identity/relationship analysis and publication. Actual retrieved categories were official, episode-guide and character-profile; novel chapters, manga and wiki articles were not retrieved.

Generated queries included a site-specific official Emilia/Pack query, a half-elf/Lugunica profile query, and questions about names, titles and bloodline evidence. Some local-model queries included irrelevant or mistaken domain variants. They were not silently presented as successful searches.

## Frontier and coverage

Eleven leads remain persisted as partially resolved, with evidence/source references, attempts and stop reasons. Questions concern companion spelling/aliases, titles, family or bloodline evidence and missing character connections. A bounded job does not imply complete subject coverage. Questions beyond the follow-up depth remain stored, and near duplicates preserve their variants. Future jobs using the same objective see this backlog.

The final focused single-pass outcome is `BUDGET_EXHAUSTED` for its pass allowance, with five relevant accepted facts, identity coverage, missing connection coverage, no material conflicts detected in that assessment and 11 pending leads. The reported two declared source families are not proof of independent corroboration. Coverage is an operational/model-assisted estimate; unknown order, unresolved identity and unavailable primary sources remain gaps.

## Actual runs and provider usage

All seven runs below called real local Ollama. Ordinary tests use owned fakes separately.

| Run | Calls | Reported tokens | Result |
| --- | ---: | ---: | --- |
| `5e50579a-03c6-44ec-9b14-5032029b7cd7` | 18 | 59,174 | Partial; over-conservative token reservation stop exposed and fixed |
| `77f9b9ca-0239-465d-8621-5bf9c983000d` | 32 | 115,023 | Failed optional coverage format after factual publication; indexed review/fallback subsequently fixed |
| `ba770168-bd3c-491b-8b3e-a6b27aab123a` | 3 | 12,978 | Partial single-pass coverage; some blocked-host attempts exposed |
| `88125ca9-62f1-4bcc-aea1-bae6db545086` | 2 | 10,107 | Partial repeat; archive/inference reuse, remaining blocked-host attempts |
| `cd3272c0-7a53-434f-91b0-cf921d938948` | 3 | 4,525 | Emilia English entry generated; arc withheld |
| `0622c7b5-8ca7-4eb0-975f-002c2b72710e` | 2 | 10,084 | Final protected repeat: zero source retrievals, six indexed passages reused |
| `06a5bccc-9c5a-4f71-914f-a0ea6aa16d86` | 2 | 1,892 | Arc-only retry withheld by grounding |

Total: **62 actual model calls and 213,783 reported tokens**, including unsuccessful diagnostics. This is not a count of successful discoveries. Each job retained its own bounded policy/deadline; no old budget was replenished. The final repeat used fewer calls than the preceding comparable single pass (two versus three), with an inference cache hit and zero source retrievals. This is a small local comparison, not a general performance benchmark.

Chat model: Ollama `qwen3.5:4b`, installed digest `d8b0f5e9760cd1682034f292d7ef72ec46f432149be0df7574bf2d6e92e38c04`. Embeddings: `embeddinggemma:latest`, measured 768 dimensions, digest `85462619ee721b466c5927d109d4cb765861907d5417b9109caebc4e614679f1`. One new passage/vector row was indexed; later unchanged passages/vectors were reused. No Groq/cloud inference, credential changes or key rotation occurred. Groq [retry-after/token-reset behavior](https://console.groq.com/docs/rate-limits) and privacy were tested with identified fake responses; no live 429 is claimed.

The runtime host policy excluded the previously registered TVmaze network URLs in this session. Earlier runs attempted them and were rejected; final selection records those access gaps before fetching. The allowlist was not relaxed. Existing permitted archived TVmaze evidence remained reusable locally under registry policy.

## Connected knowledge, citations and preservation

Graph before: 24 nodes / 31 edges. After: 26 / 33. All 24 original nodes and 31 original edges remain field-for-field identical. No reset, reseed, volume removal or adaptation merge occurred.

Two new source-anchored event records describe summoning and accompaniment. These are source-specific assertions, not proof of two previously unknown story occurrences; broader cross-source occurrence reconciliation remains incomplete. Existing Emilia identity was reused.

Accepted new relationships include:

- `81f3105f-3f07-55fe-89bc-5e0faef2de41`: Subaru `PARTICIPATED_IN` the source-anchored summoning event.
- `180542db-6fe0-516d-b340-43a2adadb099`: a source-assessed `PRECEDES` relation from summoning to the girl's appearance. This does not establish a complete chronology or first reveal.

These passed existing evidence/endpoint/publication checks. Model assessment is not independent verification. No new `CAUSED` edge, motive or unsupported Emilia–Puck relationship was manufactured. The specific Emilia connection facet therefore remains incomplete even though other relationships were added.

The [audit JSON](phase-3-increment-5-1-demo.json) contains actual canonical IDs, source references, passage IDs, normalized offsets, hashes, source ranking, queries, providers and frontier records. Quotation fields and prompts are omitted. Actual read examples:

```text
GET /api/universes/re-zero/research/profile
GET /api/universes/re-zero/research/frontier?continuity_id=7f3e5d50-2c7a-5bf7-942c-04094052a639
GET /api/universes/re-zero/entries/a13997f9-a7a5-5468-85dc-130e52b12db3?continuity_id=7f3e5d50-2c7a-5bf7-942c-04094052a639
GET /api/universes/re-zero/entries/f974ad2b-7275-5dfa-8f3d-27bf2b40c03d/connections?continuity_id=7f3e5d50-2c7a-5bf7-942c-04094052a639
```

## Before/after measurements

| Indicator | Increment 5 baseline | Increment 5.1 observation |
| --- | --- | --- |
| Registry entries | 8 | 13; four additions are navigation-only |
| Retrieved source categories represented | Official / episode guide | Official / episode guide / character profile |
| Canonical event records | 12 | 14; source-specific occurrence identity remains conservative |
| Canonical relationships | 31 total | 33 total; two added, no new causal edge |
| Citation completeness in this run's published rows | Not a matched-objective baseline | 12/12 published rows have evidence; seven distinct target/description pairs |
| Pending questions | No durable frontier | 11 persisted partial leads |
| Comparable single-pass repeat calls | 3 before the final repeat | 2 in the final repeat |
| Final repeat network acquisition | Not measured comparably in Increment 5 | Zero source retrievals |
| Coherent arc presentation | Isolated-sentence assembly | Grounded synthesis attempted but withheld |

Across all diagnostic calls, seven distinct published target/description pairs divided by 62 calls is about 0.113; these include support for already known entities, not seven novel discoveries. Net graph additions are four records (two nodes and two edges), about 0.065 per diagnostic call. These numbers do not demonstrate a general efficiency or presentation-quality win over Increment 5: objectives differ, and failed diagnostics are included. The concrete demonstrated improvements are durable gaps, source-aware selection, a sourced character entry, bounded outcomes and repeat reuse. Original-source research depth remains limited.

## Before/after presentation quality

Increment 5 assembled isolated validated sentences into a partial guide. Increment 5.1 has a separate dossier-based model synthesis path with scoped names, indexed fact references and entailment checks. **The actual new arc drafts did not pass.** The reader uses neutral partial-guide text instead of presenting rejected synthesis as coherent or verified. No successful cohesive recap is claimed.

The real Emilia entry is more substantive than a bare extracted label: it describes her half-elf appearance, the official profile's personality description, and her catlike spirit companion. It retains four evidence references and omits unsupported biography fields. The new profile's unknown reveal boundary is fenced from narrower reads. It is still a short introductory entry, not a complete biography.

## Browser and tests

Production Next.js, actual FastAPI/PostgreSQL, the independent worker and installed Chrome were used. The unmocked capture verified the partial guide, selected moment, Emilia profile, source-reference controls and restored journey bookmark; page errors: zero. Screenshots were inspected:

- [Actual journey](phase-3-increment-5-1-journey.png)
- [Selected event](phase-3-increment-5-1-event.png)
- [Emilia entry](phase-3-increment-5-1-encyclopedia.png)

| Executed check | Result |
| --- | --- |
| Backend Ruff check / format check | Passed; 117 files formatted |
| Backend mypy | Passed; 81 source files |
| Backend pytest with explicit `_test` PostgreSQL URL | 177 passed, including seven opt-in PostgreSQL tests |
| Actual migration upgrade/downgrade | Passed in unique test schemas |
| Local `alembic upgrade head` / `alembic check` | Passed; no new operations |
| Frontend lint / typecheck | Passed |
| Frontend unit tests | 57 passed |
| Production frontend build | Passed |
| Complete Playwright suite | 11 passed; one opt-in repeated-inference test skipped |
| Separate live research and unmocked browser capture | Executed as recorded above |

Tests include durable leads, beyond-depth persistence, query diversification, medium/continuity/access selection, source families, byte reservations, pre-call token rejection, old-evidence retrieval beyond the recent window, current cloud policy revocation, unchanged-source freshness, scoped dossiers, isolated synthesis cache and legacy pipeline behavior. Existing promotion, relationship, causality, inference fallback and privacy tests remain passing. LangSmith deprecation and Playwright color-environment warnings remain non-failing observations. No mocked test is counted as real research.

## Remaining limits

The full deep-research acceptance benchmark remains unmet. Original chapters/books and wiki material were not ingested; autonomous web discovery needs SearXNG configured. Sparse permitted evidence and local-model output quality still prevent a grounded cohesive arc and richer Emilia relationship history. Source-level unknown reveal positions remain fenced. Full global contradiction inventory, learned information-value estimation, automatic profile identification for every medium, general multilingual name reconciliation and account-wide persistent cloud quota scheduling are not established by this run. Frontier value/cost ranking uses simple heuristics.

Existing per-call extraction/frame/context limits still apply. They are resource controls, not claims of exhaustive extraction; the frontier carries unfinished work. Lexical candidate windows are bounded and older unindexed evidence may rely on lexical matching until targeted indexing. Related but differently worded objectives are not automatically the same research task. The archive is incremental, not an unlimited crawler.

The current frontend, database and local services are preserved and left running. Image discovery, visual redesign, advanced animation and deployment remain outside scope.
