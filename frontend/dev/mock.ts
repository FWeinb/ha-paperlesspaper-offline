/**
 * Dev harness: renders the panel/card against an in-memory fake of the
 * integration's websocket API. Query params:
 *   ?view=panel|card   ?frame=<entry_id|global>   ?tab=photos|settings
 *   ?edit=<photo index>   ?import=1   ?dark=1   ?narrow=1
 */
import "../src/card";
import "../src/panel";
import type { Frame, FrameSettings, Photo } from "../src/types";

const params = new URLSearchParams(location.search);
if (params.get("dark")) document.body.classList.add("dark");

const PERCEIVED = [
  [0x1f, 0x22, 0x26], [0x41, 0x6c, 0xe1], [0x06, 0x74, 0x06],
  [0xea, 0x48, 0x43], [0xdb, 0xd5, 0x29], [0xd6, 0xd6, 0xd6],
];

function sampleImage(seed: number, w = 1280, h = 860): HTMLCanvasElement {
  const c = document.createElement("canvas");
  c.width = w;
  c.height = h;
  const g = c.getContext("2d")!;
  const sky = g.createLinearGradient(0, 0, 0, h);
  const hues = [[200, 30], [20, 280], [160, 50], [330, 40], [45, 210], [260, 120]][seed % 6];
  sky.addColorStop(0, `hsl(${hues[0]} 70% 70%)`);
  sky.addColorStop(1, `hsl(${hues[1]} 60% 45%)`);
  g.fillStyle = sky;
  g.fillRect(0, 0, w, h);
  g.fillStyle = `hsl(${(hues[0] + 40) % 360} 80% 60%)`;
  g.beginPath();
  g.arc(w * (0.25 + 0.1 * (seed % 4)), h * 0.32, h * 0.13, 0, Math.PI * 2);
  g.fill();
  for (let i = 0; i < 3; i++) {
    g.fillStyle = `hsl(${(hues[1] + i * 30) % 360} 45% ${30 - i * 6}%)`;
    g.beginPath();
    g.moveTo(0, h);
    for (let x = 0; x <= w; x += 40) g.lineTo(x, h * (0.55 + i * 0.12) + Math.sin(x / (90 + i * 40) + seed) * 40);
    g.lineTo(w, h);
    g.fill();
  }
  return c;
}

function quantize(src: HTMLCanvasElement, w: number, h: number, crop?: number[]): string {
  const c = document.createElement("canvas");
  c.width = w;
  c.height = h;
  const g = c.getContext("2d")!;
  const [cx, cy, cw, ch] = crop ?? [0, 0, 1, 1];
  const sw = src.width * cw, sh = src.height * ch;
  const scale = Math.max(w / sw, h / sh);
  const dw = sw * scale, dh = sh * scale;
  g.drawImage(src, src.width * cx, src.height * cy, sw, sh, (w - dw) / 2, (h - dh) / 2, dw, dh);
  const img = g.getImageData(0, 0, w, h);
  const d = img.data;
  for (let i = 0; i < d.length; i += 4) {
    let best = 0, bd = Infinity;
    PERCEIVED.forEach((p, j) => {
      const dist = (d[i] - p[0]) ** 2 + (d[i + 1] - p[1]) ** 2 + (d[i + 2] - p[2]) ** 2;
      if (dist < bd) { bd = dist; best = j; }
    });
    [d[i], d[i + 1], d[i + 2]] = PERCEIVED[best];
  }
  g.putImageData(img, 0, 0);
  return c.toDataURL();
}

