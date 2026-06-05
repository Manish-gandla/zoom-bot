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

async function sleep(ms) {
  return new Promise(r => setTimeout(r, ms));
}

async function screenshot(page, name) {
  const fp = path.join(SCREENSHOT_DIR, `${BOT_NAME.replace(/\s+/g, '_')}_${name}.png`);
  await page.screenshot({ path: fp, fullPage: false });
  log(`📸 ${name}`);
}

async function clickByText(page, text, timeout = 5000) {
  // Strategy 1: button with text
  try {
    const btn = page.locator(`button:has-text("${text}")`).first();
    await btn.waitFor({ state: 'visible', timeout: 3000 });
    await btn.click({ force: true, timeout: 3000 });
    log(`  ✅ Clicked button: "${text}"`);
    return true;
  } catch (e) {
    // Strategy 2: any element with exact text
    try {
      const el = page.locator(`text="${text}"`).first();
      await el.waitFor({ state: 'visible', timeout: 2000 });
      await el.click({ force: true });
      log(`  ✅ Clicked text: "${text}"`);
      return true;
    } catch (e2) {
      // Strategy 3: any element containing text (case-insensitive)
      try {
        const el = page.getByText(text, { exact: false }).first();
        await el.waitFor({ state: 'visible', timeout: 2000 });
        await el.click({ force: true });
        log(`  ✅ Clicked containing: "${text}"`);
        return true;
      } catch (e3) {
        return false;
      }
    }
  }
}

async function clickBySelector(page, selector, timeout = 5000) {
  try {
    const el = page.locator(selector).first();
    await el.waitFor({ state: 'visible', timeout });
    await el.click({ force: true });
    log(`  ✅ Clicked selector: "${selector}"`);
    return true;
  } catch (e) {
    return false;
  }
}

async function handlePotentialPasscode(page) {
  log('  Checking for passcode input...');
  const passcodeSelectors = [
    'input[type="password"]',
    'input[placeholder*="passcode" i]',
    'input[placeholder*="password" i]',
    'input[id*="passcode" i]',
    'input[id*="password" i]',
    'input[name*="passcode" i]',
    'input[name*="password" i]',
  ];
  for (const sel of passcodeSelectors) {
    try {
      const input = page.locator(sel).first();
      if (await input.isVisible({ timeout: 2000 })) {
        await input.fill(MEETING_PASSWORD || '');
        log(`  ✅ Filled passcode input: ${sel}`);
        // Click the Join/Submit button next to it
        await clickByText(page, 'Join', 3000);
        return true;
      }
    } catch (e) {}
  }
  return false;
}

async function handlePotentialNameInput(page) {
  log('  Checking for name input...');
  const nameSelectors = [
    'input[placeholder*="Name" i]',
    'input[placeholder*="name" i]',
    'input[id*="name" i]',
    'input[name*="name" i]',
    'input[data-testid*="name" i]',
    'input[aria-label*="name" i]',
    'input[aria-label*="Name" i]',
  ];
  for (const sel of nameSelectors) {
    try {
      const input = page.locator(sel).first();
      if (await input.isVisible({ timeout: 2000 })) {
        await input.fill('');
        await input.fill(BOT_NAME);
        log(`  ✅ Filled name: "${BOT_NAME}" via ${sel}`);
        // Check for "Turn off my video" checkbox
        await clickByText(page, 'Turn off my video', 2000);
        await clickByText(page, 'Mute my microphone', 2000);
        return true;
      }
    } catch (e) {}
  }
  return false;
}

async function handleMicCameraDialog(page) {
  log('  Handling mic/camera permission dialog...');
  
  // Check for browser-level permission prompt
  try {
    const dialog = page.locator('div[role="dialog"]').first();
    if (await dialog.isVisible({ timeout: 2000 })) {
      // Try various "continue without" buttons
      const continueTexts = [
        'Continue without microphone and camera',
        'Continue without',
        'continue without',
        'Continue',
        'Skip',
        'Not now',
        'Dismiss',
      ];
      for (const txt of continueTexts) {
        if (await clickByText(page, txt, 2000)) {
          await sleep(3000);
          return true;
        }
      }
      // Try all buttons in the dialog
      const buttons = dialog.locator('button, a, span[role="button"]');
      const count = await buttons.count();
      for (let i = 0; i < count; i++) {
        try {
          await buttons.nth(i).click({ force: true });
          log(`  ✅ Clicked dialog button #${i}`);
          await sleep(3000);
          return true;
        } catch (e) {}
      }
    }
  } catch (e) {}
  return false;
}

