"""Chromium Playwright end-to-end acceptance tests for the Finite Field Lab workbench."""
from __future__ import annotations

from pathlib import Path

import pytest

DEMO_OPERANDS = Path(__file__).resolve().parents[2] / "data" / "demo-operands.json"


def test_browser_workflow(live_url: str) -> None:
    """Verify core calculator flow, presets, Step view default, share links, exports, alerts, upload, and mobile tour."""
    playwright = pytest.importorskip("playwright.sync_api")
    with playwright.sync_playwright() as runner:
        browser = runner.chromium.launch()
        context = browser.new_context(
            permissions=["clipboard-read", "clipboard-write"], accept_downloads=True
        )
        page = context.new_page()
        page_errors = []
        page.on("pageerror", lambda err: page_errors.append(str(err)))
        page.goto(live_url)
        check = playwright.expect
        check(page.locator("#field")).to_have_value("163")
        check(page.locator("#hero-degree")).to_have_text("163")
        check(page.locator("#poly-a")).to_have_value("")
        check(page.locator("#poly-b")).to_have_value("")
        check(page.locator("#result")).to_be_hidden()
        check(page.locator("#trace-panel")).to_be_hidden()

        # Chapter 4 preset in GF(2^8) defaults to Step view cleanly (Step 1 of 8).
        page.locator("#presets").get_by_role("button", name="Chapter 4", exact=False).click()
        check(page.locator("#result-value")).to_have_text("C1")
        check(page.locator("#hero-degree")).to_have_text("8")
        check(page.get_by_role("button", name="Step view", exact=True)).to_have_attribute("aria-pressed", "true")
        check(page.locator(".trace-progress")).to_have_text("Step 1 of 8")
        page.get_by_role("button", name="Next step", exact=True).click()
        check(page.locator(".trace-progress")).to_have_text("Step 2 of 8")
        check(page.get_by_role("region", name="Previous trace step")).to_be_visible()

        # Classic table shows Table 1, Table 2, and the color legend.
        page.get_by_role("button", name="Classic table", exact=True).click()
        check(page.locator(".table-color-legend")).to_be_visible()
        check(page.get_by_role("heading", name="Table 1", exact=False)).to_be_visible()
        check(page.get_by_role("heading", name="Table 2", exact=False)).to_be_visible()

        page.get_by_role("button", name="Binary", exact=True).click()
        check(page.locator("#poly-a")).to_have_value("01010111")

        page.get_by_role("button", name="Share link", exact=True).click()
        share = page.evaluate("navigator.clipboard.readText()")
        assert "base=binary&poly_a=57&poly_b=83" in share
        assert share.endswith("#calculator")
        restored = context.new_page()
        restored.goto(share)
        check(restored.locator("#result-value")).to_have_text("11000001")
        check(restored.locator("#poly-a")).to_have_value("01010111")
        restored.close()

        page.locator('input[value="add"]').check(force=True)
        page.locator("#calculate").click()
        check(page.locator("#result-value")).to_have_text("11010100")
        check(page.get_by_role("region", name="Current trace step")).to_contain_text("Bitwise XOR")

        page.locator('input[value="modulo"]').check(force=True)
        page.locator("#poly-a").fill("100000000")
        page.locator("#calculate").click()
        check(page.locator("#result-value")).to_have_text("00011011")
        check(page.get_by_role("region", name="Current trace step")).to_contain_text("Shifted modulus · m(x) << 0")

        page.locator("#tutorial-open").click()
        check(page.locator("#tour-title")).to_have_text("Choose a field")
        check(page.locator(".setting.tour-highlight")).to_be_visible()
        page.locator("#tour-next").click()
        check(page.locator(".operands.tour-highlight")).to_be_visible()
        page.locator("#tour-prev").click()
        check(page.locator("#tour-prev")).to_be_disabled()
        page.locator("#concepts-open").click()
        check(page.locator("#tutorial")).to_be_visible()
        for _ in range(3):
            page.locator("#slide-next").click()
        page.locator("#tutorial-slide").get_by_role("button", name="Chapter 5", exact=False).click()
        page.keyboard.press("Escape")
        check(page.locator("#page-tour")).to_be_hidden()
        check(page.locator("#result-value")).to_have_text("10001010")
        check(page.locator("#poly-b")).to_be_disabled()
        page.get_by_label("Euclid cell notation").select_option("algebraic")
        page.get_by_role("button", name="Classic table", exact=True).click()
        check(page.get_by_role("heading", name="Table 4.7", exact=False)).to_be_visible()

        for fmt in ("md", "json"):
            page.locator("#export-format").select_option(fmt)
            with page.expect_download() as download:
                page.locator("#export").click()
            assert download.value.suggested_filename.endswith("." + fmt)

        # Top-center floating error alert on zero-inverse HTTP 400.
        page.locator("#poly-a").fill("100011011")
        page.locator("#calculate").click()
        check(page.locator("#error-popup")).to_be_visible()
        check(page.get_by_role("alert")).to_contain_text("Zero element")
        page.locator("#error-popup-trace").click()
        check(page.locator("#error-popup")).to_be_hidden()
        check(page.get_by_text("A3(x) gives the gcd", exact=False)).to_be_visible()

        page.locator("#file").set_input_files(DEMO_OPERANDS)
        check(page.locator("#notice")).to_have_text("4 pairs loaded.")
        check(page.locator('#pairs option[value="1"]')).to_have_text("Pair 2 · A=02, B=87 (hex)")
        page.locator("#pairs").select_option("1")
        check(page.locator("#poly-a")).to_have_value("00000010")
        page.locator('input[value="multiply"]').check(force=True)
        page.locator("#calculate").click()
        check(page.locator("#result-value")).to_have_text("00010101")

        page.locator("#file").set_input_files(
            {"name": "broken.json", "mimeType": "application/json", "buffer": b"{"}
        )
        check(page.locator("#error-popup")).to_be_visible()
        check(page.get_by_role("alert")).to_contain_text("parse error")
        page.locator("#error-popup-ok").click()
        check(page.locator("#error-popup")).to_be_hidden()
        page.locator("#random").click()
        check(page.locator("#notice")).to_have_text("Random operands generated.")

        page.set_viewport_size({"width": 390, "height": 840})
        page.locator("#field").select_option("571")
        page.locator('input[value="divide"]').check(force=True)
        page.locator("#poly-a").fill("1" + "0" * 569 + "1")
        page.locator("#poly-b").fill("10")
        page.locator("#calculate").click()
        check(page.locator("#verification")).to_contain_text("Mathematically verified")
        page.locator("#tutorial-open").click()
        for expected_target in (
            ".operands",
            ".calculator .section-head",
            ".operations",
            ".action",
            ".examples",
            "#result",
            "#trace-panel",
            "#trace-body",
            "#presets",
            "#share",
        ):
            page.locator("#tour-next").click()
            check(page.locator(expected_target + ".tour-highlight")).to_be_visible()
        page.get_by_role("button", name="Done", exact=True).click()
        check(page.locator("#page-tour")).to_be_hidden()
        check(page.locator(".tour-highlight")).to_have_count(0)
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        assert not page_errors
        browser.close()


