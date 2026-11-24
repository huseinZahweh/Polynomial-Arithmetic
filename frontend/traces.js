/**
 * @fileoverview Interactive trace visualizers, previous-to-current visual diff tracking,
 * informative educational step titles, sequential step cascade, auto-maximized grid,
 * and step-playback controller for GF(2^m) algorithms.
 *
 * Original Author: Ali Zahreddine - Milestone 4, Integration & Milestone 6 (Waves 1-4).
 *
 * Renders all course-aligned visualizers plus generic exploration tables across three layout modes
 * (`Step view`, `All steps grid` with auto-maximize, `Classic table`), an optional side-by-side
 * `Compare prev → curr` comparison mode, and an expandable full-viewport modal:
 *   1. Bitwise XOR visualizer (Add / Subtract - Stallings Ch. 4) with `1 ⊕ 1 → 0` cancellation highlights
 *   2. Modulo reduction shift-and-XOR steps (Stallings Ch. 4 & 5) with leading-term elimination diffs
 *   3. Shift-and-XOR multiplication Tables 1 & 2 with linked interactive multiplier-bit highlighting,
 *      sequential step cascade, instant `First changed bit` jump, `prev → now` shift/reduction and accumulator deltas, and arrow keys
 *   4. Extended Euclidean Algorithm Table 4.7 with zero-horizontal-scroll Step Inspector Square
 *      (Triple A carried ← prev B, Triple B updated New T, inline `was:` values, recurrence callout),
 *      true `<sup>`/`<sub>` typography, Hex/Binary/Polynomial cell switcher, Compact values / Full m-bit
 *      toggle, and B3(x) = 1 vs. 0 termination badges
 *   5. Combined two-stage division trace (Stage 1 Table 4.7 + Stage 2 Shift-and-XOR)
 */

import {
  appendMathText,
  attachSlidingIndicator,
  copyToClipboard,
  element,
  mathElement,
  polynomial,
  setMathText,
  showFeedbackPopup,
  significantDigits,
} from "./notation.js";

const PLAY_SPEED_MS = { slow: 900, normal: 450, fast: 200 };
const CASCADE_STEP_MS = 95;
const MAX_CASCADE_HOPS = 12;

/**
 * Compute an informative one-line educational title for an Extended Euclid Table 4.7 step.
 *
 * @param {object} trace - Extended Euclid trace dictionary.
 * @param {number} rowIndex - Zero-based index into `table_4_7_rows`.
 * @param {string} [stagePrefix=""] - Optional stage prefix (e.g. for two-stage division).
 * @returns {string} Educational title describing the mathematical action of the step.
 */
function euclidKnowledgeTitle(trace, rowIndex, stagePrefix = "") {
  const rows = trace.table_4_7_rows;
  const row = rows[rowIndex];
  const isFinal = rowIndex === rows.length - 1;
  const success = trace.termination.b3_final === 1;
  if (isFinal && !success) {
    return stagePrefix + "Step " + row.step + ": Terminated (B3(x) = 0): No Inverse Exists; A3(x) = gcd(m(x), b(x))";
  }
  if (isFinal && success) {
    return stagePrefix + "Step " + row.step + ": Inverse Found: gcd(m(x), b(x)) = B3(x) = 1 → B2(x) is b^-1(x)";
  }
  if (row.step === 0) {
    return stagePrefix + "Step 0: Initialize Bézout Triples: A ← m(x), B ← b(x) mod m(x)";
  }
  const qPoly = row.cells.Q.algebraic;
  return stagePrefix + "Step " + row.step + ": Divide A3(x) by B3(x) (Q = " + qPoly + ") & Update Bézout Remainder T3(x)";
}

/**
 * Compute an informative one-line educational title for a Shift-and-XOR multiplication step.
 *
 * @param {object} step - Single Shift-and-XOR step entry.
 * @param {string} [stagePrefix=""] - Optional stage prefix (e.g. for two-stage division).
 * @returns {string} Educational title describing shift, overflow reduction, and accumulation.
 */
function multiplyKnowledgeTitle(step, stagePrefix = "") {
  if (step.i === 0) {
    return stagePrefix + "Step 1 (Bit b0): Initialize Shifted Term x^0·A(x) & Check Multiplier Bit b0";
  }
  const n = step.i + 1;
  const bitLabel = "Bit b_" + step.i + " = " + step.multiplier_bit;
  if (step.reduced && step.added) {
    return stagePrefix + "Step " + n + " (" + bitLabel + "): Shift Left (× x), Reduce Overflow x^m ⊕ m(x), & XOR into Sum";
  }
  if (step.reduced && !step.added) {
    return stagePrefix + "Step " + n + " (" + bitLabel + "): Shift Left (× x) & Reduce Overflow x^m ⊕ m(x) (Skip Sum)";
  }
  if (!step.reduced && step.added) {
    return stagePrefix + "Step " + n + " (" + bitLabel + "): Shift Left (× x, No Overflow) & XOR into Sum";
  }
  return stagePrefix + "Step " + n + " (" + bitLabel + "): Shift Left (× x, No Overflow) & Keep Sum Unchanged";
}

/**
 * Compute an informative educational title for a Modulo Reduction step.
 *
 * @param {object} row - Reduction step record `{target_degree, shift}`.
 * @param {number} idx - Zero-based step index.
 * @param {string} [stagePrefix=""] - Optional prefix.
 * @returns {string} Educational step title.
 */
function reductionKnowledgeTitle(row, idx, stagePrefix = "") {
  return stagePrefix + "Step " + (idx + 1) + ": Eliminate Leading Term x^" + row.target_degree +
    " by XORing m(x) · x^" + (row.shift > 0 ? row.shift : 0);
}

/**
 * Compute an informative educational title for a Bitwise XOR column step.
 *
 * @param {object} bit - Column record `{exp, a, b, xor}`.
 * @param {string} [stagePrefix=""] - Optional prefix.
 * @returns {string} Educational step title.
 */
function xorKnowledgeTitle(bit, stagePrefix = "") {
  const cancels = bit.a === 1 && bit.b === 1;
  return stagePrefix + "Column x^" + bit.exp + ": Compute a_" + bit.exp + " ⊕ b_" + bit.exp + " mod 2" +
    (cancels ? " (Cancel 1 ⊕ 1 → 0)" : bit.xor === 1 ? " (Keep x^" + bit.exp + ")" : " (Stays 0)");
}

/**
 * Build the shared, color-blind-safe visual diff legend bar used across Traces and Lessons.
 *
 * Every visual state pairs a WCAG AA tinted surface/border with an explicit text label:
 *   - `.diff-carried`: Indigo/Blue (Carried / Shifted)
 *   - `.diff-updated`: Emerald/Green (New / Updated)
 *   - `.diff-reduced`: Amber/Orange (Reduced / Cancelled)
 *   - `.diff-unchanged`: Neutral Muted (Unchanged)
 *
 * @returns {HTMLElement} Compact `.diff-legend` bar element.
 */
export function createDiffLegend() {
  const bar = element("div", undefined, "diff-legend");
  bar.setAttribute("role", "note");
  bar.setAttribute("aria-label", "Change highlight legend");
  bar.append(element("span", "Step diff:", "diff-legend-title"));
  for (const [cls, label] of [
    ["diff-carried", "Carried / Shifted"],
    ["diff-updated", "New / Updated"],
    ["diff-reduced", "Reduced / Cancelled"],
    ["diff-unchanged", "Unchanged"],
  ]) {
    bar.append(element("span", label, "diff-legend-item " + cls));
  }
  return bar;
}

/**
 * Format a trace value according to the active notation and `compactValues` toggle.
 *
 * When `compactValues` is enabled on large fields (`m > 8`), trims leading zero padding
 * for hex/binary values and summarizes middle terms of long algebraic polynomials.
 *
 * @param {string | number} rawValue - Raw cell string or number.
 * @param {"hex" | "bin" | "algebraic"} [notation="hex"] - Cell notation.
 * @param {boolean} [compactValues=false] - Whether compact large-field summarization is active.
 * @param {number} [mDegree=8] - Field degree `m`.
 * @returns {string} Formatted cell string.
 */
function formatCellText(rawValue, notation = "hex", compactValues = false, mDegree = 8) {
  const raw = String(rawValue ?? "");
  const formatted = notation === "hex" ? raw.toUpperCase() : raw;
  if (!compactValues || mDegree <= 8) return formatted;
  if (notation === "algebraic") {
    const terms = formatted.split(" + ");
    return terms.length > 4 ? terms.slice(0, 2).join(" + ") + " + … + " + terms.at(-1) : formatted;
  }
  const sig = significantDigits(formatted);
  return sig.length > 28 ? sig.slice(0, 14) + "…" + sig.slice(-8) : sig;
}

/**
 * Attach click-to-copy behavior and tooltip metadata to a trace value element.
 *
 * @param {HTMLElement} node - Clickable DOM element displaying a polynomial/hex/binary value.
 * @param {string} fullValue - Complete unshortened value to copy.
 */
function makeCopyableValue(node, fullValue) {
  node.title = "Click to copy full value: " + fullValue;
  node.dataset.fullValue = fullValue;
  node.classList.add("trace-copyable");
  node.addEventListener("click", async () => {
    const copied = await copyToClipboard(fullValue);
    if (copied) {
      node.classList.add("is-copied");
      showFeedbackPopup("Copied to clipboard", "Trace value copied to clipboard");
      setTimeout(() => node.classList.remove("is-copied"), 900);
    }
  });
}

/**
 * Build a styled diff value box (`<dd>`) with optional color-coded badge, math typography
 * on non-hex values, and inline `was:` / `prev:` sub-row.
 *
 * @param {string | number} displayValue - Primary text shown in the cell.
 * @param {object} [meta] - Optional diff metadata `{diffClass?, badge?, prevText?, fullValue?, extraClass?, isMathValue?}`.
 * @returns {HTMLElement} Populated `<dd>` element.
 */
function buildDiffValueNode(displayValue, meta = {}) {
  const dd = element("dd");
  const fullValue = String(meta.fullValue ?? displayValue);
  if (meta.diffClass || meta.badge || meta.prevText) {
    dd.className = "diff-cell-box" + (meta.diffClass ? " " + meta.diffClass : "") + (meta.extraClass ? " " + meta.extraClass : "");
    const head = element("div", undefined, "diff-cell-head");
    const valSpan = meta.isMathValue
      ? mathElement("span", displayValue, "diff-cell-val")
      : element("span", String(displayValue), "diff-cell-val");
    makeCopyableValue(valSpan, fullValue);
    head.append(valSpan);
    if (meta.badge) {
      head.append(mathElement("span", meta.badge, "diff-tag" + (meta.diffClass ? " " + meta.diffClass : "")));
    }
    dd.append(head);
    if (meta.prevText) {
      const prevNode = meta.isMathValue
        ? mathElement("span", meta.prevText, "diff-prev-value")
        : element("span", meta.prevText, "diff-prev-value");
      dd.append(prevNode);
    }
  } else {
    if (meta.isMathValue) setMathText(dd, displayValue);
    else dd.textContent = String(displayValue);
    if (meta.extraClass) dd.className = meta.extraClass;
    makeCopyableValue(dd, fullValue);
  }
  return dd;
}

