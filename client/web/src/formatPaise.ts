/**
 * Format integer paise as rupees: en-IN digit grouping, exactly two decimals,
 * integer maths only (no floating-point division of the amount).
 *
 *   formatPaise(199999)   === "₹1,999.99"
 *   formatPaise(12345678) === "₹1,23,456.78"
 *   formatPaise(5)        === "₹0.05"
 *   formatPaise(0)        === "₹0.00"
 *
 * Throws an Error if `paise` is not an integer.
 */
export function formatPaise(paise: number): string {
  if (typeof paise !== "number" || !Number.isSafeInteger(paise)) {
    throw new Error(`formatPaise: expected an integer number of paise, got ${String(paise)}`);
  }
  // BigInt keeps every step exact; no division produces a fraction.
  const negative = paise < 0;
  const abs = BigInt(paise) * (negative ? -1n : 1n);
  const rupees = (abs / 100n).toString();
  const fraction = (abs % 100n).toString().padStart(2, "0");
  return `${negative ? "-" : ""}₹${groupIndian(rupees)}.${fraction}`;
}

/** 1234567 -> "12,34,567": last three digits, then pairs. */
function groupIndian(digits: string): string {
  if (digits.length <= 3) return digits;
  const head = digits.slice(0, -3);
  const tail = digits.slice(-3);
  const pairs: string[] = [];
  for (let end = head.length; end > 0; end -= 2) {
    pairs.unshift(head.slice(Math.max(0, end - 2), end));
  }
  return `${pairs.join(",")},${tail}`;
}