def test_explorations_and_applications_in_browser(live_url: str) -> None:
    """Verify Modulus explorer polish, Applications tab (XTS-AES GF(2^128) & Binary ECC B-163), and Compare multiplication."""
    playwright = pytest.importorskip("playwright.sync_api")
    with playwright.sync_playwright() as runner:
        browser = runner.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page_errors = []
        console_errors = []
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        page.goto(live_url)
        check = playwright.expect
        check(page.locator("#poly-a")).to_have_value("")
        check(page.locator("#result")).to_be_hidden()

        # Verify top navigation has exactly 5 tabs and no AES S-box tab.
        nav_links = page.locator(".lab-nav a")
        check(nav_links).to_have_count(5)
        check(page.locator(".lab-nav")).not_to_contain_text("AES S-box")
        check(page.locator(".lab-nav")).to_contain_text("Applications")

        # 1. Modulus explorer: empty initial state, Random polynomial, ASCII x^k input, non-numeric placeholder, plain-English GCD note.
        page.get_by_role("link", name="Modulus explorer").click()
        check(page.locator("#custom-modulus")).to_have_attribute("placeholder", "Enter modulus m(x)")
        check(page.locator("#custom-modulus")).to_have_value("")
        check(page.locator("#modulus-result")).to_be_hidden()
        page.locator("#modulus-random").click()
        check(page.locator("#modulus-result")).to_be_visible()
        page.locator("#custom-modulus").fill("x⁸ + x⁴ + x³ + x + 1")
        check(page.locator("#custom-modulus")).to_have_value("x^8 + x^4 + x^3 + x + 1")
        page.get_by_role("button", name="Check irreducibility").click()
        check(page.locator("#modulus-status")).to_have_text("Irreducible · degree 8")
        page.get_by_role("button", name="Try reducible", exact=False).click()
        check(page.locator("#custom-modulus")).to_have_value("x^8 + 1")
        check(page.locator("#modulus-status")).to_have_text("Reducible · degree 8")
        check(page.locator("#modulus-witness")).to_contain_text("leaves remainder 0")
        page.get_by_text("Show the polynomial GCD checks").click()
        check(page.locator(".modulus-gcd-explain")).to_contain_text("irreducible factor of degree i")
        check(page.get_by_role("heading", name="GCD checkpoints")).to_be_visible()
        page.get_by_role("button", name="Use calculator modulus").click()
        check(page.locator("#modulus-status")).to_have_text("Irreducible · degree 163")

        # 2. Applications tab: empty initial states, Random buttons, XTS-AES + Binary ECC + GCM/GHASH.
        page.get_by_role("link", name="Applications", exact=True).click()
        check(page.get_by_role("heading", name="Cryptographic applications")).to_be_visible()
        check(page.locator("#app-hero-field")).to_have_text("GF(2128)")
        check(page.locator("#app-hero-std")).to_have_text("IEEE 1619")
        check(page.locator("#xts-t0")).to_have_attribute("placeholder", "Enter 128-bit tweak T0 (hex)")
        check(page.locator("#xts-t0")).to_have_value("")
        check(page.locator("#xts-steps")).to_have_value("")
        check(page.locator("#xts-results")).to_be_hidden()
        # Verify single-line Applications labels and matched input heights.
        for lbl_sel in ("#xts-form .field-label",):
            for box in page.locator(lbl_sel).evaluate_all("els => els.map(e => e.getBoundingClientRect())"):
                assert box["height"] < 30, f"Wrapped label detected: {box}"
        xts_t0_box = page.locator("#xts-t0").bounding_box()
        xts_steps_box = page.locator("#xts-steps").bounding_box()
        assert xts_t0_box and xts_steps_box and abs(xts_t0_box["height"] - xts_steps_box["height"]) <= 2
        page.locator("#xts-t0").fill("50000000000000000000000000000001")
        page.locator("#xts-steps").fill("6")
        page.locator("#xts-form button[type=submit]").click()
        check(page.locator("#xts-results")).to_be_visible()
        check(page.locator("#xts-chain .xts-block-row")).to_have_count(7)
        check(page.locator("#xts-chain")).to_contain_text("XOR 0x87")
        page.locator("#xts-step-next").click()
        check(page.locator("#xts-chain .xts-block-row")).to_have_count(8)
        page.locator("#xts-random").click()
        check(page.locator("#xts-chain .xts-block-row")).to_have_count(8)
        page.locator("#xts-reset").click()
        check(page.locator("#xts-t0")).to_have_value("")
        check(page.locator("#xts-results")).to_be_hidden()

        # Switch to Binary ECC sub-tab: empty initial state, Randomize keys, NIST B-163 + Polynomial ECC slide notation.
        page.locator("#app-tab-ecc").click()
        check(page.locator("#app-hero-field")).to_have_text("GF(2163)")
        check(page.locator("#app-hero-std")).to_have_text("NIST B-163")
        check(page.locator("#ecc-na")).to_have_value("")
        check(page.locator("#ecc-nb")).to_have_value("")
        check(page.locator("#ecc-results")).to_be_hidden()
        for box in page.locator("#ecc-form .field-label").evaluate_all("els => els.map(e => e.getBoundingClientRect())"):
            assert box["height"] < 30, f"Wrapped ECC label detected: {box}"
        ecc_curve_box = page.locator("#ecc-curve").bounding_box()
        ecc_na_box = page.locator("#ecc-na").bounding_box()
        ecc_nb_box = page.locator("#ecc-nb").bounding_box()
        assert ecc_curve_box and ecc_na_box and ecc_nb_box
        assert abs(ecc_curve_box["y"] - ecc_na_box["y"]) <= 2
        assert abs(ecc_na_box["y"] - ecc_nb_box["y"]) <= 2
        assert abs(ecc_curve_box["height"] - ecc_na_box["height"]) <= 2
        page.locator("#ecc-random").click()
        check(page.locator("#ecc-results")).to_be_visible()
        page.locator("#ecc-switch-b163").click()
        check(page.locator("#ecc-curve-badge")).to_contain_text("NIST B-163")
        # Verify Polynomial ECC slide notation (Xp, Yp, s, Xr, Yr) on Binary ECC sub-tab.
        check(page.locator("#ecc-ops-grid")).to_contain_text("Point Doubling")
        check(page.locator("#ecc-ops-grid")).to_contain_text("Point Addition")
        check(page.locator("#ecc-ops-grid")).to_contain_text("s = Xp + Yp / Xp")
        check(page.locator("#ecc-ops-grid")).to_contain_text("Xr = s2 + s + a")
        check(page.locator("#ecc-ops-grid")).to_contain_text("Yr = Xp2 + (s + 1) * Xr")
        check(page.locator("#ecc-ops-grid")).to_contain_text("s = (Yp - Yq) / (Xp + Xq)")
        check(page.locator("#ecc-ops-grid")).to_contain_text("Xr = s2 + s + Xp + Xq + a")
        check(page.locator("#ecc-ops-grid")).to_contain_text("Yr = s(Xp + Xr) + Xr + Yp")
        check(page.locator("#ecc-ops-grid")).to_contain_text("÷ / EEA")
        check(page.locator("#ecc-ops-grid")).to_contain_text("× Shift-and-XOR")
        check(page.locator("#ecc-ops-grid .ecc-verified-badge").first).to_contain_text("Verified on curve")
        check(page.locator("#ecc-ecdh-card")).to_contain_text("Shared secret matches")

        # Click a 163-bit coordinate to open the Full Value Inspector Popup.
        coord_btn = page.locator("#ecc-results button.trace-inspectable").first
        coord_btn.click()
        inspector_popup = page.locator("#inspector-popup")
        check(inspector_popup).to_be_visible()
        check(inspector_popup).to_contain_text("Hexadecimal")
        check(inspector_popup).to_contain_text("Binary")
        check(inspector_popup).to_contain_text("Polynomial")
        page.locator("#inspector-popup-close-btn").click()
        check(inspector_popup).to_be_hidden()

        # Switch to Teaching Curve GF(2^4) and verify 2G = (A, B) and 3G = (F, 7).
        page.locator("#ecc-switch-teaching").click()
        check(page.locator("#ecc-curve-badge")).to_contain_text("Teaching Curve")
        check(page.locator("#ecc-ops-grid")).to_contain_text("{A}")
        check(page.locator("#ecc-ops-grid")).to_contain_text("{B}")
        check(page.locator("#ecc-ops-grid")).to_contain_text("{F}")

        # Switch to third sub-tab: GCM · GHASH (GF(2^128)) starts empty, Randomize populates & computes tag.
        page.locator("#app-tab-ghash").click()
        check(page.locator("#app-hero-field")).to_have_text("GF(2128)")
        check(page.locator("#app-hero-std")).to_have_text("NIST SP 800-38D")
        check(page.locator("#ghash-h")).to_have_attribute("placeholder", "Enter 128-bit hash key H (hex)")
        check(page.locator("#ghash-h")).to_have_value("")
        check(page.locator("#ghash-blocks")).to_have_value("")
        check(page.locator("#ghash-results")).to_be_hidden()
        page.locator("#ghash-random").click()
        check(page.locator("#ghash-results")).to_be_visible()
        check(page.locator("#ghash-steps tbody tr")).to_have_count(3)
        page.locator("#ghash-tag-display button.trace-inspectable").click()
        check(inspector_popup).to_be_visible()
        check(inspector_popup).to_contain_text("Hexadecimal")
        check(inspector_popup).to_contain_text("Binary")
        check(inspector_popup).to_contain_text("Polynomial")
        page.locator("#inspector-popup-close-btn").click()
        check(inspector_popup).to_be_hidden()
        page.locator("#ghash-reset").click()
        check(page.locator("#ghash-h")).to_have_value("")
        check(page.locator("#ghash-results")).to_be_hidden()

        # 3. Compare multiplication & benchmark (starts empty, has Random operands + Compare methods).
        page.get_by_role("link", name="Compare multiplication").click()
        check(page.locator("#compare-a")).to_have_value("")
        check(page.locator("#compare-b")).to_have_value("")
        check(page.locator("#compare-results")).to_be_hidden()
        page.locator("#compare-random").click()
        check(page.locator("#compare-results")).to_be_visible()
        page.locator("#compare-degree").select_option("8")
        page.locator("#compare-a").fill("57")
        page.locator("#compare-b").fill("83")
        page.get_by_role("button", name="Compare methods").click()
        check(page.locator("#compare-status")).to_have_text("Both methods agree · GF(28)")
        check(page.locator("#compare-status sup")).to_have_text("8")
        check(page.locator("#shift-method-result")).to_have_text("C1 (hex)")
        check(page.locator("#compare-division-body")).to_contain_text("Leading-term cancellations")
        page.get_by_role("button", name="Run benchmark").click()
        benchmark = page.get_by_role("region", name="Median time per multiplication")
        check(benchmark.get_by_role("row", name="163 bits", exact=False)).to_contain_text("Match")
        check(benchmark.get_by_role("row", name="571 bits", exact=False)).to_contain_text("Match")

        page.set_viewport_size({"width": 390, "height": 840})
        page.locator("#compare-degree").select_option("571")
        page.locator("#compare-a").fill("4" + "0" * 141 + "1")
        page.locator("#compare-b").fill("1")
        page.get_by_role("button", name="Compare methods").click()
        check(page.locator("#compare-status")).to_have_text("Both methods agree · GF(2571)")
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        page.get_by_role("link", name="Applications", exact=True).click()
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        page.get_by_role("link", name="Calculator", exact=True).click()
        check(page.locator("#field")).to_have_value("163")
        assert not console_errors
        assert not page_errors
        browser.close()


