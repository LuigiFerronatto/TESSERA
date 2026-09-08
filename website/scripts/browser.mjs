import { chromium } from 'playwright';
import { existsSync, readdirSync } from 'node:fs';
import { homedir } from 'node:os';
import { join } from 'node:path';

export function chromePath() {
  if (process.env.CHROME_PATH) return process.env.CHROME_PATH;
  const installed = chromium.executablePath();
  if (existsSync(installed)) return installed;
  // Prefer an already installed local browser; CI can use playwright install chromium.
  const cache = join(homedir(), '.cache/ms-playwright');
  if (existsSync(cache)) {
    for (const entry of readdirSync(cache).filter(name => /^chromium-\d+$/.test(name)).sort().reverse()) {
      const candidate = join(cache, entry, 'chrome-linux64/chrome');
      if (existsSync(candidate)) return candidate;
    }
  }
  throw new Error('Install Chromium with npx playwright install chromium, or set CHROME_PATH.');
}

export async function launchBrowser() {
  return chromium.launch({ executablePath: chromePath(), headless: true, args: ['--no-sandbox'] });
}
