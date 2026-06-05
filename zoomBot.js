const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const MEETING_URL = process.env.MEETING_URL;
const BOT_NAME = process.env.BOT_NAME || 'Rahul Sharma';
const MEETING_PASSWORD = process.env.MEETING_PASSWORD || '';
const STAY_DURATION = parseInt(process.env.STAY_DURATION || '3600');
const SCREENSHOT_DIR = process.env.SCREENSHOT_DIR || 'screenshots';

if (!fs.existsSync(SCREENSHOT_DIR)) {
  fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
}

function log(msg) {
  console.log(`[${new Date().toISOString()}] [${BOT_NAME}] ${msg}`);
}

function sleep(ms) {
  return new Promise(r => setTimeout(r, ms));
}

async function screenshot(page, name) {
  try {
    const fp = path.join(SCREENSHOT_DIR, `${BOT_NAME.replace(/\s+/g, '_')}_${name}.png`);
    await page.screenshot({ path: fp });
  } catch (e) {
    log(`Screenshot failed: ${e.message}`);
  }
}

/**
 * Analyze the current page state and return what buttons/text are visible.
 */
async function analyzePage(page) {
  return await page.evaluate(() => {
    const results = { buttons: [], headings: [], texts: [], inputs: [], dialogs: [] };

    // Collect all visible button text
    document.querySelectorAll('button, a, [role="button"], span[role="button"], input[type="submit"]').forEach(el => {
      if (el.offsetParent !== null) {
        const text = el.innerText?.trim() || el.value?.trim() || el.textContent?.trim() || '';
        if (text) results.buttons.push(text);
      }
    });

    // Collect visible headings
    document.querySelectorAll('h1, h2, h3, h4, [role="heading"]').forEach(el => {
      if (el.offsetParent !== null) {
        const text = el.innerText?.trim() || '';
        if (text) results.headings.push(text);
      }
    });

    // Collect visible text blocks (smaller phrases)
    document.querySelectorAll('p, label, div.zoom-text, span.zoom-text, [class*="message"], [class*="description"]').forEach(el => {
      if (el.offsetParent !== null) {
        const text = el.innerText?.trim() || '';
        if (text && text.length < 200) results.texts.push(text);
      }
    });

    // Collect input placeholders
    document.querySelectorAll('input:not([type="hidden"])').forEach(el => {
      if (el.offsetParent !== null) {
        const placeholder = el.placeholder || '';
        const id = el.id || '';
        const name = el.name || '';
        const type = el.type || '';
        if (placeholder || id || name) results.inputs.push({ placeholder, id, name, type });
      }
    });

    // Check for dialogs/modals
    document.querySelectorAll('[role="dialog"], [role="alertdialog"], .modal, .dialog').forEach(el => {
      if (el.offsetParent !== null) {
        results.dialogs.push(el.innerText?.trim()?.substring(0, 200) || '');
      }
    });

    return results;
  });
}

/**
 * Check if the page has specific text visible (case-insensitive).
 */
async function pageHasText(page, text) {
  try {
    return await page.locator(`:has-text("${text}")`).first().isVisible({ timeout: 2000 });
  } catch {
    return false;
  }
}

/**
 * Click the first visible button that contains the given text.
 */
async function clickVisibleButton(page, text) {
  try {
    // Try getByRole first (only finds visible elements)
    const btn = page.getByRole('button', { name: text, exact: false }).first();
    if (await btn.isVisible({ timeout: 2000 })) {
      await btn.click();
      log(`  ✅ Clicked button: "${text}" (getByRole)`);
      return true;
    }
  } catch {}

  try {
    // Try text locator filtered to visible
    const btn = page.getByText(text, { exact: false }).first();
    if (await btn.isVisible({ timeout: 2000 })) {
      await btn.click({ force: true });
      log(`  ✅ Clicked text: "${text}" (getByText)`);
      return true;
    }
  } catch {}

  try {
    // Fallback: button with has-text
    const btn = page.locator(`button:has-text("${text}")`).first();
    if (await btn.isVisible({ timeout: 2000 })) {
      await btn.click({ force: true });
      log(`  ✅ Clicked button: "${text}" (has-text)`);
      return true;
    }
  } catch {}

  // Last resort: evaluate and click in page context
  try {
    const clicked = await page.evaluate((searchText) => {
      const elements = document.querySelectorAll('button, a, [role="button"], span[role="button"], input[type="submit"]');
      for (const el of elements) {
        if (el.offsetParent !== null) {
          const t = (el.innerText || el.value || el.textContent || '').trim().toLowerCase();
          if (t.includes(searchText.toLowerCase())) {
            el.click();
            return true;
          }
        }
      }
      return false;
    }, text);
    if (clicked) {
      log(`  ✅ Clicked via evaluate: "${text}"`);
      return true;
    }
  } catch {}

  return false;
}

