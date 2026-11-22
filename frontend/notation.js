/**
 * @fileoverview Client-side BigInt polynomial parsing, formatting, and DOM helper utilities.
 *
 * Original Author: Ali Zahreddine — Milestone 4 & Integration (Educational Web GUI).
 *
 * Uses JavaScript arbitrary-precision `BigInt` so live input validation, base
 * conversion, polynomial preview, and bit-builder toggling stay exact across all
 * supported degrees up to GF(2^571) (Stallings Chapter 4 polynomial basis,
 * Chapter 5 AES byte hex notation, Chapter 6 XTS-AES, and Chapter 10 binary ECC).
 */

/**
 * Display metadata for each supported operand and result notation.
 * @type {Record<"hex" | "binary" | "algebraic", {label: string, field: string, example: string}>}
 */
export const bases = {
  hex: {label: "Hexadecimal", field: "hex", example: "57"},
  binary: {label: "Binary", field: "bin", example: "01010111"},
  algebraic: {label: "Polynomial", field: "poly", example: "x^6 + x^4 + 1"},
};

/**
 * Parse a user-entered polynomial string in hex, binary, or algebraic notation into a BigInt.
 *
 * Mirrors the server's strict validation rules (`backend.engine.polyrepr.parse_value`):
 * strips matching `{...}` braces (Stallings Ch. 5 notation) and optional `0x`/`0b` prefixes,
 * cancels duplicate algebraic monomials modulo 2 via XOR, and enforces the 4096-bit cap.
 *
 * Complexity: O(n) time and space in input length `n`.
 *
 * @param {string} text - Raw user input string.
 * @param {"hex" | "binary" | "algebraic"} base - Active input notation.
 * @returns {bigint} Non-negative polynomial bitmask.
 * @throws {Error} When characters, monomial syntax, or bit width (> 4096) are invalid.
 */
export function parseOperand(text, base) {
  if (base === "algebraic") {
    let value = 0n;
    for (const raw of text.toLowerCase().split("+")) {
      const term = raw.trim();
      if (term === "0") continue;
      const match = /^x\s*\^\s*([0-9]{1,4})$/.exec(term);
      const exponent = term === "1" ? 0 : term === "x" ? 1 : Number(match?.[1]);
      if (!Number.isInteger(exponent) || exponent >= 4096) {
        throw new Error("Use polynomial terms like x^7 + x + 1, with exponents below 4096.");
      }
      // Characteristic-2 cancellation: repeating x^k XORs it back to 0.
      value ^= 1n << BigInt(exponent);
    }
    return value;
  }
  let digits = text.trim();
  if (digits.startsWith("{") && digits.endsWith("}")) digits = digits.slice(1, -1).trim();
  const binary = base === "binary";
  digits = digits.replace(binary ? /^0b/i : /^0x/i, "");
  if (!(binary ? /^[01]+$/ : /^[\da-f]+$/i).test(digits)) {
    throw new Error(binary ? "Use the digits 0 and 1." : "Use hexadecimal digits 0–9 and A–F.");
  }
  const value = BigInt((binary ? "0b" : "0x") + digits);
  if (value.toString(2).length > 4096) throw new Error("Enter at most 4096 bits.");
  return value;
}

/**
 * Compute the polynomial degree of a non-negative BigInt bitmask.
 *
 * Complexity: O(m) in bit length `m`.
 *
 * @param {bigint} value - Non-negative polynomial bitmask.
 * @returns {number} Highest set-bit exponent, or `-1` for the zero polynomial `0n`.
 */
export function degreeOf(value) {
  return value === 0n ? -1 : value.toString(2).length - 1;
}

/**
 * Strip leading zeros from a hex or binary string while preserving a single `"0"`.
 *
 * Used for compact large-field result previews and concise step equations.
 *
 * @param {string} text - Zero-padded hex or binary representation.
 * @returns {string} Compact digit string without leading padding zeros.
 */
export function significantDigits(text) {
  return text.replace(/^0+(?=.)/, "");
}

/**
 * Render a BigInt polynomial bitmask in descending algebraic notation (e.g. `"x^6 + x^4 + 1"`).
 *
 * Complexity: O(m) time and space in bit length `m`.
 *
 * @param {bigint} value - Non-negative polynomial bitmask.
 * @returns {string} Algebraic polynomial string, or `"0"` when `value === 0n`.
 */
export function polynomial(value) {
  const digits = value.toString(2);
  const terms = [];
  for (let i = 0; i < digits.length; i += 1) {
    const exponent = digits.length - i - 1;
    if (digits[i] === "1") terms.push(exponent > 1 ? "x^" + exponent : exponent ? "x" : "1");
  }
  return terms.join(" + ") || "0";
}

/**
 * Format a BigInt bitmask in hex, binary, or algebraic notation padded to field degree `m`.
 *
 * Complexity: O(max(m, bit_length)) time and space.
 *
 * @param {bigint} value - Non-negative polynomial bitmask.
 * @param {"hex" | "binary" | "algebraic"} base - Target display notation.
 * @param {number} m - Extension field degree used for zero-padding hex (`ceil(m/4)`) or binary (`m`).
 * @returns {string} Formatted operand string.
 */
export function formatOperand(value, base, m) {
  if (base === "algebraic") return polynomial(value);
  if (base === "binary") return value.toString(2).padStart(m, "0");
  return value.toString(16).toUpperCase().padStart(Math.ceil(m / 4), "0");
}

/**
 * Create a DOM element with optional plain text content and CSS class name.
 *
 * Uses `textContent` (never `innerHTML`) so all backend/user strings render safely.
 *
 * @param {string} tag - HTML tag name (e.g. `"button"`, `"td"`, `"section"`).
 * @param {string | number} [text] - Optional text assigned via `textContent`.
 * @param {string} [className] - Optional CSS class list.
 * @returns {HTMLElement} Newly created DOM node.
 */
export function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}
