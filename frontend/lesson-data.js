/**
 * @fileoverview Structured 7-lesson animated curriculum data for the Finite Field Lab.
 *
 * Original Author: Ali Zahreddine - Milestone 6 (Interactive Lessons & Trace Redesign).
 *
 * Course References:
 *   - William Stallings, Cryptography and Network Security, Chapter 4 (Finite Fields:
 *     GF(2^m) polynomial basis, modulo-2 XOR addition/subtraction, modulo reduction,
 *     Shift-and-XOR multiplication, and Extended Euclid Table 4.7 inversion).
 *   - Stallings Chapter 5 (Advanced Encryption Standard: GF(2^8) byte arithmetic
 *     modulo x^8 + x^4 + x^3 + x + 1 = 0x11B, MixColumns, and SubBytes S-Box).
 *   - Stallings Chapter 6 (Block Cipher Operation: XTS-AES tweak arithmetic in GF(2^128)).
 *   - Stallings Chapter 10 (Elliptic Curve Cryptography: binary curves E_{2^m}(a,b)
 *     over NIST/SEC standard degrees m in {163, 233, 239, 283, 409, 571}).
 */

/**
 * Complete 7-lesson curriculum array consumed by `frontend/lessons.js`.
 * Each lesson contains metadata, sub-lessons, step frames, visual animation payloads,
 * interactive self-check questions, and one-click Calculator handoff presets.
 * @type {Array<object>}
 */
