/**
 * @fileoverview Interactive Visual Lab (`#visual`) and scoped `Visual | Classic` learning
 * mode switch for the Finite Field Lab workbench.
 *
 * Implements a five-screen guided finite-field intro alongside a live small-field
 * (`GF(2^2)` .. `GF(2^8)`) visualizer supporting hex, binary, and polynomial input,
 * interactive coefficient bit tiles, column-by-column XOR addition, Shift-and-XOR
 * animation belt, 3D rotatable Powers-of-g ring, and Classic textbook tables.
 */

import { attachSlidingIndicator } from "./notation.js";

/** @param {string} id @returns {HTMLElement | null} */
const $ = id => document.getElementById(id);

const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

/**
 * Create an element with optional CSS class and inner markup.
 * @param {string} tag - HTML tag name.
 * @param {string} [cls] - Optional CSS class string.
 * @param {string} [html] - Optional trusted static HTML string.
 * @returns {HTMLElement} Created element.
 */
const el = (tag, cls, html) => {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (html !== undefined) n.innerHTML = html;
  return n;
};

/** @returns {"auto" | "smooth"} Respect reduced-motion preference when scrolling. */
const smooth = () => (reduceMotion.matches ? "auto" : "smooth");

/* ================================================================ math */
// Mirrors backend/engine/fields.py for the textbook fields (m = 2 .. 8).
const MODS = { 2: 0x7, 3: 0xd, 4: 0x19, 5: 0x25, 6: 0x43, 7: 0x83, 8: 0x11b };
const SUP = "⁰¹²³⁴⁵⁶⁷⁸⁹";

/**
 * Render a non-negative integer as Unicode superscript digits for native `<option>` labels.
 * @param {number} n - Exponent integer.
 * @returns {string} Unicode superscript string.
 */
const supText = n => String(n).split("").map(d => SUP[d]).join("");

/**
 * Multiply two small-field elements in `GF(2^m)` modulo `mod` via Shift-and-XOR.
 * @param {number} a - First operand bitmask.
 * @param {number} b - Second operand bitmask.
 * @param {number} m - Extension degree `2..8`.
 * @param {number} mod - Irreducible modulus bitmask.
 * @returns {number} Product modulo `mod`.
 */
function fmul(a, b, m, mod) {
  let r = 0;
  while (b) {
    if (b & 1) r ^= a;
    b >>= 1;
    a <<= 1;
    if ((a >> m) & 1) a ^= mod;
  }
  return r;
}

const cache = {};

/**
 * Build and cache generator powers (`EXP`) and discrete logs (`LOG`) for `GF(2^m)`.
 * @param {number} m - Field degree in `2..8`.
 * @returns {{m: number, mod: number, N: number, g: number, EXP: number[], LOG: Array<number | null>, xOrder: number}} Field table metadata.
 */
function field(m) {
  if (cache[m]) return cache[m];
  const mod = MODS[m];
  const N = (1 << m) - 1;
  const order = c => {
    let v = c;
    let k = 1;
    while (v !== 1) {
      v = fmul(v, c, m, mod);
      k += 1;
    }
    return k;
  };
  let g = 2;
  while (order(g) !== N) g += 1;
  const EXP = [];
  const LOG = new Array(N + 1).fill(null);
  for (let k = 0, v = 1; k < N; k += 1) {
    EXP.push(v);
    LOG[v] = k;
    v = fmul(v, g, m, mod);
  }
  return (cache[m] = { m, mod, N, g, EXP, LOG, xOrder: order(2) });
}

/**
 * Format an integer as zero-padded uppercase hexadecimal.
 * @param {number} v - Value.
 * @param {number} bits - Field bit width.
 * @returns {string} Uppercase hex string.
 */
const hx = (v, bits) => v.toString(16).toUpperCase().padStart(Math.ceil(bits / 4), "0");

/**
 * Format an integer as zero-padded binary.
 * @param {number} v - Value.
 * @param {number} bits - Bit width.
 * @returns {string} Binary string.
 */
const bn = (v, bits) => v.toString(2).padStart(bits, "0");

/**
 * Render one monomial power label using true HTML `<sup>`.
 * @param {number} k - Non-negative exponent.
 * @returns {string} HTML monomial string.
 */
const powLabel = k => (k === 0 ? "1" : k === 1 ? "x" : `x<sup>${k}</sup>`);

/**
 * Render an integer bitmask as an HTML polynomial with `<sup>` exponents.
 * @param {number} v - Polynomial bitmask.
 * @returns {string} HTML polynomial string.
 */
function poly(v) {
  if (!v) return "0";
  const t = [];
  for (let k = 12; k >= 0; k -= 1) if ((v >> k) & 1) t.push(powLabel(k));
  return t.join(" + ");
}

/**
 * Render a generator power `g^k` using HTML `<sup>`.
 * @param {number} k - Exponent.
 * @returns {string} HTML string `g<sup>k</sup>`.
 */
const pw = k => `g<sup>${k}</sup>`;

/**
 * Parse hex (`"57"`, `"{57}"`, `"0x57"`), binary (`"0b1010111"`), or a polynomial
 * (`"x^6 + x + 1"`), then reduce modulo `f.mod` into `GF(2^m)`.
 *
 * @param {string} raw - Raw user input text.
 * @param {{m: number, mod: number}} f - Active small-field descriptor.
 * @returns {{value?: number, reduced?: boolean, orig?: bigint, error?: string}} Parsed value or error.
 */
function parseInput(raw, f) {
  const s = raw.trim().replace(/[{}\s]/g, "");
  if (!s) return { error: "Enter a value, for example 57." };
  let v;
  if (/x/i.test(s.replace(/^0x/i, ""))) {
    v = 0n;
    for (const term of s.split("+")) {
      if (!term) return { error: "A polynomial needs a term on each side of every +." };
      let k;
      if (term === "1") k = 0;
      else {
        const t = term.match(/^x(?:(?:\^|\*\*)(\d{1,3}))?$/i);
        if (!t) return { error: `"${term}" isn't a term I can read. Use terms like x^3, x or 1, joined with +.` };
        k = t[1] ? Number(t[1]) : 1;
      }
      v ^= 1n << BigInt(k);
    }
  } else if (/^0b[01]+$/i.test(s)) {
    v = BigInt(s.toLowerCase());
  } else if (/^(0x)?[0-9a-f]+$/i.test(s)) {
    v = BigInt(/^0x/i.test(s) ? s.toLowerCase() : "0x" + s);
  } else {
    return { error: "Use hex (57), binary (0b1010111) or a polynomial (x^6 + x^4 + 1)." };
  }
  const orig = v;
  const len = x => x.toString(2).length;
  while (v > 0n && len(v) > f.m) v ^= BigInt(f.mod) << BigInt(len(v) - 1 - f.m);
  return { value: Number(v), reduced: orig !== v, orig };
}

