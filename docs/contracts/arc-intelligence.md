# Backend arc artifacts — Increment 6.2 checkpoint

Increment 6.2.1 adds a section `development_plan` to the existing dossier. It includes exact archive coordinates and provenance, scoped clause references, action modality and negation, unresolved context, and separately assessed factual, structural and editorial stages. `reference_presentation` orders anchors within a source. Chronology, revelation, causation and prerequisites use distinct relations and require explicit support. Chapter ceilings continue to govern eligibility.

The worker saves development-plan decisions independently of prose. An unavailable or blocked plan withholds the section before any composition call. An eligible pending review can reuse a draft that already passed deterministic checks for the matching section revision. Reader-facing artifacts exclude pending prose. The fixed archive benchmark and its measured outcomes are documented in the [controlled reconstruction report](../increment-6-2-1-controlled-benchmark.md).

This is an additive backend contract. Frontend integration is deliberately absent.

`GET /api/universes/{slug}/arcs/{arc_id}?continuity_id={uuid}&spoiler_position=7`

Optional repeated `allowed_source_id` restricts sources. Omit the boundary for full-lore eligibility. Unknown arc/continuity pairs return 404. A missing or stale dossier returns `status: pending`, `dossier: null`, `article: null`; GET performs no inference. Current evidence and permission revisions are checked before returning stored prose.

`dossier` is a validated `ArcDossier`: stable arc/section IDs, provisional plan status, source range, perspective, accepted assertion references, editorial facet assignments, per-section coverage, reconstruction and revision. Facet assignment is not canonical publication or proof of causation. Research status, missing facets and presentation readiness are separate. The current real dossier is partial; these structures do not demonstrate complete narrative understanding.

`article` is a separate `ArcArticle` artifact: section headings, paragraphs with exact fact references, coverage, perspective and dossier revision. Its status is `withheld` when no section is validated, otherwise `partial`. No complete-arc state is currently asserted. Withheld drafts expose no paragraph prose. Historical model-approved artifacts do not override current revision/policy eligibility.

Organization must account for every accepted input assertion in a section assignment or in `organization_omissions` with its fact IDs, reason and explanation. This exposes excluded duplicate, incomplete, unrelated or context-poor assertions. Omission reasons and editorial connections remain provisional model assessments; they are not canonical facts or a completeness certificate. Missing accounting fails the bounded organization repair instead of silently losing developments.

Research commands opt in with `arc_id`. A `presentation_only` arc command can reuse accepted evidence without supplying new sources. `retry_withheld_presentations` explicitly retries withheld sections; unchanged validated sections are reused. Existing short narrative and encyclopedia endpoints remain compatible. The independent worker and existing budgets remain mandatory.

`arc_section_keys` limits work to existing provisional section keys. Optional `presentation_source_ids` limits dossier facts, reconstruction and article composition to the named archived sources; `null` means all eligible sources and `[]` means none. It does not grant retrieval or cloud permission. Source-bounded artifacts have separate cache identities and never fall back to broader prose. Only the provisional section plan may be reused from the broader view. Read the matching artifact with repeated `allowed_source_id` query parameters, or export it with repeated `--allowed-source` arguments. `extraction_source_ids` separately selects primary extraction material from the job's acquired sources; other acquired material remains available for corroboration.

Paragraphs contain individually cited `claims`. Their displayed `text` and paragraph-level `fact_ids` are computed from those claims. Model input supplies claims only. Legacy representations are accepted only when their duplicated text and references agree exactly. Semantic review still checks each claim against its own accepted assertions, including roles, modality, sequence and causation, and must pass owned adversarial qualification cases. Model approval is not independent source verification or a claim of whole-arc completeness.

A qualified semantic rejection permits one bounded revision with the same assertions and the review's concrete `coherence_issues`. Fresh validation and review are mandatory afterward. `assessment.review_attempts` retains the original and subsequent verdicts, including when a later inference fails. A model/provider change requires reviewer requalification. Unchanged validated sections remain reusable; GET performs neither revision nor inference.

After that revision, a faithful/coherent draft with mixed claim verdicts may propose one partial projection that drops rejected/uncertain claims without adding text. It preserves paragraph structure and drops empty paragraphs. Publication requires a fresh complete claim/coherence review of that projection; failure leaves prose withheld. `assessment.partial_projection.removed_claims` retains original review indices and reasons. This does not mark the section or arc complete. A failed reviewer qualification never permits projection or publication.

Export current backend artifacts without inference:

```powershell
..\..\.venv\Scripts\python -m src.export_arc --universe db33dec2-5da5-53f2-9a1f-d43009d50dba --continuity 9110bdd8-a094-570f-827b-ad75793989cd --arc 757483a7-667c-5caf-9e49-64f6d8772839 --through 7 --output ../../docs/evidence/increment-6-2/romance-dawn.md
```

The sibling JSON retains the dossier and article state. A coverage-only Markdown export is explicitly marked failed; it is not a successful article.

Cloud sharing of imported material requires an explicitly permitted import registry entry with both `cloud_content_allowed` and `imported_content_cloud_allowed`. The new import opt-in is consulted only by the arc workflow, checked live for every included source, and revocation takes effect immediately. Imported provenance is preserved; source attribution alone never grants sharing. The user approved only the supplied Romance Dawn narrative sections and selected ComicBook chapter-966 inscription section for this checkpoint.
