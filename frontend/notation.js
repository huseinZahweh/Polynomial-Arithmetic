/**
 * @fileoverview Client-side BigInt polynomial parsing, formatting, safe math typography (`<sup>`/`<sub>`),
 * gliding navigation indicator, and elevated pop-up error modal utilities.
 *
 * Original Author: Ali Zahreddine - Milestone 4, Integration & Milestone 6 (Waves 1-4).
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
  hex: { label: "Hexadecimal", field: "hex", example: "57" },
  binary: { label: "Binary", field: "bin", example: "01010111" },
  algebraic: { label: "Polynomial", field: "poly", example: "x^6 + x^4 + 1" },
};

const UNICODE_SUP_MAP = {
  "⁰": "0", "¹": "1", "²": "2", "³": "3", "⁴": "4",
  "⁵": "5", "⁶": "6", "⁷": "7", "⁸": "8", "⁹": "9",
  "⁻": "−", "⁺": "+", "ⁱ": "i", "ᵐ": "m", "ⁿ": "n",
};

const UNICODE_SUB_MAP = {
  "₀": "0", "₁": "1", "₂": "2", "₃": "3", "₄": "4",
  "₅": "5", "₆": "6", "₇": "7", "₈": "8", "₉": "9", "ᵢ": "i",
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
    throw new Error(binary ? "Use the digits 0 and 1." : "Use hexadecimal digits 0-9 and A-F.");
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

/**
 * Tokenize a single mathematical expression string into safe DOM text, `<sup>`, and `<sub>` nodes.
 *
 * Converts ASCII and Unicode exponents (`x^4`, `2^163`, `x^-1`, `x^(2^i)`, `GF(2^m)`, `⁸`, `⁻¹`)
 * into real `<sup>` nodes, and converts braced/underscored subscripts (`b_{m-1}`, `Z_2`, `b_i`) plus
 * standalone variable indices (`A1`-`A3`, `B1`-`B3`, `T1`-`T3`, `b0`-`b7`, `a0`-`a7`, `₀`-`₉`)
 * into real `<sub>` nodes without corrupting braced or multi-digit hexadecimal constants.
 *
 * Never uses `innerHTML`; strictly constructs nodes with `document.createTextNode` and
 * `document.createElement("sup" | "sub")`.
 *
 * @param {string | number} rawText - Input mathematical label or expression.
 * @returns {DocumentFragment} Safe DOM fragment ready for insertion.
 */
