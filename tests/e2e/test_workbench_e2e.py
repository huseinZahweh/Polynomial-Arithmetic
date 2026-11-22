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
        page.get_by_role("button", name="Show all").click()
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
        check(page.get_by_role("alert")).to_contain_text("Zero element")
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
        check(page.get_by_role("alert")).to_contain_text("parse error")
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
        check(page.locator("#compare-status")).to_have_text("Both methods agree · GF(2^8)")
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
        check(page.locator("#compare-status")).to_have_text("Both methods agree · GF(2^571)")
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
        tutorial = page.get_by_role("button", name="Tutorial", exact=True)
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
        page.get_by_role("button", name="Tutorial", exact=True).click()
        next_step = page.locator("#tour-next")
        for _ in range(6):
            next_step.click()
        description = page.locator("#tour-description")
        check(description).to_contain_text("Show full value", timeout=2500)
        check(description).to_contain_text("Back to inputs")
        page.get_by_role("button", name="Show full value", exact=True).click()
        check(page.locator("#result-value")).to_have_text(format(0x2B79, "041X"))

        next_step.click()
        check(description).to_contain_text("Show tables")
        next_step.click()
        check(page.locator("#trace-body.tour-highlight")).to_be_visible()
        page.locator('label:has(input[value="add"])').click()
        page.locator("#calculate").click()
        check(page.locator("#presets.tour-highlight")).to_be_visible()
        page.locator("#presets").get_by_role("button", name="Chapter 4", exact=False).click()
        check(page.locator("#trace-body.tour-highlight")).to_be_visible()
        page.get_by_role("button", name="Multiplier bit 7", exact=True).click()
        check(page.get_by_text("F9 ⊕ 38 = C1", exact=True)).to_be_visible()
        check(page.locator("#trace-body.tour-highlight")).to_be_visible()

        next_step.click()
        shortcut = page.locator("#compare-product.tour-highlight")
        check(shortcut).to_be_visible()
        shortcut.click()
        check(page.locator("#page-tour")).to_be_hidden()
        check(page.locator("#compare-status")).to_have_text("Both methods agree · GF(2^8)")
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
                "0 ⊕ 57 = 57", exact=True
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
        check(card).to_contain_text("F9 ⊕ 38 = C1")
        check(trace.get_by_role("region", name="Table 1", exact=False)).to_be_hidden()
        trace.get_by_role("button", name="Show tables", exact=True).click()
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
        check(page.locator("#compare-status")).to_have_text("Both methods agree · GF(2^3)")
        check(page.locator("#shift-method-result")).to_have_text("6 (hex)")

        page.get_by_role("link", name="Calculator", exact=True).click()
        check(page.locator("#poly-a")).to_have_value("10110")
        page.locator('label:has(input[value="add"])').click()
        check(page.locator('input[value="add"]')).to_be_checked()
        page.locator("#calculate").click()
        check(page.locator("#result-value")).to_be_visible()
        check(shortcut).to_be_hidden()
        browser.close()
