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


async def click_by_text_js(page, texts):
    """Click any element containing given text using JavaScript."""
    texts_json = str(texts)
    result = await page.evaluate(f"""() => {{
        const texts = {texts_json};
        const allEls = document.querySelectorAll('button, a, div[role="button"], span[role="button"], input[type="submit"], input[type="button"]');
        for (const el of allEls) {{
            const t = (el.textContent || el.value || '').toLowerCase().trim();
            for (const s of texts) {{
                if (t.includes(s.toLowerCase())) {{
                    el.click();
                    return 'clicked';
                }}
            }}
        }}
        return 'not-found';
    }}""")
    return 'clicked' in result


async def click_text_with_wait(page, texts, max_attempts=15):
    """Keep trying to click a button with given text for max_attempts times."""
    for i in range(max_attempts):
        if await click_by_text_js(page, texts):
            print(f"  ✅ Clicked: {texts[0]}")
            return True
        await asyncio.sleep(jitter(1.5))
    print(f"  ⚠️ Not found: {texts[0]}")
    return False


async def fill_form(page, values):
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

        # ---- OPEN LINK ----
        print(f"[1] Opening Zoom link...")
        await page.goto(JOIN_URL, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(jitter(5.0))
        await page.screenshot(path=f"01_{first_name}.png")

        # Handle cookie popup
        await click_text_with_wait(page, ["Accept all cookies", "Accept All Cookies", "Accept"], max_attempts=5)

        # =============================================================
        # STEP 1: Click "Join from Browser"
        # =============================================================
        print(f"[2] Clicking 'Join from Browser'...")
        await click_text_with_wait(page, [
            "join from your browser",
            "join from browser",
            "from your browser",
            "browser"
        ], max_attempts=15)
        await asyncio.sleep(jitter(4.0))
        await page.screenshot(path=f"02_{first_name}.png")

        # =============================================================
        # STEP 2: Fill form (First Name, Last Name, Email)
        # =============================================================
        print(f"[3] Filling form...")
        await asyncio.sleep(jitter(2.0))
        await fill_form(page, [first_name, last_name, email])
        await page.screenshot(path=f"03_{first_name}.png")

        # =============================================================
        # STEP 3: Click "Register and Join"
        # =============================================================
        print(f"[4] Clicking 'Register and Join'...")
        await click_text_with_wait(page, [
            "register and join",
            "register",
            "join meeting",
            "submit",
            "join now"
        ], max_attempts=15)
        await asyncio.sleep(jitter(4.0))
        await page.screenshot(path=f"04_{first_name}.png")

        # =============================================================
        # STEP 4: Click "Continue without audio and video"
        # =============================================================
        print(f"[5] Clicking 'Continue without audio and video'...")
        await click_text_with_wait(page, [
            "continue without audio and video",
            "continue without",
            "continue",
            "skip",
            "no thanks"
        ], max_attempts=15)
        await asyncio.sleep(jitter(3.0))
        await page.screenshot(path=f"05_{first_name}.png")

        # =============================================================
        # STEP 5: Click "Continue without microphone and camera" (1st)
        # =============================================================
        print(f"[6] First 'Continue without microphone and camera'...")
        await click_text_with_wait(page, [
            "continue without microphone and camera",
            "continue without microphone",
            "continue without camera",
            "continue without",
            "continue",
            "skip",
            "don't allow",
            "block"
        ], max_attempts=15)
        await asyncio.sleep(jitter(3.0))
        await page.screenshot(path=f"06_{first_name}.png")

        # =============================================================
        # STEP 6: Click "Continue without microphone and camera" (2nd)
        # =============================================================
        print(f"[7] Second 'Continue without microphone and camera'...")
        await click_text_with_wait(page, [
            "continue without microphone and camera",
            "continue without microphone",
            "continue without camera",
            "continue without",
            "continue",
            "skip",
            "don't allow",
            "block"
        ], max_attempts=15)
        await asyncio.sleep(jitter(3.0))
        await page.screenshot(path=f"07_{first_name}.png")

        # =============================================================
        # STEP 7: Click "Join"
        # =============================================================
        print(f"[8] Clicking 'Join'...")
        await click_text_with_wait(page, [
            "join",
            "join meeting",
            "join now",
            "enter meeting",
            "join the meeting",
            "enter"
        ], max_attempts=15)
        await asyncio.sleep(jitter(5.0))
        await page.screenshot(path=f"08_{first_name}.png")

        # =============================================================
        # Handle audio prompt inside meeting
        # =============================================================
        print(f"[9] Checking for audio prompt...")
        await asyncio.sleep(jitter(3.0))
        await click_text_with_wait(page, [
            "join with computer audio",
            "join audio",
            "listen only",
            "use computer audio"
        ], max_attempts=5)
        await asyncio.sleep(jitter(3.0))
        await page.screenshot(path=f"09_{first_name}.png")

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
