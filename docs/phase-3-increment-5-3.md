# Increment 5.3 — deep acquisition implemented; connected research remains partial

Verified 2026-11-14. This is an execution report, not a claim that the autonomous encyclopedia acceptance benchmark passes. [Persisted run audit](phase-3-increment-5-3-results.json) contains job IDs, provider telemetry, frozen policies, evidence IDs/offsets, source hashes, retractions, and unfinished questions. [Information-loss audit](phase-3-increment-5-3-audit.md) records the constraints and changes.

## Working changes

- Open SearXNG navigation remains independent of retrieval permission. Exact current registry grants authorize new public URLs without duplicating a global domain allowlist. Redirects, public-IP/DNS pinning, robots, access challenges, current scope, cloud permission and rate limits remain enforced.
- Existing services now support permitted MediaWiki search metadata, relevant document-link discovery, persistent URL/depth tracking, and an explicitly enabled controlled Chrome extractor. Browser requests use the existing pinned reader; no login, challenge bypass, third-party traffic or private-network access. The real browser test uses owned material, not research evidence.
- Complete bounded documents are archived before token-aware inference selection. Structure includes source language, explicit numbered sections, definition headings, links and exact normalized offsets. Mixed novel/anime documents retain their complete archive but index only declared eligible sections. Old passages crossing upgraded section boundaries are excluded without destroying historical evidence IDs.
- `adaptive-v2` implements configurable quick/focused/deep ceilings. Effective policy, deadlines, reservations and unfinished questions persist per job. Page count is a ceiling, never a claim of sufficient coverage. Global limits can further restrict a job.
- Retrieval considers exact focal names, semantic similarity, section context, authority, source families, categories and token cost. Ordinary extraction stays local. The per-job `complex_event_reasoning` option uses the existing complex-task route and reserves capacity for downstream relationship analysis. It does not change global cloud extraction or export canonical user edits during identity resolution.
- Event/participant bundles retain endpoints, explicit occurrence status and roles. Research dossiers rank content rather than schema-key vocabulary. Optional relationship discovery can stop at its quota while already extracted claims still pass verification and publication checks.
- Ordinary literal named-subject primary claims can use one public primary source. Hidden identities, disputed interpretations and complex causality retain stronger requirements. Current registered permission is locked and rechecked during publication. Production opinions, incomplete speech fragments and hypothetical material are not ordinary story facts. Corrections use audited retraction.
- Presentation is gated by coverage. GET endpoints perform no inference. Frontend design, graph IDs, seed/user data and existing database functionality are preserved; no schema migration was needed.

## Actual live investigation

The initial benchmark investigated Subaru/Emilia in the opening anime. It returned shallow identity/episode material and no accepted relationship. We then investigated their original-novel relationship in a **separate light-novel continuity**, retaining the anime result as a regression. Later-volume material is not eligible for an opening-anime spoiler view.

The novel setup supplied an official navigation root and permitted path families, **not the exact Q&A article URL or the Ice Brand Arts finding**. Search and extracted links discovered eligible articles. The controlled provider comparison below subsequently selected a known relevant archived section; that operator selection is not autonomous discovery.

Examples of genuinely archived public sources:

