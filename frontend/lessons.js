/**
 * @fileoverview Standalone interactive & animated Lessons page controller (#lessons)
 * with Previous-to-Current visual diff tracking, true `<sup>`/`<sub>` typography,
 * gliding sub-lesson/timeline indicators, sequential step cascade, and slide comparison.
 *
 * Original Author: Ali Zahreddine - Milestone 6 (Waves 1-4).
 *
 * Renders the 7-lesson curriculum from `frontend/lesson-data.js` inside the dedicated
 * `[data-lab-view="lessons"]` view:
 *   - Lesson Selector Hub with symbol badges, step counts, and completion tracking
 *   - Sub-lesson switcher pills with gliding active selection highlight
 *   - 5-Button Playback Bar (`First step`, `Previous`, `Play animation`/`Pause` with
 *     `Slow`/`Normal`/`Fast` speed control, `Next`, `Last step`), clickable gliding step
 *     dots with sequential cascade, and `Compare prev → curr` side-by-side slide toggle
 *   - Persistent color-coded change tracking (`.diff-carried`, `.diff-updated`,
 *     `.diff-reduced`, `.diff-unchanged`), `"From Step k-1 → Step k"` transition banners,
 *     informative `.step-knowledge-title` headings, and inline `was:` / `prev → now` deltas
 *   - Interactive mini-activities (8-bit polynomial builder, XOR bit check, self-check quizzes)
 *   - Keyboard navigation (`ArrowLeft`, `ArrowRight`, `Home`, `End`, `Space`) and one-click
 *     "Open in Calculator" deep-link handoffs.
 */

import { LESSONS } from "./lesson-data.js";
import { attachSlidingIndicator, element, formatOperand, mathElement, polynomial, setMathText } from "./notation.js";
import { createDiffLegend } from "./traces.js";

/** @param {string} id @returns {HTMLElement} */
const $ = id => document.getElementById(id);

const SPEED_MS = { slow: 2200, normal: 1300, fast: 650 };
const LESSON_CASCADE_MS = 140;
const MAX_LESSON_HOPS = 12;

/**
 * Determine whether bit column `colIdx` was highlighted in a `xor-columns` visual payload.
 *
 * @param {object | null | undefined} visual - `xor-columns` visual descriptor.
 * @param {number} colIdx - Zero-based column index.
 * @returns {boolean} True if column `colIdx` is active/highlighted.
 */
function isXorColHighlighted(visual, colIdx) {
  if (!visual || visual.type !== "xor-columns") return false;
  const inRange = visual.highlightRange && colIdx >= visual.highlightRange[0] && colIdx <= visual.highlightRange[1];
  return Boolean(colIdx === visual.activeCol || inRange);
}

/**
 * Render the custom visual payload for a lesson step with true `<sup>`/`<sub>` math typography,
 * automatic Previous-to-Current value-level diff highlights, and zero horizontal scrolling.
 *
 * @param {object} visual - Step visual specification from `LESSONS`.
 * @param {object | null} [prevVisual=null] - Previous step's visual payload for automatic diffing.
 * @returns {HTMLElement} Populated visual stage DOM node.
 */
