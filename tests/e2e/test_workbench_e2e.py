"""Chromium Playwright end-to-end acceptance tests for the Finite Field Lab workbench."""
from __future__ import annotations

from pathlib import Path

import pytest

DEMO_OPERANDS = Path(__file__).resolve().parents[2] / "data" / "demo-operands.json"


def test_browser_workflow(live_url: str) -> None:
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
        check(page.locator("#result-value")).to_be_visible()

        page.locator("#presets").get_by_role("button", name="Chapter 4", exact=False).click()
        check(page.locator("#result-value")).to_have_text("C1")
        check(page.locator("#hero-degree")).to_have_text("8")
        check(page.get_by_role("heading", name="Table 1", exact=False)).to_be_visible()
        check(page.get_by_role("heading", name="Table 2", exact=False)).to_be_visible()
        page.get_by_role("button", name="Next step").click()
        check(page.get_by_text("Step 1 of", exact=False)).to_be_visible()
        page.get_by_role("button", name="Classic table", exact=True).click()
        page.get_by_role("button", name="Binary", exact=True).click()
        check(page.locator("#poly-a")).to_have_value("01010111")

        page.get_by_role("button", name="Copy calculation link").click()
        share = page.evaluate("navigator.clipboard.readText()")
        assert "base=binary&poly_a=57&poly_b=83" in share
        restored = context.new_page()
        restored.goto(share)
        check(restored.locator("#result-value")).to_have_text("11000001")
        check(restored.locator("#poly-a")).to_have_value("01010111")
        restored.close()

        page.locator('input[value="add"]').check(force=True)
        page.locator("#calculate").click()
        check(page.locator("#result-value")).to_have_text("11010100")
        check(page.get_by_role("heading", name="Bitwise XOR")).to_be_visible()

        page.locator('input[value="modulo"]').check(force=True)
        page.locator("#poly-a").fill("100000000")
        page.locator("#calculate").click()
        check(page.locator("#result-value")).to_have_text("00011011")
        check(page.get_by_role("heading", name="Modulo reduction")).to_be_visible()

        page.locator("#tutorial-open").click()
        check(page.locator("#tour-title")).to_have_text("Choose a field")
        check(page.locator(".setting.tour-highlight")).to_be_visible()
        page.locator("#tour-next").click()
        check(page.locator(".operands.tour-highlight")).to_be_visible()
        page.locator("#tour-prev").click()
        check(page.locator("#tour-prev")).to_be_disabled()
        page.locator("#concepts-open").click()
        check(page.get_by_role("dialog")).to_be_visible()
        for _ in range(3):
            page.locator("#slide-next").click()
        page.locator("#tutorial-slide").get_by_role("button", name="Chapter 5", exact=False).click()
        page.keyboard.press("Escape")
        check(page.locator("#page-tour")).to_be_hidden()
        check(page.locator("#result-value")).to_have_text("10001010")
        check(page.locator("#poly-b")).to_be_disabled()
        page.get_by_label("Euclid cell notation").select_option("algebraic")
        check(page.get_by_role("heading", name="Table 4.7", exact=False)).to_be_visible()

        for fmt in ("md", "json"):
            page.locator("#export-format").select_option(fmt)
            with page.expect_download() as download:
                page.locator("#export").click()
            assert download.value.suggested_filename.endswith("." + fmt)

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
            "#presets",
            "#presets",
            "#share",
        ):
            page.locator("#tour-next").click()
            check(page.locator(expected_target + ".tour-highlight")).to_be_visible()
        page.get_by_role("button", name="Done", exact=True).click()
        check(page.locator("#page-tour")).to_be_hidden()
        check(page.locator(".tour-highlight")).to_have_count(0)
        assert page.evaluate("document.documentElement.scrollWidth === window.innerWidth")
        assert not page_errors
        browser.close()


def test_explorations_in_browser(live_url: str) -> None:
    playwright = pytest.importorskip("playwright.sync_api")
    with playwright.sync_playwright() as runner:
        browser = runner.chromium.launch()
        page = browser.new_page()
        page_errors = []
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        page.goto(live_url)
        check = playwright.expect
        check(page.locator("#result-value")).to_be_visible()

        page.get_by_role("link", name="Modulus explorer").click()
        page.get_by_role("button", name="Test irreducibility").click()
        check(page.locator("#modulus-status")).to_have_text("Irreducible · degree 8")
        page.get_by_role("button", name="Try reducible", exact=False).click()
        check(page.locator("#modulus-status")).to_have_text("Reducible · degree 8")
        check(page.locator("#modulus-witness")).to_contain_text("leaves remainder 0")
        page.get_by_text("Show the polynomial GCD checks").click()
        check(page.get_by_role("heading", name="GCD checkpoints")).to_be_visible()
        page.get_by_role("button", name="Use calculator modulus").click()
        check(page.locator("#modulus-status")).to_have_text("Irreducible · degree 163")

        page.get_by_role("link", name="AES S-box").click()
        page.get_by_role("button", name="Try byte 53").click()
        check(page.locator("#aes-pipeline")).to_contain_text("ED")
        page.get_by_text("Show the Extended Euclid trace").click()
        check(page.get_by_role("heading", name="Table 4.7", exact=False)).to_be_visible()
        page.get_by_role("button", name="Try byte 00").click()
        check(page.locator("#aes-pipeline")).to_contain_text("63")
        check(page.locator("#aes-euclid")).to_be_hidden()

        page.get_by_role("link", name="Compare multiplication").click()
        page.get_by_role("button", name="Compare results").click()
        check(page.locator("#compare-status")).to_have_text("Both methods agree · GF(28)")
        check(page.locator("#compare-status sup")).to_have_text("8")
        check(page.locator("#shift-method-result")).to_have_text("C1 (hex)")
        check(page.get_by_role("heading", name="Leading-term cancellations")).to_be_visible()
        page.get_by_role("button", name="Run benchmark").click()
        benchmark = page.get_by_role("region", name="Median time per multiplication")
        check(benchmark.get_by_role("row", name="163 bits", exact=False)).to_contain_text("Match")
        check(benchmark.get_by_role("row", name="571 bits", exact=False)).to_contain_text("Match")

        page.set_viewport_size({"width": 390, "height": 840})
        page.locator("#compare-degree").select_option("571")
        page.locator("#compare-a").fill("4" + "0" * 141 + "1")
        page.get_by_role("button", name="Compare results").click()
        check(page.locator("#compare-status")).to_have_text("Both methods agree · GF(2571)")
        assert page.evaluate("document.documentElement.scrollWidth === window.innerWidth")
        page.get_by_role("link", name="Calculator", exact=True).click()
        check(page.locator("#field")).to_have_value("163")
        assert not page_errors
        browser.close()


