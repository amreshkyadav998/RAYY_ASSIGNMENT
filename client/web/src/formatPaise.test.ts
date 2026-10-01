import { describe, expect, it } from "vitest";
import { formatPaise } from "./formatPaise";

describe("formatPaise", () => {
  it.each([
    [0, "₹0.00"],
    [5, "₹0.05"],
    [99, "₹0.99"],
    [100, "₹1.00"],
    [19999, "₹199.99"],
    [99999, "₹999.99"],
    [100000, "₹1,000.00"],
    [199999, "₹1,999.99"],
    [1000000, "₹10,000.00"],
    [12345678, "₹1,23,456.78"],
    [1234567800, "₹1,23,45,678.00"],
    [123456789000, "₹1,23,45,67,890.00"],
  ])("formats %i as %s", (paise, expected) => {
    expect(formatPaise(paise)).toBe(expected);
  });

  it("formats negative amounts with a leading minus", () => {
    expect(formatPaise(-12345)).toBe("-₹123.45");
  });

  it.each([1.5, 0.1, NaN, Infinity, -Infinity, Number.MAX_SAFE_INTEGER + 2])("throws on %s", (bad) => {
    expect(() => formatPaise(bad)).toThrow();
  });

  it("throws on non-numbers", () => {
    expect(() => formatPaise("100" as unknown as number)).toThrow();
    expect(() => formatPaise(null as unknown as number)).toThrow();
  });
});
