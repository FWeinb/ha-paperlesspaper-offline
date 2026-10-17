/**
 * Dev harness: renders the panel/card against an in-memory fake of the
 * integration's websocket API. Query params:
 *   ?view=panel|card   ?frame=<entry_id|global>   ?tab=photos|settings
 *   ?edit=<library index> (7 is a card)   ?import=1   ?dark=1   ?narrow=1
 */
import "../src/card";
import "../src/panel";
import type { Frame, FrameSettings, LibraryItem } from "../src/types";

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
const photoOf = (i: number, entry: string): LibraryItem => ({
  photo_id: `p${entry}${i}`,
  kind: "photo",
  name: names[i],
  enabled: i !== 4,
  added: new Date().toISOString(),
  overrides: i === 1 ? { dither: "atkinson", saturation: 1.3 } : i === 2 ? { crop: [0.1, 0.05, 0.5, 0.9] } : {},
  hide_frame_overlays: false,
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
    pending: ["photo"], motion_suppressed_until: "2026-06-02T07:00:00+00:00",
    current: { kind: "photo", photo_id: "pkitchen0", name: names[0] },
    up_next: { kind: "photo", photo_id: "pkitchen3", name: names[3] }, override: null, photo_count: 7, enabled_count: 6,
    ble: { voltage: 3912, usb: false, charging: false, rssi: -61, read_at: new Date(Date.now() - 2 * 3600_000).toISOString() }, overdue: false, needs_reprovision: false,
  },
  {
    entry_id: "hall", title: "Hallway", client_id: "epd13-aabbccddeeff", device_id: "dev_hall",
    panel: { model: 'Paper L (13.3" Spectra 6)', width: 1200, height: 1600 }, canvas: { width: 1200, height: 1600 },
    mounting: "portrait", order: "shuffle", interval: 7200, render_defaults: {},
    last_seen: new Date(Date.now() - 3 * 3600_000).toISOString(), last_wake: null, wake_count: 3,
    pending: [], motion_suppressed_until: null,
    current: { kind: "placeholder", photo_id: null, name: "placeholder" },
    up_next: { kind: "placeholder", photo_id: null, name: null }, override: null, photo_count: 0, enabled_count: 0,
    ble: { read_at: null }, overdue: true, needs_reprovision: false,
  },
];
const photos: Record<string, LibraryItem[]> = { kitchen: names.map((_, i) => photoOf(i, "kitchen")), hall: [] };

const FILL: Record<string, string> = { white: "#d6d6d6", black: "#1f2226", red: "#ea4843", green: "#067406", blue: "#416ce1", yellow: "#dbd529" };
type Bg = { background?: string; background_photo_id?: string | null };

/** A library item's base image: a photo's dithered render, or a card's background. */
function baseImage(entry: string, photoId: string | null, w: number, h: number, bg?: Bg): string {
  const item = photos[entry].find((p) => p.photo_id === photoId) ?? photos[entry].find((p) => p.kind === "photo");
  if (item?.kind === "card") {
    const b = bg ?? item;
    if (b.background === "photo" && b.background_photo_id) return baseImage(entry, b.background_photo_id, w, h);
    const c = document.createElement("canvas");
    c.width = w; c.height = h;
    const g = c.getContext("2d")!;
    g.fillStyle = FILL[b.background ?? "white"];
    g.fillRect(0, 0, w, h);
    return c.toDataURL();
  }
  const idx = item ? Number(item.photo_id.slice(1 + entry.length)) : 0;
  return quantize(sources[idx], w, h);
}

/** A card's preview: its background with its overlays (and the global ones unless hidden). */
async function cardImage(entry: string, card: LibraryItem, w: number, h: number, bg?: Bg): Promise<string> {
  const list = [...(overlays[`photo:${card.photo_id}`] ?? []), ...(card.hide_frame_overlays ? [] : overlays[entry] ?? [])];
  return drawOverlayMock(baseImage(entry, card.photo_id, w, h, bg), list, w, h);
}

