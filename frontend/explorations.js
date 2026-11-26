/**
 * @fileoverview Hash-based view routing and controllers for the exploration & real-world
 * application labs (`#modulus`, `#applications`, `#compare`), upgraded with gliding tab
 * indicators, true `<sup>` polynomial input overlays, auto-uppercase Hex formatting,
 * JSON Export/Import, GHASH key save/share, Full-Value Inspector popups on 163-bit ECC
 * coordinates, legacy `#aes` redirect, and top-center error alerts.
 *
 * Original Author: Ali Zahreddine - Milestone 4, Integration & Milestone 6 (Waves 1-4).
 *
 * Connects the frontend exploration views to `/api/explorations/*`:
 *   - `#modulus`:      Binary polynomial irreducibility checker & factor witnesses (Stallings Ch. 4
 *                      plus Berlekamp square-free splitting extension).
 *   - `#applications`: Four gliding sub-tabs:
 *                      (1) XTS-AES GF(2^128) Tweak Multiplier (Stallings Ch. 6 / IEEE 1619-2007)
 *                      (2) Polynomial / Binary ECC E_{2^m}(a,b) Explorer (Teaching GF(2^4) & NIST B-163, Stallings Ch. 10)
 *                      (3) GCM / GHASH GF(2^128) Authenticator (Stallings Ch. 12 / NIST SP 800-38D)
 *                      (4) AES S-Box GF(2^8) Byte Substitution (Stallings Ch. 5 / FIPS 197)
 *   - `#compare`:      Shift-and-XOR vs. carry-free + long-division comparison and 163/571-bit benchmark.
 */

import {
  applyInputFormatting,
  attachPolyInputOverlay,
  attachSlidingIndicator,
  copyToClipboard,
  element,
  mathElement,
  normalizeAlgebraicInput,
  polynomial,
  setMathText,
  showErrorPopup,
  showFeedbackPopup,
  showInspectorPopup,
} from "./notation.js";
import { createTraceView, table } from "./traces.js";

/** @param {string} id @returns {HTMLElement} */
const $ = id => document.getElementById(id);
/** @param {{hex: string}} value @returns {string} */
const hex = value => value.hex.toUpperCase();

const DEFAULT_XTS_TWEAK = "50000000000000000000000000000001";
const DEFAULT_GHASH_H = "66E94BD4EF8A2C3B884CFA59CA342B2E";
const DEFAULT_GHASH_BLOCKS = [
  "0388DACE60B6A392F328C2B971B2FE78",
  "D9313225F88406E5A55909C5AFF5269A",
  "00000000000000000000000000000080",
];

/**
 * Generate one cryptographically random 128-bit uppercase hex block (32 hex digits).
 * @returns {string} 32-character uppercase hex string.
 */
function random128BitHex() {
  const bytes = new Uint8Array(16);
  if (window.crypto?.getRandomValues) {
    window.crypto.getRandomValues(bytes);
  } else {
    for (let i = 0; i < 16; i += 1) bytes[i] = Math.floor(Math.random() * 256);
  }
  return Array.from(bytes, b => b.toString(16).padStart(2, "0")).join("").toUpperCase();
}

/**
 * Render an inspectable 128-bit hexadecimal value button that opens `#inspector-popup`
 * with full Hexadecimal, Binary, and Polynomial (`<sup>`) views plus Copy buttons.
 *
 * @param {string} hexStr - 32-char uppercase hexadecimal value.
 * @param {string} title - Modal heading title.
 * @param {string} subtitle - Modal subtitle context.
 * @param {boolean} [compact=false] - Compact middle-ellipsis display inside dense table cells.
 * @param {string} [extraClass=""] - Optional extra CSS class names.
 * @returns {HTMLButtonElement} Clickable inspector button.
 */
function makeGhashInspectButton(hexStr, title, subtitle, compact = false, extraClass = "") {
  const upper = hexStr.toUpperCase();
  const display = compact && upper.length > 20 ? upper.slice(0, 10) + "…" + upper.slice(-8) : upper;
  const btn = element("button", display, ("trace-inspectable " + extraClass).trim());
  btn.type = "button";
  btn.title = "Click to view full value";
  btn.dataset.fullValue = upper;
  btn.setAttribute("aria-label", "Click to view full value of " + title);
  const cue = element("span", "⤢", "inspect-cue");
  cue.setAttribute("aria-hidden", "true");
  btn.append(cue);
  btn.addEventListener("click", () => {
    showInspectorPopup({
      title,
      valueBigInt: BigInt("0x" + upper),
      mDegree: 128,
      subtitle,
    });
  });
  return btn;
}

/**
 * Show or clear an optional status message element.
 * @param {string} id - Target DOM element id.
 * @param {string} [text=""] - Message text; empty string hides the element.
 */
function message(id, text = "") {
  const node = $(id);
  if (!node) return;
  setMathText(node, text);
  node.hidden = !text;
}

/**
 * Render a pass/fail status banner inside an exploration result panel with true `<sup>`/`<sub>`.
 * @param {string} id - Target status banner id.
 * @param {string} text - Banner message text.
 * @param {boolean} passed - Highlights red (`.failed`) when `false`.
 */
function status(id, text, passed) {
  setMathText($(id), text);
  $(id).classList.toggle("failed", !passed);
}

/**
 * Bind an exploration form with in-flight locking, error alert routing, and `lab:calculation-result` dispatch.
 *
 * @param {string} formId - Form element id.
 * @param {string[]} results - Result section ids revealed on success and hidden on failure.
 * @param {() => Promise<void>} calculate - Async handler calling the API and populating the DOM.
 * @param {(msg: string, title?: string) => void} reportError - Error alert callback.
 * @param {string} errorTitle - Alert heading shown when `calculate` throws.
 * @returns {() => void} Helper triggering programmatic form submission.
 */
function bindExperiment(formId, results, calculate, reportError, errorTitle) {
  const form = $(formId);
  form.addEventListener("submit", async event => {
    event.preventDefault();
    if (form.getAttribute("aria-busy") === "true") return;
    const controls = Array.from(form.elements).filter(control => !control.disabled);
    form.setAttribute("aria-busy", "true");
    controls.forEach(control => { control.disabled = true; });
    try {
      await calculate();
      results.forEach(id => { $(id).hidden = false; });
    } catch (error) {
      results.forEach(id => { $(id).hidden = true; });
      reportError(error.message, errorTitle);
    } finally {
      controls.forEach(control => { control.disabled = false; });
      form.removeAttribute("aria-busy");
      form.dispatchEvent(new Event("lab:calculation-result", { bubbles: true }));
    }
  });
  return () => form.requestSubmit();
}

/**
 * Format a hexadecimal coordinate compactly when `m > 8` and attach a Full-Value Inspector
 * Popup click handler so students can inspect the full 163-bit Hex, Binary, and Polynomial value.
 *
 * @param {string} hexStr - Full uppercase hex string.
 * @param {number} mDeg - Field degree `m`.
 * @param {string} label - Descriptive label for the inspector modal title.
 * @returns {HTMLElement} Styled coordinate span element.
 */
function makeEccCoordSpan(hexStr, mDeg, label) {
  const upper = hexStr.toUpperCase();
  if (mDeg <= 8 || upper.length <= 20) {
    return element("code", "{" + upper + "}", "ecc-coord-val");
  }
  const compact = upper.slice(0, 10) + "…" + upper.slice(-8);
  const btn = element("button", "{" + compact + "}", "ecc-coord-val trace-inspectable");
  btn.type = "button";
  btn.title = "Click to view full value";
  btn.dataset.fullValue = upper;
  btn.setAttribute("aria-label", "Click to view full value of " + label);
  const cue = element("span", "⤢", "inspect-cue");
  cue.setAttribute("aria-hidden", "true");
  btn.append(cue);
  btn.addEventListener("click", () => {
    showInspectorPopup({
      title: label,
      valueBigInt: BigInt("0x" + upper),
      mDegree: mDeg,
      subtitle: "GF(2^" + mDeg + ") curve coordinate",
    });
  });
  return btn;
}

