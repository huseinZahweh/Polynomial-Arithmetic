/**
 * @fileoverview Interactive trace visualizers, built-in Previous-to-Current comparison in
 * `Step view`, inline 4-step paginated `All steps grid`, `Classic table` with color legend,
 * playback locking outside `Step view`, Full-Value Inspector popup for truncated large-field
 * cells, and step-specific BigInt derivation popups for Extended Euclid (`Q`, `T1`, `T2`, `T3`)
 * and Shift-and-XOR (`<< 1` / `⊕ m(x)`).
 *
 * Original Author: Ali Zahreddine - Milestone 4, Integration & Milestone 6 (Waves 1-4).
 *
 * Renders all course-aligned visualizers plus generic exploration tables across three layout modes:
 *   - `Step view` (default across ALL 13 fields `m in {2..8, 163..571}`): single card on Step 0,
 *     side-by-side Previous -> Current comparison from Step 1 onward (stacking vertically on mobile).
 *   - `All steps grid`: inline full-width single-column stack loading 4 steps initially with
 *     incremental `Show more` pagination (+4 steps per click) and locked playback controls.
 *   - `Classic table`: complete table view with a concise color legend above and locked playback.
 */

import {
  appendMathText,
  attachSlidingIndicator,
  copyToClipboard,
  degreeOf,
  element,
  mathElement,
  polynomial,
  setMathText,
  showDerivationPopup,
  showFeedbackPopup,
  showInspectorPopup,
  significantDigits,
} from "./notation.js";

const PLAY_SPEED_MS = { slow: 1800, normal: 900, fast: 450 };
const CASCADE_STEP_MS = 95;
const MAX_CASCADE_HOPS = 12;
const GRID_PAGE_SIZE = 4;

/**
 * Perform exact carry-free multiplication `a(x) * b(x)` over `GF(2)[x]` using `BigInt`,
 * recording every partial shifted term contributed by set bits of `a(x)`.
 *
 * Complexity: O(deg(a)) bit shifts and XORs.
 *
 * @param {bigint} a - Multiplier polynomial bitmask (e.g. `Q(x)`).
 * @param {bigint} b - Multiplicand polynomial bitmask (e.g. `B_k(x)`).
 * @returns {{product: bigint, terms: Array<{bit: number, shifted: bigint}>}} Exact product and partial terms.
 */
function polyMulNoModBigInt(a, b) {
  let product = 0n;
  const terms = [];
  let temp = a;
  let bit = 0;
  while (temp > 0n) {
    if (temp & 1n) {
      const shifted = b << BigInt(bit);
      product ^= shifted;
      terms.push({ bit, shifted });
    }
    temp >>= 1n;
    bit += 1;
  }
  return { product, terms };
}

/**
 * Perform exact Euclidean polynomial long division (`POLY_DIVMOD`) of `dividend` by `divisor`
 * over `GF(2)[x]`, recording every degree-alignment shift and XOR cancellation step.
 *
 * Complexity: O(deg(dividend) - deg(divisor) + 1) alignment steps.
 *
 * @param {bigint} dividend - Dividend polynomial `A3(x)`.
 * @param {bigint} divisor - Nonzero divisor polynomial `B3(x)`.
 * @returns {{quotient: bigint, remainder: bigint, steps: Array<{stepNum: number, targetDeg: number, shift: number, before: bigint, shiftedDivisor: bigint, after: bigint}>}} Division result and trace.
 */
function polyDivModBigInt(dividend, divisor) {
  if (divisor === 0n) return { quotient: 0n, remainder: dividend, steps: [] };
  let rem = dividend;
  let quot = 0n;
  const degB = degreeOf(divisor);
  const steps = [];
  let stepNum = 1;
  while (rem !== 0n && degreeOf(rem) >= degB) {
    const targetDeg = degreeOf(rem);
    const shift = targetDeg - degB;
    const shiftedDivisor = divisor << BigInt(shift);
    const after = rem ^ shiftedDivisor;
    quot ^= 1n << BigInt(shift);
    steps.push({ stepNum, targetDeg, shift, before: rem, shiftedDivisor, after });
    rem = after;
    stepNum += 1;
  }
  return { quotient: quot, remainder: rem, steps };
}

/**
 * Format a `BigInt` value cleanly for step derivation popups: shows `{HEX}` and polynomial
 * form for small fields (`m <= 16`) or full `{HEX}` with degree note for large cryptographic fields.
 *
 * @param {bigint} value - Polynomial bitmask.
 * @param {number} mDeg - Field degree `m`.
 * @returns {string} Readable mathematical value summary.
 */
function formatPopupPoly(value, mDeg) {
  const hexVal = value.toString(16).toUpperCase();
  if (mDeg <= 16) {
    return "{" + hexVal + "}  (" + polynomial(value) + ")";
  }
  const deg = degreeOf(value);
  return "{" + hexVal + "}  (" + (deg < 0 ? "zero" : "deg " + deg) + ")";
}

/**
 * Open the step-specific derivation popup for `Q`, `T1`, `T2`, or `T3` on an Extended Euclid row.
 * Computes the exact carry-free division / multiplication / XOR derivation from the previous row's
 * Triple `A` and Triple `B` using client-side `BigInt`.
 *
 * @param {"Q" | "T1" | "T2" | "T3"} target - Which Extended Euclid value to derive.
 * @param {object} prevRow - Previous Table 4.7 row (`rowIndex - 1`).
 * @param {object} currRow - Current Table 4.7 row (`rowIndex`).
 * @param {number} mDeg - Field degree `m`.
 */