const PRESETS: Record<string, any[]> = {
  blank: [],
  info: [
    { name: "Title", template: "# {{ frame.name }}", anchor: "top_center", align: "center", size: "l", text_color: "black", backing: "box" },
    { name: "Values", template: "{{ date_local(now(), 'long') }}\nAdd your values here", anchor: "center", align: "center", size: "m", text_color: "black", backing: "box" },
  ],
  notice: [{ name: "Notice", template: "Notice", anchor: "center", align: "center", size: "xxl", text_color: "black", backing: "none" }],
};
let nextCard = 1;

function addCardMock(entry: string, msg: any): LibraryItem {
  const id = `c${nextCard++}`;
  const card: LibraryItem = {
    photo_id: id, kind: "card", name: msg.name || ({ blank: "Card", info: "Info", notice: "Notice" } as any)[msg.preset ?? "blank"],
    enabled: true, added: new Date().toISOString(), overrides: {}, hide_frame_overlays: true,
    background: msg.background ?? "white", background_photo_id: msg.background === "photo" ? msg.background_photo_id : null,
    thumb_url: "", display_urls: {},
  };
  const darkBg = ["black", "blue", "red", "green"].includes(card.background!);
  overlays[`photo:${id}`] = PRESETS[msg.preset ?? "blank"].map((o) => ({
    enabled: true, show_if: null, margin: 0.03, width: null, backing_color: "white", redraw: "change", last_text: null, last_error: null,
    ...o, text_color: o.backing === "none" && darkBg ? "white" : o.text_color, overlay_id: `o${nextOverlay++}`,
  }));
  card.overlay_count = overlays[`photo:${id}`].length;
  photos[entry].push(card);
  return card;
}

/** Subscribers of `paperlessoffline/subscribe`: told whenever a frame's data changes. */
const subscribers = new Set<(m: { entry_id: string | null }) => void>();
async function changed(entry: string) {
  for (const card of photos[entry] ?? []) {
    if (card.kind === "card") card.thumb_url = await cardImage(entry, card, 320, 192);
  }
  const f = frames.find((x) => x.entry_id === entry);
  if (f) { f.photo_count = photos[entry].length; f.enabled_count = photos[entry].filter((p) => p.enabled).length; }
  for (const cb of subscribers) cb({ entry_id: entry });
}

/** Overlay lists: the frame's global ones under the entry id, a photo's own under `photo:<id>`. */
const scopeKey = (msg: any): string => (msg.photo_id ? `photo:${msg.photo_id}` : msg.entry_id);
const overlays: Record<string, any[]> = {
  kitchen: [
    { overlay_id: "o1", name: "Temperature", template: ":mdi:thermometer: **{{ states('sensor.outdoor_temperature') }} °C**", enabled: true, show_if: null, anchor: "top_right", margin: 0.03, width: null, align: "left", size: "l", text_color: "black", backing: "box", backing_color: "white", redraw: "change", last_text: ":mdi:thermometer: **7.5 °C**", last_error: null },
    { overlay_id: "o2", name: "Date", template: "{{ date_local(now(), 'long') }}", enabled: true, show_if: null, anchor: "bottom_center", margin: 0.03, width: null, align: "center", size: "m", text_color: "white", backing: "halo", backing_color: "white", redraw: "change", last_text: "Wednesday, October 14, 2026", last_error: null },
  ],
  hall: [],
};
let nextOverlay = 3;

