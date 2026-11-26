/**
 * @fileoverview Client-side BigInt polynomial parsing, uniform ASCII `x^k` & auto-uppercase
 * input formatting, safe math typography (`<sup>`/`<sub>`), gliding navigation indicator,
 * top-center floating error alert, Full-Value Inspector popup, and step derivation popup.
 *
 * Original Author: Ali Zahreddine - Milestone 4, Integration & Milestone 6 (Waves 1-4).
 *
 * Uses JavaScript arbitrary-precision `BigInt` so live input validation, base
 * conversion, polynomial preview, bit-builder toggling, and interactive step derivations
 * stay exact across all supported degrees up to GF(2^571) (Stallings Chapter 4 polynomial
 * basis, Chapter 6 XTS-AES, and Chapter 10 binary ECC).
 */

/**
 * Display metadata for each supported operand and result notation.
 * @type {Record<"hex" | "binary" | "algebraic", {label: string, field: string, example: string}>}
 */
export const bases = {
  hex: { label: "Hexadecimal", field: "hex", example: "Enter hexadecimal value" },
  binary: { label: "Binary", field: "bin", example: "Enter binary value" },
  algebraic: { label: "Polynomial", field: "poly", example: "Enter polynomial" },
};

const DIGIT_TO_SUP = {
  "0": "⁰", "1": "¹", "2": "²", "3": "³", "4": "⁴",
  "5": "⁵", "6": "⁶", "7": "⁷", "8": "⁸", "9": "⁹",
};

const SUP_TO_DIGIT = {
  "⁰": "0", "¹": "1", "²": "2", "³": "3", "⁴": "4",
  "⁵": "5", "⁶": "6", "⁷": "7", "⁸": "8", "⁹": "9",
};

const UNICODE_SUP_MAP = {
  ...SUP_TO_DIGIT,
  "⁻": "−", "⁺": "+", "ⁱ": "i", "ᵐ": "m", "ⁿ": "n", "ʲ": "j",
};

const UNICODE_SUB_MAP = {
  "₀": "0", "₁": "1", "₂": "2", "₃": "3", "₄": "4",
  "₅": "5", "₆": "6", "₇": "7", "₈": "8", "₉": "9", "ᵢ": "i", "ⱼ": "j",
};

/**
 * Convert an ASCII digit string (e.g. `"163"`) into Unicode superscript digits (`"¹⁶³"`).
 *
 * @param {string | number} digits - Non-negative integer or ASCII digit string.
 * @returns {string} Unicode superscript string.
 */
export function toSuperscriptDigits(digits) {
  return String(digits).replace(/[0-9]/g, ch => DIGIT_TO_SUP[ch] ?? ch);
}

/**
 * Format a polynomial string for display inside `<input>` boxes using Unicode superscript
 * exponents (e.g. `"x^6 + x^4 + 1"` -> `"x⁶ + x⁴ + 1"`), normalizing variable `X` to lowercase `x`
 * and seamlessly promoting digits typed immediately after existing superscript digits.
 *
 * @param {string} text - Raw or partially formatted polynomial text.
 * @returns {string} Display string with raised Unicode exponents.
 */
export function formatPolyWithSuperscripts(text) {
  let out = String(text ?? "").replace(/X/g, "x");
  out = out.replace(/x\s*\^\s*([0-9]+)/g, (_, digits) => "x" + toSuperscriptDigits(digits));
  // Promote digits typed directly after superscript digits (e.g. typing "x^163" one key at a time).
  out = out.replace(/([⁰¹²³⁴⁵⁶⁷⁸⁹]+)([0-9]+)/g, (_, sups, digits) => sups + toSuperscriptDigits(digits));
  return out;
}

/**
 * Normalize a polynomial string containing Unicode superscripts (e.g. `"x⁶ + x⁴ + 1"`)
 * back into plain ASCII `x^k` notation (`"x^6 + x^4 + 1"`) for parsing, API requests,
 * exports, and share links.
 *
 * @param {string} text - Polynomial input text (ASCII `^` or Unicode superscripts).
 * @returns {string} Plain ASCII polynomial text with lowercase `x` and `^` exponents.
 */
