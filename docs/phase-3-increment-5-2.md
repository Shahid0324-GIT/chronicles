# Phase 3, increment 5.2 — operational research, partial acceptance

The local search service and real Groq integration work, but the requested autonomous, connected, multi-publisher research benchmark is **not complete**. Live runs exposed search access limits, weak extraction, invalid structured outputs and semantic verification false positives. These are recorded, not replaced with simulated successes. The frontend remains unchanged.

See [actual jobs, questions, findings, provider attempts and comparison](phase-3-increment-5-2-results.json), [initial search captures](phase-3-increment-5-2-search.json), and [setup/recovery checkpoint](phase-3-increment-5-2-search.md).

## Operational changes

- Added a pinned, loopback-only SearXNG Docker service and repeatable PowerShell startup. Existing PostgreSQL volumes remain intact. Queries are paced, response bytes/results bounded, and unsafe discovered URLs rejected.
- Fixed Groq model availability checks to compare the configured model ID rather than its display name. Actual configured model: `openai/gpt-oss-120b`; local model: `qwen3.5:4b`. Keys were not printed or rotated after a rate limit.
- Persisted result titles, snippets and discovery origin. Explicit same-origin/path/continuity permission rules can admit matching discoveries; unknown pages stay navigation-only. Successful queries survive failures later in a batch. Revocation of a rule prevents new grants; previously admitted entries must be revoked separately.
- Reapplied host/spoiler fences after discovery. Cloud routing rechecks current source permissions for passage context. Only the user-approved small public dossier was newly opted in; existing restrictions and provider defaults remain unchanged.
  The final registry audit confirms three opted-in selected sections and **zero cloud-allowed discovery families**; future discoveries do not inherit this dossier’s cloud opt-in.
- Constrained empty identity catalogs to new-or-ambiguous responses, preserved explicitly typed extraction modes, strengthened subject/attribute and pronoun grounding, and repaired Groq tool-validation classification. Failed generations yield redacted schema locations, never content in telemetry. Model responses, independent corroboration and canonical publication remain separate.

## Real evidence and access

The focused objective became **Felt and Rom’s background, caring bond and connection to the loot house**, under a separate original-novel continuity. The existing anime scope is not merged with it. First-reveal positions are unknown, so these sources are not eligible for spoiler-bounded reads.