export function mathFragment(rawText) {
  const frag = document.createDocumentFragment();
  const str = String(rawText ?? "");
  if (!str) return frag;

  // Ordered pattern matching parenthesized/braced/simple exponents, unicode scripts, subscripts, and variable indices.
  const tokenRegex = new RegExp([
    "([A-Za-z0-9)\\]}])\\^\\(([^)]+)\\)",
    "\\^\\{([^}]+)\\}",
    "([A-Za-z0-9)\\]}])\\^(-?\\d+|[imdnkp])(?![A-Za-z0-9_])",
    "([⁻⁺⁰¹²³⁴⁵⁶⁷⁸⁹ⁱᵐⁿ]+)",
    "([A-Za-z])_\\{([^}]+)\\}",
    "([A-Za-z])_([A-Za-z0-9]+)",
    "(?<![A-Za-z0-9_{])([ABT])([123])(?![A-Za-z0-9_}])",
    "(?<![A-Za-z0-9_{])([ab])([0-7])(?![A-Za-z0-9_}])",
    "([₀₁₂₃₄₅₆₇₈₉ᵢ]+)",
  ].join("|"), "g");

  let lastIndex = 0;
  let match;
  while ((match = tokenRegex.exec(str)) !== null) {
    if (match.index > lastIndex) {
      frag.append(document.createTextNode(str.slice(lastIndex, match.index)));
    }
    if (match[1] !== undefined) {
      // Base + parenthesized exponent e.g. x^(2^i) or x^(d-m)
      frag.append(document.createTextNode(match[1]));
      const sup = document.createElement("sup");
      sup.append(mathFragment(match[2].replace(/^-|(?<= )-|\s-(?=[A-Za-z0-9])/g, "−")));
      frag.append(sup);
    } else if (match[3] !== undefined) {
      // Braced exponent e.g. x^{-1} or x^{d-m}
      const sup = document.createElement("sup");
      sup.append(mathFragment(match[3].replace(/^-/, "−")));
      frag.append(sup);
    } else if (match[4] !== undefined) {
      // Simple exponent e.g. 2^163, x^4, x^-1, {95}^-1
      frag.append(document.createTextNode(match[4]));
      const sup = document.createElement("sup");
      sup.textContent = match[5].replace(/^-/, "−");
      frag.append(sup);
    } else if (match[6] !== undefined) {
      // Unicode superscripts e.g. ⁻¹, ⁸, ⁱ, ᵐ
      const sup = document.createElement("sup");
      sup.textContent = Array.from(match[6], ch => UNICODE_SUP_MAP[ch] ?? ch).join("");
      frag.append(sup);
    } else if (match[7] !== undefined) {
      // Braced subscript e.g. b_{m-1} or E_{2^m}
      frag.append(document.createTextNode(match[7]));
      const sub = document.createElement("sub");
      sub.append(mathFragment(match[8]));
      frag.append(sub);
    } else if (match[9] !== undefined) {
      // Underscored subscript e.g. Z_2, B_i
      frag.append(document.createTextNode(match[9]));
      const sub = document.createElement("sub");
      sub.textContent = match[10];
      frag.append(sub);
    } else if (match[11] !== undefined) {
      // Extended Euclid variables A1..A3, B1..B3, T1..T3
      frag.append(document.createTextNode(match[11]));
      const sub = document.createElement("sub");
      sub.textContent = match[12];
      frag.append(sub);
    } else if (match[13] !== undefined) {
      // Bit indices b0..b7, a0..a7
      frag.append(document.createTextNode(match[13]));
      const sub = document.createElement("sub");
      sub.textContent = match[14];
      frag.append(sub);
    } else if (match[15] !== undefined) {
      // Unicode subscripts e.g. ₀..₉, ᵢ
      const sub = document.createElement("sub");
      sub.textContent = Array.from(match[15], ch => UNICODE_SUB_MAP[ch] ?? ch).join("");
      frag.append(sub);
    }
    lastIndex = tokenRegex.lastIndex;
  }
  if (lastIndex < str.length) {
    frag.append(document.createTextNode(str.slice(lastIndex)));
  }
  return frag;
}

/**
 * Append math-formatted (`<sup>`/`<sub>`) text into an existing DOM container.
 *
 * @param {HTMLElement} node - Target container node.
 * @param {string | number} text - Mathematical text to append.
 * @returns {HTMLElement} The target node for chaining.
 */
export function appendMathText(node, text) {
  node.append(mathFragment(text));
  return node;
}

/**
 * Replace a DOM element's children with math-formatted (`<sup>`/`<sub>`) nodes.
 *
 * @param {HTMLElement} node - Target DOM element.
 * @param {string | number} text - Mathematical text to render inside `node`.
 * @returns {HTMLElement} The target node for chaining.
 */
export function setMathText(node, text) {
  node.replaceChildren(mathFragment(text));
  return node;
}

/**
 * Create a DOM element whose contents are formatted with true `<sup>` and `<sub>` nodes.
 *
 * @param {string} tag - HTML tag name.
 * @param {string | number} text - Mathematical expression or label.
 * @param {string} [className] - Optional CSS class name(s).
 * @returns {HTMLElement} Populated DOM element.
 */
export function mathElement(tag, text, className) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.append(mathFragment(text));
  return node;
}