function renderVisual(visual, prevVisual = null) {
  const container = element("div", undefined, "lesson-visual");
  if (!visual) return container;

  if (visual.type === "cards") {
    const prevTitles = new Set(
      prevVisual?.type === "cards" ? prevVisual.items.map(item => item.title) : [],
    );
    const grid = element("div", undefined, "lesson-card-grid");
    for (const item of visual.items) {
      const isNew = prevVisual?.type === "cards" && !prevTitles.has(item.title);
      const card = element(
        "article",
        undefined,
        "lesson-concept-card" + (isNew ? " diff-updated" : ""),
      );
      const badgeRow = element("div", undefined, "diff-cell-head");
      badgeRow.append(mathElement("span", item.badge, "lesson-badge"));
      if (isNew) badgeRow.append(element("span", "New", "diff-tag diff-updated"));
      card.append(
        badgeRow,
        mathElement("h4", item.title),
        mathElement("p", item.detail),
      );
      grid.append(card);
    }
    container.append(grid);
  }

  if (visual.type === "xor-columns") {
    const wrap = element("div", undefined, "lesson-xor-stage");
    const width = visual.aBits.length;
    const grid = element("div", undefined, "lesson-bit-grid");
    grid.style.setProperty("--bit-cols", String(width));

    const headerRow = element("div", undefined, "lesson-bit-row lesson-bit-header");
    headerRow.append(element("span", "Power", "lesson-row-label"));
    for (let i = 0; i < width; i += 1) {
      const exp = width - 1 - i;
      headerRow.append(mathElement("span", exp === 0 ? "1" : "x^" + exp, "lesson-bit-exp"));
    }
    grid.append(headerRow);

    const outBits = [];
    for (let i = 0; i < width; i += 1) {
      outBits.push(String(Number(visual.aBits[i]) ^ Number(visual.bBits[i])));
    }
    const prevOutBits = prevVisual?.type === "xor-columns" && prevVisual.aBits.length === width
      ? Array.from({ length: width }, (_, i) => String(Number(prevVisual.aBits[i]) ^ Number(prevVisual.bBits[i])))
      : null;

    for (const [label, bits, rowKind] of [
      [visual.aLabel, visual.aBits, "a"],
      [visual.bLabel, visual.bBits, "b"],
      [visual.outLabel, outBits.join(""), "out"],
    ]) {
      const row = element("div", undefined, "lesson-bit-row" + (rowKind === "out" ? " is-result" : ""));
      row.append(mathElement("span", label, "lesson-row-label"));
      for (let i = 0; i < width; i += 1) {
        const isActive = isXorColHighlighted(visual, i);
        const wasActive = isXorColHighlighted(prevVisual, i);
        const cancels = visual.aBits[i] === "1" && visual.bBits[i] === "1";
        let cls = "lesson-bit-tile";
        if (isActive) cls += " is-active";
        if (bits[i] === "1") cls += " is-one";

        if (rowKind === "out") {
          const resultChanged = prevOutBits ? prevOutBits[i] !== bits[i] : false;
          if (isActive && cancels) cls += " is-cancel diff-reduced";
          else if ((isActive && bits[i] === "1") || resultChanged) cls += " diff-updated";
          else if (wasActive && !isActive) cls += " diff-carried";
          else cls += " diff-unchanged";
        } else {
          const prevBits = rowKind === "a" ? prevVisual?.aBits : prevVisual?.bBits;
          if (prevBits && prevBits.length === width && prevBits[i] !== bits[i]) {
            cls += " diff-updated";
          } else if (isActive && cancels) {
            cls += " is-cancel diff-reduced";
          } else if (isActive && bits[i] === "1") {
            cls += " diff-carried";
          } else {
            cls += " diff-unchanged";
          }
        }
        row.append(element("span", bits[i], cls));
      }
      grid.append(row);
    }

    // Micro-badge row showing accessible text status beneath every active column (never color alone).
    const tagRow = element("div", undefined, "lesson-bit-diff-row");
    tagRow.append(element("span", "Diff", "lesson-row-label"));
    for (let i = 0; i < width; i += 1) {
      const isActive = isXorColHighlighted(visual, i);
      const cancels = visual.aBits[i] === "1" && visual.bBits[i] === "1";
      if (isActive && cancels) {
        tagRow.append(element("span", "1⊕1→0", "lesson-bit-diff-tag diff-reduced"));
      } else if (isActive && outBits[i] === "1") {
        tagRow.append(element("span", "Set 1", "lesson-bit-diff-tag diff-updated"));
      } else if (isActive) {
        tagRow.append(element("span", "0", "lesson-bit-diff-tag diff-unchanged"));
      } else {
        tagRow.append(element("span", "·", "lesson-bit-diff-tag diff-unchanged"));
      }
    }
    grid.append(tagRow);

    wrap.append(grid);
    if (visual.note) wrap.append(mathElement("p", visual.note, "lesson-visual-note"));
    container.append(wrap);
  }

  if (visual.type === "reduction-step") {
    const box = element("div", undefined, "lesson-reduction-stage");
    const prevInputChanged = prevVisual?.type === "reduction-step" && prevVisual.beforeHex !== visual.beforeHex;
    const rows = [
      {
        label: "Dividend / Remainder",
        hex: "{" + visual.beforeHex + "}",
        bits: visual.beforeBits,
        poly: visual.beforePoly,
        diffClass: "diff-reduced",
        badge: "Cancel x^" + visual.d,
        prevText: prevInputChanged ? "prev input: {" + prevVisual.beforeHex + "}" : undefined,
      },
      {
        label: "Shifted m(x) << " + visual.shift,
        hex: "{" + visual.reducerHex + "}",
        bits: visual.reducerBits,
        poly: visual.reducerPoly,
        diffClass: "diff-carried",
        badge: "Shifted m(x)",
      },
      {
        label: "After XOR (deg < " + visual.m + ")",
        hex: "{" + visual.afterHex + "}",
        bits: visual.afterBits,
        poly: visual.afterPoly,
        diffClass: "diff-updated",
        badge: visual.stage === "xor" ? "Reduced" : "Target Remainder",
        prevText: "was: {" + visual.beforeHex + "} → now: {" + visual.afterHex + "}",
      },
    ];
    for (const r of rows) {
      const card = element("div", undefined, "lesson-reduce-row " + r.diffClass);
      const head = element("div", undefined, "diff-cell-head");
      head.append(
        mathElement("span", r.label, "lesson-badge"),
        mathElement("span", r.badge, "diff-tag " + r.diffClass),
      );
      card.append(head, mathElement("strong", r.hex + " · " + r.bits), mathElement("code", r.poly));
      if (r.prevText) card.append(mathElement("span", r.prevText, "diff-prev-value"));
      box.append(card);
    }
    container.append(box);
  }

  if (visual.type === "shift-register") {
    const box = element("div", undefined, "lesson-register-stage");
    const flow = element("div", undefined, "lesson-register-flow");
    const prevReg = prevVisual?.type === "shift-register" ? prevVisual : null;

    const inputChanged = prevReg && prevReg.inputHex !== visual.inputHex;
    const step1 = element("div", undefined, "lesson-concept-card " + (inputChanged ? "diff-updated" : "diff-unchanged"));
    const h1 = element("div", undefined, "diff-cell-head");
    h1.append(
      element("span", "1 · Input Register", "lesson-badge"),
      element("span", inputChanged ? "New input" : "Input", "diff-tag " + (inputChanged ? "diff-updated" : "diff-unchanged")),
    );
    step1.append(
      h1,
      mathElement("h4", "{" + visual.inputHex + "} = " + visual.inputBits + "₂"),
      mathElement("p", "Inspect MSB bit b7 = " + visual.msb),
    );
    if (inputChanged) step1.append(mathElement("span", "was: {" + prevReg.inputHex + "} (b7 = " + prevReg.msb + ")", "diff-prev-value"));

    const shiftClass = visual.msb ? "diff-reduced" : "diff-carried";
    const step2 = element("div", undefined, "lesson-concept-card " + shiftClass + (visual.msb ? " is-overflow" : ""));
    const h2 = element("div", undefined, "diff-cell-head");
    h2.append(
      element("span", "2 · Shift Left << 1", "lesson-badge"),
      mathElement("span", visual.msb ? "Overflow x^8 = 1" : "Shifted left", "diff-tag " + shiftClass),
    );
    step2.append(
      h2,
      mathElement("h4", visual.shiftedBits + "₂"),
      mathElement("p", visual.msb ? "Overflow x^8 = 1 popped out!" : "No overflow (b7 was 0)"),
      mathElement("span", "prev: " + visual.inputBits + "₂ → shifted: " + visual.shiftedBits + "₂", "diff-prev-value"),
    );

    const step3 = element("div", undefined, "lesson-concept-card is-highlight diff-updated");
    const h3 = element("div", undefined, "diff-cell-head");
    h3.append(
      element("span", visual.reduced ? "3 · XOR Low Terms {" + visual.modLowHex + "}" : "3 · Reduced Output", "lesson-badge"),
      element("span", visual.reduced ? "Reduced ⊕ {" + visual.modLowHex + "}" : "Updated output", "diff-tag diff-updated"),
    );
    step3.append(
      h3,
      mathElement("h4", "{" + visual.outputHex + "} = " + visual.outputBits + "₂"),
      mathElement("p", visual.note),
      element("span", "prev: {" + visual.inputHex + "} → now: {" + visual.outputHex + "}", "diff-prev-value"),
    );
    flow.append(step1, step2, step3);
    box.append(flow);
    container.append(box);
  }

  if (visual.type === "mul-walkthrough") {
    const wrap = element("div", undefined, "lesson-mul-stage");
    const grid = element("div", undefined, "lesson-mul-grid");
    const prevActiveI = prevVisual?.type === "mul-walkthrough" ? prevVisual.activeI : -1;
    visual.rows.forEach((row, idx) => {
      const prevRow = idx > 0 ? visual.rows[idx - 1] : null;
      const prevAcc = prevRow ? prevRow.acc : "00";
      const shiftClass = row.reduced ? "diff-reduced" : row.i > 0 ? "diff-carried" : "diff-unchanged";
      const accClass = row.bit ? "diff-updated" : "diff-unchanged";
      const card = element(
        "div",
        undefined,
        "lesson-mul-row" +
          (row.i === visual.activeI ? " is-current " + (row.bit ? "diff-updated" : shiftClass) : "") +
          (row.i === prevActiveI && prevActiveI !== visual.activeI ? " diff-prev-row" : "") +
          (row.bit === 1 ? " is-selected" : ""),
      );
      const top = element("div", undefined, "diff-cell-head");
      top.append(
        element("span", "i = " + row.i + " · bit = " + row.bit, "lesson-badge"),
        mathElement(
          "span",
          row.reduced ? "Shifted + Reduced ⊕ m(x)" : row.i > 0 ? "Shifted left" : "Init A",
          "diff-tag " + shiftClass,
        ),
        element(
          "span",
          row.bit ? "XOR'd (bit = 1)" : "Unchanged (bit = 0)",
          "diff-tag " + accClass,
        ),
      );
      const prevPartialNote = prevRow ? "prev: {" + prevRow.partial + "} → now: {" + row.partial + "}" : "initial: {" + row.partial + "}";
      const accText = row.bit
        ? "Acc: {" + prevAcc + "} ⊕ {" + row.partial + "} → {" + row.acc + "}"
        : "Acc unchanged: {" + row.acc + "}";
      card.append(
        top,
        mathElement("strong", "x^" + row.i + "·A = {" + row.partial + "} (" + prevPartialNote + ")"),
        element("span", accText),
      );
      grid.append(card);
    });
    wrap.append(grid);
    if (visual.note) wrap.append(mathElement("p", visual.note, "lesson-visual-note"));
    container.append(wrap);
  }

  if (visual.type === "poly-divmod") {
    const box = element("div", undefined, "lesson-divmod-stage");
    const items = [
      ["Dividend A3(x)", visual.dividend, "diff-unchanged", "Dividend", undefined],
      ["Divisor B3(x)", visual.divisor, "diff-unchanged", "Divisor", undefined],
      ["Quotient Q(x) = A3 div B3", visual.quotient, "diff-updated", "New Quotient", undefined],
      ["Aligned Q(x) · B3(x)", visual.shiftedDivisor, "diff-carried", "Shifted Divisor", undefined],
      ["Remainder R(x) = A3 ⊕ Q·B3", visual.remainder, "diff-reduced", "Leading term cancelled", "was: " + visual.dividend],
    ];
    const dl = element("dl", undefined, "equivalents lesson-divmod-list");
    for (const [dt, val, diffClass, badge, prevText] of items) {
      const dd = element("dd", undefined, "diff-cell-box " + diffClass);
      const head = element("div", undefined, "diff-cell-head");
      head.append(
        mathElement("span", val, "diff-cell-val"),
        element("span", badge, "diff-tag " + diffClass),
      );
      dd.append(head);
      if (prevText) dd.append(mathElement("span", prevText, "diff-prev-value"));
      dl.append(mathElement("dt", dt), dd);
    }
    box.append(dl, mathElement("p", visual.note, "lesson-visual-note"));
    container.append(box);
  }

  if (visual.type === "euclid-step") {
    const prevEuclid = prevVisual?.type === "euclid-step" ? prevVisual : null;
    const square = element("div", undefined, "euclid-inspector-square");
    const head = element("div", undefined, "euclid-inspector-head");
    head.append(
      element("span", "Table 4.7 · Step " + visual.step, "lesson-badge"),
      mathElement("span", "Quotient Q(x) = " + visual.q, "euclid-q-badge"),
      mathElement("code", visual.formula, "euclid-formula-pill"),
    );
    const triples = element("div", undefined, "euclid-triples-grid");

    // Triple A: carried from previous B
    const cardA = element("div", undefined, "euclid-triple-card is-carried");
    const headA = mathElement("h4", "Triple A(x) ");
    headA.append(mathElement("small", visual.step > 0 ? "A ← prev B" : "Modulus m(x)"));
    const dlA = element("dl", undefined, "equivalents");
    for (const [k, v] of Object.entries(visual.a)) {
      const prevVal = prevEuclid?.a?.[k];
      const changed = Boolean(prevVal && prevVal !== v);
      const diffClass = visual.step === 0 ? "diff-unchanged" : changed ? "diff-carried" : "diff-unchanged";
      const badge = visual.step === 0 ? "Init" : changed ? "← prev B" + k[1] : "Unchanged";
      const dd = element("dd", undefined, "diff-cell-box " + diffClass);
      const cellHead = element("div", undefined, "diff-cell-head");
      cellHead.append(mathElement("span", v, "diff-cell-val"), mathElement("span", badge, "diff-tag " + diffClass));
      dd.append(cellHead);
      if (changed) dd.append(mathElement("span", "was: " + prevVal, "diff-prev-value"));
      dlA.append(mathElement("dt", k + "(x)"), dd);
    }
    cardA.append(headA, dlA);

    // Triple B: newly computed T = A ⊕ Q·B
    const cardB = element(
      "div",
      undefined,
      "euclid-triple-card is-updated" + (visual.status === "success" ? " is-inverse-found" : ""),
    );
    const headB = mathElement("h4", "Triple B(x) ");
    headB.append(mathElement("small", visual.step > 0 ? "B ← A ⊕ Q·B" : "Operand b(x)"));
    const dlB = element("dl", undefined, "equivalents");
    for (const [k, v] of Object.entries(visual.b)) {
      const prevVal = prevEuclid?.b?.[k];
      const changed = Boolean(prevVal && prevVal !== v);
      const isInverse = visual.status === "success" && k === "B2";
      const diffClass = visual.step === 0 ? "diff-unchanged" : (changed || isInverse) ? "diff-updated" : "diff-unchanged";
      const badge = visual.step === 0 ? "Init" : isInverse ? "Inverse Found" : changed ? "New T" + k[1] : "Unchanged";
      const dd = element("dd", undefined, "diff-cell-box " + diffClass + (isInverse ? " picked" : ""));
      const cellHead = element("div", undefined, "diff-cell-head");
      cellHead.append(mathElement("span", v, "diff-cell-val"), mathElement("span", badge, "diff-tag " + diffClass));
      dd.append(cellHead);
      if (changed) dd.append(mathElement("span", "was: " + prevVal, "diff-prev-value"));
      dlB.append(mathElement("dt", k + "(x)"), dd);
    }
    cardB.append(headB, dlB);

    triples.append(cardA, cardB);
    square.append(head, triples);
    container.append(square);
  }

  if (visual.type === "pipeline") {
    const prevActiveStage = prevVisual?.type === "pipeline" ? prevVisual.activeStage : 0;
    const grid = element("div", undefined, "lesson-card-grid");
    visual.stages.forEach((item, idx) => {
      const stageNum = idx + 1;
      const isCurrent = stageNum === visual.activeStage;
      const isCompleted = stageNum < visual.activeStage;
      const diffClass = isCurrent ? "diff-updated" : isCompleted ? "diff-carried" : "diff-unchanged";
      const badge = isCurrent ? "Active Stage" : isCompleted ? "Completed" : "Pending";
      const card = element(
        "article",
        undefined,
        "lesson-concept-card " + diffClass + (isCurrent ? " is-highlight" : ""),
      );
      const head = element("div", undefined, "diff-cell-head");
      head.append(element("span", item.stage, "lesson-badge"), element("span", badge, "diff-tag " + diffClass));
      card.append(head, mathElement("h4", item.title), mathElement("p", item.detail));
      if (isCurrent && prevActiveStage > 0 && prevActiveStage < stageNum) {
        card.append(element("span", "was: Pending → now active", "diff-prev-value"));
      }
      grid.append(card);
    });
    container.append(grid);
  }

  return container;
}

