# Increment 5.4 — connected evidence, atomic publication and recovery

Verified on 2026-11-15. The existing LangGraph workflow now investigates a specified relationship using reusable evidence bundles, publishes supported connected knowledge transactionally, and builds reader explanations from accepted clauses. No agents, crawlers, deployment, image discovery or frontend redesign were added.

[Observed failure trace](phase-3-increment-5-4-diagnosis.md) records the reproduced 5.3 path. [Actual run audit](phase-3-increment-5-4-results.json) contains real job IDs, evidence offsets/hashes, canonical IDs, frozen budgets, provider attempts, negative controls and remaining questions. Fake-provider tests are separately identified below.

## What changed

| Component | Change |
| --- | --- |
| `application/relationship_contracts.py`, `research.py` | Typed investigation subjects, hypotheses, bundles, atomic assertions, verification and publication state. `relationship_subjects` enables this path; supplied aliases are query candidates, not identity proof. |
| `application/evidence_bundles.py`, `retrieval.py`, `ports/retrieval.py`, `persistence/evidence_index.py` | Rank concrete connecting actions above name mentions; count aliases as alternatives; include neighboring passages within the same explicit section. Keep exact source IDs, document revision, normalized offsets, language, authority, publisher family and current permission identity. Existing exact-name/pgvector retrieval supplies candidates. |
| `application/connected_extraction.py` | Compile connected subject/action/object assertions into existing entity/event/edge contracts. Explicit joint clauses survive model omission. Directly involved companions and named lore remain, while irrelevant mentions, guessed pronoun substitutions and nonactual actions do not become participation. |
| `application/identity.py`, `orchestration/knowledge_pipeline.py` | Preserve unique scoped IDs, supported bilingual/name-order bridges and exact event anchors. Exclude irrelevant zero-evidence identity candidates; retain unresolved matches. Targeted cross-field repair is bounded and charged. Completed identity steps persist against exact candidate/catalog/evidence fingerprints. |
| `domain/atomic_evidence.py`, `application/atomic_verification.py`, `promotion.py` | Separate compound assertions; bind subject, predicate, object and direction literally before semantic assessment. Batch compatible atoms with independent verdicts. Recheck atomic binding in the publication transaction, alongside existing evidence, scope, endpoint, contradiction and source-policy checks. |
| `application/research_budget.py`, `research_policy.py` | Per-stage call/token ledger; configurable verification reserve (default 35%); preserve unknown reservations and original job deadlines. No credential rotation or budget replenishment. |
| `persistence/research_repository.py`, `ports/research.py`, `research_workflow.py` | Reuse the existing job checkpoint/frontier, rather than adding tables or a new job system. Persist each completed extraction, identity step and atomic assessment. Continuation checks current evidence, permission, scope and related contradiction context before reusing work. |
| `evidence_dossier.py`, `knowledge_presentation.py` | Remove archive navigation metadata from inference dossiers while retaining citations/revisions. Select distinct accepted actions before duplicate representations. Include accepted direct relationships in character dossiers. Compose from published atomic clauses, not every assertion in their longer source quotations. Withhold incomplete coverage or role conflation; bounded repair and full grounding still apply. Cached withheld output stays marked partial. |
| `apps/web/tests/e2e/atlas.spec.ts` | Follow the selected backend ID when viewing all continuities. Two Emilia labels across distinct adaptations are legitimate, not duplicate canonical identities. Product UI is unchanged. |

No schema or dependency changes were needed. Repositories do not commit, network/model calls remain outside archive transactions, and graph writes still pass through `CanonicalGraphPromotionService`.

## Diagnosis verified against actual evidence

The 5.3 job retrieved the relevant passage but ranked it fourth for three extraction calls. Its identity model saw irrelevant catalog entries; per-candidate verification repeatedly included the entire selected dossier. The run ended with no retained novel relationship after audited retractions.

Additional measured bottlenecks were corrected during 5.4:

- Whole-document section/link metadata made each reader fact cost approximately 3,200–3,450 estimated tokens, although that metadata was unnecessary for prose. The 3,500-token selector retained one fact. Compact evidence now retains four or five facts across the relevant atomic actions under the same limit.
- The model omitted a literal joint-role clause and guessed a name for a pronoun. Generic literal joint-clause extraction recovers the former; the latter stays unresolved.
- A model chose an unrelated character or an invalid event target index. Scoped name evidence and bounded repair correct candidate selection without forcing a semantic merge.
- Early reader drafts conflated joint roles or copied source Q&A text. The current `grounded-english-v11` policy invalidates those earlier artifacts. Reader inference receives only accepted atomic clauses, and summaries cannot silently assign both joint roles to one person.

## Real Subaru–Emilia demonstration