export function normalizeAlgebraicInput(text) {
  let out = String(text ?? "").replace(/X/g, "x");
  out = out.replace(/x\s*([⁰¹²³⁴⁵⁶⁷⁸⁹]+)/g, (_, sups) => {
    const digits = Array.from(sups, ch => SUP_TO_DIGIT[ch] ?? ch).join("");
    return "x^" + digits;
  });
  out = out.replace(/[⁰¹²³⁴⁵⁶⁷⁸⁹]/g, ch => SUP_TO_DIGIT[ch] ?? ch);
  return out;
}

/**
 * Apply live notation-aware formatting to a text `<input>` element while preserving caret position:
 *   - `"hex"`: auto-uppercases typed or pasted hex letters (`a-f` -> `A-F`).
 *   - `"algebraic"`: keeps variable `x` lowercase and normalizes pasted Unicode superscripts (`x¹³⁸`)
 *     into uniform non-wavy ASCII caret notation (`x^138`).
 *
 * @param {HTMLInputElement | null} inputEl - Target text input element.
 * @param {"hex" | "binary" | "algebraic"} mode - Active notation mode.
 */
export function applyInputFormatting(inputEl, mode) {
  if (!inputEl) return;
  inputEl.classList.remove("is-algebraic-input");
  const raw = inputEl.value;
  let formatted = raw;
  if (mode === "hex") {
    formatted = raw.replace(/[a-f]/g, ch => ch.toUpperCase());
  } else if (mode === "algebraic") {
    formatted = normalizeAlgebraicInput(raw);
  }
  if (formatted === raw) return;

  const isFocused = document.activeElement === inputEl;
  const selStart = inputEl.selectionStart;
  const selEnd = inputEl.selectionEnd;
  inputEl.value = formatted;

  if (isFocused && selStart !== null && selEnd !== null) {
    try {
      if (mode === "algebraic") {
        const nextStart = normalizeAlgebraicInput(raw.slice(0, selStart)).length;
        const nextEnd = normalizeAlgebraicInput(raw.slice(0, selEnd)).length;
        inputEl.setSelectionRange(nextStart, nextEnd);
      } else {
        inputEl.setSelectionRange(selStart, selEnd);
      }
    } catch {
      /* Ignore selection errors on unsupported input types. */
    }
  }
}

/**
 * Attach a crisp, non-wavy HTML `<sup>` display overlay onto a polynomial text `<input>`.
 *
 * Whenever `isPolyModeFn()` returns `true` and the input is unfocused with non-empty text,
 * renders the normalized polynomial inside an `aria-hidden` sibling `.poly-input-overlay`
 * via `appendMathText` (true `<sup>` nodes) while keeping `<input>.value` as plain ASCII `x^k`.
 * Focusing the input hides the overlay immediately for exact native cursor editing, and
 * blurring snaps it right back to crisp `<sup>` powers.
 *
 * @param {HTMLInputElement | null} inputEl - Target text input element.
 * @param {() => boolean} isPolyModeFn - Predicate returning `true` when Polynomial mode is active.
 * @returns {{sync: () => void}} Controller whose `sync()` refreshes the overlay state.
 */
export function attachPolyInputOverlay(inputEl, isPolyModeFn) {
  if (!inputEl) return { sync() { } };

  let wrap = inputEl.parentElement;
  if (!wrap || !wrap.classList.contains("poly-input-wrap")) {
    wrap = document.createElement("span");
    wrap.className = "poly-input-wrap";
    inputEl.parentNode?.insertBefore(wrap, inputEl);
    wrap.append(inputEl);
  }

  let overlay = wrap.querySelector(":scope > .poly-input-overlay");
  if (!overlay) {
    overlay = document.createElement("span");
    overlay.className = "poly-input-overlay";
    overlay.setAttribute("aria-hidden", "true");
    overlay.hidden = true;
    wrap.append(overlay);
  }

  /** Synchronize overlay visibility and rendered `<sup>` DOM nodes with input state. */
  function sync() {
    const raw = inputEl.value;
    const active = Boolean(isPolyModeFn())
      && document.activeElement !== inputEl
      && !inputEl.disabled
      && raw.trim().length > 0;
    if (active) {
      const textSpan = document.createElement("span");
      textSpan.className = "poly-input-overlay-text";
      appendMathText(textSpan, normalizeAlgebraicInput(raw));
      overlay.replaceChildren(textSpan);
      overlay.classList.toggle("is-invalid", inputEl.getAttribute("aria-invalid") === "true");
      overlay.hidden = false;
      inputEl.classList.add("has-poly-overlay");
    } else {
      overlay.hidden = true;
      overlay.replaceChildren();
      inputEl.classList.remove("has-poly-overlay");
    }
  }

  if (!inputEl.dataset.polyOverlayBound) {
    inputEl.dataset.polyOverlayBound = "true";
    inputEl.addEventListener("focus", () => {
      overlay.hidden = true;
      inputEl.classList.remove("has-poly-overlay");
    });
    inputEl.addEventListener("blur", () => sync());
  }

  sync();
  return { sync };
}

