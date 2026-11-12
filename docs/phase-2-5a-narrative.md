# Phase 2.5A — Narrative and lore exploration

The atlas now opens a manually curated four-moment Re:Zero introduction within original TV anime episodes 1–2. The sequence follows **broadcast presentation**, including a return to an earlier situation; it does not claim linear in-world chronology. Facts, editorial interpretations and unanswered questions have separate visible labels. No agent discovered or verified this material.

## Reused and changed

Reused: the continuous `/` experience, FastAPI graph contracts, UUID identities, per-experience Zustand provider, Sigma/Graphology adapter, GSAP CameraDirector, search, graph inspection, keyboard controls, local SVG media and reduced-motion lifecycle. Backend architecture, migrations and read-only API remain unchanged.

Changed: guided controls consume an explicit narrative provider; lore has a discovery panel; the store tracks scoped progress, bookmarks and camera history. GraphCanvas chooses deterministic narrative, lore or free layout strategies. Step changes update focus/highlights without recomputing layout. Layout changes crossfade the renderer; individual WebGL nodes are not tweened in bulk. The old journey metadata validator remains a compatibility utility, not the source of this introduction.

## Files and responsibilities

| Location | Responsibility |
| --- | --- |
| `apps/web/src/features/narrative/contracts.ts` | Journey, step, lore, discovery, presentation and provider contracts |
| `features/narrative/fixtures/` | Editorial notes, citations and stable graph references; no copied canonical entities |
| `features/narrative/provider.ts` | Injectable local provider with async loading and cancellation |
| `features/narrative/resolve.ts` | Scope, citation and graph-reference validation |
| `features/narrative/selectors.ts` | Current narrative item and graph emphasis |
| `features/narrative/NarrativePanel.tsx`, `NarrativeDock.tsx` | Story/discovery panels and navigation |
| `apps/web/src/stores/narrative-state.ts` | Scoped progress, lore branches and bounded camera/focus history |
| `features/graph/layout-strategies.ts` | Story anchors, lore classification groups and free clusters |
| `services/intelligence/src/infrastructure/persistence/seed.py` | Five additional persisted records and thirteen edges |

Paths beginning `features/` are relative to `apps/web/src/`. See [the complete change manifest](phase-2-5a-files.txt).

## Data and navigation

`NarrativeDataProvider.load(scope, signal)` returns a versioned `NarrativeCatalog`. Inject a replacement at `createExplorationStore(graph, provider)` or the client `ExplorationProvider` boundary. React panels do not know whether notes came from fixtures or an API. The graph response remains authoritative for node titles, types, continuity and edges. Missing required references remove the affected journey/thread; they never generate substitute entities. Loading/error/unavailable guidance leaves free graph inspection available.

The store separately tracks universe, continuity, mode, layout, selected node/edge, journey ID/index, lore thread/discovery, per-scope progress, a journey bookmark and up to forty focus frames. Inspecting a character pauses the narrative. Entering lore preserves the step; Return to journey resumes it. Back to previous focus restores the previous layout, selection and camera pose. Progress is session memory, not persistent across reloads. Scope changes clear incompatible history and notes. Async responses are discarded after scope changes or cancellation.

Narrative anchors weave horizontally rather than forming a tree. Supporting nodes branch from actual connectivity and presentation references; sorting UUIDs keeps coordinates deterministic. Lore centers the concept with established observations, interpretation and unresolved questions in separate groups. Layout caches retain positions across revisits. Brass story paths and teal lore links are presentation attributes on existing edges, never invented graph relationships.

## Seed and sources

Rerun the seed from `services/intelligence` after upgrading an existing checkout:

```powershell
..\..\.venv\Scripts\python -m src.infrastructure.persistence.seed
```

It inserts missing deterministic IDs and retains existing records/user edits. The illustrative graph now has **15 nodes and 25 edges**. No migration or volume reset is needed. Existing edited records that no longer satisfy references can make the introduction unavailable.

The added records describe arrival, the first return, recognition, Return by Death and the introductory question about its cause. Source locators accompany each note:

- [Official TV story guide](https://re-zero-anime.jp/tv/story/tv1r.html), original episodes 1–2; the full page includes later spoilers.
- [TV Tokyo introduction](https://www.tv-tokyo.co.jp/anime/re-zero/story/), arrival and shared search.
- [Licensed episode 2 synopsis](https://tv.apple.com/us/episode/episode-2/umc.cmc.60smxe7gvy3ak446dw2trjhhk), repeated deaths/returns and recognition.

Only short manual paraphrases are included. Illustrations reuse existing permitted local assets and are labeled interpretive. They are presentation metadata, not evidence or canonical graph data.

## Verification and limits

See [verification](verification.md) and [future narrative API](contracts/narrative-api.md). Unit tests use synthetic graphs. Browser tests use actual seeded FastAPI/PostgreSQL and installed Chrome, including mobile reduced-motion lore exploration and return to moment two.

This is one small introduction and one thread. There is no journey chooser, narrative API, durable user progress, server-enforced spoiler authorization, live research, streaming producer, AI or orchestration. Layouts target small graphs; automatic collision avoidance and pagination remain future work. Source links may lead beyond the introductory spoiler scope. The illustrative graph is not a complete encyclopedia.
