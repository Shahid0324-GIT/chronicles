import "server-only";

/** Fixed build paths only. Checking a site waits for its requested delay, so be patient. */
export async function proxyBuilds(
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
          body === undefined
            ? {}
            : {
                "Content-Type": "application/json",
                "X-Chronicles-Local": "1",
              },
        body: body === undefined ? undefined : JSON.stringify(body),
        cache: "no-store",
        redirect: "error",
        signal: AbortSignal.any([request.signal, AbortSignal.timeout(120000)]),
      },
    );
    const data = (await response.json()) as { detail?: unknown };
    if (!response.ok)
      return Response.json(
        {
          // The local API's own refusals are written for the reader.
          error:
            typeof data.detail === "string"
              ? data.detail
              : "The request could not be completed. Check what you entered.",
        },
        { status: response.status },
      );
    return Response.json(data, { headers: { "Cache-Control": "no-store" } });
  } catch {
    return Response.json(
      { error: "The local service is unavailable. Is the API running?" },
      { status: 503 },
    );
  }
}