@pytest.mark.parametrize(
    "view,form,example,result,remaining",
    [
        ("modulus", "#modulus-form", "#modulus-example", "#modulus-result", (".witness", "#modulus-result details")),
        ("aes", "#aes-form", "#aes-example", "#aes-result", ("#aes-euclid", "#aes-affine")),
        (
            "compare",
            "#compare-form",
            "#compare-form button[type=submit]",
            "#compare-results",
            ("#compare-shift-body", "#compare-division-body", "#compare-benchmark"),
        ),
    ],
)
def test_experiment_tour_tracks_the_active_view_and_result(
    live_url: str, view: str, form: str, example: str, result: str, remaining: tuple[str, ...]
) -> None:
    playwright = pytest.importorskip("playwright.sync_api")
    check = playwright.expect
    viewport = {"width": 390, "height": 840} if view == "compare" else {"width": 1280, "height": 900}
    with playwright.sync_playwright() as runner:
        browser = runner.chromium.launch()
        page = browser.new_page(viewport=viewport)
        page.goto(f"{live_url}#{view}")
        check(page.locator(form)).to_be_visible()
        tutorial = page.get_by_role("button", name="Tutorial tour", exact=True)
        check(tutorial).to_be_visible(timeout=2000)
        tutorial.click()
        check(page.locator(form + ".tour-highlight")).to_be_in_viewport()

        next_step = page.locator("#tour-next")
        next_step.click()
        check(page.locator(form + " button[type=submit].tour-highlight")).to_be_visible()
        page.locator(example).click()
        check(page.locator(result + ".tour-highlight")).to_be_in_viewport()
        for target in remaining:
            next_step.click()
            check(page.locator(target + ".tour-highlight")).to_be_in_viewport()

        check(next_step).to_have_text("Done")
        next_step.click()
        check(tutorial).to_be_focused()
        check(page.locator(result)).to_be_visible()
        check(page.locator(".tour-highlight")).to_have_count(0)
        tutorial.click()
        page.get_by_role("link", name="Calculator", exact=True).click()
        check(page.locator("#page-tour")).to_be_hidden()
        browser.close()


def test_calculator_tour_guides_the_preview_bits_and_comparison(live_url: str) -> None:
    playwright = pytest.importorskip("playwright.sync_api")
    check = playwright.expect
    with playwright.sync_playwright() as runner:
        browser = runner.chromium.launch()
        page = browser.new_page(viewport={"width": 390, "height": 840})
        page.goto(live_url)
        check(page.locator("#result-value")).to_have_text("2B79")
        page.get_by_role("button", name="Tutorial tour", exact=True).click()
        next_step = page.locator("#tour-next")
        for _ in range(6):
            next_step.click()
        description = page.locator("#tour-description")
        check(description).to_contain_text("Show full value", timeout=2500)
        check(description).to_contain_text("Back to inputs")
        page.get_by_role("button", name="Show full value", exact=True).click()
        check(page.locator("#result-value")).to_have_text(format(0x2B79, "041X"))

        next_step.click()
        check(description).to_contain_text("Classic table")
        next_step.click()
        check(page.locator("#trace-body.tour-highlight")).to_be_visible()
        page.locator('label:has(input[value="add"])').click()
        page.locator("#calculate").click()
        check(page.locator("#presets.tour-highlight")).to_be_visible()
        page.locator("#presets").get_by_role("button", name="Chapter 4", exact=False).click()
        check(page.locator("#trace-body.tour-highlight")).to_be_visible()
        page.get_by_role("button", name="Multiplier bit 7", exact=True).click()
        check(page.get_by_text("{F9} ⊕ {38} = {C1}", exact=True)).to_be_visible()
        check(page.locator("#trace-body.tour-highlight")).to_be_visible()

        next_step.click()
        shortcut = page.locator("#compare-product.tour-highlight")
        check(shortcut).to_be_visible()
        shortcut.click()
        check(page.locator("#page-tour")).to_be_hidden()
        check(page.locator("#compare-status")).to_have_text("Both methods agree · GF(28)")
        browser.close()


