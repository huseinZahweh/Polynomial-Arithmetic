/**
 * @fileoverview Hash-based view routing and controllers for the three teaching explorations,
 * upgraded with gliding tab selection, `<sup>`/`<sub>` typography, and pop-up error alerts.
 *
 * Original Author: Ali Zahreddine — Milestone 4, Integration & Milestone 6 (Waves 1–3).
 *
 * Connects the frontend exploration views to `/api/explorations/*`:
 *   - `#modulus` — Binary polynomial irreducibility checker & factor witnesses (Stallings Ch. 4
 *     plus Berlekamp square-free splitting extension).
 *   - `#aes`     — FIPS 197 §5.1.1 / Stallings Ch. 5 AES S-box walkthrough (EEA + affine XOR).
 *   - `#compare` — Shift-and-XOR vs. carry-free + long-division comparison and 163/571-bit benchmark.
 */

import { attachSlidingIndicator, element, mathElement, setMathText, showErrorPopup } from "./notation.js";
import { createTraceView, table } from "./traces.js";

/** @param {string} id @returns {HTMLElement} */
const $ = id => document.getElementById(id);
/** @param {{hex: string}} value @returns {string} */
const hex = value => value.hex.toUpperCase();

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
 * Bind an exploration form with in-flight locking, pop-up error routing, and `lab:calculation-result` dispatch.
 *
 * @param {string} formId - Form element id.
 * @param {string[]} results - Result section ids revealed on success and hidden on failure.
 * @param {() => Promise<void>} calculate - Async handler calling the API and populating the DOM.
 * @param {(msg: string, title?: string) => void} reportError - Pop-up error reporting callback.
 * @param {string} errorTitle - Modal heading shown when `calculate` throws.
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
 * Bind top-level hash navigation (`#calculator`, `#lessons`, `#lessons/<id>`, `#modulus`, `#aes`, `#compare`)
 * and attach the gliding active tab pill to `.lab-nav`.
 *
 * @param {() => void} closeTour - Callback closing any active spotlight walkthrough on switch.
 * @param {(lessonSlug?: string) => void} [onLessonRoute] - Optional callback invoked when `#lessons/<slug>` is navigated.
 */
function setupNavigation(closeTour, onLessonRoute) {
  const nav = document.querySelector(".lab-nav");
  const tabs = Array.from(document.querySelectorAll("[data-lab-tab]"));
  const views = Array.from(document.querySelectorAll("[data-lab-view]"));
  const navIndicator = attachSlidingIndicator(nav, '[aria-current="page"]');

  function selectView(focus) {
    const rawHash = window.location.hash.slice(1);
    const [requested, subroute] = rawHash.split("/");
    const selected = views.find(view => view.dataset.labView === requested) || views[0];
    closeTour();
    for (const view of views) view.hidden = view !== selected;
    for (const tab of tabs) {
      if (tab.dataset.labTab === selected.dataset.labView) tab.setAttribute("aria-current", "page");
      else tab.removeAttribute("aria-current");
    }
    navIndicator.update();
    if (selected.dataset.labView === "lessons" && typeof onLessonRoute === "function") {
      onLessonRoute(subroute);
    }
    // Share-link URL encoding applies specifically to calculator state.
    $("share").hidden = selected.dataset.labView !== "calculator";
    if (focus) {
      window.scrollTo(0, 0);
      selected.querySelector("h1")?.focus({ preventScroll: true });
    }
  }
  window.addEventListener("hashchange", () => selectView(true));
  selectView(false);
}

/**
 * Configure the Modulus explorer (`#modulus`) irreducibility test and factor-witness display.
 *
 * @param {(path: string, data?: object) => Promise<any>} api - Shared JSON API client.
 * @param {() => object | undefined} currentField - Accessor returning the calculator's active field info.
 * @param {(msg: string, title?: string) => void} reportError - Pop-up error reporter.
 */
