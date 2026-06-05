import asyncio
import random
import time
import json
import sys
from playwright.async_api import async_playwright

# ============================================================
# CONFIGURATION
# ============================================================

# Zoom meeting link
JOIN_URL = "https://bytexl-in.zoom.us/w/87508297509?tk=Jwab1SSwtXE_pvbtNcHafwa2tqnfgysJfPZP7pS8Cz8.DQkAAAAUX-anJRZYb09MRWd2WFRDU0FwY2ZLY1ZKT2ZBAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA&pwd=wloDbtKaR91Ui2VqKxn9yqIm92pw8c.1"

# Bot 1 details
BOT1_FIRST = "Rahul"
BOT1_LAST = "Sharma"
BOT1_EMAIL = f"rahul.sharma{random.randint(100,999)}@gmail.com"

# Bot 2 details
BOT2_FIRST = "Priya"
BOT2_LAST = "Patel"
BOT2_EMAIL = f"priya.patel{random.randint(100,999)}@gmail.com"

# Duration each bot stays (seconds) — 3600 = 1 hour
DURATION_SECONDS = 3600

# ============================================================
STEALTH_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
try { if (!window.chrome) { Object.defineProperty(window, 'chrome', { get: () => ({ runtime: {}, loadTimes: function() {}, csi: function() {}, app: {} }) }); } } catch(e) {}
Object.defineProperty(navigator, 'plugins', { get: () => [1,2,3,4,5] });
Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
"""

def jitter(base, variance=0.3):
    return base + random.uniform(-variance * base, variance * base)


async def click_by_text(page, text_list):
    """Click any element whose textContent contains one of the given strings."""
    texts_json = json.dumps(text_list)
    return await page.evaluate(f"""() => {{
        const texts = {texts_json};
        const els = document.querySelectorAll('button, a, div[role="button"], span[role="button"], input[type="submit"], input[type="button"]');
        for (const el of els) {{
            const t = (el.textContent || el.value || '').toLowerCase().trim();
            for (const search of texts) {{
                if (t.includes(search.toLowerCase())) {{
                    el.click();
                    return 'clicked: ' + t;
                }}
            }}
        }}
        return 'not-found';
    }}""")


async def fill_inputs_by_order(page, values):
    """Fill all visible empty text inputs in order with given values."""
    filled = 0
    inputs = await page.query_selector_all("input:not([type='hidden']):not([type='checkbox']):not([type='radio']):not([type='submit']):not([type='button'])")
    for inp in inputs:
        if filled >= len(values):
            break
        try:
            current = await inp.input_value()
            if not current:
                await inp.click()
                await asyncio.sleep(random.uniform(0.1, 0.3))
                await inp.fill(values[filled], delay=random.randint(40, 120))
                print(f"    Field {filled+1}: {values[filled]}")
                filled += 1
        except:
            pass
    return filled


async def run_single_bot(first_name, last_name, email, display_name, duration):
    print(f"\n{'='*50}")
    print(f"STARTING BOT: {display_name} ({email})")
    print(f"{'='*50}")

    async with async_playwright() as p:
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
        )

        await context.add_init_script(STEALTH_SCRIPT)
        page = await context.new_page()

        # =============================================================
        # STEP 1: Open Zoom link
        # =============================================================
        print(f"[1] Opening Zoom link...")
        await page.goto(JOIN_URL, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(jitter(5.0))
        await page.screenshot(path=f"01_initial_{first_name}.png")

        # =============================================================
        # STEP 2: Handle Cookie popup if present
        # =============================================================
        print(f"[2] Checking for cookie popup...")
        for text in ["Accept all cookies", "Accept All Cookies", "Accept all", "Accept", "Save", "Confirm"]:
            try:
                btn = await page.query_selector(f"button:has-text('{text}')")
                if btn:
                    await btn.click()
                    print(f"    Accepted cookies: {text}")
                    await asyncio.sleep(jitter(2.0))
                    break
            except:
                pass

        await page.screenshot(path=f"02_cookies_{first_name}.png")

        # =============================================================
        # STEP 3: Fill Registration Form (First Name, Last Name, Email)
        # =============================================================
        print(f"[3] Filling registration form...")
        await asyncio.sleep(jitter(2.0))
        filled = await fill_inputs_by_order(page, [first_name, last_name, email])
        if filled < 3:
            print(f"    Only filled {filled}/3 fields — trying fallback selectors...")
            # Fallback: try by placeholder/aria-label
            for selector, val in [
                ("input[placeholder*='irst'], input[aria-label*='irst'], input[name='firstName']", first_name),
                ("input[placeholder*='ast'], input[aria-label*='ast'], input[name='lastName']", last_name),
                ("input[type='email'], input[placeholder*='email'], input[aria-label*='email'], input[name='email']", email),
            ]:
                try:
                    el = await page.query_selector(selector)
                    if el:
                        curr = await el.input_value()
                        if not curr:
                            await el.click()
                            await asyncio.sleep(0.2)
                            await el.fill(val, delay=random.randint(40, 120))
                            print(f"    Fallback filled: {val}")
                except:
                    pass

        await page.screenshot(path=f"03_form_{first_name}.png")

        # =============================================================
        # STEP 4: Click "Register and Join"
        # =============================================================
        print(f"[4] Clicking Register and Join...")
        for attempt in range(5):
            await asyncio.sleep(jitter(1.5))
            result = await click_by_text(page, ["register and join", "register", "join meeting", "join now", "submit"])
            print(f"    Attempt {attempt+1}: {result}")
            if "clicked" in result:
                break

        await asyncio.sleep(jitter(5.0))
        await page.screenshot(path=f"04_register_{first_name}.png")

        # =============================================================
        # STEP 5: Click "Continue without audio and video"
        # =============================================================
        print(f"[5] Looking for 'Continue without audio and video'...")
        for attempt in range(5):
            await asyncio.sleep(jitter(2.0))
            result = await click_by_text(page, [
                "continue without audio and video",
                "continue without",
                "continue",
                "skip",
                "no thanks"
            ])
            if "clicked" in result:
                print(f"    Attempt {attempt+1}: {result}")
                break
            else:
                print(f"    Attempt {attempt+1}: {result}")

        await asyncio.sleep(jitter(3.0))
        await page.screenshot(path=f"05_continue1_{first_name}.png")

        # =============================================================
        # STEP 6: Click "Join from Browser"
        # =============================================================
        print(f"[6] Looking for 'Join from Browser'...")
        browser_clicked = False
        
        # Method 1: Text search
        for attempt in range(3):
            await asyncio.sleep(jitter(2.0))
            result = await click_by_text(page, [
                "join from your browser",
                "join from browser",
                "from your browser",
                "from browser",
                "browser"
            ])
            if "clicked" in result:
                print(f"    Text search: {result}")
                browser_clicked = True
                break

        # Method 2: Search all links/buttons for "browser"
        if not browser_clicked:
            try:
                all_els = await page.query_selector_all("a, span, div, button")
                for el in all_els:
                    text = await el.text_content()
                    if text and "from your browser" in text.lower():
                        await el.click()
                        print(f"    Found via element scan: {text.strip()[:50]}")
                        browser_clicked = True
                        await asyncio.sleep(jitter(3.0))
                        break
            except:
                pass

        # Method 3: Direct WC URL
        if not browser_clicked:
            try:
                wc_url = "https://bytexl-in.zoom.us/wc/join/87508297509"
                await page.goto(wc_url, wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(jitter(4.0))
                print(f"    Used direct WC URL")
                browser_clicked = True
            except:
                pass

        await page.screenshot(path=f"06_browser_link_{first_name}.png")

        # =============================================================
        # STEP 7: Click "Continue without microphone and camera" (1st time)
        # =============================================================
        print(f"[7] First 'Continue without microphone and camera'...")
        for attempt in range(5):
            await asyncio.sleep(jitter(2.0))
            result = await click_by_text(page, [
                "continue without microphone and camera",
                "continue without microphone",
                "continue without camera",
                "continue without",
                "continue",
                "skip",
                "no thanks",
                "don't allow",
                "block"
            ])
            if "clicked" in result:
                print(f"    Attempt {attempt+1}: {result}")
                break
            else:
                print(f"    Attempt {attempt+1}: {result}")

        await asyncio.sleep(jitter(3.0))
        await page.screenshot(path=f"07_continue2_{first_name}.png")

        # =============================================================
        # STEP 8: Click "Continue without microphone and camera" (2nd time)
        # =============================================================
        print(f"[8] Second 'Continue without microphone and camera'...")
        for attempt in range(5):
            await asyncio.sleep(jitter(2.0))
            result = await click_by_text(page, [
                "continue without microphone and camera",
                "continue without microphone",
                "continue without camera",
                "continue without",
                "continue",
                "skip",
                "no thanks",
                "don't allow",
                "block"
            ])
            if "clicked" in result:
                print(f"    Attempt {attempt+1}: {result}")
                break
            else:
                print(f"    Attempt {attempt+1}: {result}")

        await asyncio.sleep(jitter(3.0))
        await page.screenshot(path=f"08_continue3_{first_name}.png")

        # =============================================================
        # STEP 9: Click "Join"
        # =============================================================
        print(f"[9] Clicking Join...")
        join_clicked = False
        for attempt in range(5):
            await asyncio.sleep(jitter(2.0))
            result = await click_by_text(page, [
                "join", "join meeting", "join now", "enter meeting",
                "join the meeting", "enter", "continue"
            ])
            print(f"    Attempt {attempt+1}: {result}")
            if "clicked" in result:
                join_clicked = True
                break

        await asyncio.sleep(jitter(5.0))
        await page.screenshot(path=f"09_join_{first_name}.png")

        # =============================================================
        # STEP 10: Handle "Join with Computer Audio" inside meeting
        # =============================================================
        print(f"[10] Checking for audio prompt inside meeting...")
        await asyncio.sleep(jitter(3.0))
        await click_by_text(page, [
            "join with computer audio", "join audio", "listen only",
            "use computer audio", "join audio by computer"
        ])

        await asyncio.sleep(jitter(3.0))
        await page.screenshot(path=f"10_final_{first_name}.png")

        # =============================================================
        # STEP 11: Check if in meeting
        # =============================================================
        in_meeting = False
        try:
            check = await page.evaluate("""() => {
                const body = (document.body?.innerText || '').toLowerCase();
                return {
                    leave: body.includes('leave meeting') || body.includes('leave'),
                    participants: body.includes('participants'),
                    footer: document.getElementById('wc-footer') !== null,
                    mute: document.querySelector('[class*="unmute"], [class*="mute"]') !== null
                };
            }""")
            print(f"[11] Status: {check}")
            in_meeting = any(check.values())
        except:
            pass

        if in_meeting:
            print(f"[11] ✅ SUCCESS: IN THE MEETING!")
        else:
            print(f"[11] ❌ NOT in meeting. URL: {page.url}")

        # =============================================================
        # STEP 12: Stay in meeting
        # =============================================================
        print(f"[12] Staying for {duration//60} min...")
        start = time.time()
        while time.time() - start < duration:
            await asyncio.sleep(45)
            elapsed = int(time.time() - start)
            if elapsed % 300 < 10:
                print(f"    {elapsed//60}m {elapsed%60}s elapsed")
            if elapsed % 120 < 5:
                try:
                    ok = await page.evaluate("""() => (document.body?.innerText || '').toLowerCase().includes('leave')""")
                    if not ok:
                        break
                except:
                    break

        print(f"[12] Done ✓")
        await browser.close()


async def main():
    global JOIN_URL, BOT1_FIRST, BOT1_LAST, BOT1_EMAIL
    global BOT2_FIRST, BOT2_LAST, BOT2_EMAIL, DURATION_SECONDS

    if len(sys.argv) >= 2 and sys.argv[1] and sys.argv[1].startswith("http"):
        JOIN_URL = sys.argv[1]

    print("=" * 60)
    print("  ZOOM BOT — FAKE LIVE LIKES")
    print(f"  Bot 1: {BOT1_FIRST} {BOT1_LAST} <{BOT1_EMAIL}>")
    print(f"  Bot 2: {BOT2_FIRST} {BOT2_LAST} <{BOT2_EMAIL}>")
    print(f"  Duration: {DURATION_SECONDS//60} min each")
    print("=" * 60)

    # Run Bot 1
    display1 = f"{BOT1_FIRST} {BOT1_LAST}"
    await run_single_bot(BOT1_FIRST, BOT1_LAST, BOT1_EMAIL, display1, DURATION_SECONDS)

    # Run Bot 2
    display2 = f"{BOT2_FIRST} {BOT2_LAST}"
    await run_single_bot(BOT2_FIRST, BOT2_LAST, BOT2_EMAIL, display2, DURATION_SECONDS)

    print("\n✅ BOTH BOTS COMPLETED SUCCESSFULLY")


if __name__ == "__main__":
    asyncio.run(main())