/**
 * Render an elliptic curve point `(x, y)` (or point at infinity `O`) with click-to-inspect coordinates.
 *
 * @param {{is_infinity: boolean, x: {hex: string} | null, y: {hex: string} | null}} pt - Point payload from `/api/explorations/binary-ecc`.
 * @param {number} mDeg - Field degree `m`.
 * @param {string} label - Point name (e.g. `"G"`, `"2G"`, `"3G"`).
 * @returns {HTMLElement} Inline point element.
 */
function renderPointDisplay(pt, mDeg, label) {
  const wrap = element("div", undefined, "ecc-point-display");
  if (!pt || pt.is_infinity || !pt.x || !pt.y) {
    wrap.append(element("code", "O (Point at infinity)", "ecc-coord-val"));
    return wrap;
  }
  const xRow = element("div", undefined, "ecc-coord-row");
  xRow.append(element("span", "x =", "ecc-coord-axis"), makeEccCoordSpan(pt.x.hex, mDeg, label + " · x-coordinate"));
  const yRow = element("div", undefined, "ecc-coord-row");
  yRow.append(element("span", "y =", "ecc-coord-axis"), makeEccCoordSpan(pt.y.hex, mDeg, label + " · y-coordinate"));
  wrap.append(xRow, yRow);
  return wrap;
}

/**
 * Bind top-level hash navigation (`#calculator`, `#lessons`, `#lessons/<id>`, `#visual`,
 * `#modulus`, `#applications`, `#compare`, plus legacy `#aes` redirect) and attach the
 * gliding active tab pill to `.lab-nav`.
 *
 * @param {() => void} closeTour - Callback closing any active spotlight walkthrough on switch.
 * @param {(lessonSlug?: string) => void} [onLessonRoute] - Callback invoked on `#lessons`.
 * @param {(forcedSubTab?: string) => void} [onApplicationsRoute] - Callback invoked on `#applications`.
 * @param {(viewName: string) => void} [onViewChange] - Callback invoked on every view change.
 */
function setupNavigation(closeTour, onLessonRoute, onApplicationsRoute, onViewChange) {
  const nav = document.querySelector(".lab-nav");
  const tabs = Array.from(document.querySelectorAll("[data-lab-tab]"));
  const views = Array.from(document.querySelectorAll("[data-lab-view]"));
  const navIndicator = attachSlidingIndicator(nav, '[aria-current="page"]');

  function selectView(focus) {
    const rawHash = window.location.hash.slice(1);
    const [rawRequested, subroute] = rawHash.split("/");
    let requested = rawRequested;
    let forcedAppTab;
    // Redirect legacy #aes links directly to #applications with the AES S-Box sub-tab active.
    if (requested === "aes") {
      requested = "applications";
      forcedAppTab = "aes";
      window.history.replaceState(null, "", location.pathname + location.search + "#applications");
    }
    const selected = views.find(view => view.dataset.labView === requested) || views[0];
    const activeViewName = selected.dataset.labView;
    closeTour();
    for (const view of views) view.hidden = view !== selected;
    for (const tab of tabs) {
      if (tab.dataset.labTab === activeViewName) tab.setAttribute("aria-current", "page");
      else tab.removeAttribute("aria-current");
    }
    navIndicator.update();
    if (typeof onViewChange === "function") {
      onViewChange(activeViewName);
    }
    if (activeViewName === "lessons" && typeof onLessonRoute === "function") {
      onLessonRoute(subroute);
    }
    if (activeViewName === "applications" && typeof onApplicationsRoute === "function") {
      onApplicationsRoute(forcedAppTab);
    }
    if (focus) {
      window.scrollTo(0, 0);
      selected.querySelector("h1")?.focus({ preventScroll: true });
    }
  }
  window.addEventListener("hashchange", () => selectView(true));
  selectView(false);
}

/**
 * Configure the Modulus explorer (`#modulus`) irreducibility test, true `<sup>` polynomial
 * overlay, auto-uppercase hex formatting, factor-witness display, and plain-English GCD explanation.
 *
 * @param {(path: string, data?: object) => Promise<any>} api - Shared JSON API client.
 * @param {() => object | undefined} currentField - Accessor returning the calculator's active field info.
 * @param {(msg: string, title?: string) => void} reportError - Error alert reporter.
 */
function setupModulus(api, currentField, reportError) {
  const modInput = $("custom-modulus");
  const modBase = $("modulus-base");
  const modOverlay = attachPolyInputOverlay(modInput, () => modBase.value === "algebraic");
  applyInputFormatting(modInput, modBase.value);
  modOverlay.sync();

  modInput.addEventListener("input", () => {
    applyInputFormatting(modInput, modBase.value);
    modOverlay.sync();
  });
  modBase.addEventListener("change", () => {
    applyInputFormatting(modInput, modBase.value);
    modOverlay.sync();
  });

  const test = bindExperiment("modulus-form", ["modulus-result"], async () => {
    const baseVal = modBase.value;
    const rawPoly = modInput.value;
    const apiPoly = baseVal === "algebraic" ? normalizeAlgebraicInput(rawPoly) : rawPoly;
    const data = await api("explorations/modulus", {
      polynomial: apiPoly, input_base: baseVal,
    });
    status("modulus-status", (data.irreducible ? "Irreducible" : "Reducible") + " · degree " + data.degree, data.irreducible);
    $("modulus-conclusion").textContent = data.irreducible
      ? "Every GCD is 1, so there are no factors of degree at most half the modulus degree. This modulus defines a field."
      : "The modulus factors into two nonzero remainders whose product reduces to zero.";
    $("modulus-witness").replaceChildren();
    if (data.witness) {
      const witness = data.witness;
      const box = element("div", undefined, "witness");
      box.append(
        element("h3", "Two nonzero factors"),
        mathElement("code", "(" + witness.a.poly + ") × (" + witness.b.poly + ") = " + witness.product.poly),
        element("p", "Hex " + hex(witness.a) + " × " + hex(witness.b) + " leaves remainder " + hex(witness.remainder) + "."),
      );
      if (data.split_with_berlekamp) {
        box.append(element("p", "The first nontrivial GCD was the entire modulus. A binary linear system split it into smaller factors."));
      }
      $("modulus-witness").append(box);
    }
    const explanation = mathElement(
      "p",
      "Each row computes gcd(f(x), x^(2^i) + x) to test whether f(x) has any irreducible factor of degree i; if every checkpoint up to floor(deg(f)/2) equals 1, no non-trivial factors exist and f(x) is irreducible.",
      "meta modulus-gcd-explain",
    );
    $("modulus-checks").replaceChildren(
      explanation,
      table("GCD checkpoints", ["i", "x^(2^i) mod f (hex)", "gcd(f, x^(2^i) + x) (hex)"],
        data.checks.map(row => [row.i, row.power_remainder_hex, row.gcd_hex]),
        (row, col) => col === 2 && data.checks[row].gcd_hex !== "1"),
    );
  }, reportError, "Modulus explorer error");

  function load(text, notation) {
    modBase.value = notation;
    modInput.classList.remove("is-algebraic-input");
    modInput.value = notation === "algebraic" ? normalizeAlgebraicInput(text) : text.toUpperCase();
    modOverlay.sync();
    test();
  }
  $("modulus-random").addEventListener("click", () => {
    const targetDeg = Math.min(Math.max(currentField()?.m || 8, 2), 16);
    let val = (1n << BigInt(targetDeg)) | 1n;
    const rand = new Uint16Array(1);
    if (window.crypto?.getRandomValues) window.crypto.getRandomValues(rand);
    else rand[0] = Math.floor(Math.random() * 65536);
    val |= (BigInt(rand[0]) & ((1n << BigInt(targetDeg)) - 2n));
    const notation = modBase.value;
    const formatted = notation === "algebraic"
      ? polynomial(val)
      : notation === "binary"
        ? val.toString(2)
        : val.toString(16).toUpperCase();
    load(formatted, notation);
  });
  $("modulus-example").addEventListener("click", () => load("x^8 + 1", "algebraic"));
  $("modulus-current").addEventListener("click", () => {
    const field = currentField();
    if (field) load(field.reduction_poly_hex.toUpperCase(), "hex");
    else reportError("The calculator field is still loading.", "Modulus explorer");
  });

  return {
    /**
     * Serialize current Modulus explorer inputs for a shareable URL.
     * @returns {{mod: string, mod_base: string}} Encoded modulus text and short base key.
     */
    getShareState() {
      const b = modBase.value;
      const shortBase = b === "algebraic" ? "poly" : b === "binary" ? "bin" : "hex";
      const raw = modInput.value.trim();
      const mod = b === "algebraic" ? normalizeAlgebraicInput(raw) : raw.toUpperCase();
      return { mod, mod_base: shortBase };
    },
    /**
     * Restore a shared `#modulus` URL (`?mod=...&mod_base=...#modulus`) and run the test.
     * @param {URLSearchParams} params - Parsed URL query parameters.
     * @returns {boolean} True when a shared modulus state was restored.
     */
    restoreShareState(params) {
      const mod = params.get("mod");
      if (!mod) return false;
      const rawBase = (params.get("mod_base") || "poly").toLowerCase();
      const notation = rawBase === "hex" ? "hex" : (rawBase === "bin" || rawBase === "binary") ? "binary" : "algebraic";
      load(mod, notation);
      return true;
    },
  };
}