def test_linked_multiplier_bit_highlights_both_rows(live_url: str) -> None:
    playwright = pytest.importorskip("playwright.sync_api")
    check = playwright.expect
    with playwright.sync_playwright() as runner:
        browser = runner.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(live_url)
        page.locator("#presets").get_by_role("button", name="Chapter 4", exact=False).click()
        check(page.locator("#result-value")).to_have_text("C1")
        trace = page.locator("#trace-panel")
        bit = trace.get_by_role("button", name="Multiplier bit 7", exact=True)
        check(bit).to_be_visible(timeout=2500)
        check(bit).to_have_accessible_description("Value 1", timeout=2500)
        bit.focus()
        bit.press("Enter")
        check(bit).to_be_focused()
        check(bit).to_have_attribute("aria-pressed", "true")
        for title in ("Table 1", "Table 2"):
            row = trace.get_by_role("region", name=title, exact=False).locator('tr[aria-current="true"]')
            check(row.locator("td").first).to_have_text("7")
            check(row).to_contain_text("38")
        check(trace.get_by_text("F9 ⊕ 38 = C1", exact=True)).to_be_visible()

        trace.get_by_role("button", name="Multiplier bit 6", exact=True).click()
        check(
            trace.get_by_role("region", name="Table 1", exact=False)
            .locator('tr[aria-current="true"] td')
            .first
        ).to_have_text("6")
        check(
            trace.get_by_role("region", name="Table 2", exact=False).locator('tr[aria-current="true"]')
        ).to_have_count(0)
        check(trace.get_by_text("Running XOR stays F9", exact=False)).to_be_visible()
        browser.close()


def test_compact_result_keeps_the_full_copyable_value(live_url: str) -> None:
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
        page.locator("#calculate").click()
        check(page.locator("#result-title")).to_be_focused(timeout=2500)
        check(page.locator("#result-value")).to_be_in_viewport()
        check(page.locator("#result-value")).to_have_text("2B79")
        check(
            page.get_by_role("region", name="Current trace step").get_by_text(
                "{0} ⊕ {57} = {57}", exact=True
            )
        ).to_be_visible(timeout=2500)

        full_163 = format(0x2B79, "041X")
        page.get_by_role("button", name="Copy result", exact=True).click()
        assert page.evaluate("navigator.clipboard.readText()") == full_163
        page.get_by_role("button", name="Show full value", exact=True).click()
        check(page.locator("#result-value")).to_have_text(full_163)
        page.get_by_role("button", name="Show preview", exact=True).click()
        check(page.locator("#result-value")).to_have_text("2B79")
        page.get_by_role("button", name="Back to inputs", exact=True).click()
        check(page.locator("#poly-a")).to_be_focused()

        full_571 = "4" + "0" * 141 + "1"
        page.locator("#field").select_option("571")
        page.locator("#poly-a").fill(full_571)
        page.locator("#poly-b").fill("1")
        page.locator("#calculate").click()
        check(page.locator("#result-value")).to_contain_text("…")
        page.get_by_role("button", name="Show full value", exact=True).click()
        check(page.locator("#result-value")).to_have_text(full_571)
        assert page.evaluate("document.documentElement.scrollWidth === window.innerWidth")
        browser.close()


def test_mobile_trace_shows_one_labelled_step(live_url: str) -> None:
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
        check(card).to_contain_text("Multiplier bit 0")
        check(card).to_contain_text("Shifted operand A")
        trace.get_by_role("button", name="Next step", exact=True).click()
        check(card).to_contain_text("Multiplier bit 1")
        trace.get_by_role("button", name="Multiplier bit 6", exact=True).click()
        trace.get_by_role("button", name="Next step", exact=True).click()
        check(trace.get_by_role("button", name="Multiplier bit 7", exact=True)).to_be_in_viewport(
            ratio=0.95, timeout=2500
        )
        check(card).to_contain_text("{F9} ⊕ {38} = {C1}")
        check(trace.get_by_role("region", name="Table 1", exact=False)).to_be_hidden()
        trace.get_by_role("button", name="Classic table", exact=True).click()
        check(trace.get_by_role("region", name="Table 1", exact=False)).to_be_visible()

        page.locator('input[value="modulo"]').check(force=True)
        page.locator("#poly-a").fill("100")
        page.locator("#calculate").click()
        check(card).to_contain_text("Shifted modulus")
        check(card).to_contain_text("11B")
        check(card).to_contain_text("1B")
        browser.close()


def test_compare_this_product_transfers_the_exact_calculation(live_url: str) -> None:
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
        shortcut = page.get_by_role("button", name="Compare this product", exact=True)
        check(shortcut).to_be_visible(timeout=2500)
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
        browser.close()