/**
 * Build an accessible trace table inside a labelled region with smart cell wrapping,
 * true `<sup>`/`<sub>` headers and polynomial columns, and optional row/cell diff styling.
 *
 * @param {string} title - Section heading and ARIA region label.
 * @param {Array<string | number>} headers - Column header labels.
 * @param {Array<Array<string | number>>} rows - Matrix of cell text values.
 * @param {(row: number, col: number) => boolean} [selected] - Predicate highlighting key cells (`.picked`).
 * @param {{prevRow?: number, currRow?: number, cellClass?: (row: number, col: number) => string, mathCols?: Set<number>, subtitle?: string}} [diffOpts] - Optional decorators.
 * @returns {HTMLElement} Populated `<section>` containing the table or empty notice.
 */
export function table(title, headers, rows, selected = () => false, diffOpts = {}) {
  const section = element("section");
  section.append(mathElement("h3", title));
  if (diffOpts.subtitle) {
    section.append(mathElement("p", diffOpts.subtitle, "step-knowledge-title"));
  }
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
    const cell = mathElement("th", label);
    cell.scope = "col";
    heading.append(cell);
  }
  const body = grid.createTBody();
  rows.forEach((values, row) => {
    const line = body.insertRow();
    if (diffOpts.prevRow === row) line.classList.add("diff-prev-row");
    if (diffOpts.currRow === row) {
      line.classList.add("diff-curr-row");
      line.setAttribute("aria-current", "true");
    }
    values.forEach((value, col) => {
      const cell = line.insertCell();
      if (diffOpts.mathCols?.has(col)) setMathText(cell, value);
      else cell.textContent = value;
      if (selected(row, col)) cell.classList.add("picked");
      const extra = diffOpts.cellClass?.(row, col);
      if (extra) cell.classList.add(extra);
    });
  });
  wrapper.append(grid);
  section.append(wrapper);
  return section;
}

/**
 * Render one labelled key-value step card for `Step view` or `All steps grid`,
 * featuring a step eyebrow badge, prominent educational `.step-knowledge-title`,
 * step-change transition banner, and per-row visual diff badges.
 *
 * @param {string} eyebrow - Step identifier eyebrow (e.g. `"Multiplier bit 7"`).
 * @param {string} knowledgeTitle - Informative educational summary of what the step computes.
 * @param {string[]} labels - Term labels for the `<dl>` list.
 * @param {Array<string | number>} values - Corresponding values aligned with `labels`.
 * @param {boolean} [isCurrentRegion=true] - Attach `role="region"` and `aria-label="Current trace step"`.
 * @param {{banner?: string, cellMeta?: Array<object>, mathLabels?: boolean}} [options] - Optional decorators.
 * @returns {HTMLElement} Compact step-card `<section>`.
 */
function stepCard(eyebrow, knowledgeTitle, labels, values, isCurrentRegion = true, options = {}) {
  const card = element("section", undefined, "trace-card");
  if (isCurrentRegion) {
    card.setAttribute("role", "region");
    card.setAttribute("aria-label", "Current trace step");
  }
  card.append(mathElement("span", eyebrow, "step-eyebrow"));
  card.append(mathElement("h3", knowledgeTitle, "step-knowledge-title"));
  if (options.banner) {
    card.append(mathElement("p", options.banner, "diff-banner"));
  }
  const details = element("dl", undefined, "equivalents");
  labels.forEach((label, index) => {
    const dt = options.mathLabels === false ? element("dt", label) : mathElement("dt", label);
    details.append(dt, buildDiffValueNode(values[index], options.cellMeta?.[index]));
  });
  card.append(details);
  return card;
}

/**
 * Build one modulo reduction step card with leading-term elimination and after-XOR diff badges.
 *
 * @param {object} trace - Backend `mod_reduce` trace dictionary.
 * @param {number} idx - Zero-based reduction step index.
 * @param {string} heading - Section heading prefix.
 * @param {boolean} compactValues - Whether compact large-field summarization is enabled.
 * @param {boolean} isCurrentRegion - Attach `"Current trace step"` ARIA region label.
 * @param {string} [stagePrefix=""] - Optional stage prefix.
 * @returns {HTMLElement} Rendered modulo reduction step card.
 */
function reductionStepCard(trace, idx, heading, compactValues, isCurrentRegion, stagePrefix = "") {
  const labels = ["Highest degree", "Shift", "Before (hex)", "Shifted modulus (hex)", "After XOR (hex)"];
  const hex = text => formatCellText(text, "hex", compactValues, trace.m_degree);
  const row = trace.steps[idx];
  const beforeStr = hex(row.before_hex);
  const reducerStr = hex(row.reducer_hex);
  const afterStr = hex(row.after_hex);
  const banner = "Step " + (idx + 1) + ": Cancelled leading term x^" + row.target_degree +
    " using m(x) << " + row.shift + " → remainder {" + beforeStr + "} → {" + afterStr + "}.";
  const cellMeta = [
    { diffClass: "diff-reduced", badge: "Cancel x^" + row.target_degree },
    { diffClass: "diff-carried", badge: "m(x) << " + row.shift },
    { diffClass: "diff-reduced", badge: "Leading term cancelled", fullValue: row.before_hex.toUpperCase() },
    { diffClass: "diff-carried", badge: "Shifted modulus", fullValue: row.reducer_hex.toUpperCase() },
    { diffClass: "diff-updated", badge: "Reduced", prevText: "was: " + beforeStr, fullValue: row.after_hex.toUpperCase() },
  ];
  return stepCard(
    heading + " · step " + (idx + 1),
    reductionKnowledgeTitle(row, idx, stagePrefix),
    labels,
    [row.target_degree, row.shift, beforeStr, reducerStr, afterStr],
    isCurrentRegion,
    { banner, cellMeta },
  );
}

/**
 * Render modulo reduction steps (`MOD_REDUCE`) in `step`, `grid`, or `table` layout mode.
 *
 * @param {object} trace - Backend `mod_reduce` trace dictionary.
 * @param {number} limit - Number of steps currently revealed (`Infinity` for all).
 * @param {string} [heading="Modulo reduction"] - Section heading text.
 * @param {"step" | "grid" | "table"} [layoutMode="table"] - Active trace layout mode.
 * @param {boolean} [compactValues=false] - Whether to trim leading zero padding on large fields.
 * @param {number} [currentStep=0] - Active zero-based step index.
 * @param {boolean} [isCurrentRegion=true] - Whether the step card is the live `"Current trace step"` region.
 * @returns {HTMLElement} Rendered modulo reduction section.
 */
function reduction(trace, limit, heading = "Modulo reduction", layoutMode = "table", compactValues = false, currentStep = 0, isCurrentRegion = true) {
  const labels = ["Highest degree", "Shift", "Before (hex)", "Shifted modulus (hex)", "After XOR (hex)"];
  const hex = text => formatCellText(text, "hex", compactValues, trace.m_degree);
  const cells = row => [row.target_degree, row.shift, hex(row.before_hex), hex(row.reducer_hex), hex(row.after_hex)];

  let section;
  if (layoutMode === "step" && trace.steps.length) {
    const idx = Math.max(0, Math.min(trace.steps.length - 1, limit === Infinity ? currentStep : limit - 1));
    section = reductionStepCard(trace, idx, heading, compactValues, isCurrentRegion);
  } else if (layoutMode === "grid" && trace.steps.length) {
    section = element("section");
    section.append(element("h3", heading));
    const grid = element("div", undefined, "trace-grid-cards");
    trace.steps.slice(0, limit).forEach((_, idx) => {
      const card = reductionStepCard(trace, idx, heading, compactValues, idx === currentStep && isCurrentRegion);
      if (idx === currentStep) card.classList.add("is-current");
      if (idx === currentStep - 1) card.classList.add("diff-prev-card");
      grid.append(card);
    });
    section.append(grid);
  } else {
    const rows = trace.steps.slice(0, limit);
    const activeRow = rows[Math.max(0, Math.min(rows.length - 1, currentStep))];
    section = table(
      heading,
      labels,
      rows.map(cells),
      () => false,
      {
        prevRow: limit !== Infinity && currentStep > 0 ? currentStep - 1 : -1,
        currRow: limit !== Infinity ? currentStep : -1,
        cellClass: (r, c) => (c === 2 ? "diff-reduced" : c === 3 ? "diff-carried" : c === 4 ? "diff-updated" : ""),
        subtitle: activeRow
          ? reductionKnowledgeTitle(activeRow, Math.max(0, Math.min(rows.length - 1, currentStep)))
          : "No reduction needed: degree is already below m",
      },
    );
  }
  section.insertBefore(mathElement("p", trace.was_reduced
    ? "Shift the modulus so its leading term aligns with the remainder, then XOR to cancel that term."
    : "The input already has degree below m. No reduction is needed."), section.children[1] || null);
  return section;
}

/**
 * Build one bitwise XOR step card with cancellation (`1 ⊕ 1 → 0`) and set-bit (`1`) badges.
 *
 * @param {object} trace - Backend `bitwise-xor` trace object.
 * @param {number} idx - Zero-based column index.
 * @param {boolean} isCurrentRegion - Attach `"Current trace step"` ARIA region label.
 * @returns {HTMLElement} Rendered bitwise XOR step card.
 */
function xorStepCard(trace, idx, isCurrentRegion) {
  const bit = trace.columns[idx];
  const cancels = bit.a === 1 && bit.b === 1;
  const xorDiff = cancels
    ? { diffClass: "diff-reduced", badge: "1 ⊕ 1 → 0 (Cancelled)" }
    : bit.xor === 1
      ? { diffClass: "diff-updated", badge: "Set to 1" }
      : { diffClass: "diff-unchanged", badge: "Unchanged (0)" };
  const banner = "Column x^" + bit.exp + ": " + bit.a + " ⊕ " + bit.b + " = " + bit.xor +
    (cancels ? ", matching 1s cancel in GF(2)." : bit.xor === 1 ? ", term survives in result." : ", remains 0.");
  return stepCard(
    "Bitwise XOR · x^" + bit.exp,
    xorKnowledgeTitle(bit),
    ["Bit of A", "Bit of B", "A ⊕ B"],
    [bit.a, bit.b, bit.xor],
    isCurrentRegion,
    {
      banner,
      cellMeta: [
        { diffClass: bit.a ? "diff-carried" : "diff-unchanged" },
        { diffClass: bit.b ? "diff-carried" : "diff-unchanged" },
        xorDiff,
      ],
    },
  );
}