/**
 * Trigger a browser download of a formatted JSON object and show a confirmation toast.
 *
 * @param {string} filename - Suggested download filename (e.g. `"gf2m-xts-aes.json"`).
 * @param {object} payload - Serializable JSON object.
 * @param {string} [detail="Saved JSON file"] - Toast detail line.
 */
function downloadJsonFile(filename, payload, detail = "Saved JSON file") {
  const blob = new Blob([JSON.stringify(payload, null, 2) + "\n"], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = element("a");
  link.href = url;
  link.download = filename;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
  showFeedbackPopup("Exported " + filename, detail);
}

/**
 * Validate and normalize a 128-bit hexadecimal value to 32 uppercase hex digits.
 *
 * @param {string} raw - Raw hex string (optional `0x` or `{...}` wrappers allowed).
 * @param {string} label - Field label used in validation errors.
 * @returns {string} 32-character uppercase hex string.
 * @throws {Error} When blank or not valid 1..32 hex digits.
 */
function normalize128BitHex(raw, label) {
  let clean = String(raw ?? "").trim();
  if (clean.startsWith("{") && clean.endsWith("}")) clean = clean.slice(1, -1).trim();
  clean = clean.replace(/^0x/i, "").replace(/\s+/g, "");
  if (!clean) throw new Error("Enter " + label + " first.");
  if (!/^[0-9a-fA-F]{1,32}$/.test(clean)) {
    throw new Error(label + " must be 1 to 32 hexadecimal digits (0-9, A-F).");
  }
  return clean.toUpperCase().padStart(32, "0");
}

/**
 * Configure the `#applications` view with gliding sub-tabs for:
 *   1. XTS-AES GF(2^128) Tweak Multiplier (Stallings Ch. 6 / IEEE 1619-2007)
 *   2. Polynomial / Binary Elliptic Curve (E_{2^m}(a,b)) Explorer (Teaching GF(2^4) + NIST B-163, Stallings Ch. 10)
 *   3. GCM / GHASH GF(2^128) Authenticator (Stallings Ch. 12 / NIST SP 800-38D) + Save key / Share key
 *   4. AES S-Box GF(2^8) Byte Substitution (Stallings Ch. 5 / FIPS 197)
 * Plus Export JSON / Import JSON across all four sub-tabs.
 *
 * @param {(path: string, data?: object) => Promise<any>} api - Shared JSON API client.
 * @param {(msg: string, title?: string) => void} reportError - Error alert reporter.
 * @returns {{onActivate: (forcedTab?: string) => void, getShareState: () => {params: Record<string, string>, label: string}, restoreShareState: (params: URLSearchParams) => boolean}} Activation and share-link controller.
 */
function setupApplications(api, reportError) {
  const subtabsEl = $("applications-subtabs");
  const subtabButtons = Array.from(subtabsEl.querySelectorAll("[data-app-tab]"));
  const subpanels = {
    xts: $("app-panel-xts"),
    ecc: $("app-panel-ecc"),
    ghash: $("app-panel-ghash"),
    aes: $("app-panel-aes"),
  };
  const subtabsIndicator = attachSlidingIndicator(subtabsEl, '[aria-pressed="true"]');

  let activeApp = "xts";
  let lastXtsLastTweak = DEFAULT_XTS_TWEAK;
  const lastResults = { xts: null, ecc: null, ghash: null, aes: null };

  // --- Sub-Tab 1: XTS-AES GF(2^128) Tweak Multiplier ---
  const xtsT0Input = $("xts-t0");
  const xtsStepsInput = $("xts-steps");
  xtsT0Input.addEventListener("input", () => applyInputFormatting(xtsT0Input, "hex"));

  const runXts = bindExperiment("xts-form", ["xts-results"], async () => {
    const stepsVal = Math.max(1, Math.min(16, Number(xtsStepsInput.value) || 6));
    xtsStepsInput.value = String(stepsVal);
    const data = await api("explorations/xts-tweak", {
      t0_hex: xtsT0Input.value.trim(),
      steps: stepsVal,
    });
    lastResults.xts = data;
    const overflowCount = data.blocks.filter(b => b.reduced_xor_87).length;
    setMathText($("xts-modulus-badge"), "m(x) = " + data.modulus_poly + " · mask 0x" + data.reduction_mask_hex);
    status(
      "xts-status",
      "Computed " + data.blocks.length + " tweaks (j = 0 to " + data.steps + ") in GF(2^128) · " +
        overflowCount + (overflowCount === 1 ? " overflow (XOR 0x87)" : " overflows (XOR 0x87)"),
      true,
    );

    const chainEl = $("xts-chain");
    chainEl.replaceChildren();
    data.blocks.forEach(block => {
      lastXtsLastTweak = block.tweak_hex;
      const row = element(
        "article",
        undefined,
        "xts-block-row" + (block.reduced_xor_87 ? " is-overflow" : block.block_index === 0 ? " is-initial" : ""),
      );
      const head = element("div", undefined, "xts-block-head");
      head.append(mathElement("strong", "Block j = " + block.block_index, "xts-block-title"));

      if (block.block_index === 0) {
        head.append(element("span", "Initial tweak T0", "diff-tag diff-unchanged"));
      } else if (block.reduced_xor_87) {
        head.append(mathElement("span", "b_127 = 1 → x^128 overflow → XOR 0x87", "diff-tag diff-reduced"));
      } else {
        head.append(mathElement("span", "b_127 = 0 → Pure left shift (<< 1)", "diff-tag diff-carried"));
      }

      const hexBox = element("code", block.tweak_hex, "xts-tweak-hex");
      row.append(head, hexBox);

      if (block.block_index > 0) {
        const detailText = block.reduced_xor_87
          ? "Previous MSB b_127 = 1 popped x^128; shifted value " + block.shifted_hex + " XORed with 0x87 (x^7 + x^2 + x + 1)."
          : "Previous MSB b_127 = 0; shifted left by 1 bit without exceeding degree 127.";
        row.append(mathElement("p", detailText, "meta xts-block-detail"));
      }
      chainEl.append(row);
    });
  }, reportError, "XTS-AES tweak error");

  $("xts-random").addEventListener("click", () => {
    xtsT0Input.value = random128BitHex();
    if (!xtsStepsInput.value.trim()) xtsStepsInput.value = "6";
    runXts();
  });

  $("xts-step-next").addEventListener("click", () => {
    if (!xtsT0Input.value.trim()) xtsT0Input.value = DEFAULT_XTS_TWEAK;
    const currentSteps = Number(xtsStepsInput.value) || 0;
    if (currentSteps < 16) {
      xtsStepsInput.value = String(Math.max(1, currentSteps + 1));
    } else {
      xtsT0Input.value = lastXtsLastTweak || DEFAULT_XTS_TWEAK;
      xtsStepsInput.value = "1";
    }
    runXts();
  });

  $("xts-reset").addEventListener("click", () => {
    xtsT0Input.value = "";
    xtsStepsInput.value = "";
    $("xts-results").hidden = true;
    $("xts-status").textContent = "";
    $("xts-chain").replaceChildren();
    lastXtsLastTweak = DEFAULT_XTS_TWEAK;
    lastResults.xts = null;
  });

  // --- Sub-Tab 2: Binary ECC Explorer ---
  const eccCurveSelect = $("ecc-curve");
  const eccNaInput = $("ecc-na");
  const eccNbInput = $("ecc-nb");

  const runEcc = bindExperiment("ecc-form", ["ecc-results"], async () => {
    const nA = Math.max(2, Math.min(25, Number(eccNaInput.value) || 5));
    const nB = Math.max(2, Math.min(25, Number(eccNbInput.value) || 9));
    eccNaInput.value = String(nA);
    eccNbInput.value = String(nB);

    const data = await api("explorations/binary-ecc", {
      curve: eccCurveSelect.value,
      n_a: nA,
      n_b: nB,
    });
    lastResults.ecc = data;
    const curve = data.curve;
    const mDeg = curve.m;
    const gOnCurve = Boolean(curve.base_point_g?.on_curve);
    const dblOnCurve = Boolean(data.doubling?.result?.on_curve);
    const addOnCurve = Boolean(data.addition?.result?.on_curve);
    const ecdh = data.ecdh;

    setMathText($("ecc-curve-badge"), curve.name + " · GF(2^" + mDeg + ")");
    status(
      "ecc-status",
      curve.name + " (" + curve.standard + ") · G, 2G, 3G, and ECDH shared secret K all verified on curve y^2 + xy = x^3 + ax^2 + b",
      gOnCurve && dblOnCurve && addOnCurve && ecdh.shared_secret_matches && ecdh.all_points_on_curve,
    );

    // Curve parameters summary (aligned with classroom "Polynomial ECC" slide)
    const infoEl = $("ecc-curve-info");
    infoEl.replaceChildren();
    const dl = element("dl", undefined, "equivalents ecc-params-dl");
    dl.append(
      element("dt", "Curve equation"),
      mathElement("dd", curve.equation + " mod m(x)   (a = " + curve.a.hex.toUpperCase() + "; a, b, x, y are polynomials)"),
      element("dt", "Irreducible m(x)"),
      mathElement("dd", curve.modulus_poly),
      element("dt", "Parameter b"),
      (() => {
        const dd = element("dd");
        dd.append(makeEccCoordSpan(curve.b.hex, mDeg, curve.name + " · Curve parameter b"));
        return dd;
      })(),
      element("dt", "Base point G"),
      (() => {
        const dd = element("dd");
        dd.append(renderPointDisplay(curve.base_point_g, mDeg, "Base point G"));
        return dd;
      })(),
    );
    infoEl.append(dl);

    // Point Doubling (R = 2P) and Point Addition (R = P + Q) aligned to classroom Polynomial ECC slide notation
    const slideStepSpecs = {
      doubling: [
        { symbol: "Y_p / X_p", formula: "Y_p · X_p^-1 mod m(x)" },
        { symbol: "s", formula: "s = X_p + Y_p / X_p" },
        { symbol: "X_r", formula: "X_r = s^2 + s + a" },
        { symbol: "Y_r", formula: "Y_r = X_p^2 + (s + 1) * X_r" },
      ],
      addition: [
        { symbol: "s", formula: "s = (Y_p - Y_q) / (X_p + X_q)   (note: -Y_q = +Y_q in GF(2^m))" },
        { symbol: "X_r", formula: "X_r = s^2 + s + X_p + X_q + a" },
        { symbol: "Y_r", formula: "Y_r = s(X_p + X_r) + X_r + Y_p" },
      ],
    };

    const opsGrid = $("ecc-ops-grid");
    opsGrid.replaceChildren();
    for (const [kind, title, opData, resultLabel] of [
      ["doubling", "Point Doubling (R = 2P = 2G, P = (X_p, Y_p))", data.doubling, "R = (X_r, Y_r) = 2G"],
      ["addition", "Point Addition (R = P + Q = G + 2G = 3G, P = (X_p, Y_p), Q = (X_q, Y_q))", data.addition, "R = (X_r, Y_r) = 3G"],
    ]) {
      const onCurve = Boolean(opData.result?.on_curve);
      const card = element("section", undefined, "ecc-op-card");
      const head = element("div", undefined, "ecc-op-head");
      head.append(
        mathElement("h3", title),
        element(
          "span",
          onCurve ? "Verified on curve ✓" : "Curve check failed",
          "ecc-verified-badge" + (onCurve ? "" : " failed"),
        ),
      );

      const stepsList = element("div", undefined, "ecc-steps-list");
      const rawSteps = opData.steps || [];
      rawSteps.forEach((st, idx) => {
        const slideSpec = slideStepSpecs[kind]?.[idx];
        const sym = slideSpec ? slideSpec.symbol : st.symbol;
        const form = slideSpec ? slideSpec.formula : st.formula;
        const stepRow = element("div", undefined, "ecc-step-row");
        const stepTop = element("div", undefined, "ecc-step-top");
        stepTop.append(
          mathElement("strong", sym),
          mathElement("span", st.engine_op, "ecc-engine-tag"),
        );
        stepRow.append(
          stepTop,
          mathElement("code", form, "ecc-step-formula"),
          makeEccCoordSpan(st.value.hex, mDeg, title + " · " + sym),
        );
        stepsList.append(stepRow);
      });

      const resWrap = element("div", undefined, "ecc-op-result");
      resWrap.append(
        mathElement("span", "Resulting Point " + resultLabel, "mul-step-result-label"),
        renderPointDisplay(opData.result, mDeg, "Result point " + resultLabel),
      );
      card.append(head, stepsList, resWrap);
      opsGrid.append(card);
    }

    // Compact ECDH Key Exchange Card
    const ecdhCard = $("ecc-ecdh-card");
    ecdhCard.replaceChildren();
    const ecdhHead = element("div", undefined, "ecc-op-head");
    const ecdhTitle = mathElement("h3", "Elliptic Curve Diffie-Hellman (ECDH) Key Exchange");
    ecdhTitle.id = "ecc-ecdh-title";
    const ecdhOk = Boolean(ecdh.shared_secret_matches && ecdh.all_points_on_curve);
    ecdhHead.append(
      ecdhTitle,
      element(
        "span",
        ecdhOk ? "Shared secret matches · Verified on curve ✓" : "Mismatch",
        "ecc-verified-badge" + (ecdhOk ? "" : " failed"),
      ),
    );
    const ecdhGrid = element("div", undefined, "ecc-ecdh-grid");
    const aliceBox = element("div", undefined, "ecc-ecdh-party");
    aliceBox.append(
      mathElement("strong", "Alice · Private key n_A = " + ecdh.n_a),
      mathElement("span", "Public key P_A = " + ecdh.n_a + "G", "meta"),
      renderPointDisplay(ecdh.public_a, mDeg, "Alice public key P_A"),
      mathElement("span", "Derived secret K_A = " + ecdh.n_a + "·P_B", "meta"),
      renderPointDisplay(ecdh.shared_a, mDeg, "Alice shared secret K_A"),
    );
    const bobBox = element("div", undefined, "ecc-ecdh-party");
    bobBox.append(
      mathElement("strong", "Bob · Private key n_B = " + ecdh.n_b),
      mathElement("span", "Public key P_B = " + ecdh.n_b + "G", "meta"),
      renderPointDisplay(ecdh.public_b, mDeg, "Bob public key P_B"),
      mathElement("span", "Derived secret K_B = " + ecdh.n_b + "·P_A", "meta"),
      renderPointDisplay(ecdh.shared_b, mDeg, "Bob shared secret K_B"),
    );
    ecdhGrid.append(aliceBox, bobBox);
    ecdhCard.append(
      ecdhHead,
      mathElement("p", "Both parties perform scalar multiplication via double-and-add over GF(2^" + mDeg + ") and arrive at the exact same curve point K = n_A P_B = n_B P_A.", "meta"),
      ecdhGrid,
    );
  }, reportError, "Binary ECC error");

  $("ecc-random").addEventListener("click", () => {
    eccNaInput.value = String(2 + Math.floor(Math.random() * 24));
    eccNbInput.value = String(2 + Math.floor(Math.random() * 24));
    runEcc();
  });
  $("ecc-switch-teaching").addEventListener("click", () => {
    eccCurveSelect.value = "gf2_4";
    if (!eccNaInput.value.trim()) eccNaInput.value = "5";
    if (!eccNbInput.value.trim()) eccNbInput.value = "9";
    runEcc();
  });
  $("ecc-switch-b163").addEventListener("click", () => {
    eccCurveSelect.value = "nist_b163";
    if (!eccNaInput.value.trim()) eccNaInput.value = "5";
    if (!eccNbInput.value.trim()) eccNbInput.value = "9";
    runEcc();
  });
  eccCurveSelect.addEventListener("change", () => {
    if (eccNaInput.value.trim() && eccNbInput.value.trim()) runEcc();
  });

  // --- Sub-Tab 3: GCM / GHASH GF(2^128) Authenticator ---
  const ghashHInput = $("ghash-h");
  const ghashBlocksInput = $("ghash-blocks");
  ghashHInput.addEventListener("input", () => applyInputFormatting(ghashHInput, "hex"));
  ghashBlocksInput.addEventListener("input", () => {
    const start = ghashBlocksInput.selectionStart;
    const end = ghashBlocksInput.selectionEnd;
    const upper = ghashBlocksInput.value.replace(/[a-f]/g, ch => ch.toUpperCase());
    if (upper !== ghashBlocksInput.value) {
      ghashBlocksInput.value = upper;
      if (start !== null && end !== null) ghashBlocksInput.setSelectionRange(start, end);
    }
  });

  /**
   * Parse non-empty trimmed lines from the GHASH blocks textarea.
   * @returns {string[]} Uppercase block strings.
   */
  function readGhashBlocks() {
    return ghashBlocksInput.value
      .split(/\r?\n/)
      .map(line => line.trim().toUpperCase())
      .filter(Boolean);
  }

  const runGhash = bindExperiment("ghash-form", ["ghash-results"], async () => {
    const blocks = readGhashBlocks();
    const data = await api("explorations/gcm-ghash", {
      h_hex: ghashHInput.value.trim().toUpperCase(),
      blocks_hex: blocks,
    });
    lastResults.ghash = data;
    setMathText($("ghash-modulus-badge"), "m(x) = " + data.modulus_poly);
    status(
      "ghash-status",
      "Hashed " + data.block_count + (data.block_count === 1 ? " block" : " blocks") +
        " in GF(2^128) · " + data.elapsed_ms.toFixed(3) + " ms · H = " + data.h_hex.slice(0, 10) + "…" + data.h_hex.slice(-6),
      true,
    );

    const tagDisplay = $("ghash-tag-display");
    tagDisplay.replaceChildren(
      mathElement("span", "128-bit GHASH Value (Y_" + data.block_count + ")", "ghash-tag-label"),
      makeGhashInspectButton(
        data.tag_hex,
        "GHASH Value (Y_" + data.block_count + ")",
        "Final 128-bit GHASH value in NIST block order over GF(2^128) mod (x^128 + x^7 + x^2 + x + 1)",
        false,
        "ghash-tag-btn",
      ),
    );

    const stepsWrap = $("ghash-steps");
    const box = element("div", undefined, "trace-table");
    box.setAttribute("role", "region");
    box.setAttribute("aria-label", "GHASH block-by-block chain");
    box.tabIndex = 0;
    const tbl = element("table", undefined, "ghash-table");
    const thead = element("thead");
    const headRow = element("tr");
    for (const heading of ["Block i", "X_i (hex)", "Y_{i-1} ⊕ X_i (hex)", "Y_i = (Y_{i-1} ⊕ X_i) · H mod m(x)"]) {
      headRow.append(mathElement("th", heading));
    }
    thead.append(headRow);
    const tbody = element("tbody");
    for (const st of data.steps) {
      const tr = element("tr");
      tr.append(element("td", String(st.block_index)));
      const tdX = element("td");
      tdX.append(makeGhashInspectButton(st.x_i_hex, "Block X_" + st.block_index, "Input 128-bit block X_" + st.block_index, true));
      const tdXor = element("td");
      tdXor.append(makeGhashInspectButton(st.xor_input_hex, "Y_" + (st.block_index - 1) + " ⊕ X_" + st.block_index, "Pre-multiplication XOR state for block " + st.block_index, true));
      const tdY = element("td");
      if (st.block_index === data.block_count) tdY.className = "picked";
      tdY.append(makeGhashInspectButton(st.y_i_hex, "GHASH State Y_" + st.block_index, "Output after GF(2^128) multiplication by H", true));
      tr.append(tdX, tdXor, tdY);
      tbody.append(tr);
    }
    tbl.append(thead, tbody);
    box.append(tbl);
    stepsWrap.replaceChildren(box);
  }, reportError, "GCM / GHASH error");

  $("ghash-random").addEventListener("click", () => {
    ghashHInput.value = random128BitHex();
    ghashBlocksInput.value = [random128BitHex(), random128BitHex(), random128BitHex()].join("\n");
    runGhash();
  });

  $("ghash-reset").addEventListener("click", () => {
    ghashHInput.value = "";
    ghashBlocksInput.value = "";
    $("ghash-results").hidden = true;
    $("ghash-status").textContent = "";
    $("ghash-tag-display").replaceChildren();
    $("ghash-steps").replaceChildren();
    lastResults.ghash = null;
  });

  $("ghash-save-key").addEventListener("click", () => {
    try {
      const hHex = normalize128BitHex(ghashHInput.value, "Hash subkey H");
      ghashHInput.value = hHex;
      downloadJsonFile(
        "ghash-key-H.json",
        {
          algorithm: "GCM-GHASH",
          field: "GF(2^128)",
          modulus_hex: "100000000000000000000000000000087",
          h_hex: hHex,
        },
        "Saved 128-bit GHASH hash subkey H",
      );
    } catch (error) {
      reportError(error.message, "Save key error");
    }
  });

  $("ghash-share-key").addEventListener("click", async () => {
    try {
      const hHex = normalize128BitHex(ghashHInput.value, "Hash subkey H");
      ghashHInput.value = hHex;
      const url = new URL(location.pathname, location.origin);
      url.search = new URLSearchParams({ app: "ghash", h: hHex });
      url.hash = "applications";
      const copied = await copyToClipboard(url.href);
      if (copied) {
        showFeedbackPopup("GHASH key link copied", "Key-only share link for H copied to clipboard");
      } else {
        window.prompt("Copy GHASH key link", url.href);
      }
    } catch (error) {
      reportError(error.message, "Share key error");
    }
  });

  // --- Sub-Tab 4: AES S-Box GF(2^8) Byte Substitution ---
  const aesByteInput = $("aes-byte");
  const aesBaseSelect = $("aes-base");
  const aesTrace = createTraceView($("aes-trace"), $("aes-trace-body"), $("aes-trace-tools"));
  const aesAffine = createTraceView($("aes-affine"), $("aes-affine-table"), $("aes-affine-tools"));

  aesByteInput.addEventListener("input", () => {
    if (aesBaseSelect.value === "hex") applyInputFormatting(aesByteInput, "hex");
  });
  aesBaseSelect.addEventListener("change", () => {
    if (aesBaseSelect.value === "hex") applyInputFormatting(aesByteInput, "hex");
  });

  const runAes = bindExperiment("aes-form", ["aes-result", "aes-affine"], async () => {
    const rawByte = aesByteInput.value.trim();
    const baseVal = aesBaseSelect.value;
    const data = await api("explorations/aes-sbox", {
      byte: baseVal === "hex" ? rawByte.toUpperCase() : rawByte,
      input_base: baseVal,
    });
    lastResults.aes = data;
    $("aes-pipeline").replaceChildren();
    for (const [label, value] of [["Input byte", data.input], ["Inverse stage", data.inverse], ["S-box output", data.output]]) {
      const cell = element("div");
      const bytes = element("dd", hex(value));
      bytes.append(element("span", value.bin));
      cell.append(element("dt", label), bytes);
      $("aes-pipeline").append(cell);
    }
    $("aes-inverse-note").textContent = data.inverse_trace
      ? "Find the multiplicative inverse modulo the AES polynomial 11B (hex), then apply the affine transformation."
      : "AES maps a zero input to zero in the inversion stage. The affine constant then gives an S-box output of 63 (hex).";
    $("aes-euclid").hidden = !data.inverse_trace;
    aesTrace.show(data.inverse_trace);
    aesAffine.show({
      trace_type: "tabular_steps",
      title: "XOR by step",
      headers: ["Term", "Added (hex)", "Added (binary)", "Running XOR (hex)"],
      rows: data.affine_rows.map(row => [row.label, hex(row.value), row.value.bin, hex(row.running)]),
      selected: (row, col) => row === data.affine_rows.length - 1 && col === 3,
    });
  }, reportError, "AES S-Box error");

  $("aes-random").addEventListener("click", () => {
    const bytes = new Uint8Array(1);
    if (window.crypto?.getRandomValues) window.crypto.getRandomValues(bytes);
    else bytes[0] = Math.floor(Math.random() * 256);
    const val = bytes[0];
    aesByteInput.value = aesBaseSelect.value === "binary"
      ? val.toString(2).padStart(8, "0")
      : val.toString(16).toUpperCase().padStart(2, "0");
    runAes();
  });

  for (const [id, byteHex] of [["aes-example", "53"], ["aes-preset-95", "95"], ["aes-zero", "00"]]) {
    $(id).addEventListener("click", () => {
      aesBaseSelect.value = "hex";
      aesByteInput.value = byteHex;
      runAes();
    });
  }

  // --- Shared Export JSON / Import JSON across all 4 Applications sub-tabs ---
  /**
   * Build and download a structured JSON snapshot for one Applications sub-tab.
   * @param {"xts" | "ecc" | "ghash" | "aes"} appKey - Sub-tab identifier.
   */
  function exportAppJson(appKey) {
    try {
      if (appKey === "xts") {
        const t0Hex = normalize128BitHex(xtsT0Input.value, "Initial 128-bit tweak T0");
        const steps = Number(xtsStepsInput.value);
        if (!Number.isInteger(steps) || steps < 1 || steps > 16) {
          throw new Error("Enter a valid number of blocks (1 to 16) before exporting.");
        }
        downloadJsonFile(
          "gf2m-xts-aes.json",
          { application: "xts", inputs: { t0_hex: t0Hex, steps }, result: lastResults.xts },
          "Saved XTS-AES inputs and result",
        );
        return;
      }
      if (appKey === "ecc") {
        const nA = Number(eccNaInput.value);
        const nB = Number(eccNbInput.value);
        if (!Number.isInteger(nA) || nA < 2 || nA > 25 || !Number.isInteger(nB) || nB < 2 || nB > 25) {
          throw new Error("Enter valid Alice and Bob private keys (2 to 25) before exporting.");
        }
        downloadJsonFile(
          "gf2m-binary-ecc.json",
          { application: "ecc", inputs: { curve: eccCurveSelect.value, n_a: nA, n_b: nB }, result: lastResults.ecc },
          "Saved Binary ECC scenario and result",
        );
        return;
      }
      if (appKey === "ghash") {
        const hHex = normalize128BitHex(ghashHInput.value, "Hash subkey H");
        const rawBlocks = readGhashBlocks();
        if (!rawBlocks.length || rawBlocks.length > 8) {
          throw new Error("Enter 1 to 8 128-bit hex blocks before exporting.");
        }
        const blocks = rawBlocks.map((blk, i) => normalize128BitHex(blk, "Block X_" + (i + 1)));
        downloadJsonFile(
          "gf2m-gcm-ghash.json",
          { application: "ghash", inputs: { h_hex: hHex, blocks_hex: blocks }, result: lastResults.ghash },
          "Saved GCM / GHASH inputs and result",
        );
        return;
      }
      const rawByte = aesByteInput.value.trim();
      const baseVal = aesBaseSelect.value;
      if (!rawByte) throw new Error("Enter an AES input byte before exporting.");
      if (baseVal === "hex" && !/^(0x)?[0-9a-fA-F]{1,2}$/.test(rawByte)) {
        throw new Error("Enter one valid hex byte (00 to FF) before exporting.");
      }
      if (baseVal === "binary" && !/^(0b)?[01]{1,8}$/i.test(rawByte)) {
        throw new Error("Enter one valid 8-bit binary byte before exporting.");
      }
      downloadJsonFile(
        "gf2m-aes-sbox.json",
        {
          application: "aes",
          inputs: { byte: baseVal === "hex" ? rawByte.toUpperCase() : rawByte, input_base: baseVal },
          result: lastResults.aes,
        },
        "Saved AES S-Box input and result",
      );
    } catch (error) {
      reportError(error.message, "Export JSON error");
    }
  }

  /**
   * Read, validate, and load an imported Applications JSON file (including `ghash-key-H.json`).
   * @param {File | undefined} file - Selected JSON file.
   */
  async function importAppJson(file) {
    if (!file) return;
    try {
      let parsed;
      try {
        parsed = JSON.parse(await file.text());
      } catch {
        throw new Error("Invalid JSON file. Check syntax and try again.");
      }
      if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
        throw new Error("JSON root must be an object with application inputs.");
      }

      // Support importing a saved GHASH key-only file (ghash-key-H.json).
      if (parsed.algorithm === "GCM-GHASH" && typeof parsed.h_hex === "string" && !parsed.application) {
        const hHex = normalize128BitHex(parsed.h_hex, "Hash subkey H");
        selectAppTab("ghash");
        ghashHInput.value = hHex;
        showFeedbackPopup("Imported " + file.name, "Loaded 128-bit GHASH key H");
        return;
      }

      const appKey = String(parsed.application || "").toLowerCase();
      const inputs = parsed.inputs;
      if (!["xts", "ecc", "ghash", "aes"].includes(appKey) || !inputs || typeof inputs !== "object") {
        throw new Error('JSON must specify "application" ("xts", "ecc", "ghash", or "aes") and an "inputs" object.');
      }

      if (appKey === "xts") {
        const t0Hex = normalize128BitHex(inputs.t0_hex, "Initial tweak T0");
        const steps = Number(inputs.steps ?? 6);
        if (!Number.isInteger(steps) || steps < 1 || steps > 16) {
          throw new Error("XTS-AES steps must be an integer between 1 and 16.");
        }
        selectAppTab("xts");
        xtsT0Input.value = t0Hex;
        xtsStepsInput.value = String(steps);
        runXts();
        showFeedbackPopup("Imported " + file.name, "Loaded XTS-AES scenario");
        return;
      }

      if (appKey === "ecc") {
        const curve = String(inputs.curve || "nist_b163");
        if (curve !== "gf2_4" && curve !== "nist_b163") {
          throw new Error('Binary ECC curve must be "gf2_4" or "nist_b163".');
        }
        const nA = Number(inputs.n_a);
        const nB = Number(inputs.n_b);
        if (!Number.isInteger(nA) || nA < 2 || nA > 25 || !Number.isInteger(nB) || nB < 2 || nB > 25) {
          throw new Error("Binary ECC private keys n_a and n_b must be integers from 2 to 25.");
        }
        selectAppTab("ecc");
        eccCurveSelect.value = curve;
        eccNaInput.value = String(nA);
        eccNbInput.value = String(nB);
        runEcc();
        showFeedbackPopup("Imported " + file.name, "Loaded Binary ECC scenario");
        return;
      }

      if (appKey === "ghash") {
        const hHex = normalize128BitHex(inputs.h_hex, "Hash subkey H");
        if (!Array.isArray(inputs.blocks_hex) || inputs.blocks_hex.length < 1 || inputs.blocks_hex.length > 8) {
          throw new Error("GHASH JSON must contain 1 to 8 hex strings in inputs.blocks_hex.");
        }
        const blocks = inputs.blocks_hex.map((blk, i) => normalize128BitHex(blk, "Block X_" + (i + 1)));
        selectAppTab("ghash");
        ghashHInput.value = hHex;
        ghashBlocksInput.value = blocks.join("\n");
        runGhash();
        showFeedbackPopup("Imported " + file.name, "Loaded GCM / GHASH inputs");
        return;
      }

      const inputBase = inputs.input_base === "binary" ? "binary" : "hex";
      const rawByte = String(inputs.byte ?? "").trim();
      if (!rawByte) throw new Error("AES S-Box JSON must include inputs.byte.");
      if (inputBase === "hex" && !/^(0x)?[0-9a-fA-F]{1,2}$/.test(rawByte)) {
        throw new Error("AES S-Box hex byte must be 1 to 2 hex digits (00 to FF).");
      }
      if (inputBase === "binary" && !/^(0b)?[01]{1,8}$/i.test(rawByte)) {
        throw new Error("AES S-Box binary byte must be 1 to 8 binary digits.");
      }
      selectAppTab("aes");
      aesBaseSelect.value = inputBase;
      aesByteInput.value = inputBase === "hex" ? rawByte.replace(/^0x/i, "").toUpperCase() : rawByte.replace(/^0b/i, "");
      runAes();
      showFeedbackPopup("Imported " + file.name, "Loaded AES S-Box input");
    } catch (error) {
      reportError(error.message, "Import JSON error");
    }
  }

  for (const appKey of ["xts", "ecc", "ghash", "aes"]) {
    $(appKey + "-export-json").addEventListener("click", () => exportAppJson(appKey));
    const fileInput = $(appKey + "-import-file");
    $(appKey + "-import-json").addEventListener("click", () => fileInput.click());
    fileInput.addEventListener("change", async () => {
      try {
        await importAppJson(fileInput.files?.[0]);
      } finally {
        fileInput.value = "";
      }
    });
  }

  /**
   * Synchronize the `#applications` hero badge with the active sub-tab:
   *   - `xts`:   `GF(2^128) · IEEE 1619`
   *   - `ecc`:   `GF(2^163) · NIST B-163`
   *   - `ghash`: `GF(2^128) · NIST SP 800-38D`
   *   - `aes`:   `GF(2^8) · FIPS 197 · Ch. 5`
   *
   * @param {"xts" | "ecc" | "ghash" | "aes"} tabKey - Active application sub-tab.
   */
  function syncHeroBadge(tabKey) {
    const fieldEl = $("app-hero-field");
    const stdEl = $("app-hero-std");
    if (!fieldEl || !stdEl) return;
    if (tabKey === "ecc") {
      setMathText(fieldEl, "GF(2^163)");
      stdEl.textContent = "NIST B-163";
    } else if (tabKey === "ghash") {
      setMathText(fieldEl, "GF(2^128)");
      stdEl.textContent = "NIST SP 800-38D";
    } else if (tabKey === "aes") {
      setMathText(fieldEl, "GF(2^8)");
      stdEl.textContent = "FIPS 197 · Ch. 5";
    } else {
      setMathText(fieldEl, "GF(2^128)");
      stdEl.textContent = "IEEE 1619";
    }
  }

  /**
   * Switch between the XTS-AES, Binary ECC, GCM / GHASH, and AES S-Box application sub-tabs,
   * update the hero badge, and glide the active pill.
   *
   * @param {"xts" | "ecc" | "ghash" | "aes"} tabKey - Sub-tab key.
   */
  function selectAppTab(tabKey) {
    activeApp = ["xts", "ecc", "ghash", "aes"].includes(tabKey) ? tabKey : "xts";
    for (const btn of subtabButtons) {
      const isActive = btn.dataset.appTab === activeApp;
      btn.setAttribute("aria-selected", String(isActive));
      btn.setAttribute("aria-pressed", String(isActive));
    }
    subpanels.xts.hidden = activeApp !== "xts";
    subpanels.ecc.hidden = activeApp !== "ecc";
    subpanels.ghash.hidden = activeApp !== "ghash";
    subpanels.aes.hidden = activeApp !== "aes";
    syncHeroBadge(activeApp);
    subtabsIndicator.update();
  }

  for (const btn of subtabButtons) {
    btn.addEventListener("click", () => selectAppTab(btn.dataset.appTab));
  }

  let restoredFromQuery = false;

  /**
   * Restore a shared `#applications` URL state (`?app=xts...`, `?app=ecc...`, `?app=ghash...`,
   * or `?app=aes...`) and compute live when full inputs are supplied (leaving key-only GHASH
   * links ready for block input).
   *
   * @param {URLSearchParams} params - Parsed URL query parameters.
   * @returns {boolean} True when an application state was restored.
   */
  function restoreShareState(params) {
    const app = (params.get("app") || "").toLowerCase();
    if (app === "ecc") {
      restoredFromQuery = true;
      const curve = params.get("curve");
      if (curve === "gf2_4" || curve === "nist_b163") eccCurveSelect.value = curve;
      const na = Number(params.get("na"));
      if (Number.isInteger(na) && na >= 2 && na <= 25) eccNaInput.value = String(na);
      const nb = Number(params.get("nb"));
      if (Number.isInteger(nb) && nb >= 2 && nb <= 25) eccNbInput.value = String(nb);
      selectAppTab("ecc");
      runEcc();
      return true;
    }
    if (app === "ghash") {
      restoredFromQuery = true;
      const hParam = params.get("h");
      if (hParam) ghashHInput.value = hParam.trim().toUpperCase();
      const blocksParam = params.get("blocks");
      let hasBlocks = false;
      if (blocksParam) {
        const list = blocksParam.split(",").map(item => item.trim().toUpperCase()).filter(Boolean).slice(0, 8);
        if (list.length) {
          ghashBlocksInput.value = list.join("\n");
          hasBlocks = true;
        }
      }
      selectAppTab("ghash");
      // Only auto-compute when blocks are supplied; key-only links (?app=ghash&h=...) leave blocks ready for input.
      if (hasBlocks) runGhash();
      return true;
    }
    if (app === "aes") {
      restoredFromQuery = true;
      const baseParam = (params.get("base") || "hex").toLowerCase();
      aesBaseSelect.value = baseParam === "binary" ? "binary" : "hex";
      const byteParam = params.get("byte");
      if (byteParam) {
        aesByteInput.value = aesBaseSelect.value === "hex" ? byteParam.trim().toUpperCase() : byteParam.trim();
      }
      selectAppTab("aes");
      if (byteParam && byteParam.trim()) runAes();
      return true;
    }
    if (app === "xts") {
      restoredFromQuery = true;
      const t0 = params.get("t0");
      if (t0) xtsT0Input.value = t0.trim().toUpperCase();
      const steps = Number(params.get("steps"));
      if (Number.isInteger(steps) && steps >= 1 && steps <= 16) xtsStepsInput.value = String(steps);
      selectAppTab("xts");
      runXts();
      return true;
    }
    return false;
  }

  return {
    onActivate(forcedTab) {
      if (forcedTab) {
        selectAppTab(forcedTab);
      } else {
        syncHeroBadge(activeApp);
        subtabsIndicator.update();
      }
      if (!restoredFromQuery) {
        const params = new URLSearchParams(location.search);
        if (params.has("app")) restoreShareState(params);
      }
    },
    /**
     * Serialize active `#applications` sub-tab state for a shareable URL.
     * @returns {{params: Record<string, string>, label: string}} Query params and toast label.
     */
    getShareState() {
      if (activeApp === "ecc") {
        return {
          params: {
            app: "ecc",
            curve: eccCurveSelect.value,
            na: String(eccNaInput.value || 5),
            nb: String(eccNbInput.value || 9),
          },
          label: "Applications (Binary ECC)",
        };
      }
      if (activeApp === "ghash") {
        const params = {
          app: "ghash",
          h: ghashHInput.value.trim().toUpperCase(),
        };
        const blocks = readGhashBlocks();
        if (blocks.length) params.blocks = blocks.join(",");
        return {
          params,
          label: "Applications (GCM / GHASH)",
        };
      }
      if (activeApp === "aes") {
        const params = {
          app: "aes",
          byte: aesByteInput.value.trim().toUpperCase(),
        };
        if (aesBaseSelect.value === "binary") params.base = "binary";
        return {
          params,
          label: "Applications (AES S-Box)",
        };
      }
      return {
        params: {
          app: "xts",
          t0: xtsT0Input.value.trim().toUpperCase(),
          steps: String(xtsStepsInput.value || 6),
        },
        label: "Applications (XTS-AES)",
      };
    },
    restoreShareState(params) {
      if (restoredFromQuery) return true;
      return restoreShareState(params);
    },
  };
}