export const LESSONS = [
  {
    id: "foundations",
    number: 1,
    symbol: "GF",
    title: "Foundations: Bits, Polynomials & Why GF(2^m) Matters",
    subtitle: "Encode bit-strings as polynomials over Z₂ and understand why irreducible moduli create finite fields.",
    handoff: {
      label: "Open {57} × {83} in Calculator",
      m: 8,
      operation: "multiply",
      base: "hex",
      a: "57",
      b: "83",
    },
    sublessons: [
      {
        id: "1.1",
        title: "1.1 · Bits ↔ Polynomials ↔ Hex",
        summary: "Every m-bit string encodes a polynomial of degree at most m − 1 with binary coefficients in {0, 1}.",
        activity: "bit-sandbox",
        steps: [
          {
            title: "Bit i is the coefficient of x^i",
            formula: "f(x) = b_{m-1}x^{m-1} + … + b_1x + b_0,   b_i ∈ {0, 1}",
            explanation: "In GF(2^8), each byte has 8 bits (b7 down to b0). Whenever bit i is 1, the term x^i appears in the polynomial; whenever bit i is 0, that power is omitted.",
            visual: {
              type: "cards",
              items: [
                { badge: "Hexadecimal", title: "{57}", detail: "5 = 0101₂ (high nibble), 7 = 0111₂ (low nibble)" },
                { badge: "Binary (8 bits)", title: "01010111", detail: "Set bits at positions i ∈ {6, 4, 2, 1, 0}" },
                { badge: "Polynomial", title: "x^6 + x^4 + x^2 + x + 1", detail: "Degree 6 · Hamming weight 5 (five nonzero terms)" },
              ],
            },
          },
          {
            title: "Zero, constant 1, and single powers of x",
            formula: "00000001₂ = 1,   00000010₂ = x,   10000000₂ = x^7 = {80}",
            explanation: "Shifting a bit string left by 1 bit increases every exponent by 1, which corresponds to multiplying the polynomial by x.",
            visual: {
              type: "cards",
              items: [
                { badge: "Identity", title: "{01} = 1", detail: "Bit 0 is 1 → constant term x^0 = 1" },
                { badge: "Generator x", title: "{02} = x", detail: "Bit 1 is 1 → linear term x^1 = x" },
                { badge: "Stallings Ch. 4", title: "{83} = x^7 + x + 1", detail: "10000011₂ has set bits at exponents 7, 1, and 0" },
              ],
            },
          },
          {
            title: "Interactive 8-bit polynomial builder",
            formula: "Toggle any bit below to see Binary, Hex, and Polynomial update live",
            explanation: "Use the interactive 8-bit sandbox below to toggle powers x^7 down to 1 and observe how all three notations stay synchronized.",
            visual: {
              type: "cards",
              items: [
                { badge: "Degree", title: "Highest set bit", detail: "deg(0) = −1 by convention; deg({57}) = 6" },
                { badge: "Hamming weight", title: "Count of 1 bits", detail: "Measures sparsity: fewer set bits mean fewer XOR steps" },
              ],
            },
          },
        ],
      },
      {
        id: "1.2",
        title: "1.2 · Arithmetic Modulo 2",
        summary: "Coefficient arithmetic happens in Z₂ = {0, 1}, where 1 + 1 = 0 and carries never propagate.",
        steps: [
          {
            title: "Why 1 + 1 = 0 in characteristic 2",
            formula: "1 + 1 = 2 ≡ 0 (mod 2)   ⇒   x^k + x^k = 0",
            explanation: "In ordinary integer addition, 1 + 1 generates a carry into the next bit position. In GF(2), coefficients wrap modulo 2 inside their own column: no carry ever crosses into an adjacent power of x.",
            visual: {
              type: "xor-columns",
              aLabel: "Term A",
              bLabel: "Term B",
              outLabel: "A ⊕ B (mod 2)",
              aBits: "0101",
              bBits: "0110",
              activeCol: 1,
              note: "At x^2, both bits are 1 → 1 ⊕ 1 = 0 with zero carry into x^3.",
            },
          },
          {
            title: "Hardware & software speed advantage",
            formula: "Addition = Subtraction = Bitwise XOR (⊕)",
            explanation: "Because there is no carry chain, a 163-bit or 571-bit addition executes in a single clock cycle on hardware logic gates or one word-level XOR instruction in Python.",
            visual: {
              type: "cards",
              items: [
                { badge: "No Carry Chain", title: "O(1) Gate Depth", detail: "Every bit position computes independently in parallel" },
                { badge: "Self-Inverse", title: "A ⊕ A = 0", detail: "Every polynomial is its own additive inverse" },
              ],
            },
          },
        ],
      },
      {
        id: "1.3",
        title: "1.3 · Why Irreducible m(x) Matters",
        summary: "Just as Z_p requires a prime p to form a field, GF(2^m) requires an irreducible polynomial m(x) of degree m.",
        steps: [
          {
            title: "Prime integers vs. irreducible polynomials",
            formula: "Z_p is a field ⇔ p is prime   |   GF(2)[x]/⟨m(x)⟩ is a field ⇔ m(x) is irreducible",
            explanation: "An irreducible polynomial m(x) of degree m cannot be factored into two nonconstant polynomials of degree < m over GF(2). This guarantees gcd(m(x), b(x)) = 1 for every nonzero element b(x).",
            visual: {
              type: "cards",
              items: [
                { badge: "Irreducible (AES)", title: "x^8 + x^4 + x^3 + x + 1 ({11B})", detail: "No factors of degree 1..4 → all 255 nonzero bytes have inverses" },
                { badge: "Reducible (Broken)", title: "x^8 + 1 = (x + 1)^8", detail: "(x + 1) × (x^7 + … + 1) ≡ 0 → zero divisors exist, no inverse!" },
              ],
            },
          },
          {
            title: "What breaks when m(x) is reducible?",
            formula: "a(x) ≠ 0 and b(x) ≠ 0,  but  a(x) · b(x) ≡ 0 (mod m(x))",
            explanation: "If m(x) = a(x) · b(x), then neither factor can ever have a multiplicative inverse modulo m(x), because Extended Euclid terminates with B3 = 0 and A3 = gcd(m(x), b(x)) = a(x) ≠ 1.",
            visual: {
              type: "cards",
              items: [
                { badge: "Modulus Explorer", title: "Test any polynomial", detail: "Use the Modulus explorer tab to factor reducible moduli up to degree 571" },
                { badge: "Primary Field", title: "m(x) = x^163 + x^7 + x^6 + x^3 + 1", detail: "Sparse pentanomial defining GF(2^163) in Project-3" },
              ],
            },
          },
        ],
      },
      {
        id: "1.4",
        title: "1.4 · Real-World Cryptography (Ch. 4, 5, 6, 10)",
        summary: "How GF(2^8), GF(2^128), and GF(2^163)..GF(2^571) power AES, disk encryption, and elliptic curves.",
        quiz: {
          question: "Why does AES use m(x) = x^8 + x^4 + x^3 + x + 1 ({11B}) instead of x^8 + 1?",
          options: [
            { text: "Because {11B} is irreducible over GF(2), guaranteeing every nonzero byte has a unique multiplicative inverse for SubBytes.", correct: true },
            { text: "Because x^8 + 1 has too many terms to store in a byte.", correct: false },
          ],
        },
        steps: [
          {
            title: "Stallings Chapters 4, 5, 6, and 10 in one platform",
            formula: "m ∈ {8 (AES), 128 (XTS-AES), 163, 233, 239, 283, 409, 571 (Binary ECC)}",
            explanation: "The exact same polynomial-basis algorithms you learn in this lab scale from 8-bit AES bytes to 571-bit elliptic-curve coordinates.",
            visual: {
              type: "cards",
              items: [
                { badge: "Chapter 5 · AES", title: "GF(2^8) · m(x) = {11B}", detail: "SubBytes S-box uses b⁻¹ mod m(x); MixColumns multiplies by {02} and {03}" },
                { badge: "Chapter 6 · XTS-AES", title: "GF(2^128) Tweakable Encryption", detail: "Multiplies sector tweak T by α = x modulo x^128 + x^7 + x^2 + x + 1" },
                { badge: "Chapter 10 · Binary ECC", title: "GF(2^163) to GF(2^571)", detail: "Point addition slope λ = (y₁ + y₂)/(x₁ + x₂) requires fast field division" },
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
    handoff: {
      label: "Open {57} + {83} in Calculator",
      m: 8,
      operation: "add",
      base: "hex",
      a: "57",
      b: "83",
    },
    sublessons: [
      {
        id: "2.1",
        title: "2.1 · Prerequisite: Modulo-2 Truth Table",
        summary: "Adding coefficients in Z₂ is the exclusive-OR (XOR, ⊕) logical operation.",
        steps: [
          {
            title: "The four rules of coefficient addition",
            formula: "0 ⊕ 0 = 0,   0 ⊕ 1 = 1,   1 ⊕ 0 = 1,   1 ⊕ 1 = 0",
            explanation: "When only one polynomial contains x^k, the term survives in the sum. When both polynomials contain x^k, the two identical terms cancel out (1 ⊕ 1 = 0).",
            visual: {
              type: "cards",
              items: [
                { badge: "0 ⊕ 0 = 0", title: "Absent in both", detail: "Coefficient of x^k stays 0" },
                { badge: "0 ⊕ 1 = 1 · 1 ⊕ 0 = 1", title: "Present in exactly one", detail: "Term x^k is kept in the sum" },
                { badge: "1 ⊕ 1 = 0", title: "Present in both (Cancellation!)", detail: "x^k + x^k = 2x^k ≡ 0 (mod 2)" },
              ],
            },
          },
        ],
      },
      {
        id: "2.2",
        title: "2.2 · Animated Walkthrough: {57} + {83} = {D4}",
        summary: "Step column-by-column through the Stallings Chapter 4 addition example in GF(2^8).",
        steps: [
          {
            title: "Step 1 · Write both operands as 8-bit strings",
            formula: "{57} = 01010111₂ = x^6 + x^4 + x^2 + x + 1   |   {83} = 10000011₂ = x^7 + x + 1",
            explanation: "Line up the 8 bit positions from x^7 (leftmost MSB) down to x^0 = 1 (rightmost LSB).",
            visual: {
              type: "xor-columns",
              aLabel: "A = {57}",
              bLabel: "B = {83}",
              outLabel: "A ⊕ B",
              aBits: "01010111",
              bBits: "10000011",
              activeCol: -1,
              note: "Ready to XOR each column independently from x^7 down to 1.",
            },
          },
          {
            title: "Step 2 · High nibble columns (x^7 down to x^4)",
            diffSummary: "Evaluated upper 4 bit columns (x^7..x^4): three bits set to 1 (x^7, x^6, x^4) forming high hex nibble {D}.",
            formula: "x^7: 0⊕1=1,   x^6: 1⊕0=1,   x^5: 0⊕0=0,   x^4: 1⊕0=1   ⇒   1101₂ = {D}",
            explanation: "In the upper 4 bits, none of the 1 bits overlap: x^7 comes from {83}, while x^6 and x^4 come from {57}.",
            visual: {
              type: "xor-columns",
              aLabel: "A = {57}",
              bLabel: "B = {83}",
              outLabel: "A ⊕ B",
              aBits: "01010111",
              bBits: "10000011",
              activeCol: 0,
              highlightRange: [0, 3],
              note: "Upper nibble produces 1101₂ = D in hexadecimal.",
            },
          },
          {
            title: "Step 3 · Low nibble columns & 1 ⊕ 1 cancellations (x^3 down to 1)",
            diffSummary: "Evaluated lower 4 bit columns (x^3..1): x^2 set to 1 while matching 1s at x^1 and 1 cancelled (1 ⊕ 1 → 0), completing {D4}.",
            formula: "x^3: 0⊕0=0,   x^2: 1⊕0=1,   x^1: 1⊕1=0 (cancels!),   x^0: 1⊕1=0 (cancels!)   ⇒   0100₂ = {4}",
            explanation: "Notice columns x^1 and x^0: both {57} and {83} have 1s in those positions, so x + x = 0 and 1 + 1 = 0 cancel completely!",
            visual: {
              type: "xor-columns",
              aLabel: "A = {57}",
              bLabel: "B = {83}",
              outLabel: "A ⊕ B = {D4}",
              aBits: "01010111",
              bBits: "10000011",
              activeCol: 6,
              highlightRange: [4, 7],
              note: "Matching 1s at x^1 and x^0 pulse and cancel to 0 → final result 11010100₂ = {D4} = x^7 + x^6 + x^4 + x^2.",
            },
          },
        ],
      },
      {
        id: "2.3",
        title: "2.3 · Interactive XOR Check & Calculator Handoff",
        summary: "Test your understanding with an interactive bit-XOR challenge and launch the live Calculator.",
        activity: "xor-check",
        quiz: {
          question: "In GF(2^8), why does adding two reduced polynomials of degree < 8 never require a modulo reduction step?",
          options: [
            { text: "Because bitwise XOR never creates a degree higher than max(deg(A), deg(B)) < 8.", correct: true },
            { text: "Because the modulus {11B} is automatically added to every sum.", correct: false },
          ],
        },
        steps: [
          {
            title: "Try the interactive XOR bit challenge below",
            formula: "{57} ⊕ {83} = {D4} = x^7 + x^6 + x^4 + x^2",
            explanation: "Click the bits in the interactive XOR check below to compute a column-by-column sum yourself, or open {57} + {83} directly in the Calculator.",
            visual: {
              type: "cards",
              items: [
                { badge: "Complexity", title: "O(m) Bit Operations", detail: "Single word-level XOR in Python regardless of field size" },
                { badge: "Degree Bound", title: "deg(A + B) ≤ max(deg(A), deg(B)) < m", detail: "No overflow past x^(m−1) is ever possible for reduced inputs" },
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
    handoff: {
      label: "Open {57} − {83} in Calculator",
      m: 8,
      operation: "subtract",
      base: "hex",
      a: "57",
      b: "83",
    },
    sublessons: [
      {
        id: "3.1",
        title: "3.1 · Prerequisite: Why −1 ≡ +1 (mod 2)",
        summary: "In Z₂, adding 1 and subtracting 1 land on the exact same residue class.",
        steps: [
          {
            title: "Every element is its own negative",
            formula: "−1 ≡ +1 (mod 2)   ⇒   −B(x) = +B(x)   ⇒   A(x) − B(x) = A(x) + B(x) = A(x) ⊕ B(x)",
            explanation: "The additive inverse of B(x) is the polynomial that adds to B(x) to give 0. Since B(x) ⊕ B(x) = 0, the additive inverse of B(x) is B(x) itself!",
            visual: {
              type: "cards",
              items: [
                { badge: "Additive Inverse", title: "−B(x) = B(x)", detail: "Negating a polynomial in GF(2^m) leaves every coefficient unchanged" },
                { badge: "Zero Borrow", title: "No Borrow Propagation", detail: "0 − 1 ≡ 0 + 1 = 1 (mod 2) without borrowing from higher bits" },
              ],
            },
          },
        ],
      },
      {
        id: "3.2",
        title: "3.2 · Animated Walkthrough: Self-Inverse & {57} − {83}",
        summary: "Watch A(x) − A(x) cancel to zero and compare {57} − {83} side-by-side with {57} + {83}.",
        steps: [
          {
            title: "Self-inverse cancellation: A(x) − A(x) = 0",
            formula: "{57} − {57} = 01010111₂ ⊕ 01010111₂ = 00000000₂ = {00}",
            explanation: "Every set bit in A(x) aligns with the identical set bit in itself, triggering 1 ⊕ 1 = 0 across all m columns simultaneously.",
            visual: {
              type: "xor-columns",
              aLabel: "A = {57}",
              bLabel: "A = {57}",
              outLabel: "A − A = {00}",
              aBits: "01010111",
              bBits: "01010111",
              activeCol: 1,
              highlightRange: [0, 7],
              note: "All five nonzero terms (x^6, x^4, x^2, x, 1) pair up and cancel to 0.",
            },
          },
          {
            title: "Side-by-side proof: {57} − {83} = {57} + {83} = {D4}",
            diffSummary: "Changed second operand from {57} to {83}: only x^1 and 1 now cancel (1 ⊕ 1 → 0), while x^7, x^6, x^4, x^2 become 1 ({D4}).",
            formula: "({57} − {83}) + {83} = {D4} ⊕ {83} = {57}",
            explanation: "Subtracting {83} from {57} produces {D4}. Adding {83} back to {D4} cancels {83} and recovers {57}!",
            visual: {
              type: "xor-columns",
              aLabel: "A = {57}",
              bLabel: "B = {83}",
              outLabel: "A − B = {D4}",
              aBits: "01010111",
              bBits: "10000011",
              activeCol: 6,
              highlightRange: [0, 7],
              note: "{57} − {83} uses the exact same XOR truth table as {57} + {83} → {D4}.",
            },
          },
        ],
      },
      {
        id: "3.3",
        title: "3.3 · Cryptographic Takeaway & Handoff",
        summary: "Why characteristic-2 subtraction unifies encryption and decryption hardware.",
        quiz: {
          question: "In Stallings Table 4.7 (Extended Euclid), the recurrence is written B_i ← A_i − Q × B_i. How is the subtraction performed in GF(2^m)?",
          options: [
            { text: "Using bitwise XOR: T_i = A_i ⊕ (Q × B_i).", correct: true },
            { text: "Using two's complement integer subtraction with borrow bits.", correct: false },
          ],
        },
        steps: [
          {
            title: "One circuit for both + and −",
            formula: "AddRoundKey(State, K) =AddRoundKey⁻¹(State, K) = State ⊕ K",
            explanation: "In AES AddRoundKey and XTS-AES whitening, encryption (adding the key) and decryption (subtracting the key) use the exact same XOR gate array.",
            visual: {
              type: "cards",
              items: [
                { badge: "AES AddRoundKey", title: "Involution: (S ⊕ K) ⊕ K = S", detail: "Applying XOR twice with the round key restores the original state" },
                { badge: "Extended Euclid", title: "T_i = A_i ⊕ (Q · B_i)", detail: "Quotient multiples are subtracted via carry-free XOR" },
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
    subtitle: "Cancel overflow terms of degree d ≥ m by shifting the irreducible modulus m(x) by d − m and XORing.",
    handoff: {
      label: "Open {10E} mod {11B} in Calculator",
      m: 8,
      operation: "modulo",
      base: "hex",
      a: "10E",
      b: "",
    },
    sublessons: [
      {
        id: "4.1",
        title: "4.1 · Prerequisite: Degree Overflow (deg(f) ≥ m)",
        summary: "Multiplying or shifting polynomials can create terms of degree m or higher that must be folded back into GF(2^m).",
        steps: [
          {
            title: "When does a polynomial leave GF(2^m)?",
            formula: "GF(2^m) = { f(x) ∈ GF(2)[x]  |  deg(f) < m }",
            explanation: "Every canonical element of GF(2^8) fits in 8 bits (degree ≤ 7). If an unreduced input or product reaches bit 8 (x^8) or higher, we reduce it modulo m(x) until deg(r) < 8.",
            visual: {
              type: "cards",
              items: [
                { badge: "Reduced (deg < 8)", title: "{87} = x^7 + x^2 + x + 1", detail: "Highest term is x^7 → already inside GF(2^8)" },
                { badge: "Overflow (deg = 8)", title: "{10E} = x^8 + x^3 + x^2 + x", detail: "Bit 8 is set (degree 8 ≥ 8) → requires modulo reduction!" },
              ],
            },
          },
        ],
      },
      {
        id: "4.2",
        title: "4.2 · Core Identity: x^m ≡ m(x) − x^m (mod m(x))",
        summary: "Since m(x) ≡ 0 (mod m(x)) and subtraction is XOR, the leading term x^m equals the lower terms of m(x).",
        steps: [
          {
            title: "Replacing x^m with the low-degree tail of m(x)",
            formula: "m(x) = x^m + r(x) ≡ 0 (mod m(x))   ⇒   x^m ≡ r(x) (mod m(x))",
            explanation: "XORing a degree-d remainder with (m(x) << (d − m)) simultaneously cancels the leading x^d term and injects the lower-degree terms of x^(d−m) · m(x).",
            visual: {
              type: "cards",
              items: [
                { badge: "GF(2^8) · AES (Ch. 5)", title: "x^8 ≡ x^4 + x^3 + x + 1 ({1B})", detail: "Because m(x) = x^8 + x^4 + x^3 + x + 1 ({11B})" },
                { badge: "GF(2^163) · ECC (Ch. 10)", title: "x^163 ≡ x^7 + x^6 + x^3 + 1", detail: "A 163-bit overflow folds directly into 4 low bits!" },
              ],
            },
          },
        ],
      },
      {
        id: "4.3",
        title: "4.3 · Animated Walkthrough: {10E} mod {11B} = {15}",
        summary: "Watch the shifted modulus align under the highest term and cancel it via XOR.",
        quiz: {
          question: "What is the result of reducing the modulus itself, m(x) = {11B}, modulo {11B} in GF(2^8)?",
          options: [
            { text: "{00} (zero), which is why entering {11B} for Inverse or Divide triggers the zero-element error.", correct: true },
            { text: "{01} (multiplicative identity).", correct: false },
          ],
        },
        steps: [
          {
            title: "Step 1 · Inspect the unreduced dividend {10E}",
            formula: "f(x) = {10E} = 100001110₂ = x^8 + x^3 + x^2 + x   (degree d = 8 ≥ m = 8)",
            explanation: "In Stallings Chapter 5, multiplying {02} × {87} produces the 9-bit intermediate {10E}. Its highest set bit is at exponent d = 8.",
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
              afterHex: "015",
              afterBits: "000010101",
              afterPoly: "x^4 + x^2 + 1",
              stage: "align",
            },
          },
          {
            title: "Step 2 · Shift m(x) by d − m = 0 and XOR",
            diffSummary: "Applied XOR with {11B}: cancelled x^8 and x^3, introduced x^4 and 1, reducing {10E} → {15}.",
            formula: "{10E} ⊕ ({11B} << 0) = 100001110₂ ⊕ 100011011₂ = 000010101₂ = {15}",
            explanation: "Both x^8 and x^3 cancel out (1 ⊕ 1 = 0), while x^4 and 1 are introduced from {11B}, leaving {15} = x^4 + x^2 + 1 of degree 4 < 8.",
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
          {
            title: "Edge Case · Reducing m(x) = {11B} modulo {11B} gives {00}",
            diffSummary: "Switched input from {10E} to m(x) = {11B}: every set bit cancelled against m(x), collapsing remainder to {00}.",
            formula: "{11B} ⊕ {11B} = {00}   ⇒   m(x) ≡ 0 (mod m(x))",
            explanation: "Any multiple of m(x) reduces to 0. That is why the Calculator automatically reduces inputs first and rejects {11B} when computing an inverse or division!",
            visual: {
              type: "reduction-step",
              d: 8,
              m: 8,
              shift: 0,
              beforeHex: "11B",
              beforeBits: "100011011",
              beforePoly: "x^8 + x^4 + x^3 + x + 1",
              reducerHex: "11B",
              reducerBits: "100011011",
              reducerPoly: "x^8 + x^4 + x^3 + x + 1",
              afterHex: "00",
              afterBits: "000000000",
              afterPoly: "0",
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
    title: "Multiplication (×): Shift-and-XOR Algorithm",
    subtitle: "Interleave 1-bit left shifts with conditional m(x) reductions and accumulate partial products for set bits of B(x).",
    handoff: {
      label: "Open {57} × {83} in Calculator",
      m: 8,
      operation: "multiply",
      base: "hex",
      a: "57",
      b: "83",
    },
    secondaryHandoff: {
      label: "Compare with Long Division",
      view: "compare",
    },
    sublessons: [
      {
        id: "5.1",
        title: "5.1 · Why Not Lookup Tables?",
        summary: "Lookup tables work for tiny fields like GF(2^3), but cryptographic fields like GF(2^163) require direct algorithmic multiplication.",
        steps: [
          {
            title: "GF(2^3) vs. GF(2^163) storage explosion",
            formula: "|GF(2^3)| = 8 elements (64-cell table)   vs.   |GF(2^163)| = 2^163 ≈ 1.17 × 10^49 elements",
            explanation: "A multiplication lookup table for GF(2^163) would need 2^326 entries, more than the number of atoms in the observable universe (~10^80). Shift-and-XOR computes any product on the fly in at most m steps!",
            visual: {
              type: "cards",
              items: [
                { badge: "Tiny Field GF(2^3)", title: "8 × 8 Lookup Table", detail: "Only 64 cells; easy to print in a textbook" },
                { badge: "AES Field GF(2^8)", title: "256 × 256 = 65,536 Cells", detail: "Feasible in software, or computed directly with xtime()" },
                { badge: "Project-3 GF(2^163)..GF(2^571)", title: "Shift-and-XOR in ≤ m Steps", detail: "O(m^2) bit operations and O(1) memory words" },
              ],
            },
          },
        ],
      },
      {
        id: "5.2",
        title: "5.2 · Prerequisite: Multiplying by x (xtime Shift Register)",
        summary: "Inspect MSB bit b_{m-1} before shifting left: if b_{m-1} = 1, XOR the shifted register with the low terms of m(x).",
        steps: [
          {
            title: "Case A · MSB b₇ = 0 (No overflow: {57} × x = {AE})",
            formula: "b₇({57}) = 0   ⇒   x · {57} mod {11B} = {57} << 1 = 10101110₂ = {AE}",
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
            title: "Case B · MSB b₇ = 1 (Overflow reduction: {02} × {87} = {15})",
            diffSummary: "Input changed from {57} (MSB 0) to {87} (MSB 1): shifting now overflows x^8 and triggers XOR with {1B} → {15}.",
            formula: "b₇({87}) = 1   ⇒   (({87} << 1) & 0xFF) ⊕ {1B} = {0E} ⊕ {1B} = {15}",
            explanation: "In Stallings Chapter 5 ({02} × {87}), bit 7 of {87} (10000111₂) is 1. Shifting left pushes x^8 out of the 8-bit register, so we immediately XOR with {1B} (x^4 + x^3 + x + 1) to get {15}.",
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
              note: "MSB was 1 → x^8 overflow triggers XOR with {1B} → {0E} ⊕ {1B} = {15}!",
            },
          },
        ],
      },
      {
        id: "5.3",
        title: "5.3 · Animated Walkthrough: {57} × {83} = {C1}",
        summary: "Follow all 8 Shift-and-XOR steps from Stallings Chapter 4 (Table 1 shifts + Table 2 selected partial products).",
        quiz: {
          question: "In {57} × {83} (where {83} = 10000011₂), which shifted partial products x^i · {57} mod {11B} are XORed into the accumulator?",
          options: [
            { text: "Only i = 0 ({57}), i = 1 ({AE}), and i = 7 ({38}), because bits 0, 1, and 7 of {83} are 1.", correct: true },
            { text: "All 8 partial products from i = 0 through i = 7.", correct: false },
          ],
        },
        steps: [
          {
            title: "Step 1 · Decompose multiplier B = {83} = 10000011₂",
            formula: "{57} × (x^7 + x + 1) = ({57}·1) ⊕ ({57}·x) ⊕ ({57}·x^7) mod {11B}",
            explanation: "Only bits i ∈ {0, 1, 7} of {83} are 1. As we shift A = {57} from i = 0 up to i = 7, we add the shifted value into our accumulator only at i = 0, 1, and 7.",
            visual: {
              type: "mul-walkthrough",
              activeI: 0,
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
              note: "i = 0: Bit 0 of {83} is 1 → accumulator starts at 00 ⊕ 57 = {57}.",
            },
          },
          {
            title: "Step 2 · i = 1 selects {AE}; i = 2..4 overflow and reduce",
            diffSummary: "Accumulator updated {57} → {F9} at i = 1 (bit = 1); shifted value reduced {AE} → {47} at i = 2 while accumulator stayed {F9} (bit = 0).",
            formula: "i = 1: acc = {57} ⊕ {AE} = {F9}   |   i = 2: ({AE} << 1) ⊕ {11B} = {47} (skipped, bit 2 = 0)",
            explanation: "At i = 1, bit 1 is 1 so {AE} is XORed in ({57} ⊕ {AE} = {F9}). At i = 2 and i = 4, shifting overflows x^8 so {11B} reduces the partial product, while the accumulator stays {F9} because bits 2..6 of {83} are 0.",
            visual: {
              type: "mul-walkthrough",
              activeI: 2,
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
              note: "i = 2: {AE} had MSB = 1, so shifting reduced it to {47}; bit 2 of {83} is 0 so accumulator stays {F9}.",
            },
          },
          {
            title: "Step 3 · i = 7 selects {38} → Final Product {C1}",
            diffSummary: "Advanced from i = 2 to i = 7: bit 7 is 1, so XORing {38} updated accumulator {F9} → {C1} (final product).",
            formula: "i = 7: acc = {F9} ⊕ {38} = 11111001₂ ⊕ 00111000₂ = 11000001₂ = {C1} = x^7 + x^6 + 1",
            explanation: "At the final bit i = 7, bit 7 of {83} is 1. XORing {38} with the running accumulator {F9} yields {C1}!",
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
              note: "i = 7: Bit 7 is 1 → {F9} ⊕ {38} = {C1} (11000001₂). Table 2 is complete!",
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
    title: "Number Theory & Multiplicative Inverse (x⁻¹)",
    subtitle: "Master Euclidean polynomial long division, Bézout's GCD invariant, and Stallings Table 4.7 Extended Euclid.",
    handoff: {
      label: "Open {83}⁻¹ in Calculator",
      m: 8,
      operation: "inverse",
      base: "hex",
      a: "83",
      b: "",
    },
    secondaryHandoff: {
      label: "Explore AES S-Box",
      view: "aes",
    },
    sublessons: [
      {
        id: "6.1",
        title: "6.1 · Why We Need Multiplicative Inverses",
        summary: "The inverse b(x)⁻¹ satisfies b(x) · b(x)⁻¹ ≡ 1 (mod m(x)) and unlocks division, AES SubBytes, and ECC.",
        steps: [
          {
            title: "Definition & cryptographic applications",
            formula: "b(x) · b(x)⁻¹ ≡ 1 (mod m(x))   for every b(x) ≢ 0 (mod m(x))",
            explanation: "In GF(2^m), division A / B is computed as A × B⁻¹. Furthermore, the nonlinear core of the AES S-box (Stallings Ch. 5) and point-addition slopes on binary elliptic curves (Ch. 10) both depend on computing b(x)⁻¹ via Extended Euclid.",
            visual: {
              type: "cards",
              items: [
                { badge: "Stallings Table 4.7", title: "{83}⁻¹ mod {11B} = {80}", detail: "Because (x^7 + x + 1) · x^7 mod (x^8 + x^4 + x^3 + x + 1) = 1" },
                { badge: "Chapter 5 · AES S-Box", title: "{95}⁻¹ mod {11B} = {8A}", detail: "Inverts the byte in GF(2^8) before applying the affine XOR matrix" },
                { badge: "Zero Rule", title: "0 has NO inverse", detail: "0 · c(x) = 0 ≠ 1 for every polynomial c(x)" },
              ],
            },
          },
        ],
      },
      {
        id: "6.2",
        title: "6.2 · Prerequisite 1: Polynomial Long Division (POLY_DIVMOD)",
        summary: "Inside each Extended Euclid step, we divide A3(x) by B3(x) over GF(2)[x] to obtain quotient Q(x) and remainder R(x).",
        steps: [
          {
            title: "Euclidean division rule: A3(x) = Q(x)·B3(x) ⊕ R(x) with deg(R) < deg(B3)",
            formula: "Step 1 of Table 4.7:  (x^8 + x^4 + x^3 + x + 1) ÷ (x^7 + x + 1)",
            explanation: "To divide A3 = {11B} (degree 8) by B3 = {83} (degree 7), shift B3 by 8 − 7 = 1 (quotient term x^1 = x) and XOR with A3.",
            visual: {
              type: "poly-divmod",
              dividend: "x^8 + x^4 + x^3 + x + 1 ({11B})",
              divisor: "x^7 + x + 1 ({83})",
              quotient: "x ({02})",
              shiftedDivisor: "x^8 + x^2 + x ({106})",
              remainder: "x^4 + x^3 + x^2 + 1 ({1D})",
              note: "deg(R) = 4 < deg(B3) = 7, so division stops after 1 shift: Q(x) = x ({02}), R(x) = {1D}.",
            },
          },
        ],
      },
      {
        id: "6.3",
        title: "6.3 · Prerequisite 2: Polynomial GCD & Bézout's Identity",
        summary: "Extended Euclid tracks two triples (A1, A2, A3) and (B1, B2, B3) preserving B1·m(x) ⊕ B2·b(x) = B3(x).",
        steps: [
          {
            title: "Why B3(x) = 1 makes B2(x) the inverse!",
            formula: "Invariant:  B1(x)·m(x) ⊕ B2(x)·b(x) = B3(x)   ⇒   B2(x)·b(x) ≡ B3(x) (mod m(x))",
            explanation: "Because B1(x)·m(x) vanishes modulo m(x), the invariant guarantees B2(x)·b(x) ≡ B3(x) (mod m(x)) at every row! As soon as B3(x) reaches 1, B2(x)·b(x) ≡ 1 (mod m(x)), so B2(x) is b(x)⁻¹!",
            visual: {
              type: "cards",
              items: [
                { badge: "Case 1 · B3(x) = 1", title: "gcd(m, b) = 1 → Inverse Found!", detail: "B2(x) holds the unique multiplicative inverse b(x)⁻¹ mod m(x)" },
                { badge: "Case 2 · B3(x) = 0", title: "No Inverse Exists", detail: "A3(x) = gcd(m(x), b(x)) (equals m(x) if b ≡ 0, or a shared factor if m is reducible)" },
              ],
            },
          },
        ],
      },
      {
        id: "6.4",
        title: "6.4 · Animated Stallings Table 4.7: {83}⁻¹ = {80}",
        summary: "Step through all 4 rows of Stallings Chapter 4 Table 4.7 with zero horizontal overflow and animated triple transfers.",
        quiz: {
          question: "When Extended Euclid terminates with B3(x) = 1 in Table 4.7, which column holds the multiplicative inverse b(x)⁻¹ mod m(x)?",
          options: [
            { text: "Column B2(x) (which equals x^7 = {80} for b(x) = {83}).", correct: true },
            { text: "Column Q(x) (the final polynomial quotient).", correct: false },
          ],
        },
        steps: [
          {
            title: "Row 0 · Initialization",
            formula: "A ← (1, 0, m(x) = {11B}),   B ← (0, 1, b(x) = {83})",
            explanation: "At Step 0, Q(x) is undefined ('-'). A3 holds the modulus x^8 + x^4 + x^3 + x + 1 ({11B}) and B3 holds the input x^7 + x + 1 ({83}).",
            visual: {
              type: "euclid-step",
              step: 0,
              q: "-",
              formula: "Init: A ← (1, 0, m(x)),  B ← (0, 1, b(x))",
              a: { A1: "1 (01)", A2: "0 (00)", A3: "x^8+x^4+x^3+x+1 (11B)" },
              b: { B1: "0 (00)", B2: "1 (01)", B3: "x^7+x+1 (83)" },
              status: "running",
            },
          },
          {
            title: "Row 1 · Divide {11B} by {83} → Q = x ({02}), R = {1D}",
            diffSummary: "Previous B (0, 1, 83) carried into A; Q = x (02) computed new B = (1, x, 1D), dropping deg(B3) from 7 → 4.",
            formula: "Q = x,   T1 = 1 ⊕ (x·0) = 1,   T2 = 0 ⊕ (x·1) = x,   T3 = x^4+x^3+x^2+1 ({1D})",
            explanation: "Previous B shifts into A, and the newly computed (T1, T2, T3) becomes the new B. Notice deg(B3) dropped from 7 to 4!",
            visual: {
              type: "euclid-step",
              step: 1,
              q: "x (02)",
              formula: "A ← prev B,   B ← A ⊕ (x)·B",
              a: { A1: "0 (00)", A2: "1 (01)", A3: "x^7+x+1 (83)" },
              b: { B1: "1 (01)", B2: "x (02)", B3: "x^4+x^3+x^2+1 (1D)" },
              status: "running",
            },
          },
          {
            title: "Row 2 · Divide {83} by {1D} → Q = x^3+x^2+1 ({0D}), R = x ({02})",
            diffSummary: "Previous B (1, x, 1D) carried into A; Q = 0D computed new B = (0D, 1B, 02), dropping deg(B3) from 4 → 1.",
            formula: "Q = x^3+x^2+1,   T1 = 0 ⊕ Q·1 = x^3+x^2+1,   T2 = 1 ⊕ Q·x = x^4+x^3+x+1 ({1B}),   T3 = x ({02})",
            explanation: "Long division of x^7+x+1 by x^4+x^3+x^2+1 yields quotient x^3+x^2+1 ({0D}) and remainder x ({02}). deg(B3) is now 1.",
            visual: {
              type: "euclid-step",
              step: 2,
              q: "x^3+x^2+1 (0D)",
              formula: "A ← prev B,   B ← A ⊕ (x^3+x^2+1)·B",
              a: { A1: "1 (01)", A2: "x (02)", A3: "x^4+x^3+x^2+1 (1D)" },
              b: { B1: "x^3+x^2+1 (0D)", B2: "x^4+x^3+x+1 (1B)", B3: "x (02)" },
              status: "running",
            },
          },
          {
            title: "Row 3 · Termination! B3(x) = 1 → B2(x) = x^7 ({80}) is the Inverse",
            diffSummary: "Previous B (0D, 1B, 02) carried into A; Q = 0E drove B3 → 1 and produced inverse B2 = x^7 ({80}).",
            formula: "Q = x^3+x^2+x ({0E}),   T2 = x ⊕ (x^3+x^2+x)(x^4+x^3+x+1) = x^7 ({80}),   T3 = 1 ({01})",
            explanation: "Dividing x^4+x^3+x^2+1 by x leaves remainder B3 = 1! Because B3(x) = 1, the algorithm terminates and B2(x) = x^7 ({80}) is the verified inverse of {83}!",
            visual: {
              type: "euclid-step",
              step: 3,
              q: "x^3+x^2+x (0E)",
              formula: "B3(x) = 1 ⇒ Termination! B2(x) = x^7 ({80}) = {83}⁻¹",
              a: { A1: "x^3+x^2+1 (0D)", A2: "x^4+x^3+x+1 (1B)", A3: "x (02)" },
              b: { B1: "x^6+x^2+x+1 (47)", B2: "x^7 (80) ★ INVERSE", B3: "1 (01) ★ DONE" },
              status: "success",
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
    title: "Division (÷): Two-Stage Field Division",
    subtitle: "Combine Extended Euclid inversion of B(x) with Shift-and-XOR multiplication by A(x) and verify (A/B)·B = A.",
    handoff: {
      label: "Open {C1} ÷ {83} in Calculator",
      m: 8,
      operation: "divide",
      base: "hex",
      a: "C1",
      b: "83",
    },
    sublessons: [
      {
        id: "7.1",
        title: "7.1 · Prerequisite: Turning Division Into Multiplication",
        summary: "Finite-field division A(x) / B(x) is defined as multiplying A(x) by the multiplicative inverse B(x)⁻¹.",
        steps: [
          {
            title: "Two-stage identity in GF(2^m)",
            formula: "A(x) / B(x) mod m(x)  =  A(x) × (B(x)⁻¹ mod m(x)) mod m(x),    B(x) ≢ 0 (mod m(x))",
            explanation: "Note that polynomial Euclidean long division (POLY_DIVMOD) gives a quotient and remainder in the ring GF(2)[x], which is NOT field division! In the finite field GF(2^m), exact division by any nonzero B(x) always succeeds with zero remainder by multiplying by B(x)⁻¹.",
            visual: {
              type: "cards",
              items: [
                { badge: "Stage 1 · Extended Euclid", title: "Compute B(x)⁻¹ mod m(x)", detail: "Finds the unique field element whose product with B(x) is 1" },
                { badge: "Stage 2 · Shift-and-XOR", title: "Compute Q(x) = A(x) × B(x)⁻¹ mod m(x)", detail: "Multiplies reduced dividend A(x) by the inverse from Stage 1" },
                { badge: "Stage 3 · Live Proof", title: "Verify Q(x) × B(x) mod m(x) == A(x)", detail: "Confirms the round-trip algebraic identity automatically" },
              ],
            },
          },
        ],
      },
      {
        id: "7.2",
        title: "7.2 · Animated Two-Stage Pipeline: {C1} ÷ {83} = {57}",
        summary: "Walk through dividing {C1} by {83} in GF(2^8) to recover {57}.",
        steps: [
          {
            title: "Stage 1 · Invert divisor B(x) = {83} via Extended Euclid",
            formula: "EXTENDED_EUCLID_GF2M(m(x) = {11B}, B(x) = {83})  ⇒  B(x)⁻¹ = {80} = x^7  (in 3 steps)",
            explanation: "First, run Extended Euclid on B(x) = {83} modulo {11B}. As shown in Table 4.7 (Lesson 6), B3 reaches 1 at Step 3 with B2 = {80} = x^7.",
            visual: {
              type: "pipeline",
              activeStage: 1,
              stages: [
                { stage: "Stage 1 · Inverse", title: "{83}⁻¹ mod {11B} = {80}", detail: "Extended Euclid Table 4.7 completes in 3 division steps (x^7)" },
                { stage: "Stage 2 · Multiply", title: "{C1} × {80} mod {11B}", detail: "Pending: multiply dividend A = {C1} by B⁻¹ = {80}" },
                { stage: "Stage 3 · Verify", title: "Q × {83} mod {11B} == {C1}", detail: "Pending: confirm algebraic round-trip identity" },
              ],
            },
          },
          {
            title: "Stage 2 · Multiply dividend A(x) = {C1} by B(x)⁻¹ = {80}",
            diffSummary: "Stage 1 completed (B⁻¹ = {80}); Stage 2 multiplied {C1} × {80} mod {11B} to obtain quotient {57}.",
            formula: "GF2M_MULTIPLY({C1}, {80}, {11B})  =  (x^7 + x^6 + 1) × x^7 mod {11B}  =  {57}",
            explanation: "Next, run Shift-and-XOR to multiply A = {C1} by B⁻¹ = {80} (which has a single set bit at i = 7). After 7 shifts and reductions modulo {11B}, the product is {57} = x^6 + x^4 + x^2 + x + 1!",
            visual: {
              type: "pipeline",
              activeStage: 2,
              stages: [
                { stage: "Stage 1 · Inverse", title: "{83}⁻¹ mod {11B} = {80}", detail: "Completed: B⁻¹ = x^7" },
                { stage: "Stage 2 · Multiply", title: "{C1} × {80} mod {11B} = {57}", detail: "Shift-and-XOR shifts {C1} seven times modulo {11B} → {57}" },
                { stage: "Stage 3 · Verify", title: "{57} × {83} mod {11B} == {C1}", detail: "Pending: confirm algebraic round-trip identity" },
              ],
            },
          },
          {
            title: "Stage 3 · Live Algebraic Self-Verification",
            diffSummary: "Stage 2 completed (Q = {57}); Stage 3 verified {57} × {83} mod {11B} == {C1}.",
            formula: "VERIFY_DIVISION:  ({C1} / {83}) × {83} = {57} × {83} mod {11B} = {C1}  ✓",
            explanation: "Finally, multiplying our quotient {57} by the divisor {83} modulo {11B} recovers the original dividend {C1} (matching Lesson 5!), earning the green Mathematically verified badge.",
            visual: {
              type: "pipeline",
              activeStage: 3,
              stages: [
                { stage: "Stage 1 · Inverse", title: "{83}⁻¹ = {80}", detail: "Verified: {83} × {80} mod {11B} = {01}" },
                { stage: "Stage 2 · Multiply", title: "{C1} × {80} = {57}", detail: "Quotient Q(x) = x^6 + x^4 + x^2 + x + 1 ({57})" },
                { stage: "Stage 3 · Verified ✓", title: "{57} × {83} mod {11B} = {C1}", detail: "Mathematically verified · (A(x)/B(x)) * B(x) mod m(x) = A(x)" },
              ],
            },
          },
        ],
      },
      {
        id: "7.3",
        title: "7.3 · Summary & Calculator Handoff",
        summary: "Test two-stage field division across GF(2^8) through GF(2^571) in the live Calculator.",
        quiz: {
          question: "What happens if you attempt to divide A(x) = {57} by B(x) = {00} or B(x) = {11B} in GF(2^8)?",
          options: [
            { text: "Stage 1 (Extended Euclid) terminates at Step 0 with B3(x) = 0 and A3(x) = gcd(m, 0) = {11B}, returning an HTTP 400 zero-divisor alert.", correct: true },
            { text: "The calculator returns {00} without running Extended Euclid.", correct: false },
          ],
        },
        steps: [
          {
            title: "Ready to explore division in GF(2^163) and GF(2^571)",
            formula: "Time Complexity:  O(m^2) bit operations  (Stage 1 EEA + Stage 2 Shift-and-XOR)",
            explanation: "Click the button below to load {C1} ÷ {83} = {57} directly into the Calculator and inspect both Stage 1 (Table 4.7) and Stage 2 (Shift-and-XOR) traces.",
            visual: {
              type: "cards",
              items: [
                { badge: "Stage 1 Trace", title: "Extended Euclid Table 4.7", detail: "Inspect every quotient Q(x) and triple update (A1, A2, A3), (B1, B2, B3)" },
                { badge: "Stage 2 Trace", title: "Shift-and-XOR Tables 1 & 2", detail: "Inspect every shifted partial product of A(x) × B(x)⁻¹" },
              ],
            },
          },
        ],
      },
    ],
  },
];
