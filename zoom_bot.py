import asyncio
import random
import time
import json
import sys
from playwright.async_api import async_playwright

# ============================================================
# CONFIGURATION
# ============================================================

JOIN_URL = "https://bytexl-in.zoom.us/w/87508297509?tk=Jwab1SSwtXE_pvbtNcHafwa2tqnfgysJfPZP7pS8Cz8.DQkAAAAUX-anJRZYb09MRWd2WFRDU0FwY2ZLY1ZKT2ZBAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA&pwd=wloDbtKaR91Ui2VqKxn9yqIm92pw8c.1"

BOT1_NAME = "Rahul Sharma"
BOT2_NAME = "Priya Patel"
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


async def run_single_bot(display_name, duration):
    print(f"\n{'='*50}")
    print(f"STARTING BOT: {display_name}")
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

        # ---- Step 1: Open link ----
        print(f"[{display_name}] Opening Zoom link...")
        await page.goto(JOIN_URL, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(jitter(5.0))

        # ---- Step 2: ACCEPT COOKIES (critical!) ----
        print(f"[{display_name}] Looking for cookie popup...")
        try:
            # Try clicking "Accept All Cookies" button
            cookie_btn = await page.query_selector("button:has-text('Accept'), button:has-text('Accept All Cookies'), button:has-text('Accept all')")
            if cookie_btn:
                await cookie_btn.click()
                print(f"[{display_name}] ✅ Accepted cookies")
                await asyncio.sleep(jitter(2.0))
            else:
                # Try rejecting/functional only
                reject_btn = await page.query_selector("button:has-text('Reject'), button:has-text('Decline')")
                if reject_btn:
                    await reject_btn.click()
                    print(f"[{display_name}] Rejected cookies")
                    await asyncio.sleep(jitter(2.0))
                else:
                    # Try "Manage Consent Preferences" close
                    save_btn = await page.query_selector("button:has-text('Save'), button:has-text('Confirm')")
                    if save_btn:
                        await save_btn.click()
                        print(f"[{display_name}] Saved cookie preferences")
                        await asyncio.sleep(jitter(2.0))
                    else:
                        print(f"[{display_name}] No cookie popup found")
        except Exception as e:
            print(f"[{display_name}] Cookie handling: {e}")

        await page.screenshot(path=f"1_after_cookies_{display_name.replace(' ', '_')}.png")

        # ---- Step 3: Look for "Join from your Browser" link ----
        print(f"[{display_name}] Looking for 'Join from Browser' link...")
        join_from_browser_clicked = False
        
        try:
            # Common selectors for the browser join link
            browser_link = await page.query_selector(
                "a[href*='wc/join'], a:has-text('browser'), a:has-text('Browser'), "
                "a:has-text('join from your browser'), a:has-text('Join from your browser'), "
                "a:has-text('join from browser'), a:has-text('from your browser'), "
                "span:has-text('Join from your browser'), span:has-text('from your browser'), "
                "div:has-text('Join from your browser')"
            )
            
            if not browser_link:
                # Try finding by searching all links
                all_links = await page.query_selector_all("a")
                for link in all_links:
                    text = await link.text_content()
                    href = await link.get_attribute("href") or ""
                    if text and ("browser" in text.lower() or "from your browser" in text.lower()):
                        browser_link = link
                        break
                    if href and "wc/join" in href:
                        browser_link = link
                        break
            
            if browser_link:
                await browser_link.click()
                print(f"[{display_name}] ✅ Clicked 'Join from your Browser'")
                join_from_browser_clicked = True
                await asyncio.sleep(jitter(5.0))
            else:
                print(f"[{display_name}] No 'Join from Browser' link found. Trying direct...")
                # The page might already be the web client or auto-redirected
                # Try navigating to the WC version directly
                meeting_id = "87508297509"
                wc_url = f"https://bytexl-in.zoom.us/wc/join/{meeting_id}"
                await page.goto(wc_url, wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(jitter(4.0))
                print(f"[{display_name}] Tried direct WC URL")
        except Exception as e:
            print(f"[{display_name}] Browser link error: {e}")

        await page.screenshot(path=f"2_after_browser_link_{display_name.replace(' ', '_')}.png")

        # ---- Step 4: Set display name ----
        print(f"[{display_name}] Looking for name input...")
        try:
            name_input = await page.wait_for_selector(
                "input[type='text'], input[placeholder*='name'], input[placeholder*='Name']",
                timeout=15000
            )
            if name_input:
                current = await name_input.input_value()
                if not current:
                    await name_input.click()
                    await asyncio.sleep(0.2)
                    await name_input.fill(display_name)
                    print(f"[{display_name}] ✅ Name set: {display_name}")
        except:
            print(f"[{display_name}] No name input found")
            await page.screenshot(path=f"2b_no_name_{display_name.replace(' ', '_')}.png")

        # ---- Step 5: Turn OFF video ----
        await asyncio.sleep(jitter(1.0))
        await page.evaluate("""() => {
            document.querySelectorAll('button').forEach(b => {
                const t = b.textContent.toLowerCase();
                if (t.includes('turn off') && (t.includes('video') || t.includes('camera'))) b.click();
                const label = (b.getAttribute('aria-label') || '').toLowerCase();
                if (label.includes('stop video') || label.includes('turn off camera')) b.click();
            });
        }""")
        print(f"[{display_name}] Video: OFF")

        # ---- Step 6: Turn OFF audio ----
        await asyncio.sleep(jitter(1.0))
        await page.evaluate("""() => {
            document.querySelectorAll('button').forEach(b => {
                const t = b.textContent.toLowerCase();
                if ((t.includes('turn off') && (t.includes('mic') || t.includes('audio')))) b.click();
                const label = (b.getAttribute('aria-label') || '').toLowerCase();
                if (label.includes('mute')) b.click();
            });
        }""")
        print(f"[{display_name}] Audio: OFF")

        # ---- Step 7: Click Join button (multiple attempts) ----
        print(f"[{display_name}] Looking for Join button...")
        join_clicked = False
        for attempt in range(5):
            await asyncio.sleep(jitter(2.0))
            
            # Try clicking via text
            result = await page.evaluate("""() => {
                const btns = document.querySelectorAll('button, a, div[role="button"]');
                for (const b of btns) {
                    const t = (b.textContent || '').toLowerCase().trim();
                    if (t.includes('join meeting') || t == 'join' || t.includes('join now') || 
                        t.includes('enter meeting') || t.includes('join the meeting') || t.includes('continue')) {
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
        
        if not join_clicked:
            # Last resort: try clicking any button with 'join' in aria-label
            await page.evaluate("""() => {
                document.querySelectorAll('button').forEach(b => {
                    const label = (b.getAttribute('aria-label') || '').toLowerCase();
                    if (label.includes('join')) b.click();
                });
            }""")
            print(f"[{display_name}] Tried aria-label join buttons")

        # ---- Step 8: Handle audio prompt inside meeting ----
        await asyncio.sleep(jitter(5.0))
        await page.evaluate("""() => {
            document.querySelectorAll('button, div[role="button"]').forEach(b => {
                const t = (b.textContent || '').toLowerCase();
                if (t.includes('join with computer audio') || t.includes('join audio') || 
                    t.includes('listen only') || t.includes('use computer audio') ||
                    t.includes('join audio by computer')) b.click();
            });
        }""")

        await page.screenshot(path=f"3_after_join_{display_name.replace(' ', '_')}.png")

        # ---- Step 9: Check if in meeting ----
        await asyncio.sleep(jitter(4.0))
        in_meeting = False
        try:
            check = await page.evaluate("""() => {
                const body = (document.body?.innerText || '').toLowerCase();
                return {
                    leave: body.includes('leave meeting') || body.includes('leave'),
                    participants: body.includes('participants'),
                    footer: document.getElementById('wc-footer') !== null,
                    mute: document.querySelector('[class*="unmute"]') !== null
                };
            }""")
            print(f"[{display_name}] Status: {check}")
            in_meeting = any(check.values())
        except:
            pass

        if in_meeting:
            print(f"[{display_name}] ✅ SUCCESS: IN THE MEETING!")
        else:
            print(f"[{display_name}] ❌ Not in meeting. Current URL: {page.url}")
            try:
                body_text = await page.text_content("body")
                print(f"[{display_name}] Page text: {body_text[:300]}")
            except:
                pass
            await page.screenshot(path=f"4_failed_{display_name.replace(' ', '_')}.png")

        # ---- Step 10: Stay in meeting ----
        print(f"[{display_name}] Staying for {duration//60} min...")
        start = time.time()
        while time.time() - start < duration:
            await asyncio.sleep(45)
            elapsed = int(time.time() - start)
            if elapsed % 300 < 10:
                print(f"[{display_name}] {elapsed//60}m {elapsed%60}s elapsed")
            if elapsed % 120 < 5 and in_meeting:
                try:
                    ok = await page.evaluate("""() => (document.body?.innerText || '').toLowerCase().includes('leave')""")
                    if not ok:
                        break
                except:
                    break

        print(f"[{display_name}] Done")
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
        except:
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