/**
 * Attach a smoothly gliding highlight pill (`.sliding-pill`) inside any navigation strip,
 * segmented bar, or button group matching `activeSelector`.
 *
 * Positions an `aria-hidden` pill behind the currently active item using CSS `transform`
 * and `width`/`height` transitions, updating on resize and layout changes.
 *
 * @param {HTMLElement | null} container - Navigation or segmented button container.
 * @param {string} activeSelector - CSS selector matching the active child element.
 * @returns {{update: () => void}} Controller handle with `update()` to glide to the active item.
 */
export function attachSlidingIndicator(container, activeSelector) {
  if (!container) return { update() { } };
  container.classList.add("has-sliding-pill");

  let pill = container.querySelector(":scope > .sliding-pill");
  if (!pill) {
    pill = document.createElement("span");
    pill.className = "sliding-pill";
    pill.setAttribute("aria-hidden", "true");
    pill.style.opacity = "0";
    container.prepend(pill);
  }

  function syncGeometry() {
    if (!pill.isConnected) {
      container.prepend(pill);
    }
    const active = container.querySelector(activeSelector);
    if (!active || active.offsetWidth === 0 || active.offsetHeight === 0) {
      pill.style.opacity = "0";
      return;
    }
    pill.style.opacity = "1";
    pill.style.width = active.offsetWidth + "px";
    pill.style.height = active.offsetHeight + "px";
    pill.style.transform = "translate3d(" + active.offsetLeft + "px, " + active.offsetTop + "px, 0)";
  }

  function snapGeometry() {
    pill.style.transition = "none";
    syncGeometry();
    // Force reflow before re-enabling transitions so viewport resizes and first reveal snap within bounds.
    pill.getBoundingClientRect();
    pill.style.transition = "";
  }

  function update() {
    const wasHidden = pill.style.opacity === "0";
    if (wasHidden) {
      snapGeometry();
    } else {
      syncGeometry();
    }
    // Re-measure on next animation frame in case fonts/tabs just finished revealing.
    if (typeof window.requestAnimationFrame === "function") {
      window.requestAnimationFrame(wasHidden ? snapGeometry : syncGeometry);
    }
  }

  if (typeof ResizeObserver === "function" && !container.dataset.pillObserved) {
    container.dataset.pillObserved = "true";
    const observer = new ResizeObserver(() => snapGeometry());
    observer.observe(container);
    window.addEventListener("resize", snapGeometry);
  }

  update();
  return { update };
}

/**
 * Display any validation, file-upload, exploration, or mathematical error in a prominent
 * top-level `<dialog id="error-popup">` overlay with `<sup>`/`<sub>` typography and optional trace jump.
 *
 * @param {{title?: string, message: string, onViewTrace?: () => void}} options - Popup display config.
 */
export function showErrorPopup({ title = "Error", message, onViewTrace } = {}) {
  const dialog = document.getElementById("error-popup");
  const titleEl = document.getElementById("error-popup-title");
  const bodyEl = document.getElementById("error-popup-body");
  const traceBtn = document.getElementById("error-popup-trace");
  const okBtn = document.getElementById("error-popup-ok");
  if (!dialog || !titleEl || !bodyEl || !okBtn) return;

  if (!dialog.dataset.bound) {
    dialog.dataset.bound = "true";
    okBtn.addEventListener("click", () => dialog.close());
    dialog.addEventListener("click", event => {
      if (event.target === dialog) dialog.close();
    });
    dialog.addEventListener("cancel", () => dialog.close());
  }

  setMathText(titleEl, title);
  setMathText(bodyEl, message || "An unexpected error occurred.");

  if (traceBtn) {
    if (typeof onViewTrace === "function") {
      traceBtn.hidden = false;
      traceBtn.onclick = () => {
        dialog.close();
        onViewTrace();
      };
    } else {
      traceBtn.hidden = true;
      traceBtn.onclick = null;
    }
  }

  if (!dialog.open) dialog.showModal();
  okBtn.focus({ preventScroll: true });
}

