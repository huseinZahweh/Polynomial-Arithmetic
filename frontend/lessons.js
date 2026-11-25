/**
 * @fileoverview Simplified, self-contained Lessons page controller (`#lessons`) featuring
 * a 7-lesson selector hub, gliding top section navigation bar (`#lesson-subtabs`),
 * clean scrollable visual study cards (including 4-row Z_2 truth tables, worked tables,
 * aligned XOR columns, shift registers, interactive sandboxes, and self-check quizzes),
 * and linear `Previous section` / `Next section` footer navigation across the full curriculum.
 *
 * Original Author: Ali Zahreddine - Milestone 6 (Waves 1-4).
 */

import { LESSONS } from "./lesson-data.js";
import { attachSlidingIndicator, element, formatOperand, mathElement, polynomial, setMathText } from "./notation.js";

/** @param {string} id @returns {HTMLElement} */
const $ = id => document.getElementById(id);

/**
 * Build a flat ordered list of every `(lessonIdx, subIdx)` section across all 7 lessons
 * so `Previous section` and `Next section` step seamlessly across section and lesson boundaries.
 *
 * @returns {Array<{lessonIdx: number, subIdx: number, id: string}>} Ordered curriculum sections.
 */
function buildFlatSections() {
  const flat = [];
  LESSONS.forEach((lesson, lessonIdx) => {
    lesson.sublessons.forEach((sub, subIdx) => {
      flat.push({ lessonIdx, subIdx, id: sub.id });
    });
  });
  return flat;
}

/**
 * Render one visual block payload (`truth-table`, `worked-table`, `cards`, `xor-columns`,
 * `reduction-step`, `shift-register`, `mul-walkthrough`, `poly-divmod`, or `pipeline`)
 * with true HTML `<sup>`/`<sub>` typography and zero horizontal overflow.
 *
 * @param {object} visual - Visual descriptor from `LESSONS`.
 * @returns {HTMLElement} Populated visual container element.
 */