@pytest.mark.parametrize(
    "view,first_target,trigger_btn,result_sel,remaining",
    [
        ("modulus", "#modulus-form", "#modulus-example", "#modulus-result", (".witness", "#modulus-result details")),
        ("applications", "#applications-subtabs", "#xts-random", "#xts-results", ()),
        (
            "compare",
            "#compare-form",
            "#compare-random",
            "#compare-results",
            ("#compare-shift-body", "#compare-division-body", "#compare-benchmark"),
        ),
    ],
)
def test_experiment_tour_tracks_the_active_view_and_result(
    live_url: str, view: str, first_target: str, trigger_btn: str, result_sel: str, remaining: tuple[str, ...]
) -> None:
    """Verify Tutorial tour spotlight tracks controls and live results across Modulus, Applications, and Compare."""
    playwright = pytest.importorskip("playwright.sync_api")
    check = playwright.expect
    viewport = {"width": 390, "height": 840} if view == "compare" else {"width": 1280, "height": 900}
    with playwright.sync_playwright() as runner:
        browser = runner.chromium.launch()
        page = browser.new_page(viewport=viewport)
        page.goto(f"{live_url}#{view}")
        check(page.locator(first_target)).to_be_visible()
        tutorial = page.get_by_role("button", name="Tutorial tour", exact=True)
        check(tutorial).to_be_visible(timeout=2000)
        tutorial.click()
        check(page.locator(first_target + ".tour-highlight")).to_be_in_viewport()

        next_step = page.locator("#tour-next")
        if view == "applications":
            next_step.click()
            check(page.locator("#xts-form.tour-highlight")).to_be_in_viewport()
            page.locator(trigger_btn).click()
            check(page.locator(result_sel)).to_be_visible()
            next_step.click()
            check(page.locator(result_sel + ".tour-highlight")).to_be_in_viewport()
        else:
            next_step.click()
            check(page.locator(first_target + " button[type=submit].tour-highlight")).to_be_visible()
            page.locator(trigger_btn).click()
            check(page.locator(result_sel + ".tour-highlight")).to_be_in_viewport()
            for target in remaining:
                next_step.click()
                check(page.locator(target + ".tour-highlight")).to_be_in_viewport()

        check(next_step).to_have_text("Done")
        next_step.click()
        check(tutorial).to_be_focused()
        check(page.locator(result_sel)).to_be_visible()
        check(page.locator(".tour-highlight")).to_have_count(0)
        tutorial.click()
        page.get_by_role("link", name="Calculator", exact=True).click()
        check(page.locator("#page-tour")).to_be_hidden()
        browser.close()