/**
 * Build the interactive 8-bit polynomial sandbox for Lesson 1.1 with true `<sup>` labels.
 *
 * @returns {HTMLElement} Interactive bit-builder widget.
 */
function buildBitSandbox() {
  let mask = 0x57n;
  const box = element("section", undefined, "lesson-activity");
  box.append(element("h4", "Interactive 8-Bit Polynomial Sandbox"));
  const bitsRow = element("div", undefined, "bit-builder lesson-sandbox-bits");
  const readout = element("div", undefined, "lesson-sandbox-readout");

  function update() {
    bitsRow.replaceChildren();
    for (let bit = 7; bit >= 0; bit -= 1) {
      const toggle = element("input");
      toggle.type = "checkbox";
      toggle.checked = Boolean(mask & (1n << BigInt(bit)));
      toggle.setAttribute("aria-label", "Sandbox bit x^" + bit);
      toggle.addEventListener("change", () => {
        mask ^= 1n << BigInt(bit);
        update();
      });
      const label = element("label");
      label.append(toggle, mathElement("span", bit === 0 ? "1" : "x^" + bit));
      bitsRow.append(label);
    }
    readout.replaceChildren(
      element("span", "Hex: {" + formatOperand(mask, "hex", 8) + "}"),
      element("span", "Binary: " + formatOperand(mask, "binary", 8)),
      mathElement("span", "Polynomial: " + polynomial(mask)),
    );
  }
  update();
  box.append(bitsRow, readout);
  return box;
}

