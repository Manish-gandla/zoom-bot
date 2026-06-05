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


async def human_type(page, selector, text):
    try:
        await page.click(selector)
        await asyncio.sleep(random.uniform(0.1, 0.3))
        for char in text:
            await page.keyboard.type(char, delay=random.randint(40, 120))
    except:
        pass


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
                    return 'clicked: ' + t;
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
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--mute-audio",
                "--window-size=1920,1080",
                # CRITICAL: Fake media devices so Zoom lets us join
                "--use-fake-device-for-media-stream",
                "--use-fake-ui-for-media-stream",
                "--auto-accept-camera-and-microphone-capture",
            ],
        )

        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            locale="en-US",
            timezone_id="Asia/Kolkata",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            # Grant camera and mic permissions
            permissions=["camera", "microphone"],
        )

        await context.add_init_script(STEALTH_SCRIPT)
        page = await context.new_page()

        # ---- Step 1: Open join link ----
        print(f"[{display_name}] Opening join link...")
        try:
            await page.goto(JOIN_URL, wait_until="domcontentloaded", timeout=60000)
        except:
            print(f"[{display_name}] Navigation timeout, continuing...")
        await asyncio.sleep(jitter(5.0))

        # ---- Step 2: Handle "Join from Browser" link if shown ----
        try:
            browser_link = await page.query_selector("a[href*='wc/join'], a:has-text('browser'), a:has-text('web'), a:has-text('click here')")
            if browser_link:
                await browser_link.click()
                print(f"[{display_name}] Clicked browser join link")
                await asyncio.sleep(jitter(4.0))
        except:
            pass

        # ---- Step 3: Wait for meeting lobby page ----
        await asyncio.sleep(jitter(3.0))

        # Take screenshot to see current state
        await page.screenshot(path=f"step1_lobby_{display_name.replace(' ', '_')}.png")

        # ---- Step 4: Set display name ----
        try:
            name_input = await page.wait_for_selector(
                "input[type='text'], input[placeholder*='name'], input[placeholder*='Name'], input[id*='name'], input[aria-label*='name']",
                timeout=15000
            )
            if name_input:
                current = await name_input.input_value()
                if not current:
                    await name_input.click()
                    await asyncio.sleep(0.2)
                    await name_input.fill(display_name, delay=random.randint(40, 120))
                    print(f"[{display_name}] Name set: {display_name}")
                else:
                    print(f"[{display_name}] Name pre-filled: {current}")
            else:
                print(f"[{display_name}] No name input found")
        except:
            print(f"[{display_name}] Name input timeout")
            await page.screenshot(path=f"debug_no_name_{display_name.replace(' ', '_')}.png")

        # ---- Step 5: Turn OFF video ----
        await asyncio.sleep(jitter(1.0))
        await page.evaluate("""() => {
            document.querySelectorAll('button').forEach(b => {
                const t = b.textContent.toLowerCase();
                if (t.includes('turn off') && (t.includes('video') || t.includes('camera'))) b.click();
                if ((b.getAttribute('aria-label') || '').toLowerCase().includes('stop video')) b.click();
            });
            document.querySelectorAll('[class*="toggle"]').forEach(t => {
                const p = (t.parentElement?.textContent || '').toLowerCase();
                if ((p.includes('video') || p.includes('camera')) && 
                    (t.getAttribute('aria-checked') === 'true' || t.classList.contains('on') || 
                     t.getAttribute('aria-pressed') === 'true')) t.click();
            });
        }""")
        print(f"[{display_name}] Video: OFF")

        # ---- Step 6: Turn OFF audio ----
        await asyncio.sleep(jitter(1.0))
        await page.evaluate("""() => {
            document.querySelectorAll('button').forEach(b => {
                const t = b.textContent.toLowerCase();
                if ((t.includes('turn off') && (t.includes('mic') || t.includes('audio'))) ||
                    (b.getAttribute('aria-label') && b.getAttribute('aria-label').toLowerCase().includes('mute'))) b.click();
            });
            document.querySelectorAll('[class*="toggle"]').forEach(t => {
                const p = (t.parentElement?.textContent || '').toLowerCase();
                if ((p.includes('mic') || p.includes('audio')) && 
                    (t.getAttribute('aria-checked') === 'true' || t.classList.contains('on'))) t.click();
            });
        }""")
        print(f"[{display_name}] Audio: OFF")

        # ---- Step 7: Click "Join" or "Join Meeting" button ----
        await asyncio.sleep(jitter(2.0))
        
        # Try multiple button texts
        for attempt in range(3):
            result = await click_button_by_text(page, [
                "join meeting", "join now", "join the meeting", "join", 
                "enter meeting", "continue", "enter"
            ])
            print(f"[{display_name}] Join attempt {attempt+1}: {result}")
            
            if "clicked" in result:
                break
            
            await asyncio.sleep(jitter(2.0))
            
            # Try clicking any button with 'join' in aria-label
            if attempt == 1:
                await page.evaluate("""() => {
                    document.querySelectorAll('button').forEach(b => {
                        const label = (b.getAttribute('aria-label') || '').toLowerCase();
                        if (label.includes('join')) b.click();
                    });
                }""")

        # ---- Step 8: Handle waiting room or in-meeting prompts ----
        await asyncio.sleep(jitter(5.0))
        
        # Handle "Join with Computer Audio" prompt
        audio_result = await click_button_by_text(page, [
            "join with computer audio", "join audio", "listen only", 
            "join via computer audio", "use computer audio"
        ])
        if "clicked" in audio_result:
            print(f"[{display_name}] Audio prompt handled: {audio_result}")

        # Take screenshot to see if we're in the meeting
        await asyncio.sleep(jitter(3.0))
        await page.screenshot(path=f"step2_after_join_{display_name.replace(' ', '_')}.png")

        # ---- Step 9: Confirm in meeting ----
        await asyncio.sleep(jitter(3.0))
        in_meeting = False
        try:
            check = await page.evaluate("""() => {
                const body = (document.body?.innerText || '').toLowerCase();
                return {
                    hasLeave: body.includes('leave meeting') || body.includes('leave'),
                    hasParticipants: body.includes('participants') || body.includes('participant'),
                    hasFooter: document.getElementById('wc-footer') !== null,
                    hasMute: document.querySelector('[class*="mute"]') !== null || document.querySelector('[class*="unmute"]') !== null,
                    hasEndMeeting: body.includes('end meeting')
                };
            }""")
            in_meeting = check.get('hasLeave') or check.get('hasParticipants') or check.get('hasFooter') or check.get('hasMute') or check.get('hasEndMeeting')
            print(f"[{display_name}] Meeting check: {check}")
        except Exception as e:
            print(f"[{display_name}] Check error: {e}")

        if in_meeting:
            print(f"[{display_name}] ✅ SUCCESS: Bot is IN the meeting!")
        else:
            print(f"[{display_name}] ❌ NOT confirmed in meeting. Checking page...")
            try:
                title = await page.title()
                print(f"[{display_name}] Page title: {title}")
                url = page.url
                print(f"[{display_name}] Current URL: {url}")
            except:
                pass

        # ---- Step 10: Stay in meeting ----
        print(f"[{display_name}] 🕒 Staying for {duration//60} minutes...")
        start = time.time()
        last_report = 0
        
        while time.time() - start < duration:
            await asyncio.sleep(random.randint(30, 60))
            elapsed = int(time.time() - start)
            
            # Report every 5 minutes
            if elapsed - last_report >= 300:
                print(f"[{display_name}] In meeting ({elapsed//60}m {elapsed%60}s)")
                last_report = elapsed
            
            # Occasional mouse movement
            if random.random() < 0.15:
                try:
                    await page.mouse.move(random.randint(500, 1400), random.randint(200, 800), steps=random.randint(5, 12))
                except:
                    pass
            
            # Check connection every 2 minutes
            if elapsed % 120 < 10:
                try:
                    ok = await page.evaluate("""() => {
                        const body = (document.body?.innerText || '').toLowerCase();
                        return body.includes('leave') || document.querySelector('[class*="leave"]') !== null;
                    }""")
                    if not ok:
                        print(f"[{display_name}] ⚠️ May have disconnected at {elapsed}s")
                        await page.screenshot(path=f"disconnect_{display_name.replace(' ', '_')}.png")
                        break
                except:
                    print(f"[{display_name}] ⚠️ Page error at {elapsed}s")
                    break

        print(f"[{display_name}] ✅ Finished.")
        await page.close()
        await context.close()
        await browser.close()


