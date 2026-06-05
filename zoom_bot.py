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

        # ---- STEP 1: Open Zoom link ----
        print(f"[{display_name}] Opening Zoom link...")
        await page.goto(JOIN_URL, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(jitter(5.0))

        # Take screenshot
        await page.screenshot(path=f"1_initial_{first_name}.png")

        # ---- STEP 2: Handle Cookie popup ----
        print(f"[{display_name}] Handling cookie popup...")
        try:
            # Try multiple cookie button text variations
            for text in ["Accept all cookies", "Accept All Cookies", "Accept", "Accept all", 
                        "Save", "Confirm", "Reject", "Decline"]:
                btn = await page.query_selector(f"button:has-text('{text}')")
                if btn:
                    await btn.click()
                    print(f"[{display_name}] Cookie: {text}")
                    await asyncio.sleep(jitter(2.0))
                    break
        except:
            pass

        await page.screenshot(path=f"2_after_cookies_{first_name}.png")

        # ---- STEP 3: Click "Join from your Browser" ----
        print(f"[{display_name}] Looking for 'Join from your Browser' link...")
        
        # Try multiple approaches to find the browser link
        browser_clicked = False
        
        # Method 1: Direct text match on links and buttons
        for selector in [
            "a:has-text('Join from your Browser')",
            "a:has-text('Join from your browser')",
            "a:has-text('from your browser')",
            "a:has-text('from your Browser')",
            "span:has-text('Join from your Browser')",
            "span:has-text('from your browser')",
            "div:has-text('Join from your Browser')",
            "button:has-text('browser')",
            "a:has-text('browser')",
            "a[href*='wc/join']",
        ]:
            try:
                el = await page.query_selector(selector)
                if el:
                    await el.click()
                    print(f"[{display_name}] Clicked browser link via selector")
                    browser_clicked = True
                    await asyncio.sleep(jitter(4.0))
                    break
            except:
                continue

        # Method 2: Search all elements
        if not browser_clicked:
            try:
                all_els = await page.query_selector_all("a, span, div, button")
                for el in all_els:
                    text = await el.text_content()
                    if text and "from your browser" in text.lower():
                        await el.click()
                        print(f"[{display_name}] Clicked browser link via text search")
                        browser_clicked = True
                        await asyncio.sleep(jitter(4.0))
                        break
            except:
                pass

        # Method 3: Navigate to WC URL directly (fallback)
        if not browser_clicked:
            try:
                wc_url = "https://bytexl-in.zoom.us/wc/join/87508297509"
                await page.goto(wc_url, wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(jitter(4.0))
                print(f"[{display_name}] Used direct WC URL")
            except:
                pass

        await page.screenshot(path=f"3_after_browser_{first_name}.png")

        # ---- STEP 4: Fill Registration Form (First Name, Last Name, Email) ----
        print(f"[{display_name}] Filling registration form...")

        await asyncio.sleep(jitter(2.0))

        # Find all visible text inputs
        inputs = await page.query_selector_all("input:not([type='hidden']):not([type='checkbox']):not([type='radio']):not([type='submit'])")
        
        field_values = [first_name, last_name, email]
        filled_count = 0

        for inp in inputs:
            try:
                current_val = await inp.input_value()
                if not current_val and filled_count < len(field_values):
                    await inp.click()
                    await asyncio.sleep(random.uniform(0.1, 0.3))
                    await inp.fill(field_values[filled_count], delay=random.randint(40, 120))
                    print(f"[{display_name}] Field {filled_count+1}: {field_values[filled_count]}")
                    filled_count += 1
            except:
                pass

        # If the above didn't fill all 3, try by placeholder/type
        if filled_count < 3:
            try:
                for selector, val in [
                    ("input[placeholder*='irst'], input[aria-label*='irst'], input[name='firstName']", first_name),
                    ("input[placeholder*='ast'], input[aria-label*='ast'], input[name='lastName']", last_name),
                    ("input[type='email'], input[placeholder*='email'], input[aria-label*='email'], input[name='email']", email),
                ]:
                    el = await page.query_selector(selector)
                    if el:
                        current = await el.input_value()
                        if not current:
                            await el.click()
                            await asyncio.sleep(0.2)
                            await el.fill(val, delay=random.randint(40, 120))
                            print(f"[{display_name}] Selector fill: {val}")
            except:
                pass

        await page.screenshot(path=f"4_after_form_{first_name}.png")

        # ---- STEP 5: Click "Register and Join" button ----
        print(f"[{display_name}] Clicking Register and Join...")

        register_clicked = False
        for attempt in range(5):
            await asyncio.sleep(jitter(1.5))
            
            result = await page.evaluate("""() => {
                const btns = document.querySelectorAll('button, a, div[role="button"], input[type="submit"]');
                for (const b of btns) {
                    const t = (b.textContent || b.value || '').toLowerCase().trim();
                    if (t.includes('register') || (t.includes('register') && t.includes('join'))) {
                        b.click();
                        return 'clicked: ' + t;
                    }
                }
                return 'not-found';
            }""")
            print(f"[{display_name}] Register attempt {attempt+1}: {result}")
            
            if 'clicked' in result:
                register_clicked = True
                break

        await asyncio.sleep(jitter(5.0))
        await page.screenshot(path=f"5_after_register_{first_name}.png")

        # ---- STEP 6: Continue without Audio and Video ----
        print(f"[{display_name}] Turning off audio/video...")
        
        # Turn off video
        await page.evaluate("""() => {
            document.querySelectorAll('button').forEach(b => {
                const t = b.textContent.toLowerCase();
                if ((t.includes('turn off') && (t.includes('video') || t.includes('camera'))) ||
                    t.includes('stop video') || t.includes('disable video')) b.click();
                const label = (b.getAttribute('aria-label') || '').toLowerCase();
                if (label.includes('stop video') || label.includes('turn off camera')) b.click();
            });
        }""")
        
        await asyncio.sleep(jitter(1.0))
        
        # Turn off audio
        await page.evaluate("""() => {
            document.querySelectorAll('button').forEach(b => {
                const t = b.textContent.toLowerCase();
                if ((t.includes('turn off') && (t.includes('mic') || t.includes('audio'))) ||
                    t.includes('mute') || t.includes('disable mic')) b.click();
                const label = (b.getAttribute('aria-label') || '').toLowerCase();
                if (label.includes('mute') || label.includes('turn off mic')) b.click();
            });
        }""")

        print(f"[{display_name}] Audio/Video: OFF")
        await page.screenshot(path=f"6_after_toggles_{first_name}.png")

        # ---- STEP 7: Click "Join Meeting" ----
        print(f"[{display_name}] Clicking Join Meeting...")

        join_clicked = False
        for attempt in range(5):
            await asyncio.sleep(jitter(2.0))
            
            result = await page.evaluate("""() => {
                const btns = document.querySelectorAll('button, a, div[role="button"], input[type="submit"]');
                for (const b of btns) {
                    const t = (b.textContent || b.value || '').toLowerCase().trim();
                    if (t == 'join' || t.includes('join meeting') || t.includes('join now') || 
                        t.includes('enter meeting') || t.includes('join the meeting') || 
                        t.includes('continue') || t.includes('enter')) {
                        b.click();
                        return 'clicked: ' + t;
                    }
                }
                return 'not-found';
            }""")
            print(f"[{display_name}] Join attempt {attempt+1}: {result}")
            
            if 'clicked' in result:
                join_clicked = True
                break

        await asyncio.sleep(jitter(5.0))
        await page.screenshot(path=f"7_after_join_{first_name}.png")

        # ---- STEP 8: Handle "Join with Computer Audio" prompt (inside meeting) ----
        await asyncio.sleep(jitter(3.0))
        await page.evaluate("""() => {
            document.querySelectorAll('button, div[role="button"]').forEach(b => {
                const t = (b.textContent || '').toLowerCase();
                if (t.includes('join with computer audio') || t.includes('join audio') || 
                    t.includes('listen only') || t.includes('use computer audio') ||
                    t.includes('join audio by computer')) b.click();
            });
        }""")

        await asyncio.sleep(jitter(3.0))
        await page.screenshot(path=f"8_final_{first_name}.png")

        # ---- STEP 9: Check if in meeting ----
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
            print(f"[{display_name}] Status: {check}")
            in_meeting = any(check.values())
        except:
            pass

        if in_meeting:
            print(f"[{display_name}] ✅ SUCCESS: IN THE MEETING!")
        else:
            print(f"[{display_name}] ❌ NOT in meeting. URL: {page.url}")

        # ---- STEP 10: Stay in meeting ----
        print(f"[{display_name}] Staying for {duration//60} min...")
        start = time.time()
        while time.time() - start < duration:
            await asyncio.sleep(45)
            elapsed = int(time.time() - start)
            if elapsed % 300 < 10:
                print(f"[{display_name}] {elapsed//60}m {elapsed%60}s")
            if elapsed % 120 < 5:
                try:
                    ok = await page.evaluate("""() => (document.body?.innerText || '').toLowerCase().includes('leave')""")
                    if not ok:
                        break
                except:
                    break

        print(f"[{display_name}] Done ✓")
        await browser.close()


async def main():
    global JOIN_URL, BOT1_FIRST, BOT1_LAST, BOT1_EMAIL
    global BOT2_FIRST, BOT2_LAST, BOT2_EMAIL, DURATION_SECONDS

    # Override from command line if provided
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
