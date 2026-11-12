# Phase 2.5B, Pass 1 — The illustrated chronicle

The default atlas is now a dedicated horizontal illustrated story canvas. It replaces the previous free-floating narrative graph rather than adding a timeline above it. Sigma remains the separate Free graph experience. Everything stays on `/` and uses the same API graph, narrative provider and per-experience store.

## Reference interpretation and review

The One Piece reference supplies the composition: illustrated milestones, an anchored selected event, left/right investigation and nearby branches. The actual Genshin Travel Log screenshots supply restraint: a readable horizontal line, a few significant images, compact controls, chapter annotations and ample separation. The later investigation mockup informs the optional source notebook, rather than a permanent text-heavy sidebar. Reference screenshots are examples, not application assets or story evidence.

The Phase 2.5A screenshots showed overlapping labels, a small disconnected cluster and a large panel carrying most of the story. The replacement gives each of the four existing moments a readable illustrated marker, current/earlier/ahead state, explicit episode annotation and branch indicator. It removes default category labels, full-graph edge noise, a permanent context panel and the oversized universe caption.

First browser review at 1920×1080 found expanded branches falling below the viewport. The refinement pass tightened the introduction, milestone sizes and central illustration only in investigation mode, preserving the spacious overview. It added a selected-milestone origin connector and kept the expanded lore region visible with its originating event. A graph regression test found a context panel covering the reset control; the free-view panel now ends above those controls.

## Visual architecture

| Component / module | Responsibility |
| --- | --- |
| `features/chronicle/StoryCanvas.tsx` | Story canvas, orientation, upcoming-detail preference, focus history and source notebook |
| `StorySpine.tsx` | Illustrated milestone navigation, current state and keyboard focus |
| `EventInvestigation.tsx` | Centered event illustration/editorial note, causes/consequences and compact branch controls |
| `StoryBranches.tsx` | Origin annotation, character/location/object/mystery media and lore discoveries |
| `SourceNotes.tsx` | Dismissible parchment-style source/scope/media notebook with focus restoration |
| `model.ts` | Deterministic spine window and scoped branch/causal projection from actual graph records |
| `design.ts` | Universe palettes/motifs, shared motion values and spine window configuration |
| `loading-contracts.ts` | Future overview, milestones, arc, branch, related-region and release seam; no network implementation |
| `src/app/chronicle.css` | Central typography, spacing, geometry, surfaces, ornaments and desktop adjustments |

Component paths are under `apps/web/src/`. `AtlasExperience.tsx` composes the header, shared search/universe controls and either the story canvas or the dynamically imported Sigma graph. Old narrative-panel modules remain in the checkout but are not mounted by the new main experience. The compatibility JourneyControls export still mounts the compact navigator.

## Story order and causal honesty

The current journey follows **original broadcast presentation**, not one linear in-world chronology. Earlier/current/ahead describe the position in that explicit sequence. Repeated attempts stay distinct. The four provider steps are not reordered from response arrays or graph traversal.

The seed has **no `CAUSED` edges**. Causes/consequences therefore explicitly state that no causal relationship is recorded. Adjacent steps are separately labeled “Earlier/Later in the telling” and “Story sequence · not a causal claim.” If compatible, explicit `CAUSED` graph edges arrive in the future, `eventRegion` resolves incoming causes on the left and outgoing consequences on the right. It never upgrades `CONNECTED_TO`, `REVEALED` or step adjacency to causality. Synthetic tests exercise actual causal-edge behavior without adding fabricated franchise content.

The overview shows four milestones and compact branch counts. Opening a moment expands the event composition. Opening a branch reveals only the relevant category; collapsing removes it. Character inspection uses the existing canonical node panel. Lore discovery keeps the journey's event visible and labels observations, editorial interpretations and unresolved questions. Return to journey restores the saved step. Back to previous focus restores branch expansion as well as the original selection, mode/layout and graph camera pose.

The upcoming-detail checkbox is a **local presentation preference**, not spoiler authorization. It hides ahead titles/artwork until selected. All underlying local graph/narrative data is still fetched. True server-enforced spoiler scopes belong to the future API.

## Adjustable design system

