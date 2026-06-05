import asyncio
import random
import time
import sys
from playwright.async_api import async_playwright

# ============================================================
# CONFIGURATION
# ============================================================

JOIN_URL = "https://bytexl-in.zoom.us/w/87508297509?tk=Jwab1SSwtXE_pvbtNcHafwa2tqnfgysJfPZP7pS8Cz8.DQkAAAAUX-anJRZYb09MRWd2WFRDU0FwY2ZLY1ZKT2ZBAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA&pwd=wloDbtKaR91Ui2VqKxn9yqIm92pw8c.1"

# Bot 1
BOT1_FIRST = "Rahul"
BOT1_LAST = "Sharma"
BOT1_EMAIL = f"rahul.sharma{random.randint(100,999)}@gmail.com"

# Bot 2
BOT2_FIRST = "Priya"
BOT2_LAST = "Patel"
BOT2_EMAIL = f"priya.patel{random.randint(100,999)}@gmail.com"

DURATION_SECONDS = 3600  # 1 hour

# ============================================================

STEALTH_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
try { if (!window.chrome) { Object.defineProperty(window, 'chrome', { get: () => ({ runtime: {}, loadTimes: function() {}, csi: function() {}, app: {} }) }); } } catch(e) {}
Object.defineProperty(navigator, 'plugins', { get: () => [1,2,3,4,5] });
Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
"""

def jitter(base, variance=0.3):
    return base + random.uniform(-variance * base, variance * base)


async def click_text(page, texts, timeout=10):
    """
    Wait for an element containing any of the given texts, then click it.
    Returns True if clicked, False if not found within timeout seconds.
    """
    for text in texts:
        try:
            # Try button
            btn = await page.wait_for_selector(f"button:has-text('{text}')", timeout=timeout * 1000)
            if btn:
                await btn.click()
                print(f"  ✅ Clicked: '{text}'")
                return True
        except:
            pass
        try:
            # Try anchor/div/span
            el = await page.wait_for_selector(f"a:has-text('{text}'), div[role='button']:has-text('{text}'), span:has-text('{text}')", timeout=timeout * 1000)
            if el:
                await el.click()
                print(f"  ✅ Clicked: '{text}'")
                return True
        except:
            pass
    return False


async def click_button_evaluate(page, text_parts):
    """Click using JavaScript evaluate for more reliability."""
    parts_json = str(text_parts)
    result = await page.evaluate(f"""() => {{
        const parts = {parts_json};
        const allEls = document.querySelectorAll('button, a, div[role="button"], span[role="button"], input[type="submit"], input[type="button"]');
        for (const el of allEls) {{
            const t = (el.textContent || el.value || '').toLowerCase().trim();
            for (const p of parts) {{
                if (t.includes(p.toLowerCase())) {{
                    el.click();
                    return 'clicked';
                }}
            }}
        }}
        return 'not-found';
    }}""")
    if result == 'clicked':
        print(f"  ✅ Clicked via JS: {text_parts[0]}...")
        return True
    return False


async def fill_form_fields(page, values):
    """Fill visible text inputs in order."""
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
                print(f"  ✅ Filled: {values[filled]}")
                filled += 1
        except:
            pass
    
    # Fallback for remaining fields
    if filled < len(values):
        remaining = values[filled:]
        for selector, val in [
            ("input[placeholder*='irst'], input[aria-label*='irst'], input[name='firstName']", remaining[0] if len(remaining) > 0 else None),
            ("input[placeholder*='ast'], input[aria-label*='ast'], input[name='lastName']", remaining[1] if len(remaining) > 1 else None),
            ("input[type='email'], input[placeholder*='email'], input[aria-label*='email'], input[name='email']", remaining[2] if len(remaining) > 2 else None),
        ]:
            if val:
                try:
                    el = await page.query_selector(selector)
                    if el:
                        curr = await el.input_value()
                        if not curr:
                            await el.click()
                            await asyncio.sleep(0.2)
                            await el.fill(val, delay=random.randint(40, 120))
                            print(f"  ✅ Filled (fallback): {val}")
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
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage", "--disable-gpu", "--mute-audio"],
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
        # OPEN LINK
        # =============================================================
        print(f"[1] Opening Zoom link...")
        await page.goto(JOIN_URL, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(jitter(5.0))
        await page.screenshot(path=f"01_{first_name}.png")

        # Handle cookie popup if present
        await click_text(page, ["Accept all cookies", "Accept All Cookies", "Accept all", "Accept"], timeout=3)
        await asyncio.sleep(jitter(2.0))

        # =============================================================
        # STEP 1: Fill form (First Name, Last Name, Email)
        # =============================================================
        print(f"[2] Filling form: First Name, Last Name, Email...")
        await asyncio.sleep(jitter(2.0))
        await fill_form_fields(page, [first_name, last_name, email])

        # =============================================================
        # STEP 2: Click "Register and Join"
        # =============================================================
        print(f"[3] Looking for 'Register and Join'...")
        await asyncio.sleep(jitter(1.0))
        for attempt in range(10):
            found = await click_button_evaluate(page, ["register and join", "register", "join meeting", "submit", "join now"])
            if found:
                break
            await asyncio.sleep(jitter(1.5))
        await asyncio.sleep(jitter(4.0))

        # =============================================================
        # STEP 3: Click "Continue without audio and video"
        # =============================================================
        print(f"[4] Looking for 'Continue without audio and video'...")
        for attempt in range(10):
            found = await click_button_evaluate(page, [
                "continue without audio and video",
                "continue without",
                "continue",
                "skip",
                "no thanks",
                "don't connect audio"
            ])
            if found:
                break
            await asyncio.sleep(jitter(1.5))
        await asyncio.sleep(jitter(3.0))

        # =============================================================
        # STEP 4: Click "Join from Browser"
        # =============================================================
        print(f"[5] Looking for 'Join from Browser'...")
        
        # Try text-based click first
        browser_found = False
        for attempt in range(10):
            found = await click_button_evaluate(page, [
                "join from your browser",
                "join from browser",
                "from your browser",
                "browser"
            ])
            if found:
                browser_found = True
                break
            # Also try clicking any link containing "browser"
            try:
                link = await page.query_selector("a:has-text('browser'), a:has-text('Browser')")
                if link:
                    await link.click()
                    print(f"  ✅ Clicked browser link (direct)")
                    browser_found = True
                    break
            except:
                pass
            await asyncio.sleep(jitter(1.5))
        
        if not browser_found:
            # Fallback: go to WC URL directly
            try:
                wc_url = "https://bytexl-in.zoom.us/wc/join/87508297509"
                await page.goto(wc_url, wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(jitter(4.0))
                print(f"  Used direct WC URL (fallback)")
            except:
                pass
        
        await asyncio.sleep(jitter(3.0))

        # =============================================================
        # STEP 5: Click "Continue without microphone and camera" (1st)
        # =============================================================
        print(f"[6] First 'Continue without microphone and camera'...")
        for attempt in range(10):
            found = await click_button_evaluate(page, [
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
            if found:
                break
            await asyncio.sleep(jitter(1.5))
        await asyncio.sleep(jitter(3.0))

        # =============================================================
        # STEP 6: Click "Continue without microphone and camera" (2nd)
        # =============================================================
        print(f"[7] Second 'Continue without microphone and camera'...")
        for attempt in range(10):
            found = await click_button_evaluate(page, [
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
            if found:
                break
            await asyncio.sleep(jitter(1.5))
        await asyncio.sleep(jitter(3.0))

        # =============================================================
        # STEP 7: Click "Join"
        # =============================================================
        print(f"[8] Looking for 'Join'...")
        for attempt in range(10):
            found = await click_button_evaluate(page, [
                "join",
                "join meeting",
                "join now",
                "enter meeting",
                "join the meeting",
                "enter"
            ])
            if found:
                break
            await asyncio.sleep(jitter(1.5))
        
        await asyncio.sleep(jitter(5.0))

        # Handle "Join with Computer Audio" inside meeting
        print(f"[9] Checking for audio prompt...")
        await asyncio.sleep(jitter(3.0))
        await click_button_evaluate(page, [
            "join with computer audio", "join audio", "listen only",
            "use computer audio", "join audio by computer"
        ])
        await asyncio.sleep(jitter(3.0))

        # =============================================================
        # CHECK IF IN MEETING
        # =============================================================
        in_meeting = False
        try:
            check = await page.evaluate("""() => {
                const body = (document.body?.innerText || '').toLowerCase();
                return body.includes('leave meeting') || body.includes('leave') || 
                       document.getElementById('wc-footer') !== null ||
                       document.querySelector('[class*="unmute"], [class*="mute"]') !== null;
            }""")
            in_meeting = check
        except:
            pass

        if in_meeting:
            print(f"[10] ✅ SUCCESS: IN THE MEETING!")
        else:
            print(f"[10] ❌ NOT in meeting. URL: {page.url}")

        await page.screenshot(path=f"10_final_{first_name}.png")

        # =============================================================
        # STAY IN MEETING
        # =============================================================
        print(f"[11] Staying for {duration//60} min...")
        start = time.time()
        while time.time() - start < duration:
            await asyncio.sleep(45)
            elapsed = int(time.time() - start)
            if elapsed % 300 < 10:
                print(f"    {elapsed//60}m {elapsed%60}s")
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

    # Bot 1
    display1 = f"{BOT1_FIRST} {BOT1_LAST}"
    await run_single_bot(BOT1_FIRST, BOT1_LAST, BOT1_EMAIL, display1, DURATION_SECONDS)

    # Bot 2
    display2 = f"{BOT2_FIRST} {BOT2_LAST}"
    await run_single_bot(BOT2_FIRST, BOT2_LAST, BOT2_EMAIL, display2, DURATION_SECONDS)

    print("\n✅ BOTH BOTS COMPLETED SUCCESSFULLY")


if __name__ == "__main__":
    asyncio.run(main())
