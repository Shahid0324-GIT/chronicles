# Explicit journey ordering

Graph relationships, response-array order, discovery arrival and traversal are not chronological evidence.

Phase 2.5A uses `NarrativeJourney` and `JourneyStep` from `apps/web/src/features/narrative/contracts.ts`, supplied through `NarrativeDataProvider`. The four-step Re:Zero introduction is manually curated outside React in `features/narrative/fixtures/re-zero.ts`. It follows **original broadcast presentation**, not linear in-world chronology. Each step references a real EVENT UUID, source locators and existing graph relationships.

The resolver requires a selected matching continuity, at least two steps, unique step IDs, valid graph references and citations. Missing references make the journey unavailable, without invented substitutes or traversal-based ordering. The seed contains graph knowledge, not editorial sequence metadata. Previous/Next clamp at boundaries; inspection and lore preserve separate journey progress.

The older `features/journey/derive-journey.ts` validator remains a compatibility utility. Its optional EVENT metadata convention requires `journey.id`, `title`, unique nonnegative integer `order`, HTTP(S) `source`, and `order_verified: true`; consecutive events must be connected in one continuity. That flag is not evidence by itself and is not the provider for the current introduction. New work should use the explicit narrative contracts.

See [Phase 2.5A](../phase-2-5a-narrative.md) and [future API requirements](narrative-api.md). Backend-owned ordering requires evidence, spoiler scope, revisions and editorial review. Never fabricate ordering to demonstrate controls.
