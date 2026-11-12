import "server-only";
import type { Universe, UniverseGraph } from "./contracts";

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
  }
}
async function request<T>(path: string): Promise<T> {
  const base = process.env.API_BASE_URL ?? "http://127.0.0.1:8000";
  let response: Response;
  try {
    response = await fetch(`${base}${path}`, {
      cache: "no-store",
      signal: AbortSignal.timeout(10000),
    });
  } catch {
    throw new ApiError(
      503,
      "The local atlas service is unavailable. Start FastAPI and PostgreSQL, then try again.",
    );
  }
  if (!response.ok)
    throw new ApiError(
      response.status,
      response.status === 404
        ? "This universe has not been charted."
        : "The atlas could not be loaded. Check the local database and migrations.",
    );
  return response.json() as Promise<T>;
}
export const listUniverses = () => request<Universe[]>("/api/universes");
export const getUniverseGraph = (slug: string) =>
  request<UniverseGraph>(`/api/universes/${encodeURIComponent(slug)}/graph`);
