/**
 * @fileoverview Presentational hero modulus bit-strip renderer for the Finite Field Lab
 * Precision Instrument theme.
 *
 * Observes `#mod-bin` and `#mod-poly` on the Calculator view and renders a compact
 * coefficient strip inside the hero banner (amber bars for set `1` bits, zero horizontal
 * overflow across all supported degrees `m = 2..571` on desktop and mobile).
 */

const hero = document.querySelector('[data-lab-view="calculator"] .hero');
const source = document.getElementById("mod-bin");
const polySource = document.getElementById("mod-poly");

if (hero && source) {
  const strip = document.createElement("div");
  strip.className = "field-strip";
  strip.setAttribute("aria-hidden", "true");
  hero.append(strip);

  /**
   * Re-render the hero modulus bit strip whenever the active field modulus changes.
   */
  const render = () => {
    const bits = (source.textContent || "").replace(/[^01]/g, "");
    if (!bits) return;
    const m = bits.length - 1;
    const ones = [...bits].filter(b => b === "1").length;
    const cells = [...bits]
      .map((b, i) => `<i class="${b === "1" ? "on" : ""}" style="--i:${i}"></i>`)
      .join("");
    const gapPx = m > 64 ? 0 : 2;
    strip.innerHTML = `
      <div class="field-strip-bits" style="gap:${gapPx}px">${cells}</div>
      <div class="field-strip-caption">
        <span>m(x) = <b>${(polySource?.innerHTML || "").trim()}</b></span>
        <span><b>${m + 1}</b> coefficients · <b>${ones}</b> set · x<sup>${m}</sup> … x<sup>0</sup></span>
      </div>`;
  };

  new MutationObserver(render).observe(source, { childList: true, characterData: true, subtree: true });
  render();
}