/**
 * Render bitwise XOR addition/subtraction trace columns aligned by power of `x`.
 *
 * @param {object} trace - Backend `bitwise-xor` trace object (`columns: [{exp, a, b, xor}]`).
 * @param {number} limit - Number of bit columns revealed (`Infinity` for all).
 * @param {"step" | "grid" | "table"} layoutMode - Active layout mode.
 * @param {number} currentStep - Zero-based active step index.
 * @param {boolean} [isCurrentRegion=true] - Attach `"Current trace step"` ARIA region label.
 * @returns {HTMLElement} Rendered XOR table, grid, or step card.
 */
function xor(trace, limit, layoutMode, currentStep = 0, isCurrentRegion = true) {
  if (layoutMode === "step" && trace.columns.length) {
    const idx = Math.max(0, Math.min(trace.columns.length - 1, limit === Infinity ? currentStep : limit - 1));
    return xorStepCard(trace, idx, isCurrentRegion);
  }
  if (layoutMode === "grid" && trace.columns.length) {
    const section = element("section");
    section.append(element("h3", "Bitwise XOR"));
    const grid = element("div", undefined, "trace-grid-cards");
    trace.columns.slice(0, limit).forEach((_, idx) => {
      const card = xorStepCard(trace, idx, idx === currentStep && isCurrentRegion);
      if (idx === currentStep) card.classList.add("is-current");
      if (idx === currentStep - 1) card.classList.add("diff-prev-card");
      grid.append(card);
    });
    section.append(grid);
    return section;
  }
  const columns = trace.columns.slice(0, limit);
  return table(
    "Bitwise XOR",
    ["Power of x", ...columns.map(bit => bit.exp)],
    [
      ["A", ...columns.map(bit => bit.a)],
      ["B", ...columns.map(bit => bit.b)],
      ["A ⊕ B", ...columns.map(bit => bit.xor)],
    ],
    row => row === 2,
    {
      subtitle: "Bitwise Modulo-2 Addition (XOR): Cancel Matching 1 ⊕ 1 Terms Without Carries",
      cellClass: (r, c) => {
        if (r !== 2 || c === 0) return "";
        const col = columns[c - 1];
        if (!col) return "";
        if (col.a === 1 && col.b === 1) return "diff-reduced";
        return col.xor === 1 ? "diff-updated" : "diff-unchanged";
      },
    },
  );
}

/**
 * Format the explicit shift-and-XOR reduction calculation (`FORMAT_STEP_REDUCTION_BREAKDOWN`)
 * for a Shift-and-XOR multiplication step using Stallings' identity `x^m mod m(x) = m(x) - x^m`.
 *
 * - For `stepIndex === 0`: explains that `x^0 * A(x)` requires no shift yet.
 * - When `!wasReduced`: shows the left shift (`<< 1`) and notes no `x^m` overflow occurred.
 * - When `wasReduced` and `mDegree <= 16`: returns a 3-line aligned binary XOR breakdown
 *   (`shifted_bin`, `mod_bin`, `result_bin` + `{hex}`).
 * - When `wasReduced` and `mDegree > 16`: returns a 3-line compact sparse-tap breakdown
 *   showing `low_shifted`, `polynomial(low_mod)` lower `m(x)` taps, and `{reduced_hex}`.
 *
 * @param {bigint} prevVal - Previous step's partial value (`x^(i-1) * A(x) mod m(x)`).
 * @param {bigint} currVal - Current step's partial value (`x^i * A(x) mod m(x)`).
 * @param {bigint} modPoly - Irreducible modulus `m(x)` bitmask with bit `mDegree` set.
 * @param {number} mDegree - Extension field degree `m`.
 * @param {number} stepIndex - Zero-based step index `i`.
 * @param {boolean} wasReduced - True when `prevVal << 1n` overflowed bit `mDegree`.
 * @returns {{lines: string[], isOverflow: boolean}} Formatted lines ready for `appendMathText`.
 */
export function formatStepReductionBreakdown(prevVal, currVal, modPoly, mDegree, stepIndex, wasReduced) {
  const toHex = val => val.toString(16).toUpperCase();
  const compactHex = val => formatCellText(val.toString(16), "hex", true, mDegree);
  const toPaddedBin = (val, width) => val.toString(2).padStart(width, "0");

  if (stepIndex === 0) {
    const initHex = mDegree <= 16 ? toHex(currVal) : compactHex(currVal);
    return {
      lines: ["Initial term (x^0 · A(x)): {" + initHex + "} (no shift yet)"],
      isOverflow: false,
    };
  }

  const unreducedShift = prevVal << 1n;
  if (!wasReduced) {
    if (mDegree <= 16) {
      return {
        lines: [
          "Shift left (× x): " + toPaddedBin(prevVal, mDegree) + " << 1 = " +
            toPaddedBin(currVal, mDegree) + " ({" + toHex(currVal) + "}, no x^" + mDegree + " overflow)",
        ],
        isOverflow: false,
      };
    }
    return {
      lines: [
        "Shift left (× x): {" + compactHex(prevVal) + "} << 1 = {" +
          compactHex(currVal) + "} (no x^" + mDegree + " overflow)",
      ],
      isOverflow: false,
    };
  }

  if (mDegree <= 16) {
    const shiftedBin = toPaddedBin(unreducedShift, mDegree + 1);
    const modBin = toPaddedBin(modPoly, mDegree + 1);
    const resultBin = toPaddedBin(currVal, mDegree);
    return {
      lines: [
        "1. Shift left (× x):   " + shiftedBin + "  (overflows x^" + mDegree + ")",
        "2. XOR m(x):         ⊕ " + modBin,
        "3. Reduced result:      " + resultBin + "  ({" + toHex(currVal) + "})",
      ],
      isOverflow: true,
    };
  }

  const mask = (1n << BigInt(mDegree)) - 1n;
  const lowShifted = unreducedShift & mask;
  const lowMod = modPoly & mask;
  return {
    lines: [
      "1. Shift left & drop x^" + mDegree + ": {" + compactHex(lowShifted) + "}",
      "2. XOR lower m(x) taps: ⊕ (" + polynomial(lowMod) + ")",
      "3. Reduced result: {" + compactHex(currVal) + "}",
    ],
    isOverflow: true,
  };
}

/**
 * Build one Shift-and-XOR multiplication step card organized into two student-friendly sub-blocks
 * (**1. Shift & Reduce** and **2. Check Bit & Update Running Sum**), Stallings `{hex}` brace notation,
 * explicit `m(x)` overflow reduction math, de-cluttered status badges, and a live running formula strip.
 *
 * @param {object} trace - Backend `shift-and-xor` trace dictionary.
 * @param {number} idx - Zero-based multiplier bit step index.
 * @param {boolean} compactValues - Whether compact large-field summarization is enabled.
 * @param {boolean} isCurrentRegion - Attach `"Current trace step"` ARIA region label.
 * @param {string} [stagePrefix=""] - Optional stage prefix for two-stage division.
 * @returns {HTMLElement} Populated multiplication step card.
 */
