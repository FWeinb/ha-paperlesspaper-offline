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

// 5. Overlays: add from a preset, edit, preview, save, toggle.
await page.goto(`${BASE}?frame=kitchen&tab=settings`);
await new Promise((r) => setTimeout(r, 1500));
await page.evaluate(() => {
  const panel = document.querySelector("paperlessoffline-panel");
  panel.tab = "settings";
});
await new Promise((r) => setTimeout(r, 800));
const overlaysRoot = () =>
  page.evaluateHandle(() => document.querySelector("paperlessoffline-panel").shadowRoot.querySelector("pp-overlays").shadowRoot);
await (await overlaysRoot()).evaluate((root) => root.querySelector(".menu-wrap button").click());
await new Promise((r) => setTimeout(r, 200));
await (await overlaysRoot()).evaluate((root) => root.querySelector(".menu button").click()); // "Sensor value"
await new Promise((r) => setTimeout(r, 300));
await (await overlaysRoot()).evaluate((root) => {
  const editor = root.querySelector("pp-overlay-editor").shadowRoot;
  const area = editor.querySelector("textarea.template");
  area.value = "**{{ states('sensor.living_room_humidity') }} %**";
  area.dispatchEvent(new Event("input"));
  editor.querySelectorAll(".anchors button")[6].click(); // bottom left
});
await new Promise((r) => setTimeout(r, 1200));
const ovPreviews = (await ws()).filter((m) => m.type === "paperlessoffline/overlay/preview");
check(ovPreviews.length >= 2, `overlay preview re-rendered (${ovPreviews.length})`);
const lastPreview = ovPreviews.at(-1);
check(lastPreview?.overlays?.some((o) => o.id === "draft" && o.anchor === "bottom_left"), "preview includes the draft with its anchor");
await (await overlaysRoot()).evaluate((root) => root.querySelector("pp-overlay-editor").shadowRoot.querySelector("button.primary").click());
await new Promise((r) => setTimeout(r, 500));
const saveMsg = (await ws()).filter((m) => m.type === "paperlessoffline/overlay/save").pop();
check(saveMsg?.overlay?.template?.includes("living_room_humidity") && !saveMsg.overlay.id, "new overlay saved without id");
const rows = await (await overlaysRoot()).evaluate((root) => root.querySelectorAll("li").length);
check(rows === 3, `list shows 3 overlays (${rows})`);
await (await overlaysRoot()).evaluate((root) => root.querySelector("li .toggle input").click());
await new Promise((r) => setTimeout(r, 400));
const toggled = (await ws()).filter((m) => m.type === "paperlessoffline/overlay/save").pop();
check(toggled?.overlay?.id === "o1" && toggled.overlay.enabled === false, "toggle disables an overlay");

// 6. Slow previews: changes made while one renders are coalesced into one request.
await page.goto(`${BASE}?frame=kitchen&edit=0&slow=1500`);
await new Promise((r) => setTimeout(r, 1000)); // the first preview is still running
const editorForm = () => page.evaluateHandle(() =>
  document.querySelector("paperlessoffline-panel").shadowRoot.querySelector("pp-photo-editor")
    .shadowRoot.querySelector("pp-render-settings").shadowRoot.querySelectorAll(".row")[0]);
await (await editorForm()).evaluate((row) => row.querySelector("input[type=checkbox]").click());
for (const value of ["atkinson", "bayer", "none", "atkinson", "sierra2"]) {
  await new Promise((r) => setTimeout(r, 500));
  await (await editorForm()).evaluate((row, v) => {
    const sel = row.querySelector("select");
    sel.value = v;
    sel.dispatchEvent(new Event("change"));
  }, value);
}
await new Promise((r) => setTimeout(r, 4500));
const slow = (await ws()).filter((m) => m.type === "paperlessoffline/preview");
const maxInFlight = await page.evaluate(() => window.__previewMax);
check(maxInFlight === 1, `one preview in flight at a time (max ${maxInFlight})`);
check(slow.length <= 4, `stale changes coalesced (${slow.length} requests for 6 changes)`);
check(slow.at(-1)?.overrides?.dither === "sierra2", "last request has the latest draft");

await browser.close();
console.log(failures.length ? `${failures.length} failure(s)` : "all interactions ok");
process.exit(failures.length ? 1 : 0);
