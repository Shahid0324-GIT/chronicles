import { describe, expect, it } from "vitest";
import { buildPath, isRunning, type Build } from "@/features/new-story/model";

describe("new story requests", () => {
  it("forwards only the build paths", () => {
    expect(buildPath([], "POST")).toBe("/api/builds");
    expect(buildPath(["sites", "check"], "POST")).toBe(
      "/api/builds/sites/check",
    );
    expect(buildPath(["my-story", "arc-1"], "GET")).toBe(
      "/api/builds/my-story/arc-1",
    );
    expect(buildPath(["my-story", "arc-1", "pages"], "POST")).toBe(
      "/api/builds/my-story/arc-1/pages",
    );
    for (const parts of [
      ["..", "arc"],
      ["my-story", "arc-1", "delete"],
      ["my-story"],
      ["my story", "arc"],
    ])
      expect(buildPath(parts, "POST")).toBeNull();
    expect(buildPath(["my-story", "arc-1", "resume"], "GET")).toBeNull();
  });

  it("watches only builds that are still working", () => {
    const build = (state: Build["state"]) => ({ state }) as Build;
    expect(isRunning(build("finding"))).toBe(true);
    expect(isRunning(build("choose_pages"))).toBe(false);
  });
});
