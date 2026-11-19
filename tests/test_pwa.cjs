const { chromium } = require('playwright');
const assert = require('assert');
(async () => {
  const browser = await chromium.launchPersistentContext(require('fs').mkdtempSync(require('path').join(require('os').tmpdir(),'plastopil-pwa-')), {channel:'chrome',headless:true,viewport:{width:390,height:844},deviceScaleFactor:2});
  try {
    const page = await browser.newPage();
    await page.goto('http://127.0.0.1:8017/report/new');
    await page.waitForFunction(() => navigator.serviceWorker.controller !== null);
    const manifest = await page.evaluate(async () => (await fetch(document.querySelector('link[rel=manifest]').href)).json());
    assert.equal(manifest.display,'standalone');
    assert.equal(manifest.start_url,'/report/new');
    assert(await page.locator('[data-pwa-install]').isVisible());
    await page.screenshot({path:process.env.PWA_PREVIEW_PATH});
    const cdp = await page.context().newCDPSession(page);
    const result = await cdp.send('Page.getInstallabilityErrors');
    console.log('Installability:', JSON.stringify(result.installabilityErrors));
    assert.equal(result.installabilityErrors.length,0);
    // Test the installed-state UI separately; this simulates the standalone
    // media query without installing anything on the user's computer.
    await page.addInitScript(() => { const nativeMatch = window.matchMedia.bind(window); window.matchMedia = q => q === '(display-mode: standalone)' ? {matches:true} : nativeMatch(q); });
    await page.reload();
    assert(!(await page.locator('[data-pwa-install]').isVisible()));
    await page.screenshot({path:process.env.PWA_STANDALONE_PATH});
    console.log('PWA manifest, service worker, installability and standalone display passed');
  } finally {await browser.close();}
})().catch(e => {console.error(e); process.exit(1);});
