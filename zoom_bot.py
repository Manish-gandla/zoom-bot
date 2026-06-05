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
BOT1_NAME = "Rahul Sharma"

# Bot 2
BOT2_NAME = "Priya Patel"

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


async def wait_and_click(page, texts, wait_seconds=5, max_attempts=10):
    """Wait for given seconds, then try to click button with matching text."""
    print(f"  Waiting {wait_seconds}s before attempting...")
    await asyncio.sleep(wait_seconds)
    
    for i in range(max_attempts):
        if await click_by_text_js(page, texts):
            print(f"  ✅ Clicked: {texts[0]}")
            return True
        await asyncio.sleep(1)
    print(f"  ⚠️ Could not find: {texts[0]}")
    return False


async def run_single_bot(display_name, duration):
    print(f"\n{'='*50}")
    print(f"STARTING BOT: {display_name}")
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
        await asyncio.sleep(jitter(3.0))

        # Handle cookie popup if present
        await click_by_text_js(page, ["Accept all cookies", "Accept All Cookies", "Accept"])
        await asyncio.sleep(jitter(2.0))

        # =============================================================
        # STEP 1: Wait 5s → Click "Join from Browser"
        # =============================================================
        print(f"\n[STEP 1] 'Join from Browser'")
        await wait_and_click(page, [
            "join from your browser",
            "join from browser",
            "from your browser",
            "browser"
        ], wait_seconds=5)
        await page.screenshot(path=f"1_join_browser_{display_name.replace(' ', '_')}.png")

        # =============================================================
        # STEP 2: Wait 5s → Click "Continue without microphone and camera" (1st)
        # =============================================================
        print(f"\n[STEP 2] First 'Continue without microphone and camera'")
        await wait_and_click(page, [
            "continue without microphone and camera",
            "continue without microphone",
            "continue without camera",
            "continue without",
            "continue",
            "skip",
            "don't allow",
            "block"
        ], wait_seconds=5)
        await page.screenshot(path=f"2_continue1_{display_name.replace(' ', '_')}.png")

        # =============================================================
        # STEP 3: Wait 5s → Click "Continue without microphone and camera" (2nd)
        # =============================================================
        print(f"\n[STEP 3] Second 'Continue without microphone and camera'")
        await wait_and_click(page, [
            "continue without microphone and camera",
            "continue without microphone",
            "continue without camera",
            "continue without",
            "continue",
            "skip",
            "don't allow",
            "block"
        ], wait_seconds=5)
        await page.screenshot(path=f"3_continue2_{display_name.replace(' ', '_')}.png")

        # =============================================================
        # STEP 4: Wait 5s → Click "Join"
        # =============================================================
        print(f"\n[STEP 4] 'Join'")
        await wait_and_click(page, [
            "join",
            "join meeting",
            "join now",
            "enter meeting",
            "join the meeting",
            "enter"
        ], wait_seconds=5)
        await page.screenshot(path=f"4_join_{display_name.replace(' ', '_')}.png")

        # =============================================================
        # Handle audio prompt inside meeting
        # =============================================================
        await asyncio.sleep(jitter(3.0))
        await click_by_text_js(page, [
            "join with computer audio",
            "join audio",
            "listen only",
            "use computer audio"
        ])
        await asyncio.sleep(jitter(2.0))
        await page.screenshot(path=f"5_final_{display_name.replace(' ', '_')}.png")

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
            print(f"\n✅ SUCCESS: {display_name} IS IN THE MEETING!")
        else:
            print(f"\n❌ {display_name} NOT in meeting. URL: {page.url}")

        # =============================================================
        # STAY IN MEETING
        # =============================================================
        print(f"\nStaying for {duration//60} min...")
        start = time.time()
        while time.time() - start < duration:
            await asyncio.sleep(45)
            elapsed = int(time.time() - start)
            if elapsed % 300 < 10:
                print(f"  {elapsed//60}m {elapsed%60}s elapsed")
            if elapsed % 120 < 5:
                try:
                    ok = await page.evaluate("""() => (document.body?.innerText || '').toLowerCase().includes('leave')""")
                    if not ok:
                        break
                except:
                    break

        print(f"Done ✓")
        await browser.close()


async def main():
    global JOIN_URL, BOT1_NAME, BOT2_NAME, DURATION_SECONDS

    if len(sys.argv) >= 2 and sys.argv[1] and sys.argv[1].startswith("http"):
        JOIN_URL = sys.argv[1]

    print("=" * 60)
    print("  ZOOM BOT — FAKE LIVE LIKES")
    print(f"  Bot 1: {BOT1_NAME}")
    print(f"  Bot 2: {BOT2_NAME}")
    print(f"  Duration: {DURATION_SECONDS//60} min each")
    print("=" * 60)

    # Bot 1
    await run_single_bot(BOT1_NAME, DURATION_SECONDS)

    # Bot 2
    await run_single_bot(BOT2_NAME, DURATION_SECONDS)

    print("\n✅ BOTH BOTS COMPLETED SUCCESSFULLY")


if __name__ == "__main__":
    asyncio.run(main())