`chronicle.css` centralizes fonts, spacing, header/page dimensions, scene/milestone sizes, branch separation, path widths, panels and ornaments. System fonts use Palatino/Book Antiqua/Georgia fallbacks, with a quiet sans serif for annotations. All visual values are in shared presentation modules rather than story records or JSX styling scattered across components.

`UniverseTheme` supplies palettes and an arch/chart/rune motif. The active universe slug selects a configuration; unknown universes receive a manuscript fallback. Manuscript, nautical and weathered examples demonstrate the seam without adding fake universes to the catalog. Components and layout calculations contain no franchise-specific story rules. The new landscape SVG is original decorative fantasy engraving, not an official location depiction or a reference screenshot used as a background.

The primary target is 1920×1080. Smaller desktops keep the same hierarchy and scroll where necessary. Existing narrow-viewport smoke tests remain; there is no new mobile navigation, touch system, draggable sheet or advanced responsive choreography.

## Reused foundations and lifecycle

- `NarrativeDataProvider`, resolver and typed journeys/lore remain the data boundary. No story summaries or entities are embedded in presentation components.
- The Zustand narrative slice adds selected-event expansion, expanded branch, local upcoming preference and source-note visibility. Focus history includes expansion; universe/continuity changes clear incompatible active state. Rapid milestone selection updates progress and canonical selection together.
- The dedicated spine uses DOM illustrations and a presentation connector. It is not a second canonical graph. Sigma/Graphology still render the detailed free graph with their existing endpoint semantics, image layer and cleanup. Sigma is not loaded for the default story view.
- Existing GSAP hooks provide one interruptible entry transition per selected event/branch/notebook. Shared durations/easing now come from `CHRONICLE_DESIGN.motion`. CameraDirector remains responsible for the Sigma camera, reveal and emphasis scalars. `revertOnUpdate`, scoped matchMedia and teardown prevent accumulating tweens/listeners. Reduced motion sets transition durations to zero.
- No bulk WebGL-node animation, advanced line-tracing choreography, particles, auto-pulsing or Pass 2 motion system was added.

## Media and future agents

`MediaArtwork` now accepts thumbnail/scene variants. `MediaAsset` can carry thumbnail/full URLs, focal point, credit, source URL and interpretive/reference/fallback designation. Missing variants use the existing source; failures use the original compass fallback. Unselected illustrations load lazily; current scenes get priority. The registry still contains presentation assets only, never graph entities.

All current portraits and event art reuse permitted local SVGs. They are interpretive/symbolic, not official anime scenes. Richer, distinct scene images are a remaining content limitation. Future agents should supply permitted media metadata and sourced narrative/graph records through providers, not rewrite components. URL validation, licensing/attribution policy, image caching and actual research remain future backend work. No scraping, agent controls, confidence scores, fake AI streams or new backend endpoints were added.

`AtlasRegionProvider` describes future overview, nearby milestones, arc, event branch and related-entity requests plus release. It intentionally has no fake fetch implementation. The current dataset still loads in full. `spineLayout` limits display to five ordered steps at once for larger journeys without changing or deleting the provider sequence. Branch membership is stable and scoped to actual universe/continuity IDs. Existing free-graph renderer recreation on graph-snapshot changes is retained; incremental Sigma reconciliation is not implemented in this pass.

## Visual review and evidence

Final screenshot evidence and exact executed checks are recorded in [Pass 1 verification](phase-2-5b-verification.md). Review conclusions:

- The horizontal sequence and selected moment are understandable at a glance; broadcast order is explicit.
- The origin connector and moment annotation retain branch orientation.
- Earlier/current/ahead states use words, borders and position, not color alone.
- The map dominates; source notes and canonical details appear only when requested.
- Negative space separates the spine, event composition and discoveries. No full graph is overlaid behind the narrative.
- Portraits/event illustrations provide type/context cues; their limited symbolic fidelity is disclosed.
- Journey selection, branch exploration, lore and return stay on one URL and preserve progress.

## Remaining work for Pass 2

Review the actual structure before adding choreography. Potential next work includes coordinated story-camera travel, branch-line tracing, illustration crossfades and refined reveal ordering, with interruption/reduced-motion tests. The current artwork could be replaced by permitted, attributed higher-quality variants through the media seam. Do not begin agents, backend extensions, causal content ingestion or unrelated optimizations as part of Pass 2 without a separate instruction.
