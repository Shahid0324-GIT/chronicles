import { proxyBackend } from "@/lib/server-proxy";

export async function GET(
  request: Request,
  context: { params: Promise<{ slug: string }> },
) {
  const { slug } = await context.params;
  if (!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(slug))
    return Response.json({}, { status: 400 });
  const incoming = new URL(request.url).searchParams;
  const query = new URLSearchParams();
  for (const key of [
    "continuity_id",
    "spoiler_position",
    "allowed_source_id",
  ]) {
    for (const value of incoming.getAll(key)) query.append(key, value);
  }
  return proxyBackend(`/api/universes/${slug}/narrative?${query}`, request);
}