def test_calculator_tour_guides_full_result_popups_and_comparison(live_url: str) -> None:
    """Verify updated Calculator tour guides untruncated results, Full-Value/Breakdown popups, and comparison."""
    playwright = pytest.importorskip("playwright.sync_api")
    check = playwright.expect
    with playwright.sync_playwright() as runner:
        browser = runner.chromium.launch()
        page = browser.new_page(viewport={"width": 390, "height": 840})
        page.goto(live_url)
        page.locator("#poly-a").fill("57")
        page.locator("#poly-b").fill("83")
        page.locator("#calculate").click()
        full_163 = format(0x2B79, "041X")
        check(page.locator("#result-value")).to_have_text(full_163)
        page.get_by_role("button", name="Tutorial tour", exact=True).click()
        next_step = page.locator("#tour-next")
        for _ in range(6):
            next_step.click()
        description = page.locator("#tour-description")
        check(description).to_contain_text("untruncated", timeout=2500)
        check(description).to_contain_text("Back to inputs")

        next_step.click()
        check(description).to_contain_text("Classic table")
        next_step.click()
        check(page.locator("#trace-body.tour-highlight")).to_be_visible()
        check(description).to_contain_text("Full Value Inspector")

        next_step.click()
        shortcut = page.locator("#compare-product.tour-highlight")
        check(shortcut).to_be_visible()
        shortcut.click()
        check(page.locator("#page-tour")).to_be_hidden()
        check(page.locator("#compare-status")).to_have_text("Both methods agree · GF(2163)")
        browser.close()


def test_linked_multiplier_bit_and_classic_table_color_legend(live_url: str) -> None:
    """Verify Step view multiplier-bit selection (bits 7 and 6) and Classic table color legend on Chapter 4."""
    playwright = pytest.importorskip("playwright.sync_api")
    check = playwright.expect
    with playwright.sync_playwright() as runner:
        browser = runner.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(live_url)
        page.locator("#presets").get_by_role("button", name="Chapter 4", exact=False).click()
        check(page.locator("#result-value")).to_have_text("C1")
        trace = page.locator("#trace-panel")
        bit7 = trace.get_by_role("button", name="Multiplier bit 7", exact=True)
        check(bit7).to_be_visible(timeout=2500)
        check(bit7).to_have_accessible_description("Value 1", timeout=2500)
        bit7.click()
        check(bit7).to_have_attribute("aria-pressed", "true", timeout=4000)
        curr = trace.get_by_role("region", name="Current trace step")
        check(curr).to_contain_text("{F9} ⊕ {38} = {C1}")
        check(curr.locator(".mul-sum-block .mul-step-result-val")).to_have_text("{C1}")

        bit6 = trace.get_by_role("button", name="Multiplier bit 6", exact=True)
        bit6.click()
        check(bit6).to_have_attribute("aria-pressed", "true", timeout=4000)
        check(curr).to_contain_text("Skip because b6 = 0")
        check(curr.locator(".mul-sum-block .mul-step-result-val")).to_have_text("{F9}")

        trace.get_by_role("button", name="Classic table", exact=True).click()
        check(trace.locator(".table-color-legend")).to_be_visible()
        check(trace.get_by_role("region", name="Table 1", exact=False)).to_be_visible()
        check(trace.get_by_role("region", name="Table 2", exact=False)).to_be_visible()
        browser.close()


def test_full_untruncated_result_and_copy_on_large_fields(live_url: str) -> None:
    """Verify full untruncated Hex/Binary/Polynomial Result values (no ellipsis) and mobile zero overflow."""
    playwright = pytest.importorskip("playwright.sync_api")
    check = playwright.expect
    with playwright.sync_playwright() as runner:
        browser = runner.chromium.launch()
        context = browser.new_context(
            viewport={"width": 390, "height": 840},
            permissions=["clipboard-read", "clipboard-write"],
        )
        page = context.new_page()
        page.goto(live_url)
        check(page.locator("#field")).to_have_value("163")
        page.locator("#poly-a").fill("57")
        page.locator("#poly-b").fill("83")
        page.locator("#calculate").click()
        check(page.locator("#result-title")).to_be_focused(timeout=2500)
        check(page.locator("#result-value")).to_be_in_viewport()

        full_163 = format(0x2B79, "041X")
        check(page.locator("#result-value")).to_have_text(full_163)
        check(page.locator("#result-expanded")).to_have_count(0)
        check(page.locator("#metrics")).to_contain_text("ms")
        check(page.locator("#metrics")).to_contain_text("bits")
        check(page.locator("#metrics")).to_contain_text("Hamming weight")

        page.get_by_role("button", name="Copy result", exact=True).click()
        assert page.evaluate("navigator.clipboard.readText()") == full_163
        page.get_by_role("button", name="Back to inputs", exact=True).click()
        check(page.locator("#poly-a")).to_be_focused()

        full_571 = "4" + "0" * 141 + "1"
        page.locator("#field").select_option("571")
        page.locator("#poly-a").fill(full_571)
        page.locator("#poly-b").fill("1")
        page.locator("#calculate").click()
        check(page.locator("#result-value")).to_have_text(full_571)
        check(page.locator("#result-value")).not_to_contain_text("…")
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        browser.close()


