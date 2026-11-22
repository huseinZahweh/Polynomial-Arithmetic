/**
 * @fileoverview Interactive per-view spotlight walkthroughs for the Finite Field Lab.
 *
 * Original Author: Ali Zahreddine — Milestone 4 & Integration (Educational Web GUI).
 *
 * Provides contextual guided tours for all four lab views (Calculator, Modulus explorer,
 * AES S-box, Compare multiplication), dynamically falling back to the triggering action
 * button whenever a step's result section has not yet been calculated, and automatically
 * re-highlighting newly rendered results on `lab:calculation-result` events.
 */

/**
 * Guided walkthrough steps for the main Calculator view.
 * Tuple shape: `[selector, title, description, fallback?, requiredChild?]`.
 * @type {Array<Array>}
 */
const calculatorSteps = [
  [".setting", "Choose a field",
    "Field degree sets how many bits fit in one element. Watch the banner and the modulus update. Use Hex, Binary, or Polynomial to change notation without changing the operand values."],
  [".operands", "Enter the operands",
    "Type values into A(x) and B(x). Each input previews the polynomial, bit length, and degree. In fields up to eight bits, click the checkboxes to turn individual coefficients on or off."],
  [".calculator .section-head", "Generate or upload operands",
    "Choose Sparse or Dense and click Random operands to fill both inputs. Upload accepts .txt or .json files. When a file contains several pairs, choose one from the pair list."],
  [".operations", "Pick an operation",
    "Add and Subtract both use XOR. Reduce takes A modulo the field polynomial. Multiply uses both operands, Inverse gives A⁻¹, and Divide gives A ÷ B."],
  [".action", "Run the calculation",
    "Click Calculate to run the selected operation. The result and tables appear below. The calculator also shows a message for a missing operand or an operation such as division by zero."],
  [".examples", "Try a textbook example",
    "Chapter 4 loads and multiplies 57 and 83 in the 8-bit field. Chapter 5 loads and inverts 95. Both examples calculate immediately."],
  ["#result", "Read, copy, or export the answer",
    "Calculate brings the result into view. For large fields, Show full value expands the preview. Copy result always copies the complete value in the selected notation. Use Back to inputs to edit the operands or Export to download the calculation."],
  ["#trace-panel", "Follow the calculation",
    "Use Previous step and Next step to follow the calculation. Narrow screens show one labelled step at a time. Select Show tables for the full trace, or Show step cards to return to one step at a time."],
  ["#trace-body", "See which partial product a bit selects",
    "Select a bit of B to highlight its shifted row and any selected partial product. In Chapter 4, bit 7 selects 38 and the running XOR becomes C1. The arrow keys also move between bits.",
    ["#presets", "Load the Chapter 4 example to see the multiplier bits."], ".multiplier-bits"],
  ["#compare-product", "Compare this product",
    "Click Compare this product to run both multiplication methods with the same field and original operands. The comparison view has its own Tutorial.",
    ["#presets", "Load the Chapter 4 example to show the comparison shortcut."]],
  ["#share", "Reopen an exact calculation",
    "Copy calculation link puts the field, operation, notation, and operands into a URL. Open it in another tab to recreate the calculation. A localhost link works on the computer running the lab."],
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
  modulus: {
    name: "Modulus walkthrough",
    fallback: ["#modulus-form button[type=submit]", "Click Test irreducibility to see the result."],
    steps: [
      ["#modulus-form", "Choose a polynomial",
        "The field modulus is a polynomial with binary coefficients. Test the prefilled AES modulus, enter another polynomial, or use the calculator's current modulus."],
      ["#modulus-result", "Read the irreducibility result",
        "An irreducible polynomial of degree m defines GF(2^m). A reducible polynomial has smaller factors, so some nonzero values have no inverse."],
      ["#modulus-witness .witness", "See two nonzero factors multiply to zero",
        "Each factor is nonzero. Their product equals the modulus and leaves remainder zero.",
        ["#modulus-example", "Click Try reducible x⁸ + 1 to reveal the factors."]],
      ["#modulus-result details", "Read the GCD checks",
        "Each row tests for common factors with x raised to 2^i, plus x. A GCD other than 1 signals a factor at that checkpoint. If every GCD is 1 through half the modulus degree, the polynomial is irreducible."],
    ],
  },
  aes: {
    name: "AES S-box walkthrough",
    fallback: ["#aes-form button[type=submit]", "Click Compute S-box output to see this stage."],
    steps: [
      ["#aes-form", "Choose a byte",
        "Enter one byte in hex or binary. Use Try byte 53 for a worked example, or Try byte 00 to see the special AES zero case."],
      ["#aes-result", "Follow the byte through both stages",
        "Read the input, its field inverse, and the substituted byte. For 53 in hex, the inverse is CA and the final output is ED."],
      ["#aes-euclid", "See how Extended Euclid finds the inverse",
        "Follow the quotients until B3 becomes 1. At that point B2 holds the inverse. AES uses zero directly in this stage when the input is 00.",
        ["#aes-example", "Click Try byte 53 to generate a nonzero inverse trace."]],
      ["#aes-affine", "Build the output with XOR",
        "Start with the inverse byte, XOR its four left rotations, then XOR 63 in hex. The final running XOR is the S-box output. In step cards, use Next step for each XOR or Show tables for all rows."],
    ],
  },
  compare: {
    name: "Multiplication walkthrough",
    fallback: ["#compare-form button[type=submit]", "Click Compare results to run both methods."],
    steps: [
      ["#compare-form", "Give both methods the same inputs",
        "Enter two hex operands and select a field degree. The starting example uses 57 and 83 in the 8-bit field. Compare this product in the calculator brings its field and operands here and runs both methods."],
      ["#compare-results", "Compare the remainders",
        "Shift and XOR reduces during multiplication. Carry-free multiplication forms the raw product first, then uses long division. Both give C1 for the starting example."],
      ["#compare-shift-body", "Follow the multiplier bits",
        "Select a bit to inspect its shift, partial product, and running XOR. On small screens, step cards show these values one bit at a time. Select Show tables to see the matching rows together.",
        ["#compare-form button[type=submit]", "Compare a product with a nonzero multiplier to see the bit steps."], ".multiplier-bits"],
      ["#compare-division-body", "Follow the long-division steps",
        "The raw product is 2B79 in the starting example. Each row shifts the modulus and XORs it to cancel the leading term. The final After XOR value is the same remainder produced by shift and XOR."],
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
    heading.textContent = title;
    description.textContent = available ? detail : fallback[1] + " " + detail;
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
   * @param {boolean} [restoreFocus=true] - Return keyboard focus to the Tutorial button.
   */
  function close(restoreFocus = true) {
    panel.hidden = true;
    highlight?.classList.remove("tour-highlight");
    highlight = undefined;
    if (restoreFocus) trigger.focus();
  }

  trigger.addEventListener("click", () => {
    const view = document.querySelector("[data-lab-view]:not([hidden])").dataset.labView;
    tour = walkthroughs[view];
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
    if (event.key === "Escape" && !panel.hidden && !document.getElementById("tutorial").open) close();
  });
  return () => close(false);
}