| Source | Archived characters | Category / use |
| --- | ---: | --- |
| [Official Q&A 2193](https://re-zero.com/news/2193/) | 20,299 | Creator Q&A; declared novel sections only |
| [Official Q&A 2403](https://re-zero.com/news/2403/) | 33,256 | Creator Q&A; declared novel sections only |
| [Official Q&A 2517](https://re-zero.com/news/2517/) | 34,514 | Creator Q&A; declared novel sections only |
| [Official Q&A 2159](https://re-zero.com/news/2159/) | 9,176 | Creator Q&A, discovered during continuation |
| [Official Emilia profile](https://re-zero.com/character/%E3%82%A8%E3%83%9F%E3%83%AA%E3%82%A2/) | 216 | Character profile, found in final run |

These are different documents/categories from **one publisher family**, not independent corroborating publishers. The navigation index supplies links and no factual passages.

Model-generated research questions included the characters' explicit roles and collaboration, associated named abilities, official Q&A support, and actual events within the selected continuity. English and Japanese searches were generated. Broad results included dedicated wikis, Wikipedia, Reddit, reviews and other publishers; discovery did not automatically grant retrieval or cloud permission.

| Actual run | Sources in final context | Actual model attempts | Measured tokens | Retained new novel promotions |
| --- | ---: | ---: | ---: | ---: |
| Anime regression `f861c16f` | 12 | 18 | 79,953 | N/A; four supported updates to existing records, no new edge |
| Novel first run `d4d4781b` | 8 | 20 | 52,882 | 0 after one audited retraction |
| Same-objective continuation `b8805763` | 8 | 26 | 76,184 | 0 after one audited retraction |
| Complex-event continuation `e77f3a5e` | 6 | 29 | 87,567 | 0 after two audited retractions |

Attempts include provider failures; cache hits do not count as model calls. Tokens are measured returned usage, not a guarantee that failed/incomplete requests used zero tokens. Conservative incomplete reservations remain charged. These are sequential diagnostic runs with code corrections, **not a controlled before/after performance experiment**. They do not establish improved claims per call.

The second novel run recorded six archive reuse events and two newly archived sources. The final run acquired a different factual category, produced 19 candidates and reached verification after one bounded retry of the same frozen extraction. That retry retained its original deadline and consumed budgets. Six final-run candidates received supported model assessments, but this did not mean six canonical facts. No relationship passed publication. The job stopped on its token budget, leaving unassessed edges withheld.

Human quality review found author-production clauses incorrectly promoted as character facts, and an incomplete speech fragment. All four novel promotions across the three jobs were retracted through the existing audit API. Original evidence, decisions and retraction history remain. The graph is **27 nodes / 33 relationships**, matching the pre-5.3 snapshot. Historical coverage counters in the audit predate these retractions and must not be read as current canonical coverage. Fifty-four same-objective frontier leads remain persisted; no new novel recap was published.

## Real local / hybrid comparison

Both modes received the same exact archived section 16 of Q&A 2517, passage `e24409d2-c45f-5f9e-bc3d-b710198b8635`, content hash `952367677ee6d40abb193e1c82e996eeb377bfd531110445eb1e12f19b6ed23b`. The user approved all permitted public benchmark material for cloud processing. This comparison made no canonical writes.

| Mode | Actual provider / model | Calls | Wall time | Reviewed quality |
| --- | --- | ---: | ---: | --- |
| Local | Ollama `qwen3.5:4b` | 2 | 33.2 s | Valid citation IDs, but blurred which pair became master and knight; marked explicit statements uncertain; its verifier rejected the draft |
| Hybrid | Groq `openai/gpt-oss-120b`, primary credential | 2 | 6.0 s | Clearer roles and collaboration; valid citation IDs; added an unsupported design-collaboration interpretation that its verifier incorrectly accepted |

The latter interpretation remains unaccepted. These are model assessments, not independent verification. The production jobs additionally exercised real Groq verification/event reasoning and actual rate-limit fallback. No secondary key was used to bypass a rate limit.

A **reviewed, source-grounded example**, paraphrased from that dossier: after the fourth chapter, Emilia holds the master role and Subaru the knight role. Their collaboration includes Subaru devising Ice Brand Arts following consultation with Emilia; she then practices shaping weapons. The author's estimates of training time remain approximate. This is a controlled evidence example, **not a published autonomous recap**. It establishes neither reciprocal romance, hidden identity, detailed ability mechanics nor a complete relationship history.

## Checks and remaining gaps

Final backend: Ruff check and format check; mypy on 83 modules; **210 tests passed** with explicit disposable PostgreSQL test URL and installed-Chrome opt-in; Alembic found no new upgrade operations. PostgreSQL tests use unique disposable schemas and exercise migration upgrade/downgrade. No developer-volume reset. Existing LangSmith emits 13 deprecation warnings.

Frontend: lint, typecheck, **57 unit tests**, production build, and **11 end-to-end tests passed**. One explicit opt-in real-repeat research browser test was skipped. The bounded progress browser fixture is synthetic HTTP, not proof of live research quality. A generated Next development type-reference change was reverted.

Remaining acceptance failures are material:

- No retained new novel canonical relationship, named-lore entity, connected narrative or published cohesive entry. The comparison's useful Ice Brand Arts answer has not become an automatically published graph finding.
- Passage selection can still favor long author-production discussions or alias-rich profiles over the best relationship answer. Local extraction can hallucinate attributes, misbind roles or omit relevant named lore. Identity resolution and publication remain conservative, including unresolved English/Japanese name bridges.
- Per-candidate identity/verification costs and conservative reservations can exhaust the budget before connected bundles finish. The optional stage-quota correction prevents one failure mode; it does not solve overall budget allocation or persist partial verifier progress as a completed canonical bundle.
- SearXNG yielded real results but also upstream-unavailable events. A real MediaWiki metadata probe failed `source_tls_validation_failed`; TLS verification was retained. Dedicated-wiki restrictions and navigation-only leads are not permission to fetch or republish content.
- Functional MediaWiki and rendered extraction adapters have owned tests; unrestricted live wiki ingestion and a real JavaScript research source were not demonstrated. No image discovery, visual redesign or new future-agent placeholders were added.

The next useful milestone is selective, budget-aware extraction and verification of one complete focal relationship/lore bundle from the already archived evidence. Adding sources or agents without fixing this semantic bottleneck would not meet the quality objective.
