import assert from 'node:assert/strict';
import { writeFile, mkdir } from 'node:fs/promises';
import AxeBuilder from '@axe-core/playwright';
import { launchBrowser } from './browser.mjs';

const url = process.env.SITE_URL || 'http://localhost:4174';
await mkdir('verification', { recursive: true });
const browser = await launchBrowser();
const errors = [];
const report = { url, browser: browser.version(), testedAt: new Date().toISOString(), viewports: [], checks: [] };

async function audit(page, label) {
  const result = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa']).analyze();
  assert.deepEqual(result.violations.map(v => ({ id: v.id, nodes: v.nodes.map(n => n.target) })), [], `${label}: accessibility`);
}

async function noOverflow(page, label) {
  const result = await page.evaluate(() => ({ viewport: innerWidth, content: document.documentElement.scrollWidth }));
  assert.ok(result.content <= result.viewport, `${label}: horizontal overflow ${JSON.stringify(result)}`);
}

try {
  for (const width of [360, 390, 768, 1024, 1440]) {
    const context = await browser.newContext({ viewport: { width, height: 900 }, deviceScaleFactor: 1, hasTouch: width < 768 });
    const page = await context.newPage();
    page.on('pageerror', error => errors.push(error.message));
    page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
    page.on('response', response => { if (response.status() >= 400) errors.push(`${response.status()} ${response.url()}`); });
    await page.goto(url, { waitUntil: 'networkidle' });
    await page.evaluate(() => document.fonts.ready);
    assert.equal(await page.locator('h1').count(), 1);
    assert.ok(await page.locator('.hero-actions').isVisible());
    await noOverflow(page, `${width}: initial`);
    await audit(page, `${width}: initial`);
    await page.screenshot({ path: `verification/hero-${width}.png` });
    await page.screenshot({ path: `verification/page-${width}.png`, fullPage: true });
    await page.getByRole('link', { name: 'Explore the memory', exact: true }).click();
    await page.waitForFunction(() => Math.abs(document.querySelector('#explore').getBoundingClientRect().top - parseInt(getComputedStyle(document.documentElement).scrollPaddingTop)) < 4);
    const anchor = await page.locator('#explore').boundingBox();
    const header = await page.locator('.site-header').boundingBox();
    assert.ok(anchor.y >= header.height, 'Sticky masthead must not cover target');
    assert.equal(await page.locator('#later-note').isVisible(), false);
    await page.locator('#next-step').click();
    assert.ok(await page.locator('#later-note').isVisible());
    assert.ok(await page.locator('#earlier-note').isVisible());
    await page.locator('#next-step').click();
    assert.ok(await page.locator('#result-copy').textContent().then(text => text.includes('September 26')));
    await page.locator('[data-question="change"]').click();
    assert.ok((await page.locator('#result-copy').textContent()).includes('accessibility testing'));
    await page.locator('#next-step').click();
    assert.equal(await page.locator('#source-details').getAttribute('open'), '');
    await page.locator('#earlier-note .source-link').click();
    assert.ok((await page.locator('#sheet-quote').textContent()).includes('September 12'));
    assert.equal(await page.evaluate(() => document.activeElement.id), 'source-sheet');
    await page.locator('#later-source-button').click();
    assert.ok((await page.locator('#sheet-quote').textContent()).includes('September 26'));
    await noOverflow(page, `${width}: expanded demo`);
    await audit(page, `${width}: expanded demo`);
    await page.locator('.walkthrough').screenshot({ path: `verification/demo-${width}.png` });
    await page.locator('#architecture').screenshot({ path: `verification/architecture-${width}.png` });
    await page.locator('#next-step').click();
    assert.equal(await page.locator('#later-note').isVisible(), false);
    assert.equal(await page.locator('#source-details').getAttribute('open'), null);
    assert.equal(await page.locator('.step[aria-current="step"]').count(), 1);
    // Direct navigation is supported without completing previous steps.
    await page.locator('.step[data-step="3"]').click();
    assert.ok(await page.locator('#later-note').isVisible());
    assert.ok((await page.locator('#result-copy').textContent()).includes('September 26'));
    // Native disclosures work by keyboard, and fully expanded content stays in bounds.
    for (const selector of ['.technical-details', '.query-example details', '.install-details']) {
      await page.locator(`${selector} > summary`).focus();
      await page.keyboard.press('Enter');
      assert.equal(await page.locator(selector).getAttribute('open'), '');
    }
    await noOverflow(page, `${width}: expanded technical content`);
    await audit(page, `${width}: expanded technical content`);
    const links = await page.locator('a').evaluateAll(anchors => anchors.map(a => a.getAttribute('href')));
    for (const href of links) {
      assert.ok(href && href !== '#', 'No placeholder link');
      if (href.startsWith('#')) assert.equal(await page.locator(href).count(), 1, `Anchor ${href}`);
      else assert.ok(href.startsWith('https://github.com/LuigiFerronatto/TESSERA'), `Unexpected external destination: ${href}`);
    }
    report.viewports.push({ width, overflow: false, axeViolations: 0, fullJourney: 'pass', disclosures: 'pass' });
    await context.close();
  }

  const context = await browser.newContext({ viewport: { width: 390, height: 844 }, reducedMotion: 'reduce', permissions: ['clipboard-read', 'clipboard-write'] });
  const page = await context.newPage();
  await page.goto(url, { waitUntil: 'networkidle' });
  await page.keyboard.press('Tab');
  assert.equal(await page.evaluate(() => document.activeElement.textContent.trim()), 'Skip to content');
  await page.keyboard.press('Enter');
  await page.locator('.step[data-step="0"]').focus();
  for (let step = 1; step <= 3; step++) {
    await page.keyboard.press('Tab');
    assert.equal(await page.evaluate(() => document.activeElement.dataset.step), String(step));
    await page.keyboard.press('Enter');
    assert.equal(await page.locator('.step[aria-current="step"]').getAttribute('data-step'), String(step));
  }
  assert.equal(await page.evaluate(() => document.getAnimations().filter(a => a.playState === 'running').length), 0);
  assert.equal(await page.evaluate(() => getComputedStyle(document.documentElement).scrollBehavior), 'auto');
  await page.locator('#next-step').focus();
  await page.keyboard.press('Space');
  assert.equal(await page.locator('.step[aria-current="step"]').getAttribute('data-step'), '0');
  await page.locator('.install-details summary').click();
  await page.locator('[data-copy="install-code"]').click();
  assert.equal(await page.evaluate(() => navigator.clipboard.readText()), await page.locator('#install-code').textContent());
  await page.locator('.query-example summary').click();
  await page.locator('[data-copy="query-code"]').click();
  assert.equal(await page.evaluate(() => navigator.clipboard.readText()), await page.locator('#query-code').textContent());
  report.checks.push('Keyboard-only steps, source focus, reset and native disclosures', 'Reduced motion: complete story with zero running animations', 'Both clipboard buttons copy their exact command');
  await context.close();

  const staticContext = await browser.newContext({ javaScriptEnabled: false, viewport: { width: 390, height: 844 } });
  const staticPage = await staticContext.newPage();
  await staticPage.goto(url, { waitUntil: 'networkidle' });
  assert.ok(await staticPage.locator('h1').isVisible());
  assert.ok(await staticPage.getByRole('heading', { name: 'The complete story' }).isVisible());
  assert.ok((await staticPage.locator('.no-script-note').textContent()).includes('September 26'));
  assert.equal(await staticPage.locator('#next-step').isVisible(), false);
  await staticPage.locator('.technical-details summary').click();
  assert.ok(await staticPage.locator('.technical-content').isVisible());
  await noOverflow(staticPage, 'No JavaScript');
  report.checks.push('No JavaScript: crawlable narrative, complete example, native disclosures and working documentation links');
  await staticContext.close();
  assert.deepEqual(errors, [], 'Browser/network errors');
  report.errors = errors;
  report.passed = true;
  await writeFile('verification/browser-results.json', JSON.stringify(report, null, 2) + '\n');
  console.log(JSON.stringify(report, null, 2));
} finally {
  await browser.close();
}