function openEuclidDerivationPopup(target, prevRow, currRow, mDeg) {
  const parseHex = (row, term) => BigInt("0x" + (row.cells[term]?.hex || "0"));
  const prevA1 = parseHex(prevRow, "A1");
  const prevA2 = parseHex(prevRow, "A2");
  const prevA3 = parseHex(prevRow, "A3");
  const prevB1 = parseHex(prevRow, "B1");
  const prevB2 = parseHex(prevRow, "B2");
  const prevB3 = parseHex(prevRow, "B3");
  const currQ = parseHex(currRow, "Q");
  const currB1 = parseHex(currRow, "B1");
  const currB2 = parseHex(currRow, "B2");
  const currB3 = parseHex(currRow, "B3");

  if (target === "Q") {
    const div = polyDivModBigInt(prevA3, prevB3);
    const steps = [];
    steps.push({
      heading: "Inputs from Step " + prevRow.step,
      badge: "POLY_DIVMOD",
      tone: "diff-carried",
      lines: [
        "Dividend A3(x) = " + formatPopupPoly(prevA3, mDeg),
        "Divisor  B3(x) = " + formatPopupPoly(prevB3, mDeg),
      ],
    });
    if (!div.steps.length) {
      steps.push({
        heading: "No alignment needed",
        badge: "Q = 0",
        tone: "diff-unchanged",
        lines: ["deg(A3) < deg(B3), so the quotient Q(x) is 0 and remainder T3(x) = A3(x)."],
      });
    } else {
      const shown = div.steps.length <= 16 ? div.steps : [...div.steps.slice(0, 12), ...div.steps.slice(-3)];
      const omitted = div.steps.length - shown.length;
      shown.forEach((s, idx) => {
        if (omitted > 0 && idx === 12) {
          steps.push({
            heading: "Intermediate alignment steps",
            badge: omitted + " more shifts",
            tone: "diff-unchanged",
            lines: [omitted + " intermediate single-term cancellations follow the exact same shift-and-XOR rule."],
          });
        }
        const termStr = s.shift === 0 ? "1" : (s.shift === 1 ? "x" : "x^" + s.shift);
        steps.push({
          heading: "Long-division alignment " + s.stepNum + " · Cancel x^" + s.targetDeg,
          badge: "Add " + termStr + " to Q",
          tone: "diff-reduced",
          lines: [
            "Shift = deg(rem) − deg(B3) = " + s.targetDeg + " − " + degreeOf(prevB3) + " = " + s.shift + "  →  quotient term " + termStr,
            "Current remainder:  " + formatPopupPoly(s.before, mDeg),
            "XOR (B3 << " + s.shift + "):     " + formatPopupPoly(s.shiftedDivisor, mDeg),
            "New remainder:      " + formatPopupPoly(s.after, mDeg),
          ],
        });
      });
    }
    showDerivationPopup({
      title: "Step " + currRow.step + ": How Q(x) is calculated",
      subtitle: "Carry-free Euclidean polynomial long division A3(x) ÷ B3(x) in GF(2)[x]",
      formula: "Q(x) = A3(x) div B3(x)   (from Step " + prevRow.step + ")",
      steps,
      result: {
        label: "Quotient Q(x) for Step " + currRow.step,
        value: formatPopupPoly(currQ, mDeg),
        detail: "Remainder T3(x) after cancelling all terms down to degree < " + degreeOf(prevB3) + " is {" + div.remainder.toString(16).toUpperCase() + "}.",
        isMath: true,
      },
    });
    return;
  }

  if (target === "T1" || target === "T2") {
    const idxNum = target === "T1" ? "1" : "2";
    const prevA = target === "T1" ? prevA1 : prevA2;
    const prevB = target === "T1" ? prevB1 : prevB2;
    const currT = target === "T1" ? currB1 : currB2;
    const mul = polyMulNoModBigInt(currQ, prevB);

    const mulLines = [];
    if (currQ === 0n || prevB === 0n) {
      mulLines.push("Since " + (currQ === 0n ? "Q(x) = 0" : "B" + idxNum + "(x) = 0") + ", the carry-free product Q(x) · B" + idxNum + "(x) = 0.");
    } else {
      const shownTerms = mul.terms.length <= 12 ? mul.terms : [...mul.terms.slice(0, 8), ...mul.terms.slice(-3)];
      for (const term of shownTerms) {
        const powerLabel = term.bit === 0 ? "1" : (term.bit === 1 ? "x" : "x^" + term.bit);
        mulLines.push("Term " + powerLabel + " of Q(x):  B" + idxNum + " << " + term.bit + " = " + formatPopupPoly(term.shifted, mDeg));
      }
      if (mul.terms.length > shownTerms.length) {
        mulLines.push("(" + (mul.terms.length - shownTerms.length) + " additional shifted terms XORed in the same way)");
      }
      mulLines.push("XOR of shifted terms  →  Q(x) · B" + idxNum + "(x) = " + formatPopupPoly(mul.product, mDeg));
    }

    showDerivationPopup({
      title: "Step " + currRow.step + ": How T" + idxNum + "(x) is calculated",
      subtitle: "Carry-free product Q(x) · B" + idxNum + "(x) followed by bitwise XOR with previous A" + idxNum + "(x)",
      formula: "T" + idxNum + "(x) = A" + idxNum + "(x) ⊕ (Q(x) · B" + idxNum + "(x))   (becomes new B" + idxNum + "(x))",
      steps: [
        {
          heading: "1. Read inputs from Step " + prevRow.step,
          badge: "Inputs",
          tone: "diff-carried",
          lines: [
            "Previous A" + idxNum + "(x) = " + formatPopupPoly(prevA, mDeg),
            "Previous B" + idxNum + "(x) = " + formatPopupPoly(prevB, mDeg),
            "Quotient Q(x)  = " + formatPopupPoly(currQ, mDeg),
          ],
        },
        {
          heading: "2. Carry-free product Q(x) · B" + idxNum + "(x)",
          badge: "Multiply in GF(2)[x]",
          tone: "diff-reduced",
          lines: mulLines,
        },
        {
          heading: "3. XOR with previous A" + idxNum + "(x)",
          badge: "A" + idxNum + " ⊕ Q·B" + idxNum,
          tone: "diff-updated",
          lines: [
            "A" + idxNum + "(x):         " + formatPopupPoly(prevA, mDeg),
            "⊕ (Q · B" + idxNum + "):  " + formatPopupPoly(mul.product, mDeg),
            "= T" + idxNum + "(x):       " + formatPopupPoly(currT, mDeg),
          ],
        },
      ],
      result: {
        label: "New B" + idxNum + "(x) = T" + idxNum + "(x) for Step " + currRow.step,
        value: formatPopupPoly(currT, mDeg),
        detail: target === "T2"
          ? "B2(x) tracks the Bézout coefficient of b(x): once B3(x) reaches 1, B2(x) is the multiplicative inverse."
          : "B1(x) tracks the Bézout coefficient of the modulus m(x) in B1·m ⊕ B2·b = B3.",
        isMath: true,
      },
    });
    return;
  }

  // target === "T3"
  const mul3 = polyMulNoModBigInt(currQ, prevB3);
  const prodLines = [];
  if (currQ === 0n) {
    prodLines.push("Q(x) = 0, so Q(x) · B3(x) = 0.");
  } else {
    const shownTerms = mul3.terms.length <= 12 ? mul3.terms : [...mul3.terms.slice(0, 8), ...mul3.terms.slice(-3)];
    for (const term of shownTerms) {
      const powerLabel = term.bit === 0 ? "1" : (term.bit === 1 ? "x" : "x^" + term.bit);
      prodLines.push("Term " + powerLabel + " of Q(x):  B3 << " + term.bit + " = " + formatPopupPoly(term.shifted, mDeg));
    }
    if (mul3.terms.length > shownTerms.length) {
      prodLines.push("(" + (mul3.terms.length - shownTerms.length) + " additional shifted terms XORed in the same way)");
    }
    prodLines.push("Aligned multiple Q(x) · B3(x) = " + formatPopupPoly(mul3.product, mDeg));
  }

  showDerivationPopup({
    title: "Step " + currRow.step + ": How T3(x) is calculated",
    subtitle: "Euclidean remainder T3(x) = A3(x) mod B3(x) = A3(x) ⊕ (Q(x) · B3(x))",
    formula: "T3(x) = A3(x) ⊕ (Q(x) · B3(x))   (becomes new B3(x))",
    steps: [
      {
        heading: "1. Read remainders from Step " + prevRow.step,
        badge: "Inputs",
        tone: "diff-carried",
        lines: [
          "Previous A3(x) = " + formatPopupPoly(prevA3, mDeg),
          "Previous B3(x) = " + formatPopupPoly(prevB3, mDeg),
          "Quotient Q(x)  = " + formatPopupPoly(currQ, mDeg),
        ],
      },
      {
        heading: "2. Form aligned multiple Q(x) · B3(x)",
        badge: "Align divisor",
        tone: "diff-reduced",
        lines: prodLines,
      },
      {
        heading: "3. Cancel leading terms via XOR",
        badge: "A3 ⊕ Q·B3",
        tone: "diff-updated",
        lines: [
          "A3(x):         " + formatPopupPoly(prevA3, mDeg),
          "⊕ (Q · B3):   " + formatPopupPoly(mul3.product, mDeg),
          "= T3(x):       " + formatPopupPoly(currB3, mDeg),
        ],
      },
    ],
    result: {
      label: "New Remainder B3(x) = T3(x) for Step " + currRow.step,
      value: formatPopupPoly(currB3, mDeg),
      detail: "Degree strictly drops from " + degreeOf(prevB3) + " down to " + degreeOf(currB3) +
        (currB3 === 1n ? " (B3 = 1 reached: inverse found in B2!)" : currB3 === 0n ? " (B3 = 0: no inverse exists)" : "."),
      isMath: true,
    },
  });
}

/**
 * Open the step-specific Shift-and-XOR visual illustration popup showing the 1-bit left shift (`<< 1`),
 * highlighting any popped `x^m` overflow bit, and showing the aligned `⊕ m(x)` reduction.
 *
 * @param {object} trace - Backend `shift-and-xor` trace object.
 * @param {number} idx - Zero-based step index.
 */
function openShiftXorIllustrationPopup(trace, idx) {
  const step = trace.steps[idx];
  const prevStep = idx > 0 ? trace.steps[idx - 1] : null;
  const mDeg = trace.m ?? trace.m_degree ?? 8;
  const prevBig = prevStep ? BigInt("0x" + prevStep.partial_hex) : 0n;
  const currBig = BigInt("0x" + step.partial_hex);
  const modBig = BigInt("0x" + (trace.reduction_poly_hex || "1"));
  const toPaddedBin = (val, width) => val.toString(2).padStart(width, "0");

  if (idx === 0) {
    showDerivationPopup({
      title: "Step 1 (Bit b_0): Initial Value A(x)",
      subtitle: "On bit b_0 (i = 0), we start directly with A(x) without shifting left yet.",
      formula: "Start term = A(x)   (0 shifts applied)",
      steps: [
        {
          heading: "1. Load reduced operand A(x)",
          badge: "No shift yet",
          tone: "diff-carried",
          lines: [
            "Value: " + formatPopupPoly(currBig, mDeg),
            ...(mDeg <= 16 ? ["Binary (" + mDeg + " bits): " + toPaddedBin(currBig, mDeg)] : []),
          ],
        },
        {
          heading: "2. Overflow check",
          badge: "Degree < " + mDeg,
          tone: "diff-unchanged",
          lines: ["Because no left shift occurred on Step 1, bit x^" + mDeg + " is 0 and no ⊕ m(x) reduction is needed."],
        },
      ],
      result: {
        label: "Shifted value for Step 1",
        value: formatPopupPoly(currBig, mDeg),
        detail: "Next step (Step 2) will shift this value left by 1 bit (<< 1).",
        isMath: true,
      },
    });
    return;
  }

  const unreduced = prevBig << 1n;
  const overflowBit = Number((unreduced >> BigInt(mDeg)) & 1n);
  const mask = (1n << BigInt(mDeg)) - 1n;
  const lowShifted = unreduced & mask;
  const lowMod = modBig & mask;

  const steps = [];
  if (mDeg <= 16) {
    const prevBin = toPaddedBin(prevBig, mDeg);
    const shiftedBin = toPaddedBin(unreduced, mDeg + 1);
    const modBin = toPaddedBin(modBig, mDeg + 1);
    const outBin = toPaddedBin(currBig, mDeg);

    steps.push({
      heading: "1. Inspect previous term & shift left by 1 bit (<< 1)",
      badge: overflowBit ? "MSB was 1 → overflows x^" + mDeg : "MSB was 0 → fits in " + mDeg + " bits",
      tone: overflowBit ? "diff-reduced" : "diff-carried",
      lines: [
        "Previous term:  " + prevBin + "  ({" + prevBig.toString(16).toUpperCase() + "})",
        "Shift left << 1: [" + shiftedBin[0] + "] " + shiftedBin.slice(1) + "  (popped x^" + mDeg + " bit = " + overflowBit + ")",
      ],
    });
    if (step.reduced) {
      steps.push({
        heading: "2. Cancel popped x^" + mDeg + " bit with ⊕ m(x)",
        badge: "⊕ m(x) reduction",
        tone: "diff-updated",
        lines: [
          "Shifted (" + (mDeg + 1) + "b):   " + shiftedBin,
          "⊕ m(x)  (" + (mDeg + 1) + "b):   " + modBin + "  (" + polynomial(modBig) + ")",
          "Reduced (" + mDeg + "b):    " + outBin + "  ({" + currBig.toString(16).toUpperCase() + "})",
        ],
      });
    } else {
      steps.push({
        heading: "2. Reduction check",
        badge: "No ⊕ m(x) needed",
        tone: "diff-unchanged",
        lines: ["Because the popped x^" + mDeg + " bit is 0, the degree stays below " + mDeg + " and no XOR with m(x) is performed."],
      });
    }
  } else {
    steps.push({
      heading: "1. Shift previous term left by 1 bit (<< 1)",
      badge: overflowBit ? "Popped x^" + mDeg + " = 1" : "Popped x^" + mDeg + " = 0",
      tone: overflowBit ? "diff-reduced" : "diff-carried",
      lines: [
        "Previous term: {" + prevBig.toString(16).toUpperCase() + "}",
        "After << 1 (low " + mDeg + " bits): {" + lowShifted.toString(16).toUpperCase() + "}",
        "Popped x^" + mDeg + " overflow bit = " + overflowBit,
      ],
    });
    if (step.reduced) {
      steps.push({
        heading: "2. Fold x^" + mDeg + " overflow using lower taps of m(x)",
        badge: "⊕ m(x) reduction",
        tone: "diff-updated",
        lines: [
          "Identity: x^" + mDeg + " ≡ " + polynomial(lowMod) + "  ({" + lowMod.toString(16).toUpperCase() + "})",
          "Low shifted: {" + lowShifted.toString(16).toUpperCase() + "}",
          "⊕ low m(x):  {" + lowMod.toString(16).toUpperCase() + "}",
          "= Reduced:   {" + currBig.toString(16).toUpperCase() + "}",
        ],
      });
    } else {
      steps.push({
        heading: "2. Reduction check",
        badge: "No ⊕ m(x) needed",
        tone: "diff-unchanged",
        lines: ["Top bit b_" + (mDeg - 1) + " was 0, so shifting left stayed strictly below degree " + mDeg + "."],
      });
    }
  }

  showDerivationPopup({
    title: "Step " + (idx + 1) + " (Bit b_" + step.i + "): Shift & XOR Illustration",
    subtitle: "Multiplying the previous term by x (1-bit left shift) modulo m(x) in GF(2^" + mDeg + ")",
    formula: step.reduced
      ? "next = (prev << 1) ⊕ m(x)   (x^" + mDeg + " overflow cancelled)"
      : "next = prev << 1   (no x^" + mDeg + " overflow)",
    steps,
    result: {
      label: "Shifted value for Step " + (idx + 1),
      value: formatPopupPoly(currBig, mDeg),
      detail: step.added
        ? "Bit b_" + step.i + " of B(x) is 1, so this shifted value is XORed into the running sum."
        : "Bit b_" + step.i + " of B(x) is 0, so this shifted value is skipped for the running sum.",
      isMath: true,
    },
  });
}

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
  const qPoly = formatCellText(row.cells.Q.algebraic, "algebraic", (trace.m_degree ?? 8) > 8, trace.m_degree ?? 8);
  return stagePrefix + "Step " + row.step + ": Divide A3(x) by B3(x) (Q = " + qPoly + ") & Update Bézout Remainder T3(x)";
}

