const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const MEETING_URL = process.env.MEETING_URL;
const BOT_NAME = process.env.BOT_NAME || 'Bot';
const SCREENSHOT_DIR = path.join(__dirname, 'screenshots');

// Helper: base64 encode name for the ?un= parameter
const b64name = Buffer.from(BOT_NAME).toString('base64');

// Helper: take a screenshot
async function screenshot(page, label) {
  if (!fs.existsSync(SCREENSHOT_DIR)) fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
  const safeName = BOT_NAME.replace(/\s+/g, '_');
  await page.screenshot({ 
    path: path.join(SCREENSHOT_DIR, `${safeName}_${label}.png`),
    fullPage: true 
  });
  console.log(`📸 Screenshot: ${label}`);
}

// Helper: wait for a fixed time
const wait = (ms) => new Promise(r => setTimeout(r, ms));

// Helper: log page text for debugging
async function logPageState(page, label) {
  const text = await page.evaluate(() => document.body.innerText);
  console.log(`\n=== PAGE STATE [${label}] ===`);
  console.log(text.substring(0, 1000));
  console.log('===========================\n');
}

// --- DYNAMIC CLICKING STRATEGY ---
// Instead of following a fixed sequence, we analyze what's on the page
// and click the appropriate button based on what's visible.

const BUTTON_PATTERNS = [
  // Priority order - most specific first
  { text: 'join from browser', type: 'action', label: 'JoinFromBrowser' },
  { text: 'continue without microphone', type: 'action', label: 'ContinueNoMic' },
  { text: 'continue without camera', type: 'action', label: 'ContinueNoCam' },
  { text: 'join', type: 'action', label: 'Join' },
  { text: 'join audio', type: 'action', label: 'JoinAudio' },
  { text: 'join with computer audio', type: 'action', label: 'JoinWithAudio' },
  { text: 'mute', type: 'action', label: 'Mute' },
  { text: 'stop video', type: 'action', label: 'StopVideo' },
  { text: 'turn off microphone', type: 'action', label: 'TurnOffMic' },
  { text: 'turn off camera', type: 'action', label: 'TurnOffCam' },
];

async function findAndClickButton(page, pattern) {
  // Strategy 1: getByRole with name matching
  // Using regex for case-insensitive partial match
  const roleBtn = page.getByRole('button', { name: new RegExp(pattern.text, 'i') });
  const roleCount = await roleBtn.count();
  if (roleCount > 0) {
    const btn = roleBtn.first();
    if (await btn.isVisible()) {
      await btn.click();
      console.log(`✅ Clicked "${pattern.label}" via getByRole (${pattern.text})`);
      return true;
    }
  }

  // Strategy 2: getByText for any element
  const textEl = page.getByText(new RegExp(pattern.text, 'i'));
  const textCount = await textEl.count();
  if (textCount > 0) {
    for (let i = 0; i < textCount; i++) {
      const el = textEl.nth(i);
      if (await el.isVisible()) {
        // Try clicking parent button if this is a span/div inside a button
        await el.click().catch(async () => {
          // If direct click fails, try clicking parent
          const parent = el.locator('..');
          await parent.click().catch(() => {});
        });
        console.log(`✅ Clicked "${pattern.label}" via getByText (${pattern.text})`);
        return true;
      }
    }
  }

  // Strategy 3: page.evaluate - brute force DOM search
  const clicked = await page.evaluate((searchText) => {
    const lower = searchText.toLowerCase();
    
    // Find all clickable elements containing the text
    const selectors = ['button', 'a', 'span[role="button"]', '[onclick]', 
                       '.zm-btn', '.btn', '.join-btn', '.action-button',
                       '[class*="button"]', '[class*="btn"]', '[class*="join"]'];
    
    for (const sel of selectors) {
      const elements = document.querySelectorAll(sel);
      for (const el of elements) {
        const text = (el.textContent || '').toLowerCase().trim();
        if (text.includes(lower)) {
          // Make sure it's visible
          const rect = el.getBoundingClientRect();
          if (rect.width > 0 && rect.height > 0 && rect.top >= 0) {
            el.click();
            return `Clicked element: ${sel} with text: "${el.textContent.trim()}"`;
          }
        }
      }
    }
    
    // Last resort: search any element that contains this text
    const allElements = document.querySelectorAll('*');
    for (const el of allElements) {
      const text = (el.textContent || '').toLowerCase().trim();
      if (text === lower || text.startsWith(lower) || text.includes(lower)) {
        const rect = el.getBoundingClientRect();
        if (rect.width > 0 && rect.height > 0 && rect.top >= 0) {
          // Try the element itself, then its parent
          if (el.tagName === 'BUTTON' || el.tagName === 'A' || el.getAttribute('role') === 'button') {
            el.click();
            return `Clicked element: ${el.tagName} with text: "${el.textContent.trim()}"`;
          }
          // Maybe the parent is the clickable element
          const parent = el.parentElement;
          if (parent && (parent.tagName === 'BUTTON' || parent.tagName === 'A' || parent.getAttribute('role') === 'button')) {
            parent.click();
            return `Clicked parent: ${parent.tagName} with text: "${parent.textContent.trim()}"`;
          }
        }
      }
    }
    return null;
  }, pattern.text);

  if (clicked) {
    console.log(`✅ Clicked "${pattern.label}" via evaluate: ${clicked}`);
    return true;
  }

  return false;
}

