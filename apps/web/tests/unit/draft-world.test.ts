import { describe, expect, it } from "vitest";
import { DRAFT_NOTE, isDraftWorld } from "@/features/narrative/draft";

describe("draft worlds", () => {
  it("recognises only the -draft suffix and never claims verification", () => {
    expect(isDraftWorld("sample-draft")).toBe(true);
    expect(isDraftWorld("sample")).toBe(false);
    expect(isDraftWorld("drafting-table")).toBe(false);
    expect(isDraftWorld(undefined)).toBe(false);
    expect(DRAFT_NOTE).toContain("not verified");
  });
});