/**
 * Compute an intuitive one-line educational title for a Shift-and-XOR multiplication step,
 * explicitly naming `A(x)`, the 1-bit left shift (`<< 1`), and bit `b_i` of `B(x)`.
 *
 * @param {object} step - Single Shift-and-XOR step entry.
 * @param {string} [stagePrefix=""] - Optional stage prefix (e.g. for two-stage division).
 * @param {number} [mDeg=8] - Field degree `m`.
 * @returns {string} Educational title describing shift, overflow reduction, and bit check.
 */
function multiplyKnowledgeTitle(step, stagePrefix = "", mDeg = 8) {
  if (step.i === 0) {
    const startHex = formatCellText(step.partial_hex, "hex", mDeg > 8, mDeg);
    return stagePrefix + "Step 1: Start with A(x) = {" + startHex + "} (no shift yet) & Check Bit b_0 of B(x)";
  }
  const n = step.i + 1;
  if (step.reduced) {
    return stagePrefix + "Step " + n + ": Shift Previous Term Left by 1 Bit (<< 1), Reduce ⊕ m(x), & Check Bit b_" + step.i + " of B(x)";
  }
  return stagePrefix + "Step " + n + ": Shift Previous Term Left by 1 Bit (<< 1) & Check Bit b_" + step.i + " of B(x)";
}

/**
 * Compute an informative one-line educational title for a Modulo Reduction step.
 *
 * @param {object} row - Reduction step record `{target_degree, shift}`.
 * @param {number} idx - Zero-based step index.
 * @param {string} [stagePrefix=""] - Optional prefix.
 * @returns {string} Educational step title.
 */
function reductionKnowledgeTitle(row, idx, stagePrefix = "") {
  return stagePrefix + "Step " + (idx + 1) + ": Cancel Leading Term x^" + row.target_degree +
    " using m(x) << " + (row.shift > 0 ? row.shift : 0);
}

/**
 * Compute an informative one-line educational title for a Bitwise XOR column step.
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
 * Build the shared, color-blind-safe visual diff legend bar used above step traces.
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
 * Build a concise, readable color legend placed right above every `Classic table` view.
 *
 * @returns {HTMLElement} Compact `.table-color-legend` element.
 */
export function createTableColorLegend() {
  const bar = element("div", undefined, "diff-legend table-color-legend");
  bar.setAttribute("role", "note");
  bar.setAttribute("aria-label", "Table color legend");
  bar.append(element("span", "Table highlights:", "diff-legend-title"));
  for (const [cls, label] of [
    ["diff-updated", "Surviving 1 bit / Updated / Inverse found"],
    ["diff-reduced", "1 ⊕ 1 → 0 cancellation / Overflow reduced"],
    ["diff-carried", "Carried / Active row"],
    ["diff-unchanged", "Unchanged"],
  ]) {
    bar.append(mathElement("span", label, "diff-legend-item " + cls));
  }
  return bar;
}

/**
 * Format a trace value according to the active notation and `compactValues` toggle.
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
 * Attach either Full-Value Inspector Popup (for truncated compact values in large fields)
 * or click-to-copy (for short untruncated cells) to a trace value element.
 *
 * @param {HTMLElement} node - Clickable DOM element displaying a polynomial/hex/binary value.
 * @param {{fullValue: string, displayValue?: string, valueBigInt?: bigint | null, mDegree?: number, label?: string}} info - Value metadata.
 */
function attachValueInteraction(node, info) {
  const fullValue = String(info.fullValue ?? "");
  const displayValue = String(info.displayValue ?? fullValue);
  const isTruncated = displayValue.includes("…") || displayValue.includes("...");
  node.dataset.fullValue = fullValue;

  if (isTruncated && info.valueBigInt !== undefined && info.valueBigInt !== null) {
    node.classList.add("trace-inspectable");
    node.title = "Click to view full value";
    node.tabIndex = 0;
    node.setAttribute("role", "button");
    node.setAttribute("aria-label", "Click to view full value for " + (info.label || "trace cell"));
    const cue = element("span", "⤢", "inspect-cue");
    cue.setAttribute("aria-hidden", "true");
    node.append(cue);
    const open = () => {
      showInspectorPopup({
        title: info.label || "Full value",
        valueBigInt: info.valueBigInt,
        mDegree: info.mDegree ?? 163,
      });
    };
    node.addEventListener("click", open);
    node.addEventListener("keydown", event => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        open();
      }
    });
    return;
  }

  node.title = "Click to copy full value: " + fullValue;
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
 * Build a styled diff value box (`<dd>`) with optional color-coded badge, math typography,
 * Full-Value Inspector click behavior on truncated cells, and inline `was:` / `prev:` sub-row.
 *
 * @param {string | number} displayValue - Primary text shown in the cell.
 * @param {object} [meta] - Optional metadata `{diffClass?, badge?, prevText?, fullValue?, valueBigInt?, mDegree?, label?, extraClass?, isMathValue?, scrollable?}`.
 * @returns {HTMLElement} Populated `<dd>` element.
 */
function buildDiffValueNode(displayValue, meta = {}) {
  const dd = element("dd");
  const fullValue = String(meta.fullValue ?? displayValue);
  const valInteraction = {
    fullValue,
    displayValue: String(displayValue),
    valueBigInt: meta.valueBigInt ?? null,
    mDegree: meta.mDegree ?? 8,
    label: meta.label || "Trace value",
  };

  if (meta.diffClass || meta.badge || meta.prevText) {
    dd.className = "diff-cell-box" + (meta.diffClass ? " " + meta.diffClass : "") + (meta.extraClass ? " " + meta.extraClass : "");
    const head = element("div", undefined, "diff-cell-head");
    const valClass = "diff-cell-val" + (meta.scrollable ? " value-scroll-wrap" : "");
    const valSpan = meta.isMathValue
      ? mathElement("span", displayValue, valClass)
      : element("span", String(displayValue), valClass);
    attachValueInteraction(valSpan, valInteraction);
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
    if (meta.scrollable) dd.classList.add("value-scroll-wrap");
    attachValueInteraction(dd, valInteraction);
  }
  return dd;
}

