import { proxyBuilds } from "@/lib/builds-proxy";
import { guidePath } from "@/features/search/model";
import { sameRequestOrigin } from "@/lib/request-origin";

type Context = { params: Promise<{ path?: string[] }> };

export async function GET(request: Request, context: Context) {
  const path = guidePath((await context.params).path ?? [], "GET");
  if (path === null) return Response.json({}, { status: 404 });
  return proxyBuilds(path, request);
}

export async function POST(request: Request, context: Context) {
  if (!sameRequestOrigin(request)) return Response.json({}, { status: 403 });
  const path = guidePath((await context.params).path ?? [], "POST");
  if (path === null) return Response.json({}, { status: 404 });
  const text = await request.text();
  if (text.length > 4000) return Response.json({}, { status: 413 });
  let body: unknown = {};
  try {
    if (text) body = JSON.parse(text);
  } catch {
    return Response.json({}, { status: 400 });
  }
  return proxyBuilds(path, request, body);
}
