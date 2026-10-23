// Browser enforcement checks using the built site's actual page policies.
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert = require('assert/strict');
const BASE = (process.env.SITE_URL || 'http://127.0.0.1:8812').replace(/\/$/, '');
const ONLY = process.env.SECURITY_CASE;
const routes = ['/', '/about/', '/work/targeting-architecture/', '/work/testing-the-fix/', '/work/personal-finance-tools/', '/404.html'];

(async () => {
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  try {
    const context = await browser.newContext();
    await context.addInitScript(() => {
      window.__securityViolations = [];
      addEventListener('securitypolicyviolation', event => {
        window.__securityViolations.push(event.effectiveDirective);
      });
    });
    // Intercept synthetic probes. No probe request reaches a hosted service.
    await context.route('https://security.invalid/**', route => route.fulfill({ status: 204 }));
    const page = await context.newPage();
    for (const route of routes) {
      const response = await page.goto(BASE + route);
      assert.equal(response.status(), 200);
      await page.evaluate(() => document.fonts.ready);
      assert(await page.locator('html').evaluate(el => el.classList.contains('js')), 'approved bootstrap must run');
      assert.deepEqual(await page.evaluate(() => window.__securityViolations), [], 'ordinary page must not violate CSP');
    }

    const checks = {
      inline: async () => {
        await page.evaluate(() => {
          const script = document.createElement('script');
          script.textContent = 'window.__securityInlineMarker = true';
          document.head.append(script);
        });
        await page.waitForFunction(() => window.__securityViolations.includes('script-src-elem'));
        assert.equal(await page.evaluate(() => window.__securityInlineMarker), undefined);
      },
      resources: async () => {
        await page.evaluate(() => {
          const image = new Image();
          image.src = 'https://security.invalid/probe.png';
          document.body.append(image);
        });
        await page.waitForFunction(() => window.__securityViolations.includes('img-src'));
      },
      objects: async () => {
        await page.evaluate(() => {
          const object = document.createElement('object');
          object.type = 'text/html';
          object.data = '/about/';
          document.body.append(object);
        });
        await page.waitForFunction(() => window.__securityViolations.includes('object-src'));
      },
      base: async () => {
        const original = await page.evaluate(() => document.baseURI);
        await page.evaluate(() => {
          const base = document.createElement('base');
          base.href = 'https://security.invalid/';
          document.head.append(base);
        });
        await page.waitForFunction(() => window.__securityViolations.includes('base-uri'));
        assert.equal(await page.evaluate(() => document.baseURI), original);
      },
      referrer: async () => {
        let observed;
        await page.route('**/__security_referrer_probe', route => {
          observed = route.request().headers();
          return route.fulfill({ status: 204 });
        });
        await page.evaluate(() => fetch('/__security_referrer_probe'));
        assert(observed, 'same-origin control request must occur');
        assert.equal(observed.referer, undefined, 'no-referrer must apply even to same-origin requests');
      }
    };
    if (ONLY) assert(Object.hasOwn(checks, ONLY), 'unknown SECURITY_CASE');
    for (const [name, check] of Object.entries(checks)) {
      if (ONLY && ONLY !== name) continue;
      await page.goto(BASE + '/');
      page.setDefaultTimeout(3000);
      await check();
    }
    console.log(JSON.stringify({ passed: true, pages: routes.length, checks: ONLY ? [ONLY] : Object.keys(checks) }));
    await context.close();
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