def test_milestone6_zero_scroll_trace_modes_and_playback(live_url: str) -> None:
    """Verify Milestone 6 zero-horizontal-scroll trace modes, 5-button playback, compact toggle, and full-view modal."""
    playwright = pytest.importorskip("playwright.sync_api")
    check = playwright.expect
    with playwright.sync_playwright() as runner:
        browser = runner.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page_errors = []
        page.on("pageerror", lambda err: page_errors.append(str(err)))
        page.goto(live_url)

        # Verify "Tutorial tour" header button rename.
        check(page.locator("#tutorial-open")).to_have_text("Tutorial tour")

        # Run GF(2^163) Multiplicative Inverse (Extended Euclid Table 4.7).
        page.locator("#field").select_option("163")
        page.locator('input[value="inverse"]').check(force=True)
        page.locator("#poly-a").fill("57")
        page.locator("#calculate").click()
        check(page.locator("#verification")).to_contain_text("Mathematically verified")

        trace = page.locator("#trace-panel")
        check(trace).to_be_visible()
        # Large field (m=163 > 8) defaults to Step view and Compact values ON.
        step_mode_btn = trace.get_by_role("button", name="Step view", exact=True)
        grid_mode_btn = trace.get_by_role("button", name="All steps grid", exact=True)
        table_mode_btn = trace.get_by_role("button", name="Classic table", exact=True)
        check(step_mode_btn).to_have_attribute("aria-pressed", "true")

        # Step Inspector Square renders Triple A(x), Triple B(x), and Q(x) with zero horizontal scroll.
        inspector = trace.get_by_role("region", name="Current trace step")
        check(inspector).to_be_visible()
        check(inspector).to_contain_text("Extended Euclid · step 0")
        check(inspector).to_contain_text("Triple A(x)")
        check(inspector).to_contain_text("Triple B(x)")
        assert page.evaluate(
            "document.getElementById('trace-panel').scrollWidth <= document.getElementById('trace-panel').clientWidth"
        )
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")

        # Test 5-button playback bar: Next step, Last step, First step, Previous step.
        trace.get_by_role("button", name="Next step", exact=True).click()
        check(inspector).to_contain_text("Extended Euclid · step 1")
        trace.get_by_role("button", name="Last step", exact=True).click()
        check(inspector).to_contain_text("B3(x) = 1, so B2(x) gives the inverse.")
        trace.get_by_role("button", name="Previous step", exact=True).click()
        check(inspector).to_contain_text("Extended Euclid · step")
        trace.get_by_role("button", name="First step", exact=True).click()
        check(inspector).to_contain_text("Extended Euclid · step 0")

        # Test Compact values / Full m-bit toggle in Step view with zero horizontal overflow.
        full_toggle = trace.get_by_role("button", name="Full m-bit", exact=True)
        check(full_toggle).to_be_visible()
        full_toggle.click()
        check(trace.get_by_role("button", name="Compact values", exact=True)).to_be_visible()
        assert page.evaluate(
            "document.getElementById('trace-panel').scrollWidth <= document.getElementById('trace-panel').clientWidth"
        )

        # Switch to All steps grid mode and verify zero horizontal overflow.
        grid_mode_btn.click()
        check(grid_mode_btn).to_have_attribute("aria-pressed", "true")
        check(trace.locator(".trace-grid-cards .euclid-inspector-square").first).to_be_visible()
        assert page.evaluate(
            "document.getElementById('trace-panel').scrollWidth <= document.getElementById('trace-panel').clientWidth"
        )

        # Switch to Classic table mode and verify wrapped cells keep page overflow at zero.
        table_mode_btn.click()
        check(table_mode_btn).to_have_attribute("aria-pressed", "true")
        check(trace.get_by_role("heading", name="Table 4.7", exact=False)).to_be_visible()
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")

        # Open Expand full view modal and verify full Table 4.7 inside dialog.
        trace.get_by_role("button", name="Expand full view", exact=True).click()
        fullscreen = page.locator("#trace-fullscreen")
        check(fullscreen).to_be_visible()
        check(fullscreen.get_by_role("heading", name="Table 4.7", exact=False)).to_be_visible()
        page.locator("#trace-fullscreen-close").click()
        check(fullscreen).to_be_hidden()

        # Verify mobile viewport (390x840) has zero horizontal overflow.
        page.set_viewport_size({"width": 390, "height": 840})
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        assert not page_errors
        browser.close()


def test_milestone6_standalone_lessons_page_and_handoff(live_url: str) -> None:
    """Verify the standalone animated #lessons curriculum, 5-button playback, tour, activities, and Calculator handoff."""
    playwright = pytest.importorskip("playwright.sync_api")
    check = playwright.expect
    with playwright.sync_playwright() as runner:
        browser = runner.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page_errors = []
        page.on("pageerror", lambda err: page_errors.append(str(err)))
        page.goto(live_url)

        # Navigate to Lessons page via top-level tab.
        page.get_by_role("link", name="Lessons", exact=True).click()
        check(page.get_by_role("heading", name="Polynomial arithmetic lessons")).to_be_visible()

        # Verify all 7 lessons are rendered in the catalog hub.
        cards = page.locator("#lesson-catalog .lesson-hub-card")
        check(cards).to_have_count(7)
        check(page.locator("#lesson-active-title")).to_contain_text("Lesson 1")

        # Verify Tutorial tour works on the Lessons view across all 5 steps.
        page.locator("#tutorial-open").click()
        check(page.locator("#lesson-hub.tour-highlight")).to_be_visible()
        for target in ("#lesson-subtabs", "#lesson-controls", "#lesson-stage", "#lesson-handoff-bar"):
            page.locator("#tour-next").click()
            check(page.locator(target + ".tour-highlight")).to_be_visible()
        page.get_by_role("button", name="Done", exact=True).click()
        check(page.locator("#page-tour")).to_be_hidden()

        # Test Lesson 1 interactive 8-bit polynomial sandbox and 5-button playback controls.
        sandbox = page.locator(".lesson-activity").first
        check(sandbox).to_contain_text("Hex: {57}")
        sandbox.get_by_label("Sandbox bit x^7").check()
        check(sandbox).to_contain_text("Hex: {D7}")
        check(page.locator("#lesson-step-progress")).to_have_text("Step 1 / 3")
        page.locator("#lesson-next").click()
        check(page.locator("#lesson-step-progress")).to_have_text("Step 2 / 3")
        page.locator("#lesson-last").click()
        check(page.locator("#lesson-step-progress")).to_have_text("Step 3 / 3")
        page.locator("#lesson-first").click()
        check(page.locator("#lesson-step-progress")).to_have_text("Step 1 / 3")

        # Switch to Lesson 2 (Addition & Subtraction), sub-lesson 2.2 (3 steps), then sub-lesson 2.3 (quiz).
        cards.nth(1).click()
        check(page.locator("#lesson-active-title")).to_contain_text("Lesson 2")
        page.locator("#lesson-subtabs .lesson-subtab").nth(1).click()
        check(page.locator("#lesson-step-progress")).to_have_text("Step 1 / 3")
        page.locator("#lesson-next").click()
        check(page.locator("#lesson-step-progress")).to_have_text("Step 2 / 3")
        page.locator("#lesson-subtabs .lesson-subtab").nth(2).click()
        quiz_option = page.locator(".lesson-quiz-option").first
        quiz_option.click()
        check(page.locator(".lesson-quiz-feedback")).to_contain_text("Correct!")

        # Switch to Lesson 6 (Multiplicative Inverse & Extended Euclid) and test Calculator handoff ({83}^-1 = {80}).
        cards.nth(5).click()
        check(page.locator("#lesson-active-title")).to_contain_text("Lesson 6")
        page.locator(".lesson-try-calculator").click()
        check(page.locator("#field")).to_have_value("8")
        check(page.locator("#result-value")).to_have_text("80")

        # Return to Lessons on mobile viewport (390x840) and verify zero horizontal overflow.
        page.set_viewport_size({"width": 390, "height": 840})
        page.get_by_role("link", name="Lessons", exact=True).click()
        check(page.get_by_role("heading", name="Polynomial arithmetic lessons")).to_be_visible()
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        assert not page_errors
        browser.close()


