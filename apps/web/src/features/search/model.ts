export type Kind = "summary" | "arc" | "character";

export interface Intent {
  kind: Kind | "story" | "unclear";
  story: string;
  subject: string;
  wikipedia_title: string;
}
export interface GuideJob {
  key: string;
  kind: Kind;
  story: string;
  title: string;
  state: "building" | "ready" | "failed" | "interrupted";
  messages: string[];
  error: string;
}
export interface GuideSource {
  number: number;
  title: string;
  url: string;
  language: string;
  heading: string;
  text: string;
  original: string;
  licence: string;
}
export interface Guide {
  kind: Kind;
  story: string;
  subject: string;
  title: string;
  sections: {
    heading: string;
    paragraphs: { text: string; cites: number[] }[];
  }[];
  cast: {
    name: string;
    role: "main" | "supporting";
    text: string;
    cites: number[];
  }[];
  sources: GuideSource[];
  notes: string[];
}

export const KIND_LABELS: Record<Kind, string> = {
  summary: "Story summary and cast",
  arc: "One arc",
  character: "One character",
};
export const SUBJECT_LABELS = { arc: "Arc", character: "Character" };
export const STATE_LABELS: Record<GuideJob["state"], string> = {
  building: "Being written",
  ready: "Ready to read",
  failed: "Stopped with a problem",
  interrupted: "Interrupted",
};
export const LANGUAGE_NAMES: Record<string, string> = {
  en: "English",
  ja: "Japanese",
  zh: "Chinese",
};

/** Whether a request names everything its kind needs. */
export function canBuild(intent: Intent) {
  if (intent.kind === "story" || intent.kind === "unclear") return false;
  if (intent.story.trim().length < 2) return false;
  return intent.kind === "summary" || intent.subject.trim().length > 0;
}

export const isWikipediaPage = (link: string) =>
  link === "" || /^https:\/\/(en|ja|zh)\.wikipedia\.org\/wiki\/\S+$/.test(link);

const KEY = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;

/** The API path a browser request may reach, or null for anything else. */
export function guidePath(parts: string[], method: "GET" | "POST") {
  const [first, second] = parts;
  if (!parts.length) return "/api/guides";
  if (method === "POST" && parts.length === 1 && first === "understand")
    return "/api/guides/understand";
  if (!KEY.test(first ?? "")) return null;
  if (method === "GET" && parts.length === 1) return `/api/guides/${first}`;
  if (method === "POST" && parts.length === 2 && second === "resume")
    return `/api/guides/${first}/resume`;
  return null;
}

export async function call<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(`/api/atlas/guides${path}`, {
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