/**
 * Parse a user-entered polynomial string in hex, binary, or algebraic notation into a BigInt.
 *
 * Mirrors the server's strict validation rules (`backend.engine.polyrepr.parse_value`):
 * normalizes Unicode superscripts to ASCII `x^k`, strips matching `{...}` braces and optional
 * `0x`/`0b` prefixes, cancels duplicate algebraic monomials modulo 2 via XOR, and enforces
 * the 4096-bit cap.
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
    const normalized = normalizeAlgebraicInput(text);
    let value = 0n;
    for (const raw of normalized.toLowerCase().split("+")) {
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
 * @param {string} text - Zero-padded hex or binary representation.
 * @returns {string} Compact digit string without leading padding zeros.
 */
export function significantDigits(text) {
  return text.replace(/^0+(?=.)/, "");
}

/**
 * Render a BigInt polynomial bitmask in descending ASCII algebraic notation (e.g. `"x^6 + x^4 + 1"`).
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
 * Format a BigInt bitmask for `<input>` boxes in hex, binary, or clean ASCII `x^k` polynomial notation.
 *
 * Complexity: O(max(m, bit_length)) time and space.
 *
 * @param {bigint} value - Non-negative polynomial bitmask.
 * @param {"hex" | "binary" | "algebraic"} base - Target display notation.
 * @param {number} m - Extension field degree used for binary zero-padding (`m` bits); hex omits leading zeros.
 * @returns {string} Formatted operand string.
 */