def test_milestone6_wave2_trace_visual_diffs_and_compare_mode(live_url: str) -> None:
    """Verify Wave 2 visual diff badges, inline was: deltas, and side-by-side Compare prev → curr in Calculator traces."""
    playwright = pytest.importorskip("playwright.sync_api")
    check = playwright.expect
    with playwright.sync_playwright() as runner:
        browser = runner.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page_errors = []
        page.on("pageerror", lambda err: page_errors.append(str(err)))
        page.goto(live_url)

        # Compute GF(2^163) Inverse ({57}^-1) which defaults to Step view.
        page.locator("#field").select_option("163")
        page.locator('input[value="inverse"]').check(force=True)
        page.locator("#poly-a").fill("57")
        page.locator("#calculate").click()
        check(page.locator("#verification")).to_contain_text("Mathematically verified")

        trace = page.locator("#trace-panel")
        check(trace.locator(".diff-legend")).to_be_visible()

        # Step 0 -> Step 1 -> Step 2: verify transition banner, diff badges, and inline was: values.
        next_btn = trace.get_by_role("button", name="Next step", exact=True)
        next_btn.click()
        inspector = trace.get_by_role("region", name="Current trace step")
        check(inspector.locator(".diff-banner")).to_contain_text("Step 0 → Step 1")
        check(inspector.locator(".diff-carried").first).to_be_visible()
        check(inspector.locator(".diff-updated").first).to_be_visible()
        check(inspector.locator(".diff-prev-value").first).to_contain_text("was:")

        next_btn.click()
        check(inspector.locator(".diff-banner")).to_contain_text("Step 1 → Step 2")
        check(inspector.locator(".diff-tag", has_text="← prev B").first).to_be_visible()
        check(inspector.locator(".diff-tag", has_text="New T").first).to_be_visible()

        # Toggle Compare prev → curr: both Previous (Step 1) and Current (Step 2) render simultaneously.
        compare_btn = trace.get_by_role("button", name="Compare prev → curr", exact=True)
        compare_btn.click()
        check(compare_btn).to_have_attribute("aria-pressed", "true")
        prev_pane = trace.get_by_role("region", name="Previous trace step")
        check(prev_pane).to_be_visible()
        check(prev_pane).to_contain_text("Extended Euclid · step 1")
        check(inspector).to_contain_text("Extended Euclid · step 2")
        assert page.evaluate(
            "document.getElementById('trace-panel').scrollWidth <= document.getElementById('trace-panel').clientWidth"
        )
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")

        # Return to Step 0 in compare mode: placeholder message appears for Previous step.
        trace.get_by_role("button", name="First step", exact=True).click()
        check(prev_pane).to_contain_text("Initial state: no previous step")

        # Verify zero horizontal overflow on mobile (390x840) with Compare prev → curr active.
        page.set_viewport_size({"width": 390, "height": 840})
        next_btn.click()
        check(prev_pane).to_be_visible()
        check(inspector).to_be_visible()
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        assert not page_errors
        browser.close()


def test_milestone6_wave2_lessons_visual_diffs_and_compare_mode(live_url: str) -> None:
    """Verify Wave 2 slide-to-slide diff banners, persistent badges, and Compare prev → curr in #lessons."""
    playwright = pytest.importorskip("playwright.sync_api")
    check = playwright.expect
    with playwright.sync_playwright() as runner:
        browser = runner.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page_errors = []
        page.on("pageerror", lambda err: page_errors.append(str(err)))
        page.goto(live_url)

        page.get_by_role("link", name="Lessons", exact=True).click()
        cards = page.locator("#lesson-catalog .lesson-hub-card")

        # Lesson 5 (Multiplication), sub-lesson 5.3 ({57} × {83} = {C1}): verify diff legend & banner.
        cards.nth(4).click()
        page.locator("#lesson-subtabs .lesson-subtab").nth(2).click()
        check(page.locator("#lesson-stage .diff-legend")).to_be_visible()
        page.locator("#lesson-next").click()
        check(page.locator("#lesson-stage .lesson-diff-banner")).to_contain_text("From Step 1 → Step 2:")
        check(page.locator("#lesson-stage .diff-reduced").first).to_be_visible()
        check(page.locator("#lesson-stage .diff-updated").first).to_be_visible()

        # Lesson 6 (Table 4.7), sub-lesson 6.4 ({83}^-1 = {80}): verify carried/updated badges & was: deltas.
        cards.nth(5).click()
        page.locator("#lesson-subtabs .lesson-subtab").nth(3).click()
        page.locator("#lesson-next").click()
        check(page.locator("#lesson-stage .lesson-diff-banner")).to_contain_text("From Step 1 → Step 2:")
        check(page.locator("#lesson-stage .diff-carried").first).to_be_visible()
        check(page.locator("#lesson-stage .diff-updated").first).to_be_visible()
        check(page.locator("#lesson-stage .diff-prev-value").first).to_contain_text("was:")

        # Advance to Step 3 (Row 2) and toggle Compare prev → curr.
        page.locator("#lesson-next").click()
        check(page.locator("#lesson-stage .lesson-diff-banner")).to_contain_text("From Step 2 → Step 3:")
        compare_btn = page.locator("#lesson-compare")
        compare_btn.click()
        check(compare_btn).to_have_attribute("aria-pressed", "true")
        prev_slide = page.get_by_role("region", name="Previous lesson step")
        curr_slide = page.get_by_role("region", name="Current lesson step")
        check(prev_slide).to_be_visible()
        check(curr_slide).to_be_visible()
        check(prev_slide).to_contain_text("Table 4.7 · Step 1")
        check(curr_slide).to_contain_text("Table 4.7 · Step 2")
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")

        # Verify mobile viewport (390x840) stacks cleanly with zero horizontal overflow.
        page.set_viewport_size({"width": 390, "height": 840})
        check(prev_slide).to_be_visible()
        check(curr_slide).to_be_visible()
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        assert not page_errors
        browser.close()


