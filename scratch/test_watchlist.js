const { chromium } = require('playwright');
const fs = require('fs');

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1440, height: 1200 } });
  await page.goto('http://127.0.0.1:3002/');
  await page.waitForTimeout(1500);

  const setupEl = await page.$('.eval-pane-section:has(.focus-ticker-grid)');
  if (setupEl) {
    await setupEl.screenshot({ path: 'scratch/shots/test_setup_current.png' });
    console.log('Saved scratch/shots/test_setup_current.png');
  } else {
    const wholePage = await page.$('.main-viewport');
    if (wholePage) {
      await wholePage.screenshot({ path: 'scratch/shots/test_whole_page.png' });
      console.log('Saved whole page');
    }
  }

  // Also test mobile 390px
  await page.setViewportSize({ width: 390, height: 844 });
  await page.waitForTimeout(500);
  await page.screenshot({ path: 'scratch/shots/test_mobile_setup.png' });
  console.log('Saved mobile screenshot');

  await browser.close();
})();