/**
 * Build the interactive 4-bit XOR challenge widget for Lesson 2.3.
 *
 * @returns {HTMLElement} Interactive XOR check widget.
 */
function buildXorActivity() {
  const a = [1, 0, 1, 1];
  const b = [0, 1, 1, 1];
  const user = [0, 0, 0, 0];
  const box = element("section", undefined, "lesson-activity");
  box.append(mathElement("h4", "Interactive 4-Bit XOR Check: Click each result bit to compute 1011₂ ⊕ 0111₂"));
  const buttons = element("div", undefined, "lesson-xor-buttons");
  const feedback = element("p", "Toggle the 4 output bits until every column satisfies A ⊕ B.", "meta");

  function render() {
    buttons.replaceChildren();
    let allCorrect = true;
    for (let i = 0; i < 4; i += 1) {
      const expected = a[i] ^ b[i];
      if (user[i] !== expected) allCorrect = false;
      const btn = mathElement(
        "button",
        "x^" + (3 - i) + ": " + a[i] + " ⊕ " + b[i] + " = " + user[i],
        "outline" + (user[i] === expected ? " is-correct-bit" : ""),
      );
      btn.type = "button";
      btn.addEventListener("click", () => {
        user[i] ^= 1;
        render();
      });
      buttons.append(btn);
    }
    if (allCorrect) {
      setMathText(feedback, "Correct! 1011₂ ⊕ 0111₂ = 1100₂ (x^3 + x^2), because x and 1 both canceled via 1 ⊕ 1 = 0.");
    } else {
      feedback.textContent = "Click the buttons above to toggle each output bit between 0 and 1.";
    }
  }
  render();
  box.append(buttons, feedback);
  return box;
}