def test_milestone6_wave3_layout_modulus_card_math_popup_maximize_cascade(live_url: str) -> None:
    """Verify Wave 3 refinements: read-only Modulus card, sup/sub typography, pop-up errors, gliding pills, informative step titles, auto-maximized grid, and sequential step cascade."""
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

        # 1. Gliding active pill indicators across primary nav, notation, and operations strips.
        for selector in (".lab-nav", ".segments.notation", ".operations"):
            check(page.locator(selector + " > .sliding-pill")).to_have_count(1)

        # 2. Read-only Modulus m(x) card on Reduce & Inverse preserves Operand B(x).
        page.locator("#field").select_option("8")
        page.locator("#poly-a").fill("57")
        page.locator("#poly-b").fill("83")
        check(page.locator("#operand-b-editable")).to_be_visible()
        check(page.locator("#operand-b-modulus")).to_be_hidden()

        page.locator('input[value="modulo"]').check(force=True)
        check(page.locator("#operand-b-editable")).to_be_hidden()
        check(page.locator("#operand-b-modulus")).to_be_visible()
        check(page.locator("#modulus-lock-badge")).to_have_text("Locked to GF(28)")
        check(page.locator("#modulus-lock-badge sup")).to_have_text("8")
        check(page.locator("#b-modulus-context")).to_have_text("Reducing A(x) mod m(x)")
        check(page.locator("#b-modulus-value")).to_have_text("11B")

        page.locator('input[value="inverse"]').check(force=True)
        check(page.locator("#b-modulus-context")).to_have_text("Inverting A(x)−1 mod m(x)")
        check(page.locator("#b-modulus-context sup")).to_have_text("−1")

        # Polynomial notation updates the read-only modulus display with true <sup> tags.
        page.get_by_role("button", name="Polynomial", exact=True).click()
        check(page.locator("#b-modulus-value sup").first).to_have_text("8")
        check(page.locator("#a-preview sup").first).to_have_text("6")
        assert page.locator("#a-bits sup").count() >= 6

        # Switching back to Multiply restores editable Operand B(x) with its preserved value.
        page.locator('input[value="multiply"]').check(force=True)
        check(page.locator("#operand-b-editable")).to_be_visible()
        check(page.locator("#operand-b-modulus")).to_be_hidden()
        check(page.locator("#poly-b")).to_have_value("x^7 + x + 1")

        # 3. Pop-Up Error Dialog (#error-popup) on 0^-1 closes cleanly on Esc and OK.
        page.get_by_role("button", name="Hex", exact=True).click()
        page.locator('input[value="inverse"]').check(force=True)
        page.locator("#poly-a").fill("00")
        page.locator("#calculate").click()
        popup = page.locator("#error-popup")
        check(popup).to_be_visible()
        check(page.get_by_role("alert")).to_contain_text("Zero element")
        page.keyboard.press("Escape")
        check(popup).to_be_hidden()

        page.locator("#calculate").click()
        check(popup).to_be_visible()
        page.locator("#error-popup-ok").click()
        check(popup).to_be_hidden()

        # 4. Real <sub> / <sup> and .step-knowledge-title in Extended Euclid + Auto-Maximize on All steps grid.
        page.locator("#field").select_option("163")
        page.locator("#poly-a").fill("57")
        page.locator("#calculate").click()
        trace = page.locator("#trace-panel")
        check(trace.locator(".trace-modes > .sliding-pill")).to_have_count(1)
        check(trace.locator(".step-knowledge-title")).to_contain_text("Initialize Bézout Triples")
        check(trace.locator("dt sub").first).to_have_text("1")

        trace.get_by_role("button", name="All steps grid", exact=True).click()
        check(trace).to_have_class("panel trace is-maximized")
        exit_max = trace.get_by_role("button", name="Exit maximized view", exact=True)
        check(exit_max).to_be_visible()
        assert page.evaluate(
            "document.getElementById('trace-panel').scrollWidth <= document.getElementById('trace-panel').clientWidth"
        )
        exit_max.click()
        check(trace).not_to_have_class("panel trace is-maximized")

        # 5. Sequential step cascade (0 -> 1 -> 2 -> 3) when clicking distant multiplier bit 3.
        page.locator("#presets").get_by_role("button", name="Chapter 4", exact=False).click()
        trace.get_by_role("button", name="Step view", exact=True).click()
        check(trace.locator(".step-eyebrow")).to_have_text("Multiplier bit 0")
        page.evaluate("""() => {
            window.__visitedTraceSteps = [];
            const record = () => {
                const el = document.querySelector('#trace-body .step-eyebrow');
                if (el && window.__visitedTraceSteps.at(-1) !== el.textContent) {
                    window.__visitedTraceSteps.push(el.textContent);
                }
            };
            record();
            window.__traceObserver = new MutationObserver(record);
            window.__traceObserver.observe(document.getElementById('trace-body'), { childList: true, subtree: true });
        }""")
        bit3 = trace.get_by_role("button", name="Multiplier bit 3", exact=True)
        bit3.click()
        check(bit3).to_have_attribute("aria-pressed", "true", timeout=4000)
        check(trace.locator(".step-eyebrow")).to_have_text("Multiplier bit 3")
        check(trace.locator(".step-knowledge-title")).not_to_be_empty()
        visited = page.evaluate("""() => {
            window.__traceObserver?.disconnect();
            return window.__visitedTraceSteps;
        }""")
        assert "Multiplier bit 1" in visited and "Multiplier bit 2" in visited and visited[-1] == "Multiplier bit 3"

        # 6. Informative .step-knowledge-title and zero overflow on #lessons (desktop & 390x840 mobile).
        page.get_by_role("link", name="Lessons", exact=True).click()
        check(page.locator("#lesson-stage .step-knowledge-title")).not_to_be_empty()
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")

        page.set_viewport_size({"width": 390, "height": 840})
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        page.get_by_role("link", name="Calculator", exact=True).click()
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        unexpected_console = [msg for msg in console_errors if "400 (Bad Request)" not in msg]
        assert not unexpected_console
        assert not page_errors
        browser.close()