export function formatOperand(value, base, m) {
  if (base === "algebraic") return polynomial(value);
  if (base === "binary") return value.toString(2).padStart(m, "0");
  return value.toString(16).toUpperCase();
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
 * Converts ASCII and Unicode exponents (`x^4`, `2^163`, `x^-1`, `x^(2^i)`, `α^j`, `GF(2^m)`, `⁸`, `⁻¹`)
 * into real `<sup>` nodes, and converts braced/underscored subscripts (`b_{m-1}`, `Z_2`, `b_1x`,
 * `b_i`, `P_A`, `T_j`) plus standalone variable indices (`A1`-`A3`, `B1`-`B3`, `T1`-`T3`, `b0`-`b7`,
 * `a0`-`a7`, `₀`-`₉`) into real `<sub>` nodes without corrupting adjacent variables (so `b_1x` renders
 * cleanly as `b<sub>1</sub>x`) or multi-digit hexadecimal constants.
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

  // Ordered pattern matching combined sub+sup, parenthesized/braced/simple exponents, unicode scripts, subscripts, and variable indices.
  const tokenRegex = new RegExp([
    "([A-Za-z])_([A-Za-z0-9]+)\\^(-?\\d+|[imdnkpj])(?![A-Za-z0-9_])",
    "([A-Za-z0-9)\\]}α])\\^\\(([^)]+)\\)",
    "\\^\\{([^}]+)\\}",
    "([A-Za-z0-9)\\]}α])\\^(-?\\d+|[imdnkpj])(?![A-Za-z0-9_])",
    "([⁻⁺⁰¹²³⁴⁵⁶⁷⁸⁹ⁱᵐⁿʲ]+)",
    "([A-Za-z])_\\{([^}]+)\\}",
    "([A-Za-z])_(\\d+)",
    "([A-Za-z])_([A-Za-z])(?![A-Za-z0-9_])",
    "(?<![A-Za-z0-9_{])([ABT])([123])(?![A-Za-z0-9_}])",
    "(?<![A-Za-z0-9_{])([ab])([0-7])(?![A-Za-z0-9_}])",
    "([₀₁₂₃₄₅₆₇₈₉ᵢⱼ]+)",
  ].join("|"), "g");

  let lastIndex = 0;
  let match;
  while ((match = tokenRegex.exec(str)) !== null) {
    if (match.index > lastIndex) {
      frag.append(document.createTextNode(str.slice(lastIndex, match.index)));
    }
    if (match[1] !== undefined) {
      // Combined subscript + exponent e.g. X_p^2, X_p^-1, x_1^2
      frag.append(document.createTextNode(match[1]));
      const sub = document.createElement("sub");
      sub.textContent = match[2];
      const sup = document.createElement("sup");
      sup.textContent = match[3].replace(/^-/, "−");
      frag.append(sub, sup);
    } else if (match[4] !== undefined) {
      // Base + parenthesized exponent e.g. x^(2^i) or x^(d-m)
      frag.append(document.createTextNode(match[4]));
      const sup = document.createElement("sup");
      sup.append(mathFragment(match[5].replace(/^-|(?<= )-|\s-(?=[A-Za-z0-9])/g, "−")));
      frag.append(sup);
    } else if (match[6] !== undefined) {
      // Braced exponent e.g. x^{-1} or x^{d-m}
      const sup = document.createElement("sup");
      sup.append(mathFragment(match[6].replace(/^-/, "−")));
      frag.append(sup);
    } else if (match[7] !== undefined) {
      // Simple exponent e.g. 2^163, x^4, x^-1, {95}^-1, α^j
      frag.append(document.createTextNode(match[7]));
      const sup = document.createElement("sup");
      sup.textContent = match[8].replace(/^-/, "−");
      frag.append(sup);
    } else if (match[9] !== undefined) {
      // Unicode superscripts e.g. ⁻¹, ⁸, ⁱ, ᵐ
      const sup = document.createElement("sup");
      sup.textContent = Array.from(match[9], ch => UNICODE_SUP_MAP[ch] ?? ch).join("");
      frag.append(sup);
    } else if (match[10] !== undefined) {
      // Braced subscript e.g. b_{m-1} or E_{2^m}
      frag.append(document.createTextNode(match[10]));
      const sub = document.createElement("sub");
      sub.append(mathFragment(match[11]));
      frag.append(sub);
    } else if (match[12] !== undefined) {
      // Numeric underscored subscript e.g. b_1x -> b<sub>1</sub>x, Z_2, b_127, T_0
      frag.append(document.createTextNode(match[12]));
      const sub = document.createElement("sub");
      sub.textContent = match[13];
      frag.append(sub);
    } else if (match[14] !== undefined) {
      // Single-letter underscored subscript e.g. b_i, T_j, P_A, n_B, G_x
      frag.append(document.createTextNode(match[14]));
      const sub = document.createElement("sub");
      sub.textContent = match[15];
      frag.append(sub);
    } else if (match[16] !== undefined) {
      // Extended Euclid variables A1..A3, B1..B3, T1..T3
      frag.append(document.createTextNode(match[16]));
      const sub = document.createElement("sub");
      sub.textContent = match[17];
      frag.append(sub);
    } else if (match[18] !== undefined) {
      // Bit indices b0..b7, a0..a7
      frag.append(document.createTextNode(match[18]));
      const sub = document.createElement("sub");
      sub.textContent = match[19];
      frag.append(sub);
    } else if (match[20] !== undefined) {
      // Unicode subscripts e.g. ₀..₉, ᵢ
      const sub = document.createElement("sub");
      sub.textContent = Array.from(match[20], ch => UNICODE_SUB_MAP[ch] ?? ch).join("");
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
    let lastViewportWidth = window.innerWidth;
    const observer = new ResizeObserver(() => {
      if (window.innerWidth !== lastViewportWidth) {
        lastViewportWidth = window.innerWidth;
        snapGeometry();
      } else {
        syncGeometry();
      }
    });
    observer.observe(container);
    window.addEventListener("resize", () => {
      lastViewportWidth = window.innerWidth;
      snapGeometry();
    });
  }

  update();
  return { update };
}

/**
 * Display any validation, file-upload, exploration, or mathematical error in the sleek
 * top-center floating alert card (`#error-popup`) without obscuring operand inputs underneath.
 *
 * Supports `<sup>`/`<sub>` typography, top-right `×` close button, optional trace jump,
 * and `Escape` dismissal.
 *
 * @param {{title?: string, message: string, onViewTrace?: () => void}} options - Alert display config.
 */
export function showErrorPopup({ title = "Error", message, onViewTrace } = {}) {
  const alertBox = document.getElementById("error-popup");
  const titleEl = document.getElementById("error-popup-title");
  const bodyEl = document.getElementById("error-popup-body");
  const traceBtn = document.getElementById("error-popup-trace");
  const okBtn = document.getElementById("error-popup-ok");
  const closeBtn = document.getElementById("error-popup-close");
  if (!alertBox || !titleEl || !bodyEl || !okBtn) return;

  if (!alertBox.dataset.bound) {
    alertBox.dataset.bound = "true";
    okBtn.addEventListener("click", () => closeErrorPopup());
    closeBtn?.addEventListener("click", () => closeErrorPopup());
    document.addEventListener("keydown", event => {
      if (event.key === "Escape" && !alertBox.hidden) {
        const activeDialog = document.querySelector("dialog[open]");
        if (activeDialog) return;
        event.preventDefault();
        closeErrorPopup();
      }
    });
  }

  setMathText(titleEl, title);
  setMathText(bodyEl, message || "An unexpected error occurred.");

  if (traceBtn) {
    if (typeof onViewTrace === "function") {
      traceBtn.hidden = false;
      traceBtn.onclick = () => {
        closeErrorPopup();
        onViewTrace();
      };
    } else {
      traceBtn.hidden = true;
      traceBtn.onclick = null;
    }
  }

  alertBox.hidden = false;
  alertBox.classList.remove("is-entering");
  // Trigger slide-down entrance animation cleanly on repeated errors.
  alertBox.getBoundingClientRect();
  alertBox.classList.add("is-entering");
}

/**
 * Programmatically dismiss the top-center error alert card if currently visible.
 */
export function closeErrorPopup() {
  const alertBox = document.getElementById("error-popup");
  if (alertBox && !alertBox.hidden) {
    alertBox.hidden = true;
    alertBox.classList.remove("is-entering");
  }
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

/**
 * Bind backdrop-click and close-button handlers once on a `<dialog>` popup.
 *
 * @param {HTMLDialogElement} dialog - Target modal dialog element.
 * @param {string} closeId - Primary close button ID.
 * @param {string} [secondaryCloseId] - Optional top-right `×` close button ID.
 */
function bindDialogClose(dialog, closeId, secondaryCloseId) {
  if (dialog.dataset.bound) return;
  dialog.dataset.bound = "true";
  document.getElementById(closeId)?.addEventListener("click", () => dialog.close());
  if (secondaryCloseId) {
    document.getElementById(secondaryCloseId)?.addEventListener("click", () => dialog.close());
  }
  dialog.addEventListener("click", event => {
    if (event.target === dialog) dialog.close();
  });
}

/**
 * Open the Full-Value Inspector modal (`#inspector-popup`) showing the complete untruncated
 * Hexadecimal, Binary, and Polynomial (`<sup>`) representations of a large `GF(2^m)` element,
 * with per-format Copy buttons and toast confirmation.
 *
 * @param {{title?: string, valueBigInt: bigint, mDegree?: number, subtitle?: string}} options - Value details.
 */
export function showInspectorPopup({ title = "Full value", valueBigInt, mDegree = 8, subtitle = "" }) {
  const dialog = document.getElementById("inspector-popup");
  const titleEl = document.getElementById("inspector-popup-title");
  const metaEl = document.getElementById("inspector-popup-meta");
  const bodyEl = document.getElementById("inspector-popup-body");
  if (!dialog || !titleEl || !bodyEl) return;

  bindDialogClose(dialog, "inspector-popup-close-btn", "inspector-popup-close");

  const hexStr = valueBigInt.toString(16).toUpperCase();
  const rawBin = valueBigInt.toString(2);
  const binStr = rawBin.padStart(Math.max(1, mDegree), "0");
  const polyStr = polynomial(valueBigInt);
  const deg = degreeOf(valueBigInt);
  const bitLen = valueBigInt === 0n ? 0 : rawBin.length;

  setMathText(titleEl, title);
  if (metaEl) {
    const metaParts = [];
    if (subtitle) metaParts.push(subtitle);
    metaParts.push(bitLen + " significant bits · " + (deg < 0 ? "zero polynomial" : "degree " + deg));
    setMathText(metaEl, metaParts.join(" · "));
  }

  bodyEl.replaceChildren();
  const rows = [
    { label: "Hexadecimal", text: hexStr, isMath: false },
    { label: "Binary (" + binStr.length + " bits)", text: binStr, isMath: false },
    { label: "Polynomial", text: polyStr, isMath: true },
  ];

  for (const row of rows) {
    const block = element("section", undefined, "inspector-format-block");
    const head = element("div", undefined, "inspector-format-head");
    head.append(element("h3", row.label));
    const copyBtn = element("button", "Copy", "outline inspector-copy-btn");
    copyBtn.type = "button";
    copyBtn.setAttribute("aria-label", "Copy " + row.label);
    copyBtn.addEventListener("click", async () => {
      const copied = await copyToClipboard(row.text);
      if (copied) {
        showFeedbackPopup("Copied to clipboard", row.label + " copied");
      }
    });
    head.append(copyBtn);

    const valBox = element("div", undefined, "inspector-value-box");
    if (row.isMath) setMathText(valBox, row.text);
    else valBox.textContent = row.text;

    block.append(head, valBox);
    bodyEl.append(block);
  }

  if (!dialog.open) dialog.showModal();
  document.getElementById("inspector-popup-close-btn")?.focus({ preventScroll: true });
}

/**
 * Open the Step Derivation modal (`#derivation-popup`) showing a step-specific mathematical
 * breakdown for Extended Euclid (`Q`, `T1`, `T2`, `T3`) or Shift-and-XOR (`<< 1` / `⊕ m(x)`).
 *
 * @param {{
 *   title: string,
 *   subtitle?: string,
 *   formula?: string,
 *   steps?: Array<{heading: string, lines: string[], badge?: string, tone?: string}>,
 *   result?: {label: string, value: string, detail?: string, isMath?: boolean} | null
 * }} config - Structured derivation payload.
 */
export function showDerivationPopup({ title, subtitle = "", formula = "", steps = [], result = null }) {
  const dialog = document.getElementById("derivation-popup");
  const titleEl = document.getElementById("derivation-popup-title");
  const subEl = document.getElementById("derivation-popup-subtitle");
  const bodyEl = document.getElementById("derivation-popup-body");
  if (!dialog || !titleEl || !bodyEl) return;

  bindDialogClose(dialog, "derivation-popup-close-btn", "derivation-popup-close");

  setMathText(titleEl, title);
  if (subEl) {
    setMathText(subEl, subtitle);
    subEl.hidden = !subtitle;
  }

  bodyEl.replaceChildren();
  if (formula) {
    bodyEl.append(mathElement("code", formula, "derivation-formula-banner"));
  }

  if (steps.length) {
    const list = element("div", undefined, "derivation-steps-list");
    for (const item of steps) {
      const card = element("section", undefined, "derivation-step-item" + (item.tone ? " " + item.tone : ""));
      const head = element("div", undefined, "derivation-step-head");
      head.append(mathElement("h3", item.heading));
      if (item.badge) {
        head.append(mathElement("span", item.badge, "diff-tag" + (item.tone ? " " + item.tone : "")));
      }
      card.append(head);
      const linesBox = element("div", undefined, "derivation-step-lines");
      for (const line of item.lines || []) {
        const lineNode = element("div", undefined, "derivation-line");
        appendMathText(lineNode, line);
        linesBox.append(lineNode);
      }
      card.append(linesBox);
      list.append(card);
    }
    bodyEl.append(list);
  }

  if (result) {
    const resBox = element("section", undefined, "derivation-result-box");
    resBox.append(mathElement("span", result.label, "derivation-result-label"));
    const valEl = result.isMath
      ? mathElement("div", result.value, "derivation-result-val")
      : element("div", result.value, "derivation-result-val");
    resBox.append(valEl);
    if (result.detail) {
      resBox.append(mathElement("p", result.detail, "derivation-result-detail"));
    }
    bodyEl.append(resBox);
  }

  if (!dialog.open) dialog.showModal();
  document.getElementById("derivation-popup-close-btn")?.focus({ preventScroll: true });
}