/**
 * Build an instant-feedback multiple-choice check card for a sub-lesson.
 *
 * @param {{question: string, options: Array<{text: string, correct: boolean}>}} quiz - Quiz config.
 * @returns {HTMLElement} Rendered self-check quiz section.
 */
function buildQuiz(quiz) {
  const box = element("section", undefined, "lesson-activity lesson-quiz");
  box.append(element("h4", "Quick Self-Check"), mathElement("p", quiz.question));
  const choices = element("div", undefined, "lesson-quiz-choices");
  const status = element("p", "", "lesson-quiz-feedback");
  status.hidden = true;

  for (const option of quiz.options) {
    const btn = mathElement("button", option.text, "outline lesson-quiz-option");
    btn.type = "button";
    btn.addEventListener("click", () => {
      status.hidden = false;
      status.className = "lesson-quiz-feedback " + (option.correct ? "is-correct" : "is-wrong");
      setMathText(
        status,
        option.correct
          ? "Correct! " + option.text
          : "Not quite: review the step formula above and try the other choice.",
      );
    });
    choices.append(btn);
  }
  box.append(choices, status);
  return box;
}

/**
 * Build one complete lesson step frame (header with prominent `.step-knowledge-title`,
 * optional `"From Step k-1 → Step k"` transition banner, diff-aware visual stage, and activities).
 *
 * @param {object} sub - Active sub-lesson object.
 * @param {Array<object>} steps - Step array for `sub`.
 * @param {number} idx - Zero-based step index to render.
 * @param {boolean} [isPreviousSnapshot=false] - True when rendering the compact read-only previous slide.
 * @returns {HTMLElement} Populated `<article class="lesson-step-frame">`.
 */
function buildLessonStepFrame(sub, steps, idx, isPreviousSnapshot = false) {
  const step = steps[idx];
  const prevStep = idx > 0 ? steps[idx - 1] : null;
  const frame = element("article", undefined, "lesson-step-frame");
  const header = element("header", undefined, "lesson-step-header");
  header.append(
    mathElement("span", sub.title + " · Step " + (idx + 1) + " / " + steps.length, "lesson-badge"),
    mathElement("h3", step.title, "step-knowledge-title"),
    mathElement("code", step.formula, "lesson-formula-banner"),
    mathElement("p", step.explanation, "lesson-step-explanation"),
  );
  frame.append(header);

  if (!isPreviousSnapshot && prevStep) {
    const changeSummary = step.diffSummary || ("Transitioned from \"" + prevStep.title + "\" to \"" + step.title + "\".");
    frame.append(
      mathElement("p", "From Step " + idx + " → Step " + (idx + 1) + ": " + changeSummary, "diff-banner lesson-diff-banner"),
    );
  }

  frame.append(renderVisual(step.visual, isPreviousSnapshot ? null : prevStep?.visual ?? null));

  if (!isPreviousSnapshot) {
    if (sub.activity === "bit-sandbox") frame.append(buildBitSandbox());
    if (sub.activity === "xor-check") frame.append(buildXorActivity());
    if (sub.quiz) frame.append(buildQuiz(sub.quiz));
  }
  return frame;
}

/**
 * Initialize the standalone `#lessons` page, catalog cards, gliding sub-lesson and timeline pills,
 * 5-button stepper with sequential cascade on timeline jumps, `Compare prev → curr`, and Calculator handoff.
 *
 * @param {{openInCalculator: (preset: {m: number, operation: string, base: string, a: string, b: string}) => void}} hooks - Integration callbacks.
 * @returns {{selectLessonById: (id?: string) => void}} Controller handle for hash navigation.
 */