/**
 * Programmatically dismiss the pop-up error modal if currently open.
 */
export function closeErrorPopup() {
  const dialog = document.getElementById("error-popup");
  if (dialog?.open) dialog.close();
}

let feedbackHideTimer = null;
let feedbackFadeTimer = null;

/**
 * Copy plain text to the clipboard using `navigator.clipboard.writeText` with a reliable
 * hidden `<textarea>` + `document.execCommand("copy")` fallback across browser contexts.
 *
 * @param {string} text - Plain text string to copy.
 * @returns {Promise<boolean>} True when the text was placed on the clipboard.
 */
export async function copyToClipboard(text) {
  const str = String(text ?? "");
  if (navigator.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(str);
      return true;
    } catch {
      /* Fall back to hidden textarea + execCommand when Clipboard API permission is restricted. */
    }
  }
  const helper = document.createElement("textarea");
  helper.value = str;
  helper.setAttribute("readonly", "");
  helper.style.position = "fixed";
  helper.style.top = "-9999px";
  helper.style.left = "-9999px";
  helper.style.opacity = "0";
  document.body.append(helper);
  helper.focus({ preventScroll: true });
  helper.select();
  helper.setSelectionRange(0, str.length);
  let copied = false;
  try {
    copied = document.execCommand("copy");
  } catch {
    copied = false;
  } finally {
    helper.remove();
  }
  return copied;
}

/**
 * Display a non-blocking bottom-right confirmation toast (`#feedback-popup`) that slides in
 * smoothly and auto-dismisses after 2800 ms (or immediately when dismissed manually).
 *
 * @param {string} title - Bold primary message (e.g. `"Copied to clipboard"`).
 * @param {string} [detail=""] - Optional secondary detail line (e.g. filename or action label).
 * @param {"success" | "info" | "warning"} [variant="success"] - Visual status accent variant.
 */
export function showFeedbackPopup(title, detail = "", variant = "success") {
  const toast = document.getElementById("feedback-popup");
  if (!toast) return;

  if (feedbackHideTimer) {
    clearTimeout(feedbackHideTimer);
    feedbackHideTimer = null;
  }
  if (feedbackFadeTimer) {
    clearTimeout(feedbackFadeTimer);
    feedbackFadeTimer = null;
  }

  const iconChar = variant === "warning" ? "!" : variant === "info" ? "i" : "✓";
  const badge = element("span", iconChar, "feedback-popup-icon");
  badge.setAttribute("aria-hidden", "true");

  const body = element("div", undefined, "feedback-popup-content");
  body.append(mathElement("strong", title, "feedback-popup-title"));
  if (detail) {
    body.append(mathElement("span", detail, "feedback-popup-detail"));
  }

  const dismissBtn = element("button", "×", "feedback-popup-close");
  dismissBtn.type = "button";
  dismissBtn.setAttribute("aria-label", "Dismiss notification");
  dismissBtn.addEventListener("click", () => {
    if (feedbackHideTimer) {
      clearTimeout(feedbackHideTimer);
      feedbackHideTimer = null;
    }
    if (feedbackFadeTimer) {
      clearTimeout(feedbackFadeTimer);
      feedbackFadeTimer = null;
    }
    toast.classList.remove("is-visible", "is-closing");
    toast.hidden = true;
  });

  toast.dataset.variant = variant;
  toast.replaceChildren(badge, body, dismissBtn);
  toast.classList.remove("is-closing");
  toast.hidden = false;
  toast.classList.add("is-visible");

  feedbackHideTimer = setTimeout(() => {
    feedbackHideTimer = null;
    toast.classList.remove("is-visible");
    toast.classList.add("is-closing");
    feedbackFadeTimer = setTimeout(() => {
      feedbackFadeTimer = null;
      toast.classList.remove("is-closing");
      toast.hidden = true;
    }, 220);
  }, 2800);
}