def test_mobile_trace_step_view_and_modulo_reduction(live_url: str) -> None:
    """Verify mobile Step view, stacked Previous -> Current comparison, and untruncated Modulo Reduction m(x) << k."""
    playwright = pytest.importorskip("playwright.sync_api")
    check = playwright.expect
    with playwright.sync_playwright() as runner:
        browser = runner.chromium.launch()
        page = browser.new_page(viewport={"width": 390, "height": 840})
        page.goto(live_url)
        page.locator("#presets").get_by_role("button", name="Chapter 4", exact=False).click()
        trace = page.locator("#trace-panel")
        card = trace.get_by_role("region", name="Current trace step")
        check(card).to_be_visible(timeout=2500)
        check(card).to_contain_text("Multiplier bit b0")
        check(card).to_contain_text("Shifted value")
        trace.get_by_role("button", name="Next step", exact=True).click()
        check(trace.get_by_role("region", name="Previous trace step")).to_be_visible()
        check(card).to_contain_text("Multiplier bit b1")
        trace.get_by_role("button", name="Multiplier bit 6", exact=True).click()
        check(trace.get_by_role("button", name="Multiplier bit 6", exact=True)).to_have_attribute("aria-pressed", "true", timeout=4000)
        trace.get_by_role("button", name="Next step", exact=True).click()
        check(card).to_contain_text("{F9} ⊕ {38} = {C1}")
        check(trace.get_by_role("region", name="Table 1", exact=False)).to_be_hidden()
        trace.get_by_role("button", name="Classic table", exact=True).click()
        check(trace.get_by_role("region", name="Table 1", exact=False)).to_be_visible()

        page.locator('label:has(input[value="modulo"])').click()
        check(page.locator('input[value="modulo"]')).to_be_checked()
        page.locator("#poly-a").fill("100")
        page.locator("#calculate").click()
        check(card).to_contain_text("Shifted modulus · m(x) << 0")
        check(card).to_contain_text("11B")
        check(card).to_contain_text("1B")
        check(card.locator(".diff-banner")).to_have_count(0)
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        browser.close()


def test_compare_multiplication_methods_transfers_the_exact_calculation(live_url: str) -> None:
    """Verify the renamed Compare multiplication methods button + helper note transfer exact operands to #compare."""
    playwright = pytest.importorskip("playwright.sync_api")
    check = playwright.expect
    with playwright.sync_playwright() as runner:
        browser = runner.chromium.launch()
        page = browser.new_page()
        page.goto(live_url)
        page.locator("#field").select_option("3")
        page.get_by_role("button", name="Binary", exact=True).click()
        page.locator("#poly-a").fill("10110")
        page.locator("#poly-b").fill("1011")
        page.locator("#calculate").click()
        shortcut = page.get_by_role("button", name="Compare multiplication methods", exact=True)
        check(shortcut).to_be_visible(timeout=2500)
        check(page.locator("#compare-product-hint")).to_be_visible()
        shortcut.click()
        check(page.locator("#compare-degree")).to_have_value("3")
        check(page.locator("#compare-a")).to_have_value("16")
        check(page.locator("#compare-b")).to_have_value("B")
        check(page.locator("#compare-status")).to_have_text("Both methods agree · GF(23)")
        check(page.locator("#shift-method-result")).to_have_text("6 (hex)")

        page.get_by_role("link", name="Calculator", exact=True).click()
        check(page.locator("#poly-a")).to_have_value("10110")
        page.locator('label:has(input[value="add"])').click()
        check(page.locator('input[value="add"]')).to_be_checked()
        page.locator("#calculate").click()
        check(page.locator("#result-value")).to_be_visible()
        check(shortcut).to_be_hidden()
        check(page.locator("#compare-product-hint")).to_be_hidden()
        browser.close()


