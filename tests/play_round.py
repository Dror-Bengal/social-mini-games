"""Play a complete real-time round through the rendered controls."""
import argparse
import os
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


def play(url, touch, captures):
    with sync_playwright() as engine:
        browser = engine.chromium.launch(channel=os.getenv("BROWSER_CHANNEL") or None)
        context = browser.new_context(
            viewport={"width": 390 if touch else 1100, "height": 720 if touch else 800},
            has_touch=touch, is_mobile=touch, device_scale_factor=1,
        )
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on("response", lambda r: errors.append(f"{r.status} {r.url}") if r.status >= 400 else None)

        def capture(name):
            if captures:
                captures.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=captures / (name + ".png"))

        def press(button):
            if touch:
                button.tap(timeout=4000)
            else:
                button.click(timeout=4000)

        page.goto(url, wait_until="networkidle")
        start = page.get_by_role("button", name="Start round")
        expect(start).to_be_visible()
        expect(page.locator(".hole")).to_have_count(9)
        assert page.locator("img").evaluate_all("(imgs) => imgs.every(i => i.complete && i.naturalWidth > 0)")
        capture("start")
        press(start)
        expect(page.locator("#speed")).to_have_text("0%")
        # Hit the active hole via the actual mouse/touch device. Never write score or time.
        for score in range(1, 21):
            active = page.locator(".hole:has(.mole.active)").first
            press(active)
            expect(page.locator("#score")).to_have_text(str(score))
            if score == 3:
                page.locator(".mole.active").first.wait_for()
                page.wait_for_timeout(200)
                capture("round")
            if score in (10, 15, 20):
                popup = page.locator(".win-message")
                expect(popup).to_be_visible()
                paused_at = page.locator("#timer").inner_text()
                page.wait_for_timeout(1110)
                expect(page.locator("#timer")).to_have_text(paused_at)
                press(popup.get_by_role("button", name="Continue!"))
                expect(popup).to_have_count(0)

        expect(page.locator("#gameOver")).to_be_visible(timeout=70000)
        expect(page.locator("#timer")).to_have_text("0")
        expect(page.locator("#finalScore")).to_have_text("20")
        expect(page.locator(".mole.active")).to_have_count(0)
        capture("result")
        press(page.get_by_role("button", name="Play again"))
        expect(page.locator("#score")).to_have_text("0")
        expect(page.locator("#timer")).to_have_text("60")
        expect(page.locator("#gameOver")).to_be_hidden()
        press(page.locator(".hole:has(.mole.active)").first)
        expect(page.locator("#score")).to_have_text("1")
        assert not errors, errors
        print("Verified the final score, replay and first hit of the next round.", flush=True)
        context.close()
        browser.close()


if __name__ == "__main__":
    args = argparse.ArgumentParser()
    args.add_argument("--url", default="http://127.0.0.1:18794")
    args.add_argument("--touch", action="store_true")
    args.add_argument("--capture", type=Path)
    options = args.parse_args()
    play(options.url, options.touch, options.capture)
    print("PASS: start, 20 hits, all three milestone pauses, timer expiry, final score, replay")