async def main():
    global JOIN_URL, BOT1_NAME, BOT2_NAME, DURATION_SECONDS

    if len(sys.argv) >= 2 and sys.argv[1] and (sys.argv[1].startswith("http") or sys.argv[1].startswith("https")):
        JOIN_URL = sys.argv[1]
    if len(sys.argv) >= 3 and sys.argv[2]:
        BOT1_NAME = sys.argv[2]
    if len(sys.argv) >= 4 and sys.argv[3]:
        BOT2_NAME = sys.argv[3]
    if len(sys.argv) >= 5 and sys.argv[4]:
        try:
            DURATION_SECONDS = int(sys.argv[4])
        except ValueError:
            print(f"[!] Invalid duration '{sys.argv[4]}', using default: {DURATION_SECONDS}s")

    print("=" * 60)
    print("  ZOOM BOT — FAKE LIVE LIKES")
    print(f"  Bot 1: {BOT1_NAME}")
    print(f"  Bot 2: {BOT2_NAME}")
    print(f"  Each stays: {DURATION_SECONDS//60} minutes")
    print(f"  Join URL: {JOIN_URL[:80]}...")
    print("=" * 60)

    await run_single_bot(BOT1_NAME, DURATION_SECONDS)
    await run_single_bot(BOT2_NAME, DURATION_SECONDS)
    print("\n✅ BOTH BOTS COMPLETED SUCCESSFULLY")


if __name__ == "__main__":
    asyncio.run(main())
