/**
 * @fileoverview Main controller for the Finite Field Lab educational calculator workbench.
 *
 * Original Author: Ali Zahreddine - Milestone 4, Integration & Milestone 6 (Waves 1-4).
 *
 * Orchestrates all six core REST endpoints (`/api/fields`, `/api/calculate`,
 * `/api/random-polynomials`, `/api/parse-polynomials`, `/api/export-calculation`,
 * `/api/tutorial`), live BigInt operand validation and notation switching, the dynamic
 * read-only Modulus m(x) card on unary ops (`modulo`, `inverse`), true HTML `<sup>`/`<sub>`
 * math typography, pop-up error alerts (`#error-popup`), confirmation toasts (`#feedback-popup`),
 * drag-and-drop upload modal (`#upload-modal`), gliding navigation indicators,
 * `m <= 8` coefficient bit-builder, Hex-compressed shareable URLs, classroom presets,
 * standalone animated Lessons bridge, and the 4-slide concepts modal.
 */

import {
  attachSlidingIndicator,
  bases,
  closeErrorPopup,
  copyToClipboard,
  degreeOf,
  element,
  formatOperand,
  mathElement,
  parseOperand,
  polynomial,
  setMathText,
  showErrorPopup,
  showFeedbackPopup,
  significantDigits,
} from "./notation.js";
import { createTraceView } from "./traces.js";
import { setupPageTour } from "./tour.js";
import { setupExplorations } from "./explorations.js";
import { setupLessons } from "./lessons.js";

/** @param {string} id @returns {HTMLElement} */
const $ = id => document.getElementById(id);
const fields = new Map();
const operands = ["a", "b"];
const operations = new Set(["add", "subtract", "modulo", "multiply", "inverse", "divide"]);
const traceView = createTraceView($("trace-panel"), $("trace-body"), $("trace-tools"));

let base = "hex";
let result;
let showFullResult = false;
// Monotonic revision counter discards stale async API responses when inputs change mid-flight.
let revision = 0;
let slides = [];
let slideIndex = 0;
let uploadPairs = [];

// Gliding active selection bars across notation and operation controls.
const notationIndicator = attachSlidingIndicator(document.querySelector(".segments.notation"), '[aria-pressed="true"]');
const operationsIndicator = attachSlidingIndicator(document.querySelector(".operations"), "label:has(:checked)");

/** @returns {string} Active operation radio value. */
const activeOperation = () => document.querySelector("input[name=operation]:checked").value;
/** @returns {number} Active field degree `m`. */
const activeDegree = () => Number($("field").value);
/** @returns {boolean} True when the selected operation only uses operand A (`modulo` / `inverse`). */
const unary = () => ["modulo", "inverse"].includes(activeOperation());
/** @param {"a" | "b"} key @returns {HTMLInputElement} */
const operandInput = key => $("poly-" + key);

/**
 * Programmatically check an operation radio button and update its gliding pill.
 * @param {string} op - Operation identifier (`add`, `subtract`, `modulo`, `multiply`, `inverse`, `divide`).
 */
function selectOperation(op) {
  document.querySelector('input[name="operation"][value="' + op + '"]').checked = true;
  operationsIndicator.update();
}

/**
 * Send a GET or JSON POST request to `/api/{path}` and normalize HTTP errors.
 *
 * Preserves the server's structured error payload (`error.payload`, including `gcd`
 * and `trace` on zero-inverse HTTP 400 responses) so Table 4.7 termination rows render.
 *
 * @param {string} path - Relative path under `/api/`.
 * @param {object} [data] - JSON body for POST; omit for GET.
 * @param {boolean} [download=false] - Return a binary `Blob` when `true`, JSON otherwise.
 * @returns {Promise<any>} Parsed JSON object or `Blob`.
 * @throws {Error & {payload?: object}} Error with server detail message and attached payload.
 */
