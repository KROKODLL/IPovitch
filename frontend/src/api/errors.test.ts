import { describe, expect, it } from "vitest";
import { API_UNREACHABLE, isApiUnreachable } from "./errors";

describe("isApiUnreachable", () => {
  it("returns true for API_UNREACHABLE error", () => {
    expect(isApiUnreachable(new Error(API_UNREACHABLE))).toBe(true);
  });

  it("returns false for other errors", () => {
    expect(isApiUnreachable(new Error("other"))).toBe(false);
  });

  it("returns false for non-errors", () => {
    expect(isApiUnreachable("x")).toBe(false);
  });
});
