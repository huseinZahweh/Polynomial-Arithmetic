/**
 * @fileoverview Interactive per-view spotlight walkthroughs for the Finite Field Lab
 * with true HTML `<sup>`/`<sub>` math typography in tooltips.
 *
 * Original Author: Ali Zahreddine - Milestone 4, Integration & Milestone 6 (Waves 1-4).
 *
 * Provides contextual guided tours for all five lab views (Calculator, Lessons, Modulus
 * explorer, Applications, Compare multiplication), dynamically falling back to the triggering
 * action button whenever a step's result section has not yet been calculated, and
 * automatically re-highlighting newly rendered results on `lab:calculation-result` events.
 */

import { setMathText } from "./notation.js";

/**
 * Guided walkthrough steps for the main Calculator view.
 * Tuple shape: `[selector, title, description, fallback?, requiredChild?]`.
 * @type {Array<Array>}
 */
const calculatorSteps = [
  [".setting", "Choose a field",
    "Field degree sets how many bits fit in one element. Watch the banner and the modulus update. Use Hex, Binary, or Polynomial to change notation without changing operand values."],
  [".operands", "Enter the operands",
    "Type values into A(x) and B(x), or view the locked Modulus m(x) card on Reduce and Inverse. Hex inputs auto-uppercase, Polynomial inputs use clean x^k notation (accepting pasted superscripts like x^6), and the two non-selected notations update live below. In fields up to eight bits, click the checkboxes to toggle individual coefficients."],
  [".calculator .section-head", "Generate or upload operands",
    "Choose Sparse or Dense and click Random operands to fill both inputs. Upload accepts .txt or .json files. When a file contains several pairs, choose one from the pair list."],
  [".operations", "Pick an operation",
    "Add and Subtract both use XOR. Reduce takes A modulo the field polynomial. Multiply uses both operands, Inverse gives A^-1, and Divide gives A ÷ B."],
  [".action", "Run the calculation",
    "Click Calculate to run the selected operation. Validation or zero-inverse errors appear in a sleek top-center alert without obscuring your inputs."],
  [".examples", "Try a textbook example",
    "Chapter 4 loads and multiplies 57 and 83 in the 8-bit field. Chapter 5 loads and inverts 95. Both examples calculate immediately."],
  ["#result", "Read, copy, or export the full answer",
    "Calculate displays the complete untruncated result across Hex, Binary, and Polynomial notations with verification and performance badges. Use Copy result, Back to inputs, or Export to Markdown/JSON."],
  ["#trace-panel", "Step through or inspect all steps",
    "Every calculation opens in Step view with built-in Previous → Current comparison from Step 1 onward. Switch to All steps grid (inline 4-step pagination with Show more) or Classic table (with a color highlight legend). Playback controls lock automatically outside Step view."],
  ["#trace-body", "Open Full-Value & Step Breakdown Popups",
    "In large fields (GF(2^163) to GF(2^571)), click any truncated value marked with an expand icon to open the Full Value Inspector popup with Hex, Binary, Polynomial, and a Copy button. Inside Extended Euclid steps click How Q / T1 / T2 / T3 is calculated, or click Show Shift & XOR illustration in multiplication steps."],
  ["#compare-product", "Compare multiplication methods",
    "Click Compare multiplication methods to run Shift-and-XOR side-by-side against Carry-Free Multiplication + Euclidean Long Division on the exact same field and operands.",
    ["#presets", "Load the Chapter 4 example to show the comparison shortcut."]],
  ["#share", "Share a link to any page",
    "Share link encodes your active page and parameters into a compact URL. Open it in another tab to restore the exact calculation, lesson section, modulus check, application demo, or comparison."],
];

/**
 * Walkthrough registry keyed by `data-lab-view` attribute name.
 * @type {Record<string, {name: string, fallback: [string, string], steps: Array<Array>}>}
 */
