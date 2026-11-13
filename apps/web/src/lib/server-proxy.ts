import "server-only";

/** Fixed backend paths only. Never accepts a caller-supplied URL or forwards credentials. */
export async function proxyBackend(
  path: string,
  request: Request,
  body?: unknown,
) {
  try {
    const response = await fetch(
      (process.env.API_BASE_URL ?? "http://127.0.0.1:8000") + path,
      {
        method: body === undefined ? "GET" : "POST",
        headers:
          body === undefined ? {} : { "Content-Type": "application/json" },
        body: body === undefined ? undefined : JSON.stringify(body),
        cache: "no-store",
        redirect: "error",
        signal: AbortSignal.any([request.signal, AbortSignal.timeout(15000)]),
      },
    );
    if (!response.ok)
      return Response.json(
        { error: "Research service request unavailable." },
        { status: response.status },
      );
    return Response.json(await response.json(), {
      headers: { "Cache-Control": "no-store" },
    });
  } catch {
    return Response.json(
      { error: "The local research service is unavailable." },
      { status: 503 },
    );
  }
}
