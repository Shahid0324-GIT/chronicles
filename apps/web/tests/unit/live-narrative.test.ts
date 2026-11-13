import { afterEach, describe, expect, it, vi } from "vitest";
import {
  BackendNarrativeDataProvider,
  LocalNarrativeDataProvider,
} from "../../src/features/narrative/provider";
import { createExplorationStore } from "../../src/stores/exploration";
import { eventRegion } from "../../src/features/chronicle/model";
import {
  getResearchSummary,
  startResearch,
} from "../../src/features/research/client";
import type { NarrativeCatalog } from "../../src/features/narrative/contracts";
import type { UniverseGraph } from "../../src/lib/contracts";
import { sameRequestOrigin } from "../../src/lib/request-origin";
import {
  readResearchJob,
  saveResearchJob,
} from "../../src/features/research/session";

const id = (n: number) =>
  `00000000-0000-4000-8000-${String(n).padStart(12, "0")}`;
const universe = id(1),
  continuity = id(2),
  source = id(3);
function catalog(): NarrativeCatalog {
  return {
    schemaVersion: 1,
    sources: [
      {
        id: source,
        title: "Owned story",
        url: "https://example.org/owned",
        locator: "Owned paragraph",
      },
    ],
    journeys: [
      {
        id: id(4),
        universeId: universe,
        continuityId: continuity,
        title: "Owned journey",
        introduction: "Owned synthetic fixture",
        spoilerScope: "Owned scope",
        ordering: {
          basis: "broadcast-presentation",
          explanation: "Owned explicit order",
          sourceIds: [source],
        },
        steps: [5, 6].map((n) => ({
          id: id(n + 10),
          eventNodeId: id(n),
          title: `Owned event ${n}`,
          body: "Owned event evidence",
          episodeLabel: `By episode ${n - 4}`,
          sourceIds: [source],
          loreThreadIds: [],
          presentation: { relatedNodeIds: [id(7)], relationshipIds: [id(8)] },
        })),
      },
    ],
    loreThreads: [],
    discoveries: [],
  };
}
function graph(): UniverseGraph {
  return {
    universe: {
      id: universe,
      slug: "owned",
      title: "Owned",
      description: "Owned",
      created_at: "",
      updated_at: "",
    },
    continuities: [
      {
        id: continuity,
        universe_id: universe,
        name: "Owned",
        medium: "ANIME",
        description: "Owned",
      },
    ],
    nodes: [5, 6, 7].map((n) => ({
      id: id(n),
      universe_id: universe,
      continuity_id: continuity,
      type: n === 7 ? "CHARACTER" : "EVENT",
      title: "Owned",
      summary: "Owned",
      metadata: {},
      created_at: "",
      updated_at: "",
    })),
    edges: [
      {
        id: id(8),
        universe_id: universe,
        continuity_id: continuity,
        source: id(7),
        target: id(5),
        relationship_type: "PARTICIPATED_IN",
        description: "Owned",
      },
    ],
  };
}
const scope = {
  universeId: universe,
  universeSlug: "owned",
  continuityId: continuity,
};
afterEach(() => vi.unstubAllGlobals());
describe("live narrative provider", () => {
  it("decodes an API catalog through the provider contract", async () => {
    const request = vi.fn<typeof fetch>().mockResolvedValue(
      Response.json({
        ...catalog(),
        revision: "owned-revision",
        partial: true,
        orderingGaps: [{}],
      }),
    );
    const result = await new BackendNarrativeDataProvider(
      new LocalNarrativeDataProvider(catalog()),
      request,
    ).load(scope);
    expect(result.availability).toMatchObject({
      kind: "generated",
      partial: true,
      gapCount: 1,
      revision: "owned-revision",
    });
    expect(request.mock.calls[0][0]).toContain(
      "/owned/narrative?continuity_id=",
    );
  });
  it.each([
    new Response(null, { status: 503 }),
    Response.json({ ...catalog(), journeys: [{ broken: true }] }),
  ])("uses one identified curated fallback on failure", async (response) => {
    const result = await new BackendNarrativeDataProvider(
      new LocalNarrativeDataProvider(catalog()),
      vi.fn<typeof fetch>().mockResolvedValue(response),
    ).load(scope);
    expect(result.availability?.kind).toBe("curated");
    expect(result.journeys).toEqual(catalog().journeys);
  });
  it("does not replace cancellation with curated content", async () => {
    const controller = new AbortController();
    controller.abort();
    const request = vi
      .fn<typeof fetch>()
      .mockRejectedValue(new DOMException("Aborted", "AbortError"));
    await expect(
      new BackendNarrativeDataProvider(undefined, request).load(
        scope,
        controller.signal,
      ),
    ).rejects.toThrow();
  });
  it("preserves stable milestone selection and branch expansion across refresh", async () => {
    let value = catalog();
    const store = createExplorationStore(graph(), {
      load: async () => structuredClone(value),
    });
    await store.getState().loadNarrative();
    store.getState().selectMilestone(1);
    store.getState().toggleBranch("characters");
    const extra = { ...value.journeys[0].steps[0], id: id(90) };
    value = {
      ...value,
      journeys: [
        { ...value.journeys[0], steps: [extra, ...value.journeys[0].steps] },
      ],
    };
    await store.getState().loadNarrative();
    expect(store.getState().journeyIndex).toBe(2);
    expect(store.getState().selectedId).toBe(id(6));
    expect(store.getState().expandedBranch).toBe("characters");
    value = {
      ...value,
      journeys: [
        { ...value.journeys[0], steps: value.journeys[0].steps.slice(0, 2) },
      ],
    };
    await store.getState().loadNarrative();
    expect(store.getState().journeyIndex).toBeLessThan(2);
  });
  it("does not mix curated graph edges into a generated event region", () => {
    const c = catalog();
    c.availability = { kind: "generated", reason: "Owned" };
    c.journeys[0].steps[0].presentation = {
      relatedNodeIds: [],
      relationshipIds: [],
    };
    expect(
      eventRegion(graph(), c.journeys[0].steps[0], c, continuity).characters,
    ).toEqual([]);
  });
  it("refreshes graph data without resetting exploration scope or branch state", async () => {
    const store = createExplorationStore(
      graph(),
      new LocalNarrativeDataProvider(catalog()),
    );
    await store.getState().loadNarrative();
    store.getState().selectMilestone(1);
    store.getState().toggleBranch("characters");
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(Response.json(graph())));
    await store.getState().refreshAtlas();
    expect(store.getState().continuityId).toBe(continuity);
    expect(store.getState().selectedId).toBe(id(6));
    expect(store.getState().expandedBranch).toBe("characters");
  });
});
describe("research controls transport", () => {
  it("restores only a validated, versioned job ID within its own scope", () => {
    const values = new Map<string, string>();
    vi.stubGlobal("window", {
      sessionStorage: {
        getItem: (k: string) => values.get(k) ?? null,
        setItem: (k: string, v: string) => values.set(k, v),
      },
      dispatchEvent: vi.fn(),
    });
    saveResearchJob("owned-anime", id(30));
    expect(readResearchJob("owned-anime")).toBe(id(30));
    expect(readResearchJob("other-continuity")).toBeNull();
    values.set(
      "chronicles:research:v1:owned-anime",
      JSON.stringify({ version: 99, id: id(30) }),
    );
    expect(readResearchJob("owned-anime")).toBeNull();
  });
  it("accepts local adapter aliases but rejects cross-site and wrong-port submissions", () => {
    expect(
      sameRequestOrigin(
        new Request("http://localhost:3000/api/atlas/research/jobs", {
          headers: { origin: "http://127.0.0.1:3000" },
        }),
      ),
    ).toBe(true);
    expect(
      sameRequestOrigin(
        new Request("http://localhost:3000/api/atlas/research/jobs", {
          headers: { origin: "https://example.org" },
        }),
      ),
    ).toBe(false);
    expect(
      sameRequestOrigin(
        new Request("http://localhost:3000/api/atlas/research/jobs", {
          headers: { origin: "http://localhost:4444" },
        }),
      ),
    ).toBe(false);
    expect(
      sameRequestOrigin(
        new Request("http://localhost:3000/api/atlas/research/jobs", {
          headers: {
            origin: "http://localhost:3000",
            "sec-fetch-site": "cross-site",
          },
        }),
      ),
    ).toBe(false);
  });
  it("starts a scoped job and validates a concise status response", async () => {
    const summary = {
      id: id(30),
      status: "partial",
      stage: "narrative_builder",
      error: null,
      model_calls: 4,
      cache_hits: 1,
      retry_count: 0,
      validation_failures: 0,
      sources: 2,
      embedding_reused: 2,
      accepted_relationships: 1,
      unresolved_findings: 1,
      discoveries: [],
    };
    const request = vi
      .fn()
      .mockResolvedValueOnce(Response.json({ id: id(30) }))
      .mockResolvedValueOnce(Response.json(summary));
    vi.stubGlobal("fetch", request);
    expect(
      await startResearch(
        universe,
        continuity,
        "Owned focused research objective",
        1,
      ),
    ).toBe(id(30));
    expect(JSON.parse(request.mock.calls[0][1].body)).toMatchObject({
      universe_id: universe,
      continuity_id: continuity,
      spoiler_position: 1,
    });
    expect((await getResearchSummary(id(30))).status).toBe("partial");
  });
  it("rejects malformed progress instead of displaying success", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(Response.json({ id: id(30), status: "completed" })),
    );
    await expect(getResearchSummary(id(30))).rejects.toThrow(
      "Invalid research status",
    );
  });
});