def test_milestone6_wave4_boundaries_first_changed_toasts_upload_modal_and_dashes(live_url: str) -> None:
    """Verify Wave 4 playback boundaries, First changed bit jump, toasts, upload modal, hero badge & zero long dashes."""
    playwright = pytest.importorskip("playwright.sync_api")
    check = playwright.expect
    repo_root = Path(__file__).resolve().parents[2]
    frontend_and_data = sorted(
        list((repo_root / "frontend").glob("*")) + [repo_root / "data" / "tutorial_slides.json"]
    )
    for asset in frontend_and_data:
        if asset.is_file():
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
        page.on("pageerror", lambda err: page_errors.append(str(err)))
        page.goto(live_url)

        # 1. Hero badge shows GF(2^m) cleanly without "1 ⊕ 1 = 0".
        hero_badge = page.locator('[data-lab-view="calculator"] .hero-math')
        check(hero_badge).to_contain_text("GF(2")
        check(hero_badge).not_to_contain_text("1 \u2295 1 = 0")

        # 2. Large-field First changed bit jump (B = 100000 hex = x^20, A = 57 hex in GF(2^163)) & boundary states.
        page.locator("#field").select_option("163")
        page.get_by_role("button", name="Hex", exact=True).click()
        page.locator('input[value="multiply"]').check(force=True)
        page.locator("#poly-a").fill("57")
        page.locator("#poly-b").fill("100000")
        page.locator("#calculate").click()

        trace = page.locator("#trace-panel")
        first_btn = trace.get_by_role("button", name="First step", exact=True)
        prev_btn = trace.get_by_role("button", name="Previous step", exact=True)
        next_btn = trace.get_by_role("button", name="Next step", exact=True)
        last_btn = trace.get_by_role("button", name="Last step", exact=True)
        jump_btn = trace.locator(".trace-first-changed-btn")

        check(trace.locator(".step-eyebrow")).to_have_text("Multiplier bit 0")
        check(first_btn).to_be_disabled()
        check(first_btn).to_have_attribute("aria-disabled", "true")
        check(prev_btn).to_be_disabled()
        check(prev_btn).to_have_attribute("aria-disabled", "true")
        check(next_btn).to_be_enabled()
        check(last_btn).to_be_enabled()
        check(jump_btn).to_have_text("First changed bit")
        check(jump_btn).to_be_enabled()

        jump_btn.click()
        check(trace.locator(".step-eyebrow")).to_have_text("Multiplier bit 20")
        check(trace.locator(".trace-progress")).to_have_text("Step 21 of 21")
        check(trace.get_by_role("button", name="Multiplier bit 20", exact=True)).to_have_attribute("aria-pressed", "true")
        check(jump_btn).to_be_disabled()
        check(jump_btn).to_have_attribute("aria-disabled", "true")
        check(first_btn).to_be_enabled()
        check(prev_btn).to_be_enabled()

        first_btn.click()
        check(trace.locator(".trace-progress")).to_have_text("Step 1 of 21")
        last_btn.click()
        check(trace.locator(".trace-progress")).to_have_text("Step 21 of 21")
        check(next_btn).to_be_disabled()
        check(next_btn).to_have_attribute("aria-disabled", "true")
        check(last_btn).to_be_disabled()
        check(last_btn).to_have_attribute("aria-disabled", "true")
        check(first_btn).to_be_enabled()
        check(prev_btn).to_be_enabled()

        # 3. Copy & Export confirmation pop-up toast (#feedback-popup).
        toast = page.locator("#feedback-popup")
        page.locator("#copy-result").click()
        check(toast).to_be_visible()
        check(toast).to_contain_text("Copied to clipboard")
        toast.get_by_role("button", name="Dismiss notification", exact=True).click()
        check(toast).to_be_hidden()

        page.locator("#export-format").select_option("md")
        with page.expect_download() as download:
            page.locator("#export").click()
        assert download.value.suggested_filename.endswith(".md")
        check(toast).to_be_visible()
        check(toast).to_contain_text("Exported successfully")

        # 4. Upload pop-up modal (#upload-modal) with .txt/.json guide, drag-drop zone, and confirmation toast.
        page.locator("#upload").click()
        upload_modal = page.locator("#upload-modal")
        check(upload_modal).to_be_visible()
        check(upload_modal.locator("#upload-dropzone")).to_be_visible()
        check(upload_modal).to_contain_text(".txt Format")
        check(upload_modal).to_contain_text(".json Format")
        upload_modal.locator("#file").set_input_files(DEMO_OPERANDS)
        check(upload_modal).to_be_hidden()
        check(toast).to_be_visible()
        check(toast).to_contain_text("File uploaded")
        check(page.locator('#pairs option[value="1"]')).to_contain_text("Pair 2")
        check(page.locator("#poly-a")).to_have_value(format(0x57, "041X"))

        # 5. Lesson boundary disabled states (1-step sub-lesson vs. multi-step) + zero overflow on mobile (390x840).
        page.get_by_role("link", name="Lessons", exact=True).click()
        l_first = page.locator("#lesson-first")
        l_prev = page.locator("#lesson-prev")
        l_play = page.locator("#lesson-play")
        l_next = page.locator("#lesson-next")
        l_last = page.locator("#lesson-last")

        # Multi-step sub-lesson (Lesson 1 · 1.1 has 3 steps): start disabled on Step 0, end disabled on Last.
        check(l_first).to_be_disabled()
        check(l_prev).to_be_disabled()
        check(l_play).to_be_enabled()
        check(l_next).to_be_enabled()
        l_last.click()
        check(l_next).to_be_disabled()
        check(l_last).to_be_disabled()
        check(l_first).to_be_enabled()

        # Single-step sub-lesson (Lesson 2 · 2.1): all steppers including Play animation are disabled.
        page.get_by_role("button", name="Lesson 2", exact=False).click()
        check(l_first).to_be_disabled()
        check(l_prev).to_be_disabled()
        check(l_play).to_be_disabled()
        check(l_next).to_be_disabled()
        check(l_last).to_be_disabled()

        page.set_viewport_size({"width": 390, "height": 840})
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        page.get_by_role("link", name="Calculator", exact=True).click()
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        assert not page_errors
        browser.close()