async function handleJoinFromBrowser(page) {
  log('Step 1: Find "Join from Browser"...');
  const selectors = [
    'a:has-text("Join from your Browser")',
    'a:has-text("Join from Browser")',
    'button:has-text("Join from your Browser")',
    'button:has-text("Join from Browser")',
    'text=Join from your Browser',
    'text=Join from Browser',
    'a[href*="wc/join"]',
  ];
  for (const sel of selectors) {
    try {
      const el = page.locator(sel).first();
      if (await el.isVisible({ timeout: 2000 })) {
        await el.click({ force: true });
        log(`  ✅ Clicked "Join from Browser"`);
        await sleep(5000);
        return true;
      }
    } catch (e) {}
  }
  log('  ⚠️ No "Join from Browser" found - may already be on meeting page');
  return false;
}

async function handleJoinButton(page) {
  log('Step: Find "Join" button...');
  
  // First fill name if present
  await handlePotentialNameInput(page);
  
  // Fill passcode if present  
  await handlePotentialPasscode(page);
  
  // Try various Join button selectors
  const joinSelectors = [
    'button:has-text("Join")',
    'button#joinBtn',
    '#joinBtn',
    'button[class*="join"]',
    'input[type="submit"]',
    'button[data-testid*="join"]',
    '[data-testid*="join-button"]',
    'button[aria-label*="Join"]',
    '.join-btn',
    'a:has-text("Join")',
    'button:has-text("join")',
  ];
  
  for (const sel of joinSelectors) {
    try {
      const el = page.locator(sel).first();
      if (await el.isVisible({ timeout: 2000 })) {
        await el.click({ force: true });
        log(`  ✅ Clicked Join: "${sel}"`);
        await sleep(5000);
        return true;
      }
    } catch (e) {}
  }
  
  // Final fallback: click any "Join" text
  try {
    await page.getByText('Join', { exact: true }).first().click({ force: true });
    log('  ✅ Clicked Join text (fallback)');
    await sleep(5000);
    return true;
  } catch (e) {
    return false;
  }
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
      '--disable-web-security',
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
  
  // Log console messages from the page
  page.on('console', msg => {
    if (msg.type() === 'error') log(`[PAGE ERROR] ${msg.text()}`);
  });

  try {
    log(`Starting bot: ${BOT_NAME}`);
    
    // Navigate
    await page.goto(MEETING_URL, { waitUntil: 'networkidle', timeout: 60000 });
    await screenshot(page, '00_landed');
    await sleep(5000);

    // Step 1: Join from Browser
    await handleJoinFromBrowser(page);
    await screenshot(page, '01_after_join_browser');
    await sleep(3000);

    // Step 2: Handle any mic/camera dialog
    await handleMicCameraDialog(page);
    await screenshot(page, '02_after_permission');
    await sleep(3000);

    // Step 3: Handle second dialog (if present)
    await handleMicCameraDialog(page);
    await screenshot(page, '03_after_permission2');
    await sleep(3000);

    // Step 4: Handle name/passcode and click Join
    await handleJoinButton(page);
    await screenshot(page, '04_after_join');

    // Wait and check state
    await sleep(10000);
    await screenshot(page, '05_post_join_check');

    // Check if in meeting
    const inMeeting = await checkInMeeting(page);
    
    if (inMeeting) {
      log(`🎉 SUCCESS! ${BOT_NAME} is in the meeting! Staying for ${STAY_DURATION}s`);
      for (let i = 0; i < Math.floor(STAY_DURATION / 300); i++) {
        await sleep(300000);
        await screenshot(page, `staying_${i + 1}`);
      }
    } else {
      log('❌ Not in meeting - staying for debugging');
      await sleep(30000);
    }

  } catch (err) {
    log(`ERROR: ${err.message}`);
    await screenshot(page, 'error');
  } finally {
    await screenshot(page, 'final');
    await page.close();
    await context.close();
    await browser.close();
  }
}

async function checkInMeeting(page) {
  const indicators = [
    'button[aria-label*="Mute" i]',
    'button[aria-label*="Leave" i]',
    'text=Participants',
    'text=Leave Meeting',
    'text=Leave',
    '[class*="in-meeting"]',
    '[class*="meeting-ui"]',
    'text=Waiting for the host',
    'text=waiting for host',
    '[class*="waiting-room"]',
  ];
  for (const sel of indicators) {
    try {
      if (await page.locator(sel).first().isVisible({ timeout: 2000 })) {
        log(`  ✅ In-meeting indicator found: "${sel}"`);
        return true;
      }
    } catch (e) {}
  }
  return false;
}

run().catch(err => { console.error(err); process.exit(1); });