The benchmark reused the permitted public [official author Q&A, section 16](https://re-zero.com/news/2517/). This is later-novel material, scoped to light-novel continuity `4bea70af-22a3-57ae-8010-d55be5e15bd3`; it is not merged into the opening anime.

Evidence bundle:

- Source ID: `75b99b73-acf8-5c33-a961-ff9907908bd4`.
- Archived document hash: `952367677ee6d40abb193e1c82e996eeb377bfd531110445eb1e12f19b6ed23b`.
- Anchor passage: `e24409d2-c45f-5f9e-bc3d-b710198b8635`, normalized document offsets **13779:14596**.
- Bundle ID: `d50a82b9-809d-58b1-bf2d-35b79ba231f3`.
- Complete context and original-language evidence remain archived; inference uses bounded selected material. One publisher family supplies these direct ordinary claims, not multiple independent corroborators.

Three distinct, source-bound interactions were accepted automatically:

1. Emilia and Subaru establish a master/knight relationship.
2. Subaru and Beatrice begin magic training.
3. Subaru creates the named technique Ice Brand Arts.

These are represented by **seven new nodes and eight new edges**, not fifteen unrelated discoveries: three characters, one lore concept, three actual events; three direct connections and five participation edges. Each successful run has fifteen active claim-to-graph support records. The overall graph grew from **27 nodes / 33 edges** to **34 nodes / 41 edges**. Existing scoped records remained intact.

Rejected/unresolved examples:

- Replacing the source's pronoun with Emilia in a consultation assertion: insufficient literal name binding.
- Treating a spoken intention or an author-production clause as a completed event.
- Turning an incidental dialogue string or a generic facility phrase into a character/entity without adequate grounding.
- Unsupported species, reversed creator/creation direction, hidden identity, motivation, affiliation and causality. Owned regressions also verify that a fake supporting model cannot override deterministic rejection.

The actual Groq negative-control call accepted the supported creation assertion and rejected three deliberately unsupported controls: a species attribution, reversed invention direction, and an identity equation. Python independently rejected those three. The control call made **no canonical writes**.

## Publication, recovery and repeated runs

| Real diagnostic run | Actual model attempts | Returned measured tokens | Active support records | Outcome |
| --- | ---: | ---: | ---: | --- |
| `2ea40307` | 8 | 12,381 | 3 | Useful technique connection; joint clause/identity gaps found |
| `6937cce5` | 9 | 17,641 | 7 | Joint clause recovered; irrelevant identity shortlist found |
| `0a54121a` | 10 | 12,570 | 15 | Connected publication; initial reader drafts subsequently superseded |
| `c67f6ae1` | 7 | 12,098 | 15 | Stricter reader role checks withheld drafts |
| `cda524e5` | 6 | 12,943 | 15 | Reader-summary correction; broader quotation leakage identified |
| `fcc08f31` | 9 | 13,736 | 15 | Current policy: one validated entry, one withheld draft |
| `91aa53bf` | **1** | **4,474** | **15** | Stable API-submitted repeat: only planning used a model |

These are bounded diagnostic iterations with code corrections, not a controlled throughput experiment or repeated downloading of more sources. Attempts include provider/schema failures; token totals are returned usage, not a claim that unknown failed calls consumed zero tokens. Conservative incomplete reservations remain charged. Earlier artifact validation does not override the current presentation policy.

The stable repeat reused archived evidence, connected extraction, exact identity matches, completed atomic assessments, and both reader artifact statuses. It made **no identity, extraction, verification or presentation model calls**. The complete API graph node/edge snapshot was identical before and after the repeat. Reaffirmed claim support records do not create duplicate graph entities or edges.

Partial recovery is demonstrated separately with **owned fake-provider tests**, not described as live research: verification is interrupted after one atomic interaction; that complete interaction is published, completed assessments and pending work are persisted, and a fresh bounded job verifies only the remaining two. The original job's allowance/deadline is never reset. The same tests verify graph idempotency and current-context invalidation.

The real early diagnostic jobs also retained their supported technique findings and incomplete identity work; later continuations reused that evidence/extraction/assessment state to complete the connected publication. The deliberately forced budget interruption itself is a test, not a claim that a live provider exhausted that allowance.

## Providers and reader output

Actual production calls used local **Ollama `qwen3.5:4b`**, local **EmbeddingGemma/pgvector**, and eligible **Groq `openai/gpt-oss-120b`**. Identity and routine work stay local. The public source's existing cloud permission and global setting were checked. Real rate-limit/schema failures exercised bounded repair and Ollama fallback; no secondary credential was used to evade a rate limit.

The current Emilia entry is validated, cited English prose covering the joint role relationship and the associated named technique. Its cross-references come from accepted graph relationships. The separate Subaru draft covers the three interactions but remains **`withheld_grounding`** after provider fallback. It is not shown as validated just because it reads plausibly.

Consequently the final repeated job is honestly **partial for reader output**, while its bounded relationship investigation has fifteen accepted support records, no pending atomic verification, and sufficient evidence for the available explanation. Thirty-six broader frontier questions remain; neither topic coverage nor a complete story chronology is claimed.

## Executed checks

- Backend Ruff check/format, mypy (**89 modules**), **239 tests passed** with explicit disposable PostgreSQL and installed-Chrome opt-ins, and `alembic check` with no new upgrade operations. PostgreSQL tests exercise migration upgrade/downgrade and concurrency safeguards in unique test schemas. No developer-volume reset.
- Frontend lint, typecheck, **57 unit tests**, production build, and **11 browser tests passed**. One explicit opt-in repeated-research browser test was skipped. Browser verification initially exposed the same-label/across-continuities test assumption; the corrected test follows the actual selected ID and the full browser suite passed on rerun.
- Owned tests cover bundle ranking/context/offsets, multilingual identity versus co-occurrence, related-entity retention, compound decomposition, negative attribute transfer/direction/participation, contradictory context, one-primary publication, protected budgets, immediate partial persistence, continuation, idempotency, privacy/rate behavior and grounded reader composition.
- Thirteen existing LangSmith deprecation warnings remain. The browser progress fixture uses synthetic HTTP; the optional repeated-research browser case is not the live worker demonstration above.

## Remaining limits

Literal argument binding and joint-clause recovery support a deliberately bounded predicate grammar. Rich pronoun resolution, free-form motives, disputed historical causality and full multilingual narrative reconciliation can still remain unresolved. A query alias is never an identity proof. The real benchmark uses English evidence; multilingual bridge demonstrations are owned tests.

One reader entry remains withheld. Model entailment is not independent verification, and the safeguards are conservative rather than a proof that all semantic errors are impossible. Ordering positions remain unknown where the source does not establish a usable boundary; events are not placed into inferred broadcast chronology. Research breadth, source access, image discovery, visual design and choreography were not expanded.