const walkthroughs = {
  calculator: {
    name: "Page walkthrough",
    fallback: ["#calculate", "Click Calculate to show this section."],
    steps: calculatorSteps,
  },
  lessons: {
    name: "Lessons walkthrough",
    fallback: ["#lesson-hub", "Select a lesson from the catalog."],
    steps: [
      ["#lesson-hub", "Choose a lesson topic",
        "Pick from 7 self-contained visual lessons covering GF(2^m) foundations, modulo-2 XOR addition and subtraction, modular reduction, Shift-and-XOR multiplication, Extended Euclid (Table 4.7), division, and cryptographic standards."],
      ["#lesson-subtabs", "Jump between lesson sections",
        "Use the top section navigation bar to jump directly to any topic within the opened lesson."],
      ["#lesson-stage", "Read visual explanations & interactive checks",
        "Every section renders cleanly in one scrollable card with Z_2 truth tables, worked classroom examples, interactive bit sandboxes, and quick self-check quizzes."],
      [".lesson-footer", "Move linearly through the curriculum",
        "Use Previous section and Next section at the bottom to step seamlessly through every section across all 7 lessons."],
    ],
  },
  modulus: {
    name: "Modulus walkthrough",
    fallback: ["#modulus-form button[type=submit]", "Click Check irreducibility to see the result."],
    steps: [
      ["#modulus-form", "Choose a polynomial",
        "Enter a binary polynomial in clean x^k notation (pasted superscripts like x^8 and lowercase hex auto-normalize), generate a Random polynomial, load the calculator's current modulus, or test reducible x^8 + 1."],
      ["#modulus-result", "Read the irreducibility result",
        "An irreducible polynomial of degree m defines GF(2^m). A reducible polynomial has smaller factors, so some nonzero values have no inverse."],
      ["#modulus-witness .witness", "See two nonzero factors multiply to zero",
        "Each factor is nonzero. Their product equals the modulus and leaves remainder zero.",
        ["#modulus-example", "Click Try reducible x^8 + 1 to reveal the factors."]],
      ["#modulus-result details", "Read the GCD checkpoints",
        "Each row tests gcd(f(x), x^(2^i) + x) = 1 to confirm f(x) has no irreducible factors of degree i. Checking up to floor(deg(f)/2) guarantees irreducibility."],
    ],
  },
  applications: {
    name: "Applications walkthrough",
    fallback: ["#xts-form button[type=submit]", "Click Compute tweak chain to see the XTS-AES blocks."],
    steps: [
      ["#applications-subtabs", "Switch between XTS-AES, Binary ECC, and GCM / GHASH",
        "Explore three real-world standards built on GF(2^m): XTS-AES disk encryption over GF(2^128), Polynomial / Binary Elliptic Curve Cryptography over GF(2^4) and NIST B-163, and AES-GCM GHASH authentication over GF(2^128)."],
      ["#xts-form", "Configure the 128-bit XTS-AES tweak",
        "Enter or randomize a 128-bit hex tweak T_0, compute a block chain, or click Step next block (j → j+1) to watch T_j = T_0 ⊗ α^j advance block by block.",
        ["#app-tab-xts", "Select the XTS-AES sub-tab to inspect the 128-bit tweak multiplier."]],
      ["#xts-results", "Spot x^128 overflows and explore ECC & GHASH",
        "Whenever top bit b_127 = 1 before shifting left, the overflow bit triggers XOR with 0x87 (x^7 + x^2 + x + 1). Switch to Binary ECC to trace NIST B-163 point doubling, addition, and ECDH, or GCM · GHASH to chain full 128-bit XOR and Shift-and-XOR block authentication.",
        ["#xts-form button[type=submit]", "Click Compute tweak chain to display the 128-bit sector tweaks."]],
    ],
  },
  compare: {
    name: "Multiplication walkthrough",
    fallback: ["#compare-form button[type=submit]", "Click Compare methods to run both methods."],
    steps: [
      ["#compare-form", "Give both methods the same inputs",
        "Enter two hex operands (or click Random operands / Use calculator operands) and select a field degree. Compare multiplication methods in the calculator brings its exact field and operands here and runs both methods."],
      ["#compare-results", "Compare the remainders",
        "Shift and XOR reduces during multiplication. Carry-free multiplication forms the raw product first, then uses long division. Both give identical remainders."],
      ["#compare-shift-body", "Follow the multiplier bits",
        "Step through each shift and XOR or switch to All steps grid or Classic table to compare rows.",
        ["#compare-form button[type=submit]", "Compare a product with a nonzero multiplier to see the bit steps."], ".multiplier-bits"],
      ["#compare-division-body", "Follow the long-division steps",
        "Carry-free multiplication forms the raw product first, and each long-division step shifts the modulus and XORs it to cancel the leading term until the remainder matches Shift and XOR."],
      ["#compare-benchmark", "Benchmark both methods",
        "Click Run benchmark to compare median times at 163 and 571 bits. Both methods receive the same seeded operands at each degree, with trace generation left out of the timing."],
    ],
  },
};

