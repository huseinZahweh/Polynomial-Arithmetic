"""Verify audit fixes in the local website, including upload mode defaults."""
import pytest


def test_standard_ghash_and_algebraic_upload(live_url):
    api = pytest.importorskip("playwright.sync_api")
    with api.sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(live_url)
        resources = page.evaluate("performance.getEntriesByType('resource').map(r => r.name)")
        assert not any('fonts.googleapis.com' in url or 'fonts.gstatic.com' in url for url in resources)
        page.get_by_role("link", name="Applications", exact=True).click()
        page.locator("#app-tab-ghash").click()
        page.locator("#ghash-h").fill("80000000000000000000000000000000")
        page.locator("#ghash-blocks").fill("00000000000000000000000000000001")
        page.locator('#ghash-form button[type="submit"]').click()
        value = page.locator("#ghash-tag-display button.trace-inspectable")
        api.expect(value).to_have_attribute("data-full-value", "00000000000000000000000000000001")
        api.expect(page.locator("#app-panel-ghash")).to_contain_text("GHASH value only")
        page.get_by_role("link", name="Calculator", exact=True).click()
        page.get_by_role("button", name="Polynomial", exact=True).click()
        page.locator('#upload').click()
        page.locator('#upload-modal input[type="file"]').set_input_files({"name": "algebraic.txt", "mimeType": "text/plain", "buffer": b"A: x + 1\nB: x"})
        api.expect(page.locator('#poly-a')).to_have_value('x + 1')
        api.expect(page.locator('#poly-b')).to_have_value('x')
        page.locator('label:has(input[value="add"])').click()
        page.locator('#calculate').click()
        api.expect(page.locator('#result-value')).to_have_text('1')
        page.set_viewport_size({"width": 390, "height": 840})
        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
        browser.close()