/**
 * Fill the name input if visible.
 */
async function fillNameIfVisible(page) {
  try {
    // Check for any text input that looks like a name field
    const input = page.locator('input[placeholder*="name" i], input[placeholder*="Name" i], input[id*="name" i], input[aria-label*="name" i], input[aria-label*="Name" i]').first();
    if (await input.isVisible({ timeout: 2000 })) {
      await input.fill('');
      await input.fill(BOT_NAME);
      log(`  ✅ Filled name: "${BOT_NAME}"`);
      return true;
    }
  } catch {}
  
  // Check for any visible text input on a join page
  try {
    const inputs = page.locator('input[type="text"]');
    const count = await inputs.count();
    for (let i = 0; i < count; i++) {
      const input = inputs.nth(i);
      if (await input.isVisible()) {
        const ph = await input.getAttribute('placeholder');
        if (!ph || ph.toLowerCase().includes('name') || ph.toLowerCase().includes('your')) {
          await input.fill('');
          await input.fill(BOT_NAME);
          log(`  ✅ Filled name via text input #${i}: "${BOT_NAME}"`);
          return true;
        }
      }
    }
  } catch {}
  
  return false;
}

/**
 * Fill the passcode input if visible.
 */
async function fillPasscodeIfVisible(page) {
  try {
    const input = page.locator('input[type="password"], input[placeholder*="passcode" i], input[placeholder*="password" i]').first();
    if (await input.isVisible({ timeout: 2000 })) {
      await input.fill(MEETING_PASSWORD);
      log(`  ✅ Filled passcode`);
      return true;
    }
  } catch {}
  return false;
}

/**
 * Core logic: Continuously analyze page state and take action.
 * Returns true when we believe we're in the meeting.
 */
async function joinMeeting(page) {
  const MAX_ITERATIONS = 30; // Safety limit
  const BUTTON_PRIORITY = [
    // Highest priority - buttons we want to click
    'Join from your Browser',
    'Join from Browser',
    'join from your browser',
    'Join from browser',
    'Continue without microphone and camera',
    'Continue without',
    'continue without microphone and camera',
    'Join',
    'Join Audio',
    'Join Audio By Computer',
    'Join with Computer Audio',
    'Allow',
    'Allow All',
    'Cancel',
    'Dismiss',
    'Skip',
    'Not now',
  ];

  let iteration = 0;

  while (iteration < MAX_ITERATIONS) {
    iteration++;
    await sleep(2000); // Brief pause between checks

    // 1. Analyze current page state
    const state = await analyzePage(page);
    log(`\n--- Analysis #${iteration} ---`);
    log(`  Buttons visible: [${state.buttons.join(' | ')}]`);
    if (state.headings.length) log(`  Headings: [${state.headings.join(' | ')}]`);
    if (state.texts.length) log(`  Messages: [${state.texts.slice(0, 3).join(' | ')}]`);
    if (state.inputs.length) log(`  Inputs: [${state.inputs.map(i => i.placeholder || i.id || i.name).join(' | ')}]`);

    await screenshot(page, `state_${String(iteration).padStart(2, '0')}`);

    // 2. Check if we're already in the meeting
    if (await pageHasText(page, 'Leave')) {
      log('\n🎉 SUCCESS! Bot appears to be in the meeting!');
      return true;
    }
    if (await pageHasText(page, 'Mute')) {
      log('\n🎉 SUCCESS! Bot appears to be in the meeting (Mute button visible)!');
      return true;
    }
    if (await pageHasText(page, 'Participants')) {
      log('\n🎉 SUCCESS! Bot appears to be in the meeting (Participants visible)!');
      return true;
    }
    if (await pageHasText(page, 'Waiting for the host')) {
      log('\n⏳ Bot is in the waiting room. Waiting for host to admit...');
      return true; // We're as far as we can go
    }
    if (await pageHasText(page, 'waiting for host')) {
      log('\n⏳ Bot is in the waiting room.');
      return true;
    }

    // 3. Fill passcode if present (always do this first)
    await fillPasscodeIfVisible(page);

    // 4. Fill name if present
    await fillNameIfVisible(page);

    // 5. Click buttons based on priority
    let clicked = false;
    for (const btnText of BUTTON_PRIORITY) {
      if (await clickVisibleButton(page, btnText)) {
        clicked = true;
        await sleep(2000);
        break;
      }
    }

    if (!clicked) {
      // If no priority buttons were found, check for any clickable buttons on a Zoom page
      const anyClicked = await page.evaluate(() => {
        const buttons = document.querySelectorAll('button, a, [role="button"]');
        for (const btn of buttons) {
          if (btn.offsetParent !== null && (btn.innerText || '').trim()) {
            btn.click();
            return btn.innerText.trim();
          }
        }
        return null;
      });
      
      if (anyClicked) {
        log(`  ⚠️ Clicked generic button: "${anyClicked}"`);
        await sleep(2000);
      } else {
        log('  ⏳ No clickable buttons found. Waiting...');
        // Check if page is still loading or has an error
        const bodyText = await page.evaluate(() => document.body?.innerText?.substring(0, 500) || '');
        log(`  Page body: ${bodyText.substring(0, 200)}`);
        await sleep(5000);
      }
    }

    // Check for "started a meeting" or redirect to zoom app
    if (await pageHasText(page, 'Open Zoom')) {
      log('  ⚠️ Zoom asking to open desktop app - looking for browser link...');
      await clickVisibleButton(page, 'Join from your Browser');
    }
  }

  log('\n❌ Reached max iterations without joining meeting.');
  return false;
}