/**
 * Wire up the floating `#page-tour` walkthrough panel, keyboard Escape handler, and event listeners.
 *
 * @returns {() => void} Cleanup function closing any active walkthrough (invoked on tab switches).
 */
export function setupPageTour() {
  const panel = document.getElementById("page-tour");
  const trigger = document.getElementById("tutorial-open");
  const heading = document.getElementById("tour-title");
  const description = document.getElementById("tour-description");
  const progress = document.getElementById("tour-progress");
  const previous = document.getElementById("tour-prev");
  const next = document.getElementById("tour-next");
  const concepts = document.getElementById("concepts-open");
  let index = 0;
  let highlight;
  let tour = walkthroughs.calculator;

  /**
   * Highlight and scroll to the current walkthrough step (or its fallback control if hidden).
   * @param {boolean} [scroll=true] - Whether to scroll the highlighted target into view.
   */
  function showStep(scroll = true) {
    const [selector, title, detail, fallback = tour.fallback, requiredChild] = tour.steps[index];
    const requested = document.querySelector(selector);
    const available = requested && !requested.closest("[hidden]") && (!requiredChild || requested.querySelector(requiredChild));
    const target = available ? requested : document.querySelector(fallback[0]);
    const moved = target !== highlight;
    if (moved) {
      highlight?.classList.remove("tour-highlight");
      highlight = target;
      highlight.classList.add("tour-highlight");
    }
    progress.textContent = tour.name + " · " + (index + 1) + " / " + tour.steps.length;
    setMathText(heading, title);
    setMathText(description, available ? detail : fallback[1] + " " + detail);
    previous.disabled = index === 0;
    next.textContent = index === tour.steps.length - 1 ? "Done" : "Next";
    if (scroll || moved) {
      const details = target.closest("details");
      if (details) details.open = true;
      target.scrollIntoView({ block: "start" });
    }
  }

  /**
   * Close the walkthrough panel, remove highlight outlines, and optionally restore focus.
   * @param {boolean} [restoreFocus=true] - Return keyboard focus to the Tutorial tour button.
   */
  function close(restoreFocus = true) {
    panel.hidden = true;
    highlight?.classList.remove("tour-highlight");
    highlight = undefined;
    if (restoreFocus) trigger.focus();
  }

  trigger.addEventListener("click", () => {
    const view = document.querySelector("[data-lab-view]:not([hidden])").dataset.labView;
    tour = walkthroughs[view] || walkthroughs.calculator;
    concepts.hidden = view !== "calculator";
    index = 0;
    panel.hidden = false;
    showStep();
    heading.focus({ preventScroll: true });
  });
  previous.addEventListener("click", () => {
    index -= 1;
    showStep();
    if (previous.disabled) next.focus({ preventScroll: true });
  });
  next.addEventListener("click", () => {
    if (index === tour.steps.length - 1) close();
    else {
      index += 1;
      showStep();
    }
  });
  document.getElementById("tour-close").addEventListener("click", () => close());
  // Re-evaluate step availability after any calculation finishes so results get highlighted live.
  document.addEventListener("lab:calculation-result", event => {
    if (!panel.hidden && !event.target.closest("[data-lab-view]").hidden) showStep(false);
  });
  document.addEventListener("keydown", event => {
    const errPopup = document.getElementById("error-popup");
    const openDialog = document.querySelector("dialog[open]");
    if (
      event.key === "Escape" &&
      !panel.hidden &&
      !openDialog &&
      errPopup?.hidden !== false
    ) {
      close();
    }
  });
  return () => close(false);
}
