export const bases = {
  hex: {label: "Hexadecimal", field: "hex", example: "57"},
  binary: {label: "Binary", field: "bin", example: "01010111"},
  algebraic: {label: "Polynomial", field: "poly", example: "x^6 + x^4 + 1"},
};

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

export function degreeOf(value) {
  return value === 0n ? -1 : value.toString(2).length - 1;
}

export function significantDigits(text) {
  return text.replace(/^0+(?=.)/, "");
}

export function polynomial(value) {
  const digits = value.toString(2);
  const terms = [];
  for (let i = 0; i < digits.length; i += 1) {
    const exponent = digits.length - i - 1;
    if (digits[i] === "1") terms.push(exponent > 1 ? "x^" + exponent : exponent ? "x" : "1");
  }
  return terms.join(" + ") || "0";
}

export function formatOperand(value, base, m) {
  if (base === "algebraic") return polynomial(value);
  if (base === "binary") return value.toString(2).padStart(m, "0");
  return value.toString(16).toUpperCase().padStart(Math.ceil(m / 4), "0");
}

export function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}
