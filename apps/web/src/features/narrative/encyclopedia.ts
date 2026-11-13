import { useEffect, useState } from "react";

export interface EncyclopediaEntry {
  id: string;
  display_title: string;
  short_introduction: string;
  aliases: string[];
  sections: {
    name: string;
    statements: { text: string; fact_ids: string[] }[];
  }[];
  connections: { id: string; source: string; target: string; type: string }[];
  source_references: {
    id: string;
    title: string;
    url: string;
    locator: string;
    quote?: string;
  }[];
}
const object = (v: unknown): v is Record<string, unknown> =>
  !!v && typeof v === "object";
const text = (v: unknown): v is string =>
  typeof v === "string" && v.length <= 20000;
const id = (v: unknown) => text(v) && /^[0-9a-f-]{36}$/i.test(v);
const list = (v: unknown, check: (item: unknown) => boolean) =>
  Array.isArray(v) && v.length <= 500 && v.every(check);
export function decodeEntry(v: unknown): EncyclopediaEntry {
  if (
    !object(v) ||
    !id(v.id) ||
    !text(v.display_title) ||
    !text(v.short_introduction) ||
    !list(v.aliases, text) ||
    !list(
      v.sections,
      (s) =>
        object(s) &&
        text(s.name) &&
        list(
          s.statements,
          (a) => object(a) && text(a.text) && list(a.fact_ids, text),
        ),
    ) ||
    !list(
      v.connections,
      (e) =>
        object(e) && id(e.id) && id(e.source) && id(e.target) && text(e.type),
    ) ||
    !list(
      v.source_references,
      (s) =>
        object(s) &&
        id(s.id) &&
        text(s.title) &&
        text(s.url) &&
        /^https?:\/\//.test(s.url) &&
        text(s.locator) &&
        (s.quote === undefined || text(s.quote)),
    )
  )
    throw new Error("The encyclopedia response is invalid.");
  return v as unknown as EncyclopediaEntry;
}
export function useEncyclopediaEntry(
  nodeId: string | null,
  slug: string | undefined,
  continuity: string | null,
  boundary: number | null,
  enabled: boolean,
  revision?: string,
) {
  const [result, setResult] = useState<{
    key: string;
    entry?: EncyclopediaEntry;
    error?: string;
  }>();
  const key = [nodeId, slug, continuity, boundary, enabled, revision].join(":");
  useEffect(() => {
    if (!enabled || !nodeId || !slug || !continuity) return;
    const controller = new AbortController();
    const query = new URLSearchParams({ continuity_id: continuity });
    if (boundary) query.set("spoiler_position", String(boundary));
    fetch(
      `/api/atlas/universes/${encodeURIComponent(slug)}/entries/${nodeId}?${query}`,
      { signal: controller.signal, cache: "no-store" },
    )
      .then(async (response) => {
        if (!response.ok)
          throw new Error("No entry is available at this story boundary.");
        return decodeEntry(await response.json());
      })
      .then((entry) => {
        if (entry.id !== nodeId)
          throw new Error("The entry identity does not match.");
        if (!controller.signal.aborted) setResult({ key, entry });
      })
      .catch((error: unknown) => {
        if (!controller.signal.aborted)
          setResult({
            key,
            error:
              error instanceof Error
                ? error.message
                : "This entry could not be opened.",
          });
      });
    return () => controller.abort();
  }, [nodeId, slug, continuity, boundary, enabled, key]);
  return result?.key === key ? result : undefined;
}
