import { describe, expect, it } from "vitest";
import { unwrap } from "@/shared/api/envelope";

describe("unwrap", () => {
  it("returns the .data field when present", () => {
    expect(unwrap<number[]>({ data: [1, 2], traceId: "t" })).toEqual([1, 2]);
  });

  it("returns a bare array unchanged", () => {
    expect(unwrap<number[]>([1, 2, 3])).toEqual([1, 2, 3]);
  });

  it("returns a primitive unchanged", () => {
    expect(unwrap<string>("hello")).toBe("hello");
  });
});
