# Increment 5.3 restriction audit

Objective: explain Subaru and Emilia’s relationship in the opening TV anime, using explicit actions, motivations where stated, and unresolved questions. Quality means an answerable, sourced account with meaningful connections, not more graph rows. Adaptation and spoiler boundaries remain explicit.

| Restriction before 5.3 | Purpose | Observed information loss | Decision |
| --- | --- | --- | --- |
| Registry permitted HTML still rejected unless its domain is in global host list | Retrieval authorization | Reviewed source permission cannot work on a newly discovered publisher | Replace this redundant host gate with exact current registry URL/continuity authorization; retain SSRF/redirect/DNS controls |
| Discovery-only SearXNG already accepts arbitrary public domains | Open navigation | Planner prefers `site:` on every query, hiding other categories | Retain open adapter; require broad and source-language queries, rank after discovery |
| SearXNG returns at most 8 metadata leads per query | Bound memory | Low-ranked useful references can remain unseen | Make query/result effort bounded by policy; preserve unfinished leads; avoid treating more results as quality |
| Only SearXNG supplies search results | Reuse infrastructure | Search throttling prevents alternative permitted structured discovery | Add permitted MediaWiki search and index links through existing registry adapters |
| Navigation-only and unverified media are excluded from ingestion | Permission/continuity integrity | Discovery cannot itself establish rights or adaptation | Retain; provide actionable source-access gaps rather than silently granting access |
| Fetch cap 500 KB; archive cap 12,000 characters | Resource safety | Full Q&A and articles lose later sections before embeddings see them | Separate bounded complete archive acquisition from inference context; retain byte/request/time ceilings |
| HTML flattened, headings/internal links/language discarded | Simple normalized offsets | No section hierarchy or link frontier survives | Retain normalized evidence text and add exact section offsets, links, language and provenance |
| No controlled rendered-document path | Small dependency surface | Permitted JavaScript documents have no usable text | Add an explicit controlled extractor with all network routed through existing pinned/robots-checked fetcher; never bypass denied pages |
| Complete source indexed in 1,400-character passages | Stable exact evidence | Arbitrary cuts can lose headings and local context | Preserve structure and section context alongside chunks; retain exact archived offsets |
| Fallback selects 8 passages / 4,000 characters in source order | Legacy caller bounds | Relevant later evidence loses to early unrelated text | Token-aware relevance selection; honest fallback when semantic retrieval is unavailable |
| Hybrid retrieval cap 16 hits, 3/source | Diversity | Long relevant source contributes too little context | Configurable token-aware selection with name, authority, section and independent-family diversity |
| Dossier 3,500-token default | Inference safety | A fixed context ceiling cannot scale to a deeper question | Depth-specific configurable policies; preserve explicit token budgets |
| Focused is the only policy depth | Bounded research | Quick and deep work share the same small ceilings | Add quick/focused/deep presets and request count; freeze effective policy per job |
| Max pass/query/document/global stage budgets | Cost/termination | Budget stop can be mistaken for subject completion | Retain hard ceilings; keep coverage and unfinished leads separate from execution success |
| No persisted canonical URL visit/depth tracking | No crawler | Useful linked references are never investigated | Extend existing indexed source registry with scoped link origin/depth and visited health; avoid domain crawls |
| Every new CHARACTER requires two publishers | Prevent false identity | One authoritative explicit character profile cannot establish even an ordinary direct fact | Claim-aware primary-evidence route; retain stronger proof for hidden identity, causal/disputed/interpretive claims |
| Source groups merge related publishers | Prevent inflated corroboration | Two official pages still count as one family | Retain; category diversity is not independence |
| Model entailment assessment | Semantic support | Both models accepted an unsupported species transfer in 5.2 | Require literal grounded direct-primary claims for reduced corroboration; retain negative controls and reject unsupported paraphrase shortcuts |
| Narrative builder runs after acquisition even with sparse coverage | Update read models | Model presentation spends budget before enough evidence exists | Separate deterministic projection refresh from optional synthesis; withhold inadequate recaps |
| Unknown reveal positions fail bounded reads | Spoiler safety | Unpositioned deep lore cannot enter opening-story views | Retain and report gaps; never invent first-reveal positions |
| Cloud permission per source, global opt-in and current read checks | Privacy | New discoveries cannot automatically use Groq | Retain; earlier approval applies only to the selected 5.2 dossier, not new benchmark content |

Before/after measurements, tests and real provider results will accompany the completed implementation. This audit is not a claim that all proposed fixes or the live acceptance benchmark already pass.

Core quality checkpoint: Ruff check/format and mypy passed; **195 backend tests passed**, including seven PostgreSQL tests using unique disposable schemas. New regressions cover long-form retention beyond 12,000 characters, structure offsets, clipped excerpt metadata, exact URL grants/revocation, depth-policy round trips, unsupported subject attribution, single-primary literal publication, hidden-identity withholding and rollback. A real broad Subaru/Emilia SearXNG query returned 25 results without upstream errors. Linked/browser/API discovery and the two-pass live benchmark remain in progress.
