// Interaction smoke test against the mock harness (run the dev server first).
import puppeteer from "puppeteer-core";

const CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const BASE = "http://localhost:5199/";
const browser = await puppeteer.launch({ executablePath: CHROME, headless: true });
const page = await browser.newPage();
await page.setViewport({ width: 1400, height: 1000 });
const failures = [];
const check = (cond, msg) => { console.log(cond ? "ok  " : "FAIL", msg); if (!cond) failures.push(msg); };
const ws = () => page.evaluate(() => window.__ws ?? []);

// 1. Editor: drag a crop, click a focal point, change dithering, save.
await page.goto(`${BASE}?frame=kitchen&edit=0`);
await new Promise((r) => setTimeout(r, 1500));
const img = await page.evaluateHandle(() =>
  document.querySelector("paperlessoffline-panel").shadowRoot.querySelector("pp-photo-editor")
    .shadowRoot.querySelector("pp-crop-area").shadowRoot.querySelector("img"));
const box = await img.boundingBox();
await page.mouse.move(box.x + box.width * 0.2, box.y + box.height * 0.1);
await page.mouse.down();
await page.mouse.move(box.x + box.width * 0.5, box.y + box.height * 0.9, { steps: 8 });
await page.mouse.up();
await page.mouse.click(box.x + box.width * 0.3, box.y + box.height * 0.5);
await page.evaluate(() => {
  const editor = document.querySelector("paperlessoffline-panel").shadowRoot.querySelector("pp-photo-editor");
  const form = editor.shadowRoot.querySelector("pp-render-settings");
  const rows = form.shadowRoot.querySelectorAll(".row");
  // Uncheck "Default" for dithering, then pick Atkinson.
  const cb = rows[0].querySelector("input[type=checkbox]");
  cb.click();
});
await new Promise((r) => setTimeout(r, 200));
await page.evaluate(() => {
  const editor = document.querySelector("paperlessoffline-panel").shadowRoot.querySelector("pp-photo-editor");
  const sel = editor.shadowRoot.querySelector("pp-render-settings").shadowRoot.querySelectorAll(".row")[0].querySelector("select");
  sel.value = "atkinson";
  sel.dispatchEvent(new Event("change"));
});
await new Promise((r) => setTimeout(r, 800));
const previews = (await ws()).filter((m) => m.type === "paperlessoffline/preview");
check(previews.length >= 2, `live preview re-rendered (${previews.length} requests)`);
await page.evaluate(() => {
  const editor = document.querySelector("paperlessoffline-panel").shadowRoot.querySelector("pp-photo-editor");
  editor.shadowRoot.querySelector("button.primary").click();
});
await new Promise((r) => setTimeout(r, 400));
const update = (await ws()).find((m) => m.type === "paperlessoffline/photo/update");
check(!!update, "save sent photo/update");
const ov = update?.overrides ?? {};
check(Array.isArray(ov.crop) && ov.crop.length === 4, `crop saved ${JSON.stringify(ov.crop)}`);
if (ov.crop) {
  const [, , cw, ch] = ov.crop;
  // Locked to the 480x800 portrait canvas: w/h in pixels = 0.6 (image is 1280x860).
  const ratio = (cw * 1280) / (ch * 860);
  check(Math.abs(ratio - 0.6) < 0.02, `crop locked to frame aspect (ratio ${ratio.toFixed(3)})`);
}
check(typeof ov.focal_x === "number" && ov.focal_x > 0 && ov.focal_x < 1, `focal point saved (${ov.focal_x}, ${ov.focal_y})`);
check(ov.dither === "atkinson", `dither override saved (${ov.dither})`);
const closed = await page.evaluate(() => !document.querySelector("paperlessoffline-panel").shadowRoot.querySelector("pp-photo-editor"));
check(closed, "editor closed after save");

// 2. Library: drag-reorder sends the new order.
await page.goto(`${BASE}?frame=kitchen`);
await new Promise((r) => setTimeout(r, 1500));
await page.evaluate(() => {
  const lib = document.querySelector("paperlessoffline-panel").shadowRoot.querySelector("pp-library");
  const tiles = lib.shadowRoot.querySelectorAll(".tile");
  const dt = new DataTransfer();
  tiles[3].dispatchEvent(new DragEvent("dragstart", { dataTransfer: dt, bubbles: true }));
  tiles[0].dispatchEvent(new DragEvent("dragover", { dataTransfer: dt, bubbles: true, cancelable: true }));
  tiles[0].dispatchEvent(new DragEvent("drop", { dataTransfer: dt, bubbles: true, cancelable: true }));
});
await new Promise((r) => setTimeout(r, 300));
const reorder = (await ws()).find((m) => m.type === "paperlessoffline/photo/reorder");
check(reorder?.order?.[0] === "pkitchen3", `reorder moved photo to front (${reorder?.order?.slice(0, 3)})`);

// 3. Toggle rotation via the eye button.
await page.evaluate(() => {
  const lib = document.querySelector("paperlessoffline-panel").shadowRoot.querySelector("pp-library");
  lib.shadowRoot.querySelectorAll(".tile .icon-btn")[1].click();
});
await new Promise((r) => setTimeout(r, 300));
const toggle = (await ws()).filter((m) => m.type === "paperlessoffline/photo/update").pop();
check(toggle?.enabled === false, "eye button disables photo");

// 4. Global defaults: change saturation and save.
await page.goto(`${BASE}?frame=global`);
await new Promise((r) => setTimeout(r, 1500));
await page.evaluate(() => {
  const g = document.querySelector("paperlessoffline-panel").shadowRoot.querySelector("pp-global-settings");
  const rows = g.shadowRoot.querySelector("pp-render-settings").shadowRoot.querySelectorAll(".row");
  const sat = [...rows].find((r) => r.textContent.includes("Saturation"));
  const range = sat.querySelector("input[type=range]");
  range.value = "1.5";
  range.dispatchEvent(new Event("input"));
});
await new Promise((r) => setTimeout(r, 200));
await page.evaluate(() => {
  const g = document.querySelector("paperlessoffline-panel").shadowRoot.querySelector("pp-global-settings");
  g.shadowRoot.querySelector("button.primary").click();
});
await new Promise((r) => setTimeout(r, 400));
const saved = (await ws()).find((m) => m.type === "paperlessoffline/defaults/set");
check(saved?.defaults?.saturation === 1.5, `global defaults saved (${JSON.stringify(saved?.defaults)})`);

await browser.close();
console.log(failures.length ? `${failures.length} failure(s)` : "all interactions ok");
process.exit(failures.length ? 1 : 0);
