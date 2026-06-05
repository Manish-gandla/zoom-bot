const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

// Configuration from environment variables
const MEETING_URL = process.env.MEETING_URL;
const BOT_NAME = process.env.BOT_NAME || 'Rahul Sharma';
const MEETING_PASSWORD = process.env.MEETING_PASSWORD || '';
const STAY_DURATION = parseInt(process.env.STAY_DURATION || '3600');
const SCREENSHOT_DIR = process.env.SCREENSHOT_DIR || 'screenshots';

// Ensure screenshot directory exists
if (!fs.existsSync(SCREENSHOT_DIR)) {
  fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
}

function log(msg) {
  const timestamp = new Date().toISOString();
  console.log(`[${timestamp}] [${BOT_NAME}] ${msg}`);
}

async function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function takeScreenshot(page, name) {
  const filePath = path.join(SCREENSHOT_DIR, `${BOT_NAME.replace(/\s+/g, '_')}_${name}.png`);
  await page.screenshot({ path: filePath, fullPage: true });
  log(`Screenshot saved: ${filePath}`);
  return filePath;
}

async function clickButton(page, buttonText, timeout = 15000, waitAfter = 5000) {
  try {
    // Try multiple selector strategies
    const button = page.locator(`button:has-text("${buttonText}")`);
    await button.waitFor({ state: 'visible', timeout });
    await button.scrollIntoViewIfNeeded();
    await button.click({ force: true });
    log(`Clicked button: "${buttonText}"`);
    await sleep(waitAfter);
    return true;
  } catch (e) {
    log(`Could not click "${buttonText}" via button selector: ${e.message}`);
    
    try {
      // Fallback: try span or div with that text
      const el = page.locator(`text="${buttonText}"`).first();
      await el.waitFor({ state: 'visible', timeout: 5000 });
      await el.click({ force: true });
      log(`Clicked text: "${buttonText}" (fallback)`);
      await sleep(waitAfter);
      return true;
    } catch (e2) {
      log(`Fallback also failed for "${buttonText}": ${e2.message}`);
      return false;
    }
  }
}