def test_milestone6_ux_simplification_popups_pagination_and_playback_locking(live_url: str) -> None:
    """Verify Wave 4 UX simplification: Step view default, Previous -> Current, 4-step grid pagination, playback locking, EEA Q/T1/T2/T3 & Shift-XOR popups, Full-Value Inspector, auto-uppercase Hex, Unicode superscript Polynomials, and top-center error alert."""
    playwright = pytest.importorskip("playwright.sync_api")
    check = playwright.expect
    repo_root = Path(__file__).resolve().parents[2]
    frontend_and_data = sorted(
        list((repo_root / "frontend").glob("*")) + [repo_root / "data" / "tutorial_slides.json"]
    )
    for asset in frontend_and_data:
        if asset.is_file() and asset.suffix.lower() in {".html", ".css", ".js", ".json"}:
            text = asset.read_text(encoding="utf-8")
            assert "\u2014" not in text, f"Found em-dash in {asset}"
            assert "\u2013" not in text, f"Found en-dash in {asset}"

    with playwright.sync_playwright() as runner:
        browser = runner.chromium.launch()
        context = browser.new_context(
            permissions=["clipboard-read", "clipboard-write"],
            accept_downloads=True,
            viewport={"width": 1280, "height": 900},
        )
        page = context.new_page()
        page_errors = []
        console_errors = []
        page.on("pageerror", lambda err: page_errors.append(str(err)))
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        page.goto(live_url)

        # 0. Verify custom GF(2^m) brand badge image, favicon, and header subtitle with <sup>m</sup>.
        badge_img = page.locator(".brand-badge-img")
        check(badge_img).to_be_visible()
        assert page.evaluate("document.querySelector('.brand-badge-img').complete && document.querySelector('.brand-badge-img').naturalWidth > 0")
        check(page.locator('link[rel="icon"]')).to_have_attribute("href", "/workbench/gf2m-badge.png")
        check(page.locator(".brand small")).to_have_text("GF(2m) Polynomial Arithmetic · EECE 455")
        check(page.locator(".brand small sup")).to_have_text("m")

        # 1. Non-numeric placeholders, auto-uppercase Hex, clean ASCII x^k Polynomial inputs, and strictly the two non-selected notations below.
        check(page.locator("#poly-a")).to_have_attribute("placeholder", "Enter A(x)")
        check(page.locator("#poly-b")).to_have_attribute("placeholder", "Enter B(x)")
        check(page.locator("#poly-a")).to_have_value("")
        check(page.locator("#a-preview dt")).to_have_text(["Binary", "Polynomial"])
        check(page.locator("#a-preview dd")).to_have_text(["-", "-"])

        page.locator("#field").select_option("8")
        page.locator("#poly-a").fill("5a")
        check(page.locator("#poly-a")).to_have_value("5A")
        check(page.locator("#a-preview dt")).to_have_text(["Binary", "Polynomial"])
        check(page.locator("#a-preview")).to_contain_text("01011010")
        check(page.locator("#a-preview")).to_contain_text("x6 + x4 + x3 + x")

        page.get_by_role("button", name="Binary", exact=True).click()
        check(page.locator("#a-preview dt")).to_have_text(["Hexadecimal", "Polynomial"])
        check(page.locator("#a-preview")).to_contain_text("5A")

        page.get_by_role("button", name="Polynomial", exact=True).click()
        check(page.locator("#poly-a")).to_have_value("x^6 + x^4 + x^3 + x")
        check(page.locator("#a-preview dt")).to_have_text(["Hexadecimal", "Binary"])
        check(page.locator("#a-preview")).to_contain_text("5A")
        check(page.locator("#a-preview")).to_contain_text("01011010")
        # Pasted Unicode superscripts normalize to clean ASCII x^k inside inputs.
        page.locator("#poly-b").fill("x⁷ + x + 1")
        check(page.locator("#poly-b")).to_have_value("x^7 + x + 1")
        page.locator("#calculate").click()
        check(page.locator("#result-value")).to_be_visible()
        check(page.locator("#result-alternatives dt")).to_have_text(["Hexadecimal", "Binary"])

        # 2. Removed controls (Expand full view, Compare prev -> curr, #trace-fullscreen) are absent.
        trace = page.locator("#trace-panel")
        check(trace.get_by_role("button", name="Expand full view", exact=True)).to_have_count(0)
        check(trace.get_by_role("button", name="Compare prev → curr", exact=True)).to_have_count(0)
        check(page.locator("#trace-fullscreen")).to_have_count(0)

        # 3. Shift-and-XOR in GF(2^4): default Step view, steps BEFORE answer, Shift & XOR popup, no blue diff-banner.
        page.get_by_role("button", name="Hex", exact=True).click()
        page.locator("#field").select_option("4")
        page.locator('input[value="multiply"]').check(force=True)
        page.locator("#poly-a").fill("e")
        check(page.locator("#poly-a")).to_have_value("E")
        page.locator("#poly-b").fill("d")
        check(page.locator("#poly-b")).to_have_value("D")
        page.locator("#calculate").click()
        check(page.locator("#result-value")).to_have_text("9")
        check(trace.get_by_role("button", name="Step view", exact=True)).to_have_attribute("aria-pressed", "true")
        # Step 0 shows single card cleanly (no Previous pane).
        check(trace.get_by_role("region", name="Previous trace step")).to_have_count(0)
        curr_card = trace.get_by_role("region", name="Current trace step")
        check(curr_card.locator(".diff-banner")).to_have_count(0)
        check(curr_card).to_contain_text("Start with A(x)")

        # Step 1 shows side-by-side Previous -> Current automatically, with calculation steps above bold Shifted value.
        trace.get_by_role("button", name="Next step", exact=True).click()
        check(trace.get_by_role("region", name="Previous trace step")).to_be_visible()
        shift_block = curr_card.locator(".mul-shift-block")
        breakdown_box = shift_block.locator(".reduction-breakdown.is-overflow")
        result_box = shift_block.locator(".mul-step-result")
        check(breakdown_box).to_be_visible()
        check(result_box).to_contain_text("{5}")
        # Verify steps appear ABOVE bold answer vertically.
        assert breakdown_box.bounding_box()["y"] < result_box.bounding_box()["y"]

        # Open Shift & XOR illustration popup from Sub-Block 1.
        shift_block.get_by_role("button", name="Show Shift & XOR illustration", exact=True).click()
        deriv_popup = page.locator("#derivation-popup")
        check(deriv_popup).to_be_visible()
        check(deriv_popup).to_contain_text("Shift & XOR Illustration")
        check(deriv_popup).to_contain_text("11100")
        check(deriv_popup).to_contain_text("11001")
        page.keyboard.press("Escape")
        check(deriv_popup).to_be_hidden()

        # 4. Extended Euclid in GF(2^163): 4 breakdown buttons (Q, T1, T2, T3), Full-Value Inspector, 4-step grid pagination, playback locking.
        page.locator("#field").select_option("163")
        page.locator('input[value="inverse"]').check(force=True)
        page.locator("#poly-a").fill("57")
        page.locator("#calculate").click()
        check(page.locator("#verification")).to_contain_text("Mathematically verified")

        # Step 0 has all 4 buttons disabled + muted note.
        check(curr_card.locator(".euclid-breakdown-bar button")).to_have_count(4)
        for btn_idx in range(4):
            check(curr_card.locator(".euclid-breakdown-bar button").nth(btn_idx)).to_be_disabled()
        check(curr_card.locator(".euclid-breakdown-note")).to_have_text("Available from Step 1 onward")

        # Step 1 enables all 4 buttons and each opens step-specific derivation popup.
        trace.get_by_role("button", name="Next step", exact=True).click()
        for target_key in ("Q", "T1", "T2", "T3"):
            btn = curr_card.locator(f'button[data-euclid-breakdown="{target_key}"]')
            check(btn).to_be_enabled()
            btn.click()
            check(deriv_popup).to_be_visible()
            check(deriv_popup).to_contain_text("Step 1:")
            page.locator("#derivation-popup-close-btn").click()
            check(deriv_popup).to_be_hidden()

        # Click a truncated GF(2^163) value cell -> opens Full-Value Inspector Popup with Copy button.
        trunc_cell = curr_card.locator(".trace-inspectable").first
        check(trunc_cell).to_be_visible()
        check(trunc_cell).to_have_attribute("title", "Click to view full value")
        trunc_cell.click()
        inspector_popup = page.locator("#inspector-popup")
        check(inspector_popup).to_be_visible()
        inspector_popup.get_by_role("button", name="Copy Hexadecimal", exact=True).click()
        check(page.locator("#feedback-popup")).to_contain_text("Copied to clipboard")
        page.locator("#inspector-popup-close-btn").click()
        check(inspector_popup).to_be_hidden()

        # Switch to All steps grid: inline (NO .is-maximized), loads 4 steps initially + Show more reveals 4 more, locks playback.
        trace.get_by_role("button", name="All steps grid", exact=True).click()
        check(trace).not_to_have_class("panel trace is-maximized")
        check(trace.locator(".trace-grid-cards > .trace-card")).to_have_count(4)
        show_more = trace.locator(".trace-show-more-btn")
        check(show_more).to_be_visible()
        check(show_more).to_contain_text("Show more (showing 4 of")
        check(trace.locator(".trace-playback-row")).to_have_class("trace-toolbar-row trace-playback-row is-locked")
        check(trace.get_by_role("button", name="Next step", exact=True)).to_be_disabled()
        check(trace.get_by_role("button", name="Play animation", exact=True)).to_be_disabled()
        check(trace.locator(".trace-scrubber")).to_be_disabled()

        show_more.click()
        assert trace.locator(".trace-grid-cards > .trace-card").count() >= 5

        # Switch to Classic table: color legend shown and playback stays locked.
        trace.get_by_role("button", name="Classic table", exact=True).click()
        check(trace.locator(".table-color-legend")).to_be_visible()
        check(trace.get_by_role("button", name="Next step", exact=True)).to_be_disabled()
        check(trace.locator(".trace-scrubber")).to_be_disabled()

        # Return to Step view: playback unlocks cleanly.
        trace.get_by_role("button", name="Step view", exact=True).click()
        check(trace.get_by_role("button", name="Next step", exact=True)).to_be_enabled()

        # 5. Modern top-center floating error alert (#error-popup) sits near top of viewport and closes on Esc.
        page.locator("#poly-a").fill("0")
        page.locator("#calculate").click()
        err = page.locator("#error-popup")
        check(err).to_be_visible()
        err_box = err.bounding_box()
        assert err_box is not None and err_box["y"] < 80
        page.keyboard.press("Escape")
        check(err).to_be_hidden()

        # 6. Upload modal, First changed bit jump, and zero overflow on desktop and mobile.
        page.locator("#upload").click()
        check(page.locator("#upload-modal")).to_be_visible()
        page.locator("#upload-modal-close").click()
        check(page.locator("#upload-modal")).to_be_hidden()

        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        page.set_viewport_size({"width": 390, "height": 840})
        check(badge_img).to_be_visible()
        assert page.evaluate("document.querySelector('.brand-badge-img').naturalWidth > 0")
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        unexpected_console = [msg for msg in console_errors if "400 (Bad Request)" not in msg]
        assert not unexpected_console
        assert not page_errors
        browser.close()


