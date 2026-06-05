import asyncio
import random
import time
import json
import sys
from playwright.async_api import async_playwright

# ============================================================
# CONFIGURATION — Edit these values
# ============================================================

# The join link you received after registration
JOIN_URL = "https://bytexl-in.zoom.us/j/xxxxxxxxxx"  # <-- PUT YOUR JOIN LINK HERE

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
    await page.click(selector)
    await asyncio.sleep(random.uniform(0.1, 0.3))
    for char in text:
        await page.keyboard.type(char, delay=random.randint(40, 120))


def jitter(base, variance=0.3):
    return base + random.uniform(-variance * base, variance * base)


async def click_button_by_text(page, text_parts):
    parts_json = json.dumps(text_parts)
    return await page.evaluate(f"""() => {{
        const parts = {parts_json};
        const els = document.querySelectorAll('button, a, div[role="button"]');
        for (const el of els) {{
            const t = el.textContent?.toLowerCase().trim() || '';
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

        # Step 1: Open join link
        print(f"[{display_name}] Opening join link...")
        await page.goto(JOIN_URL, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(jitter(4.0))

        # Step 2: Enter name if prompted
        try:
            name_input = await page.query_selector("input[type='text']")
            if name_input:
                current = await name_input.input_value()
                if not current:
                    await human_type(page, "input[type='text']", display_name)
                    print(f"[{display_name}] Name entered: {display_name}")
                else:
                    print(f"[{display_name}] Name already set: {current}")
        except:
            pass

        # Step 3: Turn OFF video
        await page.evaluate("""() => {
            document.querySelectorAll('button').forEach(b => {
                const t = b.textContent.toLowerCase();
                if (t.includes('turn off') && t.includes('video')) b.click();
            });
            document.querySelectorAll('[class*="toggle"]').forEach(t => {
                const p = t.parentElement?.textContent?.toLowerCase() || '';
                if ((p.includes('video') || p.includes('camera')) && 
                    (t.getAttribute('aria-checked') === 'true' || t.classList.contains('on'))) t.click();
            });
        }""")
        print(f"[{display_name}] Video: OFF")

        # Step 4: Turn OFF audio
        await page.evaluate("""() => {
            document.querySelectorAll('button').forEach(b => {
                const t = b.textContent.toLowerCase();
                if ((t.includes('turn off') && (t.includes('mic') || t.includes('audio'))) ||
                    (b.getAttribute('aria-label') && b.getAttribute('aria-label').toLowerCase().includes('mute'))) b.click();
            });
            document.querySelectorAll('[class*="toggle"]').forEach(t => {
                const p = t.parentElement?.textContent?.toLowerCase() || '';
                if ((p.includes('mic') || p.includes('audio')) && 
                    (t.getAttribute('aria-checked') === 'true' || t.classList.contains('on'))) t.click();
            });
        }""")
        print(f"[{display_name}] Audio: OFF")

        # Step 5: Click Join
        await asyncio.sleep(jitter(2.0))
        result = await click_button_by_text(page, ["join", "join meeting", "join now", "join the meeting"])
        print(f"[{display_name}] Join clicked: {result}")

        # Step 6: Handle launch/zoom dialog
        await asyncio.sleep(jitter(4.0))
        result = await click_button_by_text(page, ["launch meeting", "open zoom", "launch", "open link", "click here"])
        if "clicked" in result:
            print(f"[{display_name}] Launch dialog handled")

        # Step 7: Handle audio prompt inside meeting
        await asyncio.sleep(jitter(4.0))
        result = await click_button_by_text(page, ["join with computer audio", "join audio", "listen only", "join via computer audio"])
        if "clicked" in result:
            print(f"[{display_name}] Audio prompt handled")

        # Step 8: Confirm in meeting
        await asyncio.sleep(jitter(3.0))
        try:
            check = await page.evaluate("""() => {
                const body = (document.body?.innerText || '').toLowerCase();
                return body.includes('leave') || document.getElementById('wc-footer') !== null;
            }""")
            if check:
                print(f"[{display_name}] ✅ SUCCESS: Bot is IN the meeting!")
            else:
                print(f"[{display_name}] ⚠️ Could not confirm — continuing anyway")
                await page.screenshot(path=f"debug_{display_name.replace(' ', '_')}.png")
        except:
            pass

        # Step 9: Stay in meeting (fake view)
        print(f"[{display_name}] 🕒 Staying in meeting for {duration//60} minutes...")
        start = time.time()
        while time.time() - start < duration:
            await asyncio.sleep(random.randint(30, 60))
            elapsed = int(time.time() - start)
            if elapsed % 300 < 10:
                print(f"[{display_name}] In meeting ({elapsed//60}m {elapsed%60}s)")
            if random.random() < 0.15:
                await page.mouse.move(random.randint(500, 1400), random.randint(200, 800), steps=random.randint(5, 12))
            if elapsed % 120 < 5:
                try:
                    ok = await page.evaluate("""() => (document.body?.innerText || '').toLowerCase().includes('leave')""")
                    if not ok:
                        print(f"[{display_name}] ⚠️ Disconnected at {elapsed}s")
                        break
                except:
                    break

        print(f"[{display_name}] ✅ Finished.")
        await page.close()
        await context.close()
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
            print(f"[!] Invalid duration '{sys.argv[4]}', using default: {DURATION_SECONDS}s")

    print("=" * 60)
    print("  ZOOM BOT — FAKE LIVE LIKES")
    print(f"  Bot 1: {BOT1_NAME}")
    print(f"  Bot 2: {BOT2_NAME}")
    print(f"  Each stays: {DURATION_SECONDS//60} minutes")
    print("=" * 60)

    await run_single_bot(BOT1_NAME, DURATION_SECONDS)
    await run_single_bot(BOT2_NAME, DURATION_SECONDS)
    print("\n✅ BOTH BOTS COMPLETED SUCCESSFULLY")


if __name__ == "__main__":
    asyncio.run(main())