function evalTemplate(tpl: string): { text: string | null; error: string | null } {
  if (tpl.includes("| nope")) return { text: null, error: "TemplateSyntaxError: No filter named 'nope'." };
  const text = tpl
    .replace(/\{\{\s*states\('([^']+)'\)\s*\}\}/g, (_, id) => hass.states[id]?.state ?? "unknown")
    .replace(/\{\{\s*date_local\([^}]*\}\}/g, "Wednesday, October 14, 2026")
    .replace(/\{\{[^}]*\}\}/g, "…");
  return { text: text.trim() || null, error: null };
}

function drawOverlayMock(dataUrl: string, list: any[], w: number, h: number): Promise<string> {
  return new Promise((resolve) => {
    const img = new Image();
    img.onload = () => {
      const c = document.createElement("canvas");
      c.width = w; c.height = h;
      const g = c.getContext("2d")!;
      g.imageSmoothingEnabled = false;
      g.drawImage(img, 0, 0, w, h);
      for (const o of list) {
        if (!o.enabled) continue;
        const { text } = evalTemplate(o.template);
        if (!text) continue;
        const size = ({ s: 9, m: 12, l: 16, xl: 22, xxl: 36 } as any)[o.size] ?? 12;
        g.font = `${size}px sans-serif`;
        const lines = text.replace(/[*#]|:mdi:[a-z-]+:/g, "").split("\n");
        const tw = Math.max(...lines.map((t: string) => g.measureText(t).width)) + size;
        const th = lines.length * size * 1.3 + size * 0.6;
        const [v, , hz] = o.anchor === "center" ? ["center", "", "center"] : o.anchor.split("_").length === 2 ? [o.anchor.split("_")[0], "", o.anchor.split("_")[1]] : ["center", "", "center"];
        const m = 8;
        const x = hz === "left" ? m : hz === "right" ? w - m - tw : (w - tw) / 2;
        const y = v === "top" ? m : v === "bottom" ? h - m - th : (h - th) / 2;
        if (o.backing === "box") { g.fillStyle = "#f2f2f2"; g.fillRect(x, y, tw, th); }
        g.fillStyle = o.text_color === "white" ? "#fff" : "#1f2226";
        lines.forEach((t: string, i: number) => g.fillText(t, x + size / 2, y + size * (1.1 + i * 1.3)));
      }
      resolve(c.toDataURL());
    };
    img.src = dataUrl;
  });
}

const delay = <T>(v: T, ms = 120) => new Promise<T>((r) => setTimeout(() => r(v), ms));
// ?slow=<ms> makes previews take that long; window.__previewMax records the
// most preview requests that were in flight at once.
const previewMs = Number(params.get("slow") ?? 300);
let previewsInFlight = 0;
async function previewDelay<T>(v: T | Promise<T>): Promise<T> {
  previewsInFlight++;
  const w = window as any;
  w.__previewMax = Math.max(w.__previewMax ?? 0, previewsInFlight);
  try {
    return await delay(await v, previewMs);
  } finally {
    previewsInFlight--;
  }
}

const hass: any = {
  language: params.get("lang") ?? "en",
  config: { time_zone: "Europe/Berlin" },
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
      case "photos": return delay({ photos: [...(photos[msg.entry_id] ?? [])] });
      case "card/add": { const card = addCardMock(msg.entry_id, msg); await changed(msg.entry_id); return delay(card); }
      case "photo/update": {
        const p = photos[msg.entry_id].find((x) => x.photo_id === msg.photo_id)!;
        for (const k of ["name", "enabled", "overrides", "hide_frame_overlays", "background", "background_photo_id"]) if (k in msg) (p as any)[k] = msg[k];
        if (p.kind === "card" && p.background !== "photo") p.background_photo_id = null;
        await changed(msg.entry_id);
        return delay(p);
      }
      case "photo/delete": {
        photos[msg.entry_id] = photos[msg.entry_id].filter((x) => x.photo_id !== msg.photo_id);
        for (const c of photos[msg.entry_id]) if (c.background_photo_id === msg.photo_id) { c.background = "white"; c.background_photo_id = null; }
        await changed(msg.entry_id);
        return delay(null);
      }
      case "defaults": return delay({ defaults: globalDefaults, builtin: { dither: "floyd_steinberg", serpentine: false, fit: "cover", brightness: 1, contrast: 1, saturation: 1, background: "white", palette: "perceived" } });
      case "defaults/set": globalDefaults = msg.defaults; return delay({ defaults: globalDefaults });
      case "preview": {
        const frame = frames.find((f) => f.entry_id === msg.entry_id)!;
        const item = photos[msg.entry_id].find((p) => p.photo_id === msg.photo_id)!;
        const [w, h] = [frame.canvas.width / 2, frame.canvas.height / 2];
        if (item.kind === "card") return previewDelay({ image: await cardImage(msg.entry_id, item, w, h, "background" in msg ? msg : undefined), width: frame.canvas.width, height: frame.canvas.height });
        const idx = photos[msg.entry_id].indexOf(item);
        return previewDelay({ image: quantize(sources[idx], w, h, msg.overrides?.crop), width: frame.canvas.width, height: frame.canvas.height });
      }
      case "overlays": return delay({ overlays: overlays[scopeKey(msg)] ?? [] });
      case "overlay/save": {
        const list = (overlays[scopeKey(msg)] ??= []);
        const { id, ...rest } = msg.overlay;
        const r = evalTemplate(rest.template ?? "");
        if (id) { const i = list.findIndex((o) => o.overlay_id === id); list[i] = { ...list[i], ...rest, overlay_id: id }; return delay(list[i]); }
        const created = { ...rest, overlay_id: `o${nextOverlay++}`, last_text: r.text, last_error: r.error };
        list.push(created); if (msg.photo_id) await changed(msg.entry_id); return delay(created);
      }
      case "overlay/delete": overlays[scopeKey(msg)] = overlays[scopeKey(msg)].filter((o) => o.overlay_id !== msg.overlay_id); return delay(null);
      case "overlay/reorder": { const by = new Map(overlays[scopeKey(msg)].map((o) => [o.overlay_id, o])); overlays[scopeKey(msg)] = msg.order.map((i: string) => by.get(i)); return delay(null); }
      case "overlays/copy": if (msg.photo_id) { const src = overlays[`photo:${msg.photo_id}`] ?? []; let n = 0; for (const t of msg.to_photo_ids) { const k = `photo:${t}`; const copies = src.map((o) => ({ ...o, overlay_id: `o${nextOverlay++}` })); overlays[k] = msg.replace ? copies : [...(overlays[k] ?? []), ...copies]; n += copies.length; } return delay({ copied: n }); } overlays[msg.target_entry_id].push(...overlays[msg.entry_id].map((o) => ({ ...o, overlay_id: `o${nextOverlay++}` }))); return delay({ copied: overlays[msg.entry_id].length });
      case "overlay/preview": {
        const frame = frames.find((f) => f.entry_id === msg.entry_id)!;
        const drafts = msg.overlays.map((o: any) => ({ ...o, overlay_id: o.id ?? o.overlay_id }));
        // Photo drafts are drawn first, then the stored global ones on top.
        const list = msg.for_photo ? [...drafts, ...(overlays[msg.entry_id] ?? [])] : drafts;
        const base = baseImage(msg.entry_id, msg.photo_id, frame.canvas.width / 2, frame.canvas.height / 2);
        const image = await drawOverlayMock(base, list, frame.canvas.width / 2, frame.canvas.height / 2);
        const results = Object.fromEntries(list.map((o: any) => [o.overlay_id, evalTemplate(o.template)]));
        return previewDelay({ image, width: frame.canvas.width, height: frame.canvas.height, results });
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
  connection: {
    async subscribeMessage(cb: (m: { entry_id: string | null }) => void) {
      subscribers.add(cb);
      return async () => void subscribers.delete(cb);
    },
  },
};

hass.states["sensor.outdoor_temperature"] = { state: "7.5", attributes: { friendly_name: "Outdoor temperature", unit_of_measurement: "°C", device_class: "temperature" }, last_changed: "" };
hass.states["sensor.living_room_humidity"] = { state: "56", attributes: { friendly_name: "Living room humidity", unit_of_measurement: "%" }, last_changed: "" };
hass.states["weather.home"] = { state: "partlycloudy", attributes: { friendly_name: "Home", temperature: 8 }, last_changed: "" };

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

addCardMock("kitchen", { name: "Welcome", preset: "info", background: "yellow" });
frames[0].photo_count = photos.kitchen.length;

async function main() {
  await changed("kitchen");
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
  if (params.get("overlay")) {
    panel.tab = "settings";
    await new Promise((r) => setTimeout(r, 500));
    const list = panel.shadowRoot.querySelector("pp-overlays");
    list.editing = { ...overlays.kitchen[Number(params.get("overlay"))] };
  }
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