| Reference | What actually happened |
| --- | --- |
| [Official creator Q&A](https://re-zero.com/news/2517/) | Live SearXNG returned this page. Protected fetching succeeded; only question 3’s 846-character section was archived for the approved comparison. The article warns about later-volume spoilers. |
| [Official original-novel profiles](https://re-zero.com/character/) | Protected fetching succeeded; only Felt and Rom sections were archived. Japanese names do not automatically establish English aliases. This was an existing reviewed official reference. |
| [Wikipedia character list](https://en.wikipedia.org/wiki/List_of_Re:Zero_characters) | Retrieval failed certificate validation; another verified HTTP request returned 403. No verification bypass. |
| [Dedicated wiki relationship page](https://rezero.fandom.com/wiki/Puck/Relationships) | Discovered during preliminary Emilia/Puck investigation; protected robots retrieval unavailable. It was not ingested and is not evidence for the Felt/Rom objective. |

The two successfully retrieved pages belong to **one publisher family**, not two independent sources. Reviewed registration of these real references was a fallback after failed autonomous searches; it must not be described as successful unattended source admission.

Initial SearXNG tests returned real results for three Re:Zero queries and one Elden Ring query. Subsequent agent queries returned none: Brave reported a rate suspension and DuckDuckGo CAPTCHA. Google denied access; Bing returned unrelated single-term results. Blocked/unreliable engines were removed. One relevant Brave query succeeded after its reported cooldown, followed by another failure. No proxy, CAPTCHA bypass, key rotation or access-control workaround was used. Search reliability remains an external blocker.

## Findings and quality review

Source-backed candidate material includes Rom’s wartime background, care for Felt as a baby, and the author’s description of their bond. The profiles connect both characters with the loot house. These are research candidates and attributed source statements, not proof of independent corroboration or automatically published character identities. The archive retains exact passage IDs, normalized quotation offsets and source hashes.

The mixed-source workflow produced eleven relationship candidates, **zero supported relationship findings and zero published edges**. Cross-language identity bridges, canonical endpoints and the two-publisher requirement prevented publication. A supported model assessment alone did not override those guards. The existing graph gained one source-anchored novel-history event; an irrelevant profile utterance was retracted through the audited correction API. No earlier node or relationship was removed.

Important observed failures:

1. A candidate incorrectly called Felt a demihuman. Neither selected source establishes that attribute. Both models falsely accepted the same negative-control assertion even after stricter prompting. It was not published. This demonstrates that model entailment is fallible; it is not an independent fact check.
2. The planner changed typed encyclopedia requests into story extraction. Preserving the requested mode prevents that route, and the misclassified utterance was corrected with retained history.
3. Empty catalogs elicited invented match indices. A constrained response schema now excludes those choices while retaining evidence/type validation and ambiguous outcomes.
4. Structured schema errors caused sparse or empty extraction. Schema guidance improved the controlled local extraction to three candidates; Groq’s failed extraction attempts still fell back locally. No fallback is counted as a Groq extraction success.

## Same-dossier provider comparison

Both runs used source `6786e5d0-726d-5589-9d5d-cf52d9d0b768`, SHA-256 `7058b15304c8f52b0ce812f8741145db6a4b38e215a7a87e0cdca13985ddcee2`. This was a direct, explicitly dossier-scoped benchmark with ephemeral routing, not a production policy change or publication job.

| Run | Extraction | Recap |
| --- | --- | --- |
| Local Ollama | Three candidates, 7.831 s after guidance improvement | Real local generation and local model grounding assessment; preview returned |
| Groq-preferred | Two invalid-output attempts, then the same local extraction fallback; 16.322 s total | Real Groq generation and Groq model grounding assessment; preview returned |

The Groq preview discusses Rom’s wartime role alongside everyday care for Felt. The local preview combines his background and long-term caregiving. The JSON records actual drafts, referenced candidate IDs, failed attempts, token counts and provider identities. Their `validated` status means the existing model-assisted presentation check passed; it does **not** mean independent verification, publication approval or a completed cohesive story arc. These previews stay outside the canonical atlas. The negative-control failure limits confidence in that assessment.

Unfinished leads persist, including the loot-house connection, explicit subject/alias bridges, source independence, and care/bond details. New bounded jobs can continue them; old job budgets were not reset.

## Verification and remaining work

- Backend: Ruff check/format and mypy passed. **188 tests passed**, including seven isolated PostgreSQL tests with actual migration upgrade/downgrade. No schema migration or dependency change was needed.
- Frontend: lint, typecheck, **57 unit tests**, and production build passed.
- Full Playwright: **11 passed, one opt-in repeated-inference test skipped**. One passing progress-control test uses synthetic HTTP responses and is not research evidence. Live narrative/encyclopedia tests use real services. The first browser run failed after the new continuity changed initial selection; correcting the novel scope’s metadata restored the existing anime default and the full suite passed.
- Baseline: all **26 prior node IDs and 33 relationship IDs retained**; the historical 24-node/31-edge content snapshot also matches after normalizing equivalent timestamp formatting. No developer database reset or frontend rewrite occurred.

Still incomplete: reliable unattended search across runs; eligible wiki/original chapter ingestion and independent corroboration; supported canonical relationship publication for this novel dossier; robust semantic verification; broad character/event/lore coverage; and a published cohesive multi-source recap. The configured Groq model still produces schema-invalid responses on some tasks. No future-agent placeholders, image discovery, visual redesign, SSE, deployment or advanced animation were introduced.

Automatic approval review rejected a proposed persistent global cloud-extraction setting because the user had approved only the selected dossier. That change was not applied. The direct comparison stayed within the existing dossier-specific approval, and production routing defaults remain unchanged.