async function clickMatchingButton(page) {
  for (const pattern of BUTTON_PATTERNS) {
    const found = await findAndClickButton(page, pattern);
    if (found) return pattern.label;
  }
  return null;
}

async function run() {
  console.log(`\n🚀 Starting bot: ${BOT_NAME}`);
  console.log(`🔗 Meeting URL: ${MEETING_URL.substring(0, 80)}...`);

  // Build URL with name pre-filled (the ?un= parameter is base64 encoded name)
  // This can skip the name entry screen
  let url = MEETING_URL;
  const separator = MEETING_URL.includes('?') ? '&' : '?';
  url = `${MEETING_URL}${separator}prefer=1&un=${b64name}`;

  const browser = await chromium.launch({
    headless: true,
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-dev-shm-usage',
      '--disable-gpu',
      '--disable-infobars',
      '--window-size=1920,1080',
      '--use-fake-ui-for-media-stream',      // Auto-accept mic/camera prompts
      '--use-fake-device-for-media-stream',    // Use fake media devices
      '--disable-blink-features=AutomationControlled',
      '--no-first-run',
      '--disable-extensions',
      '--allow-file-access-from-files',
      '--ignore-certificate-errors',
      '--disable-web-security',
    ],
  });

  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    userAgent: 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    locale: 'en-US',
    timezoneId: 'Asia/Kolkata',
    permissions: ['camera', 'microphone'],
    ignoreHTTPSErrors: true,
  });

  const page = await context.newPage();

  // Monitor console logs from the page
  page.on('console', msg => {
    if (msg.type() === 'error') {
      console.log(`  [PAGE ERROR] ${msg.text()}`);
    }
  });

  // Log network requests for debugging
  page.on('response', response => {
    if (response.status() >= 400) {
      console.log(`  [NET ${response.status()}] ${response.url().substring(0, 100)}`);
    }
  });

  try {
    // Step 1: Navigate to the meeting URL
    console.log(`\n📱 Navigating to meeting...`);
    await page.goto(url, { 
      waitUntil: 'domcontentloaded', 
      timeout: 30000 
    });
    await wait(5000);
    await screenshot(page, '01_initial_load');
    await logPageState(page, 'After load');

    // Step 2-5: Dynamic analysis loop
    // Keep analyzing the page and clicking buttons until we either
    // join the meeting or exhaust our attempts
    let consecutiveNoClicks = 0;
    const MAX_NO_CLICKS = 15;  // Max attempts before giving up
    const MAX_TOTAL_CLICKS = 50;

    for (let attempt = 0; attempt < MAX_TOTAL_CLICKS; attempt++) {
      console.log(`\n--- Analysis attempt ${attempt + 1} ---`);
      await screenshot(page, `state_${String(attempt).padStart(2, '0')}`);
      
      const clicked = await clickMatchingButton(page);
      
      if (clicked) {
        console.log(`  👉 Action taken: ${clicked}, waiting 5s...`);
        consecutiveNoClicks = 0;
        await wait(5000);
        await logPageState(page, `After ${clicked}`);
        
        // Check if we've successfully joined (look for meeting UI indicators)
        const inMeeting = await page.evaluate(() => {
          const text = document.body.innerText.toLowerCase();
          return text.includes('leave') || 
                 text.includes('end meeting') || 
                 text.includes('participants') ||
                 text.includes('chat') ||
                 text.includes('record') ||
                 text.includes('share screen') ||
                 text.includes('security');
        });
        
        if (inMeeting) {
          console.log(`\n🎉 SUCCESS! ${BOT_NAME} has joined the meeting!`);
          await screenshot(page, 'joined_meeting');
          
          // Stay in the meeting for a while (45 minutes)
          console.log('📌 Staying in meeting for 45 minutes...');
          for (let m = 0; m < 45; m++) {
            await wait(60000); // 1 minute
            // Take a screenshot every 5 minutes
            if (m % 5 === 0) {
              await screenshot(page, `in_meeting_${m}m`);
              console.log(`  ⏱ Still in meeting... ${m + 1}m elapsed`);
            }
          }
          
          console.log('✅ Meeting duration complete!');
          break;
        }
      } else {
        consecutiveNoClicks++;
        console.log(`  ⏳ No matching button found (${consecutiveNoClicks}/${MAX_NO_CLICKS})`);
        
        if (consecutiveNoClicks >= MAX_NO_CLICKS) {
          console.log('❌ No progress for too long. Stopping.');
          await screenshot(page, 'stuck_final');
          break;
        }
        
        // Wait and check again
        await wait(3000);
      }
    }

  } catch (error) {
    console.error(`\n❌ Error: ${error.message}`);
    await screenshot(page, 'error_state').catch(() => {});
  } finally {
    await browser.close();
    console.log(`\n🏁 ${BOT_NAME} bot finished.`);
  }
}

run().catch(console.error);
