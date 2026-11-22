import { bases, degreeOf, element, formatOperand, parseOperand, polynomial, significantDigits } from "./notation.js";
import { createTraceView } from "./traces.js";
import { setupPageTour } from "./tour.js";
import { setupExplorations } from "./explorations.js";

const $ = id => document.getElementById(id);
const fields = new Map();
const operands = ["a", "b"];
const operations = new Set(["add", "subtract", "modulo", "multiply", "inverse", "divide"]);
const traceView = createTraceView($("trace-panel"), $("trace-body"), $("trace-tools"));
let base = "hex";
let result;
let showFullResult = false;
let revision = 0;
let slides = [];
let slideIndex = 0;
let uploadPairs = [];

const activeOperation = () => document.querySelector("input[name=operation]:checked").value;
const activeDegree = () => Number($("field").value);
const unary = () => ["modulo", "inverse"].includes(activeOperation());
const operandInput = key => $("poly-" + key);

function selectOperation(op) {
  document.querySelector('input[name="operation"][value="' + op + '"]').checked = true;
}

async function api(path, data, download = false) {
  const response = await fetch("/api/" + path, data === undefined ? {} : {
    method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(data),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw Object.assign(new Error(typeof error.detail === "string" ? error.detail : "Request failed (" + response.status + ")."), { payload: error });
  }
  return download ? response.blob() : response.json();
}

function showError(message = "") {
  $("error").hidden = !message;
  $("error").textContent = message;
}

function showNotice(message = "") {
  $("notice").textContent = message;
}

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

function renderField() {
  const degree = activeDegree();
  const field = fields.get(degree);
  $("hero-degree").textContent = degree;
  $("mod-poly").textContent = field.reduction_poly;
  $("mod-hex").textContent = field.reduction_poly_hex.toUpperCase();
  $("mod-bin").textContent = field.reduction_poly_bin;
}

function readOperand(key) {
  const value = operandInput(key).value;
  if (!value.trim()) throw new Error("Enter operand " + key.toUpperCase() + ".");
  return parseOperand(value, base);
}

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
    label.append(toggle, element("span", bit === 0 ? "1" : "x^" + bit));
    toggle.setAttribute("aria-label", "Operand " + key.toUpperCase() + ", coefficient of x to the power " + bit);
    toggle.addEventListener("change", () => {
      const index = [...bits.querySelectorAll("input")].indexOf(toggle);
      operandInput(key).value = formatOperand(value ^ (1n << BigInt(bit)), base, activeDegree());
      clearCalculation();
      renderOperands();
      $(key + "-bits").querySelectorAll("input")[index].focus();
    });
    bits.append(label);
  }
}

function renderOperands() {
  for (const key of operands) {
    const input = operandInput(key);
    const inactive = key === "b" && unary();
    input.disabled = inactive;
    $("operand-" + key).classList.toggle("inactive", inactive);
    input.placeholder = bases[base].example;
    input.removeAttribute("aria-invalid");
    $(key + "-preview").textContent = "";
    $(key + "-meta").textContent = inactive ? "Unused for this operation" : "";
    let value = 0n;
    let valid = true;
    if (!inactive && input.value.trim()) {
      try {
        value = readOperand(key);
        const degree = degreeOf(value);
        $(key + "-meta").textContent = (degree + 1) + " bits · " + (degree < 0 ? "zero polynomial" : "degree " + degree);
        $(key + "-preview").textContent = polynomial(value);
      } catch (error) {
        valid = false;
        input.setAttribute("aria-invalid", "true");
        $(key + "-meta").textContent = error.message;
      }
    }
    renderBits(key, value, valid);
  }
}

function renderNotation() {
  for (const button of document.querySelectorAll("[data-base]")) {
    button.setAttribute("aria-pressed", button.dataset.base === base);
  }
}

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
      showError("Operand " + key.toUpperCase() + ": " + error.message);
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

function display(value, notation) {
  const text = value[bases[notation].field];
  return notation === "hex" ? text.toUpperCase() : text;
}

function previewValue(text, notation) {
  if (result.field.m <= 8) return text;
  if (notation === "algebraic") {
    const terms = text.split(" + ");
    return terms.length > 4 ? terms.slice(0, 2).join(" + ") + " + … + " + terms.at(-1) : text;
  }
  const significant = significantDigits(text);
  return significant.length > 24 ? significant.slice(0, 14) + "…" + significant.slice(-8) : significant;
}

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
  $("result-value").textContent = values[base];
  $("result-alternatives").replaceChildren();
  for (const [key, info] of Object.entries(bases)) {
    if (key !== base) $("result-alternatives").append(element("dt", info.label), element("dd", values[key]));
  }
  const verification = $("verification");
  verification.hidden = !result.verification;
  if (result.verification) {
    const proof = result.verification;
    verification.classList.toggle("failed", !proof.passed);
    verification.textContent = (proof.passed ? "Mathematically verified · " : "Verification failed · ") + proof.label;
  }
  const metrics = result.metrics;
  $("metrics").replaceChildren(
    element("span", metrics.elapsed_ms.toFixed(3) + " ms"),
    element("span", metrics.result_bit_length + " bits"),
    element("span", "Hamming weight " + metrics.result_hamming_weight),
  );
}

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
    showError(error.message);
    traceView.show(error.payload?.trace);
  } finally {
    $("calculate").disabled = false;
    if (revision === request) {
      showNotice();
      $("calculator").dispatchEvent(new Event("lab:calculation-result", { bubbles: true }));
    }
  }
}