def test_milestone6_simplified_self_contained_lessons(live_url: str) -> None:
    """Verify simplified #lessons layout (no playback bar/handoffs), fixed b1x, Z2 truth tables in 1.2 & 2.1, and linear Previous/Next section stepping."""
    playwright = pytest.importorskip("playwright.sync_api")
    check = playwright.expect
    with playwright.sync_playwright() as runner:
        browser = runner.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page_errors = []
        console_errors = []
        page.on("pageerror", lambda err: page_errors.append(str(err)))
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        page.goto(live_url)

        page.get_by_role("link", name="Lessons", exact=True).click()
        check(page.get_by_role("heading", name="Polynomial arithmetic lessons")).to_be_visible()

        # 1. No top playback bar, no step dots, no Calculator handoff buttons.
        check(page.locator("#lesson-controls")).to_have_count(0)
        check(page.locator("#lesson-step-dots")).to_have_count(0)
        check(page.locator("#lesson-handoff-bar")).to_have_count(0)
        check(page.locator(".lesson-try-calculator")).to_have_count(0)

        # 2. All 7 lessons present; 1.1 fixes b_1x -> b<sub>1</sub>x (no <sub>1x</sub>) and keeps 8-bit sandbox.
        cards = page.locator("#lesson-catalog .lesson-hub-card")
        check(cards).to_have_count(7)
        check(page.locator("#lesson-active-title")).to_contain_text("Lesson 1")
        sub_texts = page.locator("#lesson-stage .lesson-formula-banner sub").all_inner_texts()
        assert "1" in sub_texts
        assert "1x" not in sub_texts

        sandbox = page.locator(".lesson-activity").first
        check(sandbox).to_contain_text("Hex: {57}")
        sandbox.get_by_label("Sandbox bit x^7").check()
        check(sandbox).to_contain_text("Hex: {D7}")

        # 3. Footer buttons are Previous section / Next section; disabled on very first section.
        prev_sec = page.locator("#lesson-prev-topic")
        next_sec = page.locator("#lesson-next-topic")
        check(prev_sec).to_have_text("Previous section")
        check(next_sec).to_have_text("Next section")
        check(prev_sec).to_be_disabled()
        check(next_sec).to_be_enabled()

        # Advance to Section 1.2 -> clean 4-row Z_2 truth table!
        next_sec.click()
        check(page.locator("#lesson-stage")).to_contain_text("1.2")
        check(page.locator("#lesson-stage table.truth-table tbody tr")).to_have_count(4)
        check(page.locator("#lesson-stage table.truth-table")).to_contain_text("Carry = 0")

        # Step linearly across 1.3 -> 1.4 -> 2.1 (Lesson 2, Section 2.1 truth table!).
        next_sec.click()
        check(page.locator("#lesson-stage")).to_contain_text("1.3")
        next_sec.click()
        check(page.locator("#lesson-stage")).to_contain_text("1.4")
        next_sec.click()
        check(page.locator("#lesson-active-title")).to_contain_text("Lesson 2")
        check(page.locator("#lesson-stage")).to_contain_text("2.1")
        check(page.locator("#lesson-stage table.truth-table tbody tr")).to_have_count(4)

        # Previous section steps back cleanly from 2.1 -> 1.4!
        prev_sec.click()
        check(page.locator("#lesson-active-title")).to_contain_text("Lesson 1")
        check(page.locator("#lesson-stage")).to_contain_text("1.4")

        # Simplified 4-step Lessons Tutorial tour works cleanly.
        page.locator("#tutorial-open").click()
        check(page.locator("#lesson-hub.tour-highlight")).to_be_visible()
        for target in ("#lesson-subtabs", "#lesson-stage", ".lesson-footer"):
            page.locator("#tour-next").click()
            check(page.locator(target + ".tour-highlight")).to_be_visible()
        page.get_by_role("button", name="Done", exact=True).click()
        check(page.locator("#page-tour")).to_be_hidden()

        # Verify mobile viewport zero horizontal overflow.
        page.set_viewport_size({"width": 390, "height": 840})
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        assert not console_errors
        assert not page_errors
        browser.close()