async function run() {
  const browser = await chromium.launch({
    headless: true,
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-dev-shm-usage',
      '--disable-gpu',
      '--mute-audio',
      '--disable-blink-features=AutomationControlled',
      '--use-fake-ui-for-media-stream',
      '--use-fake-device-for-media-stream',
    ],
  });

  const context = await browser.newContext({
    viewport: { width: 1280, height: 720 },
    userAgent: 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    locale: 'en-US',
    timezoneId: 'Asia/Kolkata',
    permissions: ['camera', 'microphone'],
    recordVideo: { dir: SCREENSHOT_DIR, size: { width: 1280, height: 720 } },
  });

  const page = await context.newPage();

  // Log page errors
  page.on('pageerror', err => log(`[PAGE ERROR] ${err.message}`));

  try {
    log(`🚀 Starting bot: ${BOT_NAME}`);
    log(`🌐 Navigating to meeting...`);

    await page.goto(MEETING_URL, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await sleep(5000);
    await screenshot(page, 'initial');

    // Run the dynamic join flow
    const joined = await joinMeeting(page);

    if (joined) {
      log(`\n✅ ${BOT_NAME} is connected! Staying for ${STAY_DURATION}s`);
      
      // Take periodic screenshots
      const intervals = Math.floor(STAY_DURATION / 300);
      for (let i = 0; i < intervals; i++) {
        await sleep(300000);
        await screenshot(page, `connected_${i + 1}`);
        log(`Still connected... (${((i + 1) * 5)}min)`);
      }
      
      log('✅ Stay duration complete. Leaving.');
    } else {
      log('\n❌ Could not join meeting. Final screenshots saved.');
      await sleep(15000);
      await screenshot(page, 'failed_final');
      
      // Print final state
      const finalState = await analyzePage(page);
      log(`\n--- Final page state ---`);
      log(`  Buttons: [${finalState.buttons.join(' | ')}]`);
      log(`  Headings: [${finalState.headings.join(' | ')}]`);
    }

  } catch (err) {
    log(`\n💥 FATAL ERROR: ${err.message}`);
    await screenshot(page, 'fatal_error');
  } finally {
    await screenshot(page, 'final');
    await page.close();
    await context.close();
    await browser.close();
    log('🏁 Bot finished.');
  }
}

run().catch(err => {
  console.error('Unhandled:', err);
  process.exit(1);
});