function multiplyStepCard(trace, idx, compactValues, isCurrentRegion, stagePrefix = "") {
  const step = trace.steps[idx];
  const prevStep = idx > 0 ? trace.steps[idx - 1] : null;
  const mDeg = trace.m ?? trace.m_degree ?? 8;
  const shortHex = text => significantDigits(text).toUpperCase();
  const cellHex = text => formatCellText(text, "hex", compactValues, mDeg);

  const priorShort = shortHex(prevStep?.accumulator_hex ?? "0");
  const partialShort = shortHex(step.partial_hex);
  const totalShort = shortHex(step.accumulator_hex);
  const partialDisp = cellHex(step.partial_hex);
  const totalDisp = cellHex(step.accumulator_hex);
  const prevPartialDisp = prevStep ? cellHex(prevStep.partial_hex) : null;
  const prevAccDisp = prevStep ? cellHex(prevStep.accumulator_hex) : "0";

  const card = element("section", undefined, "trace-card multiply-step-card");
  if (isCurrentRegion) {
    card.setAttribute("role", "region");
    card.setAttribute("aria-label", "Current trace step");
  }
  card.append(
    mathElement("span", "Multiplier bit " + step.i, "step-eyebrow"),
    mathElement("h3", multiplyKnowledgeTitle(step, stagePrefix), "step-knowledge-title"),
  );

  const banner = idx === 0
    ? "Step 1 (i = 0): Initial A(x) = {" + partialDisp + "}; bit b0 = " + step.multiplier_bit +
      (step.added ? " → Running XOR set to {" + totalDisp + "}" : " → Running XOR stays {0}")
    : "Step " + idx + " → Step " + (idx + 1) + " (i = " + step.i + "): " +
      (step.reduced ? "Shifted + Reduced ⊕ m(x)" : "Shifted left") +
      "; bit b_" + step.i + " = " + step.multiplier_bit +
      (step.added
        ? " → Running XOR updated ({" + prevAccDisp + "} → {" + totalDisp + "})"
        : " → Running XOR unchanged ({" + totalDisp + "})");
  card.append(mathElement("p", banner, "diff-banner"));

  // Sub-Block A: 1. Shift & Reduce (x^i · A(x) mod m(x))
  const shiftDiffClass = idx === 0 ? "diff-unchanged" : step.reduced ? "diff-reduced" : "diff-carried";
  const shiftBadgeText = idx === 0 ? "Initial A(x)" : step.reduced ? "Reduced ⊕ m(x)" : "Shifted left";
  const shiftBlock = element("div", undefined, "mul-subblock mul-shift-block " + shiftDiffClass);
  const shiftHead = element("div", undefined, "mul-subblock-head");
  shiftHead.append(
    mathElement("h4", "1. Shift & Reduce (x^" + step.i + " · A(x) mod m(x))", "mul-subblock-title"),
    mathElement("span", shiftBadgeText, "diff-tag " + shiftDiffClass),
  );

  const shiftDl = element("dl", undefined, "equivalents mul-subblock-dl");
  const shiftDd = element("dd");
  const shiftValSpan = element("span", "{" + partialDisp + "}", "diff-cell-val");
  makeCopyableValue(shiftValSpan, step.partial_hex.toUpperCase());
  shiftDd.append(shiftValSpan);
  if (prevStep) {
    shiftDd.append(element("span", "prev: {" + prevPartialDisp + "} → now: {" + partialDisp + "}", "diff-prev-value"));
  }
  const reducedDd = mathElement(
    "dd",
    step.reduced ? "Yes (overflowed x^" + mDeg + ")" : "No (degree < " + mDeg + ")",
  );
  shiftDl.append(
    element("dt", "Shifted operand A"),
    shiftDd,
    element("dt", "Reduced?"),
    reducedDd,
  );

  const prevBig = prevStep ? BigInt("0x" + prevStep.partial_hex) : 0n;
  const currBig = BigInt("0x" + step.partial_hex);
  const modBig = BigInt("0x" + (trace.reduction_poly_hex || "1"));
  const breakdown = formatStepReductionBreakdown(prevBig, currBig, modBig, mDeg, idx, Boolean(step.reduced));
  const breakdownBox = element(
    "div",
    undefined,
    "reduction-breakdown" + (breakdown.isOverflow ? " is-overflow" : ""),
  );
  for (const line of breakdown.lines) {
    const lineEl = element("div", undefined, "reduction-breakdown-line");
    appendMathText(lineEl, line);
    breakdownBox.append(lineEl);
  }
  shiftBlock.append(shiftHead, shiftDl, breakdownBox);

  // Sub-Block B: 2. Check Bit b_i & Update Running Sum
  const sumDiffClass = step.added ? "diff-updated" : "diff-unchanged";
  const sumBadgeText = "b_" + step.i + " = " + step.multiplier_bit + (step.added ? " · Include" : " · Skip");
  const sumBlock = element("div", undefined, "mul-subblock mul-sum-block " + sumDiffClass);
  const sumHead = element("div", undefined, "mul-subblock-head");
  sumHead.append(
    mathElement("h4", "2. Check Bit b_" + step.i + " & Update Running Sum", "mul-subblock-title"),
    mathElement("span", sumBadgeText, "diff-tag " + sumDiffClass),
  );

  const sumDl = element("dl", undefined, "equivalents mul-subblock-dl");
  const bitDd = element(
    "dd",
    step.multiplier_bit === 1 ? "1 (include shifted term in sum)" : "0 (skip shifted term)",
  );
  const accDd = element("dd");
  const accValSpan = element("span", "{" + totalDisp + "}", "diff-cell-val");
  makeCopyableValue(accValSpan, step.accumulator_hex.toUpperCase());
  accDd.append(accValSpan);
  if (idx === 0) {
    accDd.append(
      element(
        "span",
        step.added ? "prev: {0} → now: {" + totalDisp + "}" : "stays {0}",
        "diff-prev-value",
      ),
    );
  } else {
    accDd.append(
      element(
        "span",
        step.added
          ? "prev: {" + prevAccDisp + "} → now: {" + totalDisp + "}"
          : "prev: {" + prevAccDisp + "} (unchanged)",
        "diff-prev-value",
      ),
    );
  }
  sumDl.append(
    mathElement("dt", "Bit of B (b_" + step.i + ")"),
    bitDd,
    element("dt", "Running XOR"),
    accDd,
  );

  const equation = element(
    "p",
    step.added
      ? "{" + priorShort + "} ⊕ {" + partialShort + "} = {" + totalShort + "}"
      : "Unchanged: Running XOR stays {" + totalShort + "}",
    "bit-equation",
  );
  sumBlock.append(sumHead, sumDl, equation);

  // Bottom Live Running Formula Strip
  const formulaStrip = element("div", undefined, "mul-formula-strip");
  if (mDeg <= 8) {
    formulaStrip.append(element("span", "Sum = ", "mul-formula-prefix"));
    for (let k = 0; k <= idx; k += 1) {
      if (k > 0) formulaStrip.append(document.createTextNode(" ⊕ "));
      const termStep = trace.steps[k];
      const termSpan = element(
        "span",
        "[" + termStep.multiplier_bit + "]·{" + shortHex(termStep.partial_hex) + "}",
        "mul-formula-term" +
          (k === idx ? " is-active" : "") +
          (termStep.added ? " is-included" : " is-skipped"),
      );
      formulaStrip.append(termSpan);
    }
    formulaStrip.append(element("span", " = {" + totalShort + "}", "mul-formula-result"));
  } else {
    let includedCount = 0;
    for (let k = 0; k <= idx; k += 1) {
      if (trace.steps[k]?.added) includedCount += 1;
    }
    formulaStrip.textContent =
      "Included " + includedCount + " of " + (idx + 1) +
      " terms so far → Running XOR = {" + totalDisp + "}";
  }

  const blocksGrid = element("div", undefined, "mul-subblocks-grid");
  blocksGrid.append(shiftBlock, sumBlock);
  card.append(blocksGrid, formulaStrip);
  return card;
}

/**
 * Render the Shift-and-XOR multiplication visualizer with linked multiplier-bit buttons.
 *
 * Clicking or navigating a bit button with Left/Right/Home/End highlights its matching
 * row in Table 1 (`x^i * A mod m`) and, when the bit is `1`, its matching partial-product
 * row in Table 2, while displaying the educational step title, running XOR equation, and diff highlights.
 *
 * @param {object} trace - Backend `shift-and-xor` trace dictionary.
 * @param {number} limit - Number of steps revealed in tables.
 * @param {number} current - Currently focused multiplier-bit step index.
 * @param {"step" | "grid" | "table"} layoutMode - Active layout mode.
 * @param {boolean} compactValues - Whether compact large-field values are enabled.
 * @param {(index: number) => void} chooseBit - Callback invoked when the user selects a bit.
 * @param {{showBits?: boolean, isCurrentRegion?: boolean, stagePrefix?: string}} [options] - Optional flags for comparison/stages.
 * @returns {HTMLElement} Populated multiplication visualizer `<section>`.
 */
function multiply(trace, limit, current, layoutMode, compactValues, chooseBit, options = {}) {
  const { showBits = true, isCurrentRegion = true, stagePrefix = "" } = options;
  const section = element("section");
  if (!trace.steps.length) {
    section.append(element("p", "The multiplier is zero. There are no partial products to add."));
    return section;
  }
  const active = trace.steps[current] || trace.steps[0];
  if (showBits) {
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
      const positions = { ArrowLeft: current - 1, ArrowRight: current + 1, Home: 0, End: trace.steps.length - 1 };
      if (!Object.hasOwn(positions, event.key)) return;
      const nextIdx = Math.max(0, Math.min(positions[event.key], trace.steps.length - 1));
      if (nextIdx === current) return;
      event.preventDefault();
      chooseBit(nextIdx);
    });
    section.append(element("h3", "Multiplier bits · low to high"), bits);
  }

  const shortHex = text => significantDigits(text).toUpperCase();
  const cellHex = text => formatCellText(text, "hex", compactValues, trace.m_degree);
  const prior = shortHex(trace.steps[current - 1]?.accumulator_hex ?? "0");
  const partial = shortHex(active.partial_hex);
  const total = shortHex(active.accumulator_hex);
  const equation = element("p", active.added ? prior + " ⊕ " + partial + " = " + total : "Running XOR stays " + total,
    "bit-equation");

  if (layoutMode === "step") {
    section.append(multiplyStepCard(trace, current, compactValues, isCurrentRegion, stagePrefix));
    return section;
  }

  if (layoutMode === "grid") {
    const grid = element("div", undefined, "trace-grid-cards");
    trace.steps.slice(0, limit).forEach((_, idx) => {
      const card = multiplyStepCard(trace, idx, compactValues, idx === current && isCurrentRegion, stagePrefix);
      if (idx === current) card.classList.add("is-current");
      if (idx === current - 1) card.classList.add("diff-prev-card");
      grid.append(card);
    });
    section.append(equation, grid);
    return section;
  }

  const steps = trace.steps.slice(0, limit);
  const selected = steps.filter(step => step.added);
  const shiftTable = table(
    "Table 1 · Shifts and reductions",
    ["i", "x^i A mod m (hex)", "Reduced?", "Polynomial"],
    steps.map(step => [
      step.i,
      cellHex(step.partial_hex),
      step.reduced ? "Yes" : "No",
      formatCellText(step.partial_poly, "algebraic", compactValues, trace.m_degree),
    ]),
    () => false,
    {
      prevRow: current > 0 ? current - 1 : -1,
      currRow: current,
      mathCols: new Set([3]),
      cellClass: (r, c) => (r === current && c === 1 ? (steps[r]?.reduced ? "diff-reduced" : "diff-carried") : ""),
    },
  );
  const activeSelectedIdx = selected.indexOf(active);
  const partialTable = table(
    "Table 2 · Selected partial products",
    ["i", "Bit of B", "Partial product (hex)", "Cumulative XOR (hex)"],
    selected.map(step => [step.i, step.multiplier_bit, cellHex(step.partial_hex), cellHex(step.accumulator_hex)]),
    (_, col) => col === 3,
    {
      prevRow: activeSelectedIdx > 0 ? activeSelectedIdx - 1 : -1,
      currRow: activeSelectedIdx,
    },
  );
  section.append(
    mathElement("h3", multiplyKnowledgeTitle(active, stagePrefix), "step-knowledge-title"),
    element("p", "Bit " + active.i + " is " + active.multiplier_bit + ". " + (active.added
      ? "XOR its shifted value into the running result." : "Skip its shifted value.")),
    equation,
    shiftTable,
    partialTable,
  );
  return section;
}

/**
 * Build the zero-horizontal-scroll Extended Euclid Step Inspector Square for a single Table 4.7 step,
 * with informative educational title, persistent Previous-to-Current visual diff badges (`← prev B`,
 * `New T`, `Unchanged`), true `<sup>`/`<sub>` typography, and inline `was: <prev>` deltas.
 *
 * @param {object} trace - Backend `extended_euclid_table_4_7` trace dictionary.
 * @param {number} rowIndex - Zero-based index into `trace.table_4_7_rows`.
 * @param {"hex" | "bin" | "algebraic"} notation - Active cell notation.
 * @param {boolean} compactValues - Whether compact large-field summarization is active.
 * @param {boolean} isCurrentRegion - Whether this card is the active `"Current trace step"` region.
 * @param {string} [stagePrefix=""] - Optional stage prefix for two-stage division.
 * @returns {HTMLElement} Populated Step Inspector Square `<section>`.
 */