/* ======================================================== shared bits */

/**
 * Render a horizontal row of polynomial coefficient bit tiles (interactive when `toggle` is supplied).
 * @param {number} value - Bitmask value.
 * @param {number} width - Number of bits to display.
 * @param {{toggle?: (bit: number) => void, cls?: string}} [options] - Optional click handler and CSS class.
 * @returns {HTMLElement} Tile row container.
 */
function tileRow(value, width, { toggle, cls = "" } = {}) {
  const row = el("div", `vl-tiles ${cls}`);
  for (let k = width - 1; k >= 0; k -= 1) {
    const on = (value >> k) & 1;
    const t = el(toggle ? "button" : "span", `vl-tile${on ? " on" : ""}`, `<b>${on}</b><small>${powLabel(k)}</small>`);
    if (toggle) {
      t.type = "button";
      t.setAttribute("aria-pressed", String(Boolean(on)));
      t.setAttribute("aria-label", `Coefficient of x to the ${k}`);
      t.addEventListener("click", () => toggle(k));
    }
    row.append(t);
  }
  return row;
}

/**
 * Trigger a brief visual pulse animation on a changed tile or bit cell.
 * @param {HTMLElement} node - Target DOM node.
 */
function flash(node) {
  node.classList.remove("flash");
  void node.offsetWidth;
  node.classList.add("flash");
}

/* ================================================ 1. Start here intro */

/**
 * Wire the five-screen interactive "Start here" primer inside `#vl-path`.
 * @param {{load: (opts: object) => void, focusInputs: () => void}} lab - Explorer controller.
 */
function setupPath(lab) {
  const F = field(4);
  const nav = $("vl-path-nav");
  const stage = $("vl-stage");
  const body = $("vl-path-body");
  const toggleBtn = $("vl-path-toggle");
  const prev = $("vl-prev");
  const next = $("vl-next");
  if (!nav || !stage || !body || !toggleBtn || !prev || !next) return;

  let step = 0;

  const labelled = (text, node) => {
    const wrap = el("div", "vl-labelled");
    wrap.append(el("span", "vl-row-label", text), node);
    return wrap;
  };
  const button = (text, cls, onClick) => {
    const b = el("button", cls, text);
    b.type = "button";
    b.addEventListener("click", onClick);
    return b;
  };

  const screens = [
    {
      title: "Bits are coefficients",
      take: "A field element is a row of bits. Each bit says whether that power of x is in the polynomial. Tap the tiles.",
      mount(box) {
        let v = 0b1011;
        const draw = () => box.replaceChildren(
          tileRow(v, 4, { toggle: k => { v ^= 1 << k; draw(); box.querySelectorAll(".vl-tile")[3 - k].focus(); } }),
          el("p", "vl-readout", `<span>Polynomial</span><b>${poly(v)}</b><span>Binary</span><b>${bn(v, 4)}</b><span>Hex</span><b>${hx(v, 4)}</b>`),
        );
        draw();
      },
    },
    {
      title: "Adding is XOR",
      take: "In GF(2), 1 + 1 = 0, so nothing carries. That makes adding and subtracting the same operation.",
      mount(box) {
        let a = 0b1010;
        let b = 0b0110;
        const draw = (changed, focusRow, k) => {
          const res = tileRow(a ^ b, 4, { cls: "result" });
          box.replaceChildren(
            labelled("A", tileRow(a, 4, { toggle: k2 => { a ^= 1 << k2; draw(true, 0, k2); } })),
            labelled("B", tileRow(b, 4, { toggle: k2 => { b ^= 1 << k2; draw(true, 1, k2); } })),
            el("div", "vl-rule"),
            labelled("A + B", res),
            el("p", "vl-readout", `<span>Sum</span><b>(${poly(a)}) + (${poly(b)}) = ${poly(a ^ b)}</b>`),
          );
          if (changed) {
            flash(res);
            box.querySelectorAll(".vl-tiles")[focusRow].children[3 - k].focus();
          }
        };
        draw(false);
      },
    },
    {
      title: "Too big? Reduce",
      take: "Multiplying by x shifts every bit left. If a bit reaches x⁴, it is outside GF(2⁴), so we XOR with m(x) = x⁴ + x³ + 1 to fold it back in.",
      mount(box) {
        let v = 0b1001;
        let note = "Press the button to multiply by x.";
        const draw = over => {
          const parts = [];
          if (over !== undefined) {
            parts.push(
              labelled("Shifted", tileRow(over, 5, { cls: "overflow" })),
              labelled("m(x)", tileRow(F.mod, 5, { cls: "modulus" })),
              el("div", "vl-rule wide"),
            );
          }
          parts.push(
            labelled("Value", tileRow(v, 4)),
            el("p", "vl-readout", `<span>What happened</span><b>${note}</b>`),
          );
          const go = button("Multiply by x", "primary", () => {
            const s = v << 1;
            if (s & 0x10) {
              v = s ^ F.mod;
              note = `x⁴ appeared, so we XORed with m(x): ${bn(s, 5)} ⊕ ${bn(F.mod, 5)} = ${bn(v, 4)}.`;
              draw(s);
            } else {
              v = s;
              note = `Nothing reached x⁴, so it was just a shift. Now ${bn(v, 4)} = ${poly(v)}.`;
              draw();
            }
            box.querySelector(".primary").focus();
          });
          box.replaceChildren(...parts, go);
        };
        draw();
      },
    },
    {
      title: "The field is a cycle",
      take: "Keep multiplying 1 by x and you visit all 15 nonzero elements before landing back on 1. That loop is the whole field.",
      mount(box) {
        let k = 0;
        const strip = el("div", "vl-cycle");
        F.EXP.forEach((v, i) => strip.append(el("span", "", `<b>${hx(v, 4)}</b><small>${pw(i)}</small>`)));
        const out = el("p", "vl-readout", "");
        const paint = () => {
          [...strip.children].forEach((c, i) => {
            c.classList.toggle("lit", i <= k);
            c.classList.toggle("current", i === k % 15);
            c.classList.toggle("done", k === 15);
          });
          out.innerHTML = k === 15
            ? `<span>Back at the start</span><b>g<sup>15</sup> = 1, so the cycle has length 15 = 2<sup>4</sup> − 1.</b>`
            : `<span>Now at</span><b>${pw(k)} = ${poly(F.EXP[k])} = ${hx(F.EXP[k], 4)}</b>`;
        };
        const actions = el("div", "vl-actions");
        actions.append(
          button("Multiply by x", "primary", () => { k = k === 15 ? 0 : k + 1; paint(); }),
          button("See it as a 3D ring", "outline", () => lab.load({ m: 4, a: "2", b: "8", rel: "mul", mulView: "ring", scroll: true, play: true })),
        );
        paint();
        box.replaceChildren(strip, out, actions);
      },
    },
    {
      title: "Why it matters",
      take: "AES does its byte math in GF(2⁸). Binary elliptic-curve cryptography uses the same rules in fields as large as GF(2⁵⁷¹).",
      mount(box) {
        const facts = el(
          "ul",
          "vl-facts",
          `<li><b>AES S-box:</b> each byte is replaced by its inverse in GF(2<sup>8</sup>), followed by an affine step.</li>
           <li><b>AES MixColumns:</b> bytes are multiplied by {02} and {03}, the same shift-and-XOR you can watch below.</li>
           <li><b>Binary ECC:</b> the Calculator tab runs these rules in GF(2<sup>163</sup>) through GF(2<sup>571</sup>).</li>`,
        );
        const actions = el("div", "vl-actions");
        actions.append(
          button("Watch {57} × {83} step by step", "primary", () => lab.load({ m: 8, a: "57", b: "83", rel: "mul", mulView: "steps", scroll: true, play: true })),
          button("Try your own numbers", "outline", () => lab.focusInputs()),
        );
        box.replaceChildren(facts, actions);
      },
    },
  ];

  screens.forEach((s, i) => {
    const li = el("li");
    li.append(button(`<span>${i + 1}</span>${s.title}`, "", () => go(i)));
    nav.append(li);
  });

  /**
   * Switch the active primer screen.
   * @param {number} i - Zero-based screen index.
   */
  function go(i) {
    step = Math.max(0, Math.min(screens.length - 1, i));
    const s = screens[step];
    [...nav.querySelectorAll("button")].forEach((b, j) => {
      if (j === step) b.setAttribute("aria-current", "step");
      else b.removeAttribute("aria-current");
      b.classList.toggle("seen", j < step);
    });
    const card = el("div", "vl-screen");
    const box = el("div", "vl-play");
    card.append(el("h3", "", s.title), el("p", "vl-take", s.take), box);
    stage.replaceChildren(card);
    s.mount(box);
    prev.disabled = step === 0;
    next.textContent = step === screens.length - 1 ? "Try your own numbers" : "Next";
  }

  prev.addEventListener("click", () => go(step - 1));
  next.addEventListener("click", () => (step === screens.length - 1 ? lab.focusInputs() : go(step + 1)));

  const setOpen = open => {
    body.hidden = !open;
    toggleBtn.setAttribute("aria-expanded", String(open));
    toggleBtn.textContent = open ? "Hide intro" : "Show intro";
    localStorage.setItem("ffl-intro-hidden", open ? "0" : "1");
  };
  toggleBtn.addEventListener("click", () => setOpen(body.hidden));
  setOpen(localStorage.getItem("ffl-intro-hidden") !== "1");

  window.__vlIntro = {
    open(i) {
      setOpen(true);
      go(i);
      $("vl-path").scrollIntoView({ behavior: smooth(), block: "start" });
    },
  };
  go(0);
}