const names = ["Beach sunset", "Grandma's garden", "Alps 2024", "Kids at the lake", "Autumn forest", "City lights", "Lavender field"];
const sources = names.map((_, i) => sampleImage(i));
const photoOf = (i: number, entry: string): Photo => ({
  photo_id: `p${entry}${i}`,
  name: names[i],
  enabled: i !== 4,
  added: new Date().toISOString(),
  overrides: i === 1 ? { dither: "atkinson", saturation: 1.3 } : i === 2 ? { crop: [0.1, 0.05, 0.5, 0.9] } : {},
  thumb_url: (() => { const c = document.createElement("canvas"); c.width = 320; c.height = 215; c.getContext("2d")!.drawImage(sources[i], 0, 0, 320, 215); return c.toDataURL(); })(),
  display_urls: Object.fromEntries([0, 90, 180, 270].map((r) => [String(r), sources[i].toDataURL()])),
});

let globalDefaults: FrameSettings = { saturation: 1.2 };
const frames: Frame[] = [
  {
    entry_id: "kitchen", title: "Kitchen", client_id: "epd7-dc1ed5613e74", device_id: "dev_kitchen",
    panel: { model: 'Paper 7 (7.3" Spectra 6)', width: 800, height: 480 }, canvas: { width: 480, height: 800 },
    mounting: "portrait", order: "sequential", interval: 3600, render_defaults: { dither: "floyd_steinberg" },
    last_seen: new Date(Date.now() - 7 * 60_000).toISOString(), last_wake: null, wake_count: 42,
    pending: ["photo"], current: { kind: "photo", photo_id: "pkitchen0", name: names[0] },
    up_next: { kind: "photo", photo_id: "pkitchen3", name: names[3] }, override: null, photo_count: 7, enabled_count: 6,
    ble: { voltage: 3912, usb: false, charging: false, rssi: -61, read_at: new Date(Date.now() - 2 * 3600_000).toISOString() }, overdue: false, needs_reprovision: false,
  },
  {
    entry_id: "hall", title: "Hallway", client_id: "epd13-aabbccddeeff", device_id: "dev_hall",
    panel: { model: 'Paper L (13.3" Spectra 6)', width: 1200, height: 1600 }, canvas: { width: 1200, height: 1600 },
    mounting: "portrait", order: "shuffle", interval: 7200, render_defaults: {},
    last_seen: new Date(Date.now() - 3 * 3600_000).toISOString(), last_wake: null, wake_count: 3,
    pending: [], current: { kind: "placeholder", photo_id: null, name: "placeholder" },
    up_next: { kind: "placeholder", photo_id: null, name: null }, override: null, photo_count: 0, enabled_count: 0,
    ble: { read_at: null }, overdue: true, needs_reprovision: false,
  },
];
const photos: Record<string, Photo[]> = { kitchen: names.map((_, i) => photoOf(i, "kitchen")), hall: [] };

const delay = <T>(v: T, ms = 120) => new Promise<T>((r) => setTimeout(() => r(v), ms));

const hass: any = {
  language: params.get("lang") ?? "en",
  user: { is_admin: true },
  devices: {
    dev_kitchen: { id: "dev_kitchen", name: "Kitchen", config_entries: ["kitchen"] },
    dev_hall: { id: "dev_hall", name: "Hallway", config_entries: ["hall"] },
  },
  entities: {} as Record<string, any>,
  states: {} as Record<string, any>,
  async callWS(msg: any) {
    ((window as any).__ws ??= []).push(msg);
    const t = msg.type.replace("paperlessoffline/", "");
    switch (t) {
      case "frames": return delay({ frames });
      case "photos": return delay({ photos: photos[msg.entry_id] ?? [] });
      case "defaults": return delay({ defaults: globalDefaults, builtin: { dither: "floyd_steinberg", serpentine: false, fit: "cover", brightness: 1, contrast: 1, saturation: 1, background: "white", palette: "perceived" } });
      case "defaults/set": globalDefaults = msg.defaults; return delay({ defaults: globalDefaults });
      case "preview": {
        const frame = frames.find((f) => f.entry_id === msg.entry_id)!;
        const idx = photos[msg.entry_id].findIndex((p) => p.photo_id === msg.photo_id);
        const scale = 0.5;
        return delay({ image: quantize(sources[idx], frame.canvas.width * scale, frame.canvas.height * scale, msg.overrides?.crop), width: frame.canvas.width, height: frame.canvas.height }, 300);
      }
      case "media_source/browse_media":
        return delay(msg.media_content_id
          ? { title: "My media", media_content_id: msg.media_content_id, can_expand: true, children: names.map((n, i) => ({ title: `${n}.jpg`, media_content_id: `media-source://media_source/local/${i}.jpg`, media_class: "image", media_content_type: "image/jpeg", can_expand: false, can_play: true, thumbnail: photos.kitchen[i].thumb_url })) }
          : { title: "Media", media_content_id: "", can_expand: true, children: [{ title: "My media", media_content_id: "media-source://media_source/local/.", media_class: "directory", media_content_type: "", can_expand: true, can_play: false, thumbnail: null }, { title: "Immich", media_content_id: "media-source://immich", media_class: "directory", media_content_type: "", can_expand: true, can_play: false, thumbnail: null }] });
      default: console.log("WS", msg); return delay({});
    }
  },
  async callService(...args: unknown[]) { console.log("service", args); },
  async fetchWithAuth() { return new Response(JSON.stringify({ added: [], errors: [] })); },
  connection: { async subscribeMessage() { return async () => undefined; } },
};

