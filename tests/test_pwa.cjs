const { chromium } = require('playwright');
const assert = require('assert');
(async () => {
  const browser = await chromium.launchPersistentContext(require('fs').mkdtempSync(require('path').join(require('os').tmpdir(),'plastopil-pwa-')), {channel:'chrome',headless:true,viewport:{width:390,height:844},deviceScaleFactor:2});
  try {
    const page = await browser.newPage();
    const base = process.env.PWA_TEST_URL || 'http://127.0.0.1:8018';
    await page.goto(base + '/report/new');
    await page.waitForFunction(() => navigator.serviceWorker.controller !== null);
    const manifest = await page.evaluate(async () => (await fetch(document.querySelector('link[rel=manifest]').href)).json());
    assert.equal(manifest.display,'standalone');
    assert.equal(manifest.start_url,'/start');
    assert(await page.locator('[data-pwa-install]').isVisible());
    await page.screenshot({path:process.env.PWA_PREVIEW_PATH});
    const cdp = await page.context().newCDPSession(page);
    const result = await cdp.send('Page.getInstallabilityErrors');
    console.log('Installability:', JSON.stringify(result.installabilityErrors));
    assert.equal(result.installabilityErrors.length,0);
    await page.locator('#reporter-name').fill('עובד בדיקה');
    await page.locator('#reporter-email').fill('worker@example.test');
    await page.locator('#contact-detail').fill('0500000000');
    await page.locator('#save-reporter').click();
    await page.waitForFunction(() => document.querySelector('#identity-panel').hidden);
    await page.reload();
    await page.waitForFunction(() => document.querySelector('#identity-panel').hidden);
    assert((await page.locator('#reporter-display').innerText()).includes('עובד בדיקה'));
    await page.locator('#change-reporter').click();
    assert.equal(await page.locator('#reporter-email').inputValue(),'worker@example.test');
    await page.goto(base + '/start');
    assert(await page.locator('link[rel=manifest]').count());
    await page.goto(base + '/login');
    assert(await page.locator('link[rel=manifest]').count());
    await page.goto(base + '/report/new');
    // Test the installed-state UI separately; this simulates the standalone
    // media query without installing anything on the user's computer.
    await page.addInitScript(() => { const nativeMatch = window.matchMedia.bind(window); window.matchMedia = q => q === '(display-mode: standalone)' ? {matches:true} : nativeMatch(q); });
    await page.reload();
    assert(!(await page.locator('[data-pwa-install]').isVisible()));
    await page.screenshot({path:process.env.PWA_STANDALONE_PATH});
    console.log('PWA manifest, service worker, installability and standalone display passed');
  } finally {await browser.close();}
})().catch(e => {console.error(e); process.exit(1);});
