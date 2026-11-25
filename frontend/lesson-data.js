/**
 * @fileoverview Self-contained 7-lesson GF(2^m) visual curriculum for the Finite Field Lab.
 *
 * Original Author: Ali Zahreddine - Milestone 6 (Waves 1-4).
 *
 * Grounded directly in:
 *   - William Stallings, Cryptography and Network Security, Chapter 4 (Finite Fields:
 *     GF(2^m) polynomial basis, modulo-2 XOR addition/subtraction, modulo reduction,
 *     Shift-and-XOR multiplication, and Extended Euclid Table 4.7 inversion).
 *   - Stallings Chapter 6 (Block Cipher Operation: IEEE 1619-2007 XTS-AES over GF(2^128)).
 *   - Stallings Chapter 10 (Elliptic Curve Cryptography: NIST FIPS 186-4 / SEC 2 binary
 *     curves E_{2^m}(a,b) over GF(2^163) to GF(2^571) for RFID, IoT, smart cards, and FPGAs).
 *   - Hankerson, Menezes, and Vanstone, Guide to Elliptic Curve Cryptography (memory
 *     explosion of lookup tables vs. algorithmic polynomial-basis arithmetic).
 */

/**
 * Complete 7-lesson self-contained curriculum consumed by `frontend/lessons.js`.
 * Every section renders all of its conceptual blocks, truth tables, worked examples,
 * interactive sandboxes, and self-check quizzes in one clean scrollable view.
 * @type {Array<object>}
 */
