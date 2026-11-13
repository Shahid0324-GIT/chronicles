import type {
  NarrativeCatalog,
  NarrativeDataProvider,
  NarrativeScope,
} from "./contracts";
import { RE_ZERO_NARRATIVE } from "./fixtures/re-zero";
import { decodeNarrative } from "./decode";
import { emptyNarrativeCatalog } from "./contracts";

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

/** Uses one complete catalog at a time; fallback never merges fixture relationships. */
export class BackendNarrativeDataProvider implements NarrativeDataProvider {
  constructor(
    private readonly fallback: NarrativeDataProvider = new LocalNarrativeDataProvider(),
    private readonly request: typeof fetch = (...args) => fetch(...args),
  ) {}
  async load(
    scope: NarrativeScope,
    signal?: AbortSignal,
  ): Promise<NarrativeCatalog> {
    let reason = "No generated journey is available for this continuity.";
    if (scope.universeSlug && scope.continuityId) {
      try {
        const response = await this.request(
          `/api/atlas/universes/${encodeURIComponent(scope.universeSlug)}/narrative?continuity_id=${encodeURIComponent(scope.continuityId)}${scope.spoilerPosition ? `&spoiler_position=${scope.spoilerPosition}` : ""}`,
          {
            cache: "no-store",
            signal: signal
              ? AbortSignal.any([signal, AbortSignal.timeout(15000)])
              : AbortSignal.timeout(15000),
          },
        );
        if (!response.ok)
          throw new Error("Generated stories are temporarily unavailable.");
        const raw: unknown = await response.json();
        const catalog = decodeNarrative(raw);
        if (
          catalog.journeys.some((j) => j.steps.length >= 2) ||
          scope.spoilerPosition
        ) {
          const metadata = raw as Record<string, unknown>;
          return {
            ...catalog,
            availability: {
              kind: "generated",
              reason: "Source-backed research from the local archive.",
              revision:
                typeof metadata.revision === "string"
                  ? metadata.revision
                  : undefined,
              partial: metadata.partial === true,
              gapCount: Array.isArray(metadata.orderingGaps)
                ? metadata.orderingGaps.length
                : 0,
            },
          };
        }
      } catch (error) {
        signal?.throwIfAborted();
        reason =
          error instanceof Error
            ? error.message
            : "Generated stories are unavailable.";
      }
    }
    if (scope.spoilerPosition)
      return {
        ...emptyNarrativeCatalog(),
        availability: { kind: "generated", reason },
      };
    const curated = await this.fallback.load(scope, signal);
    return { ...curated, availability: { kind: "curated", reason } };
  }
}
