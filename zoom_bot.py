import asyncio
import random
import time
import json
import sys
import re
from playwright.async_api import async_playwright

# ============================================================
# CONFIGURATION — Edit these values
# ============================================================

# Your actual Zoom join link
JOIN_URL = "https://bytexl-in.zoom.us/w/87508297509?tk=Jwab1SSwtXE_pvbtNcHafwa2tqnfgysJfPZP7pS8Cz8.DQkAAAAUX-anJRZYb09MRWd2WFRDU0FwY2ZLY1ZKT2ZBAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA&pwd=wloDbtKaR91Ui2VqKxn9yqIm92pw8c.1"

# Bot 1 display name
BOT1_NAME = "Rahul Sharma"

# Bot 2 display name
BOT2_NAME = "Priya Patel"

# How long each bot stays (in seconds)
# 3600 = 1 hour, 7200 = 2 hours, 14400 = 4 hours
DURATION_SECONDS = 3600

# ============================================================
# STEALTH ANTI-DETECTION SCRIPT
# ============================================================
STEALTH_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
try { if (!window.chrome) { Object.defineProperty(window, 'chrome', { get: () => ({ runtime: {}, loadTimes: function() {}, csi: function() {}, app: {} }) }); } } catch(e) {}
Object.defineProperty(navigator, 'plugins', { get: () => [1,2,3,4,5] });
Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
"""


def jitter(base, variance=0.3):
    return base + random.uniform(-variance * base, variance * base)


async def click_button_by_text(page, text_parts):
    parts_json = json.dumps(text_parts)
    return await page.evaluate(f"""() => {{
        const parts = {parts_json};
        const els = document.querySelectorAll('button, a, div[role="button"], span[role="button"]');
        for (const el of els) {{
            const t = (el.textContent || '').toLowerCase().trim();
            for (const p of parts) {{
                if (t.includes(p.toLowerCase())) {{
                    el.click();
                    return 'clicked';
                }}
            }}
        }}
        return 'not-found';
    }}""")


async def run_single_bot(display_name, duration):
    print(f"\n{'='*50}")
    print(f"STARTING BOT: {display_name}")
    print(f"{'='*50}")

    async with async_playwright() as p:
        # Use chromium.launch with headless=new and minimal flags
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--mute-audio",
            ],
        )

        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            locale="en-US",
            timezone_id="Asia/Kolkata",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            permissions=["camera", "microphone"],
        )

        await context.add_init_script(STEALTH_SCRIPT)
        page = await context.new_page()

        # ---- Step 1: Open join link ----
        print(f"[{display_name}] Opening join link...")
        try:
            await page.goto(JOIN_URL, wait_until="domcontentloaded", timeout=60000)
        except Exception as e:
            print(f"[{display_name}] Navigation: {e}")
        await asyncio.sleep(jitter(5.0))

        # Take screenshot of initial page
        await page.screenshot(path=f"step1_{display_name.replace(' ', '_')}.png")

        # ---- Step 2: Click "Join from Browser" if shown ----
        try:
            btns = await page.query_selector_all("a, button")
            for btn in btns:
                text = await btn.text_content()
                if text and ("browser" in text.lower() or "web" in text.lower()):
                    await btn.click()
                    print(f"[{display_name}] Clicked browser link")
                    await asyncio.sleep(jitter(3.0))
                    break
        except:
            pass

        # ---- Step 3: Set display name ----
        await asyncio.sleep(jitter(2.0))
        try:
            name_input = await page.wait_for_selector(
                "input[type='text']",
                timeout=10000
            )
            if name_input:
                current = await name_input.input_value()
                if not current:
                    await name_input.click()
                    await asyncio.sleep(0.2)
                    await name_input.fill(display_name)
                    print(f"[{display_name}] Name: {display_name}")
        except:
            print(f"[{display_name}] No name input")

        # ---- Step 4: Turn OFF video ----
        await asyncio.sleep(jitter(1.0))
        await page.evaluate("""() => {
            document.querySelectorAll('button').forEach(b => {
                const t = b.textContent.toLowerCase();
                if (t.includes('turn off') && (t.includes('video') || t.includes('camera'))) b.click();
            });
        }""")
        print(f"[{display_name}] Video: OFF")

        # ---- Step 5: Turn OFF audio ----
        await asyncio.sleep(jitter(1.0))
        await page.evaluate("""() => {
            document.querySelectorAll('button').forEach(b => {
                const t = b.textContent.toLowerCase();
                if ((t.includes('turn off') && (t.includes('mic') || t.includes('audio')))) b.click();
            });
        }""")
        print(f"[{display_name}] Audio: OFF")

        # ---- Step 6: Click Join ----
        await asyncio.sleep(jitter(2.0))
        for attempt in range(3):
            result = await click_button_by_text(page, [
                "join meeting", "join now", "join the meeting", "join",
                "enter meeting", "continue"
            ])
            print(f"[{display_name}] Join attempt {attempt+1}: {result}")
            if "clicked" in result:
                break
            await asyncio.sleep(jitter(2.0))

        # ---- Step 7: Handle audio prompt inside meeting ----
        await asyncio.sleep(jitter(5.0))
        await click_button_by_text(page, [
            "join with computer audio", "join audio", "listen only",
            "use computer audio"
        ])

        # ---- Step 8: Screenshot and check ----
        await asyncio.sleep(jitter(3.0))
        await page.screenshot(path=f"step2_{display_name.replace(' ', '_')}.png")

        in_meeting = False
        try:
            check = await page.evaluate("""() => {
                const body = (document.body?.innerText || '').toLowerCase();
                return body.includes('leave') || document.getElementById('wc-footer') !== null;
            }""")
            in_meeting = check
        except:
            pass

        if in_meeting:
            print(f"[{display_name}] ✅ IN MEETING!")
        else:
            print(f"[{display_name}] ❌ Not in meeting")

        # ---- Step 9: Stay in meeting ----
        print(f"[{display_name}] Staying {duration//60} min...")
        start = time.time()
        last_report = 0
        while time.time() - start < duration:
            await asyncio.sleep(45)
            elapsed = int(time.time() - start)
            if elapsed - last_report >= 300:
                print(f"[{display_name}] {elapsed//60}m elapsed")
                last_report = elapsed
            if elapsed % 120 < 5:
                try:
                    ok = await page.evaluate("""() => (document.body?.innerText || '').toLowerCase().includes('leave')""")
                    if not ok:
                        break
                except:
                    break

        print(f"[{display_name}] Finished")
        await browser.close()


async def main():
    global JOIN_URL, BOT1_NAME, BOT2_NAME, DURATION_SECONDS

    if len(sys.argv) >= 2 and sys.argv[1] and sys.argv[1].startswith("http"):
        JOIN_URL = sys.argv[1]
    if len(sys.argv) >= 3 and sys.argv[2]:
        BOT1_NAME = sys.argv[2]
    if len(sys.argv) >= 4 and sys.argv[3]:
        BOT2_NAME = sys.argv[3]
    if len(sys.argv) >= 5 and sys.argv[4]:
        try:
            DURATION_SECONDS = int(sys.argv[4])
        except ValueError:
            pass

    print("=" * 60)
    print("  ZOOM BOT — FAKE LIVE LIKES")
    print(f"  Bot 1: {BOT1_NAME}")
    print(f"  Bot 2: {BOT2_NAME}")
    print(f"  Duration: {DURATION_SECONDS//60} min each")
    print("=" * 60)

    await run_single_bot(BOT1_NAME, DURATION_SECONDS)
    await run_single_bot(BOT2_NAME, DURATION_SECONDS)
    print("\n✅ BOTH BOTS COMPLETED")


if __name__ == "__main__":
    asyncio.run(main())
