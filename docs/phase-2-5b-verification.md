# Phase 2.5B Pass 1 verification

Verified on Windows with the existing Node/Python environment on 12 November 2026. Primary visual target: **1920×1080**. Implementation guide: [the illustrated chronicle](phase-2-5b-pass-1.md).

## Executed checks

| Command / boundary | Result |
| --- | --- |
| `npm run typecheck --prefix apps/web` | Passed |
| `npm run lint --prefix apps/web` | Passed |
| `npm run format:check --prefix apps/web` | Passed after formatting the media registry |
| `npm run test --prefix apps/web` | **42 passed**, 7 files |
| `npm run build --prefix apps/web` | Passed: optimized Next.js production compilation, TypeScript and page generation |
| `npm run test:e2e --prefix apps/web` | **8 passed**, final production run: 25.2 seconds |
| `git diff --check` | Passed |
| HTTP `/` | 200 |
| FastAPI `/api/health` | `status=ok`, `database=ready` |
| FastAPI Re:Zero graph | 15 nodes, 25 edges, existing persisted IDs |

The production frontend ran at `http://127.0.0.1:3000`; FastAPI used `http://127.0.0.1:8000`. Browser tests used installed Google Chrome and the real seeded PostgreSQL/FastAPI service. No mocked graph or research producer was used. No backend source, API schema, dependencies, seed records, migrations or database data changed in this phase, so the backend test suite was not rerun; its previous results are in the historical verification record.

The user story verified is: open persisted universe → provider resolves the four sourced steps against API graph IDs → select a milestone → expand characters/lore → inspect a canonical entity or discovery → return to the same journey step → continue without leaving `/`. Free graph, filters, search and universe reload remain available.

## Coverage

New unit coverage checks explicit `CAUSED` direction versus sequence adjacency, continuity/universe filtering, deterministic spine coordinates and bounded windows, theme fallback, branch expansion/collapse, branch-history restoration, milestone validation, rapid selection and retained journey position. Existing tests retain graph semantics, source/reference validation, media registry fallback and camera interruption/reduced-motion behavior.

Eight browser cases cover keyboard search at a narrow viewport, the persisted Sigma graph, missing artwork/continuity/empty layers/universe reload, desktop and retained mobile reduced-motion lore detours, the 1920×1080 illustrated milestone flow, source-note dismissal, and rapid navigation under normal and reduced motion. The new desktop test also asserts that the spine and entire expanded lore region remain in the viewport, current-step ARIA state, the upcoming-detail preference and the explicit missing-causal-data explanation. Global lore entry distinguishes a journey bookmark from a direct event relationship.

## Visual evidence

These are actual production browser captures, not mockups. The primary screenshots use 1920×1080; the smaller desktop uses 1366×768.

| View | Screenshot |
| --- | --- |
| Main narrative overview | [Overview](phase-2-5b-overview.jpg) |
| Selected event, left/right investigation | [Event](phase-2-5b-event.jpg) |
| Expanded lore and its origin | [Lore](phase-2-5b-lore.jpg) |
| Character investigation while retaining story | [Character](phase-2-5b-character.jpg) |
| Optional smaller desktop | [1366×768](phase-2-5b-desktop-small.jpg) |
| Optional editorial source notebook | [Sources](phase-2-5b-sources.jpg) |

## Comparison with the references

| Review question | Observed result |
| --- | --- |
| Narrative understandable at a glance? | Yes: four illustrated milestones, explicit direction and current position. |
| Branches connected to their origin? | Yes: selected-event connector and originating-moment annotation; global lore uses a bookmark label instead of inventing an event link. |
| Past/current/future distinguishable? | Earlier/current/ahead labels describe broadcast presentation, including repeated attempts. |
| Enough negative space? | Yes at the primary size; investigation spacing was reduced after the first capture without overlaying graph noise. |
| Map appropriately dominant? | The spine, event and branches fill the main canvas; information panels are transient. |
| Meaningful character/event imagery? | Existing SVGs identify types and context. Scene fidelity remains limited; these are interpretive illustrations. |
| Visually overwhelming? | The default omits unrelated graph edges, category clusters and permanent sidebars. One detailed branch opens at a time. |
| Illustrated chronicle rather than dashboard? | Editorial type, manuscript frames and optional parchment notes establish the intended direction, with restrained local artwork. |
| Navigate without losing position? | Browser and store tests retain moment two through character/lore detours and return. |

## Review findings and refinements

1. The first 1920×1080 pass had readable milestones but expanded lore ran below the viewport. Investigation mode now uses a compact introduction, shorter spine and smaller central illustration. An origin connector joins the selected milestone to the event composition. The complete lore region remains visible with the spine.
2. The optional 1366×768 review exposed branch controls too close to the navigator. Compact-desktop measurements now reserve room for those controls, and the canvas scroll region ends above the fixed navigator. Expanded content can scroll at smaller resolutions; there is no separate mobile redesign.
3. A regression test found the canonical context panel intercepting the free-graph reset control. Free-view panel bounds were corrected, then the case passed.
4. A legacy universe-reload assertion expected the old graph default. It was updated to verify the new story default, followed by explicit Free graph selection and persisted entity visibility.
5. Initial formatting reported the extended media registry; Prettier corrected it and the final formatting check passed.

The references were used for composition, illustrated orientation and restraint. Unlike the previous screenshots, there is no tangled default edge field or category cluster behind the story. Current position uses words, frame and sequence position rather than color alone. Dismissible canonical/source panels leave the main event and spine readable. The final production browser console returned no warning/error entries during the smaller-desktop review. Comprehensive accessibility auditing, large-data stress testing and a larger 2560×1440 screenshot were not performed.

The in-app browser retained an unreachable tab while switching dev to production. A fresh tab in the same browser resolved it. Screenshot capture used the DOM screenshot API because the native window screenshot reflects the physical 1280×720 surface, whereas the browser viewport was explicitly 1920×1080. Playwright's environment prints a NO_COLOR/FORCE_COLOR warning; Next dev reported a slow-filesystem advisory. Neither caused a final check failure.

## Boundaries and review status

The story is broadcast presentation, not inferred chronology. The seed contains no `CAUSED` edges; no fictional causal facts were invented. The upcoming-details toggle is presentation-only, not server spoiler enforcement. Existing art is symbolic/interpretive and should eventually receive permitted attributed variants. Progress remains in memory. All data is still loaded in full; the region-loading interface has no HTTP/cache implementation. Free-graph snapshot updates retain the existing renderer lifecycle.

Only essential existing GSAP transitions were retained/configured. Advanced Pass 2 choreography, agents, image scraping and backend extensions were not started. The implementation checkpoint was pushed as `3a372a5`; the final review/refinement commit follows it on `main`. Local production frontend and the existing backend/database remain running for the user's requested design review.