function euclidInspectorSquare(trace, rowIndex, notation, compactValues, isCurrentRegion, stagePrefix = "") {
  const rows = trace.table_4_7_rows;
  const row = rows[rowIndex];
  const prevRow = rowIndex > 0 ? rows[rowIndex - 1] : null;
  const isFinal = rowIndex === rows.length - 1;
  const success = trace.termination.b3_final === 1;
  const mDeg = trace.m_degree ?? 8;
  const isMathNotation = notation === "algebraic";

  const fullCell = (targetRow, term) => {
    const text = targetRow.cells[term][notation];
    return notation === "hex" ? text.toUpperCase() : text;
  };
  const displayCell = (targetRow, term) => formatCellText(targetRow.cells[term][notation], notation, compactValues, mDeg);
  const bannerCell = (targetRow, term) => {
    const val = displayCell(targetRow, term);
    return notation === "hex" ? "{" + val + "}" : val;
  };

  const square = element("section", undefined, "trace-card euclid-inspector-square");
  if (isCurrentRegion) {
    square.setAttribute("role", "region");
    square.setAttribute("aria-label", "Current trace step");
  }

  const head = element("div", undefined, "euclid-inspector-head");
  const titleWrap = element("div", undefined, "euclid-inspector-title");
  titleWrap.append(
    element("span", "Extended Euclid · step " + row.step, "step-eyebrow"),
    mathElement("h3", euclidKnowledgeTitle(trace, rowIndex, stagePrefix), "step-knowledge-title"),
  );

  const badges = element("div", undefined, "euclid-inspector-badges");
  badges.append(
    mathElement(
      "span",
      row.step === 0
        ? "Initialization"
        : isFinal
          ? success
            ? "Final step · B3(x) = 1"
            : "Terminated · B3(x) = 0"
          : "Iteration " + row.step,
      "lesson-badge",
    ),
  );
  const qBadge = element("span", undefined, "euclid-q-badge");
  qBadge.append(document.createTextNode("Q(x) = "));
  if (isMathNotation) qBadge.append(mathElement("span", displayCell(row, "Q")));
  else qBadge.append(document.createTextNode(displayCell(row, "Q")));
  makeCopyableValue(qBadge, fullCell(row, "Q"));
  badges.append(qBadge);

  const formulaText = row.step === 0
    ? "A ← (1, 0, m(x)) · B ← (0, 1, b(x))"
    : "Q = A3 div B3 · T1 = A1 ⊕ Q·B1 · T2 = A2 ⊕ Q·B2 · T3 = A3 mod B3";
  head.append(titleWrap, badges, mathElement("code", formulaText, "euclid-formula-pill"));

  // Concise 1-line transition banner summarizing Step k-1 → Step k.
  const bannerText = row.step === 0
    ? "Step 0 (Init): A starts at (1, 0, m(x)) and B starts at (0, 1, b(x))."
    : "Step " + (row.step - 1) + " → Step " + row.step + ": B shifted into A; Q = " + bannerCell(row, "Q") +
    " produced new B1, B2, B3" + (isFinal ? (success ? " (B3 = 1 → Inverse Found)" : " (B3 = 0 → No Inverse)") : "") + ".";
  const banner = mathElement("p", bannerText, "diff-banner");

  const triples = element("div", undefined, "euclid-triples-grid");

  // Left card: Triple A = (A1, A2, A3): carried from previous step's B
  const cardA = element("div", undefined, "euclid-triple-card is-carried");
  const headA = element("h4", "Triple A(x) ");
  headA.append(mathElement("small", row.step > 0 ? "A ← prev B" : "Modulus m(x)"));
  const dlA = element("dl", undefined, "equivalents");
  for (const term of ["A1", "A2", "A3"]) {
    const dt = mathElement("dt", term + "(x)");
    const currVal = displayCell(row, term);
    const fullVal = fullCell(row, term);
    let meta = { diffClass: "diff-unchanged", badge: "Init", fullValue: fullVal, isMathValue: isMathNotation };
    if (prevRow) {
      const sameAsPrevA = row[term] === prevRow[term];
      const prevAVal = displayCell(prevRow, term);
      if (isFinal && !success && term === "A3") {
        meta = {
          diffClass: "diff-reduced",
          badge: "GCD / No Inverse",
          prevText: sameAsPrevA ? undefined : "was: " + prevAVal,
          fullValue: fullVal,
          extraClass: "picked is-gcd",
          isMathValue: isMathNotation,
        };
      } else if (sameAsPrevA) {
        meta = { diffClass: "diff-unchanged", badge: "Unchanged", fullValue: fullVal, isMathValue: isMathNotation };
      } else {
        meta = {
          diffClass: "diff-carried",
          badge: "← prev B" + term[1],
          prevText: "was: " + prevAVal,
          fullValue: fullVal,
          isMathValue: isMathNotation,
        };
      }
    } else if (isFinal && !success && term === "A3") {
      meta = {
        diffClass: "diff-reduced",
        badge: "GCD / No Inverse",
        fullValue: fullVal,
        extraClass: "picked is-gcd",
        isMathValue: isMathNotation,
      };
    }
    dlA.append(dt, buildDiffValueNode(currVal, meta));
  }
  cardA.append(headA, dlA);

  // Right card: Triple B = (B1, B2, B3): newly computed via T = A ⊕ Q·B
  const cardB = element(
    "div",
    undefined,
    "euclid-triple-card is-updated" + (isFinal && success ? " is-inverse-found" : ""),
  );
  const headB = element("h4", "Triple B(x) ");
  headB.append(mathElement("small", row.step > 0 ? "B ← A ⊕ Q·B" : "Operand b(x)"));
  const dlB = element("dl", undefined, "equivalents");
  for (const term of ["B1", "B2", "B3"]) {
    const dt = mathElement("dt", term + "(x)");
    const currVal = displayCell(row, term);
    const fullVal = fullCell(row, term);
    let meta = { diffClass: "diff-unchanged", badge: "Init", fullValue: fullVal, isMathValue: isMathNotation };
    if (prevRow) {
      const sameAsPrevB = row[term] === prevRow[term];
      const prevBVal = displayCell(prevRow, term);
      if (isFinal && success && term === "B2") {
        meta = {
          diffClass: "diff-updated",
          badge: "Inverse Found",
          prevText: sameAsPrevB ? undefined : "was: " + prevBVal,
          fullValue: fullVal,
          extraClass: "picked",
          isMathValue: isMathNotation,
        };
      } else if (sameAsPrevB) {
        meta = { diffClass: "diff-unchanged", badge: "Unchanged", fullValue: fullVal, isMathValue: isMathNotation };
      } else {
        meta = {
          diffClass: "diff-updated",
          badge: "New T" + term[1],
          prevText: "was: " + prevBVal,
          fullValue: fullVal,
          isMathValue: isMathNotation,
        };
      }
    } else if (isFinal && success && term === "B2") {
      meta = {
        diffClass: "diff-updated",
        badge: "Inverse Found",
        fullValue: fullVal,
        extraClass: "picked",
        isMathValue: isMathNotation,
      };
    }
    dlB.append(dt, buildDiffValueNode(currVal, meta));
  }
  cardB.append(headB, dlB);

  triples.append(cardA, cardB);
  square.append(head, banner, triples);
  return square;
}

/**
 * Render the Stallings Chapter 4 Table 4.7 Extended Euclid trace in `step`, `grid`, or `table` mode.
 *
 * Highlights `B2(x)` (column 6) on the final row when `B3(x) == 1` (inverse found),
 * or `A3(x)` (column 4) when `B3(x) == 0` (no inverse; `A3(x) = gcd(m(x), b(x))`).
 *
 * @param {object} trace - Backend `extended_euclid_table_4_7` trace dictionary.
 * @param {number} limit - Number of Table 4.7 rows revealed.
 * @param {"hex" | "bin" | "algebraic"} notation - Active Table 4.7 cell notation.
 * @param {"step" | "grid" | "table"} layoutMode - Active layout mode.
 * @param {boolean} compactValues - Whether compact large-field summarization is enabled.
 * @param {number} currentStep - Zero-based active step index.
 * @param {boolean} [isCurrentRegion=true] - Attach `"Current trace step"` ARIA region label.
 * @param {string} [stagePrefix=""] - Optional stage prefix for two-stage division.
 * @returns {HTMLElement} Rendered Table 4.7 section with termination note.
 */
function euclid(trace, limit, notation, layoutMode, compactValues, currentStep = 0, isCurrentRegion = true, stagePrefix = "") {
  const terms = ["Q", "A1", "A2", "A3", "B1", "B2", "B3"];
  const rows = trace.table_4_7_rows;
  const termination = trace.termination;
  const success = termination.b3_final === 1;
  const labels = terms.map(term => term + "(x)");
  const mDeg = trace.m_degree ?? 8;
  const cells = row => terms.map(term => formatCellText(row.cells[term][notation], notation, compactValues, mDeg));

  const endingText = success
    ? "B3(x) = 1, so B2(x) gives the inverse."
    : "B3(x) = 0. No inverse exists. A3(x) gives the gcd: " + termination.gcd_formatted.algebraic + ".";

  if (layoutMode === "step" && rows.length) {
    const activeIdx = Math.max(0, Math.min(rows.length - 1, limit === Infinity ? currentStep : limit - 1));
    const card = euclidInspectorSquare(trace, activeIdx, notation, compactValues, isCurrentRegion, stagePrefix);
    if (activeIdx >= rows.length - 1 || !success) {
      card.append(mathElement("p", endingText, "euclid-termination-note"));
    }
    return card;
  }

  if (layoutMode === "grid" && rows.length) {
    const section = element("section");
    section.append(element("h3", "Table 4.7 · Extended Euclid"));
    const grid = element("div", undefined, "trace-grid-cards");
    const count = Math.min(rows.length, limit);
    for (let idx = 0; idx < count; idx += 1) {
      const card = euclidInspectorSquare(trace, idx, notation, compactValues, idx === currentStep && isCurrentRegion, stagePrefix);
      if (idx === currentStep) card.classList.add("is-current");
      if (idx === currentStep - 1) card.classList.add("diff-prev-card");
      grid.append(card);
    }
    section.append(grid);
    if (limit >= rows.length) section.append(mathElement("p", endingText, "euclid-termination-note"));
    return section;
  }

  const visibleRows = rows.slice(0, limit);
  const stepping = limit !== Infinity;
  const activeIdx = Math.max(0, Math.min(visibleRows.length - 1, stepping ? currentStep : visibleRows.length - 1));
  const tableView = table(
    "Table 4.7 · Extended Euclid",
    ["Step", ...labels],
    visibleRows.map(row => [row.step, ...cells(row)]),
    (row, col) => row === rows.length - 1 && (success ? col === 6 : col === 4),
    {
      prevRow: stepping && currentStep > 0 ? currentStep - 1 : -1,
      currRow: stepping ? currentStep : -1,
      mathCols: notation === "algebraic" ? new Set([1, 2, 3, 4, 5, 6, 7]) : undefined,
      subtitle: rows.length ? euclidKnowledgeTitle(trace, activeIdx, stagePrefix) : undefined,
      cellClass: (r, c) => {
        if (!stepping || r !== currentStep || r === 0) return "";
        const curr = rows[r];
        const prev = rows[r - 1];
        if (!curr || !prev) return "";
        if (c >= 2 && c <= 4) {
          const term = terms[c - 1];
          return curr[term] !== prev[term] ? "diff-carried" : "diff-unchanged";
        }
        if (c >= 5 && c <= 7) {
          const term = terms[c - 1];
          return curr[term] !== prev[term] ? "diff-updated" : "diff-unchanged";
        }
        return "";
      },
    },
  );
  if (limit >= rows.length) {
    tableView.append(mathElement("p", endingText, "euclid-termination-note"));
  }
  return tableView;
}