def test_milestone6_wave5_explicit_reduction_and_clear_step_cards(live_url: str) -> None:
    """Verify Wave 5 explicit m(x) reduction breakdown, two-block {hex} step cards, formula strip & initial reduction."""
    playwright = pytest.importorskip("playwright.sync_api")
    check = playwright.expect
    with playwright.sync_playwright() as runner:
        browser = runner.chromium.launch()
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        page = context.new_page()
        page_errors = []
        page.on("pageerror", lambda err: page_errors.append(str(err)))
        page.goto(live_url)

        # 1. GF(2^4) {E} × {D} = {9} walkthrough across Steps 2, 3, and 4.
        page.locator("#field").select_option("4")
        page.get_by_role("button", name="Hex", exact=True).click()
        page.locator('input[value="multiply"]').check(force=True)
        page.locator("#poly-a").fill("E")
        page.locator("#poly-b").fill("D")
        page.locator("#calculate").click()

        check(page.locator("#result-value")).to_have_text("9")
        trace = page.locator("#trace-panel")
        trace.get_by_role("button", name="Step view", exact=True).click()
        next_btn = trace.get_by_role("button", name="Next step", exact=True)

        # Step 2 (Multiplier bit 1, Reduced? = Yes): explicit binary XOR with m(x) = 11001.
        next_btn.click()
        card = trace.get_by_role("region", name="Current trace step")
        shift_block = card.locator(".mul-shift-block")
        sum_block = card.locator(".mul-sum-block")
        breakdown = shift_block.locator(".reduction-breakdown.is-overflow")
        check(shift_block).to_contain_text("1. Shift & Reduce")
        check(breakdown).to_be_visible()
        check(breakdown).to_contain_text("11100")
        check(breakdown).to_contain_text("11001")
        check(breakdown).to_contain_text("0101")
        check(breakdown).to_contain_text("{5}")
        check(sum_block).to_contain_text("2. Check Bit")
        check(sum_block).to_contain_text("Unchanged: Running XOR stays {E}")

        # Step 3 (Multiplier bit 2): Stallings {hex} brace notation ({E} ⊕ {A} = {4}).
        next_btn.click()
        check(sum_block.locator(".bit-equation")).to_have_text("{E} ⊕ {A} = {4}")

        # Step 4 (Multiplier bit 3): Live running formula strip ending in {9}.
        next_btn.click()
        check(card.locator(".mul-formula-strip")).to_have_text(
            "Sum = [1]·{E} ⊕ [0]·{5} ⊕ [1]·{A} ⊕ [1]·{D} = {9}"
        )

        # 2. GF(2^163) cryptographic sparse-tap overflow reduction (x^7 + x^6 + x^3 + 1 with <sup>).
        page.locator("#field").select_option("163")
        page.locator("#poly-a").fill("4" + "0" * 40)  # x^162 -> shifts to x^163 on Step 2
        page.locator("#poly-b").fill("3")
        page.locator("#calculate").click()

        trace.get_by_role("button", name="Next step", exact=True).click()
        crypto_breakdown = trace.locator(".mul-shift-block .reduction-breakdown.is-overflow")
        check(crypto_breakdown).to_be_visible()
        check(crypto_breakdown).to_contain_text("x7 + x6 + x3 + 1")
        check(crypto_breakdown).to_contain_text("{C9}")
        sup_texts = crypto_breakdown.locator("sup").all_inner_texts()
        assert "7" in sup_texts and "6" in sup_texts and "3" in sup_texts
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")

        page.set_viewport_size({"width": 390, "height": 840})
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")

        # 3. Auto-expanded Initial reduction when input has deg >= m (11B in GF(2^8)).
        page.set_viewport_size({"width": 1280, "height": 900})
        page.locator("#field").select_option("8")
        page.locator('input[value="add"]').check(force=True)
        page.locator("#poly-a").fill("11B")
        page.locator("#poly-b").fill("57")
        page.locator("#calculate").click()

        init_panel = trace.locator("details.initial-reduction-panel")
        check(init_panel).to_be_visible()
        check(init_panel).to_have_js_property("open", True)
        check(init_panel.locator(".initial-reduction-steps")).to_contain_text("{11B}")
        check(init_panel.locator(".initial-reduction-steps")).to_contain_text("m(x)")
        assert not page_errors
        browser.close()