function renderVisual(visual) {
  const container = element("div", undefined, "lesson-visual");
  if (!visual) return container;

  if (visual.type === "truth-table") {
    const wrap = element("div", undefined, "lesson-table-wrap");
    const tbl = element("table", undefined, "truth-table");
    if (visual.caption) {
      tbl.append(mathElement("caption", visual.caption, "truth-table-caption"));
    }
    const headRow = tbl.createTHead().insertRow();
    for (const h of visual.headers) {
      const th = mathElement("th", h);
      th.scope = "col";
      headRow.append(th);
    }
    const tbody = tbl.createTBody();
    for (const row of visual.rows) {
      const tr = tbody.insertRow();
      if (row.tone) tr.className = "truth-row-" + row.tone;
      tr.insertCell().textContent = row.a;
      tr.insertCell().textContent = row.b;
      const outCell = tr.insertCell();
      outCell.className = "truth-out-cell";
      outCell.textContent = row.out;
      const noteCell = tr.insertCell();
      setMathText(noteCell, row.note);
    }
    wrap.append(tbl);
    container.append(wrap);
  }

  if (visual.type === "worked-table") {
    const wrap = element("div", undefined, "lesson-table-wrap");
    const tbl = element("table", undefined, "truth-table worked-example-table");
    if (visual.caption) {
      tbl.append(mathElement("caption", visual.caption, "truth-table-caption"));
    }
    const headRow = tbl.createTHead().insertRow();
    for (const h of visual.headers) {
      const th = mathElement("th", h);
      th.scope = "col";
      headRow.append(th);
    }
    const tbody = tbl.createTBody();
    visual.rows.forEach((cells, rIdx) => {
      const tr = tbody.insertRow();
      if (visual.highlightLastRow && rIdx === visual.rows.length - 1) {
        tr.className = "truth-row-updated";
      }
      cells.forEach((cellVal, cIdx) => {
        const td = tr.insertCell();
        setMathText(td, cellVal);
        if (visual.highlightLastCol && cIdx === cells.length - 1) {
          td.classList.add("truth-out-cell");
        }
      });
    });
    wrap.append(tbl);
    if (visual.note) wrap.append(mathElement("p", visual.note, "lesson-visual-note"));
    container.append(wrap);
  }

  if (visual.type === "cards") {
    const grid = element("div", undefined, "lesson-card-grid");
    for (const item of visual.items) {
      const card = element("article", undefined, "lesson-concept-card");
      card.append(
        mathElement("span", item.badge, "lesson-badge"),
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

    for (const [label, bits, rowKind] of [
      [visual.aLabel, visual.aBits, "a"],
      [visual.bLabel, visual.bBits, "b"],
      [visual.outLabel, outBits.join(""), "out"],
    ]) {
      const row = element("div", undefined, "lesson-bit-row" + (rowKind === "out" ? " is-result" : ""));
      row.append(mathElement("span", label, "lesson-row-label"));
      for (let i = 0; i < width; i += 1) {
        const cancels = visual.aBits[i] === "1" && visual.bBits[i] === "1";
        let cls = "lesson-bit-tile";
        if (bits[i] === "1") cls += " is-one";
        if (rowKind === "out") {
          if (cancels) cls += " is-cancel diff-reduced";
          else if (bits[i] === "1") cls += " diff-updated";
          else cls += " diff-unchanged";
        } else if (cancels) {
          cls += " diff-reduced";
        } else if (bits[i] === "1") {
          cls += " diff-carried";
        } else {
          cls += " diff-unchanged";
        }
        row.append(element("span", bits[i], cls));
      }
      grid.append(row);
    }

    const tagRow = element("div", undefined, "lesson-bit-diff-row");
    tagRow.append(element("span", "Rule", "lesson-row-label"));
    for (let i = 0; i < width; i += 1) {
      const cancels = visual.aBits[i] === "1" && visual.bBits[i] === "1";
      if (cancels) tagRow.append(element("span", "1⊕1→0", "lesson-bit-diff-tag diff-reduced"));
      else if (outBits[i] === "1") tagRow.append(element("span", "Keep 1", "lesson-bit-diff-tag diff-updated"));
      else tagRow.append(element("span", "0", "lesson-bit-diff-tag diff-unchanged"));
    }
    grid.append(tagRow);

    wrap.append(grid);
    if (visual.note) wrap.append(mathElement("p", visual.note, "lesson-visual-note"));
    container.append(wrap);
  }

  if (visual.type === "reduction-step") {
    const box = element("div", undefined, "lesson-reduction-stage");
    const rows = [
      {
        label: "Before (deg = " + visual.d + ")",
        hex: "{" + visual.beforeHex + "}",
        bits: visual.beforeBits,
        poly: visual.beforePoly,
        diffClass: "diff-reduced",
        badge: "Cancel x^" + visual.d,
      },
      {
        label: "Shifted modulus · m(x) << " + visual.shift,
        hex: "{" + visual.reducerHex + "}",
        bits: visual.reducerBits,
        poly: visual.reducerPoly,
        diffClass: "diff-carried",
        badge: "m(x) << " + visual.shift,
      },
      {
        label: "After XOR (deg < " + visual.m + ")",
        hex: "{" + visual.afterHex + "}",
        bits: visual.afterBits,
        poly: visual.afterPoly,
        diffClass: "diff-updated",
        badge: "Reduced",
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
      box.append(card);
    }
    container.append(box);
  }

  if (visual.type === "shift-register") {
    const box = element("div", undefined, "lesson-register-stage");
    const flow = element("div", undefined, "lesson-register-flow");

    const step1 = element("div", undefined, "lesson-concept-card diff-unchanged");
    step1.append(
      element("span", "1 · Input Register", "lesson-badge"),
      mathElement("h4", "{" + visual.inputHex + "} = " + visual.inputBits + "₂"),
      mathElement("p", "Inspect MSB bit b_7 = " + visual.msb),
    );

    const shiftClass = visual.msb ? "diff-reduced" : "diff-carried";
    const step2 = element("div", undefined, "lesson-concept-card " + shiftClass + (visual.msb ? " is-overflow" : ""));
    step2.append(
      element("span", "2 · Shift Left (<< 1)", "lesson-badge"),
      mathElement("h4", visual.shiftedBits + "₂"),
      mathElement("p", visual.msb ? "Top bit x^8 = 1 popped out!" : "No overflow (b_7 was 0)"),
    );

    const step3 = element("div", undefined, "lesson-concept-card is-highlight diff-updated");
    step3.append(
      element("span", visual.reduced ? "3 · XOR Low Taps {" + visual.modLowHex + "}" : "3 · Reduced Output", "lesson-badge"),
      mathElement("h4", "{" + visual.outputHex + "} = " + visual.outputBits + "₂"),
      mathElement("p", visual.note),
    );
    flow.append(step1, step2, step3);
    box.append(flow);
    container.append(box);
  }

  if (visual.type === "mul-walkthrough") {
    const wrap = element("div", undefined, "lesson-mul-stage");
    const grid = element("div", undefined, "lesson-mul-grid");
    visual.rows.forEach((row, idx) => {
      const prevRow = idx > 0 ? visual.rows[idx - 1] : null;
      const prevAcc = prevRow ? prevRow.acc : "00";
      const shiftClass = row.reduced ? "diff-reduced" : row.i > 0 ? "diff-carried" : "diff-unchanged";
      const accClass = row.bit ? "diff-updated" : "diff-unchanged";
      const card = element(
        "div",
        undefined,
        "lesson-mul-row" + (row.bit === 1 ? " is-selected" : ""),
      );
      const top = element("div", undefined, "diff-cell-head");
      top.append(
        mathElement("span", "Bit b_" + row.i + " = " + row.bit, "lesson-badge"),
        mathElement("span", row.reduced ? "Shifted + Reduced ⊕ m(x)" : row.i > 0 ? "Shifted left (<< 1)" : "Start A(x)", "diff-tag " + shiftClass),
        element("span", row.bit ? "XOR into sum" : "Skip (bit = 0)", "diff-tag " + accClass),
      );
      const accText = row.bit
        ? "Running Sum: {" + prevAcc + "} ⊕ {" + row.partial + "} = {" + row.acc + "}"
        : "Running Sum unchanged: {" + row.acc + "}";
      card.append(
        top,
        mathElement("strong", "Shifted value: {" + row.partial + "}"),
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
      ["Dividend A3(x)", visual.dividend, "diff-unchanged", "Dividend"],
      ["Divisor B3(x)", visual.divisor, "diff-unchanged", "Divisor"],
      ["Quotient Q(x) = A3 div B3", visual.quotient, "diff-updated", "Quotient"],
      ["Aligned Q(x) · B3(x)", visual.shiftedDivisor, "diff-carried", "Shifted Divisor"],
      ["Remainder R(x) = A3 ⊕ Q·B3", visual.remainder, "diff-reduced", "Leading term cancelled"],
    ];
    const dl = element("dl", undefined, "equivalents lesson-divmod-list");
    for (const [dt, val, diffClass, badge] of items) {
      const dd = element("dd", undefined, "diff-cell-box " + diffClass);
      const head = element("div", undefined, "diff-cell-head");
      head.append(mathElement("span", val, "diff-cell-val"), element("span", badge, "diff-tag " + diffClass));
      dd.append(head);
      dl.append(mathElement("dt", dt), dd);
    }
    box.append(dl, mathElement("p", visual.note, "lesson-visual-note"));
    container.append(box);
  }

  if (visual.type === "pipeline") {
    const grid = element("div", undefined, "lesson-card-grid");
    visual.stages.forEach(item => {
      const card = element("article", undefined, "lesson-concept-card diff-updated");
      card.append(
        element("span", item.stage, "lesson-badge"),
        mathElement("h4", item.title),
        mathElement("p", item.detail),
      );
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
 * Build an instant-feedback multiple-choice self-check card for a lesson section.
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
          : "Not quite: review the worked explanation above and try the other choice.",
      );
    });
    choices.append(btn);
  }
  box.append(choices, status);
  return box;
}

/**
 * Initialize the simplified `#lessons` view with catalog hub, gliding section bar,
 * scrollable self-contained content cards, and linear `Previous section` / `Next section` controls.
 *
 * @returns {{selectLessonById: (id?: string) => void}} Controller handle for hash navigation.
 */
export function setupLessons() {
  const catalogEl = $("lesson-catalog");
  const subtabsEl = $("lesson-subtabs");
  const stageEl = $("lesson-stage");
  const titleEl = $("lesson-active-title");
  const subtitleEl = $("lesson-active-subtitle");
  const counterEl = $("lesson-section-counter");
  const prevSectionBtn = $("lesson-prev-topic");
  const nextSectionBtn = $("lesson-next-topic");
  const workspaceEl = $("lesson-workspace");

  const flatSections = buildFlatSections();
  let flatIndex = 0;
  let renderedSubtabsLesson = -1;
  const visitedSections = new Set();

  const subtabsIndicator = attachSlidingIndicator(subtabsEl, ".lesson-subtab.is-active");

  /** @returns {{lessonIdx: number, subIdx: number}} Current section position. */
  const currentPos = () => flatSections[flatIndex];
  /** @returns {object} Active lesson object. */
  const currentLesson = () => LESSONS[currentPos().lessonIdx];
  /** @returns {object} Active sub-lesson section object. */
  const currentSub = () => currentLesson().sublessons[currentPos().subIdx];

  /**
   * Locate the flat index for a `(lessonIdx, subIdx)` pair.
   * @param {number} lIdx - Zero-based lesson index.
   * @param {number} sIdx - Zero-based sub-lesson index.
   * @returns {number} Flat index in `flatSections`.
   */
  function findFlatIndex(lIdx, sIdx) {
    const idx = flatSections.findIndex(item => item.lessonIdx === lIdx && item.subIdx === sIdx);
    return idx >= 0 ? idx : 0;
  }

  /** Render the 7-card Lesson Selector Hub with section counts and visited status. */
  function renderCatalog() {
    const activeLessonIdx = currentPos().lessonIdx;
    catalogEl.replaceChildren();
    LESSONS.forEach((lesson, idx) => {
      const allVisited = lesson.sublessons.every(sub => visitedSections.has(sub.id));
      const card = element(
        "button",
        undefined,
        "lesson-hub-card" + (idx === activeLessonIdx ? " is-active" : "") + (allVisited ? " is-done" : ""),
      );
      card.type = "button";
      card.setAttribute("aria-pressed", String(idx === activeLessonIdx));
      card.dataset.lessonId = lesson.id;
      const top = element("div", undefined, "lesson-hub-card-top");
      top.append(
        mathElement("span", lesson.symbol, "lesson-symbol-badge"),
        element("span", "Lesson " + lesson.number + (allVisited ? " · ✓" : ""), "lesson-hub-num"),
      );
      card.append(
        top,
        mathElement("strong", lesson.title, "lesson-hub-title"),
        element("small", lesson.sublessons.length + (lesson.sublessons.length === 1 ? " section" : " sections")),
      );
      card.addEventListener("click", () => {
        flatIndex = findFlatIndex(idx, 0);
        renderAll(false);
      });
      catalogEl.append(card);
    });
  }

  /** Render or update active state on the top section navigation bar (`#lesson-subtabs`). */
  function renderSubtabs() {
    const { lessonIdx, subIdx } = currentPos();
    const lesson = currentLesson();
    if (renderedSubtabsLesson !== lessonIdx) {
      renderedSubtabsLesson = lessonIdx;
      subtabsEl.replaceChildren();
      lesson.sublessons.forEach((sub, idx) => {
        const btn = mathElement("button", sub.title, "lesson-subtab" + (idx === subIdx ? " is-active" : ""));
        btn.type = "button";
        btn.setAttribute("aria-pressed", String(idx === subIdx));
        btn.addEventListener("click", () => {
          flatIndex = findFlatIndex(lessonIdx, idx);
          renderAll(false);
        });
        subtabsEl.append(btn);
      });
    } else {
      const buttons = Array.from(subtabsEl.querySelectorAll(".lesson-subtab"));
      buttons.forEach((btn, idx) => {
        const isActive = idx === subIdx;
        btn.classList.toggle("is-active", isActive);
        btn.setAttribute("aria-pressed", String(isActive));
      });
    }
    subtabsIndicator.update();
  }

  /** Render the complete self-contained section card and update footer controls. */
  function renderWorkspace() {
    const lesson = currentLesson();
    const sub = currentSub();
    visitedSections.add(sub.id);

    setMathText(titleEl, "Lesson " + lesson.number + " · " + lesson.title);
    setMathText(subtitleEl, sub.summary);
    if (counterEl) {
      counterEl.textContent = "Section " + (flatIndex + 1) + " of " + flatSections.length + " (" + sub.id + ")";
    }

    const card = element("article", undefined, "lesson-step-frame lesson-section-card");
    const sectionHeader = element("header", undefined, "lesson-step-header");
    sectionHeader.append(
      mathElement("span", sub.title, "lesson-badge"),
      mathElement("p", sub.summary, "lesson-step-explanation"),
    );
    card.append(sectionHeader);

    for (const block of sub.blocks || []) {
      const sectionBlock = element("section", undefined, "lesson-content-block");
      sectionBlock.append(
        mathElement("h3", block.title, "step-knowledge-title"),
        mathElement("code", block.formula, "lesson-formula-banner"),
        mathElement("p", block.explanation, "lesson-step-explanation"),
      );
      if (block.visual) {
        sectionBlock.append(renderVisual(block.visual));
      }
      card.append(sectionBlock);
    }

    if (sub.activity === "bit-sandbox") card.append(buildBitSandbox());
    if (sub.activity === "xor-check") card.append(buildXorActivity());
    if (sub.quiz) card.append(buildQuiz(sub.quiz));

    stageEl.replaceChildren(card);

    prevSectionBtn.disabled = flatIndex <= 0;
    nextSectionBtn.disabled = flatIndex >= flatSections.length - 1;
  }

  /**
   * Re-render catalog, subtabs, and active section card, optionally scrolling to the card top.
   *
   * @param {boolean} [scrollToTop=false] - Smoothly scroll `#lesson-workspace` into view.
   */
  function renderAll(scrollToTop = false) {
    renderWorkspace();
    renderCatalog();
    renderSubtabs();
    if (scrollToTop && workspaceEl) {
      workspaceEl.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }

  prevSectionBtn.addEventListener("click", () => {
    if (flatIndex <= 0) return;
    flatIndex -= 1;
    renderAll(true);
  });

  nextSectionBtn.addEventListener("click", () => {
    if (flatIndex >= flatSections.length - 1) return;
    flatIndex += 1;
    renderAll(true);
  });

  renderAll(false);

  return {
    /**
     * Select a lesson by its slug ID (e.g. from `#lessons/inverse`) or refresh gliding pill geometry.
     *
     * @param {string} [slug] - Optional lesson ID string.
     */
    selectLessonById(slug) {
      if (slug) {
        const idx = LESSONS.findIndex(item => item.id === slug);
        if (idx >= 0) {
          flatIndex = findFlatIndex(idx, 0);
          renderAll(false);
          return;
        }
      }
      subtabsIndicator.update();
    },

    /**
     * Return share-link query parameters for the currently active lesson and section.
     *
     * @returns {{lesson: string, section: string}} Active lesson number and section ID.
     */
    getShareState() {
      return {
        lesson: String(currentLesson().number),
        section: currentSub().id,
      };
    },

    /**
     * Restore a shared `#lessons` URL state (`?lesson=1&section=1.2#lessons`).
     *
     * @param {URLSearchParams} params - Parsed URL query parameters.
     * @returns {boolean} True when a matching lesson or section was restored.
     */
    restoreShareState(params) {
      const sectionParam = params.get("section");
      if (sectionParam) {
        const idx = flatSections.findIndex(item => item.id === sectionParam);
        if (idx >= 0) {
          flatIndex = idx;
          renderAll(false);
          return true;
        }
      }
      const lessonParam = params.get("lesson");
      if (lessonParam) {
        const lIdx = LESSONS.findIndex(
          item => String(item.number) === lessonParam || item.id === lessonParam,
        );
        if (lIdx >= 0) {
          flatIndex = findFlatIndex(lIdx, 0);
          renderAll(false);
          return true;
        }
      }
      return false;
    },
  };
}
