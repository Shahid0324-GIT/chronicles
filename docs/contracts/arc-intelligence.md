# Backend arc artifacts — Increment 6.2 checkpoint

This is an additive backend contract. Frontend integration is deliberately absent.

`GET /api/universes/{slug}/arcs/{arc_id}?continuity_id={uuid}&spoiler_position=7`

Optional repeated `allowed_source_id` restricts sources. Omit the boundary for full-lore eligibility. Unknown arc/continuity pairs return 404. A missing or stale dossier returns `status: pending`, `dossier: null`, `article: null`; GET performs no inference. Current evidence and permission revisions are checked before returning stored prose.

`dossier` is a validated `ArcDossier`: stable arc/section IDs, provisional plan status, source range, perspective, accepted assertion references, editorial facet assignments, per-section coverage, reconstruction and revision. Facet assignment is not canonical publication or proof of causation. Research status, missing facets and presentation readiness are separate. The current real dossier is partial; these structures do not demonstrate complete narrative understanding.

`article` is a separate `ArcArticle` artifact: section headings, paragraphs with exact fact references, coverage, perspective and dossier revision. Its status is `withheld` when no section is validated, otherwise `partial`. No complete-arc state is currently asserted. Withheld drafts expose no paragraph prose. Historical model-approved artifacts do not override current revision/policy eligibility.

Research commands opt in with `arc_id`. A `presentation_only` arc command can reuse accepted evidence without supplying new sources. `retry_withheld_presentations` explicitly retries withheld sections; unchanged validated sections are reused. Existing short narrative and encyclopedia endpoints remain compatible. The independent worker and existing budgets remain mandatory.

Export current backend artifacts without inference:

```powershell
..\..\.venv\Scripts\python -m src.export_arc --universe db33dec2-5da5-53f2-9a1f-d43009d50dba --continuity 9110bdd8-a094-570f-827b-ad75793989cd --arc 757483a7-667c-5caf-9e49-64f6d8772839 --through 7 --output ../../docs/evidence/increment-6-2/romance-dawn.md
```

The sibling JSON retains the dossier and article state. A coverage-only Markdown export is explicitly marked failed; it is not a successful article.

Cloud sharing of imported material requires an explicitly permitted import registry entry with both `cloud_content_allowed` and `imported_content_cloud_allowed`. The new import opt-in is consulted only by the arc workflow, checked live for every included source, and revocation takes effect immediately. Imported provenance is preserved; source attribution alone never grants sharing. The user approved only the supplied Romance Dawn narrative sections and selected ComicBook chapter-966 inscription section for this checkpoint.
