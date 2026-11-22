/**
 * @fileoverview Interactive trace visualizers and step-playback controller for GF(2^m) algorithms.
 *
 * Original Author: Ali Zahreddine — Milestone 4 & Integration (Educational Web GUI).
 *
 * Renders all four course-aligned visualizers plus generic exploration tables:
 *   1. Bitwise XOR table (Add / Subtract — Stallings Ch. 4)
 *   2. Modulo reduction shift-and-XOR steps (Stallings Ch. 4 & 5)
 *   3. Shift-and-XOR multiplication Tables 1 & 2 with linked interactive multiplier-bit
 *      highlighting and keyboard arrow navigation (Stallings Ch. 4 & 5)
 *   4. Extended Euclidean Algorithm Table 4.7 with Hex/Binary/Algebraic cell switcher
 *      and B3(x) = 1 vs. B3(x) = 0 termination messaging (Stallings Ch. 4 & 5)
 *   5. Combined two-stage division trace (Stage 1 Table 4.7 + Stage 2 Shift-and-XOR)
 *
 * Supports desktop full-table view, narrow-screen single-step cards, and animated playback
 * (`Previous step`, `Next step`, `Play animation`, `Show all`, `Show step cards`/`Show tables`).
 */

import { element, significantDigits } from "./notation.js";

/**
 * Build an accessible, horizontally scrollable trace table inside a labelled region.
 *
 * @param {string} title - Section heading and ARIA region label.
 * @param {Array<string | number>} headers - Column header labels.
 * @param {Array<Array<string | number>>} rows - Matrix of cell text values.
 * @param {(row: number, col: number) => boolean} [selected] - Predicate highlighting key cells (`.picked`).
 * @returns {HTMLElement} Populated `<section>` containing the table or empty notice.
 */
export function table(title, headers, rows, selected = () => false) {
  const section = element("section");
  section.append(element("h3", title));
  if (!rows.length) {
    section.append(element("p", "There are no rows for this calculation."));
    return section;
  }
  const wrapper = element("div", undefined, "trace-table");
  wrapper.tabIndex = 0;
  wrapper.setAttribute("role", "region");
  wrapper.setAttribute("aria-label", title);
  const grid = element("table");
  const heading = grid.createTHead().insertRow();
  for (const label of headers) {
    const cell = element("th", label);
    cell.scope = "col";
    heading.append(cell);
  }
  const body = grid.createTBody();
  rows.forEach((values, row) => {
    const line = body.insertRow();
    values.forEach((value, col) => {
      const cell = line.insertCell();
      cell.textContent = value;
      if (selected(row, col)) cell.classList.add("picked");
    });
  });
  wrapper.append(grid);
  section.append(wrapper);
  return section;
}

/**
 * Render one labelled key-value step card for narrow viewports or compact step-by-step mode.
 *
 * @param {string} title - Card heading (e.g. `"Multiplier bit 7"`).
 * @param {string[]} labels - Term labels for the `<dl>` list.
 * @param {Array<string | number>} values - Corresponding values aligned with `labels`.
 * @returns {HTMLElement} Compact step-card `<section>` with `role="region"`.
 */
function stepCard(title, labels, values) {
  const card = element("section", undefined, "trace-card");
  card.setAttribute("role", "region");
  card.setAttribute("aria-label", "Current trace step");
  const details = element("dl", undefined, "equivalents");
  labels.forEach((label, index) => details.append(element("dt", label), element("dd", values[index])));
  card.append(element("h3", title), details);
  return card;
}

/**
 * Render modulo reduction steps (`MOD_REDUCE`) as either a compact step card or full table.
 *
 * @param {object} trace - Backend `mod_reduce` trace dictionary.
 * @param {number} limit - Number of steps currently revealed (`Infinity` for all).
 * @param {string} [heading="Modulo reduction"] - Section heading text.
 * @param {boolean} [compact=false] - Whether to render a single labelled step card.
 * @returns {HTMLElement} Rendered modulo reduction section.
 */
