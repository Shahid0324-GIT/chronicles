/** Next's local adapter can normalize 127.0.0.1 to localhost. Ports still must match. */
export function sameRequestOrigin(request: Request): boolean {
  const origin = request.headers.get("origin");
  if (request.headers.get("sec-fetch-site") === "cross-site") return false;
  if (!origin) return true;
  try {
    const supplied = new URL(origin),
      local = new URL(request.url);
    const host = request.headers.get("host");
    if (host && supplied.host === host && supplied.protocol === local.protocol)
      return true;
    if (supplied.origin === local.origin) return true;
    return (
      [supplied.hostname, local.hostname].every(
        (h) => h === "localhost" || h === "127.0.0.1",
      ) &&
      supplied.port === local.port &&
      supplied.protocol === local.protocol
    );
  } catch {
    return false;
  }
}
