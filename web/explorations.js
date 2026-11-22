import { element } from "./notation.js";
import { createTraceView, table } from "./traces.js";

const $ = id => document.getElementById(id);
const hex = value => value.hex.toUpperCase();

function message(id, text = "") {
  $(id).textContent = text;
  $(id).hidden = !text;
}

function status(id, text, passed) {
  $(id).textContent = text;
  $(id).classList.toggle("failed", !passed);
}

function bindExperiment(formId, errorId, results, calculate) {
  const form = $(formId);
  form.addEventListener("submit", async event => {
    event.preventDefault();
    if (form.getAttribute("aria-busy") === "true") return;
    const controls = Array.from(form.elements).filter(control => !control.disabled);
    form.setAttribute("aria-busy", "true");
    controls.forEach(control => { control.disabled = true; });
    message(errorId);
    try {
      await calculate();
      results.forEach(id => { $(id).hidden = false; });
    } catch (error) {
      results.forEach(id => { $(id).hidden = true; });
      message(errorId, error.message);
    } finally {
      controls.forEach(control => { control.disabled = false; });
      form.removeAttribute("aria-busy");
      form.dispatchEvent(new Event("lab:calculation-result", { bubbles: true }));
    }
  });
  return () => form.requestSubmit();
}

function setupNavigation(closeTour) {
  const tabs = Array.from(document.querySelectorAll("[data-lab-tab]"));
  const views = Array.from(document.querySelectorAll("[data-lab-view]"));
  function selectView(focus) {
    const requested = window.location.hash.slice(1);
    const selected = views.find(view => view.dataset.labView === requested) || views[0];
    closeTour();
    for (const view of views) view.hidden = view !== selected;
    for (const tab of tabs) {
      if (tab.dataset.labTab === selected.dataset.labView) tab.setAttribute("aria-current", "page");
      else tab.removeAttribute("aria-current");
    }
    $("share").hidden = selected.dataset.labView !== "calculator";
    if (focus) {
      window.scrollTo(0, 0);
      selected.querySelector("h1").focus({ preventScroll: true });
    }
  }
  window.addEventListener("hashchange", () => selectView(true));
  selectView(false);
}

function setupModulus(api, currentField) {
  const test = bindExperiment("modulus-form", "modulus-error", ["modulus-result"], async () => {
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
        element("code", "(" + witness.a.poly + ") × (" + witness.b.poly + ") = " + witness.product.poly),
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
  });

  function load(text, notation) {
    $("custom-modulus").value = text;
    $("modulus-base").value = notation;
    test();
  }
  $("modulus-example").addEventListener("click", () => load("x^8 + 1", "algebraic"));
  $("modulus-current").addEventListener("click", () => {
    const field = currentField();
    if (field) load(field.reduction_poly_hex.toUpperCase(), "hex");
    else message("modulus-error", "The calculator field is still loading.");
  });
}

function setupAES(api) {
  const trace = createTraceView($("aes-trace"), $("aes-trace-body"), $("aes-trace-tools"));
  const affine = createTraceView($("aes-affine"), $("aes-affine-table"), $("aes-affine-tools"));
  const test = bindExperiment("aes-form", "aes-error", ["aes-result", "aes-affine"], async () => {
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
  });
  for (const [id, byte] of [["aes-example", "53"], ["aes-zero", "00"]]) {
    $(id).addEventListener("click", () => {
      $("aes-byte").value = byte;
      $("aes-base").value = "hex";
      test();
    });
  }
}

function setupComparison(api, currentOperands) {
  const shiftTrace = createTraceView($("compare-shift"), $("compare-shift-body"), $("compare-shift-tools"));
  const longDivision = createTraceView($("compare-division-trace"), $("compare-division-body"), $("compare-division-tools"));
  const test = bindExperiment("compare-form", "compare-error", ["compare-results"], async () => {
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
  });

  const form = $("compare-form");
  let queuedOperands;
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
        message("compare-error", error.message);
      }
    });
  }

  const benchmark = $("run-benchmark");
  benchmark.addEventListener("click", async () => {
    benchmark.disabled = true;
    message("benchmark-error");
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
      message("benchmark-error", error.message);
    } finally {
      benchmark.disabled = false;
    }
  });
}

export function setupExplorations(api, { closeTour, currentField, currentOperands }) {
  setupNavigation(closeTour);
  setupModulus(api, currentField);
  setupAES(api);
  setupComparison(api, currentOperands);
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