function reduction(trace, limit, heading = "Modulo reduction", compact = false) {
  const labels = ["Highest degree", "Shift", "Before (hex)", "Shifted modulus (hex)", "After XOR (hex)"];
  const hex = text => (compact && trace.m_degree > 8 ? significantDigits(text) : text).toUpperCase();
  const cells = row => [row.target_degree, row.shift, hex(row.before_hex), hex(row.reducer_hex), hex(row.after_hex)];
  const section = compact && trace.steps.length
    ? stepCard(heading + " · step " + limit, labels, cells(trace.steps[limit - 1]))
    : table(heading, labels, trace.steps.slice(0, limit).map(cells));
  section.insertBefore(element("p", trace.was_reduced
    ? "Shift the modulus so its leading term aligns with the remainder, then XOR to cancel that term."
    : "The input already has degree below m. No reduction is needed."), section.children[1] || null);
  return section;
}

/**
 * Render bitwise XOR addition/subtraction trace columns aligned by power of `x`.
 *
 * @param {object} trace - Backend `bitwise-xor` trace object (`columns: [{exp, a, b, xor}]`).
 * @param {number} limit - Number of bit columns revealed (`Infinity` for all).
 * @param {boolean} compact - Render one exponent step card when `true`.
 * @returns {HTMLElement} Rendered XOR table or step card.
 */
function xor(trace, limit, compact) {
  if (compact) {
    const bit = trace.columns[limit - 1];
    return stepCard("Bitwise XOR · x^" + bit.exp, ["Bit of A", "Bit of B", "A ⊕ B"], [bit.a, bit.b, bit.xor]);
  }
  const columns = trace.columns.slice(0, limit);
  return table("Bitwise XOR", ["Power of x", ...columns.map(bit => bit.exp)], [
    ["A", ...columns.map(bit => bit.a)],
    ["B", ...columns.map(bit => bit.b)],
    ["A ⊕ B", ...columns.map(bit => bit.xor)],
  ], row => row === 2);
}

/**
 * Render the Shift-and-XOR multiplication visualizer with linked multiplier-bit buttons.
 *
 * Clicking or navigating a bit button with Left/Right/Home/End highlights its matching
 * row in Table 1 (`x^i * A mod m`) and, when the bit is `1`, its matching partial-product
 * row in Table 2, while displaying the live running XOR equation.
 *
 * @param {object} trace - Backend `shift-and-xor` trace dictionary.
 * @param {number} limit - Number of steps revealed in tables.
 * @param {number} current - Currently focused multiplier-bit step index.
 * @param {boolean} compact - Render one labelled step card instead of both tables.
 * @param {(index: number) => void} chooseBit - Callback invoked when the user selects a bit.
 * @returns {HTMLElement} Populated multiplication visualizer `<section>`.
 */