// Image entities used for the "Showing"/"Up next" previews.
for (const f of frames) {
  for (const [key, idx] of [["preview_showing", 0], ["preview_up_next", 3]] as const) {
    const entityId = `image.${f.entry_id}_${key.replace("preview_", "")}`;
    hass.entities[entityId] = { entity_id: entityId, device_id: f.device_id, platform: "paperlessoffline", translation_key: key };
    hass.states[entityId] = { state: "", attributes: { entity_picture: f.photo_count ? quantize(sources[idx], f.canvas.width / 2, f.canvas.height / 2) : null }, last_changed: "" };
  }
  for (const [domain, key, state, attrs] of [
    ["sensor", "last_seen", f.last_seen, {}], ["sensor", "current_photo", f.current.name, {}],
    ["binary_sensor", "in_sync", f.pending.length ? "off" : "on", { pending: f.pending }],
    ["select", "up_next", f.up_next.name, {}], ["button", "skip", "unknown", {}],
  ] as const) {
    const entityId = `${domain}.${f.entry_id}_${key}`;
    hass.entities[entityId] = { entity_id: entityId, device_id: f.device_id, platform: "paperlessoffline", translation_key: key };
    hass.states[entityId] = { state, attributes: attrs, last_changed: "" };
  }
}

async function main() {
  if (params.get("view") === "card") {
    const wrap = document.createElement("div");
    wrap.id = "cards";
    document.body.append(wrap);
    for (const device of ["dev_kitchen", "dev_hall"]) {
      const card = document.createElement("paperlessoffline-frame-card") as any;
      card.setConfig({ type: "custom:paperlessoffline-frame-card", device_id: device, show_up_next: true });
      card.hass = hass;
      wrap.append(card);
    }
    return;
  }
  const panel = document.createElement("paperlessoffline-panel") as any;
  panel.narrow = !!params.get("narrow");
  panel.route = { prefix: "/paperlessoffline", path: params.get("frame") ? `/${params.get("frame")}` : "" };
  panel.hass = hass;
  document.body.append(panel);
  await new Promise((r) => setTimeout(r, 600));
  if (params.get("tab")) panel.tab = params.get("tab");
  if (params.get("edit")) panel.editing = photos.kitchen[Number(params.get("edit"))];
  if (params.get("import")) {
    await panel.updateComplete;
    const lib = panel.shadowRoot.querySelector("pp-library");
    lib.importOpen = true;
    await new Promise((r) => setTimeout(r, 300));
    const dlg = lib.shadowRoot.querySelector("pp-media-import");
    await dlg.open("media-source://media_source/local/.");
    dlg.selected = new Set(["media-source://media_source/local/0.jpg", "media-source://media_source/local/2.jpg"]);
  }
}
main();