/**
 * Configure the Multiplication Comparison lab (`#compare`), operand transfer, auto-uppercase hex
 * formatting, and 163/571-bit benchmark.
 *
 * @param {(path: string, data?: object) => Promise<any>} api - Shared JSON API client.
 * @param {() => {m: number, a: string, b: string}} currentOperands - Accessor reading calculator operands in hex.
 * @param {(msg: string, title?: string) => void} reportError - Error alert reporter.
 */
function setupComparison(api, currentOperands, reportError) {
  const shiftTrace = createTraceView($("compare-shift"), $("compare-shift-body"), $("compare-shift-tools"));
  const longDivision = createTraceView($("compare-division-trace"), $("compare-division-body"), $("compare-division-tools"));
  const compareOverlays = ["compare-a", "compare-b"].map(id => {
    const input = $(id);
    const overlay = attachPolyInputOverlay(input, () => /x\s*\^/i.test(input.value));
    input.addEventListener("input", () => {
      applyInputFormatting(input, "hex");
      overlay.sync();
    });
    return overlay;
  });

  const test = bindExperiment("compare-form", ["compare-results"], async () => {
    const data = await api("explorations/compare-multiplication", {
      m: Number($("compare-degree").value), a: $("compare-a").value, b: $("compare-b").value,
    });
    status("compare-status", data.agree ? "Both methods agree · GF(2^" + data.m + ")" : "The methods returned different results", data.agree);
    message("compare-reduced", data.inputs_reduced ? "The operands were reduced first. A = " + hex(data.a) + " and B = " + hex(data.b) + " (hex)." : "");
    $("shift-method-result").textContent = hex(data.shift_result) + " (hex)";
    $("division-method-result").textContent = hex(data.remainder) + " (hex)";
    $("division-method-values").replaceChildren();
    for (const [label, value] of [["Raw product", hex(data.raw_product)], ["Modulus", data.modulus_hex], ["Quotient", hex(data.quotient)]]) {
      $("division-method-values").append(element("dt", label), element("dd", value));
    }
    shiftTrace.show(data.shift_trace);
    longDivision.show({
      trace_type: "tabular_steps",
      title: "Leading-term cancellations",
      headers: ["Shift", "Before (hex)", "Shifted divisor (hex)", "After XOR (hex)"],
      rows: data.division_steps.map(row => [row.shift, row.before_hex, row.divisor_hex, row.after_hex]),
      selected: (row, col) => row === data.division_steps.length - 1 && col === 3,
    });
  }, reportError, "Multiplication comparison error");

  const form = $("compare-form");
  let queuedOperands;
  /**
   * Populate comparison inputs and submit, queueing the latest request if one is already running.
   * @param {{m: number, a: string, b: string}} state - Field degree and hex operands.
   */
  function runWithOperands(state) {
    if (form.getAttribute("aria-busy") === "true") {
      queuedOperands = state;
      return;
    }
    $("compare-degree").value = state.m;
    $("compare-a").value = state.a.toUpperCase();
    $("compare-b").value = state.b.toUpperCase();
    compareOverlays.forEach(o => o.sync());
    $("compare-results").hidden = true;
    test();
  }
  form.addEventListener("lab:calculation-result", () => {
    if (queuedOperands) {
      const state = queuedOperands;
      queuedOperands = undefined;
      runWithOperands(state);
    }
  });
  for (const [id, navigate] of [["compare-current", false], ["compare-product", true]]) {
    $(id).addEventListener("click", () => {
      try {
        const state = currentOperands();
        if (navigate) window.location.hash = "compare";
        runWithOperands(state);
      } catch (error) {
        reportError(error.message, "Multiplication comparison error");
      }
    });
  }
  $("compare-random").addEventListener("click", async () => {
    try {
      const m = Number($("compare-degree").value || 8);
      const pair = await api("random-polynomials", { m, density: "sparse" });
      runWithOperands({ m, a: pair.a.hex.toUpperCase(), b: pair.b.hex.toUpperCase() });
    } catch (error) {
      reportError(error.message, "Random operand error");
    }
  });

  const benchmark = $("run-benchmark");
  benchmark.addEventListener("click", async () => {
    benchmark.disabled = true;
    $("benchmark-results").textContent = "Running benchmark…";
    try {
      const data = await api("explorations/multiplication-benchmarks");
      const rows = data.rows.map(row => [row.m + " bits", row.shift_xor_us.toFixed(2) + " µs",
        row.long_division_us.toFixed(2) + " µs", row.agree ? "Match" : "Mismatch"]);
      $("benchmark-results").replaceChildren(
        table("Median time per multiplication", ["Field degree", "Shift and XOR", "Carry-free + long division", "Results"], rows),
        element("p", data.trials + " trials per method per field. Operand seed " + data.seed + "."),
      );
    } catch (error) {
      $("benchmark-results").replaceChildren();
      reportError(error.message, "Benchmark error");
    } finally {
      benchmark.disabled = false;
    }
  });

  return {
    /**
     * Serialize current `#compare` inputs for a shareable URL.
     * @returns {{m: string, a: string, b: string}} Hex-compressed comparison parameters.
     */
    getShareState() {
      return {
        m: String($("compare-degree").value || "8"),
        a: $("compare-a").value.trim().toUpperCase(),
        b: $("compare-b").value.trim().toUpperCase(),
      };
    },
    /**
     * Restore a shared `#compare` URL (`?m=...&a=...&b=...#compare`) and run the comparison.
     * @param {URLSearchParams} params - Parsed URL query parameters.
     * @returns {boolean} True when comparison parameters were restored.
     */
    restoreShareState(params) {
      const m = params.get("m");
      const a = params.get("a");
      const b = params.get("b");
      if (!m || !a || !b) return false;
      const picker = $("compare-degree");
      if (!Array.from(picker.options).some(opt => opt.value === String(m))) return false;
      runWithOperands({ m: Number(m), a, b });
      return true;
    },
  };
}