function multiply(trace, limit, current, compact, chooseBit) {
  const section = element("section");
  if (!trace.steps.length) {
    section.append(element("p", "The multiplier is zero. There are no partial products to add."));
    return section;
  }
  const active = trace.steps[current];
  const bits = element("div", undefined, "multiplier-bits");
  bits.setAttribute("role", "group");
  bits.setAttribute("aria-label", "Multiplier bits");
  for (const [index, step] of trace.steps.entries()) {
    const button = element("button", undefined, "multiplier-bit");
    button.type = "button";
    button.append(element("small", step.i), element("span", step.multiplier_bit));
    button.setAttribute("aria-label", "Multiplier bit " + step.i);
    button.setAttribute("aria-description", "Value " + step.multiplier_bit);
    button.setAttribute("aria-pressed", index === current);
    // Roving tabindex keeps keyboard navigation smooth across 163..571 multiplier bits.
    button.tabIndex = index === current ? 0 : -1;
    button.addEventListener("click", () => chooseBit(index));
    bits.append(button);
  }
  bits.addEventListener("keydown", event => {
    const positions = {ArrowLeft: current - 1, ArrowRight: current + 1, Home: 0, End: trace.steps.length - 1};
    if (!Object.hasOwn(positions, event.key)) return;
    event.preventDefault();
    chooseBit(Math.max(0, Math.min(positions[event.key], trace.steps.length - 1)));
  });
  section.append(element("h3", "Multiplier bits · low to high"), bits);
  const shortHex = text => significantDigits(text).toUpperCase();
  const prior = shortHex(trace.steps[current - 1]?.accumulator_hex ?? "0");
  const partial = shortHex(active.partial_hex);
  const total = shortHex(active.accumulator_hex);
  const equation = element("p", active.added ? prior + " ⊕ " + partial + " = " + total : "Running XOR stays " + total,
    "bit-equation");
  if (compact) {
    const card = stepCard("Multiplier bit " + active.i, ["Bit of B", "Shifted operand A (hex)", "Reduced?", "Running XOR (hex)"],
      [active.multiplier_bit, partial, active.reduced ? "Yes" : "No", total]);
    card.append(equation);
    section.append(card);
    return section;
  }

  const steps = trace.steps.slice(0, limit);
  const selected = steps.filter(step => step.added);
  const shiftTable = table("Table 1 · Shifts and reductions", ["i", "xⁱ A mod m (hex)", "Reduced?", "Polynomial"],
    steps.map(step => [step.i, step.partial_hex.toUpperCase(), step.reduced ? "Yes" : "No", step.partial_poly]));
  const partialTable = table("Table 2 · Selected partial products", ["i", "Bit of B", "Partial product (hex)", "Cumulative XOR (hex)"],
    selected.map(step => [step.i, step.multiplier_bit, step.partial_hex.toUpperCase(), step.accumulator_hex.toUpperCase()]),
    (_, col) => col === 3);
  // Link the active multiplier bit to its corresponding rows in Table 1 and Table 2.
  shiftTable.querySelector("tbody").rows[current].setAttribute("aria-current", "true");
  partialTable.querySelector("tbody")?.rows[selected.indexOf(active)]?.setAttribute("aria-current", "true");
  section.append(element("p", "Bit " + active.i + " is " + active.multiplier_bit + ". " + (active.added
    ? "XOR its shifted value into the running result." : "Skip its shifted value.")), equation, shiftTable, partialTable);
  return section;
}

/**
 * Render the Stallings Chapter 4 Table 4.7 Extended Euclid trace.
 *
 * Highlights `B2(x)` (column 6) on the final row when `B3(x) == 1` (inverse found),
 * or `A3(x)` (column 4) when `B3(x) == 0` (no inverse; `A3(x) = gcd(m(x), b(x))`).
 *
 * @param {object} trace - Backend `extended_euclid_table_4_7` trace dictionary.
 * @param {number} limit - Number of Table 4.7 rows revealed.
 * @param {"hex" | "bin" | "algebraic"} notation - Active Table 4.7 cell notation.
 * @param {boolean} compact - Render one labelled step card when `true`.
 * @returns {HTMLElement} Rendered Table 4.7 section with termination note.
 */
function euclid(trace, limit, notation, compact) {
  const terms = ["Q", "A1", "A2", "A3", "B1", "B2", "B3"];
  const rows = trace.table_4_7_rows;
  const termination = trace.termination;
  const success = termination.b3_final === 1;
  const labels = terms.map(term => term + "(x)");
  const cells = row => terms.map(term => {
    let text = row.cells[term][notation];
    if (compact && trace.m_degree > 8 && notation !== "algebraic") text = significantDigits(text);
    return notation === "hex" ? text.toUpperCase() : text;
  });
  const tableView = compact
    ? stepCard("Extended Euclid · step " + rows[limit - 1].step, labels, cells(rows[limit - 1]))
    : table("Table 4.7 · Extended Euclid", ["Step", ...labels], rows.slice(0, limit).map(row => [row.step, ...cells(row)]),
      (row, col) => row === rows.length - 1 && (success ? col === 6 : col === 4));
  if (limit >= rows.length) {
    const ending = success
      ? "B3(x) = 1, so B2(x) gives the inverse."
      : "B3(x) = 0. No inverse exists. A3(x) gives the gcd: " + termination.gcd_formatted.algebraic + ".";
    tableView.append(element("p", ending));
  }
  return tableView;
}

/**
 * Create a stateful trace viewer bound to a panel, body container, and toolbar container.
 *
 * Manages step progression, 450 ms animated playback, Table 4.7 notation switching,
 * responsive mobile step-card switching (`max-width: 600px`), and linked scrolling.
 *
 * @param {HTMLElement} panel - Outer `<section>` toggled hidden when no trace is active.
 * @param {HTMLElement} body - Container where trace tables or step cards are rendered.
 * @param {HTMLElement} tools - Toolbar container populated with stepper and notation controls.
 * @returns {{show: (newTrace: object | null, newReductions?: object | null) => void}} Controller API.
 */