function setupModulus(api, currentField, reportError) {
  const test = bindExperiment("modulus-form", ["modulus-result"], async () => {
    const data = await api("explorations/modulus", {
      polynomial: $("custom-modulus").value, input_base: $("modulus-base").value,
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
    $("modulus-checks").replaceChildren(table("GCD checkpoints", ["i", "x^(2^i) mod f (hex)", "gcd(f, x^(2^i) + x) (hex)"],
      data.checks.map(row => [row.i, row.power_remainder_hex, row.gcd_hex]),
      (row, col) => col === 2 && data.checks[row].gcd_hex !== "1"));
  }, reportError, "Modulus explorer error");

  function load(text, notation) {
    $("custom-modulus").value = text;
    $("modulus-base").value = notation;
    test();
  }
  $("modulus-example").addEventListener("click", () => load("x^8 + 1", "algebraic"));
  $("modulus-current").addEventListener("click", () => {
    const field = currentField();
    if (field) load(field.reduction_poly_hex.toUpperCase(), "hex");
    else reportError("The calculator field is still loading.", "Modulus explorer");
  });
}

/**
 * Configure the AES S-box walkthrough (`#aes`) rendering inversion + affine XOR steps.
 *
 * @param {(path: string, data?: object) => Promise<any>} api - Shared JSON API client.
 * @param {(msg: string, title?: string) => void} reportError - Pop-up error reporter.
 */
function setupAES(api, reportError) {
  const trace = createTraceView($("aes-trace"), $("aes-trace-body"), $("aes-trace-tools"));
  const affine = createTraceView($("aes-affine"), $("aes-affine-table"), $("aes-affine-tools"));
  const test = bindExperiment("aes-form", ["aes-result", "aes-affine"], async () => {
    const data = await api("explorations/aes-sbox", { byte: $("aes-byte").value, input_base: $("aes-base").value });
    $("aes-pipeline").replaceChildren();
    for (const [label, value] of [["Input byte", data.input], ["Inverse stage", data.inverse], ["S-box output", data.output]]) {
      const cell = element("div");
      const bytes = element("dd", hex(value));
      bytes.append(element("span", value.bin));
      cell.append(element("dt", label), bytes);
      $("aes-pipeline").append(cell);
    }
    $("aes-inverse-note").textContent = data.inverse_trace
      ? "Find the multiplicative inverse modulo the AES polynomial 11B (hex), then start the affine transformation."
      : "AES maps a zero input to zero in the inversion stage. The affine constant then gives an S-box output of 63 (hex).";
    $("aes-euclid").hidden = !data.inverse_trace;
    trace.show(data.inverse_trace);
    affine.show({
      trace_type: "tabular_steps",
      title: "XOR by step",
      headers: ["Term", "Added (hex)", "Added (binary)", "Running XOR (hex)"],
      rows: data.affine_rows.map(row => [row.label, hex(row.value), row.value.bin, hex(row.running)]),
      selected: (row, col) => row === data.affine_rows.length - 1 && col === 3,
    });
  }, reportError, "AES S-box error");
  for (const [id, byte] of [["aes-example", "53"], ["aes-zero", "00"]]) {
    $(id).addEventListener("click", () => {
      $("aes-byte").value = byte;
      $("aes-base").value = "hex";
      test();
    });
  }
}

/**
 * Configure the Multiplication Comparison lab (`#compare`), operand transfer, and 163/571-bit benchmark.
 *
 * @param {(path: string, data?: object) => Promise<any>} api - Shared JSON API client.
 * @param {() => {m: number, a: string, b: string}} currentOperands - Accessor reading calculator operands in hex.
 * @param {(msg: string, title?: string) => void} reportError - Pop-up error reporter.
 */
function setupComparison(api, currentOperands, reportError) {
  const shiftTrace = createTraceView($("compare-shift"), $("compare-shift-body"), $("compare-shift-tools"));
  const longDivision = createTraceView($("compare-division-trace"), $("compare-division-body"), $("compare-division-tools"));
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
}

/**
 * Initialize view navigation and all three exploration labs.
 *
 * @param {(path: string, data?: object) => Promise<any>} api - Shared JSON API helper.
 * @param {{closeTour: () => void, currentField: () => object | undefined, currentOperands: () => {m: number, a: string, b: string}, onLessonRoute?: (slug?: string) => void, onError?: (msg: string, title?: string) => void}} hooks - Calculator, lesson & error modal hooks.
 * @returns {(fields: Array<{m: number}>) => void} Callback to populate `#compare-degree` once `/api/fields` loads.
 */
export function setupExplorations(api, { closeTour, currentField, currentOperands, onLessonRoute, onError }) {
  const reportError = onError || ((msg, title) => showErrorPopup({ title, message: msg }));
  setupNavigation(closeTour, onLessonRoute);
  setupModulus(api, currentField, reportError);
  setupAES(api, reportError);
  setupComparison(api, currentOperands, reportError);
  return fields => {
    const picker = $("compare-degree");
    picker.replaceChildren(...fields.map(field => {
      const option = element("option", field.m + " bits");
      option.value = field.m;
      return option;
    }));
    picker.value = "8";
  };
}
