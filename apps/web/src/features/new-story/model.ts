export interface Build {
  world: string;
  arc: string;
  story: string;
  title: string;
  slug: string;
  state:
    | "finding"
    | "choose_pages"
    | "building"
    | "ready"
    | "failed"
    | "interrupted";
  messages: string[];
  error: string;
  pages: { title: string; position: number }[];
}
export interface SiteReport {
  allowed: boolean;
  reason: string;
  name: string;
  licence: string;
  page: string;
  headings: string[];
}
export interface SiteIdea {
  name: string;
  url: string;
  why: string;
}

export const MEDIUMS = ["game", "manga", "anime", "novel", "show"] as const;

export const STATE_LABELS: Record<Build["state"], string> = {
  finding: "Finding the arc's pages",
  choose_pages: "Waiting for you to check the pages",
  building: "Reading and writing the story",
  ready: "Ready to open",
  failed: "Stopped with a problem",
  interrupted: "Interrupted",
};

export const isRunning = (build: Build) =>
  build.state === "finding" || build.state === "building";

const SLUG = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;

/** The API path a browser request may reach, or null for anything else. */
export function buildPath(parts: string[], method: "GET" | "POST") {
  const [first, second, third] = parts;
  if (!parts.length) return "/api/builds";
  if (
    method === "POST" &&
    parts.length === 2 &&
    first === "sites" &&
    (second === "suggest" || second === "check")
  )
    return `/api/builds/sites/${second}`;
  if (!SLUG.test(first ?? "") || !SLUG.test(second ?? "")) return null;
  if (method === "GET" && parts.length === 2)
    return `/api/builds/${first}/${second}`;
  if (
    method === "POST" &&
    parts.length === 3 &&
    (third === "pages" || third === "resume")
  )
    return `/api/builds/${first}/${second}/${third}`;
  return null;
}

export async function call<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(`/api/atlas/builds${path}`, {
    method: body === undefined ? "GET" : "POST",
    headers: body === undefined ? {} : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const data = (await response.json().catch(() => ({}))) as T & {
    error?: string;
  };
  if (!response.ok)
    throw new Error(data.error ?? "The request could not be completed.");
  return data;
}