export function createTraceView(panel, body, tools) {
  const narrowScreen = window.matchMedia("(max-width: 600px)");
  let timer;
  let trace;
  let reductions;
  let notation = "hex";
  let current = null;
  let compact = false;
  let allRows = true;
  let stepLabel;
  let modeButton;
  let showAllButton;
  const stop = () => clearInterval(timer);

  /**
   * Compute total number of navigable steps for the currently loaded trace.
   * @returns {number} Step count (0 when trace is absent or empty).
   */
  function length() {
    if (trace?.trace_type === "gf2m_division_two_stage") {
      return trace.stage_1_inverse.table_4_7_rows.length + trace.stage_2_multiply.steps.length;
    }
    return trace?.table_4_7_rows?.length ?? trace?.columns?.length ?? trace?.steps?.length ?? trace?.rows?.length ?? 0;
  }

  /**
   * Rebuild the trace DOM for the active `trace`, `current` step, `compact` mode, and `notation`.
   */
  function renderBody() {
    body.replaceChildren();
    if (!trace) return;
    const limit = allRows ? Infinity : current + 1;
    // Show collapsible initial-reduction details whenever operands had degree >= m.
    if (reductions && trace.trace_type !== "mod_reduce") {
      for (const [key, row] of Object.entries(reductions)) {
        const details = element("details");
        details.append(element("summary", "Operand " + key.toUpperCase() + " was reduced first"), reduction(row, Infinity, "Initial reduction"));
        body.append(details);
      }
    }
    if (trace.trace_type === "tabular_steps") {
      const view = compact && trace.rows.length
        ? stepCard(trace.title + " · step " + limit, trace.headers, trace.rows[limit - 1])
        : table(trace.title, trace.headers, trace.rows.slice(0, limit), trace.selected);
      body.append(view);
    }
    if (trace.trace_type === "mod_reduce") body.append(reduction(trace, limit, "Modulo reduction", compact));
    if (trace.algorithm === "bitwise-xor") {
      body.append(element("p", "Add or subtract each pair of bits modulo 2. Two ones cancel."), xor(trace, limit, compact));
    }
    if (trace.algorithm === "shift-and-xor") body.append(multiply(trace, limit, current ?? 0, compact, selectBit));
    if (trace.trace_type === "extended_euclid_table_4_7") body.append(euclid(trace, limit, notation, compact));
    if (trace.trace_type === "gf2m_division_two_stage") {
      // Division combines Stage 1 (Table 4.7 inverse) and Stage 2 (Shift-and-XOR product).
      const inverse = trace.stage_1_inverse;
      const inverseSteps = inverse.table_4_7_rows.length;
      const remaining = limit - inverseSteps;
      if (!compact || remaining <= 0) body.append(euclid(inverse, limit, notation, compact));
      if (remaining > 0) {
        const local = Math.max(0, (current ?? 0) - inverseSteps);
        body.append(multiply(trace.stage_2_multiply, remaining, local, compact, step => selectBit(inverseSteps + step)));
      }
    }
  }

  /**
   * Keep the selected multiplier-bit chip and highlighted table rows scrolled into view.
   *
   * @param {number} previousLeft - Previous horizontal scroll offset of `.multiplier-bits`.
   * @returns {HTMLElement | undefined} Currently pressed multiplier-bit button, if present.
   */
  function revealLinkedSelection(previousLeft) {
    const bits = body.querySelector(".multiplier-bits");
    if (!bits) return;
    const selected = bits.querySelector('[aria-pressed="true"]');
    bits.scrollLeft = previousLeft;
    const bit = selected.getBoundingClientRect();
    const strip = bits.getBoundingClientRect();
    if (bit.left < strip.left) bits.scrollLeft += bit.left - strip.left;
    else if (bit.right > strip.right) bits.scrollLeft += Math.ceil(bit.right - strip.right);

    for (const row of body.querySelectorAll('.trace-table tr[aria-current="true"]')) {
      const wrapper = row.closest(".trace-table");
      const bounds = row.getBoundingClientRect();
      const top = wrapper.getBoundingClientRect().top;
      const visibleTop = top + wrapper.querySelector("thead").offsetHeight;
      const visibleBottom = top + wrapper.clientHeight;
      if (bounds.top < visibleTop) wrapper.scrollTop += bounds.top - visibleTop;
      else if (bounds.bottom > visibleBottom) wrapper.scrollTop += bounds.bottom - visibleBottom;
    }
    return selected;
  }

  /**
   * Update toolbar labels, re-render trace DOM, and scroll linked selections into view.
   * @returns {HTMLElement | undefined} Active multiplier-bit button, if rendered.
   */
  function render() {
    const previousLeft = body.querySelector(".multiplier-bits")?.scrollLeft ?? 0;
    if (stepLabel) {
      stepLabel.textContent = allRows ? "All steps" : "Step " + (current + 1) + " of " + length();
      modeButton.textContent = compact ? "Show tables" : "Show step cards";
      showAllButton.hidden = compact;
    }
    renderBody();
    return revealLinkedSelection(previousLeft);
  }

  /**
   * Jump to a specific multiplier-bit index and preserve keyboard focus on its button.
   * @param {number} step - Zero-based step index.
   */
  function selectBit(step) {
    stop();
    current = step;
    render().focus({ preventScroll: true });
  }

  /**
   * Toggle between single-step card mode (`cards = true`) and full table view (`cards = false`).
   * @param {boolean} cards - Whether to enable compact step-card layout.
   */
  function switchMode(cards) {
    stop();
    compact = cards;
    allRows = !cards;
    if (cards && current === null) current = 0;
    render();
  }

  narrowScreen.addEventListener("change", event => {
    if (trace && length()) switchMode(event.matches);
  });

  /**
   * Load a new trace payload into the viewer and rebuild toolbar controls.
   *
   * @param {object | null} newTrace - Trace dictionary from the API, or `null` to hide panel.
   * @param {object | null} [newReductions] - Optional map of pre-reduced operands `{a?, b?}`.
   */
  function show(newTrace, newReductions) {
    stop();
    trace = newTrace;
    reductions = newReductions;
    compact = narrowScreen.matches && length() > 0;
    allRows = !compact;
    current = compact ? 0 : null;
    panel.hidden = !trace;
    tools.replaceChildren();
    stepLabel = modeButton = showAllButton = undefined;
    if (!trace) { renderBody(); return; }
    // Attach Hex/Binary/Algebraic notation switcher whenever Table 4.7 is shown.
    if (trace.table_4_7_rows || trace.stage_1_inverse) {
      const select = element("select");
      select.setAttribute("aria-label", "Euclid cell notation");
      for (const [value, title] of [["hex", "Hexadecimal"], ["bin", "Binary"], ["algebraic", "Algebraic"]]) {
        const option = element("option", title);
        option.value = value;
        select.append(option);
      }
      select.value = notation;
      select.addEventListener("change", () => {
        notation = select.value;
        render();
      });
      tools.append(select);
    }
    const count = length();
    if (!count) { renderBody(); return; }
    stepLabel = element("span", undefined, "trace-progress");
    stepLabel.setAttribute("aria-live", "polite");
    function advance(next) {
      current = Math.max(0, Math.min(count - 1, next));
      allRows = false;
      render();
    }
    const controls = [
      ["Previous step", () => advance((current ?? count - 1) - 1)],
      ["Next step", () => advance((current ?? -1) + 1)],
      ["Play animation", () => {
        advance(0);
        timer = setInterval(() => {
          if (current === count - 1) stop();
          else advance(current + 1);
        }, 450);
      }],
    ];
    for (const [title, action] of controls) {
      const button = element("button", title, "quiet");
      button.addEventListener("click", () => { stop(); action(); });
      tools.append(button);
    }
    showAllButton = element("button", "Show all", "quiet");
    showAllButton.addEventListener("click", () => switchMode(false));
    modeButton = element("button", undefined, "outline");
    modeButton.addEventListener("click", () => switchMode(!compact));
    tools.append(showAllButton, modeButton, stepLabel);
    render();
  }

  return { show };
}
