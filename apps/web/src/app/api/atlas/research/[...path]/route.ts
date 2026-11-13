import { proxyBackend } from "@/lib/server-proxy";
import { sameRequestOrigin } from "@/lib/request-origin";

type Context = { params: Promise<{ path: string[] }> };
export async function GET(request: Request, context: Context) {
  const { path } = await context.params;
  if (
    path.length !== 3 ||
    path[0] !== "jobs" ||
    path[2] !== "summary" ||
    !/^[0-9a-f-]{36}$/.test(path[1])
  )
    return Response.json({}, { status: 404 });
  return proxyBackend(`/api/research/jobs/${path[1]}/summary`, request);
}
export async function POST(request: Request, context: Context) {
  const { path } = await context.params;
  if (!sameRequestOrigin(request)) return Response.json({}, { status: 403 });
  if (path.length !== 1 || path[0] !== "jobs")
    return Response.json({}, { status: 404 });
  const text = await request.text();
  if (text.length > 6000) return Response.json({}, { status: 413 });
  try {
    const data = JSON.parse(text);
    return proxyBackend("/api/research/jobs", request, {
      universe_id: data.universe_id,
      continuity_id: data.continuity_id,
      objective: data.objective,
      use_registry: true,
      narrative_research: true,
      allow_search: false,
      sources: [],
      refresh: true,
      ...(Number.isInteger(data.spoiler_position) && data.spoiler_position > 0
        ? { spoiler_position: data.spoiler_position }
        : {}),
    });
  } catch {
    return Response.json({}, { status: 400 });
  }
}