async function run() {
  const videoPath = path.join(SCREENSHOT_DIR, `${BOT_NAME.replace(/\s+/g, '_')}_recording.webm`);
  
  const browser = await chromium.launch({
    headless: true,
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-dev-shm-usage',
      '--disable-gpu',
      '--mute-audio',
      '--disable-web-security',
      '--disable-features=IsolateOrigins,site-per-process',
      '--no-first-run',
      '--no-default-browser-check',
      '--disable-blink-features=AutomationControlled',
      '--use-fake-ui-for-media-stream',
      '--use-fake-device-for-media-stream',
    ],
  });

  // Create context with video recording
  const context = await browser.newContext({
    viewport: { width: 1280, height: 720 },
    userAgent: 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    locale: 'en-US',
    timezoneId: 'Asia/Kolkata',
    permissions: ['camera', 'microphone'],
    recordVideo: { dir: SCREENSHOT_DIR, size: { width: 1280, height: 720 } },
  });

  const page = await context.newPage();

  try {
    log(`Starting bot for meeting URL`);
    log(`Bot name: ${BOT_NAME}`);
    log(`Stay duration: ${STAY_DURATION}s`);

    // Step 0: Navigate to meeting URL
    log('Navigating to meeting URL...');
    await page.goto(MEETING_URL, { 
      waitUntil: 'networkidle',
      timeout: 60000 
    });
    await takeScreenshot(page, '00_landed');
    await sleep(5000);

    // Step 1: Click "Join from your Browser" / "Join from Browser"
    log('Step 1: Looking for "Join from Browser" link...');
    
    // Multiple possible selectors for the "Join from Browser" link
    const joinFromBrowserSelectors = [
      'a:has-text("Join from your Browser")',
      'a:has-text("Join from Browser")',
      'a:has-text("join from your browser")',
      'button:has-text("Join from your Browser")',
      'button:has-text("Join from Browser")',
      'text=Join from your Browser',
      'text=Join from Browser',
      '#zoom-ui-frame',
      'a[href*="wc/join"]',
      '.join-from-browser',
    ];
    
    let joinFromBrowserClicked = false;
    for (const selector of joinFromBrowserSelectors) {
      try {
        const el = page.locator(selector).first();
        if (await el.isVisible({ timeout: 3000 })) {
          await el.click({ force: true });
          log(`Clicked "Join from Browser" using selector: ${selector}`);
          joinFromBrowserClicked = true;
          break;
        }
      } catch (e) {
        // continue trying
      }
    }
    
    if (!joinFromBrowserClicked) {
      log('Could not find "Join from Browser" - may already be on meeting page');
    }
    
    await takeScreenshot(page, '01_after_join_from_browser');
    await sleep(5000);

    // Step 2: Handle mic/camera permission popup — "Continue without microphone and camera"
    log('Step 2: Handling mic/camera dialog...');
    
    // The permission dialog might be in an iframe or the main page
    // Check main page first
    let dialogHandled = await clickButton(page, 'Continue without microphone and camera', 5000, 5000);
    
    if (!dialogHandled) {
      // Check for any dialog-like element
      try {
        const dialogEls = ['div[role="dialog"]', '.permission-dialog', '[class*="permission"]', '[class*="dialog"]'];
        for (const sel of dialogEls) {
          const els = page.locator(sel);
          const count = await els.count();
          if (count > 0) {
            log(`Found ${count} dialog elements with selector: ${sel}`);
            // Try clicking any button inside
            const btn = els.first().locator('button, a, span').filter({ hasText: /continue|Allow|accept|ok/i }).first();
            if (await btn.isVisible({ timeout: 2000 })) {
              await btn.click({ force: true });
              log('Clicked button inside dialog');
              dialogHandled = true;
              break;
            }
          }
        }
      } catch (e) {
        log(`Error handling dialog: ${e.message}`);
      }
    }
    
    await takeScreenshot(page, '02_after_permission_dialog');
    await sleep(5000);

    // Step 3: Second "Continue without microphone and camera" (the actual join page)
    log('Step 3: Looking for second permission dialog...');
    dialogHandled = await clickButton(page, 'Continue without microphone and camera', 5000, 5000);
    
    // If the exact text doesn't match, try partial match
    if (!dialogHandled) {
      try {
        const btn = page.locator('button').filter({ hasText: /continue without/i }).first();
        if (await btn.isVisible({ timeout: 3000 })) {
          await btn.click({ force: true });
          log('Clicked button matching "continue without" (regex)');
          dialogHandled = true;
        }
      } catch (e) {
        log(`Continue without regex match failed: ${e.message}`);
      }
    }
    
    await takeScreenshot(page, '03_after_second_permission');
    await sleep(5000);

    // Step 4: Click "Join" button
    log('Step 4: Looking for Join button...');
    
    // Check if there's a name input that needs filling
    try {
      const nameInput = page.locator('input[placeholder*="Name"], input[name*="name"], input[id*="name"], input[placeholder*="name"]').first();
      if (await nameInput.isVisible({ timeout: 3000 })) {
        await nameInput.fill('');
        await nameInput.fill(BOT_NAME);
        log(`Filled name input with: ${BOT_NAME}`);
        await sleep(1000);
      }
    } catch (e) {
      log(`No name input found or error: ${e.message}`);
    }
    
    // Try to click Join
    let joinClicked = await clickButton(page, 'Join', 10000, 5000);
    
    if (!joinClicked) {
      // Try multiple Join button selectors
      const joinSelectors = [
        'button#joinBtn',
        'button.join-btn',
        'button[class*="join"]',
        'button:has-text("Join")',
        'a:has-text("Join")',
        'input[type="submit"][value*="Join"]',
        '#joinBtn',
        '[data-testid*="join"]',
        '.meeting-join-btn',
      ];
      
      for (const sel of joinSelectors) {
        try {
          const btn = page.locator(sel).first();
          if (await btn.isVisible({ timeout: 3000 })) {
            await btn.click({ force: true });
            log(`Clicked Join with selector: ${sel}`);
            joinClicked = true;
            break;
          }
        } catch (e) {
          // continue
        }
      }
    }
    
    if (!joinClicked) {
      log('WARNING: Could not find Join button - taking screenshot for debugging');
    }
    
    await takeScreenshot(page, '04_after_join_click');
    await sleep(10000);

    // Check if we successfully joined
    await takeScreenshot(page, '05_post_join_check');
    
    // Look for in-meeting indicators
    const inMeetingIndicators = [
      'button[aria-label*="Mute"]',
      'button[aria-label*="Leave"]',
      'button[aria-label*="Leave Meeting"]',
      '[class*="participant"]',
      '[class*="in-meeting"]',
      '[class*="meeting-ui"]',
      'text=Participants',
      'text=Leave',
    ];
    
    let inMeeting = false;
    for (const sel of inMeetingIndicators) {
      try {
        if (await page.locator(sel).first().isVisible({ timeout: 3000 })) {
          log(`SUCCESS: In-meeting indicator found: ${sel}`);
          inMeeting = true;
          break;
        }
      } catch (e) {}
    }
    
    if (!inMeeting) {
      log('WARNING: No in-meeting indicators found - may not have joined successfully');
      // Check if we're in a waiting room
      try {
        const waitingRoom = page.locator('text=Waiting for the host').first();
        if (await waitingRoom.isVisible({ timeout: 3000 })) {
          log('In waiting room - waiting for host to admit');
          inMeeting = true; // Treat waiting room as "in meeting"
        }
      } catch (e) {}
    }

    if (inMeeting) {
      log(`Bot successfully joined! Staying for ${STAY_DURATION} seconds...`);
      
      // Take periodic screenshots during the stay
      const screenshotInterval = 300; // every 5 minutes
      const totalScreenshots = Math.floor(STAY_DURATION / screenshotInterval);
      
      for (let i = 0; i < totalScreenshots; i++) {
        await sleep(screenshotInterval * 1000);
        await takeScreenshot(page, `06_staying_${i + 1}`);
        log(`Still in meeting... (${((i + 1) * screenshotInterval / 60).toFixed(0)}min elapsed)`);
      }
      
      log('Stay duration completed. Leaving meeting.');
    } else {
      log('Could not confirm meeting join - staying in browser for debugging');
      await sleep(30000); // extra wait for screenshots
    }

  } catch (error) {
    log(`ERROR: ${error.message}`);
    console.error(error.stack);
    await takeScreenshot(page, '99_error_state');
  } finally {
    await takeScreenshot(page, '99_final');
    await page.close();
    await context.close();
    await browser.close();
    log('Bot finished.');
  }
}

run().catch(err => {
  console.error('Fatal error:', err);
  process.exit(1);
});