/**
 * Initialize view navigation and all exploration & application labs (`#modulus`, `#applications`, `#compare`).
 *
 * @param {(path: string, data?: object) => Promise<any>} api - Shared JSON API helper.
 * @param {{closeTour: () => void, currentField: () => object | undefined, currentOperands: () => {m: number, a: string, b: string}, onLessonRoute?: (slug?: string) => void, onViewChange?: (viewName: string) => void, onError?: (msg: string, title?: string) => void}} hooks - Calculator, lesson, view-change & error alert hooks.
 * @returns {{loadFields: (fields: Array<{m: number}>) => void, getShareState: (view: string) => {params: Record<string, string>, label: string} | null, restoreFromURL: (view: string, params: URLSearchParams) => boolean}} Exploration controllers and share-link helpers.
 */
export function setupExplorations(api, { closeTour, currentField, currentOperands, onLessonRoute, onViewChange, onError }) {
  const reportError = onError || ((msg, title) => showErrorPopup({ title, message: msg }));
  const apps = setupApplications(api, reportError);
  const modulusCtrl = setupModulus(api, currentField, reportError);
  const compareCtrl = setupComparison(api, currentOperands, reportError);
  setupNavigation(closeTour, onLessonRoute, apps.onActivate, onViewChange);

  return {
    loadFields(fields) {
      const picker = $("compare-degree");
      picker.replaceChildren(...fields.map(field => {
        const option = element("option", field.m + " bits");
        option.value = field.m;
        return option;
      }));
      picker.value = "8";
    },
    getShareState(view) {
      if (view === "modulus") return { params: modulusCtrl.getShareState(), label: "Modulus explorer" };
      if (view === "applications") return apps.getShareState();
      if (view === "compare") return { params: compareCtrl.getShareState(), label: "Compare multiplication" };
      return null;
    },
    restoreFromURL(view, params) {
      if (view === "modulus") return modulusCtrl.restoreShareState(params);
      if (view === "applications") return apps.restoreShareState(params);
      if (view === "compare") return compareCtrl.restoreShareState(params);
      return false;
    },
  };
}
