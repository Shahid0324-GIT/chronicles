# Chronicles: the continuous atlas

Phase 2 replaces the catalog and index panel with a single viewport at /. The initial universe opens automatically. Its universe switcher reloads data in place through a same-origin Next.js route forwarding to FastAPI; switching never changes the URL. The old /universes/[slug] address initializes the same application for compatibility.

## Visual architecture

The map is the primary interface. A floating header contains the universe selector, keyboard-searchable entries, and Explore/Guided modes. Type filters and camera controls sit along the lower edge. Selecting a node opens a floating illustrated story panel; on narrow screens it becomes a compact bottom overlay. Connections in that panel select other nodes without navigation. Selecting a rendered edge also exposes its actual relationship description in the context panel.

The visual system uses dark ink, restrained brass, serif story typography, and original SVG illustrations. Characters have portrait frames, places have landscape frames, events and mysteries use diamonds, factions use triangles, objects use squares, and lore uses circles. Types also have distinct colors and glyphs. Connections preserve backend types/direction, with arrowheads and labels emphasized around a selection.

Local artwork is interpretive placeholder media, not official character art or canonical reference. It is bundled and licensed in apps/web/public/art/LICENSE.md. No remote images, paid image service, inference, or simulated research is used.

## Modules

| Module under apps/web/src | Responsibility |
| --- | --- |
| features/atlas/AtlasExperience.tsx | Full-viewport composition, controls and loading/error/empty states |
| features/universe/ | Universe popover and cancellable graph requests |
| features/graph/adapter.ts | Validated backend-to-Graphology mapping, stable IDs and directed multi-edges |
| features/graph/layout.ts | Deterministic semantic clusters with degree ordering and ID tie-breaks |
| features/graph/GraphCanvas.tsx | Client-only Sigma renderer, projected keyboard targets and camera integration |
| features/discovery/ | Context panel and reusable licensed-media/fallback presentation |
| features/journey/ | Explicit-order validation and guided controls |
| stores/ | Per-experience Zustand store; no server-global mutable user state |
| animations/ | Scoped GSAP overlay motion and interruptible camera/highlight/discovery controllers |
| app/api/atlas/universes/[slug]/graph | Same-origin API forwarding; no database access |

Transport contracts, backend use cases, repositories, migrations, seed data, and API responses are unchanged.

## State and graph management

Zustand stores the active universe, graph snapshot, selection, filters, panel visibility, mode, journey position and camera pose/commands. Each mounted experience owns its store, avoiding request-to-request state leakage during SSR. Per-frame camera updates only re-render camera consumers.

Universe loads clear the previous graph and selection. AbortController cancels superseded requests; monotonically increasing tokens reject late responses and failures, including repeated requests for the same universe. The forwarding route keeps API_BASE_URL server-only.

The Graphology adapter retains UUID keys, source/target direction, parallel relationships and cycles. It reports duplicate, dangling, cross-universe and incompatible-continuity records instead of inventing connections. Layouts use type-specific anchors and sorted slots, never randomness or inferred chronology. Existing coordinates can be retained when incremental records arrive.

Continuity filtering includes explicitly shared nodes and only eligible edges whose endpoints remain visible. Type filters produce an induced subgraph. Search works within the current continuity/layers. Manual selection and layer changes leave Guided mode; progression uses a distinct internal journey selection source.

## Animation and rendering

Sigma 4 and its image layer render WebGL nodes, edges, arrows and labels. The renderer is dynamically imported with SSR disabled inside a client boundary. If WebGL is unavailable, search and contextual connections remain usable with an explanatory message.

GSAP animates one camera-state object through Sigma's public camera setter. Separate scalars control relationship emphasis and discovery reveals. It never creates a DOM tween per graph node. Pointer/wheel input interrupts motion, and new selections replace old tweens.

React useGSAP scopes and reverts overlay animations on universe, selection or mode changes. Context-safe card exits are cancelled on new selections. Teardown removes store/camera/media-query listeners, WebGL resources, and active tweens. Reduced motion is honored by camera, overlay and native gestures. Compact sizing updates at the mobile breakpoint.

## Accessibility

- Projected native buttons at graph positions support Tab, Enter and Space, using actual API entity titles.
- Focus the map region to pan with arrows, zoom with +/-, or reset with Home.
- Slash focuses search outside editable fields; search supports arrows, Enter and Escape.
- Story headings receive focus on selection. The close action returns focus to the map.
- Controls have names, pressed/selected states and visible focus indicators. Narrow-screen labels use collision-aware placement.

## Run and verify

Use README's unchanged backend migration/seed instructions. From the root, install with npm ci --prefix apps/web and start with npm run dev --prefix apps/web.

Run npm run test, lint, typecheck, format:check and build with --prefix apps/web. Unit tests need no backend; their synthetic fixtures are never imported by the app.

Playwright: start the real seeded FastAPI/PostgreSQL service at 127.0.0.1:8000, then run npm run test:e2e --prefix apps/web. The configuration uses installed Google Chrome and starts or reuses Next.js at port 3000. It never resets or seeds a database. Install Chrome or deliberately change the configured channel if unavailable.

## Limits and follow-up

The Re:Zero sample has no supported order. Guided mode reports uncharted chronology. Sourced ordering and progression are tested using explicit synthetic sequences only. See [journeys](contracts/journeys.md).

Media uses a stable-ID registry; see the [proposed backend media contract](contracts/media.md). Real SSE transport is absent; see the [event-consumer interface](contracts/atlas-events.md).

This prototype loads a complete small graph. Large datasets will need layout workers, bounded queries, aggregation, and label/texture budgets. The native-button overlay is not intended for thousands of entities. Graph-data events currently replace immutable snapshots and recreate Sigma while retaining known coordinates and camera pose; a future high-volume adapter should batch updates into the existing Graphology instance.