export const LESSONS = [
  {
    id: "foundations",
    number: 1,
    symbol: "GF",
    title: "Foundations: Bits, Polynomials & Finite Fields",
    subtitle: "Encode bit strings as polynomials over Z_2 and see why irreducible moduli build GF(2^m).",
    sublessons: [
      {
        id: "1.1",
        title: "1.1 · Bits ↔ Polynomials ↔ Hex",
        summary: "Every m-bit word encodes a polynomial of degree at most m − 1 with binary coefficients in {0, 1}.",
        activity: "bit-sandbox",
        blocks: [
          {
            title: "Bit i is the coefficient of x^i",
            formula: "f(x) = b_{m-1}x^{m-1} + … + b_1x + b_0,   where each b_i ∈ {0, 1}",
            explanation: "In a binary extension field GF(2^m), each element is an m-bit string whose bits act as polynomial coefficients. Wherever bit b_i = 1, the power x^i is present; wherever b_i = 0, that term is omitted. Shifting a bit string left by 1 bit raises every exponent by 1, which corresponds directly to multiplying the polynomial by x.",
            visual: {
              type: "cards",
              items: [
                { badge: "Worked Example · {57}", title: "01010111₂ = x^6 + x^4 + x^2 + x + 1", detail: "High nibble 5 = 0101₂, low nibble 7 = 0111₂. Set bits at i ∈ {6, 4, 2, 1, 0} give degree 6 and Hamming weight 5." },
                { badge: "Worked Example · {83}", title: "10000011₂ = x^7 + x + 1", detail: "Set bits at positions 7, 1, and 0 give degree 7 and Hamming weight 3." },
                { badge: "Basis Elements", title: "{01} = 1 · {02} = x · {80} = x^7", detail: "Degree of the zero polynomial {00} is −1 by convention; Hamming weight counts nonzero terms." },
              ],
            },
          },
        ],
      },
      {
        id: "1.2",
        title: "1.2 · Arithmetic Modulo 2",
        summary: "Coefficient arithmetic runs in Z_2 = {0, 1}, where 1 + 1 = 0 and carries never propagate across bit positions.",
        blocks: [
          {
            title: "Z_2 Addition / XOR Truth Table (Carry = 0 Always)",
            formula: "1 + 1 = 2 ≡ 0 (mod 2)   ⇒   x^k + x^k = 0   (no carry into x^{k+1})",
            explanation: "In ordinary arithmetic, adding 1 + 1 generates a carry into the next column. Over Z_2, every coefficient wraps modulo 2 inside its own column, so addition is bitwise exclusive-OR (⊕) with zero carry propagation.",
            visual: {
              type: "truth-table",
              caption: "Four rules of modulo-2 coefficient addition (Z_2)",
              headers: ["a", "b", "a + b mod 2 = a ⊕ b", "Carry = 0 / Plain-English Rule"],
              rows: [
                { a: "0", b: "0", out: "0", note: "Absent in both polynomials; stays 0 (Carry = 0)", tone: "unchanged" },
                { a: "0", b: "1", out: "1", note: "Present in B only; term survives (Carry = 0)", tone: "updated" },
                { a: "1", b: "0", out: "1", note: "Present in A only; term survives (Carry = 0)", tone: "updated" },
                { a: "1", b: "1", out: "0", note: "Present in both; matching terms cancel (1 + 1 ≡ 0 mod 2, Carry = 0)", tone: "reduced" },
              ],
            },
          },
          {
            title: "Ordinary Polynomials vs. Modulo-2 Polynomials",
            formula: "(x^3 + x^2) + (x^2 + x + 1):   Ordinary = x^3 + 2x^2 + x + 1   vs.   GF(2) = x^3 + x + 1",
            explanation: "In ordinary algebra over Z, combining x^2 + x^2 yields 2x^2. In GF(2)[x], the coefficient 2 reduces modulo 2 to 0, so x^2 vanishes completely. Because columns never exchange carries, a 163-bit or 571-bit addition completes in one parallel XOR layer in hardware.",
            visual: {
              type: "cards",
              items: [
                { badge: "Ordinary Algebra (Z[x])", title: "x^3 + 2x^2 + x + 1", detail: "Coefficients grow unboundedly (2, 3, 4, ...) and binary integers generate long carry chains." },
                { badge: "Binary Field Algebra (GF(2)[x])", title: "x^3 + x + 1", detail: "2 mod 2 = 0 eliminates x^2; every bit column computes independently in O(1) gate depth." },
              ],
            },
          },
        ],
      },
      {
        id: "1.3",
        title: "1.3 · Why Irreducible m(x) Matters",
        summary: "Just as Z_p requires a prime integer p to be a field, GF(2^m) requires an irreducible degree-m polynomial m(x).",
        blocks: [
          {
            title: "Prime Integers vs. Irreducible Polynomials",
            formula: "Z_p is a field ⇔ p is prime   |   GF(2)[x]/⟨m(x)⟩ is a field ⇔ m(x) is irreducible",
            explanation: "A degree-m polynomial m(x) is irreducible over GF(2) when it cannot be factored into two non-constant lower-degree binary polynomials. Irreducibility guarantees gcd(m(x), b(x)) = 1 for every nonzero polynomial b(x) of degree < m, ensuring every nonzero element has a unique multiplicative inverse.",
            visual: {
              type: "cards",
              items: [
                { badge: "Irreducible · GF(2^8)", title: "x^8 + x^4 + x^3 + x + 1 ({11B})", detail: "No binary factors of degree 1 to 4; all 255 nonzero bytes have unique multiplicative inverses." },
                { badge: "Reducible · Broken Ring", title: "x^8 + 1 = (x + 1)^8", detail: "(x + 1) × (x^7 + x^6 + … + 1) ≡ 0 (mod x^8 + 1): nonzero factors multiply to 0, so neither has an inverse!" },
                { badge: "NIST B-163 Pentanomial", title: "x^163 + x^7 + x^6 + x^3 + 1", detail: "Irreducible degree-163 pentanomial whose sparse low terms make hardware and software reduction fast." },
              ],
            },
          },
        ],
      },
      {
        id: "1.4",
        title: "1.4 · Real-World Cryptography (Ch. 6 & Ch. 10)",
        summary: "How GF(2^128) and GF(2^163) to GF(2^571) power disk encryption and constrained binary elliptic curves.",
        quiz: {
          question: "Why do hardware designers choose binary fields GF(2^m) for RFID tags, IoT nodes, smart cards, and FPGAs?",
          options: [
            { text: "Carry-free XOR addition eliminates carry-propagation delay and lets compact bit-serial circuits run at high clock speeds.", correct: true },
            { text: "Binary fields allow multiplication using lookup tables for 163-bit and 571-bit keys.", correct: false },
          ],
        },
        blocks: [
          {
            title: "From 128-Bit Storage Tweaks to 571-Bit Elliptic Curves",
            formula: "GF(2^128) XTS-AES (IEEE 1619-2007)   |   GF(2^163) to GF(2^571) Binary ECC (NIST FIPS 186-4)",
            explanation: "The polynomial-basis operations taught in Stallings Chapter 4 directly power modern deployed standards. In Stallings Chapter 6, XTS-AES disk encryption updates 128-bit sector tweaks by shifting and conditionally XORing with 0x87. In Stallings Chapter 10, NIST binary elliptic curves E_{2^m}(a,b) over GF(2^163) through GF(2^571) run on RFID chips, smart cards, IoT devices, and FPGAs because carry-free arithmetic dramatically cuts silicon area and power consumption.",
            visual: {
              type: "cards",
              items: [
                { badge: "Stallings Ch. 6 · XTS-AES", title: "GF(2^128) · x^128 + x^7 + x^2 + x + 1", detail: "Encrypts disk sectors with C_j = E_{K_1}(P_j ⊕ T_j) ⊕ T_j where T_j = T_0 ⊗ α^j (XOR 0x87 when b_127 = 1)." },
                { badge: "Stallings Ch. 10 · Binary ECC", title: "GF(2^163) to GF(2^571) · NIST B-163", detail: "Point doubling and addition evaluate slope λ = (y_1 ⊕ y_2)/(x_1 ⊕ x_2) using XOR, Shift-and-XOR, and Extended Euclid." },
                { badge: "Hardware & Edge Impact", title: "IoT · RFID · Smart Cards · FPGAs", detail: "Zero carries eliminate long adder chains, enabling compact low-energy cryptographic accelerators." },
              ],
            },
          },
        ],
      },
    ],
  },
  {
    id: "addition",
    number: 2,
    symbol: "＋",
    title: "Addition (+) in GF(2^m)",
    subtitle: "Align coefficients by power of x and XOR matching bit columns with zero carries.",
    sublessons: [
      {
        id: "2.1",
        title: "2.1 · Addition Rule: Modulo-2 Truth Table",
        summary: "Adding polynomial coefficients in Z_2 follows the 4-row XOR truth table with zero carry into higher powers.",
        blocks: [
          {
            title: "Z_2 Coefficient Addition Truth Table",
            formula: "c_k = (a_k + b_k) mod 2 = a_k ⊕ b_k   for every exponent k = 0, …, m − 1",
            explanation: "Each power x^k is processed independently. When exactly one operand contains x^k, the term appears in the sum; when both operands contain x^k, the two 1s cancel to 0.",
            visual: {
              type: "truth-table",
              caption: "Bitwise addition table in GF(2)",
              headers: ["a_k", "b_k", "a_k + b_k mod 2 = a_k ⊕ b_k", "Carry = 0 / Effect on x^k"],
              rows: [
                { a: "0", b: "0", out: "0", note: "Neither polynomial has x^k (Carry = 0)", tone: "unchanged" },
                { a: "0", b: "1", out: "1", note: "Keep x^k from B(x) (Carry = 0)", tone: "updated" },
                { a: "1", b: "0", out: "1", note: "Keep x^k from A(x) (Carry = 0)", tone: "updated" },
                { a: "1", b: "1", out: "0", note: "Cancel matching x^k terms: 1 ⊕ 1 = 0 (Carry = 0)", tone: "reduced" },
              ],
            },
          },
        ],
      },
      {
        id: "2.2",
        title: "2.2 · Worked Example: {57} + {83} = {D4}",
        summary: "Line up all 8 bit columns of {57} and {83} in GF(2^8) and watch x^1 and 1 cancel via 1 ⊕ 1 = 0.",
        blocks: [
          {
            title: "Column-by-Column Bitwise XOR in GF(2^8)",
            formula: "{57} ⊕ {83} = (x^6 + x^4 + x^2 + x + 1) ⊕ (x^7 + x + 1) = x^7 + x^6 + x^4 + x^2 = {D4}",
            explanation: "In the upper nibble (x^7 down to x^4), no 1 bits overlap, yielding 1101₂ = {D}. In the lower nibble (x^3 down to 1), x^2 survives while both x^1 and 1 appear in both operands and cancel (1 ⊕ 1 = 0), yielding 0100₂ = {4}. Notice that deg(A + B) ≤ max(deg(A), deg(B)) < m, so adding two already-reduced elements never requires modulo reduction.",
            visual: {
              type: "xor-columns",
              aLabel: "A = {57}",
              bLabel: "B = {83}",
              outLabel: "A ⊕ B = {D4}",
              aBits: "01010111",
              bBits: "10000011",
              highlightRange: [0, 7],
              note: "Columns x^1 and 1 both cancel (1 ⊕ 1 → 0), giving 11010100₂ = {D4} = x^7 + x^6 + x^4 + x^2.",
            },
          },
        ],
      },
      {
        id: "2.3",
        title: "2.3 · Interactive 4-Bit XOR Practice",
        summary: "Verify your understanding with a hands-on 4-bit XOR check and self-check question.",
        activity: "xor-check",
        quiz: {
          question: "In GF(2^8), why does adding two reduced polynomials of degree < 8 never require a modulo reduction step?",
          options: [
            { text: "Because bitwise XOR never creates a degree higher than max(deg(A), deg(B)) < 8.", correct: true },
            { text: "Because the modulus {11B} is automatically added to every sum.", correct: false },
          ],
        },
        blocks: [
          {
            title: "Complexity & Closure Guarantee",
            formula: "deg(A(x) ⊕ B(x)) ≤ max(deg(A), deg(B)) < m   ·   O(m) bit operations",
            explanation: "Because addition never increases the maximum exponent, the sum of any two elements of GF(2^m) automatically stays inside GF(2^m). Try toggling the 4 output bits below to compute 1011₂ ⊕ 0111₂ yourself.",
            visual: {
              type: "cards",
              items: [
                { badge: "Closure", title: "Always Fits in m Bits", detail: "Zero carries mean a bit can never spill into position x^m." },
                { badge: "Performance", title: "Single Word XOR", detail: "In Python or hardware, even 571-bit addition finishes in nanoseconds." },
              ],
            },
          },
        ],
      },
    ],
  },
  {
    id: "subtraction",
    number: 3,
    symbol: "−",
    title: "Subtraction (−) & Additive Inverses",
    subtitle: "Why −1 ≡ +1 (mod 2) makes subtraction identical to addition in every binary finite field.",
    sublessons: [
      {
        id: "3.1",
        title: "3.1 · Why −1 ≡ +1 (mod 2)",
        summary: "Every polynomial in GF(2^m) is its own additive inverse, eliminating borrows completely.",
        blocks: [
          {
            title: "Self-Inverse Property: −B(x) = B(x)",
            formula: "−1 ≡ +1 (mod 2)   ⇒   B(x) ⊕ B(x) = 0   ⇒   A(x) − B(x) = A(x) + B(x) = A(x) ⊕ B(x)",
            explanation: "The additive inverse of B(x) is the unique element that adds to B(x) to yield 0. Because 1 ⊕ 1 = 0 in every bit position, adding B(x) to itself cancels every nonzero term. Therefore −B(x) = B(x), and subtracting B(x) is identical to adding B(x) with zero borrow propagation.",
            visual: {
              type: "cards",
              items: [
                { badge: "Additive Inverse", title: "A(x) ⊕ A(x) = 0", detail: "Every polynomial is its own negative: negating leaves every coefficient untouched." },
                { badge: "No Borrows", title: "0 − 1 ≡ 0 + 1 = 1 (mod 2)", detail: "Unlike integer subtraction, bit columns never borrow from higher exponents." },
              ],
            },
          },
        ],
      },
      {
        id: "3.2",
        title: "3.2 · Worked Examples: Self-Inverse & {57} − {83}",
        summary: "Verify A ⊕ A = 0 and confirm that ({57} − {83}) + {83} recovers {57}.",
        blocks: [
          {
            title: "1. Self-Inverse Cancellation: {57} − {57} = {00}",
            formula: "{57} ⊕ {57} = 01010111₂ ⊕ 01010111₂ = 00000000₂ = {00}",
            explanation: "Every set bit in {57} aligns with the identical set bit in itself, triggering 1 ⊕ 1 = 0 across all five nonzero terms (x^6, x^4, x^2, x, 1).",
            visual: {
              type: "xor-columns",
              aLabel: "A = {57}",
              bLabel: "A = {57}",
              outLabel: "A − A = {00}",
              aBits: "01010111",
              bBits: "01010111",
              highlightRange: [0, 7],
              note: "All matching 1s cancel simultaneously, proving −{57} = {57}.",
            },
          },
          {
            title: "2. Subtraction Equals Addition: {57} − {83} = {D4}",
            formula: "{57} − {83} = {57} ⊕ {83} = {D4}   ·   Check: {D4} ⊕ {83} = {57}",
            explanation: "Subtracting {83} from {57} yields {D4}, the exact same result as {57} + {83}. Adding {83} back cancels {83} via {83} ⊕ {83} = 0 and recovers {57}.",
            visual: {
              type: "xor-columns",
              aLabel: "A = {57}",
              bLabel: "B = {83}",
              outLabel: "A − B = {D4}",
              aBits: "01010111",
              bBits: "10000011",
              highlightRange: [0, 7],
              note: "Round-trip check: {D4} ⊕ {83} = 11010100₂ ⊕ 10000011₂ = 01010111₂ = {57}.",
            },
          },
        ],
      },
      {
        id: "3.3",
        title: "3.3 · Unifying Encryption, Euclid & ECC",
        summary: "One XOR gate array handles both addition and subtraction across protocols.",
        quiz: {
          question: "In Stallings Table 4.7 (Extended Euclid), the recurrence is written B_i ← A_i − Q × B_i. How is that subtraction executed in GF(2^m)?",
          options: [
            { text: "Using bitwise XOR: T_i = A_i ⊕ (Q × B_i).", correct: true },
            { text: "Using two's complement integer subtraction with borrow bits.", correct: false },
          ],
        },
        blocks: [
          {
            title: "Where Self-Inverse Subtraction Appears",
            formula: "XTS-AES: (P_j ⊕ T_j) ⊕ T_j = P_j   |   Extended Euclid: T_i = A_i ⊕ (Q · B_i)",
            explanation: "Because + and − are identical in characteristic 2, XTS-AES tweak whitening uses the exact same XOR step for encryption and decryption, Extended Euclid subtracts quotient multiples via carry-free XOR, and binary elliptic curve point subtraction computes −(x, y) = (x, x ⊕ y) with a single XOR.",
            visual: {
              type: "cards",
              items: [
                { badge: "XTS-AES Whitening", title: "Involution (P ⊕ T) ⊕ T = P", detail: "Applying the 128-bit sector tweak before and after AES cancels cleanly on decryption." },
                { badge: "Extended Euclid", title: "T_i = A_i ⊕ (Q · B_i)", detail: "Every Bézout triple update uses carry-free XOR rather than signed integer subtraction." },
                { badge: "Binary ECC Negation", title: "−(x, y) = (x, x ⊕ y)", detail: "Reversing a point on y^2 + xy = x^3 + ax^2 + b takes one field XOR." },
              ],
            },
          },
        ],
      },
    ],
  },
  {
    id: "modulo",
    number: 4,
    symbol: "mod",
    title: "Modulo Reduction (mod m(x))",
    subtitle: "Cancel overflow terms of degree d ≥ m by aligning m(x) << (d − m) and XORing.",
    sublessons: [
      {
        id: "4.1",
        title: "4.1 · Degree Overflow & Core Identity",
        summary: "Because m(x) ≡ 0 (mod m(x)), the leading term x^m folds directly into the low-degree tail of m(x).",
        blocks: [
          {
            title: "The Fundamental Reduction Identity: x^m ≡ m(x) − x^m",
            formula: "m(x) = x^m + r(x) ≡ 0 (mod m(x))   ⇒   x^m ≡ r(x) (mod m(x))",
            explanation: "Every canonical element of GF(2^m) must fit in m bits (degree < m). Whenever an input or raw polynomial product reaches degree d ≥ m, we align the leading x^m term of m(x) directly beneath x^d by shifting left by k = d − m bits and XORing. That single XOR cancels x^d and folds its weight into lower powers.",
            visual: {
              type: "cards",
              items: [
                { badge: "GF(2^8) · m(x) = {11B}", title: "x^8 ≡ x^4 + x^3 + x + 1 ({1B})", detail: "Any 9-bit overflow replaces x^8 with the low byte {1B}." },
                { badge: "GF(2^128) · XTS-AES", title: "x^128 ≡ x^7 + x^2 + x + 1 ({87})", detail: "A 128-bit tweak overflow folds into the single low byte 0x87." },
                { badge: "GF(2^163) · NIST B-163", title: "x^163 ≡ x^7 + x^6 + x^3 + 1 ({C9})", detail: "A 163-bit overflow folds into just 4 low-degree taps." },
              ],
            },
          },
        ],
      },
      {
        id: "4.2",
        title: "4.2 · Worked Reduction: {2B79} mod {11B} = {C1}",
        summary: "Follow every shift-and-XOR elimination reducing the 14-bit raw product {2B79} down to {C1} in GF(2^8).",
        quiz: {
          question: "What is the result of reducing the modulus itself, m(x) = {11B}, modulo {11B} in GF(2^8)?",
          options: [
            { text: "{00} (zero), because {11B} ⊕ {11B} = {00}, which is why m(x) itself has no multiplicative inverse.", correct: true },
            { text: "{01} (the multiplicative identity).", correct: false },
          ],
        },
        blocks: [
          {
            title: "Multi-Step Reduction: {2B79} mod {11B} = {C1}",
            formula: "{57} × {83} (raw carry-free product) = {2B79} (deg 13)   ⇒   {2B79} mod {11B} = {C1} (deg 7)",
            explanation: "When we multiply {57} and {83} without intermediate reduction, we obtain the degree-13 polynomial {2B79} = x^13 + x^11 + x^9 + x^8 + x^6 + x^5 + x^4 + x^3 + 1. Repeatedly aligning m(x) << (d − 8) under the current leading term cancels every degree ≥ 8 in 5 clean XOR steps, leaving {C1}.",
            visual: {
              type: "worked-table",
              caption: "Step-by-step elimination of {2B79} modulo m(x) = {11B} (m = 8)",
              headers: ["Step", "Leading Term", "Before (hex)", "Shifted Modulus · m(x) << k", "After XOR (hex)"],
              rows: [
                ["1", "x^13 (d = 13)", "2B79", "m(x) << 5 : 2360", "0819"],
                ["2", "x^11 (d = 11)", "0819", "m(x) << 3 : 08D8", "00C1"],
              ],
              highlightLastCol: true,
              note: "Only 2 XOR cancellations drop degree 13 → 11 → 7! At {00C1} (deg 7 < 8), reduction stops: {2B79} mod {11B} = {C1}.",
            },
          },
          {
            title: "Single-Bit Overflow ({10E} mod {11B} = {15}) & Zero Edge Case",
            formula: "{10E} ⊕ ({11B} << 0) = {15}   |   {11B} ⊕ ({11B} << 0) = {00}",
            explanation: "When degree d equals m exactly (shift k = 0), one XOR with m(x) finishes the reduction. Note also that reducing m(x) itself modulo m(x) cancels every set bit and produces {00}.",
            visual: {
              type: "reduction-step",
              d: 8,
              m: 8,
              shift: 0,
              beforeHex: "10E",
              beforeBits: "100001110",
              beforePoly: "x^8 + x^3 + x^2 + x",
              reducerHex: "11B",
              reducerBits: "100011011",
              reducerPoly: "x^8 + x^4 + x^3 + x + 1",
              afterHex: "15",
              afterBits: "000010101",
              afterPoly: "x^4 + x^2 + 1",
              stage: "xor",
            },
          },
        ],
      },
    ],
  },
  {
    id: "multiplication",
    number: 5,
    symbol: "×",
    title: "Multiplication (×): Shift-and-XOR",
    subtitle: "Interleave 1-bit left shifts with conditional m(x) reductions and XOR partial products where bit b_i = 1.",
    sublessons: [
      {
        id: "5.1",
        title: "5.1 · Why Lookup Tables Fail at 2^163",
        summary: "Small textbook fields fit in lookup tables, but cryptographic fields require on-the-fly algorithmic multiplication.",
        blocks: [
          {
            title: "Memory Explosion vs. Shift-and-XOR",
            formula: "|GF(2^3)| = 8 (64-cell table)   vs.   |GF(2^163)| = 2^163 ≈ 1.17 × 10^49 elements",
            explanation: "As emphasized by Hankerson, Menezes, and Vanstone and Stallings Chapter 4, precomputing a multiplication table for GF(2^163) would require 2^326 entries, vastly exceeding the ~10^80 atoms in the observable universe. Shift-and-XOR computes any product on the fly in at most m iterations using O(m^2) bit operations and O(1) memory.",
            visual: {
              type: "cards",
              items: [
                { badge: "Tiny Field · GF(2^3)", title: "8 × 8 = 64 Cells", detail: "Easy to print in a textbook, but useless for cryptographic security." },
                { badge: "Byte Field · GF(2^8)", title: "256 × 256 = 65,536 Cells", detail: "Fits in RAM, yet shift-and-XOR avoids cache-timing leaks." },
                { badge: "NIST B-163 to B-571", title: "Shift-and-XOR: ≤ m Steps", detail: "Zero lookup tables: runs directly on integer shifts and XORs up to 571 bits." },
              ],
            },
          },
        ],
      },
      {
        id: "5.2",
        title: "5.2 · Multiplying by x (<< 1 & Conditional ⊕ m(x))",
        summary: "Check the top bit b_{m-1} before shifting left: if b_{m-1} = 1, XOR with the low taps of m(x).",
        blocks: [
          {
            title: "Case A · MSB b_7 = 0 (No Overflow: {57} << 1 = {AE})",
            formula: "b_7({57}) = 0   ⇒   x · {57} mod {11B} = {57} << 1 = 10101110₂ = {AE}",
            explanation: "Because bit 7 of {57} (01010111₂) is 0, shifting left by 1 bit produces degree 7 < 8. No modulo reduction is needed.",
            visual: {
              type: "shift-register",
              inputHex: "57",
              inputBits: "01010111",
              msb: 0,
              shiftedBits: "10101110",
              reduced: false,
              modLowHex: "1B",
              outputHex: "AE",
              outputBits: "10101110",
              note: "MSB was 0 → pure 1-bit left shift produces {AE}.",
            },
          },
          {
            title: "Case B · MSB b_7 = 1 (Overflow Reduction: {02} × {87} = {15})",
            formula: "b_7({87}) = 1   ⇒   (({87} << 1) & 0xFF) ⊕ {1B} = {0E} ⊕ {1B} = {15}",
            explanation: "When multiplying {87} (10000111₂) by x = {02}, top bit b_7 is 1. Shifting left pops x^8 out of the 8-bit register, so we immediately XOR with {1B} (x^4 + x^3 + x + 1) to get {15}.",
            visual: {
              type: "shift-register",
              inputHex: "87",
              inputBits: "10000111",
              msb: 1,
              shiftedBits: "00001110",
              reduced: true,
              modLowHex: "1B",
              outputHex: "15",
              outputBits: "00010101",
              note: "MSB was 1 → x^8 overflow triggers XOR with {1B} → {0E} ⊕ {1B} = {15}.",
            },
          },
        ],
      },
      {
        id: "5.3",
        title: "5.3 · Worked Example: {57} × {83} = {C1} (Tables 1 & 2)",
        summary: "Inspect all 8 Shift-and-XOR iterations from Stallings Chapter 4 and verify how bits 0, 1, and 7 sum to {C1}.",
        quiz: {
          question: "In {57} × {83} (where {83} = 10000011₂), which shifted values are XORed into the running sum?",
          options: [
            { text: "Only i = 0 ({57}), i = 1 ({AE}), and i = 7 ({38}), because bits b_0, b_1, and b_7 of {83} equal 1.", correct: true },
            { text: "All 8 shifted values from i = 0 through i = 7.", correct: false },
          ],
        },
        blocks: [
          {
            title: "Decomposing B(x) = {83} = x^7 + x + 1 (10000011₂)",
            formula: "{57} × {83} = ({57} · 1) ⊕ ({57} · x) ⊕ ({57} · x^7) mod {11B} = {57} ⊕ {AE} ⊕ {38} = {C1}",
            explanation: "At each step i = 0..7, we shift the previous term left by 1 bit (reducing by ⊕ {11B} whenever x^8 overflows) and inspect bit b_i of B(x) = {83}. Only steps where b_i = 1 update the running sum.",
            visual: {
              type: "mul-walkthrough",
              activeI: 7,
              rows: [
                { i: 0, bit: 1, partial: "57", reduced: false, acc: "57" },
                { i: 1, bit: 1, partial: "AE", reduced: false, acc: "F9" },
                { i: 2, bit: 0, partial: "47", reduced: true, acc: "F9" },
                { i: 3, bit: 0, partial: "8E", reduced: false, acc: "F9" },
                { i: 4, bit: 0, partial: "07", reduced: true, acc: "F9" },
                { i: 5, bit: 0, partial: "0E", reduced: false, acc: "F9" },
                { i: 6, bit: 0, partial: "1C", reduced: false, acc: "F9" },
                { i: 7, bit: 1, partial: "38", reduced: false, acc: "C1" },
              ],
              note: "Selected partial products (green rows where bit = 1): {57} ⊕ {AE} ⊕ {38} = {F9} ⊕ {38} = {C1} (11000001₂).",
            },
          },
        ],
      },
    ],
  },
  {
    id: "inverse",
    number: 6,
    symbol: "x⁻¹",
    title: "Extended Euclid & Multiplicative Inverse",
    subtitle: "Master polynomial long division (POLY_DIVMOD), Bézout's invariant, and Stallings Table 4.7.",
    sublessons: [
      {
        id: "6.1",
        title: "6.1 · POLY_DIVMOD & Bézout's Invariant",
        summary: "Inside every Extended Euclid step, Euclidean polynomial long division shrinks the remainder degree while preserving B1·m ⊕ B2·b = B3.",
        blocks: [
          {
            title: "1. Polynomial Long Division (POLY_DIVMOD)",
            formula: "A3(x) = Q(x) · B3(x) ⊕ R(x),   with deg(R) < deg(B3)",
            explanation: "To divide A3 = x^8 + x^4 + x^3 + x + 1 ({11B}, deg 8) by B3 = x^7 + x + 1 ({83}, deg 7), shift B3 left by 8 − 7 = 1 (setting quotient term x) and XOR with A3 to cancel x^8.",
            visual: {
              type: "poly-divmod",
              dividend: "x^8 + x^4 + x^3 + x + 1 ({11B})",
              divisor: "x^7 + x + 1 ({83})",
              quotient: "x ({02})",
              shiftedDivisor: "x^8 + x^2 + x ({106})",
              remainder: "x^4 + x^3 + x^2 + 1 ({1D})",
              note: "deg(R) = 4 < deg(B3) = 7, so division finishes in 1 shift: Q(x) = x ({02}), R(x) = {1D}.",
            },
          },
          {
            title: "2. Bézout's Identity & Both Termination Rules",
            formula: "Invariant: B1(x)·m(x) ⊕ B2(x)·b(x) = B3(x)   ⇒   B2(x)·b(x) ≡ B3(x) (mod m(x))",
            explanation: "Because B1(x)·m(x) vanishes modulo m(x), every row maintains B2(x)·b(x) ≡ B3(x) (mod m(x)). The loop strictly reduces deg(B3) at every step until one of two stopping conditions occurs.",
            visual: {
              type: "cards",
              items: [
                { badge: "Termination 1 · B3(x) = 1", title: "Inverse Found: B2(x) = b(x)⁻¹", detail: "Since gcd(m, b) = B3 = 1, the invariant gives B2·b ≡ 1 (mod m), so B2(x) is the unique inverse." },
                { badge: "Termination 2 · B3(x) = 0", title: "No Inverse: A3(x) = gcd(m, b)", detail: "Occurs when b ≡ 0 (mod m) (so A3 = m(x)) or when m(x) is reducible and shares a factor with b(x)." },
              ],
            },
          },
        ],
      },
      {
        id: "6.2",
        title: "6.2 · Worked Example: Stallings Table 4.7 ({83}⁻¹ = {80})",
        summary: "Follow all 4 rows of Stallings Table 4.7 computing (x^7 + x + 1)⁻¹ mod (x^8 + x^4 + x^3 + x + 1).",
        quiz: {
          question: "When Extended Euclid terminates with B3(x) = 1 in Table 4.7, which column contains the multiplicative inverse b(x)⁻¹?",
          options: [
            { text: "Column B2(x) (which equals x^7 = {80} for b(x) = {83}).", correct: true },
            { text: "Column Q(x) (the final quotient).", correct: false },
          ],
        },
        blocks: [
          {
            title: "Complete Stallings Table 4.7 Progression for {83}⁻¹ mod {11B}",
            formula: "Recurrence: A ← prev B,   Q = A3 div B3,   T_i = A_i ⊕ (Q · B_i)   (i = 1, 2, 3)",
            explanation: "Starting at Step 0 with A = (1, 0, {11B}) and B = (0, 1, {83}), each iteration divides A3 by B3, carries previous B into A, and updates B to T = A ⊕ Q·B. After just 3 divisions, deg(B3) drops 7 → 4 → 1 → 0 (B3 = 1), revealing B2 = x^7 ({80})!",
            visual: {
              type: "worked-table",
              caption: "Stallings Chapter 4 Table 4.7: computing {83}⁻¹ mod {11B}",
              headers: ["Step", "Q(x)", "A1", "A2", "A3", "B1", "B2", "B3"],
              rows: [
                ["0 (Init)", "-", "1 (01)", "0 (00)", "11B", "0 (00)", "1 (01)", "83"],
                ["1", "x (02)", "0 (00)", "1 (01)", "83", "1 (01)", "x (02)", "1D"],
                ["2", "x^3+x^2+1 (0D)", "1 (01)", "x (02)", "1D", "0D", "1B", "x (02)"],
                ["3 (Done)", "x^3+x^2+x (0E)", "0D", "1B", "x (02)", "47", "x^7 (80) ★", "1 (01) ★"],
              ],
              highlightLastRow: true,
              note: "Verification: {83} × {80} mod {11B} = (x^7 + x + 1)·x^7 mod (x^8 + x^4 + x^3 + x + 1) = 1 ({01}).",
            },
          },
        ],
      },
    ],
  },
  {
    id: "division",
    number: 7,
    symbol: "÷",
    title: "Field Division (÷) & Cryptographic Synthesis",
    subtitle: "Combine Extended Euclid inversion with Shift-and-XOR multiplication, and see how all operations power real standards.",
    sublessons: [
      {
        id: "7.1",
        title: "7.1 · Two-Stage Field Division: {C1} ÷ {83} = {57}",
        summary: "Field division A ÷ B is defined as A × B⁻¹ mod m(x) with automatic round-trip verification.",
        blocks: [
          {
            title: "Ring Long Division vs. Finite-Field Division",
            formula: "A(x) ÷ B(x) mod m(x) = A(x) × (B(x)⁻¹ mod m(x)) mod m(x),   for B(x) ≢ 0 (mod m(x))",
            explanation: "Unlike polynomial long division (POLY_DIVMOD) in the ring GF(2)[x], which leaves a remainder, exact division in the field GF(2^m) always produces a unique field element Q(x) satisfying Q(x) × B(x) ≡ A(x) (mod m(x)). Dividing by 0 or any multiple of m(x) (such as {11B} in GF(2^8)) terminates Stage 1 at B3 = 0 with no inverse.",
            visual: {
              type: "pipeline",
              activeStage: 3,
              stages: [
                { stage: "Stage 1 · EEA Inverse", title: "{83}⁻¹ mod {11B} = {80}", detail: "Extended Euclid Table 4.7 finds B⁻¹ = x^7 ({80}) in 3 division steps." },
                { stage: "Stage 2 · Shift-and-XOR", title: "{C1} × {80} mod {11B} = {57}", detail: "Multiply dividend A = {C1} by B⁻¹ = {80} to obtain quotient Q = {57}." },
                { stage: "Stage 3 · Live Proof ✓", title: "{57} × {83} mod {11B} = {C1}", detail: "Round-trip identity Q × B ≡ A confirms exact field division automatically." },
              ],
            },
          },
        ],
      },
      {
        id: "7.2",
        title: "7.2 · Putting It Together: XTS-AES, Binary ECC & GCM / GHASH",
        summary: "Connect every operation in Lessons 1 to 7 to deployed disk encryption, NIST elliptic curves, and authenticated encryption.",
        quiz: {
          question: "In Polynomial / Binary ECC point addition over NIST B-163, computing the slope s = (Y_p - Y_q) / (X_p + X_q) requires which two finite-field stages?",
          options: [
            { text: "Stage 1: Extended Euclid inversion of (X_p + X_q) mod m(x), followed by Stage 2: Shift-and-XOR multiplication by (Y_p + Y_q).", correct: true },
            { text: "A single 163-bit lookup table indexed by (X_p, Y_p).", correct: false },
          ],
        },
        blocks: [
          {
            title: "How Lessons 1 to 7 Power Real Cryptographic Standards",
            formula: "XTS-AES (GF(2^128)): << 1 & ⊕ 0x87   |   Binary ECC (GF(2^163)): ⊕, ×, ÷ via EEA   |   GCM / GHASH (GF(2^128)): (Y_{i-1} ⊕ X_i) · H",
            explanation: "Open the Applications tab to watch all three algorithms run live. XTS-AES advances 128-bit storage tweaks by repeating Lesson 5's shift-and-reduce rule modulo x^128 + x^7 + x^2 + x + 1. Binary ECC over NIST B-163 executes point doubling, point addition, and Elliptic Curve Diffie-Hellman (ECDH) on top of XOR, Shift-and-XOR multiplication, and Extended Euclid division. GHASH chains 128-bit XOR and polynomial multiplication with hash key H, using the NIST block bit convention. It is one component of GCM: a full GCM tag additionally needs message formatting and the AES counter mask.",
            visual: {
              type: "cards",
              items: [
                { badge: "XTS-AES · GF(2^128)", title: "Disk & Volume Encryption", detail: "Shifts T_j left by 1 bit per 16-byte block and XORs 0x87 whenever MSB b_127 = 1 (IEEE 1619-2007, Stallings Ch. 6)." },
                { badge: "NIST B-163 · GF(2^163)", title: "Polynomial ECC & ECDH", detail: "Slope s uses ÷ / EEA; X_r and Y_r use × Shift-and-XOR and ⊕ XOR, then verify y^2 + xy = x^3 + ax^2 + b and K = n_A P_B = n_B P_A (Stallings Ch. 10)." },
                { badge: "GCM · GHASH (GF(2^128))", title: "GHASH Universal Hash", detail: "Iteratively computes Y_i = (Y_{i-1} ⊕ X_i) · H mod (x^128 + x^7 + x^2 + x + 1) across ciphertext blocks (NIST SP 800-38D, Stallings Ch. 12)." },
              ],
            },
          },
        ],
      },
    ],
  },
];