/* ============================================= 2. Explore your numbers */

/**
 * Create the live small-field visual explorer (`#vl-explorer`) with XOR board,
 * Shift-and-XOR belt, 3D Powers-of-g ring, and Classic textbook tables.
 *
 * @param {() => boolean} isVisual - Accessor returning `true` when Visual mode is active.
 * @param {HTMLElement} view - The `[data-lab-view="visual"]` container.
 * @returns {{load: (opts: object) => void, focusInputs: () => void, getShareState: () => Record<string, string>, restoreShareState: (params: URLSearchParams) => boolean}} Explorer controller.
 */
function createExplorer(isVisual, view) {
  const S = { f: field(8), a: 0x57, b: 0x83, ok: { a: true, b: true }, notes: { a: "", b: "" }, rel: "mul", mulView: "steps" };
  const fieldSel = $("vl-field");
  for (let m = 2; m <= 8; m += 1) {
    const f = field(m);
    fieldSel.append(new Option(`GF(2${supText(m)}), ${f.N + 1} elements${m === 8 ? " (AES)" : ""}`, String(m)));
  }
  fieldSel.value = "8";

  const RELS = [
    { id: "add", label: "A + B" },
    { id: "mul", label: "A × B" },
    { id: "div", label: "A ÷ B" },
    { id: "inv", label: "A<sup>−1</sup>" },
  ];
  const relBox = $("vl-relations");
  const relButtons = RELS.map(r => {
    const b = el("button", "vl-rel");
    b.type = "button";
    b.dataset.rel = r.id;
    b.addEventListener("click", () => { S.rel = r.id; renderStage({ animate: true }); });
    relBox.append(b);
    return b;
  });

  const mulViewIndicator = attachSlidingIndicator($("vl-mulview"), '[aria-pressed="true"]');

  /**
   * Compute the selected finite-field relation (`add`, `mul`, `div`, `inv`).
   * @param {"add" | "mul" | "div" | "inv"} id - Relation identifier.
   * @returns {{value?: number, note?: string, i?: number, j?: number, r?: number, error?: string}} Result summary.
   */
  function compute(id) {
    const { f, a, b } = S;
    const i = f.LOG[a];
    const j = f.LOG[b];
    const N = f.N;
    if (!S.ok.a || (id !== "inv" && !S.ok.b)) return { error: "Fix the input above" };
    if (id === "add") return { value: a ^ b, note: "Same as A − B" };
    if (id === "mul") {
      if (!a || !b) return { value: 0, note: "Anything times 0 is 0" };
      const r = (i + j) % N;
      return { value: f.EXP[r], note: `${pw(i)} · ${pw(j)} = ${pw(r)}`, i, j, r };
    }
    if (id === "div") {
      if (!b) return { error: "Can't divide by 0" };
      if (!a) return { value: 0, note: "0 divided by anything is 0" };
      const r = (i - j + N) % N;
      return { value: f.EXP[r], note: `${pw(i)} ÷ ${pw(j)} = ${pw(r)}`, i, j, r };
    }
    if (!a) return { error: "0 has no inverse" };
    const r = (N - i) % N;
    return { value: f.EXP[r], note: `${pw(i)} · ${pw(r)} = 1`, i, r };
  }

  /**
   * Parse and validate operand input `a` or `b`.
   * @param {"a" | "b"} key - Operand key.
   */
  function readInput(key) {
    const input = $(`vl-${key}`);
    const r = parseInput(input.value, S.f);
    S.ok[key] = !r.error;
    if (r.error) {
      S.notes[key] = r.error;
    } else {
      S[key] = r.value;
      S.notes[key] = r.reduced
        ? `{${r.orig.toString(16).toUpperCase()}} has more than ${S.f.m} bits, so it was reduced mod m(x) to {${hx(r.value, S.f.m)}}.`
        : "";
    }
    input.setAttribute("aria-invalid", String(Boolean(r.error)));
  }

  /**
   * Set an operand input value in hex and re-render cards and stage.
   * @param {"a" | "b"} key - Operand key.
   * @param {number} v - Integer element value.
   * @param {number} [focusBit] - Optional bit index to restore keyboard focus after tile click.
   */
  function setInput(key, v, focusBit) {
    $(`vl-${key}`).value = hx(v, S.f.m);
    update({ animate: false });
    if (focusBit !== undefined) $(`vl-card-${key}`).querySelectorAll(".vl-tile")[S.f.m - 1 - focusBit]?.focus();
  }

  /**
   * Render one operand card (`#vl-card-a` or `#vl-card-b`) with interactive bit tiles.
   * @param {"a" | "b"} key - Operand key.
   */
  function renderCard(key) {
    const box = $(`vl-card-${key}`);
    const f = S.f;
    const v = S[key];
    const tag = `<span class="vl-tag">${key.toUpperCase()}</span>`;
    if (!S.ok[key]) {
      box.innerHTML = `<div class="vl-number-head">${tag}</div><p class="vl-error">${S.notes[key]}</p>`;
      return;
    }
    const k = f.LOG[v];
    box.innerHTML = `
      <div class="vl-number-head">${tag}<b class="vl-hex">{${hx(v, f.m)}}</b><span class="vl-pow">${v ? `= ${pw(k)}` : "zero"}</span></div>`;
    box.append(tileRow(v, f.m, { toggle: bit => setInput(key, v ^ (1 << bit), bit), cls: f.m > 6 ? "compact" : "" }));
    box.append(el("dl", "vl-reprs", `
      <dt>Polynomial</dt><dd>${poly(v)}</dd>
      <dt>Binary</dt><dd>${bn(v, f.m)}</dd>
      <dt>Power of g</dt><dd>${v ? pw(k) : "0 is not a power of g"}</dd>`));
    if (S.notes[key]) box.append(el("p", "vl-note", S.notes[key]));
  }

  /** Refresh all four relation preview cards (`+`, `×`, `÷`, `A^-1`). */
  function renderRelations() {
    relButtons.forEach((b, n) => {
      const r = RELS[n];
      const c = compute(r.id);
      b.setAttribute("aria-pressed", String(S.rel === r.id));
      b.innerHTML = `
        <span class="vl-rel-label">${r.label}</span>
        <b class="vl-rel-value">${c.error ? "n/a" : `{${hx(c.value, S.f.m)}}`}</b>
        <span class="vl-rel-note">${c.error || c.note}</span>`;
    });
  }

  /** Update the modulus metadata line and hero badge. */
  function renderModline() {
    const f = S.f;
    const gText = f.g === 2
      ? "g = x"
      : `g = {${hx(f.g, f.m)}} = ${poly(f.g)}. (Here x alone only reaches ${f.xOrder} elements, so x + 1 is used instead.)`;
    $("vl-modline").innerHTML = `m(x) = ${poly(f.mod)} &nbsp;{${hx(f.mod, f.m + 1)}}. This field has ${f.N + 1} elements, and every nonzero one is a power of ${gText}`;
    $("vl-hero-badge").innerHTML = `GF(2<sup>${f.m}</sup>)`;
  }

  /** Build a deep link that transfers the current numbers directly into `#calculator`. */
  function calcHref() {
    const op = { add: "add", mul: "multiply", div: "divide", inv: "inverse" }[S.rel];
    const q = new URLSearchParams({ m: String(S.f.m), operation: op, base: "hex", poly_a: S.a.toString(16) });
    if (op !== "inverse") q.set("poly_b", S.b.toString(16));
    return `./?${q}#calculator`;
  }

  /**
   * Re-parse both operands and synchronize every card and stage element.
   * @param {{animate: boolean}} options - Whether to play stage animations.
   */
  function update({ animate }) {
    readInput("a");
    readInput("b");
    renderCard("a");
    renderCard("b");
    renderModline();
    renderStage({ animate });
  }

  /* ---- stage ---- */
  const caption = $("vl-caption");
  const intro = $("vl-stage-intro");
  const INTROS = {
    add: "Addition works column by column. Each column is XORed on its own, so 1 + 1 = 0 and nothing carries.",
    steps: "A shifts left one bit per step. Wherever B has a 1, the shifted A is XORed into the result. If a bit spills past the field, m(x) cancels it.",
    mul: "Every nonzero element is a power of g, and multiplying adds exponents. So A × B means starting at A and turning j steps around the ring, where B = g<sup>j</sup>.",
    div: "Dividing subtracts exponents. Start at A and turn back j steps, where B = g<sup>j</sup>.",
    inv: "A<sup>−1</sup> is the element that turns A the rest of the way around the ring to 1.",
  };
  const pane = () => (S.rel === "add" ? "add" : S.rel === "mul" && S.mulView === "steps" ? "steps" : "ring");

  /**
   * Render the active visualization pane (`add`, `steps`, or `ring`) in Visual or Classic mode.
   * @param {{animate: boolean}} options - Whether to play animations.
   */
  function renderStage({ animate }) {
    Add.stop();
    Belt.stop();
    Ring.stop();
    renderRelations();
    const p = pane();
    view.querySelectorAll(".vl-pane").forEach(n => { n.hidden = n.dataset.pane !== p; });
    $("vl-mulview").hidden = S.rel !== "mul";
    $("vl-mulview").querySelectorAll("button").forEach(b => b.setAttribute("aria-pressed", String(b.dataset.mulview === S.mulView)));
    if (S.rel === "mul") mulViewIndicator.update();
    $("vl-play").hidden = $("vl-step").hidden = $("vl-speed").parentElement.hidden = p !== "steps";
    $("vl-replay").hidden = p === "steps";
    intro.innerHTML = p === "steps" ? INTROS.steps : INTROS[S.rel];
    $("vl-calc-link").href = calcHref();
    const c = compute(S.rel);
    if (c.error === "Fix the input above") {
      caption.innerHTML = "<p>Fix the highlighted input in step 1 to see this.</p>";
      view.querySelector(`.vl-pane[data-pane="${p}"]`).hidden = true;
      return;
    }
    if (p === "add") Add.render(animate);
    else if (p === "steps") Belt.render(animate);
    else Ring.render(animate, c);
  }

  /* ---------------------------------------------- Add: column XOR */
  const Add = (() => {
    let timer = null;
    const board = $("vl-add-board");
    const classic = $("vl-add-classic");
    const cellsHtml = (v, m, cls = "") => {
      let h = "";
      for (let k = m - 1; k >= 0; k -= 1) {
        h += `<span class="vl-cell ${(v >> k) & 1 ? "on" : ""} ${cls}" data-k="${k}">${(v >> k) & 1}</span>`;
      }
      return h;
    };
    function finalCaption() {
      const { f, a, b } = S;
      caption.innerHTML = `<p class="vl-result-line">A + B = {${hx(a ^ b, f.m)}} = ${poly(a ^ b)}</p><p>In GF(2) adding and subtracting are the same, so A − B = {${hx(a ^ b, f.m)}} too.</p>`;
    }
    function render(animate) {
      const { f, a, b } = S;
      const m = f.m;
      const r = a ^ b;
      let head = "";
      for (let k = m - 1; k >= 0; k -= 1) head += `<span class="vl-cell power" data-k="${k}"><span>${powLabel(k)}</span></span>`;
      board.style.setProperty("--cols", m);
      board.innerHTML = `
        <div class="vl-board-row head"><span class="vl-row-label"></span><div class="vl-cells">${head}</div></div>
        <div class="vl-board-row"><span class="vl-row-label">A</span><div class="vl-cells">${cellsHtml(a, m)}</div></div>
        <div class="vl-board-row"><span class="vl-row-label">B</span><div class="vl-cells">${cellsHtml(b, m)}</div></div>
        <div class="vl-board-row res"><span class="vl-row-label">A + B</span><div class="vl-cells">${cellsHtml(r, m, "res")}</div></div>`;
      let th = "";
      let ra = "";
      let rb = "";
      let rr = "";
      for (let k = m - 1; k >= 0; k -= 1) {
        th += `<th>${powLabel(k)}</th>`;
        ra += `<td>${(a >> k) & 1}</td>`;
        rb += `<td>${(b >> k) & 1}</td>`;
        rr += `<td>${(r >> k) & 1}</td>`;
      }
      classic.innerHTML = `
        <table class="vl-table vl-xor">
          <thead><tr><th></th>${th}<th>Polynomial</th></tr></thead>
          <tbody>
            <tr><th>A</th>${ra}<td class="vl-poly">${poly(a)}</td></tr>
            <tr><th>⊕ B</th>${rb}<td class="vl-poly">${poly(b)}</td></tr>
            <tr class="sum"><th>A + B</th>${rr}<td class="vl-poly">${poly(r)}</td></tr>
          </tbody>
        </table>`;
      finalCaption();
      if (animate && isVisual() && !reduceMotion.matches) sweep();
    }
    function sweep() {
      stop();
      const { f, a, b } = S;
      const res = [...board.querySelectorAll(".vl-cell.res")];
      res.forEach(c => c.classList.add("pending"));
      let k = 0;
      const tick = () => {
        board.querySelectorAll(".col-lit").forEach(c => c.classList.remove("col-lit"));
        if (k >= f.m) { stop(); finalCaption(); return; }
        board.querySelectorAll(`[data-k="${k}"]`).forEach(c => c.classList.add("col-lit"));
        const cell = res.find(c => c.dataset.k === String(k));
        cell.classList.remove("pending");
        flash(cell);
        const ak = (a >> k) & 1;
        const bk = (b >> k) & 1;
        caption.innerHTML = `<p>Column ${powLabel(k)}: ${ak} ⊕ ${bk} = <b>${ak ^ bk}</b>${ak && bk ? ". Two 1s cancel, and nothing carries into the next column." : "."}</p>`;
        k += 1;
      };
      tick();
      timer = setInterval(tick, 650);
    }
    function stop() {
      clearInterval(timer);
      timer = null;
      board.querySelectorAll(".pending, .col-lit").forEach(c => c.classList.remove("pending", "col-lit"));
    }
    return { render, stop, replay: sweep };
  })();

  /* ------------------------------------------ Belt: shift-and-XOR */
  const Belt = (() => {
    const belt = $("vl-belt");
    const classic = $("vl-steps-classic");
    const play = $("vl-play");
    let rows = {};
    let builtM = 0;
    let frames = [];
    let at = 0;
    let timer = null;

    function build(m) {
      belt.innerHTML = "";
      rows = {};
      belt.style.setProperty("--cols", m + 1);
      const mk = (key, label) => {
        const row = el("div", `vl-board-row ${key}`);
        row.append(el("span", "vl-row-label", label));
        const cells = el("div", "vl-cells");
        row.append(cells);
        belt.append(row);
        return { row, cells };
      };
      const head = mk("head", "");
      for (let k = m; k >= 0; k -= 1) head.cells.append(el("span", "vl-cell power", `<span>${powLabel(k)}</span>`));
      for (const [key, label] of [["b", "B"], ["a", "x<sup>i</sup> · A"], ["m", "m(x)"], ["acc", "Result"]]) {
        const r = mk(key, label);
        for (let i = 0; i <= m; i += 1) r.cells.append(el("span", "vl-cell"));
        rows[key] = { r: r.row, box: r.cells, cells: [...r.cells.children] };
      }
      builtM = m;
    }
    function setRow(key, value, n, { highlight = -1, flip = false } = {}) {
      const m = builtM;
      const cells = rows[key].cells;
      for (let k = 0; k <= m; k += 1) {
        const c = cells[m - k];
        if (k >= n) {
          c.className = k === m && key === "a" ? "vl-cell slot" : "vl-cell ghost";
          c.textContent = "";
          continue;
        }
        const on = (value >> k) & 1;
        const was = c.textContent;
        c.className = `vl-cell${on ? " on" : ""}${k === highlight ? " current" : ""}${k === m ? " over" : ""}`;
        c.textContent = String(on);
        if (flip && was !== "" && was !== String(on)) flash(c);
      }
    }
    function makeFrames() {
      const { f, a: A, b: B } = S;
      const m = f.m;
      const top = 1 << m;
      const W = v => `{${hx(v, m)}}`;
      const out = [];
      let cur = A;
      let acc = 0;
      out.push({ i: 0, a: cur, acc, phase: "start", text: `Start with A = ${W(A)} and an empty result. We read the ${m} bits of B = ${W(B)} from right to left.` });
      for (let i = 0; i < m; i += 1) {
        const bit = (B >> i) & 1;
        if (bit) acc ^= cur;
        out.push({
          i, a: cur, acc, phase: "check", bit,
          text: bit
            ? `Bit b<sub>${i}</sub> of B is 1, so XOR x<sup>${i}</sup>·A = ${W(cur)} into the result. Result is now ${W(acc)}.`
            : `Bit b<sub>${i}</sub> of B is 0, so skip. Result stays ${W(acc)}.`,
        });
        if (i === m - 1) break;
        const s = cur << 1;
        const over = Boolean(s & top);
        out.push({
          i, a: s, acc, phase: "shift", over,
          text: over
            ? `Shift A left. A 1 spills into x<sup>${m}</sup>, which is outside the field…`
            : `Shift A left to get x<sup>${i + 1}</sup>·A = ${W(s)}. Nothing spilled over.`,
        });
        if (over) {
          cur = s ^ f.mod;
          out.push({
            i, a: cur, acc, phase: "reduce",
            text: `…so XOR with m(x) = {${hx(f.mod, m + 1)}}. The x<sup>${m}</sup> bit cancels, leaving x<sup>${i + 1}</sup>·A = ${W(cur)}.`,
          });
        } else cur = s;
      }
      const c = compute("mul");
      const check = c.i !== undefined ? ` Check with powers: ${c.note}.` : "";
      out.push({ i: m, a: cur, acc, phase: "done", text: `<span class="vl-result-line">${W(A)} × ${W(B)} = ${W(acc)} = ${poly(acc)}</span>${check}` });
      return out;
    }
    function show(idx, animate) {
      const fr = frames[idx];
      if (!fr) return;
      const m = builtM;
      const draw = () => {
        setRow("b", S.b, m, { highlight: fr.phase === "done" || fr.phase === "start" ? -1 : fr.i });
        setRow("a", fr.a, m + 1, { flip: animate });
        setRow("m", S.f.mod, m + 1);
        setRow("acc", fr.acc, m, { flip: animate });
        rows.m.r.classList.toggle("show", fr.phase === "reduce" || (fr.phase === "shift" && fr.over));
        rows.acc.r.classList.toggle("hit", fr.phase === "check" && fr.bit === 1);
        rows.acc.r.classList.toggle("final", fr.phase === "done");
        caption.innerHTML = `<p>${fr.text}</p><p class="vl-progress">Step ${idx} of ${frames.length - 1}</p>`;
      };
      if (animate && fr.phase === "shift" && !reduceMotion.matches) {
        rows.a.box.classList.add("sliding");
        setTimeout(() => { rows.a.box.classList.remove("sliding"); draw(); }, 360);
      } else draw();
    }
    function renderClassic() {
      const m = S.f.m;
      const body = frames.filter(fr => fr.phase === "check").map(fr =>
        `<tr${fr.bit ? ' class="used"' : ""}><td>${fr.i}</td><td>${fr.bit}</td><td>{${hx(fr.a, m)}}</td><td>${bn(fr.a, m)}</td><td>${fr.bit ? "XOR in" : "skip"}</td><td>{${hx(fr.acc, m)}}</td></tr>`).join("");
      classic.innerHTML = `
        <table class="vl-table">
          <caption>Shift-and-XOR with m(x) = ${poly(S.f.mod)}</caption>
          <thead><tr><th>i</th><th>b<sub>i</sub></th><th>x<sup>i</sup>·A mod m(x)</th><th>Binary</th><th>Action</th><th>Running result</th></tr></thead>
          <tbody>${body}</tbody>
        </table>`;
    }
    function render(animate) {
      stop();
      if (builtM !== S.f.m) build(S.f.m);
      frames = makeFrames();
      at = 0;
      renderClassic();
      if (isVisual()) {
        show(0, false);
        if (animate) toggle();
      } else {
        at = frames.length - 1;
        caption.innerHTML = `<p>${frames[at].text}</p>`;
      }
    }
    function stepOnce() {
      if (at >= frames.length - 1) { stop(); return; }
      at += 1;
      show(at, true);
      if (at >= frames.length - 1) stop();
    }
    function toggle() {
      if (timer) { stop(); return; }
      if (at >= frames.length - 1) { at = 0; show(0, false); }
      play.textContent = "Pause";
      timer = setInterval(stepOnce, Number($("vl-speed").value));
    }
    function stop() {
      clearInterval(timer);
      timer = null;
      play.textContent = at >= frames.length - 1 && frames.length ? "Play again" : "Play";
    }
    play.addEventListener("click", toggle);
    $("vl-step").addEventListener("click", () => { stop(); stepOnce(); });
    $("vl-speed").addEventListener("change", () => { if (timer) { stop(); toggle(); } });
    return { render, stop };
  })();

  /* --------------------------------------------- Ring: powers of g */
  const Ring = (() => {
    const ringEl = $("vl-ring");
    const stageEl = $("vl-ring-stage");
    const tableBox = $("vl-power-table");
    const svgNS = "http://www.w3.org/2000/svg";
    const svg = document.createElementNS(svgNS, "svg");
    svg.setAttribute("class", "vl-orbit");
    const orbit = document.createElementNS(svgNS, "ellipse");
    const path = document.createElementNS(svgNS, "polyline");
    path.setAttribute("class", "vl-trail");
    svg.append(orbit, path);
    ringEl.append(svg);
    ringEl.append(el("div", "vl-hub", "<b>0</b><small>outside the cycle</small>"));

    const TILT = 0.4;
    let nodes = [];
    let builtM = 0;
    let STEP = 1;
    let spin = 0;
    let target = null;
    let velocity = 0;
    let dragging = false;
    let lastX = 0;
    let idle = 0;
    let trail = [];
    let walkRAF = null;

    function build() {
      const f = S.f;
      nodes.forEach(n => n.remove());
      STEP = (2 * Math.PI) / f.N;
      ringEl.dataset.size = f.N <= 15 ? "lg" : f.N <= 31 ? "md" : "dense";
      nodes = f.EXP.map((v, k) => {
        const n = el("button", "vl-node", `<b>${hx(v, f.m)}</b><small>${pw(k)}</small>`);
        n.type = "button";
        n.setAttribute("aria-label", `g to the ${k}, value ${hx(v, f.m)}. Set as A.`);
        if (f.N > 31) n.tabIndex = -1;
        n.addEventListener("click", () => { $("vl-a").value = hx(v, f.m); update({ animate: true }); });
        ringEl.append(n);
        return n;
      });
      tableBox.innerHTML = `
        <table class="vl-table vl-power">
          <caption>Powers of g = {${hx(f.g, f.m)}} with m(x) = ${poly(f.mod)}. Click a row to set A.</caption>
          <thead><tr><th>Power</th><th>Polynomial</th><th>Binary</th><th>Hex</th></tr></thead>
          <tbody>${f.EXP.map((v, k) => `<tr data-k="${k}" tabindex="0"><td>${pw(k)}</td><td>${poly(v)}</td><td>${bn(v, f.m)}</td><td>${hx(v, f.m)}</td></tr>`).join("")}</tbody>
        </table>`;
      tableBox.querySelectorAll("tr[data-k]").forEach(tr => {
        const pick = () => { $("vl-a").value = hx(f.EXP[Number(tr.dataset.k)], f.m); update({ animate: false }); };
        tr.addEventListener("click", pick);
        tr.addEventListener("keydown", e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); pick(); } });
      });
      builtM = f.m;
    }

    const geometry = () => {
      const w = ringEl.clientWidth;
      const h = ringEl.clientHeight;
      const R = Math.max(60, Math.min(w * 0.42, (h / 2 - 34) / 0.5));
      return { cx: w / 2, cy: h / 2 - 6, R, persp: Math.max(1000, R * 3.2) };
    };
    function project(k, g) {
      const th = k * STEP + spin;
      const x = g.R * Math.sin(th);
      const z0 = g.R * Math.cos(th);
      const y = z0 * Math.sin(TILT) * 0.85;
      const z = z0 * Math.cos(TILT);
      const s = g.persp / (g.persp - z);
      return { x: g.cx + x * s, y: g.cy + y * s, s, z };
    }
    function frame() {
      if (isVisual() && stageEl.offsetParent !== null && nodes.length) {
        if (target !== null) {
          let d = target - spin;
          d = Math.atan2(Math.sin(d), Math.cos(d));
          spin += d * (reduceMotion.matches ? 1 : 0.1);
          if (Math.abs(d) < 0.002) target = null;
        } else if (!dragging) {
          spin += velocity;
          velocity *= 0.94;
          if (Math.abs(velocity) < 0.0004 && performance.now() - idle > 5000 && !reduceMotion.matches && !walkRAF) spin += 0.0015;
        }
        const g = geometry();
        orbit.setAttribute("cx", g.cx);
        orbit.setAttribute("cy", g.cy);
        orbit.setAttribute("rx", g.R);
        orbit.setAttribute("ry", g.R * Math.sin(TILT) * 0.85);
        nodes.forEach((n, k) => {
          const p = project(k, g);
          n.style.transform = `translate(${p.x.toFixed(1)}px, ${p.y.toFixed(1)}px) translate(-50%, -50%) scale(${p.s.toFixed(3)})`;
          n.style.zIndex = String(Math.round(p.z + 2000));
          n.style.opacity = String(0.4 + 0.6 * ((p.z / g.R + 1) / 2));
        });
        path.setAttribute("points", trail.map(k => { const p = project(k, g); return `${p.x.toFixed(1)},${p.y.toFixed(1)}`; }).join(" "));
      }
      requestAnimationFrame(frame);
    }
    const face = k => { target = -k * STEP; };

    function mark(c) {
      const isRing = S.rel !== "add";
      nodes.forEach((n, k) => {
        n.classList.toggle("is-a", isRing && S.a !== 0 && k === S.f.LOG[S.a]);
        n.classList.toggle("is-b", (S.rel === "mul" || S.rel === "div") && S.b !== 0 && k === S.f.LOG[S.b]);
        n.classList.toggle("is-result", c.r !== undefined && k === c.r);
        n.classList.toggle("is-one", k === 0);
        n.classList.toggle("on-trail", trail.includes(k));
      });
      tableBox.querySelectorAll("tr[data-k]").forEach(tr => {
        const k = Number(tr.dataset.k);
        tr.className = [k === S.f.LOG[S.a] ? "is-a" : "", S.rel !== "inv" && k === S.f.LOG[S.b] ? "is-b" : "", c.r === k ? "is-result" : ""].join(" ").trim();
      });
    }
    function explain(c) {
      const f = S.f;
      const N = f.N;
      const W = v => `{${hx(v, f.m)}}`;
      if (c.error) return `<p class="vl-result-line">${c.error}.</p><p>0 sits outside the cycle of powers: no power of g equals 0, so 0 has no inverse.</p>`;
      if (c.r === undefined) return `<p class="vl-result-line">Result: ${W(c.value)}</p><p>${c.note}. 0 sits outside the cycle, so there is no turning to do.</p>`;
      const wrap = sum => (sum >= N || sum < 0 ? ` Exponents wrap around at ${N} because g<sup>${N}</sup> = 1.` : "");
      if (S.rel === "mul") return `<p class="vl-result-line">A × B = ${pw(c.i)} · ${pw(c.j)} = ${pw(c.r)} = ${W(c.value)}</p><p>A = ${W(S.a)} = ${pw(c.i)} and B = ${W(S.b)} = ${pw(c.j)}. Adding the exponents, ${c.i} + ${c.j} = ${c.i + c.j}${c.i + c.j >= N ? ` → ${c.r}` : ""}.${wrap(c.i + c.j)}</p>`;
      if (S.rel === "div") return `<p class="vl-result-line">A ÷ B = ${pw(c.i)} ÷ ${pw(c.j)} = ${pw(c.r)} = ${W(c.value)}</p><p>Subtracting the exponents, ${c.i} − ${c.j} = ${c.i - c.j}${c.i - c.j < 0 ? ` → ${c.r}` : ""}.${wrap(c.i - c.j)} Check: ${W(c.value)} × ${W(S.b)} = ${W(S.a)}.</p>`;
      return `<p class="vl-result-line">A<sup>−1</sup> = ${pw(c.r)} = ${W(c.value)}</p><p>A = ${pw(c.i)}, and ${pw(c.i)} · ${pw(c.r)} = g<sup>${N}</sup> = 1. Check: ${W(S.a)} × ${W(c.value)} = {${hx(1, f.m)}}.</p>`;
    }
    function walkPlan(c) {
      const N = S.f.N;
      if (c.r === undefined) return null;
      if (S.rel === "mul") return { from: c.i, steps: c.j, dir: 1 };
      if (S.rel === "div") return { from: c.i, steps: c.j, dir: -1 };
      return { from: c.i, steps: (N - c.i) % N, dir: 1 };
    }
    function render(animate, c) {
      stop();
      if (builtM !== S.f.m) build();
      const plan = walkPlan(c);
      const N = S.f.N;
      const at = n => (((plan.from + plan.dir * n) % N) + N) % N;
      caption.innerHTML = explain(c);
      if (!plan) { trail = []; mark(c); if (S.a) face(S.f.LOG[S.a]); return; }
      const full = Array.from({ length: plan.steps + 1 }, (_, n) => at(n));
      if (!animate || !isVisual() || reduceMotion.matches || plan.steps === 0) {
        trail = full;
        mark(c);
        face(c.r);
        return;
      }
      trail = [plan.from];
      mark({ ...c, r: undefined });
      spin = -plan.from * STEP;
      target = null;
      const duration = Math.min(2600, 500 + plan.steps * 70);
      const t0 = performance.now();
      const tick = t => {
        const p = Math.min(1, (t - t0) / duration);
        const eased = 1 - Math.pow(1 - p, 3);
        const n = Math.round(eased * plan.steps);
        if (trail.length !== n + 1) {
          trail = full.slice(0, n + 1);
          mark({ ...c, r: p >= 1 ? c.r : undefined });
        }
        spin = -(plan.from + plan.dir * eased * plan.steps) * STEP;
        if (p < 1) walkRAF = requestAnimationFrame(tick);
        else { walkRAF = null; mark(c); idle = performance.now(); }
      };
      walkRAF = requestAnimationFrame(tick);
    }
    function stop() {
      if (walkRAF) cancelAnimationFrame(walkRAF);
      walkRAF = null;
    }

    ringEl.addEventListener("pointerdown", e => {
      if (e.target.closest(".vl-node")) return;
      dragging = true;
      target = null;
      lastX = e.clientX;
      velocity = 0;
      ringEl.setPointerCapture(e.pointerId);
      ringEl.classList.add("grabbing");
    });
    ringEl.addEventListener("pointermove", e => {
      if (!dragging) return;
      const dx = e.clientX - lastX;
      lastX = e.clientX;
      spin += dx * 0.008;
      velocity = dx * 0.008;
    });
    const end = () => { dragging = false; idle = performance.now(); ringEl.classList.remove("grabbing"); };
    ringEl.addEventListener("pointerup", end);
    ringEl.addEventListener("pointercancel", end);
    stageEl.addEventListener("keydown", e => {
      if (e.key === "ArrowLeft") { e.preventDefault(); target = (target ?? spin) - STEP; idle = performance.now(); }
      if (e.key === "ArrowRight") { e.preventDefault(); target = (target ?? spin) + STEP; idle = performance.now(); }
    });
    requestAnimationFrame(frame);
    return { render, stop, replay: () => renderStage({ animate: true }) };
  })();

  /* ---- wiring ---- */
  for (const key of ["a", "b"]) $(`vl-${key}`).addEventListener("input", () => update({ animate: false }));
  fieldSel.addEventListener("change", () => { S.f = field(Number(fieldSel.value)); update({ animate: true }); });
  $("vl-random").addEventListener("click", () => {
    const N = S.f.N;
    $("vl-a").value = hx(1 + Math.floor(Math.random() * N), S.f.m);
    $("vl-b").value = hx(1 + Math.floor(Math.random() * N), S.f.m);
    update({ animate: true });
  });
  $("vl-swap").addEventListener("click", () => {
    const a = $("vl-a").value;
    $("vl-a").value = $("vl-b").value;
    $("vl-b").value = a;
    update({ animate: true });
  });
  $("vl-mulview").querySelectorAll("button").forEach(b => b.addEventListener("click", () => {
    S.mulView = b.dataset.mulview;
    renderStage({ animate: true });
  }));
  $("vl-replay").addEventListener("click", () => (pane() === "add" ? Add.replay() : Ring.replay()));
  document.addEventListener("learnmodechange", () => renderStage({ animate: false }));

  update({ animate: false });

  return {
    load({ m, a, b, rel, mulView, scroll, play }) {
      fieldSel.value = String(m);
      S.f = field(m);
      $("vl-a").value = a;
      $("vl-b").value = b;
      S.rel = rel;
      if (mulView) S.mulView = mulView;
      if (scroll) $("vl-explorer").scrollIntoView({ behavior: smooth(), block: "start" });
      setTimeout(() => update({ animate: Boolean(play) }), scroll ? 450 : 0);
    },
    focusInputs() {
      $("vl-explorer").scrollIntoView({ behavior: smooth(), block: "start" });
      setTimeout(() => $("vl-a").focus({ preventScroll: true }), 400);
    },
    getShareState() {
      return {
        m: String(S.f.m),
        a: $("vl-a").value.trim(),
        b: $("vl-b").value.trim(),
        rel: S.rel,
        mulview: S.mulView,
      };
    },
    restoreShareState(params) {
      const m = Number(params.get("m"));
      if (!Number.isInteger(m) || m < 2 || m > 8) return false;
      const a = params.get("a") || "57";
      const b = params.get("b") || "83";
      const rel = ["add", "mul", "div", "inv"].includes(params.get("rel")) ? params.get("rel") : "mul";
      const mulView = params.get("mulview") === "ring" ? "ring" : "steps";
      fieldSel.value = String(m);
      S.f = field(m);
      $("vl-a").value = a;
      $("vl-b").value = b;
      S.rel = rel;
      S.mulView = mulView;
      update({ animate: false });
      return true;
    },
    onActivate() {
      mulViewIndicator.update();
    },
  };
}