/**
 * Build an accessible trace table inside a labelled region with smart cell wrapping,
 * true `<sup>`/`<sub>` headers and polynomial columns, optional row/cell diff styling,
 * and click-to-inspect Full Value Popups on truncated large-field cells.
 *
 * @param {string} title - Section heading and ARIA region label.
 * @param {Array<string | number>} headers - Column header labels.
 * @param {Array<Array<string | number>>} rows - Matrix of cell text values.
 * @param {(row: number, col: number) => boolean} [selected] - Predicate highlighting key cells (`.picked`).
 * @param {{prevRow?: number, currRow?: number, cellClass?: (row: number, col: number) => string, cellInspector?: (row: number, col: number) => {fullValue: string, valueBigInt: bigint, mDegree: number, label: string} | null, mathCols?: Set<number>, subtitle?: string}} [diffOpts] - Optional decorators.
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
      const strVal = String(value);
      if (diffOpts.mathCols?.has(col)) setMathText(cell, value);
      else cell.textContent = strVal;
      if (selected(row, col)) cell.classList.add("picked");
      const extra = diffOpts.cellClass?.(row, col);
      if (extra) cell.classList.add(extra);
      const inspectInfo = diffOpts.cellInspector?.(row, col);
      if (inspectInfo && (strVal.includes("…") || strVal.includes("..."))) {
        attachValueInteraction(cell, { ...inspectInfo, displayValue: strVal });
      }
    });
  });
  wrapper.append(grid);
  section.append(wrapper);
  return section;
}

/**
 * Render one labelled key-value step card for `Step view` or `All steps grid`,
 * featuring a step eyebrow badge, prominent educational `.step-knowledge-title`,
 * optional banner, and per-row visual diff badges.
 *
 * @param {string} eyebrow - Step identifier eyebrow.
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
 * Build one streamlined Modulo Reduction step card showing full untruncated hex values,
 * no duplicate blue summary banner, no separate `Shift` row, and explicit
 * `Shifted modulus · m(x) << k` labeling placed between `Before` and `After XOR`.
 *
 * @param {object} trace - Backend `mod_reduce` trace dictionary.
 * @param {number} idx - Zero-based reduction step index.
 * @param {string} heading - Section heading prefix.
 * @param {boolean} isCurrentRegion - Attach `"Current trace step"` ARIA region label.
 * @param {string} [stagePrefix=""] - Optional stage prefix.
 * @returns {HTMLElement} Rendered modulo reduction step card.
 */
function reductionStepCard(trace, idx, heading, isCurrentRegion, stagePrefix = "") {
  const row = trace.steps[idx];
  const beforeStr = row.before_hex.toUpperCase();
  const reducerStr = row.reducer_hex.toUpperCase();
  const afterStr = row.after_hex.toUpperCase();
  const shiftLabel = "Shifted modulus · m(x) << " + row.shift;
  const labels = ["Highest degree", "Before (hex)", shiftLabel, "After XOR (hex)"];
  const isLong = beforeStr.length > 48;
  const cellMeta = [
    { diffClass: "diff-reduced", badge: "Cancel x^" + row.target_degree },
    { diffClass: "diff-reduced", badge: "Leading term x^" + row.target_degree, fullValue: beforeStr, scrollable: isLong },
    { diffClass: "diff-carried", badge: "m(x) << " + row.shift, fullValue: reducerStr, scrollable: isLong },
    { diffClass: "diff-updated", badge: "After XOR", prevText: "Before ⊕ (m(x) << " + row.shift + ")", fullValue: afterStr, scrollable: isLong },
  ];
  return stepCard(
    heading + " · step " + (idx + 1),
    reductionKnowledgeTitle(row, idx, stagePrefix),
    labels,
    ["x^" + row.target_degree + " (degree " + row.target_degree + ")", beforeStr, reducerStr, afterStr],
    isCurrentRegion,
    { cellMeta },
  );
}

/**
 * Render modulo reduction steps (`MOD_REDUCE`) in `step`, `grid`, or `table` layout mode,
 * always showing full untruncated hex values cleanly wrapped.
 *
 * @param {object} trace - Backend `mod_reduce` trace dictionary.
 * @param {number} limit - Number of steps currently revealed (`Infinity` for all).
 * @param {string} [heading="Modulo reduction"] - Section heading text.
 * @param {"step" | "grid" | "table"} [layoutMode="step"] - Active trace layout mode.
 * @param {number} [currentStep=0] - Active zero-based step index.
 * @param {boolean} [isCurrentRegion=true] - Whether the step card is the live `"Current trace step"` region.
 * @returns {HTMLElement} Rendered modulo reduction section.
 */
