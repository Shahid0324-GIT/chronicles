import { describe, expect, it } from "vitest";
import {
  canBuild,
  guidePath,
  isWikipediaPage,
  type Intent,
} from "@/features/search/model";

describe("search requests", () => {
  it("forwards only the guide paths", () => {
    expect(guidePath([], "POST")).toBe("/api/guides");
    expect(guidePath(["understand"], "POST")).toBe("/api/guides/understand");
    expect(guidePath(["lantern-marsh-wren-1a2b3c4d"], "GET")).toBe(
      "/api/guides/lantern-marsh-wren-1a2b3c4d",
    );
    expect(guidePath(["a-page", "resume"], "POST")).toBe(
      "/api/guides/a-page/resume",
    );
    for (const parts of [[".."], ["a-page", "delete"], ["a page"]])
      expect(guidePath(parts, "POST")).toBeNull();
    expect(guidePath(["a-page", "resume"], "GET")).toBeNull();
  });

  it("never builds a whole story, and needs a name for an arc or character", () => {
    const asked = (part: Partial<Intent>): Intent => ({
      kind: "summary",
      story: "Lantern Marsh",
      subject: "",
      wikipedia_title: "",
      ...part,
    });
    expect(canBuild(asked({}))).toBe(true);
    expect(canBuild(asked({ kind: "story" }))).toBe(false);
    expect(canBuild(asked({ kind: "unclear" }))).toBe(false);
    expect(canBuild(asked({ kind: "character" }))).toBe(false);
    expect(canBuild(asked({ kind: "character", subject: "Wren" }))).toBe(true);
    expect(canBuild(asked({ story: " " }))).toBe(false);
  });

  it("accepts only Wikipedia page links", () => {
    expect(isWikipediaPage("")).toBe(true);
    expect(isWikipediaPage("https://ja.wikipedia.org/wiki/Lamp")).toBe(true);
    expect(isWikipediaPage("https://de.wikipedia.org/wiki/Lamp")).toBe(false);
    expect(isWikipediaPage("https://wiki.example.org/wiki/Lamp")).toBe(false);
  });
});