/**
 * Initialize the Visual lab (`#visual`) and the header `Visual | Classic` mode switch
 * (visible and active strictly when `#visual` is the active tab).
 *
 * @returns {{
 *   onViewChange: (viewName: string) => void,
 *   getShareState: () => Record<string, string>,
 *   restoreShareState: (params: URLSearchParams) => boolean
 * }} Controller handle for `lab.js` and `explorations.js`.
 */
export function setupVisualLab() {
  const root = document.documentElement;
  const toggleGroup = $("learn-mode-toggle");
  const modeButtons = toggleGroup ? [...toggleGroup.querySelectorAll("[data-learn-mode]")] : [];
  const modeIndicator = attachSlidingIndicator(toggleGroup, '[aria-pressed="true"]');

  let mode = localStorage.getItem("ffl-learn-mode") === "classic" ? "classic" : "visual";
  const isVisual = () => mode === "visual";

  /**
   * Apply Visual or Classic presentation mode to the Visual lab view.
   * @param {"visual" | "classic"} next - Selected learning mode.
   */
  function setMode(next) {
    mode = next === "classic" ? "classic" : "visual";
    root.dataset.learnMode = mode;
    localStorage.setItem("ffl-learn-mode", mode);
    for (const b of modeButtons) {
      b.setAttribute("aria-pressed", String(b.dataset.learnMode === mode));
    }
    modeIndicator.update();
    document.dispatchEvent(new CustomEvent("learnmodechange", { detail: mode }));
  }

  for (const b of modeButtons) {
    b.addEventListener("click", () => setMode(b.dataset.learnMode));
  }
  setMode(mode);

  const view = document.querySelector('[data-lab-view="visual"]');
  if (!view) {
    return {
      onViewChange() { if (toggleGroup) toggleGroup.hidden = true; },
      getShareState() { return {}; },
      restoreShareState() { return false; },
    };
  }

  const lab = createExplorer(isVisual, view);
  setupPath(lab);

  return {
    onViewChange(viewName) {
      const showToggle = viewName === "visual";
      if (toggleGroup) {
        toggleGroup.hidden = !showToggle;
        if (showToggle) modeIndicator.update();
      }
      if (showToggle) lab.onActivate();
    },
    getShareState: () => lab.getShareState(),
    restoreShareState: params => lab.restoreShareState(params),
  };
}
