import lighthouse from 'lighthouse';
import desktopConfig from 'lighthouse/core/config/desktop-config.js';
import { launch } from 'chrome-launcher';
import { writeFile, readdir, readFile, mkdir } from 'node:fs/promises';
import { gzipSync } from 'node:zlib';
import { chromePath } from './browser.mjs';

const url = process.env.SITE_URL || 'http://localhost:4174';
await mkdir('verification', { recursive: true });
const report = { url, measuredAt: new Date().toISOString(), type: 'Local production build; Lighthouse simulated throttling; not field data', runs: [] };
for (const mode of ['mobile', 'mobile', 'mobile', 'desktop']) {
  const chrome = await launch({ chromePath: chromePath(), chromeFlags: ['--headless', '--no-sandbox', '--disable-dev-shm-usage'] });
  try {
    const result = await lighthouse(url, {
      port: chrome.port,
      output: ['json', 'html'],
      logLevel: 'error',
    }, mode === 'desktop' ? desktopConfig : undefined);
    const { lhr } = result;
    const index = report.runs.length + 1;
    await writeFile(`verification/lighthouse-${mode}-${index}.json`, result.report[0]);
    await writeFile(`verification/lighthouse-${mode}-${index}.html`, result.report[1]);
    const run = {
      mode,
      lighthouseVersion: lhr.lighthouseVersion,
      userAgent: lhr.environment.networkUserAgent,
      scores: Object.fromEntries(Object.entries(lhr.categories).map(([key, value]) => [key, Math.round(value.score * 100)])),
      lcpMs: Math.round(lhr.audits['largest-contentful-paint'].numericValue),
      cls: lhr.audits['cumulative-layout-shift'].numericValue,
      tbtMs: Math.round(lhr.audits['total-blocking-time'].numericValue),
      fcpMs: Math.round(lhr.audits['first-contentful-paint'].numericValue),
      settings: { formFactor: lhr.configSettings.formFactor, screenEmulation: lhr.configSettings.screenEmulation, throttling: lhr.configSettings.throttling, throttlingMethod: lhr.configSettings.throttlingMethod },
      failedAudits: Object.values(lhr.audits).filter(a => a.score !== null && a.score < 1).map(a => ({ id: a.id, title: a.title, score: a.score, displayValue: a.displayValue })),
    };
    report.runs.push(run);
    console.log(JSON.stringify({ mode, scores: run.scores, lcpMs: run.lcpMs, cls: run.cls, tbtMs: run.tbtMs }));
  } finally {
    await chrome.kill();
  }
}
const assets = await readdir('dist/assets');
report.javascriptGzipBytes = 0;
for (const asset of assets.filter(name => name.endsWith('.js'))) report.javascriptGzipBytes += gzipSync(await readFile(`dist/assets/${asset}`)).byteLength;
report.fieldINP = 'Not measured: no deployed real-user traffic.';
await writeFile('verification/performance-results.json', JSON.stringify(report, null, 2) + '\n');