function reduction(trace, limit, heading = "Modulo reduction", layoutMode = "step", currentStep = 0, isCurrentRegion = true) {
  const labels = ["Highest degree", "Before (hex)", "Shifted modulus · m(x) << k (hex)", "After XOR (hex)"];
  const cells = row => [
    "x^" + row.target_degree,
    row.before_hex.toUpperCase(),
    "m(x) << " + row.shift + ": " + row.reducer_hex.toUpperCase(),
    row.after_hex.toUpperCase(),
  ];

  let section;
  if (layoutMode === "step" && trace.steps.length) {
    const idx = Math.max(0, Math.min(trace.steps.length - 1, limit === Infinity ? currentStep : limit - 1));
    section = reductionStepCard(trace, idx, heading, isCurrentRegion);
  } else if (layoutMode === "grid" && trace.steps.length) {
    section = element("section");
    section.append(element("h3", heading));
    const grid = element("div", undefined, "trace-grid-cards");
    trace.steps.slice(0, limit).forEach((_, idx) => {
      const card = reductionStepCard(trace, idx, heading, idx === currentStep && isCurrentRegion);
      grid.append(card);
    });
    section.append(grid);
  } else {
    const rows = trace.steps.slice(0, limit);
    section = table(
      heading,
      labels,
      rows.map(cells),
      () => false,
      {
        mathCols: new Set([0]),
        cellClass: (_, c) => (c === 1 ? "diff-reduced" : c === 2 ? "diff-carried" : c === 3 ? "diff-updated" : ""),
        subtitle: rows.length
          ? "Each row aligns m(x) << k under the leading term and XORs to cancel it."
          : "No reduction needed: degree is already below m",
      },
    );
  }
  section.insertBefore(mathElement("p", trace.was_reduced
    ? "Shift the modulus by k = d − m so its leading term aligns with the remainder, then XOR to cancel that term."
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
  return stepCard(
    "Bitwise XOR · x^" + bit.exp,
    xorKnowledgeTitle(bit),
    ["Bit of A", "Bit of B", "A ⊕ B"],
    [bit.a, bit.b, bit.xor],
    isCurrentRegion,
    {
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
 * Format the explicit shift-and-XOR calculation lines (`Shift left (<< 1)` and conditional `XOR m(x)`)
 * shown ABOVE the final shifted value inside Sub-Block 1 of a Shift-and-XOR multiplication card.
 *
 * @param {bigint} prevVal - Previous step's shifted value.
 * @param {bigint} currVal - Current step's shifted value.
 * @param {bigint} modPoly - Irreducible modulus `m(x)` bitmask.
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
      lines: [
        "1. Start with A(x) = {" + initHex + "} (no left shift yet on bit b_0)",
        "2. Degree < " + mDegree + ", so no ⊕ m(x) reduction needed",
      ],
      isOverflow: false,
    };
  }

  const unreducedShift = prevVal << 1n;
  if (!wasReduced) {
    if (mDegree <= 16) {
      return {
        lines: [
          "1. Shift left (<< 1): " + toPaddedBin(prevVal, mDegree) + " << 1 = " + toPaddedBin(currVal, mDegree),
          "2. Top bit x^" + mDegree + " is 0 → no ⊕ m(x) reduction needed",
        ],
        isOverflow: false,
      };
    }
    return {
      lines: [
        "1. Shift left (<< 1): {" + compactHex(prevVal) + "} << 1 = {" + compactHex(currVal) + "}",
        "2. Top bit x^" + mDegree + " is 0 → no ⊕ m(x) reduction needed",
      ],
      isOverflow: false,
    };
  }

  if (mDegree <= 16) {
    const shiftedBin = toPaddedBin(unreducedShift, mDegree + 1);
    const modBin = toPaddedBin(modPoly, mDegree + 1);
    return {
      lines: [
        "1. Shift left (<< 1): " + shiftedBin + " (overflows x^" + mDegree + ")",
        "2. XOR m(x):        ⊕ " + modBin + " (cancels x^" + mDegLabel(mDegree) + ")",
      ],
      isOverflow: true,
    };
  }

  const mask = (1n << BigInt(mDegree)) - 1n;
  const lowShifted = unreducedShift & mask;
  const lowMod = modPoly & mask;
  return {
    lines: [
      "1. Shift left (<< 1) & pop x^" + mDegree + ": {" + compactHex(lowShifted) + "}",
      "2. XOR lower m(x) taps: ⊕ (" + polynomial(lowMod) + ")",
    ],
    isOverflow: true,
  };
}

/** @param {number} m @returns {string} */
function mDegLabel(m) {
  return String(m);
}

/**
 * Build one Shift-and-XOR multiplication step card with:
 *   - No redundant blue summary banner
 *   - Clear bit-shift descriptions explicitly naming `A(x)`, `<< 1`, and `b_i` of `B(x)`
 *   - Calculation steps ALWAYS shown BEFORE the bold final answer in both Sub-Block 1 and Sub-Block 2
 *   - On-demand `Show Shift & XOR illustration` button opening a step-specific popup
 *   - Click-to-inspect Full Value Popup on truncated large-field values
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

  const partialDisp = cellHex(step.partial_hex);
  const totalDisp = cellHex(step.accumulator_hex);
  const prevPartialDisp = prevStep ? cellHex(prevStep.partial_hex) : null;
  const prevAccDisp = prevStep ? cellHex(prevStep.accumulator_hex) : "0";
  const partialShort = shortHex(step.partial_hex);
  const totalShort = shortHex(step.accumulator_hex);
  const priorShort = shortHex(prevStep?.accumulator_hex ?? "0");

  const prevBig = prevStep ? BigInt("0x" + prevStep.partial_hex) : 0n;
  const currBig = BigInt("0x" + step.partial_hex);
  const accBig = BigInt("0x" + step.accumulator_hex);
  const modBig = BigInt("0x" + (trace.reduction_poly_hex || "1"));

  const card = element("section", undefined, "trace-card multiply-step-card");
  if (isCurrentRegion) {
    card.setAttribute("role", "region");
    card.setAttribute("aria-label", "Current trace step");
  }
  card.append(
    mathElement("span", "Multiplier bit b_" + step.i + " · Step " + (idx + 1), "step-eyebrow"),
    mathElement("h3", multiplyKnowledgeTitle(step, stagePrefix, mDeg), "step-knowledge-title"),
  );

  // --- Sub-Block 1: 1. Shift & Reduce (Steps BEFORE Answer + Illustration Popup) ---
  const shiftDiffClass = idx === 0 ? "diff-unchanged" : step.reduced ? "diff-reduced" : "diff-carried";
  const shiftBadgeText = idx === 0 ? "Initial A(x)" : step.reduced ? "Reduced ⊕ m(x)" : "Shifted << 1";
  const shiftBlock = element("div", undefined, "mul-subblock mul-shift-block " + shiftDiffClass);
  const shiftHead = element("div", undefined, "mul-subblock-head");
  shiftHead.append(
    mathElement("h4", "1. Shift & Reduce", "mul-subblock-title"),
    mathElement("span", shiftBadgeText, "diff-tag " + shiftDiffClass),
  );

  // Calculation steps FIRST
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

  const illustrateBtn = element("button", "Show Shift & XOR illustration", "outline step-breakdown-btn");
  illustrateBtn.type = "button";
  illustrateBtn.addEventListener("click", () => openShiftXorIllustrationPopup(trace, idx));

  // Bold resulting answer LAST
  const shiftResultBox = element("div", undefined, "mul-step-result");
  shiftResultBox.append(element("span", "Shifted value", "mul-step-result-label"));
  const shiftValSpan = element("strong", "{" + partialDisp + "}", "mul-step-result-val");
  attachValueInteraction(shiftValSpan, {
    fullValue: step.partial_hex.toUpperCase(),
    displayValue: partialDisp,
    valueBigInt: currBig,
    mDegree: mDeg,
    label: "Step " + (idx + 1) + " · Shifted value (bit b_" + step.i + ")",
  });
  shiftResultBox.append(shiftValSpan);
  if (prevStep) {
    shiftResultBox.append(element("span", "prev: {" + prevPartialDisp + "} → now: {" + partialDisp + "}", "diff-prev-value"));
  }

  shiftBlock.append(shiftHead, breakdownBox, illustrateBtn, shiftResultBox);

  // --- Sub-Block 2: 2. Check Bit b_i & Update Sum (Steps BEFORE Answer) ---
  const sumDiffClass = step.added ? "diff-updated" : "diff-unchanged";
  const sumBadgeText = "b_" + step.i + " = " + step.multiplier_bit + (step.added ? " · Include" : " · Skip");
  const sumBlock = element("div", undefined, "mul-subblock mul-sum-block " + sumDiffClass);
  const sumHead = element("div", undefined, "mul-subblock-head");
  sumHead.append(
    mathElement("h4", "2. Check Bit b_" + step.i + " & Update Sum", "mul-subblock-title"),
    mathElement("span", sumBadgeText, "diff-tag " + sumDiffClass),
  );

  // Calculation steps FIRST
  const sumStepsBox = element("div", undefined, "reduction-breakdown");
  const checkLine = element("div", undefined, "reduction-breakdown-line");
  appendMathText(
    checkLine,
    "1. Check bit b_" + step.i + " of B(x): b_" + step.i + " = " + step.multiplier_bit +
      (step.multiplier_bit === 1 ? " (include shifted value)" : " (skip shifted value)"),
  );
  const xorLine = element("div", undefined, "reduction-breakdown-line");
  appendMathText(
    xorLine,
    step.added
      ? "2. XOR into running sum: {" + (mDeg <= 8 ? priorShort : prevAccDisp) + "} ⊕ {" + (mDeg <= 8 ? partialShort : partialDisp) + "} = {" + (mDeg <= 8 ? totalShort : totalDisp) + "}"
      : "2. Skip because b_" + step.i + " = 0 (running sum stays {" + (mDeg <= 8 ? totalShort : totalDisp) + "})",
  );
  sumStepsBox.append(checkLine, xorLine);

  // Bold resulting Running Sum LAST
  const sumResultBox = element("div", undefined, "mul-step-result");
  sumResultBox.append(element("span", "Running Sum", "mul-step-result-label"));
  const accValSpan = element("strong", "{" + totalDisp + "}", "mul-step-result-val");
  attachValueInteraction(accValSpan, {
    fullValue: step.accumulator_hex.toUpperCase(),
    displayValue: totalDisp,
    valueBigInt: accBig,
    mDegree: mDeg,
    label: "Step " + (idx + 1) + " · Running Sum (after bit b_" + step.i + ")",
  });
  sumResultBox.append(accValSpan);
  sumResultBox.append(
    element(
      "span",
      idx === 0
        ? (step.added ? "prev: {0} → now: {" + totalDisp + "}" : "stays {0}")
        : (step.added ? "prev: {" + prevAccDisp + "} → now: {" + totalDisp + "}" : "prev: {" + prevAccDisp + "} (unchanged)"),
      "diff-prev-value",
    ),
  );

  sumBlock.append(sumHead, sumStepsBox, sumResultBox);

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
      " terms so far → Running Sum = {" + totalDisp + "}";
  }

  const blocksGrid = element("div", undefined, "mul-subblocks-grid");
  blocksGrid.append(shiftBlock, sumBlock);
  card.append(blocksGrid, formulaStrip);
  return card;
}

/**
 * Build the clickable multiplier-bit strip for Shift-and-XOR multiplication.
 *
 * @param {object} trace - Backend `shift-and-xor` trace dictionary.
 * @param {number} current - Currently active bit index.
 * @param {(index: number) => void} chooseBit - Callback when user clicks/navigates a bit.
 * @param {boolean} [locked=false] - True when playback is locked outside `Step view`.
 * @returns {HTMLElement} Wrapper containing heading and `.multiplier-bits` strip.
 */
function buildMultiplierBitStrip(trace, current, chooseBit, locked = false) {
  const wrap = element("div", undefined, "multiplier-bits-wrap");
  const bits = element("div", undefined, "multiplier-bits" + (locked ? " is-locked" : ""));
  bits.setAttribute("role", "group");
  bits.setAttribute("aria-label", "Multiplier bits");
  for (const [index, step] of trace.steps.entries()) {
    const button = element("button", undefined, "multiplier-bit");
    button.type = "button";
    button.append(element("small", step.i), element("span", step.multiplier_bit));
    button.setAttribute("aria-label", "Multiplier bit " + step.i);
    button.setAttribute("aria-description", "Value " + step.multiplier_bit);
    button.setAttribute("aria-pressed", String(!locked && index === current));
    button.disabled = locked;
    button.tabIndex = !locked && index === current ? 0 : -1;
    if (!locked) button.addEventListener("click", () => chooseBit(index));
    bits.append(button);
  }
  if (!locked) {
    bits.addEventListener("keydown", event => {
      const positions = { ArrowLeft: current - 1, ArrowRight: current + 1, Home: 0, End: trace.steps.length - 1 };
      if (!Object.hasOwn(positions, event.key)) return;
      const nextIdx = Math.max(0, Math.min(positions[event.key], trace.steps.length - 1));
      if (nextIdx === current) return;
      event.preventDefault();
      chooseBit(nextIdx);
    });
  }
  wrap.append(element("h3", "Multiplier bits of B(x) · low to high"), bits);
  return wrap;
}

/**
 * Render the Shift-and-XOR multiplication visualizer across `step`, `grid`, and `table` layouts.
 *
 * @param {object} trace - Backend `shift-and-xor` trace dictionary.
 * @param {number} limit - Number of steps revealed.
 * @param {number} current - Currently focused multiplier-bit step index.
 * @param {"step" | "grid" | "table"} layoutMode - Active layout mode.
 * @param {boolean} compactValues - Whether compact large-field values are enabled.
 * @param {(index: number) => void} chooseBit - Callback invoked when user selects a bit.
 * @param {{showBits?: boolean, isCurrentRegion?: boolean, stagePrefix?: string}} [options] - Optional flags.
 * @returns {HTMLElement} Populated multiplication visualizer `<section>`.
 */
function multiply(trace, limit, current, layoutMode, compactValues, chooseBit, options = {}) {
  const { showBits = true, isCurrentRegion = true, stagePrefix = "" } = options;
  const section = element("section");
  if (!trace.steps.length) {
    section.append(element("p", "The multiplier is zero. There are no partial products to add."));
    return section;
  }
  const mDeg = trace.m ?? trace.m_degree ?? 8;
  const active = trace.steps[current] || trace.steps[0];
  if (showBits && layoutMode === "step") {
    section.append(buildMultiplierBitStrip(trace, current, chooseBit, false));
  }

  const cellHex = text => formatCellText(text, "hex", compactValues, mDeg);

  if (layoutMode === "step") {
    section.append(multiplyStepCard(trace, current, compactValues, isCurrentRegion, stagePrefix));
    return section;
  }

  if (layoutMode === "grid") {
    const grid = element("div", undefined, "trace-grid-cards");
    trace.steps.slice(0, limit).forEach((_, idx) => {
      const card = multiplyStepCard(trace, idx, compactValues, idx === current && isCurrentRegion, stagePrefix);
      grid.append(card);
    });
    section.append(grid);
    return section;
  }

  const steps = trace.steps.slice(0, limit);
  const selected = steps.filter(step => step.added);
  const shiftTable = table(
    "Table 1 · Shifts and reductions",
    ["i", "Shifted A(x) mod m (hex)", "Reduced?", "Polynomial"],
    steps.map(step => [
      step.i,
      cellHex(step.partial_hex),
      step.reduced ? "Yes" : "No",
      formatCellText(step.partial_poly, "algebraic", compactValues, mDeg),
    ]),
    () => false,
    {
      mathCols: new Set([3]),
      cellClass: (r, c) => (c === 2 && steps[r]?.reduced ? "diff-reduced" : c === 1 ? (steps[r]?.reduced ? "diff-reduced" : "diff-carried") : ""),
      cellInspector: (r, c) => {
        if (c !== 1 && c !== 3) return null;
        const st = steps[r];
        if (!st) return null;
        return {
          fullValue: c === 1 ? st.partial_hex.toUpperCase() : st.partial_poly,
          valueBigInt: BigInt("0x" + st.partial_hex),
          mDegree: mDeg,
          label: "Bit b_" + st.i + " · Shifted A(x) mod m",
        };
      },
    },
  );
  const partialTable = table(
    "Table 2 · Selected partial products",
    ["i", "Bit of B", "Partial product (hex)", "Running Sum (hex)"],
    selected.map(step => [step.i, step.multiplier_bit, cellHex(step.partial_hex), cellHex(step.accumulator_hex)]),
    (_, col) => col === 3,
    {
      cellClass: (_, col) => (col === 3 ? "diff-updated" : ""),
      cellInspector: (r, c) => {
        if (c !== 2 && c !== 3) return null;
        const st = selected[r];
        if (!st) return null;
        const hexStr = c === 2 ? st.partial_hex : st.accumulator_hex;
        return {
          fullValue: hexStr.toUpperCase(),
          valueBigInt: BigInt("0x" + hexStr),
          mDegree: mDeg,
          label: "Bit b_" + st.i + (c === 2 ? " · Partial product" : " · Running Sum"),
        };
      },
    },
  );
  section.append(shiftTable, partialTable);
  return section;
}

/**
 * Build the Extended Euclid Step Inspector Square for a single Table 4.7 step,
 * featuring 4 consistent step-specific derivation buttons (`How Q is calculated`,
 * `How T1 is calculated`, `How T2 is calculated`, `How T3 is calculated`),
 * Previous-to-Current diff badges, and Full-Value Inspector popups on truncated cells.
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
  const bigCell = (targetRow, term) => {
    const hexRaw = targetRow.cells[term]?.hex;
    if (!hexRaw || hexRaw === "-") return null;
    try { return BigInt("0x" + hexRaw); } catch { return null; }
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
  const qDisp = displayCell(row, "Q");
  if (isMathNotation) qBadge.append(mathElement("span", qDisp));
  else qBadge.append(document.createTextNode(qDisp));
  attachValueInteraction(qBadge, {
    fullValue: fullCell(row, "Q"),
    displayValue: qDisp,
    valueBigInt: bigCell(row, "Q"),
    mDegree: mDeg,
    label: "Step " + row.step + " · Quotient Q(x)",
  });
  badges.append(qBadge);

  const formulaText = row.step === 0
    ? "A ← (1, 0, m(x)) · B ← (0, 1, b(x))"
    : "Q = A3 div B3 · T1 = A1 ⊕ Q·B1 · T2 = A2 ⊕ Q·B2 · T3 = A3 mod B3";
  head.append(titleWrap, badges, mathElement("code", formulaText, "euclid-formula-pill"));

  // Step-specific derivation breakdown buttons (Q, T1, T2, T3)
  const breakdownBar = element("div", undefined, "euclid-breakdown-bar");
  breakdownBar.setAttribute("role", "group");
  breakdownBar.setAttribute("aria-label", "Step " + row.step + " calculation breakdowns");
  for (const [key, label] of [
    ["Q", "How Q is calculated"],
    ["T1", "How T1 is calculated"],
    ["T2", "How T2 is calculated"],
    ["T3", "How T3 is calculated"],
  ]) {
    const btn = mathElement("button", label, "outline step-breakdown-btn");
    btn.type = "button";
    btn.dataset.euclidBreakdown = key;
    if (!prevRow) {
      btn.disabled = true;
      btn.setAttribute("aria-disabled", "true");
    } else {
      btn.addEventListener("click", () => openEuclidDerivationPopup(key, prevRow, row, mDeg));
    }
    breakdownBar.append(btn);
  }
  if (!prevRow) {
    breakdownBar.append(element("span", "Available from Step 1 onward", "euclid-breakdown-note"));
  }

  // Concise 1-line transition banner summarizing Step k-1 -> Step k.
  const bannerText = row.step === 0
    ? "Step 0 (Init): A starts at (1, 0, m(x)) and B starts at (0, 1, b(x))."
    : "Step " + (row.step - 1) + " → Step " + row.step + ": B shifted into A; Q = " + bannerCell(row, "Q") +
    " produced new B1, B2, B3" + (isFinal ? (success ? " (B3 = 1 → Inverse Found)" : " (B3 = 0 → No Inverse)") : "") + ".";
  const banner = mathElement("p", bannerText, "diff-banner");

  const triples = element("div", undefined, "euclid-triples-grid");

  // Left card: Triple A = (A1, A2, A3)
  const cardA = element("div", undefined, "euclid-triple-card is-carried");
  const headA = element("h4", "Triple A(x) ");
  headA.append(mathElement("small", row.step > 0 ? "A ← prev B" : "Modulus m(x)"));
  const dlA = element("dl", undefined, "equivalents");
  for (const term of ["A1", "A2", "A3"]) {
    const dt = mathElement("dt", term + "(x)");
    const currVal = displayCell(row, term);
    const fullVal = fullCell(row, term);
    const valBig = bigCell(row, term);
    const common = { fullValue: fullVal, valueBigInt: valBig, mDegree: mDeg, label: "Step " + row.step + " · " + term + "(x)", isMathValue: isMathNotation };
    let meta = { ...common, diffClass: "diff-unchanged", badge: "Init" };
    if (prevRow) {
      const sameAsPrevA = row[term] === prevRow[term];
      const prevAVal = displayCell(prevRow, term);
      if (isFinal && !success && term === "A3") {
        meta = { ...common, diffClass: "diff-reduced", badge: "GCD / No Inverse", prevText: sameAsPrevA ? undefined : "was: " + prevAVal, extraClass: "picked is-gcd" };
      } else if (sameAsPrevA) {
        meta = { ...common, diffClass: "diff-unchanged", badge: "Unchanged" };
      } else {
        meta = { ...common, diffClass: "diff-carried", badge: "← prev B" + term[1], prevText: "was: " + prevAVal };
      }
    } else if (isFinal && !success && term === "A3") {
      meta = { ...common, diffClass: "diff-reduced", badge: "GCD / No Inverse", extraClass: "picked is-gcd" };
    }
    dlA.append(dt, buildDiffValueNode(currVal, meta));
  }
  cardA.append(headA, dlA);

  // Right card: Triple B = (B1, B2, B3)
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
    const valBig = bigCell(row, term);
    const common = { fullValue: fullVal, valueBigInt: valBig, mDegree: mDeg, label: "Step " + row.step + " · " + term + "(x)", isMathValue: isMathNotation };
    let meta = { ...common, diffClass: "diff-unchanged", badge: "Init" };
    if (prevRow) {
      const sameAsPrevB = row[term] === prevRow[term];
      const prevBVal = displayCell(prevRow, term);
      if (isFinal && success && term === "B2") {
        meta = { ...common, diffClass: "diff-updated", badge: "Inverse Found", prevText: sameAsPrevB ? undefined : "was: " + prevBVal, extraClass: "picked" };
      } else if (sameAsPrevB) {
        meta = { ...common, diffClass: "diff-unchanged", badge: "Unchanged" };
      } else {
        meta = { ...common, diffClass: "diff-updated", badge: "New T" + term[1], prevText: "was: " + prevBVal };
      }
    } else if (isFinal && success && term === "B2") {
      meta = { ...common, diffClass: "diff-updated", badge: "Inverse Found", extraClass: "picked" };
    }
    dlB.append(dt, buildDiffValueNode(currVal, meta));
  }
  cardB.append(headB, dlB);

  triples.append(cardA, cardB);
  square.append(head, breakdownBar, banner, triples);
  return square;
}

/**
 * Render the Stallings Chapter 4 Table 4.7 Extended Euclid trace in `step`, `grid`, or `table` mode.
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
      grid.append(card);
    }
    section.append(grid);
    if (limit >= rows.length) section.append(mathElement("p", endingText, "euclid-termination-note"));
    return section;
  }

  const visibleRows = rows.slice(0, limit);
  const tableView = table(
    "Table 4.7 · Extended Euclid",
    ["Step", ...labels],
    visibleRows.map(row => [row.step, ...cells(row)]),
    (row, col) => row === rows.length - 1 && (success ? col === 6 : col === 4),
    {
      mathCols: notation === "algebraic" ? new Set([1, 2, 3, 4, 5, 6, 7]) : undefined,
      subtitle: rows.length ? "Complete Table 4.7 progression from initialization to termination." : undefined,
      cellClass: (r, c) => {
        if (r === 0 || c === 0) return "";
        if (r === rows.length - 1 && ((success && c === 6) || (!success && c === 4))) {
          return success ? "diff-updated" : "diff-reduced";
        }
        if (c >= 2 && c <= 4) return "diff-carried";
        if (c >= 5 && c <= 7) return "diff-updated";
        return "";
      },
      cellInspector: (r, c) => {
        if (c === 0) return null;
        const row = visibleRows[r];
        const term = terms[c - 1];
        if (!row || !term) return null;
        const hexRaw = row.cells[term]?.hex;
        if (!hexRaw || hexRaw === "-") return null;
        return {
          fullValue: notation === "hex" ? hexRaw.toUpperCase() : row.cells[term][notation],
          valueBigInt: BigInt("0x" + hexRaw),
          mDegree: mDeg,
          label: "Step " + row.step + " · " + term + "(x)",
        };
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
 * - Always defaults to **`Step view`** across ALL 13 field sizes (`m in {2..8, 163..571}`) with
 *   built-in side-by-side **Previous → Current** comparison from Step 1 onward (single card on Step 0).
 * - **`All steps grid`** renders an inline full-width single-column stack with 4-step incremental
 *   `Show more` pagination (never opening a maximized overlay).
 * - **`Classic table`** renders a concise color legend above every table.
 * - Playback toolbar controls and step keyboard shortcuts are locked whenever `All steps grid`
 *   or `Classic table` is active, pausing any running animation until returning to `Step view`.
 *
 * @param {HTMLElement} panel - Outer `<section>` toggled hidden when no trace is active.
 * @param {HTMLElement} body - Container where trace tables or step cards are rendered.
 * @param {HTMLElement} tools - Toolbar container populated with stepper and notation controls.
 * @returns {{show: (newTrace: object | null, newReductions?: object | null) => void}} Controller API.
 */
export function createTraceView(panel, body, tools) {
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  let timer = null;
  let cascadeTimer = null;
  let cascadeTarget = null;
  let trace = null;
  let reductions = null;
  let notation = "hex";
  let current = 0;
  let layoutMode = "step";
  let compactValues = false;
  let gridVisibleCount = GRID_PAGE_SIZE;
  let speed = "normal";

  let playbackRow;
  let stepLabel;
  let scrubber;
  let speedSelect;
  let firstButton;
  let prevButton;
  let firstChangedButton;
  let playButton;
  let nextButton;
  let lastButton;
  let compactToggleButton;
  let modesIndicator;
  let modePills = {};

  /**
   * Synchronize a control's `disabled` property and `aria-disabled` attribute together.
   *
   * @param {HTMLElement | undefined} ctrl - Target button, select, or range input.
   * @param {boolean} isDisabled - Desired disabled state.
   */
  function setControlDisabled(ctrl, isDisabled) {
    if (!ctrl) return;
    const flag = Boolean(isDisabled);
    ctrl.disabled = flag;
    ctrl.setAttribute("aria-disabled", String(flag));
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
   * Update playback control disabled states, locking and subtly dimming the entire playback row
   * whenever `All steps grid` or `Classic table` is active.
   */
  function syncPlaybackControls() {
    const count = length();
    const activeStep = current ?? 0;
    const lockedByMode = layoutMode !== "step";
    const singleOrEmpty = count <= 1;

    if (playbackRow) {
      playbackRow.classList.toggle("is-locked", lockedByMode);
    }

    if (lockedByMode || singleOrEmpty) {
      setControlDisabled(firstButton, true);
      setControlDisabled(prevButton, true);
      setControlDisabled(firstChangedButton, true);
      setControlDisabled(playButton, true);
      setControlDisabled(speedSelect, lockedByMode || singleOrEmpty);
      setControlDisabled(nextButton, true);
      setControlDisabled(lastButton, true);
      setControlDisabled(scrubber, true);
      return;
    }

    setControlDisabled(playButton, false);
    setControlDisabled(speedSelect, false);
    setControlDisabled(scrubber, false);
    setControlDisabled(firstButton, activeStep <= 0);
    setControlDisabled(prevButton, activeStep <= 0);
    setControlDisabled(nextButton, activeStep >= count - 1);
    setControlDisabled(lastButton, activeStep >= count - 1);

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
      setControlDisabled(firstChangedButton, targetIdx === null || activeStep === targetIdx);
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
   * @param {boolean} [showBitStrip=false] - Whether to render `.multiplier-bits` inside this pane.
   * @returns {HTMLElement} Rendered step node.
   */
  function renderSingleStepNode(stepIdx, activeCompactValues, isCurrentRegion, showBitStrip = false) {
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
      return reduction(trace, stepIdx + 1, "Modulo reduction", "step", stepIdx, isCurrentRegion);
    }
    if (trace.algorithm === "bitwise-xor") {
      return xor(trace, stepIdx + 1, "step", stepIdx, isCurrentRegion);
    }
    if (trace.algorithm === "shift-and-xor") {
      return multiply(trace, stepIdx + 1, stepIdx, "step", activeCompactValues, selectBit, {
        showBits: showBitStrip,
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
          showBits: showBitStrip,
          isCurrentRegion,
          stagePrefix: "Stage 2 (Shift-and-XOR A × B^-1) · ",
        },
      );
    }
    return element("div");
  }

  /**
   * Render trace content into the body container for the active layout mode.
   */
  function renderBody() {
    body.replaceChildren();
    if (!trace) return;
    const count = length();
    const activeStep = current ?? 0;

    // Color legend: Step diff legend in Step/Grid views, concise Table highlight legend in Classic table.
    if (count > 0) {
      if (layoutMode === "table") {
        body.append(createTableColorLegend());
      } else {
        body.append(createDiffLegend());
      }
    }

    // Auto-expand initial-reduction details whenever operands had degree >= m (full untruncated hex).
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
            const beforeHex = stepRow.before_hex.toUpperCase();
            const reducerHex = stepRow.reducer_hex.toUpperCase();
            const afterHex = stepRow.after_hex.toUpperCase();
            const shiftAmt = stepRow.target_degree - row.m_degree;
            const eqLine = element("p", undefined, "initial-reduction-eq");
            appendMathText(
              eqLine,
              "Step " + (stepIdx + 1) + " (cancel x^" + stepRow.target_degree + "): {" +
                beforeHex + "} ⊕ (m(x) << " + shiftAmt + " = {" + reducerHex + "}) = {" + afterHex + "}",
            );
            eqList.append(eqLine);
          });
          details.append(eqList);
        }
        details.append(reduction(row, Infinity, "Initial reduction", "table", 0));
        body.append(details);
      }
    }

    // --- Step view: Single card cleanly on Step 0, side-by-side Previous -> Current from Step 1 onward ---
    if (layoutMode === "step" && count > 0) {
      // Place multiplier-bits strip once at top so both Previous and Current cards align cleanly.
      if (trace.algorithm === "shift-and-xor" && trace.steps.length) {
        body.append(buildMultiplierBitStrip(trace, activeStep, selectBit, false));
      } else if (trace.trace_type === "gf2m_division_two_stage") {
        const invLen = trace.stage_1_inverse.table_4_7_rows.length;
        if (activeStep >= invLen && trace.stage_2_multiply.steps.length) {
          body.append(
            buildMultiplierBitStrip(
              trace.stage_2_multiply,
              activeStep - invLen,
              step => selectBit(invLen + step),
              false,
            ),
          );
        }
      }

      if (activeStep === 0) {
        body.append(renderSingleStepNode(0, compactValues, true, false));
        return;
      }

      const grid = element("div", undefined, "diff-compare-grid");

      const prevPane = element("div", undefined, "diff-compare-pane is-prev");
      prevPane.setAttribute("role", "region");
      prevPane.setAttribute("aria-label", "Previous trace step");
      prevPane.append(element("div", "Previous · Step " + activeStep, "diff-compare-pane-head"));
      prevPane.append(renderSingleStepNode(activeStep - 1, compactValues, false, false));

      const arrow = element("div", "→", "diff-compare-arrow");
      arrow.setAttribute("aria-hidden", "true");

      const currPane = element("div", undefined, "diff-compare-pane is-curr");
      currPane.append(element("div", "Current · Step " + (activeStep + 1), "diff-compare-pane-head"));
      currPane.append(renderSingleStepNode(activeStep, compactValues, true, false));

      grid.append(prevPane, arrow, currPane);
      body.append(grid);
      return;
    }

    const limit = layoutMode === "grid" ? Math.min(count, gridVisibleCount) : Infinity;

    if (trace.trace_type === "tabular_steps") {
      if (layoutMode === "grid" && trace.rows.length) {
        const view = element("section");
        view.append(element("h3", trace.title));
        const grid = element("div", undefined, "trace-grid-cards");
        trace.rows.slice(0, limit).forEach((_, idx) => {
          grid.append(renderSingleStepNode(idx, compactValues, idx === 0, false));
        });
        view.append(grid);
        body.append(view);
      } else {
        body.append(table(trace.title, trace.headers, trace.rows, trace.selected, {
          subtitle: trace.rows.length ? trace.title + " (" + trace.rows.length + " steps)" : undefined,
        }));
      }
    }
    if (trace.trace_type === "mod_reduce") {
      body.append(reduction(trace, limit, "Modulo reduction", layoutMode, activeStep));
    }
    if (trace.algorithm === "bitwise-xor") {
      body.append(
        mathElement("p", "Add or subtract each pair of bits modulo 2. Two ones cancel."),
        xor(trace, limit, layoutMode, activeStep),
      );
    }
    if (trace.algorithm === "shift-and-xor") {
      body.append(multiply(trace, limit, activeStep, layoutMode, compactValues, selectBit, { showBits: false }));
    }
    if (trace.trace_type === "extended_euclid_table_4_7") {
      body.append(euclid(trace, limit, notation, layoutMode, compactValues, activeStep));
    }
    if (trace.trace_type === "gf2m_division_two_stage") {
      const inverse = trace.stage_1_inverse;
      const inverseSteps = inverse.table_4_7_rows.length;
      const remaining = limit - inverseSteps;
      body.append(
        euclid(
          inverse,
          Math.min(limit, inverseSteps),
          notation,
          layoutMode,
          compactValues,
          Math.min(activeStep, inverseSteps - 1),
          true,
          "Stage 1 (Extended Euclid Inverse) · ",
        ),
      );
      if (remaining > 0) {
        const local = Math.max(0, activeStep - inverseSteps);
        body.append(
          multiply(
            trace.stage_2_multiply,
            remaining,
            local,
            layoutMode,
            compactValues,
            step => selectBit(inverseSteps + step),
            { showBits: false, stagePrefix: "Stage 2 (Shift-and-XOR A × B^-1) · " },
          ),
        );
      }
    }

    // Incremental "Show more" pagination button in All steps grid
    if (layoutMode === "grid" && limit < count) {
      const pager = element("div", undefined, "trace-grid-pager");
      const moreBtn = element(
        "button",
        "Show more (showing " + limit + " of " + count + ")",
        "outline trace-show-more-btn",
      );
      moreBtn.type = "button";
      moreBtn.addEventListener("click", () => {
        gridVisibleCount = Math.min(count, gridVisibleCount + GRID_PAGE_SIZE);
        render();
      });
      pager.append(moreBtn);
      body.append(pager);
    }
  }

  /**
   * Keep the selected multiplier-bit chip scrolled into view horizontally.
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
    return selected;
  }

  /**
   * Update toolbar labels, mode pills, gliding indicator, scrubber, playback locks, and trace DOM.
   * @returns {HTMLElement | undefined} Active multiplier-bit button, if rendered.
   */
  function render() {
    const previousLeft = body.querySelector(".multiplier-bits")?.scrollLeft ?? 0;
    const count = length();
    if (stepLabel) {
      if (layoutMode === "step") {
        stepLabel.textContent = "Step " + ((current ?? 0) + 1) + " of " + count;
      } else if (layoutMode === "grid") {
        stepLabel.textContent = "Showing " + Math.min(count, gridVisibleCount) + " of " + count;
      } else {
        stepLabel.textContent = "All " + count + " steps";
      }
      if (scrubber) {
        scrubber.max = String(Math.max(1, count));
        scrubber.value = String((current ?? 0) + 1);
      }
      if (compactToggleButton) {
        compactToggleButton.textContent = compactValues ? "Full m-bit" : "Compact values";
        compactToggleButton.setAttribute("aria-pressed", String(compactValues));
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
   * Cascade sequentially (`start -> ... -> targetStep`) through intermediate steps in `Step view`
   * so non-adjacent jumps clearly reveal intermediate state changes.
   *
   * @param {number} targetStep - Destination zero-based step index.
   * @param {{focusBit?: boolean}} [opts={}] - Restore keyboard focus onto the active bit button.
   */
  function cascadeTo(targetStep, { focusBit = false } = {}) {
    if (layoutMode !== "step") return;
    const count = length();
    if (!count) return;
    const clamped = Math.max(0, Math.min(count - 1, targetStep));
    const start = current ?? 0;
    stop();

    if (Math.abs(clamped - start) <= 1 || reducedMotion.matches) {
      current = clamped;
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
    if (layoutMode !== "step") return;
    cascadeTo(step, { focusBit: true });
  }

  /**
   * Switch between the three layout modes (`"step"`, `"grid"`, `"table"`),
   * pausing any playback and resetting the 4-step grid pagination when entering `"grid"`.
   *
   * @param {"step" | "grid" | "table"} nextMode - Target layout mode.
   */
  function setLayoutMode(nextMode) {
    stop();
    layoutMode = nextMode;
    if (nextMode === "grid") {
      gridVisibleCount = GRID_PAGE_SIZE;
    }
    if (current === null) current = 0;
    render();
  }

  /**
   * Load a new trace payload into the viewer and rebuild the clean 2-row toolbar.
   * Always defaults to `"step"` (`Step view`) across all 13 field sizes (`m in {2..8, 163..571}`).
   *
   * @param {object | null} newTrace - Trace dictionary from the API, or `null` to hide panel.
   * @param {object | null} [newReductions] - Optional map of pre-reduced operands `{a?, b?}`.
   */
  function show(newTrace, newReductions) {
    stop();
    trace = newTrace;
    reductions = newReductions;
    const deg = traceDegree();
    layoutMode = "step";
    compactValues = deg > 8;
    current = 0;
    gridVisibleCount = GRID_PAGE_SIZE;
    panel.hidden = !trace;
    tools.replaceChildren();
    playbackRow = stepLabel = scrubber = speedSelect = firstButton = prevButton = firstChangedButton = playButton = nextButton = lastButton = undefined;
    compactToggleButton = modesIndicator = undefined;
    modePills = {};
    if (!trace) { renderBody(); return; }

    const count = length();
    if (!count) { renderBody(); return; }

    const row1 = element("div", undefined, "trace-toolbar-row trace-view-row");
    playbackRow = element("div", undefined, "trace-toolbar-row trace-playback-row");

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

    // Row 1.3: Compact values / Full m-bit toggle (omit for mod_reduce which always shows full values)
    if (trace.trace_type !== "mod_reduce") {
      compactToggleButton = element("button", compactValues ? "Full m-bit" : "Compact values", "outline trace-compact-toggle");
      compactToggleButton.type = "button";
      compactToggleButton.setAttribute("aria-pressed", String(compactValues));
      compactToggleButton.addEventListener("click", () => {
        compactValues = !compactValues;
        render();
      });
      row1.append(compactToggleButton);
    }

    // Row 2: 5-Button Playback Bar + Interactive Step Scrubber + Progress Counter
    stepLabel = element("span", undefined, "trace-progress");
    stepLabel.setAttribute("aria-live", "polite");

    function advance(next) {
      if (layoutMode !== "step") return;
      current = Math.max(0, Math.min(count - 1, next));
      render();
    }

    firstButton = element("button", "First step", "quiet");
    firstButton.type = "button";
    firstButton.addEventListener("click", () => {
      if (layoutMode !== "step" || (cascadeTarget ?? current ?? 0) <= 0) return;
      stop();
      advance(0);
    });

    prevButton = element("button", "Previous", "quiet");
    prevButton.type = "button";
    prevButton.setAttribute("aria-label", "Previous step");
    prevButton.title = "Previous step";
    prevButton.addEventListener("click", () => {
      if (layoutMode !== "step") return;
      const baseIdx = cascadeTarget ?? (current ?? 0);
      if (baseIdx <= 0) return;
      stop();
      advance(baseIdx - 1);
    });

    firstChangedButton = element("button", "First changed bit", "outline trace-first-changed-btn");
    firstChangedButton.type = "button";
    firstChangedButton.addEventListener("click", () => {
      if (layoutMode !== "step") return;
      const targetIdx = findFirstChangedStep(trace);
      if (targetIdx === null || (current ?? 0) === targetIdx) return;
      stop();
      current = targetIdx;
      render();
    });

    playButton = element("button", "Play animation", "quiet");
    playButton.type = "button";
    playButton.setAttribute("aria-pressed", "false");

    speedSelect = element("select", undefined, "trace-speed");
    speedSelect.setAttribute("aria-label", "Trace animation speed");
    for (const [val, label, ms] of [
      ["slow", "Slow (1.8s)", 1800],
      ["normal", "Normal (0.9s)", 900],
      ["fast", "Fast (0.45s)", 450],
    ]) {
      const opt = element("option", label);
      opt.value = val;
      opt.dataset.ms = String(ms);
      if (val === speed) opt.selected = true;
      speedSelect.append(opt);
    }

    function startPlayback() {
      if (layoutMode !== "step" || count <= 1) return;
      if (timer) {
        stop();
        return;
      }
      stopCascade();
      if (current === null || current >= count - 1) advance(0);
      else render();
      playButton.textContent = "Pause";
      playButton.setAttribute("aria-pressed", "true");
      const intervalMs = PLAY_SPEED_MS[speed] || PLAY_SPEED_MS.normal;
      timer = setInterval(() => {
        if (layoutMode !== "step" || current >= count - 1) stop();
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
      if (layoutMode !== "step") return;
      const baseIdx = cascadeTarget ?? (current ?? 0);
      if (baseIdx >= count - 1) return;
      stop();
      advance(baseIdx + 1);
    });

    lastButton = element("button", "Last step", "quiet");
    lastButton.type = "button";
    lastButton.addEventListener("click", () => {
      if (layoutMode !== "step" || (cascadeTarget ?? current ?? 0) >= count - 1) return;
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
      if (layoutMode !== "step") return;
      cascadeTo(Number(scrubber.value) - 1);
    });

    playbackRow.append(
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
    tools.append(row1, playbackRow);
    render();
  }

  // Enforce step-boundary keyboard shortcuts strictly in Step view (locked in Grid & Classic table).
  panel.addEventListener("keydown", event => {
    if (layoutMode !== "step") return;
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
      render();
    } else if (event.key === "Home") {
      if (activeStep <= 0) return;
      event.preventDefault();
      stop();
      current = 0;
      render();
    } else if (event.key === "ArrowRight") {
      if (activeStep >= count - 1) return;
      event.preventDefault();
      stop();
      current = activeStep + 1;
      render();
    } else if (event.key === "End") {
      if (activeStep >= count - 1) return;
      event.preventDefault();
      stop();
      current = count - 1;
      render();
    }
  });

  return { show };
}
