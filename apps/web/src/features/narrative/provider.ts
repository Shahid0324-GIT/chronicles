import type {
  NarrativeCatalog,
  NarrativeDataProvider,
  NarrativeScope,
} from "./contracts";
import { RE_ZERO_NARRATIVE } from "./fixtures/re-zero";

/** Explicitly curated local narrative, not agent output or an invented backend. */
export class LocalNarrativeDataProvider implements NarrativeDataProvider {
  constructor(private readonly catalog: NarrativeCatalog = RE_ZERO_NARRATIVE) {}
  async load(
    scope: NarrativeScope,
    signal?: AbortSignal,
  ): Promise<NarrativeCatalog> {
    signal?.throwIfAborted();
    const journeys = this.catalog.journeys.filter(
      (j) =>
        j.universeId === scope.universeId &&
        j.continuityId === scope.continuityId,
    );
    const loreThreads = this.catalog.loreThreads.filter(
      (t) =>
        t.universeId === scope.universeId &&
        t.continuityId === scope.continuityId,
    );
    const threadIds = new Set(loreThreads.map((t) => t.id));
    return structuredClone({
      ...this.catalog,
      journeys,
      loreThreads,
      discoveries: this.catalog.discoveries.filter((d) =>
        threadIds.has(d.threadId),
      ),
    });
  }
}