async function api(path, data, download = false) {
  const response = await fetch("/api/" + path, data === undefined ? {} : {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw Object.assign(new Error(typeof error.detail === "string" ? error.detail : "Request failed (" + response.status + ")."), { payload: error });
  }
  return download ? response.blob() : response.json();
}

/**
 * Display any validation, upload, or mathematical error in the prominent pop-up modal,
 * or dismiss the popup when called with an empty message.
 *
 * @param {string} [message=""] - Error message; empty string closes `#error-popup`.
 * @param {{title?: string, onViewTrace?: () => void}} [options={}] - Optional dialog heading and trace shortcut.
 */
function showError(message = "", options = {}) {
  if (!message) {
    closeErrorPopup();
    return;
  }
  showErrorPopup({
    title: options.title || "Calculation error",
    message,
    onViewTrace: options.onViewTrace,
  });
}

/**
 * Update the live status notice beside the Calculate button.
 * @param {string} [message=""] - Transient feedback string.
 */
function showNotice(message = "") {
  $("notice").textContent = message;
}

/**
 * Reset displayed result, trace, and status messages and bump the request revision counter.
 */
function clearCalculation() {
  revision += 1;
  result = undefined;
  showFullResult = false;
  $("result").hidden = true;
  $("result-notice").textContent = "";
  traceView.show(null);
  showError();
  showNotice();
}

/**
 * Synchronize the hero badge and modulus metadata banner with the active field degree `m`.
 */
function renderField() {
  const degree = activeDegree();
  const field = fields.get(degree);
  if (!field) return;
  $("hero-degree").textContent = degree;
  setMathText($("mod-poly"), field.reduction_poly);
  $("mod-hex").textContent = field.reduction_poly_hex.toUpperCase();
  $("mod-bin").textContent = field.reduction_poly_bin;
}

/**
 * Read and parse operand `A` or `B` in the currently selected notation.
 *
 * @param {"a" | "b"} key - Operand key.
 * @returns {bigint} Parsed non-negative polynomial bitmask.
 * @throws {Error} When the input is empty or invalid in `base`.
 */
function readOperand(key) {
  const value = operandInput(key).value;
  if (!value.trim()) throw new Error("Enter operand " + key.toUpperCase() + ".");
  return parseOperand(value, base);
}

/**
 * Render the interactive `m <= 8` coefficient bit-builder checkboxes for one operand,
 * using true `<sup>` exponents (`x⁷`, ..., `x¹`, `1`).
 *
 * @param {"a" | "b"} key - Operand key.
 * @param {bigint} value - Current parsed polynomial bitmask.
 * @param {boolean} valid - Disables checkboxes if the raw text input currently has a syntax error.
 */
function renderBits(key, value, valid) {
  const bits = $(key + "-bits");
  bits.replaceChildren();
  if (activeDegree() > 8 || (key === "b" && unary())) return;
  for (let bit = activeDegree() - 1; bit >= 0; bit -= 1) {
    const toggle = element("input");
    toggle.type = "checkbox";
    toggle.checked = Boolean(value & (1n << BigInt(bit)));
    toggle.disabled = !valid;
    const label = element("label");
    label.append(toggle, mathElement("span", bit === 0 ? "1" : "x^" + bit));
    toggle.setAttribute("aria-label", "Operand " + key.toUpperCase() + ", coefficient of x to the power " + bit);
    toggle.addEventListener("change", () => {
      const index = [...bits.querySelectorAll("input")].indexOf(toggle);
      operandInput(key).value = formatOperand(value ^ (1n << BigInt(bit)), base, activeDegree());
      clearCalculation();
      renderOperands();
      // Preserve keyboard focus on the toggled bit checkbox after DOM rebuild.
      $(key + "-bits").querySelectorAll("input")[index].focus();
    });
    bits.append(label);
  }
}

/**
 * Synchronize the second operand card (`#operand-b`):
 *   - On `modulo` (`Reduce`) or `inverse`, switches cleanly to a read-only **Modulus m(x)**
 *     display synced to the active field degree `m` and `base`, while preserving the user's
 *     typed `#poly-b` input value in state.
 *   - On binary ops (`add`, `subtract`, `multiply`, `divide`), restores editable `Operand B(x)`.
 */
function renderOperands() {
  const degree = activeDegree();
  const field = fields.get(degree);
  const op = activeOperation();

  for (const key of operands) {
    const input = operandInput(key);
    const isUnaryModulusCard = key === "b" && unary();
    input.disabled = isUnaryModulusCard;
    $("operand-" + key).classList.toggle("inactive", false);

    if (isUnaryModulusCard) {
      $("operand-b").classList.add("is-modulus-mode");
      $("operand-b-editable").hidden = true;
      $("operand-b-modulus").hidden = false;
      $("b-bits").replaceChildren();

      setMathText($("modulus-lock-badge"), "Locked to GF(2^" + degree + ")");
      setMathText(
        $("b-modulus-context"),
        op === "modulo" ? "Reducing A(x) mod m(x)" : "Inverting A(x)^-1 mod m(x)",
      );

      if (field) {
        if (base === "algebraic") {
          setMathText($("b-modulus-value"), field.reduction_poly);
          $("b-modulus-preview").textContent = "Hex: " + field.reduction_poly_hex.toUpperCase();
        } else if (base === "binary") {
          $("b-modulus-value").textContent = field.reduction_poly_bin;
          setMathText($("b-modulus-preview"), field.reduction_poly);
        } else {
          $("b-modulus-value").textContent = field.reduction_poly_hex.toUpperCase();
          setMathText($("b-modulus-preview"), field.reduction_poly);
        }
      }
      continue;
    }

    if (key === "b") {
      $("operand-b").classList.remove("is-modulus-mode");
      $("operand-b-editable").hidden = false;
      $("operand-b-modulus").hidden = true;
    }

    input.placeholder = bases[base].example;
    input.removeAttribute("aria-invalid");
    $(key + "-preview").textContent = "";
    $(key + "-meta").textContent = "";
    let value = 0n;
    let valid = true;
    if (input.value.trim()) {
      try {
        value = readOperand(key);
        const deg = degreeOf(value);
        $(key + "-meta").textContent = (deg + 1) + " bits · " + (deg < 0 ? "zero polynomial" : "degree " + deg);
        setMathText($(key + "-preview"), polynomial(value));
      } catch (error) {
        valid = false;
        input.setAttribute("aria-invalid", "true");
        $(key + "-meta").textContent = error.message;
      }
    }
    renderBits(key, value, valid);
  }
}

/**
 * Sync `aria-pressed` state and gliding indicator on the Hex / Binary / Polynomial segmented buttons.
 */
function renderNotation() {
  for (const button of document.querySelectorAll("[data-base]")) {
    button.setAttribute("aria-pressed", button.dataset.base === base);
  }
  notationIndicator.update();
}

/**
 * Switch input/output notation while losslessly converting existing operand values via BigInt.
 *
 * @param {"hex" | "binary" | "algebraic"} nextBase - Newly selected notation.
 */
function changeNotation(nextBase) {
  if (nextBase === base) return;
  const current = {};
  for (const key of operands) {
    if (!operandInput(key).value.trim()) continue;
    try {
      current[key] = readOperand(key);
    } catch (error) {
      if (key === "b" && unary()) {
        operandInput(key).value = "";
        continue;
      }
      showError("Operand " + key.toUpperCase() + ": " + error.message, { title: "Invalid operand notation" });
      return;
    }
  }
  base = nextBase;
  for (const [key, value] of Object.entries(current)) {
    operandInput(key).value = formatOperand(value, base, activeDegree());
  }
  showError();
  renderNotation();
  renderOperands();
  if (result) renderResult();
}

/**
 * Extract one formatted representation (`hex`, `bin`, or `poly`) from a server `ElementReprModel`.
 *
 * @param {{hex: string, bin: string, poly: string}} value - Server element object.
 * @param {"hex" | "binary" | "algebraic"} notation - Requested display notation.
 * @returns {string} Display-ready value (uppercase for hex).
 */
function display(value, notation) {
  const text = value[bases[notation].field];
  return notation === "hex" ? text.toUpperCase() : text;
}

/**
 * Shorten 163..571-bit result strings into compact previews unless `Show full value` is toggled.
 *
 * @param {string} text - Full formatted value.
 * @param {"hex" | "binary" | "algebraic"} notation - Value notation.
 * @returns {string} Compact preview string (or full string for `m <= 8`).
 */
function previewValue(text, notation) {
  if (result.field.m <= 8) return text;
  if (notation === "algebraic") {
    const terms = text.split(" + ");
    return terms.length > 4 ? terms.slice(0, 2).join(" + ") + " + … + " + terms.at(-1) : text;
  }
  const significant = significantDigits(text);
  return significant.length > 24 ? significant.slice(0, 14) + "…" + significant.slice(-8) : significant;
}

/**
 * Render the primary result card, secondary notations (with `<sup>` on Polynomials),
 * verification badge, and timing metrics.
 */
function renderResult() {
  $("result").hidden = false;
  const full = Object.fromEntries(Object.keys(bases).map(key => [key, display(result.result, key)]));
  const preview = Object.fromEntries(Object.keys(bases).map(key => [key, previewValue(full[key], key)]));
  const values = showFullResult ? full : preview;
  const expansion = $("result-expanded");
  expansion.hidden = Object.keys(bases).every(key => full[key] === preview[key]);
  expansion.textContent = showFullResult ? "Show preview" : "Show full value";
  expansion.setAttribute("aria-expanded", showFullResult);
  $("compare-product").hidden = result.operation !== "multiply";
  $("result-base").textContent = bases[base].label + (values[base] !== full[base] ? " preview" : "");

  if (base === "algebraic") setMathText($("result-value"), values[base]);
  else $("result-value").textContent = values[base];

  $("result-alternatives").replaceChildren();
  for (const [key, info] of Object.entries(bases)) {
    if (key !== base) {
      const dd = key === "algebraic" ? mathElement("dd", values[key]) : element("dd", values[key]);
      $("result-alternatives").append(element("dt", info.label), dd);
    }
  }
  const verification = $("verification");
  verification.hidden = !result.verification;
  if (result.verification) {
    const proof = result.verification;
    verification.classList.toggle("failed", !proof.passed);
    setMathText(verification, (proof.passed ? "Mathematically verified · " : "Verification failed · ") + proof.label);
  }
  const metrics = result.metrics;
  $("metrics").replaceChildren(
    element("span", metrics.elapsed_ms.toFixed(3) + " ms"),
    element("span", metrics.result_bit_length + " bits"),
    element("span", "Hamming weight " + metrics.result_hamming_weight),
  );
}

/**
 * Submit the current operands and operation to `POST /api/calculate` and render result + trace.
 *
 * @param {{reveal?: boolean}} [options] - When `reveal` is `true`, scrolls and focuses the result panel.
 */
async function calculate({ reveal = false } = {}) {
  clearCalculation();
  const request = revision;
  try {
    readOperand("a");
    if (!unary()) readOperand("b");
    $("calculate").disabled = true;
    showNotice("Calculating…");
    const data = await api("calculate", {
      m: activeDegree(), operation: activeOperation(), input_base: base, output_base: base,
      a: operandInput("a").value, b: unary() ? null : operandInput("b").value,
    });
    if (revision !== request) return;
    result = data;
    renderResult();
    traceView.show(data.trace, data.initial_reduction);
    if (reveal && $("page-tour").hidden && !$("result").closest("[hidden]")) {
      $("result-title").focus({ preventScroll: true });
      $("result").scrollIntoView({ block: "start" });
    }
  } catch (error) {
    if (revision !== request) return;
    const hasTrace = Boolean(error.payload?.trace);
    // Display the server's Table 4.7 B3 = 0 termination trace on zero-inverse HTTP 400 errors.
    traceView.show(error.payload?.trace);
    showError(error.message, {
      title: hasTrace ? "No multiplicative inverse" : "Calculation error",
      onViewTrace: hasTrace ? () => $("trace-panel").scrollIntoView({ behavior: "smooth", block: "start" }) : undefined,
    });
  } finally {
    $("calculate").disabled = false;
    if (revision === request) {
      showNotice();
      $("calculator").dispatchEvent(new Event("lab:calculation-result", { bubbles: true }));
    }
  }
}

/**
 * Copy text to the clipboard using `copyToClipboard` and display a `#feedback-popup` toast.
 * Falls back to `window.prompt` only if both Clipboard API and `execCommand` are blocked.
 *
 * @param {string} text - String to copy.
 * @param {string} feedback - Confirmation message displayed on success.
 * @param {HTMLElement} [notice=$("notice")] - Status element receiving confirmation text.
 */
async function copyText(text, feedback, notice = $("notice")) {
  const copied = await copyToClipboard(text);
  if (copied) {
    notice.textContent = feedback;
    showFeedbackPopup("Copied to clipboard", feedback);
  } else {
    window.prompt("Copy this value", text);
  }
}

/**
 * Build a shareable URL encoding `(m, operation, base, poly_a, poly_b)`.
 *
 * **Hexadecimal URL Compression Rule:** Operands are always serialized in lowercase
 * hexadecimal inside query parameters, even when `base=binary`, so 571-bit share links
 * remain compact (~143 chars instead of 571 chars) and convert back to `base` on load.
 *
 * @returns {string} Full shareable URL string.
 * @throws {Error} When required operands cannot be parsed.
 */
function makeShareURL() {
  const url = new URL(location.pathname, location.origin);
  const query = { m: activeDegree(), operation: activeOperation(), base, poly_a: readOperand("a").toString(16) };
  if (!unary()) {
    query.poly_b = readOperand("b").toString(16);
  }
  url.search = new URLSearchParams(query);
  return url.href;
}

/**
 * Restore calculator state from URL query parameters, converting hex operands into `base`.
 * Falls back to `configDefaults()` when no `?m=` parameter is present.
 *
 * @throws {Error} If query parameters name an unsupported field, operation, base, or invalid hex.
 */
function readShareURL() {
  const query = new URLSearchParams(location.search);
  if (!query.has("m")) return configDefaults();
  const degree = Number(query.get("m"));
  const operation = query.get("operation");
  const notation = query.get("base");
  if (!fields.has(degree) || !operations.has(operation) || !Object.hasOwn(bases, notation)) throw new Error("This calculation link is invalid.");
  $("field").value = degree;
  selectOperation(operation);
  base = notation;
  for (const key of operands) {
    const hex = query.get("poly_" + key);
    if (hex !== null) {
      operandInput(key).value = formatOperand(parseOperand(hex, "hex"), base, degree);
    }
  }
}

/**
 * Apply the Project-3 default state: primary field `GF(2^163)`, hex mode, multiply `{57} × {83}`.
 */
function configDefaults() {
  $("field").value = "163";
  base = "hex";
  selectOperation("multiply");
  operandInput("a").value = "57";
  operandInput("b").value = "83";
}

/**
 * Build a textbook preset quick-launch button (Chapter 4 `{57} × {83}` or Chapter 5 `{95}^-1`).
 *
 * @param {object} preset - Preset metadata from Slide 4 of `GET /api/tutorial`.
 * @returns {HTMLButtonElement} Configured preset button element.
 */
function presetButton(preset) {
  const inverse = preset.operation === "inverse";
  const button = element("button", "", "preset");
  button.append(
    mathElement("strong", inverse ? "Chapter 5 · AES inverse" : "Chapter 4 · GF(2^8)"),
    mathElement("small", inverse ? "{95}^-1 = {8A}" : "{57} × {83} = {C1}")
  );
  button.addEventListener("click", () => {
    $("field").value = preset.m;
    selectOperation(preset.operation);
    for (const key of operands) {
      if (preset[key]) {
        operandInput(key).value = formatOperand(parseOperand(preset[key], preset.input_base), base, preset.m);
      } else if (key !== "b" || !inverse) {
        operandInput(key).value = "";
      }
    }
    renderField();
    renderOperands();
    if ($("tutorial").open) $("tutorial").close();
    calculate({ reveal: true });
  });
  return button;
}

/**
 * Render the current slide inside the 4-slide Field Concepts `<dialog>` modal with `<sup>`/`<sub>`.
 */
function renderSlide() {
  const slide = slides[slideIndex];
  const list = element("ul");
  for (const point of slide.key_points) list.append(mathElement("li", point));
  const title = mathElement("h2", slide.title);
  title.id = "slide-title";
  $("tutorial-slide").replaceChildren(title, mathElement("p", slide.body), list,
    ...(slide.presets || []).map(presetButton));
  $("slide-count").textContent = (slideIndex + 1) + " / " + slides.length;
  $("slide-prev").disabled = slideIndex === 0;
  $("slide-next").textContent = slideIndex === slides.length - 1 ? "Done" : "Next";
}

/**
 * Populate operand inputs from the selected batch-upload pair, converting to the active notation.
 *
 * @param {number} index - Zero-based index into `uploadPairs`.
 */
function loadPair(index) {
  const pair = uploadPairs[index];
  clearCalculation();
  for (const key of operands) {
    const pairBase = pair.base === "bin" ? "binary" : pair.base;
    if (pair[key]) {
      operandInput(key).value = formatOperand(parseOperand(pair[key], pairBase), base, activeDegree());
    } else if (key !== "b" || !unary()) {
      operandInput(key).value = "";
    }
  }
  renderOperands();
}

// --- Event wiring ------------------------------------------------------------
$("calculator").addEventListener("submit", event => { event.preventDefault(); calculate({ reveal: true }); });
$("field").addEventListener("change", () => { clearCalculation(); renderField(); renderOperands(); });
for (const input of document.querySelectorAll("input[name=operation], #poly-a, #poly-b")) {
  input.addEventListener("input", () => {
    clearCalculation();
    renderOperands();
    operationsIndicator.update();
  });
}
for (const button of document.querySelectorAll("[data-base]")) {
  button.addEventListener("click", () => changeNotation(button.dataset.base));
}
$("share").addEventListener("click", () => {
  try { copyText(makeShareURL(), "Share link copied to clipboard"); }
  catch (error) { showError(error.message, { title: "Share link error" }); }
});
$("copy-result").addEventListener("click", () => copyText(display(result.result, base), "Result copied to clipboard", $("result-notice")));
$("back-to-inputs").addEventListener("click", () => operandInput("a").focus());
$("result-expanded").addEventListener("click", () => {
  showFullResult = !showFullResult;
  renderResult();
});
$("export").addEventListener("click", async () => {
  const format = $("export-format").value;
  const filename = "gf2m-calculation." + format;
  try {
    const blob = await api("export-calculation", { calculation: result, format, download: true }, true);
    const url = URL.createObjectURL(blob);
    const link = element("a");
    link.href = url;
    link.download = filename;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    showFeedbackPopup("Exported successfully", "Downloaded " + filename);
  } catch (error) { showError(error.message, { title: "Export error" }); }
});
$("random").addEventListener("click", async () => {
  const savedRevision = revision;
  try {
    const pair = await api("random-polynomials", { m: activeDegree(), density: $("density").value });
    if (savedRevision !== revision) return;
    clearCalculation();
    for (const key of operands) operandInput(key).value = display(pair[key], base);
    renderOperands();
    showNotice("Random operands generated.");
  } catch (error) { showError(error.message, { title: "Random operand error" }); }
});

const SAMPLE_TXT_CONTENT = [
  "# Comment lines start with #",
  "A: 57",
  "B: 83",
  "---",
  "# B is optional for Reduce (mod) or Inverse",
  "A: 95",
  "",
].join("\n");

const SAMPLE_JSON_CONTENT = JSON.stringify({
  pairs: [
    { a: "57", b: "83", base: "hex" },
    { a: "10010101", base: "bin" },
  ],
}, null, 2) + "\n";

/**
 * Trigger a browser download for a generated sample `.txt` or `.json` starter file.
 *
 * @param {string} filename - Suggested download filename.
 * @param {string} content - UTF-8 file text.
 * @param {string} mimeType - MIME type for the Blob.
 */
function downloadSampleFile(filename, content, mimeType) {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const link = element("a");
  link.href = url;
  link.download = filename;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
  showFeedbackPopup("Sample downloaded", "Saved " + filename, "info");
}

/**
 * Validate, read, and parse an uploaded `.txt` or `.json` operand file via `POST /api/parse-polynomials`.
 *
 * @param {File | undefined} file - User-selected or dropped file.
 */
async function handleUploadFile(file) {
  if (!file) return;
  const lowerName = (file.name || "").toLowerCase();
  if (!lowerName.endsWith(".txt") && !lowerName.endsWith(".json")) {
    if ($("upload-modal")?.open) $("upload-modal").close();
    showError("Unsupported file format. Choose a .txt or .json operand file.", { title: "Unsupported file format" });
    return;
  }
  try {
    const parsed = await api("parse-polynomials", {
      content: await file.text(), filename: file.name, default_base: base === "binary" ? "binary" : "hex",
    });
    uploadPairs = parsed.pairs;
    $("pairs").replaceChildren(...uploadPairs.map((pair, index) => {
      const shorten = value => value.length > 12 ? value.slice(0, 12) + "…" : value;
      const a = "A=" + shorten(pair.a);
      const b = pair.b ? ", B=" + shorten(pair.b) : "";
      const notation = pair.base === "bin" ? "binary" : pair.base;
      const option = element("option", "Pair " + (index + 1) + " · " + a + b + " (" + notation + ")");
      option.value = index;
      return option;
    }));
    $("batch").hidden = false;
    loadPair(0);
    if ($("upload-modal")?.open) $("upload-modal").close();
    const pairLabel = parsed.count === 1 ? " pair" : " pairs";
    showNotice(parsed.count + pairLabel + " loaded.");
    showFeedbackPopup("File uploaded", "Loaded " + parsed.count + " operand" + pairLabel + " from " + file.name);
  } catch (error) {
    if ($("upload-modal")?.open) $("upload-modal").close();
    showError(error.message, { title: "File upload error" });
  } finally {
    $("file").value = "";
  }
}

$("upload").addEventListener("click", () => {
  const modal = $("upload-modal");
  if (modal && !modal.open) modal.showModal();
});
$("upload-modal-close")?.addEventListener("click", () => $("upload-modal").close());
$("upload-modal")?.addEventListener("click", event => {
  if (event.target === $("upload-modal")) $("upload-modal").close();
});
$("upload-browse")?.addEventListener("click", event => {
  event.stopPropagation();
  $("file").click();
});
$("upload-dropzone")?.addEventListener("click", event => {
  if (event.target.closest("#upload-browse")) return;
  $("file").click();
});
$("upload-dropzone")?.addEventListener("keydown", event => {
  if (event.target !== $("upload-dropzone")) return;
  if (event.key === "Enter" || event.key === " ") {
    event.preventDefault();
    $("file").click();
  }
});
$("upload-dropzone")?.addEventListener("dragenter", event => {
  event.preventDefault();
  $("upload-dropzone").classList.add("is-dragover");
});
$("upload-dropzone")?.addEventListener("dragover", event => {
  event.preventDefault();
  $("upload-dropzone").classList.add("is-dragover");
});
$("upload-dropzone")?.addEventListener("dragleave", event => {
  if (!$("upload-dropzone").contains(event.relatedTarget)) {
    $("upload-dropzone").classList.remove("is-dragover");
  }
});
$("upload-dropzone")?.addEventListener("drop", event => {
  event.preventDefault();
  $("upload-dropzone").classList.remove("is-dragover");
  handleUploadFile(event.dataTransfer?.files?.[0]);
});
$("download-sample-txt")?.addEventListener("click", () => downloadSampleFile("gf2m-sample.txt", SAMPLE_TXT_CONTENT, "text/plain"));
$("download-sample-json")?.addEventListener("click", () => downloadSampleFile("gf2m-sample.json", SAMPLE_JSON_CONTENT, "application/json"));
$("file").addEventListener("change", () => handleUploadFile($("file").files[0]));
$("pairs").addEventListener("change", () => {
  try { loadPair(Number($("pairs").value)); }
  catch (error) { showError(error.message, { title: "File pair error" }); }
});
const lessonsController = setupLessons({
  openInCalculator(preset) {
    window.location.hash = "calculator";
    if (fields.has(preset.m)) $("field").value = String(preset.m);
    base = preset.base || "hex";
    selectOperation(preset.operation);
    for (const key of operands) {
      const raw = preset[key];
      if (raw) {
        operandInput(key).value = formatOperand(parseOperand(raw, preset.base || "hex"), base, preset.m);
      } else if (key !== "b" || !unary()) {
        operandInput(key).value = "";
      }
    }
    renderField();
    renderNotation();
    renderOperands();
    calculate({ reveal: true });
  },
});
const loadExperimentFields = setupExplorations(api, {
  closeTour: setupPageTour(),
  currentField: () => fields.get(activeDegree()),
  currentOperands: () => ({
    m: activeDegree(), a: readOperand("a").toString(16), b: readOperand("b").toString(16),
  }),
  onLessonRoute: slug => lessonsController.selectLessonById(slug),
  onError: (msg, title = "Exploration error") => showError(msg, { title }),
});
$("concepts-open").addEventListener("click", () => {
  if (slides.length) {
    slideIndex = 0;
    renderSlide();
    $("tutorial").showModal();
  }
});
$("tutorial-close").addEventListener("click", () => $("tutorial").close());
$("slide-prev").addEventListener("click", () => { slideIndex -= 1; renderSlide(); });
$("slide-next").addEventListener("click", () => {
  if (slideIndex === slides.length - 1) $("tutorial").close();
  else { slideIndex += 1; renderSlide(); }
});

/**
 * Bootstrap the workbench by loading the field catalog and tutorial slides in parallel,
 * restoring URL state (or defaults), syncing gliding indicators, and running the initial calculation.
 */
async function init() {
  try {
    const [catalog, tutorial] = await Promise.all([api("fields"), api("tutorial")]);
    for (const field of catalog.fields) {
      fields.set(field.m, field);
      const option = element("option", field.m + " bits" + (field.m === 163 ? " · project field" : ""));
      option.value = field.m;
      $("field").append(option);
    }
    loadExperimentFields(catalog.fields);
    slides = tutorial.slides;
    $("presets").replaceChildren(...slides.flatMap(slide => slide.presets || []).map(presetButton));
    let invalidLink;
    try { readShareURL(); }
    catch (error) { configDefaults(); invalidLink = error.message; }
    renderField();
    renderNotation();
    renderOperands();
    operationsIndicator.update();
    if (invalidLink) showError(invalidLink, { title: "Invalid calculation link" });
    else await calculate();
  } catch (error) { showError(error.message, { title: "Initialization error" }); }
}

init();