export function setupLessons({ openInCalculator }) {
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  const catalogEl = $("lesson-catalog");
  const subtabsEl = $("lesson-subtabs");
  const stageEl = $("lesson-stage");
  const dotsEl = $("lesson-step-dots");
  const progressEl = $("lesson-step-progress");
  const titleEl = $("lesson-active-title");
  const subtitleEl = $("lesson-active-subtitle");
  const handoffEl = $("lesson-handoff-bar");

  const firstBtn = $("lesson-first");
  const prevBtn = $("lesson-prev");
  const firstActiveBtn = $("lesson-first-active");
  const playBtn = $("lesson-play");
  const nextBtn = $("lesson-next");
  const lastBtn = $("lesson-last");
  const compareBtn = $("lesson-compare");
  const speedSelect = $("lesson-speed");
  const prevLessonBtn = $("lesson-prev-topic");
  const nextLessonBtn = $("lesson-next-topic");

  let lessonIndex = 0;
  let subIndex = 0;
  let stepIndex = 0;
  let comparePrev = false;
  let timer = null;
  let cascadeTimer = null;
  let cascadeTarget = null;
  let renderedSubtabsLesson = -1;
  let renderedDotsKey = "";
  const completedLessons = new Set();

  const subtabsIndicator = attachSlidingIndicator(subtabsEl, ".lesson-subtab.is-active");
  const dotsIndicator = attachSlidingIndicator(dotsEl, ".lesson-step-dot.is-active");

  /** Stop any active cascade timer. */
  function stopCascade() {
    if (cascadeTimer) {
      clearTimeout(cascadeTimer);
      cascadeTimer = null;
    }
    cascadeTarget = null;
  }

  /** Stop any active auto-play interval or cascade timer. */
  function stopPlay() {
    stopCascade();
    if (timer) {
      clearInterval(timer);
      timer = null;
    }
    playBtn.textContent = "Play animation";
    playBtn.setAttribute("aria-pressed", "false");
  }

  /** @returns {object} Active lesson object. */
  const currentLesson = () => LESSONS[lessonIndex];
  /** @returns {object} Active sub-lesson object. */
  const currentSub = () => currentLesson().sublessons[subIndex];
  /** @returns {Array<object>} Step array for active sub-lesson. */
  const currentSteps = () => currentSub().steps;

  /**
   * Sequentially cascade through intermediate slides when jumping across non-adjacent timeline dots.
   *
   * @param {number} targetStep - Zero-based target slide index.
   */
  function cascadeToStep(targetStep) {
    const steps = currentSteps();
    const clamped = Math.max(0, Math.min(steps.length - 1, targetStep));
    const start = stepIndex;
    stopPlay();

    if (Math.abs(clamped - start) <= 1 || reducedMotion.matches) {
      stepIndex = clamped;
      renderWorkspace();
      return;
    }

    const hops = [];
    const distance = Math.abs(clamped - start);
    const dir = clamped > start ? 1 : -1;
    if (distance <= MAX_LESSON_HOPS) {
      for (let s = start + dir; dir > 0 ? s <= clamped : s >= clamped; s += dir) hops.push(s);
    } else {
      for (let k = 1; k < MAX_LESSON_HOPS; k += 1) {
        const hop = Math.round(start + ((clamped - start) * k) / MAX_LESSON_HOPS);
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
      stepIndex = nextStep;
      renderWorkspace();
      if (hops.length) {
        cascadeTimer = setTimeout(stepHop, LESSON_CASCADE_MS);
      } else {
        cascadeTimer = null;
        cascadeTarget = null;
      }
    }
    stepHop();
  }

  /** Render the 7-card Lesson Selector Hub with completion badges and true `<sup>`/`<sub>`. */
  function renderCatalog() {
    catalogEl.replaceChildren();
    LESSONS.forEach((lesson, idx) => {
      const totalSteps = lesson.sublessons.reduce((sum, sub) => sum + sub.steps.length, 0);
      const done = completedLessons.has(lesson.id);
      const card = element(
        "button",
        undefined,
        "lesson-hub-card" + (idx === lessonIndex ? " is-active" : "") + (done ? " is-done" : ""),
      );
      card.type = "button";
      card.setAttribute("aria-pressed", String(idx === lessonIndex));
      card.dataset.lessonId = lesson.id;
      const top = element("div", undefined, "lesson-hub-card-top");
      top.append(
        mathElement("span", lesson.symbol, "lesson-symbol-badge"),
        element("span", "Lesson " + lesson.number + (done ? " · ✓" : ""), "lesson-hub-num"),
      );
      card.append(
        top,
        mathElement("strong", lesson.title, "lesson-hub-title"),
        element("small", lesson.sublessons.length + " sub-lessons · " + totalSteps + " animated steps"),
      );
      card.addEventListener("click", () => {
        stopPlay();
        lessonIndex = idx;
        subIndex = 0;
        stepIndex = 0;
        renderAll();
      });
      catalogEl.append(card);
    });
  }

  /** Render or update active state in place on sub-lesson tabs so the gliding pill animates smoothly. */
  function renderSubtabs() {
    const lesson = currentLesson();
    if (renderedSubtabsLesson !== lessonIndex) {
      renderedSubtabsLesson = lessonIndex;
      subtabsEl.replaceChildren();
      lesson.sublessons.forEach((sub, idx) => {
        const btn = mathElement("button", sub.title, "lesson-subtab" + (idx === subIndex ? " is-active" : ""));
        btn.type = "button";
        btn.setAttribute("aria-pressed", String(idx === subIndex));
        btn.addEventListener("click", () => {
          stopPlay();
          subIndex = idx;
          stepIndex = 0;
          renderWorkspace();
        });
        subtabsEl.append(btn);
      });
    } else {
      const buttons = Array.from(subtabsEl.querySelectorAll(".lesson-subtab"));
      buttons.forEach((btn, idx) => {
        const isActive = idx === subIndex;
        btn.classList.toggle("is-active", isActive);
        btn.setAttribute("aria-pressed", String(isActive));
      });
    }
    subtabsIndicator.update();
  }

  /** Render or update timeline dots in place so the active dot pill glides smoothly across steps. */
  function renderStepDots(steps) {
    const key = lessonIndex + ":" + subIndex;
    if (renderedDotsKey !== key) {
      renderedDotsKey = key;
      dotsEl.replaceChildren();
      steps.forEach((s, idx) => {
        const dot = element(
          "button",
          String(idx + 1),
          "lesson-step-dot" + (idx === stepIndex ? " is-active" : ""),
        );
        dot.type = "button";
        dot.setAttribute("aria-label", "Jump to step " + (idx + 1) + ": " + s.title);
        dot.setAttribute("aria-current", idx === stepIndex ? "step" : "false");
        dot.addEventListener("click", () => cascadeToStep(idx));
        dotsEl.append(dot);
      });
    } else {
      const dotButtons = Array.from(dotsEl.querySelectorAll(".lesson-step-dot"));
      dotButtons.forEach((dot, idx) => {
        const isActive = idx === stepIndex;
        dot.classList.toggle("is-active", isActive);
        dot.setAttribute("aria-current", isActive ? "step" : "false");
      });
    }
    dotsIndicator.update();
  }

  /** Render the active sub-lesson step, optional side-by-side comparison, dots, and handoff bar. */
  function renderWorkspace() {
    const lesson = currentLesson();
    const sub = currentSub();
    const steps = currentSteps();

    if (subIndex === lesson.sublessons.length - 1 && stepIndex === steps.length - 1) {
      completedLessons.add(lesson.id);
    }

    setMathText(titleEl, "Lesson " + lesson.number + " · " + lesson.title);
    setMathText(subtitleEl, sub.summary);
    progressEl.textContent = "Step " + (stepIndex + 1) + " / " + steps.length;

    firstBtn.disabled = stepIndex === 0;
    firstBtn.setAttribute("aria-disabled", String(stepIndex === 0));
    prevBtn.disabled = stepIndex === 0;
    prevBtn.setAttribute("aria-disabled", String(stepIndex === 0));
    nextBtn.disabled = stepIndex >= steps.length - 1;
    nextBtn.setAttribute("aria-disabled", String(stepIndex >= steps.length - 1));
    lastBtn.disabled = stepIndex >= steps.length - 1;
    lastBtn.setAttribute("aria-disabled", String(stepIndex >= steps.length - 1));
    playBtn.disabled = steps.length <= 1;
    playBtn.setAttribute("aria-disabled", String(steps.length <= 1));

    if (firstActiveBtn) {
      const firstActiveIdx = steps.length > 1 ? 1 : null;
      const isBitLesson = ["addition", "subtraction", "multiplication"].includes(lesson.id);
      firstActiveBtn.textContent = isBitLesson ? "First changed bit" : "First active step";
      const tip = firstActiveIdx === null
        ? "Only one step in this sub-lesson"
        : "Jump directly to " + (isBitLesson ? "first changed bit" : "first active step") + " (Step " + (firstActiveIdx + 1) + ")";
      firstActiveBtn.title = tip;
      firstActiveBtn.setAttribute("aria-label", tip);
      const activeDisabled = firstActiveIdx === null || stepIndex === firstActiveIdx;
      firstActiveBtn.disabled = activeDisabled;
      firstActiveBtn.setAttribute("aria-disabled", String(activeDisabled));
    }
    if (compareBtn) {
      compareBtn.setAttribute("aria-pressed", String(comparePrev));
    }

    renderStepDots(steps);

    stageEl.replaceChildren();
    if (steps.length > 1) {
      stageEl.append(createDiffLegend());
    }

    if (comparePrev) {
      const grid = element("div", undefined, "diff-compare-grid");
      const prevPane = element("div", undefined, "diff-compare-pane is-prev");
      prevPane.setAttribute("role", "region");
      prevPane.setAttribute("aria-label", "Previous lesson step");
      prevPane.append(element("div", stepIndex > 0 ? "Previous · Step " + stepIndex : "Previous step", "diff-compare-pane-head"));
      if (stepIndex === 0) {
        prevPane.append(element("div", "Initial step: no previous slide", "diff-empty-prev"));
      } else {
        prevPane.append(buildLessonStepFrame(sub, steps, stepIndex - 1, true));
      }

      const arrow = element("div", "→", "diff-compare-arrow");
      arrow.setAttribute("aria-hidden", "true");

      const currPane = element("div", undefined, "diff-compare-pane is-curr");
      currPane.setAttribute("role", "region");
      currPane.setAttribute("aria-label", "Current lesson step");
      currPane.append(element("div", "Current · Step " + (stepIndex + 1), "diff-compare-pane-head"));
      currPane.append(buildLessonStepFrame(sub, steps, stepIndex, false));

      grid.append(prevPane, arrow, currPane);
      stageEl.append(grid);
    } else {
      stageEl.append(buildLessonStepFrame(sub, steps, stepIndex, false));
    }

    handoffEl.replaceChildren();
    if (lesson.handoff) {
      const tryBtn = mathElement("button", lesson.handoff.label, "primary lesson-try-calculator");
      tryBtn.type = "button";
      tryBtn.addEventListener("click", () => {
        stopPlay();
        openInCalculator(lesson.handoff);
      });
      handoffEl.append(tryBtn);
    }
    if (lesson.secondaryHandoff) {
      const secBtn = element("button", lesson.secondaryHandoff.label, "outline");
      secBtn.type = "button";
      secBtn.addEventListener("click", () => {
        stopPlay();
        window.location.hash = lesson.secondaryHandoff.view;
      });
      handoffEl.append(secBtn);
    }

    prevLessonBtn.disabled = lessonIndex === 0;
    nextLessonBtn.disabled = lessonIndex === LESSONS.length - 1;
    renderCatalog();
    renderSubtabs();
  }

  /** Re-render catalog, sub-tabs, and active step stage. */
  function renderAll() {
    renderCatalog();
    renderSubtabs();
    renderWorkspace();
  }

  /** Toggle animated step playback at the chosen speed (`Slow`, `Normal`, `Fast`). */
  function togglePlay() {
    if (timer) {
      stopPlay();
      return;
    }
    stopCascade();
    const steps = currentSteps();
    if (stepIndex >= steps.length - 1) {
      stepIndex = 0;
      renderWorkspace();
    }
    playBtn.textContent = "Pause";
    playBtn.setAttribute("aria-pressed", "true");
    const delay = SPEED_MS[speedSelect.value] || SPEED_MS.normal;
    timer = setInterval(() => {
      const activeSteps = currentSteps();
      if (stepIndex < activeSteps.length - 1) {
        stepIndex += 1;
        renderWorkspace();
      } else {
        stopPlay();
      }
    }, delay);
  }

  firstBtn.addEventListener("click", () => {
    if ((cascadeTarget ?? stepIndex) <= 0) return;
    stopPlay();
    stepIndex = 0;
    renderWorkspace();
  });
  prevBtn.addEventListener("click", () => {
    const baseStep = cascadeTarget ?? stepIndex;
    if (baseStep <= 0) return;
    stopPlay();
    stepIndex = baseStep - 1;
    renderWorkspace();
  });
  firstActiveBtn?.addEventListener("click", () => {
    const steps = currentSteps();
    const targetIdx = steps.length > 1 ? 1 : null;
    if (targetIdx === null || stepIndex === targetIdx) return;
    stopPlay();
    stepIndex = targetIdx;
    renderWorkspace();
  });
  playBtn.addEventListener("click", () => {
    if (currentSteps().length <= 1) return;
    togglePlay();
  });
  nextBtn.addEventListener("click", () => {
    const baseStep = cascadeTarget ?? stepIndex;
    const steps = currentSteps();
    if (baseStep >= steps.length - 1) return;
    stopPlay();
    stepIndex = baseStep + 1;
    renderWorkspace();
  });
  lastBtn.addEventListener("click", () => {
    const steps = currentSteps();
    if ((cascadeTarget ?? stepIndex) >= steps.length - 1) return;
    stopPlay();
    stepIndex = steps.length - 1;
    renderWorkspace();
  });
  if (compareBtn) {
    compareBtn.addEventListener("click", () => {
      stopPlay();
      comparePrev = !comparePrev;
      renderWorkspace();
    });
  }
  speedSelect.addEventListener("change", () => {
    if (timer) {
      stopPlay();
      togglePlay();
    }
  });
  prevLessonBtn.addEventListener("click", () => {
    if (lessonIndex > 0) {
      stopPlay();
      lessonIndex -= 1;
      subIndex = 0;
      stepIndex = 0;
      renderAll();
    }
  });
  nextLessonBtn.addEventListener("click", () => {
    if (lessonIndex < LESSONS.length - 1) {
      stopPlay();
      lessonIndex += 1;
      subIndex = 0;
      stepIndex = 0;
      renderAll();
    }
  });

  // Keyboard navigation when the Lessons view is active and focus is outside form inputs.
  document.addEventListener("keydown", event => {
    const view = document.querySelector('[data-lab-view="lessons"]');
    if (!view || view.hidden) return;
    const tag = document.activeElement?.tagName;
    if (tag === "INPUT" || tag === "SELECT" || tag === "TEXTAREA") return;
    if (event.key === "ArrowLeft") {
      if (stepIndex <= 0) return;
      event.preventDefault();
      stopPlay();
      stepIndex -= 1;
      renderWorkspace();
    } else if (event.key === "ArrowRight") {
      if (stepIndex >= currentSteps().length - 1) return;
      event.preventDefault();
      stopPlay();
      stepIndex += 1;
      renderWorkspace();
    } else if (event.key === "Home") {
      if (stepIndex <= 0) return;
      event.preventDefault();
      stopPlay();
      stepIndex = 0;
      renderWorkspace();
    } else if (event.key === "End") {
      if (stepIndex >= currentSteps().length - 1) return;
      event.preventDefault();
      stopPlay();
      stepIndex = currentSteps().length - 1;
      renderWorkspace();
    } else if (event.key === " " && tag !== "BUTTON") {
      if (currentSteps().length <= 1) return;
      event.preventDefault();
      togglePlay();
    }
  });

  renderAll();

  return {
    /**
     * Select a lesson by slug id (e.g. `"addition"`, `"inverse"`) when navigating via `#lessons/<id>`,
     * and refresh gliding indicators once the view is visible.
     *
     * @param {string} [id] - Optional lesson id slug.
     */
    selectLessonById(id) {
      stopPlay();
      if (id) {
        const found = LESSONS.findIndex(item => item.id === id);
        if (found >= 0 && found !== lessonIndex) {
          lessonIndex = found;
          subIndex = 0;
          stepIndex = 0;
          renderAll();
          return;
        }
      }
      subtabsIndicator.update();
      dotsIndicator.update();
    },
  };
}
