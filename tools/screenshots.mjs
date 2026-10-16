// Dark-mode screenshots of the panel; driven by tools/screenshots.py.
import { createRequire } from "node:module";

const require = createRequire(new URL("../frontend/package.json", import.meta.url));
const puppeteer = require("puppeteer-core");

const { base, tokens, chrome, shots } = JSON.parse(process.argv[2]);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const browser = await puppeteer.launch({ executablePath: chrome, headless: true });
const page = await browser.newPage();
await page.setViewport({ width: 1440, height: 1000, deviceScaleFactor: 2 });
await page.emulateMediaFeatures([{ name: "prefers-color-scheme", value: "dark" }]);

// Log in, collapse the sidebar and pick the dark theme before the app loads.
await page.goto(base + "/auth/authorize");
await page.evaluate((t) => {
  localStorage.setItem("hassTokens", t);
  localStorage.setItem("dockedSidebar", JSON.stringify("auto"));
  localStorage.setItem("selectedTheme", JSON.stringify({ theme: "default", dark: true }));
}, tokens);

for (const shot of shots) {
  await page.goto(base + shot.path, { waitUntil: "networkidle0" });
  await sleep(4000);
  if (shot.edit) {
    await page.evaluate((name) => {
      const find = (root, sel) => {
        const hit = root.querySelector(sel);
        if (hit) return hit;
        for (const el of root.querySelectorAll("*")) {
          const found = el.shadowRoot && find(el.shadowRoot, sel);
          if (found) return found;
        }
        return null;
      };
      const panel = find(document, "paperlessoffline-panel");
      const photo = panel.photos.find((p) => p.name === name);
      if (!photo) throw new Error(`No photo named ${name}`);
      panel.editing = photo;
    }, shot.edit);
    await sleep(5000);
  }
  await page.screenshot({ path: shot.out });
}
await browser.close();
