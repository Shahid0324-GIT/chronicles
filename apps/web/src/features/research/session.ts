const prefix = "chronicles:research:v1:";
export const researchSessionEvent = "chronicles:research-session";
export function readResearchJob(scope: string): string | null {
  try {
    const value = JSON.parse(
      window.sessionStorage.getItem(prefix + scope) ?? "null",
    );
    return value?.version === 1 &&
      typeof value.id === "string" &&
      /^[0-9a-f-]{36}$/i.test(value.id)
      ? value.id
      : null;
  } catch {
    return null;
  }
}
export function saveResearchJob(scope: string, id: string) {
  try {
    window.sessionStorage.setItem(
      prefix + scope,
      JSON.stringify({ version: 1, id }),
    );
    window.dispatchEvent(new Event(researchSessionEvent));
  } catch {
    /* The running UI still follows its in-memory ID when storage is unavailable. */
  }
}
export function subscribeResearchJobs(listener: () => void) {
  window.addEventListener(researchSessionEvent, listener);
  window.addEventListener("storage", listener);
  return () => {
    window.removeEventListener(researchSessionEvent, listener);
    window.removeEventListener("storage", listener);
  };
}