def test_wave5_deboxed_ui_gentler_speeds_and_global_share_link(live_url: str) -> None:
    """Verify Wave 5 flat de-boxed styling, slower animation speeds (450/900/1800ms), and global Share link across all 5 tabs."""
    playwright = pytest.importorskip("playwright.sync_api")
    check = playwright.expect
    with playwright.sync_playwright() as runner:
        browser = runner.chromium.launch()
        context = browser.new_context(
            permissions=["clipboard-read", "clipboard-write"],
            viewport={"width": 1280, "height": 900},
        )
        page = context.new_page()
        page_errors = []
        console_errors = []
        page.on("pageerror", lambda err: page_errors.append(str(err)))
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        page.goto(live_url)
        check(page.locator("#result")).to_be_hidden()
        page.locator("#presets").get_by_role("button", name="Chapter 4", exact=False).click()
        check(page.locator("#result-value")).to_be_visible()

        # 1. Flat de-boxed UI checks on Calculator result, inline metrics, and borderless diff legend.
        styles = page.evaluate(
            """() => {
                const res = getComputedStyle(document.querySelector('.result-display'));
                const met = getComputedStyle(document.querySelector('#metrics span'));
                const leg = getComputedStyle(document.querySelector('.diff-legend-item'));
                return {
                    resultBorder: res.borderTopWidth,
                    metricBorder: met.borderTopWidth,
                    legendBorder: leg.borderTopWidth,
                    legendBg: leg.backgroundColor,
                };
            }"""
        )
        assert styles["resultBorder"] == "0px"
        assert styles["metricBorder"] == "0px"
        assert styles["legendBorder"] == "0px"
        assert styles["legendBg"] in ("rgba(0, 0, 0, 0)", "transparent")

        # 2. Gentler Play animation speed tiers (Slow 1800ms, Normal 900ms, Fast 450ms).
        speed_opts = page.locator(".trace-speed option").evaluate_all(
            "els => els.map(e => [e.value, e.dataset.ms, e.textContent.trim()])"
        )
        assert speed_opts == [
            ["slow", "1800", "Slow (1.8s)"],
            ["normal", "900", "Normal (0.9s)"],
            ["fast", "450", "Fast (0.45s)"],
        ]

        # 3. Global Share link stays visible across all 5 tabs and restores exact page state.
        share_btn = page.get_by_role("button", name="Share link", exact=True)

        # Lessons share link -> restores Lesson 1, Section 1.2.
        page.get_by_role("link", name="Lessons", exact=True).click()
        check(share_btn).to_be_visible()
        page.locator("#lesson-next-topic").click()
        check(page.locator("#lesson-stage")).to_contain_text("1.2")
        share_btn.click()
        lessons_url = page.evaluate("navigator.clipboard.readText()")
        assert "lesson=1&section=1.2#lessons" in lessons_url
        tab_lessons = context.new_page()
        tab_lessons.goto(lessons_url)
        check(tab_lessons.locator("#lesson-stage")).to_contain_text("1.2")
        tab_lessons.close()

        # Modulus share link -> restores custom reducible modulus.
        page.get_by_role("link", name="Modulus explorer", exact=True).click()
        check(share_btn).to_be_visible()
        page.get_by_role("button", name="Try reducible", exact=False).click()
        check(page.locator("#modulus-status")).to_contain_text("Reducible")
        share_btn.click()
        modulus_url = page.evaluate("navigator.clipboard.readText()")
        assert "#modulus" in modulus_url and "mod_base=poly" in modulus_url
        tab_mod = context.new_page()
        tab_mod.goto(modulus_url)
        check(tab_mod.locator("#modulus-status")).to_contain_text("Reducible")
        tab_mod.close()

        # Applications share link -> restores Binary ECC Teaching Curve with custom private keys.
        page.get_by_role("link", name="Applications", exact=True).click()
        check(share_btn).to_be_visible()
        page.locator("#app-tab-ecc").click()
        page.locator("#ecc-curve").select_option("gf2_4")
        page.locator("#ecc-na").fill("4")
        page.locator("#ecc-nb").fill("7")
        page.locator("#ecc-form button[type=submit]").click()
        check(page.locator("#ecc-curve-badge")).to_contain_text("Teaching Curve")
        share_btn.click()
        ecc_url = page.evaluate("navigator.clipboard.readText()")
        assert "app=ecc&curve=gf2_4&na=4&nb=7#applications" in ecc_url
        tab_ecc = context.new_page()
        tab_ecc.goto(ecc_url)
        check(tab_ecc.locator("#ecc-curve")).to_have_value("gf2_4")
        check(tab_ecc.locator("#ecc-na")).to_have_value("4")
        check(tab_ecc.locator("#ecc-nb")).to_have_value("7")
        check(tab_ecc.locator("#ecc-curve-badge")).to_contain_text("Teaching Curve")
        tab_ecc.close()

        # Applications GCM / GHASH share link -> restores custom H and blocks directly on GHASH sub-tab.
        page.locator("#app-tab-ghash").click()
        check(page.locator("#ghash-results")).to_be_hidden()
        page.locator("#ghash-h").fill("0123456789abcdef0123456789abcdef")
        check(page.locator("#ghash-h")).to_have_value("0123456789ABCDEF0123456789ABCDEF")
        page.locator("#ghash-blocks").fill("11111111111111111111111111111111\n22222222222222222222222222222222")
        page.locator("#ghash-form button[type=submit]").click()
        check(page.locator("#ghash-results")).to_be_visible()
        check(page.locator("#ghash-steps tbody tr")).to_have_count(2)
        expected_tag = page.locator("#ghash-tag-display button.trace-inspectable").get_attribute("data-full-value")
        share_btn.click()
        ghash_url = page.evaluate("navigator.clipboard.readText()")
        assert "app=ghash&h=0123456789ABCDEF0123456789ABCDEF" in ghash_url and "#applications" in ghash_url
        tab_ghash = context.new_page()
        tab_ghash.goto(ghash_url)
        check(tab_ghash.locator("#ghash-results")).to_be_visible()
        check(tab_ghash.locator("#ghash-steps tbody tr")).to_have_count(2)
        assert tab_ghash.locator("#ghash-tag-display button.trace-inspectable").get_attribute("data-full-value") == expected_tag
        tab_ghash.set_viewport_size({"width": 390, "height": 840})
        assert tab_ghash.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        tab_ghash.close()

        # Compare multiplication share link -> restores degree + operands.
        page.get_by_role("link", name="Compare multiplication", exact=True).click()
        check(share_btn).to_be_visible()
        page.locator("#compare-degree").select_option("4")
        page.locator("#compare-a").fill("E")
        page.locator("#compare-b").fill("D")
        page.locator("#compare-form button[type=submit]").click()
        check(page.locator("#shift-method-result")).to_have_text("9 (hex)")
        share_btn.click()
        cmp_url = page.evaluate("navigator.clipboard.readText()")
        assert "m=4&a=E&b=D#compare" in cmp_url
        tab_cmp = context.new_page()
        tab_cmp.goto(cmp_url)
        check(tab_cmp.locator("#compare-degree")).to_have_value("4")
        check(tab_cmp.locator("#shift-method-result")).to_have_text("9 (hex)")
        tab_cmp.close()

        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        page.set_viewport_size({"width": 390, "height": 840})
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        assert not console_errors
        assert not page_errors
        browser.close()