async function copyText(text, feedback, notice = $("notice")) {
  try {
    await navigator.clipboard.writeText(text);
    notice.textContent = feedback;
  } catch {
    window.prompt("Copy this value", text);
  }
}

function makeShareURL() {
  const url = new URL(location.pathname, location.origin);
  const query = {m: activeDegree(), operation: activeOperation(), base, poly_a: readOperand("a").toString(16)};
  if (operandInput("b").value.trim()) {
    try {
      query.poly_b = readOperand("b").toString(16);
    } catch (error) {
      if (!unary()) throw error;
    }
  } else if (!unary()) {
    readOperand("b");
  }
  url.search = new URLSearchParams(query);
  return url.href;
}

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
    operandInput(key).value = hex === null ? "" : formatOperand(parseOperand(hex, "hex"), base, degree);
  }
}

function configDefaults() {
  $("field").value = "163";
  base = "hex";
  selectOperation("multiply");
  operandInput("a").value = "57";
  operandInput("b").value = "83";
}

function presetButton(preset) {
  const inverse = preset.operation === "inverse";
  const button = element("button", inverse ? "Chapter 5 · AES inverse" : "Chapter 4 · GF(2⁸)", "preset");
  button.append(element("small", inverse ? "{95}⁻¹ = {8A}" : "{57} × {83} = {C1}"));
  button.addEventListener("click", () => {
    $("field").value = preset.m;
    selectOperation(preset.operation);
    for (const key of operands) {
      operandInput(key).value = preset[key] ? formatOperand(parseOperand(preset[key], preset.input_base), base, preset.m) : "";
    }
    renderField();
    renderOperands();
    if ($("tutorial").open) $("tutorial").close();
    calculate({ reveal: true });
  });
  return button;
}

function renderSlide() {
  const slide = slides[slideIndex];
  const list = element("ul");
  for (const point of slide.key_points) list.append(element("li", point));
  const title = element("h2", slide.title);
  title.id = "slide-title";
  $("tutorial-slide").replaceChildren(title, element("p", slide.body), list,
    ...(slide.presets || []).map(presetButton));
  $("slide-count").textContent = (slideIndex + 1) + " / " + slides.length;
  $("slide-prev").disabled = slideIndex === 0;
  $("slide-next").textContent = slideIndex === slides.length - 1 ? "Done" : "Next";
}

function loadPair(index) {
  const pair = uploadPairs[index];
  clearCalculation();
  for (const key of operands) {
    const pairBase = pair.base === "bin" ? "binary" : pair.base;
    operandInput(key).value = pair[key] ? formatOperand(parseOperand(pair[key], pairBase), base, activeDegree()) : "";
  }
  renderOperands();
}

$("calculator").addEventListener("submit", event => { event.preventDefault(); calculate({ reveal: true }); });
$("field").addEventListener("change", () => { clearCalculation(); renderField(); renderOperands(); });
for (const input of document.querySelectorAll("input[name=operation], #poly-a, #poly-b")) {
  input.addEventListener("input", () => { clearCalculation(); renderOperands(); });
}
for (const button of document.querySelectorAll("[data-base]")) {
  button.addEventListener("click", () => changeNotation(button.dataset.base));
}
$("share").addEventListener("click", () => {
  try { copyText(makeShareURL(), "Calculation link copied."); }
  catch (error) { showError(error.message); }
});
$("copy-result").addEventListener("click", () => copyText(display(result.result, base), "Result copied.", $("result-notice")));
$("back-to-inputs").addEventListener("click", () => operandInput("a").focus());
$("result-expanded").addEventListener("click", () => {
  showFullResult = !showFullResult;
  renderResult();
});
$("export").addEventListener("click", async () => {
  const format = $("export-format").value;
  try {
    const blob = await api("export-calculation", {calculation: result, format, download: true}, true);
    const url = URL.createObjectURL(blob);
    const link = element("a");
    link.href = url;
    link.download = "gf2m-calculation." + format;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  } catch (error) { showError(error.message); }
});
$("random").addEventListener("click", async () => {
  const savedRevision = revision;
  try {
    const pair = await api("random-polynomials", {m: activeDegree(), density: $("density").value});
    if (savedRevision !== revision) return;
    clearCalculation();
    for (const key of operands) operandInput(key).value = display(pair[key], base);
    renderOperands();
    showNotice("Random operands generated.");
  } catch (error) { showError(error.message); }
});
$("upload").addEventListener("click", () => $("file").click());
$("file").addEventListener("change", async () => {
  const file = $("file").files[0];
  if (!file) return;
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
    showNotice(parsed.count + (parsed.count === 1 ? " pair loaded." : " pairs loaded."));
  } catch (error) { showError(error.message); }
  finally { $("file").value = ""; }
});
$("pairs").addEventListener("change", () => {
  try { loadPair(Number($("pairs").value)); }
  catch (error) { showError(error.message); }
});
const loadExperimentFields = setupExplorations(api, {
  closeTour: setupPageTour(),
  currentField: () => fields.get(activeDegree()),
  currentOperands: () => ({
    m: activeDegree(), a: readOperand("a").toString(16), b: readOperand("b").toString(16),
  }),
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
    if (invalidLink) showError(invalidLink);
    else await calculate();
  } catch (error) { showError(error.message); }
}

init();