/**
 * Create a stateful trace viewer bound to a panel, body container, and toolbar container.
 *
 * Manages three layout modes (`Step view`, auto-maximized `All steps grid`, `Classic table`)
 * with a gliding active indicator, side-by-side `Compare prev → curr` visual diff mode,
 * uncluttered 2-row toolbar (`First step`, `Previous`, instant `First changed bit` / `First active step`,
 * `Play animation`/`Pause` + speed selector, `Next`, `Last step`, interactive scrubber),
 * boundary disabled states, sequential step cascade (`2 → 3 → 4 → 5`) on non-adjacent jumps,
 * `Compact values` / `Full m-bit` toggle, Table 4.7 notation switching, and the
 * `Expand full view` modal dialog (`#trace-fullscreen`).
 *
 * @param {HTMLElement} panel - Outer `<section>` toggled hidden when no trace is active.
 * @param {HTMLElement} body - Container where trace tables or step cards are rendered.
 * @param {HTMLElement} tools - Toolbar container populated with stepper and notation controls.
 * @returns {{show: (newTrace: object | null, newReductions?: object | null) => void}} Controller API.
 */
export function createTraceView(panel, body, tools) {
  const narrowScreen = window.matchMedia("(max-width: 600px)");
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  let timer = null;
  let cascadeTimer = null;
  let cascadeTarget = null;
  let trace = null;
  let reductions = null;
  let notation = "hex";
  let current = null;
  let layoutMode = "table";
  let compactValues = false;
  let comparePrev = false;
  let isMaximized = false;
  let allRows = true;
  let speed = "normal";

  let stepLabel;
  let scrubber;
  let firstButton;
  let prevButton;
  let firstChangedButton;
  let playButton;
  let nextButton;
  let lastButton;
  let exitMaxButton;
  let compactToggleButton;
  let compareToggleButton;
  let modesIndicator;
  let modePills = {};

  /**
   * Synchronize a button's `disabled` property and `aria-disabled` attribute together.
   *
   * @param {HTMLButtonElement | undefined} btn - Target button element.
   * @param {boolean} isDisabled - Desired disabled state.
   */
  function setButtonDisabled(btn, isDisabled) {
    if (!btn) return;
    const flag = Boolean(isDisabled);
    btn.disabled = flag;
    btn.setAttribute("aria-disabled", String(flag));
  }

  /**
   * Locate the first changed bit or active computation step in a trace so users on large
   * cryptographic fields (`GF(2^163)` to `GF(2^571)`) can skip trailing zeros in one click.
   *
   * @param {object | null} activeTrace - Loaded trace object.
   * @returns {number | null} Zero-based step index, or `null` when no active step exists.
   */
  function findFirstChangedStep(activeTrace) {
    if (!activeTrace) return null;
    if (activeTrace.algorithm === "shift-and-xor" && Array.isArray(activeTrace.steps)) {
      const addedIdx = activeTrace.steps.findIndex(step => Boolean(step.added) || step.multiplier_bit === 1);
      if (addedIdx >= 0) return addedIdx;
      const reducedIdx = activeTrace.steps.findIndex(step => Boolean(step.reduced));
      return reducedIdx >= 0 ? reducedIdx : null;
    }
    if (activeTrace.algorithm === "bitwise-xor" && Array.isArray(activeTrace.columns)) {
      const idx = activeTrace.columns.findIndex(col => ((col.a ^ col.b) === 1) || (col.a === 1 && col.b === 1));
      return idx >= 0 ? idx : null;
    }
    if (activeTrace.trace_type === "mod_reduce" && Array.isArray(activeTrace.steps)) {
      return activeTrace.steps.length > 0 ? 0 : null;
    }
    if (activeTrace.trace_type === "extended_euclid_table_4_7" && Array.isArray(activeTrace.table_4_7_rows)) {
      return activeTrace.table_4_7_rows.length > 1 ? 1 : null;
    }
    if (activeTrace.trace_type === "gf2m_division_two_stage") {
      const total = (activeTrace.stage_1_inverse?.table_4_7_rows?.length ?? 0) +
        (activeTrace.stage_2_multiply?.steps?.length ?? 0);
      return total > 1 ? 1 : null;
    }
    if (activeTrace.trace_type === "tabular_steps" && Array.isArray(activeTrace.rows)) {
      return activeTrace.rows.length > 1 ? 1 : (activeTrace.rows.length ? 0 : null);
    }
    return null;
  }

  /**
   * Update playback button boundary disabled states and the `First changed bit` / `First active step`
   * button label, tooltip, and availability for the current trace step.
   */
  function syncPlaybackControls() {
    const count = length();
    const activeStep = current ?? 0;
    const singleOrEmpty = count <= 1;

    if (singleOrEmpty) {
      setButtonDisabled(firstButton, true);
      setButtonDisabled(prevButton, true);
      setButtonDisabled(nextButton, true);
      setButtonDisabled(lastButton, true);
      setButtonDisabled(playButton, true);
    } else {
      setButtonDisabled(playButton, false);
      setButtonDisabled(firstButton, activeStep <= 0);
      setButtonDisabled(prevButton, activeStep <= 0);
      setButtonDisabled(nextButton, current !== null && activeStep >= count - 1);
      setButtonDisabled(lastButton, current !== null && activeStep >= count - 1);
    }

    if (firstChangedButton) {
      const targetIdx = findFirstChangedStep(trace);
      const isBitTrace = trace?.algorithm === "shift-and-xor" || trace?.algorithm === "bitwise-xor";
      firstChangedButton.textContent = isBitTrace ? "First changed bit" : "First active step";
      const actionLabel = isBitTrace ? "first changed bit" : "first active step";
      const tip = targetIdx === null
        ? "No active changed bit or step in this trace"
        : "Jump directly to " + actionLabel + " (Step " + (targetIdx + 1) + ")";
      firstChangedButton.title = tip;
      firstChangedButton.setAttribute("aria-label", tip);
      setButtonDisabled(firstChangedButton, targetIdx === null || activeStep === targetIdx);
    }
  }

  /** Stop any in-flight sequential cascade timer. */
  function stopCascade() {
    if (cascadeTimer) {
      clearTimeout(cascadeTimer);
      cascadeTimer = null;
    }
    cascadeTarget = null;
  }

  /** Stop any active playback or cascade timer and reset the Play/Pause button state. */
  function stop() {
    stopCascade();
    if (timer) {
      clearInterval(timer);
      timer = null;
    }
    if (playButton) {
      playButton.textContent = "Play animation";
      playButton.setAttribute("aria-pressed", "false");
    }
  }

  /**
   * Toggle panel-level maximized grid workspace (`.is-maximized`).
   * @param {boolean} flag - True to maximize `#trace-panel` to ~95vw/95vh.
   */
  function setMaximized(flag) {
    isMaximized = Boolean(flag);
    panel.classList.toggle("is-maximized", isMaximized);
    if (exitMaxButton) exitMaxButton.hidden = !isMaximized;
  }

  // Allow pressing Escape to exit maximized trace view without leaving the page.
  document.addEventListener("keydown", event => {
    if (event.key !== "Escape" || !isMaximized) return;
    const activeDialog = document.querySelector("dialog[open]");
    if (activeDialog) return;
    event.preventDefault();
    setMaximized(false);
    modesIndicator?.update();
  });

  /**
   * Determine the field degree `m` associated with the active trace.
   * @returns {number} Field degree `m` (defaults to 8 when unspecified).
   */
  function traceDegree() {
    return trace?.m_degree ?? trace?.m ?? trace?.stage_1_inverse?.m_degree ?? (trace?.columns?.length || 8);
  }

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
   * Render a single step snapshot of the active trace (used for both Current and Previous panes).
   *
   * @param {number} stepIdx - Zero-based step index to render.
   * @param {boolean} activeCompactValues - Compact formatting flag.
   * @param {boolean} isCurrentRegion - True for the active step pane, false for the previous snapshot.
   * @returns {HTMLElement} Rendered step node.
   */
  function renderSingleStepNode(stepIdx, activeCompactValues, isCurrentRegion) {
    if (trace.trace_type === "tabular_steps" && trace.rows.length) {
      const idx = Math.max(0, Math.min(trace.rows.length - 1, stepIdx));
      const prevRow = idx > 0 ? trace.rows[idx - 1] : null;
      const cellMeta = trace.rows[idx].map((val, colIdx) => {
        if (!prevRow) return { diffClass: "diff-unchanged", badge: "Init" };
        return prevRow[colIdx] !== val
          ? { diffClass: "diff-updated", badge: "Updated", prevText: "was: " + prevRow[colIdx] }
          : { diffClass: "diff-unchanged", badge: "Unchanged" };
      });
      return stepCard(
        trace.title + " · step " + (idx + 1),
        trace.title + ": Step " + (idx + 1) + ": " + trace.rows[idx][0],
        trace.headers,
        trace.rows[idx],
        isCurrentRegion,
        { cellMeta },
      );
    }
    if (trace.trace_type === "mod_reduce") {
      return reduction(trace, stepIdx + 1, "Modulo reduction", "step", activeCompactValues, stepIdx, isCurrentRegion);
    }
    if (trace.algorithm === "bitwise-xor") {
      return xor(trace, stepIdx + 1, "step", stepIdx, isCurrentRegion);
    }
    if (trace.algorithm === "shift-and-xor") {
      return multiply(trace, stepIdx + 1, stepIdx, "step", activeCompactValues, selectBit, {
        showBits: isCurrentRegion,
        isCurrentRegion,
      });
    }
    if (trace.trace_type === "extended_euclid_table_4_7") {
      return euclid(trace, stepIdx + 1, notation, "step", activeCompactValues, stepIdx, isCurrentRegion);
    }
    if (trace.trace_type === "gf2m_division_two_stage") {
      const inverse = trace.stage_1_inverse;
      const inverseSteps = inverse.table_4_7_rows.length;
      if (stepIdx < inverseSteps) {
        return euclid(
          inverse,
          stepIdx + 1,
          notation,
          "step",
          activeCompactValues,
          stepIdx,
          isCurrentRegion,
          "Stage 1 (Extended Euclid Inverse) · ",
        );
      }
      const local = Math.max(0, stepIdx - inverseSteps);
      return multiply(
        trace.stage_2_multiply,
        local + 1,
        local,
        "step",
        activeCompactValues,
        step => selectBit(inverseSteps + step),
        {
          showBits: isCurrentRegion,
          isCurrentRegion,
          stagePrefix: "Stage 2 (Shift-and-XOR A × B^-1) · ",
        },
      );
    }
    return element("div");
  }

  /**
   * Render trace content into a target container (`body` or `#trace-fullscreen-body`).
   *
   * @param {HTMLElement} target - Destination container.
   * @param {"step" | "grid" | "table"} activeLayout - Layout mode to render.
   * @param {number} limit - Maximum number of rows/steps revealed (`Infinity` for all).
   * @param {boolean} activeCompactValues - Whether compact large-field values are enabled.
   * @param {boolean} [allowCompare=true] - Allow side-by-side `Compare prev → curr` in step mode.
   */
  function populateTraceContainer(target, activeLayout, limit, activeCompactValues, allowCompare = true) {
    target.replaceChildren();
    if (!trace) return;
    const activeStep = current ?? 0;

    // Show the color-coded visual diff legend whenever stepping or in Step/Grid views.
    if (length() > 0 && (activeLayout === "step" || activeLayout === "grid" || !allRows)) {
      target.append(createDiffLegend());
    }

    // Auto-expand initial-reduction details whenever operands had degree >= m, showing explicit equations.
    if (reductions && trace.trace_type !== "mod_reduce") {
      for (const [key, row] of Object.entries(reductions)) {
        const details = element("details", undefined, "initial-reduction-panel");
        details.open = true;
        details.append(
          element("summary", "Initial reduction · Operand " + key.toUpperCase() + " was reduced first"),
        );
        if (Array.isArray(row.steps) && row.steps.length) {
          const eqList = element("div", undefined, "initial-reduction-steps");
          row.steps.forEach((stepRow, stepIdx) => {
            const beforeHex = formatCellText(stepRow.before_hex, "hex", activeCompactValues, row.m_degree);
            const reducerHex = formatCellText(stepRow.reducer_hex, "hex", activeCompactValues, row.m_degree);
            const afterHex = formatCellText(stepRow.after_hex, "hex", activeCompactValues, row.m_degree);
            const shiftAmt = stepRow.target_degree - row.m_degree;
            const eqLine = element("p", undefined, "initial-reduction-eq");
            appendMathText(
              eqLine,
              "Step " + (stepIdx + 1) + " (cancel x^" + stepRow.target_degree + "): {" +
                beforeHex + "} ⊕ (m(x) · x^" + shiftAmt + " = {" + reducerHex + "}) = {" + afterHex + "}",
            );
            eqList.append(eqLine);
          });
          details.append(eqList);
        }
        details.append(reduction(row, Infinity, "Initial reduction", "table", activeCompactValues, 0));
        target.append(details);
      }
    }

    // Side-by-side Previous vs. Current comparison grid in Step view.
    if (allowCompare && comparePrev && activeLayout === "step" && length() > 0) {
      const grid = element("div", undefined, "diff-compare-grid");

      const prevPane = element("div", undefined, "diff-compare-pane is-prev");
      prevPane.setAttribute("role", "region");
      prevPane.setAttribute("aria-label", "Previous trace step");
      prevPane.append(element("div", activeStep > 0 ? "Previous · Step " + activeStep : "Previous step", "diff-compare-pane-head"));
      if (activeStep === 0) {
        prevPane.append(element("div", "Initial state: no previous step", "diff-empty-prev"));
      } else {
        prevPane.append(renderSingleStepNode(activeStep - 1, activeCompactValues, false));
      }

      const arrow = element("div", "→", "diff-compare-arrow");
      arrow.setAttribute("aria-hidden", "true");

      const currPane = element("div", undefined, "diff-compare-pane is-curr");
      currPane.append(element("div", "Current · Step " + (activeStep + 1), "diff-compare-pane-head"));
      currPane.append(renderSingleStepNode(activeStep, activeCompactValues, true));

      grid.append(prevPane, arrow, currPane);
      target.append(grid);
      return;
    }

    if (trace.trace_type === "tabular_steps") {
      let view;
      if (activeLayout === "step" && trace.rows.length) {
        view = renderSingleStepNode(activeStep, activeCompactValues, true);
      } else if (activeLayout === "grid" && trace.rows.length) {
        view = element("section");
        view.append(element("h3", trace.title));
        const grid = element("div", undefined, "trace-grid-cards");
        trace.rows.slice(0, limit).forEach((_, idx) => {
          const card = renderSingleStepNode(idx, activeCompactValues, idx === activeStep);
          if (idx === activeStep) card.classList.add("is-current");
          if (idx === activeStep - 1) card.classList.add("diff-prev-card");
          grid.append(card);
        });
        view.append(grid);
      } else {
        const visible = trace.rows.slice(0, limit);
        const activeRowIdx = Math.max(0, Math.min(visible.length - 1, activeStep));
        view = table(trace.title, trace.headers, visible, trace.selected, {
          prevRow: limit !== Infinity && activeStep > 0 ? activeStep - 1 : -1,
          currRow: limit !== Infinity ? activeStep : -1,
          subtitle: visible.length ? trace.title + ": Step " + (activeRowIdx + 1) + ": " + visible[activeRowIdx][0] : undefined,
        });
      }
      target.append(view);
    }
    if (trace.trace_type === "mod_reduce") {
      target.append(reduction(trace, limit, "Modulo reduction", activeLayout, activeCompactValues, activeStep));
    }
    if (trace.algorithm === "bitwise-xor") {
      target.append(
        mathElement("p", "Add or subtract each pair of bits modulo 2. Two ones cancel."),
        xor(trace, limit, activeLayout, activeStep),
      );
    }
    if (trace.algorithm === "shift-and-xor") {
      target.append(multiply(trace, limit, activeStep, activeLayout, activeCompactValues, selectBit));
    }
    if (trace.trace_type === "extended_euclid_table_4_7") {
      target.append(euclid(trace, limit, notation, activeLayout, activeCompactValues, activeStep));
    }
    if (trace.trace_type === "gf2m_division_two_stage") {
      // Division combines Stage 1 (Table 4.7 inverse) and Stage 2 (Shift-and-XOR product).
      const inverse = trace.stage_1_inverse;
      const inverseSteps = inverse.table_4_7_rows.length;
      if (activeLayout === "step") {
        target.append(renderSingleStepNode(activeStep, activeCompactValues, true));
      } else {
        const remaining = limit - inverseSteps;
        target.append(
          euclid(
            inverse,
            Math.min(limit, inverseSteps),
            notation,
            activeLayout,
            activeCompactValues,
            Math.min(activeStep, inverseSteps - 1),
            true,
            "Stage 1 (Extended Euclid Inverse) · ",
          ),
        );
        if (remaining > 0) {
          const local = Math.max(0, activeStep - inverseSteps);
          target.append(
            multiply(
              trace.stage_2_multiply,
              remaining,
              local,
              activeLayout,
              activeCompactValues,
              step => selectBit(inverseSteps + step),
              { stagePrefix: "Stage 2 (Shift-and-XOR A × B^-1) · " },
            ),
          );
        }
      }
    }
  }

  /**
   * Rebuild the trace DOM for the active `trace`, `current` step, `layoutMode`, and `notation`.
   */
  function renderBody() {
    const limit = allRows && layoutMode !== "step" ? Infinity : (current ?? 0) + 1;
    populateTraceContainer(body, layoutMode, limit, compactValues, true);
  }

  /**
   * Open the full-viewport `<dialog id="trace-fullscreen">` showing the complete classic tables.
   */
  function openFullViewModal() {
    const dialog = document.getElementById("trace-fullscreen");
    const modalBody = document.getElementById("trace-fullscreen-body");
    const closeBtn = document.getElementById("trace-fullscreen-close");
    if (!dialog || !modalBody) return;
    populateTraceContainer(modalBody, "table", Infinity, false, false);
    if (closeBtn && !closeBtn.dataset.bound) {
      closeBtn.dataset.bound = "true";
      closeBtn.addEventListener("click", () => dialog.close());
    }
    if (!dialog.open) dialog.showModal();
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
    if (!selected) return;
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
   * Update toolbar labels, mode pills, gliding indicator, compare toggle, scrubber, and trace DOM.
   * @returns {HTMLElement | undefined} Active multiplier-bit button, if rendered.
   */
  function render() {
    const previousLeft = body.querySelector(".multiplier-bits")?.scrollLeft ?? 0;
    const count = length();
    if (stepLabel) {
      const showingAll = allRows && layoutMode !== "step";
      stepLabel.textContent = showingAll ? "All steps" : "Step " + ((current ?? 0) + 1) + " of " + count;
      if (scrubber) {
        scrubber.max = String(Math.max(1, count));
        scrubber.value = String((current ?? 0) + 1);
      }
      if (compactToggleButton) {
        compactToggleButton.textContent = compactValues ? "Full m-bit" : "Compact values";
        compactToggleButton.setAttribute("aria-pressed", String(compactValues));
      }
      if (compareToggleButton) {
        compareToggleButton.setAttribute("aria-pressed", String(comparePrev && layoutMode === "step"));
      }
      for (const [modeKey, pill] of Object.entries(modePills)) {
        pill.setAttribute("aria-pressed", String(layoutMode === modeKey));
      }
      modesIndicator?.update();
    }
    syncPlaybackControls();
    renderBody();
    return revealLinkedSelection(previousLeft);
  }

  /**
   * Cascade sequentially (`start -> ... -> targetStep`) through intermediate steps so non-adjacent
   * jumps clearly reveal every intermediate bit shift, XOR accumulation, or Euclid reduction.
   *
   * @param {number} targetStep - Destination zero-based step index.
   * @param {{focusBit?: boolean}} [opts={}] - Restore keyboard focus onto the active bit button.
   */
  function cascadeTo(targetStep, { focusBit = false } = {}) {
    const count = length();
    if (!count) return;
    const clamped = Math.max(0, Math.min(count - 1, targetStep));
    const start = current ?? 0;
    stop();

    if (Math.abs(clamped - start) <= 1 || reducedMotion.matches) {
      current = clamped;
      allRows = false;
      const focused = render();
      if (focusBit) focused?.focus({ preventScroll: true });
      return;
    }

    const hops = [];
    const distance = Math.abs(clamped - start);
    const direction = clamped > start ? 1 : -1;
    if (distance <= MAX_CASCADE_HOPS) {
      for (let s = start + direction; direction > 0 ? s <= clamped : s >= clamped; s += direction) {
        hops.push(s);
      }
    } else {
      for (let k = 1; k < MAX_CASCADE_HOPS; k += 1) {
        const hop = Math.round(start + ((clamped - start) * k) / MAX_CASCADE_HOPS);
        if (hops.at(-1) !== hop && hop !== start && hop !== clamped) hops.push(hop);
      }
      hops.push(clamped);
    }

    cascadeTarget = clamped;
    function stepHop() {
      const nextStep = hops.shift();
      if (nextStep === undefined) {
        cascadeTimer = null;
        cascadeTarget = null;
        return;
      }
      current = nextStep;
      allRows = false;
      const focused = render();
      if (focusBit) focused?.focus({ preventScroll: true });
      if (hops.length) {
        cascadeTimer = setTimeout(stepHop, CASCADE_STEP_MS);
      } else {
        cascadeTimer = null;
        cascadeTarget = null;
      }
    }
    stepHop();
  }

  /**
   * Jump (with sequential cascade when > 1 step away) to a specific multiplier-bit index
   * and keep focus on its bit button.
   *
   * @param {number} step - Zero-based step index.
   */
  function selectBit(step) {
    cascadeTo(step, { focusBit: true });
  }

  /**
   * Switch between the three layout modes (`"step"`, `"grid"`, `"table"`),
   * auto-maximizing `#trace-panel` when `"grid"` (`All steps grid`) is activated.
   *
   * @param {"step" | "grid" | "table"} nextMode - Target layout mode.
   * @param {boolean} [revealAll] - Whether to reveal all steps (`true` for grid/table by default).
   */
  function setLayoutMode(nextMode, revealAll = nextMode !== "step") {
    stop();
    layoutMode = nextMode;
    allRows = revealAll;
    if (nextMode !== "step") comparePrev = false;
    if (!allRows && current === null) current = 0;
    setMaximized(nextMode === "grid");
    render();
  }

  narrowScreen.addEventListener("change", event => {
    if (trace && length()) setLayoutMode(event.matches ? "step" : (traceDegree() > 8 ? "step" : "table"));
  });

  /**
   * Load a new trace payload into the viewer and rebuild the uncluttered 2-row toolbar.
   *
   * Defaults to `"step"` (`Step view`) on narrow screens (`max-width: 600px`) or large
   * cryptographic fields (`m > 8`), and `"table"` (`Classic table`) on desktop for `m <= 8`.
   *
   * @param {object | null} newTrace - Trace dictionary from the API, or `null` to hide panel.
   * @param {object | null} [newReductions] - Optional map of pre-reduced operands `{a?, b?}`.
   */
  function show(newTrace, newReductions) {
    stop();
    setMaximized(false);
    trace = newTrace;
    reductions = newReductions;
    const deg = traceDegree();
    const defaultStepMode = (narrowScreen.matches || deg > 8) && length() > 0;
    layoutMode = defaultStepMode ? "step" : "table";
    compactValues = deg > 8;
    comparePrev = false;
    allRows = !defaultStepMode;
    current = defaultStepMode ? 0 : null;
    panel.hidden = !trace;
    tools.replaceChildren();
    stepLabel = scrubber = firstButton = prevButton = firstChangedButton = playButton = nextButton = lastButton = undefined;
    exitMaxButton = compactToggleButton = compareToggleButton = modesIndicator = undefined;
    modePills = {};
    if (!trace) { renderBody(); return; }

    const count = length();
    if (!count) { renderBody(); return; }

    const row1 = element("div", undefined, "trace-toolbar-row trace-view-row");
    const row2 = element("div", undefined, "trace-toolbar-row trace-playback-row");

    // Row 1.1: Attach Hex/Binary/Polynomial notation switcher whenever Table 4.7 is shown.
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
      row1.append(select);
    }

    // Row 1.2: Gliding three-mode layout switcher pills: Step view | All steps grid | Classic table
    const modeSegments = element("div", undefined, "segments trace-modes");
    modeSegments.setAttribute("role", "group");
    modeSegments.setAttribute("aria-label", "Trace layout mode");
    for (const [modeKey, label] of [
      ["step", "Step view"],
      ["grid", "All steps grid"],
      ["table", "Classic table"],
    ]) {
      const btn = element("button", label);
      btn.type = "button";
      btn.setAttribute("aria-pressed", String(layoutMode === modeKey));
      btn.addEventListener("click", () => setLayoutMode(modeKey));
      modePills[modeKey] = btn;
      modeSegments.append(btn);
    }
    modesIndicator = attachSlidingIndicator(modeSegments, '[aria-pressed="true"]');
    row1.append(modeSegments);

    // Row 1.3: Compare prev → curr, Compact values / Full m-bit toggle, Expand full view, Exit maximized view
    compareToggleButton = element("button", "Compare prev → curr", "outline trace-compare-toggle");
    compareToggleButton.type = "button";
    compareToggleButton.setAttribute("aria-pressed", "false");
    compareToggleButton.addEventListener("click", () => {
      stop();
      setMaximized(false);
      if (layoutMode !== "step") {
        layoutMode = "step";
        allRows = false;
        if (current === null) current = 0;
        comparePrev = true;
      } else {
        comparePrev = !comparePrev;
      }
      render();
    });

    compactToggleButton = element("button", compactValues ? "Full m-bit" : "Compact values", "outline trace-compact-toggle");
    compactToggleButton.type = "button";
    compactToggleButton.setAttribute("aria-pressed", String(compactValues));
    compactToggleButton.addEventListener("click", () => {
      compactValues = !compactValues;
      render();
    });

    const expandButton = element("button", "Expand full view", "outline trace-expand-btn");
    expandButton.type = "button";
    expandButton.addEventListener("click", () => openFullViewModal());

    exitMaxButton = element("button", "Exit maximized view", "outline trace-exit-max-btn");
    exitMaxButton.type = "button";
    exitMaxButton.hidden = true;
    exitMaxButton.addEventListener("click", () => {
      setMaximized(false);
      modesIndicator?.update();
    });

    row1.append(compareToggleButton, compactToggleButton, expandButton, exitMaxButton);

    // Row 2: 5-Button Playback Bar + Interactive Step Scrubber + Progress Counter
    stepLabel = element("span", undefined, "trace-progress");
    stepLabel.setAttribute("aria-live", "polite");

    function advance(next) {
      current = Math.max(0, Math.min(count - 1, next));
      allRows = false;
      render();
    }

    firstButton = element("button", "First step", "quiet");
    firstButton.type = "button";
    firstButton.addEventListener("click", () => {
      if ((cascadeTarget ?? current ?? 0) <= 0) return;
      stop();
      advance(0);
    });

    prevButton = element("button", "Previous", "quiet");
    prevButton.type = "button";
    prevButton.setAttribute("aria-label", "Previous step");
    prevButton.title = "Previous step";
    prevButton.addEventListener("click", () => {
      const baseIdx = cascadeTarget ?? (current ?? 0);
      if (baseIdx <= 0) return;
      stop();
      advance(baseIdx - 1);
    });

    firstChangedButton = element("button", "First changed bit", "outline trace-first-changed-btn");
    firstChangedButton.type = "button";
    firstChangedButton.addEventListener("click", () => {
      const targetIdx = findFirstChangedStep(trace);
      if (targetIdx === null || (current ?? 0) === targetIdx) return;
      stop();
      current = targetIdx;
      allRows = false;
      render();
    });

    playButton = element("button", "Play animation", "quiet");
    playButton.type = "button";
    playButton.setAttribute("aria-pressed", "false");

    const speedSelect = element("select", undefined, "trace-speed");
    speedSelect.setAttribute("aria-label", "Trace animation speed");
    for (const [val, label] of [["slow", "Slow"], ["normal", "Normal"], ["fast", "Fast"]]) {
      const opt = element("option", label);
      opt.value = val;
      if (val === speed) opt.selected = true;
      speedSelect.append(opt);
    }

    function startPlayback() {
      if (count <= 1) return;
      if (timer) {
        stop();
        return;
      }
      stopCascade();
      if (current === null || current >= count - 1) advance(0);
      else {
        allRows = false;
        render();
      }
      playButton.textContent = "Pause";
      playButton.setAttribute("aria-pressed", "true");
      const intervalMs = PLAY_SPEED_MS[speed] || PLAY_SPEED_MS.normal;
      timer = setInterval(() => {
        if (current >= count - 1) stop();
        else advance((current ?? 0) + 1);
      }, intervalMs);
    }

    playButton.addEventListener("click", () => startPlayback());
    speedSelect.addEventListener("change", () => {
      speed = speedSelect.value;
      if (timer) {
        stop();
        startPlayback();
      }
    });

    nextButton = element("button", "Next", "quiet");
    nextButton.type = "button";
    nextButton.setAttribute("aria-label", "Next step");
    nextButton.title = "Next step";
    nextButton.addEventListener("click", () => {
      const baseIdx = cascadeTarget ?? current;
      if (baseIdx === null) {
        stop();
        advance(0);
        return;
      }
      if (baseIdx >= count - 1) return;
      stop();
      advance(baseIdx + 1);
    });

    lastButton = element("button", "Last step", "quiet");
    lastButton.type = "button";
    lastButton.addEventListener("click", () => {
      if (current !== null && (cascadeTarget ?? current) >= count - 1) return;
      stop();
      advance(count - 1);
    });

    scrubber = element("input", undefined, "trace-scrubber");
    scrubber.type = "range";
    scrubber.min = "1";
    scrubber.max = String(Math.max(1, count));
    scrubber.value = String((current ?? 0) + 1);
    scrubber.setAttribute("aria-label", "Trace step scrubber");
    scrubber.addEventListener("input", () => {
      cascadeTo(Number(scrubber.value) - 1);
    });

    row2.append(
      firstButton,
      prevButton,
      firstChangedButton,
      playButton,
      speedSelect,
      nextButton,
      lastButton,
      scrubber,
      stepLabel,
    );
    tools.append(row1, row2);
    render();
  }

  // Enforce step-boundary keyboard no-ops across the trace panel toolbar and cards.
  panel.addEventListener("keydown", event => {
    const count = length();
    if (!count || panel.hidden) return;
    const active = document.activeElement;
    if (active?.closest(".multiplier-bits")) return;
    const tag = active?.tagName;
    if (tag === "INPUT" || tag === "SELECT" || tag === "TEXTAREA") return;
    const activeStep = cascadeTarget ?? (current ?? 0);
    if (event.key === "ArrowLeft") {
      if (activeStep <= 0) return;
      event.preventDefault();
      stop();
      current = activeStep - 1;
      allRows = false;
      render();
    } else if (event.key === "Home") {
      if (activeStep <= 0) return;
      event.preventDefault();
      stop();
      current = 0;
      allRows = false;
      render();
    } else if (event.key === "ArrowRight") {
      if (current !== null && activeStep >= count - 1) return;
      event.preventDefault();
      stop();
      current = current === null ? 0 : activeStep + 1;
      allRows = false;
      render();
    } else if (event.key === "End") {
      if (current !== null && activeStep >= count - 1) return;
      event.preventDefault();
      stop();
      current = count - 1;
      allRows = false;
      render();
    }
  });

  return { show };
}
