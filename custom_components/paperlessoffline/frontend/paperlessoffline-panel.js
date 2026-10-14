import { s as A, i as E, n as d, r as l, a as M, l as g, A as n, d as c, f as st, b as o, g as V, h as it, j as rt, k as at, t as C, o as ot, p as nt, q as lt, u as pt, v as dt, w as ht, x as ct, y as ut, z as ft, B as gt, C as mt, c as N, D as vt, e as bt, E as $t } from "./chunk-CVXmZojm.js";
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const yt = (t, e, s) => (s.configurable = !0, s.enumerable = !0, Reflect.decorate && typeof e != "object" && Object.defineProperty(t, e, s), s);
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
function xt(t, e) {
  return (s, i, a) => {
    const r = (p) => p.renderRoot?.querySelector(t) ?? null;
    return yt(s, i, { get() {
      return r(this);
    } });
  };
}
const m = "paperlessoffline", G = (t) => t.callWS({ type: `${m}/frames` }).then((e) => e.frames), R = (t, e) => t.callWS({ type: `${m}/photos`, entry_id: e }).then((s) => s.photos), wt = (t, e) => t.connection.subscribeMessage((s) => e(s.entry_id), {
  type: `${m}/subscribe`
}), Q = (t, e, s, i) => t.callWS({ type: `${m}/photo/update`, entry_id: e, photo_id: s, ...i }), _t = (t, e, s) => t.callWS({ type: `${m}/photo/delete`, entry_id: e, photo_id: s }), kt = (t, e, s) => t.callWS({ type: `${m}/photo/reorder`, entry_id: e, order: s }), Pt = (t, e, s, i) => t.callWS({
  type: `${m}/photo/copy`,
  entry_id: e,
  photo_id: s,
  target_entry_id: i
}), Ot = (t, e, s) => t.callWS({ type: `${m}/photo/show`, entry_id: e, photo_id: s }), St = (t, e) => t.callWS({ type: `${m}/frame/skip`, entry_id: e }), Z = (t, e, s) => t.callWS({ type: `${m}/frame/update`, entry_id: e, ...s }), It = (t, e, s) => t.callWS({ type: `${m}/import`, entry_id: e, media_content_id: s }), tt = (t, e, s, i) => t.callWS({
  type: `${m}/preview`,
  entry_id: e,
  photo_id: s,
  ...i
}), Dt = (t) => t.callWS({ type: `${m}/defaults` }), Et = (t, e) => t.callWS({ type: `${m}/defaults/set`, defaults: e }), Ct = (t, e) => t.callWS({
  type: "media_source/browse_media",
  ...e ? { media_content_id: e } : {}
});
async function Tt(t, e, s) {
  const i = new FormData();
  for (const r of s) i.append("file", r, r.name);
  const a = await t.fetchWithAuth(`/api/${m}/upload/${e}`, {
    method: "POST",
    body: i
  });
  if (!a.ok) throw new Error(`Upload failed (${a.status})`);
  return a.json();
}
const u = (t) => t?.message ?? String(t);
var Mt = Object.defineProperty, jt = Object.getOwnPropertyDescriptor, I = (t, e, s, i) => {
  for (var a = i > 1 ? void 0 : i ? jt(e, s) : e, r = t.length - 1, p; r >= 0; r--)
    (p = t[r]) && (a = (i ? p(e, s, a) : p(a)) || a);
  return i && a && Mt(e, s, a), a;
};
const At = "media-source://paperlessoffline", X = (t) => t.media_class === "image" || t.media_content_type?.startsWith("image/");
let y = class extends M {
  constructor() {
    super(...arguments), this.item = null, this.stack = [], this.selected = /* @__PURE__ */ new Set(), this.loading = !1, this.importing = !1, this.error = null;
  }
  connectedCallback() {
    super.connectedCallback(), this.open(void 0);
  }
  async open(t, e = !0) {
    this.loading = !0, this.error = null;
    try {
      const s = await Ct(this.hass, t);
      e && this.item && (this.stack = [...this.stack, this.item.media_content_id]), this.item = s;
    } catch (s) {
      this.error = u(s);
    } finally {
      this.loading = !1;
    }
  }
  back() {
    const t = [...this.stack], e = t.pop();
    this.stack = t, this.open(e || void 0, !1);
  }
  toggle(t) {
    const e = new Set(this.selected);
    e.has(t) ? e.delete(t) : e.add(t), this.selected = e;
  }
  async import() {
    this.importing = !0, this.error = null;
    try {
      for (const t of this.selected)
        await It(this.hass, this.frame.entry_id, t);
      this.close();
    } catch (t) {
      this.error = u(t);
    } finally {
      this.importing = !1;
    }
  }
  close() {
    this.dispatchEvent(new CustomEvent("closed", { bubbles: !0, composed: !0 }));
  }
  render() {
    const t = g(this.hass), e = (this.item?.children ?? []).filter(
      (s) => !s.media_content_id.startsWith(At) && (s.can_expand || X(s))
    );
    return o`<div class="scrim" @click=${(s) => s.target === s.currentTarget && this.close()}>
      <div class="dialog card" role="dialog" aria-modal="true" aria-label=${t("import")}>
        <header>
          ${this.stack.length ? o`<button class="icon-btn" title=${t("back")} @click=${this.back}>${c(st)}</button>` : n}
          <h2>${this.item?.title || t("media_root")}</h2>
          <button class="icon-btn" title=${t("close")} @click=${this.close}>${c(V)}</button>
        </header>
        <div class="grid">
          ${this.loading ? o`<p class="muted">${t("loading")}</p>` : n}
          ${!this.loading && !e.length ? o`<p class="muted">${t("no_media")}</p>` : n}
          ${e.map((s) => {
      const i = this.selected.has(s.media_content_id), a = !s.can_expand && X(s);
      return o`<button
              class="tile ${i ? "selected" : ""}"
              @click=${() => a ? this.toggle(s.media_content_id) : this.open(s.media_content_id)}
            >
              <div class="thumb">
                ${s.thumbnail ? o`<img src=${s.thumbnail} alt="" loading="lazy" />` : c(a ? it : rt)}
                ${i ? o`<span class="tick">${c(at)}</span>` : n}
              </div>
              <span class="label">${s.title}</span>
            </button>`;
    })}
        </div>
        ${this.error ? o`<div class="msg error">${t("error", { error: this.error })}</div>` : n}
        <footer>
          <span class="spacer"></span>
          <button class="btn" @click=${this.close}>${t("cancel")}</button>
          <button
            class="btn primary"
            ?disabled=${!this.selected.size || this.importing}
            @click=${this.import}
          >
            ${this.importing ? t("importing") : t("import_selected", { n: this.selected.size })}
          </button>
        </footer>
      </div>
    </div>`;
  }
};
y.styles = [
  A,
  E`
      .scrim {
        position: fixed;
        inset: 0;
        z-index: 10;
        background: rgba(0, 0, 0, 0.45);
        display: grid;
        place-items: center;
        padding: 16px;
      }
      .dialog {
        width: min(860px, 100%);
        height: min(680px, calc(100vh - 32px));
        display: flex;
        flex-direction: column;
        overflow: hidden;
      }
      header,
      footer {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 8px 12px;
      }
      header {
        border-bottom: 1px solid var(--pp-border);
      }
      footer {
        border-top: 1px solid var(--pp-border);
      }
      h2 {
        flex: 1;
        margin: 0 8px;
        font-size: 18px;
        font-weight: 500;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
      .grid {
        flex: 1;
        overflow: auto;
        padding: 16px;
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
        gap: 12px;
        align-content: start;
      }
      .tile {
        display: grid;
        gap: 6px;
        padding: 6px;
        border: 2px solid transparent;
        border-radius: 10px;
        background: transparent;
        color: inherit;
        text-align: left;
      }
      .tile:hover {
        background: color-mix(in srgb, var(--pp-text) 6%, transparent);
      }
      .tile.selected {
        border-color: var(--pp-accent);
      }
      .thumb {
        position: relative;
        aspect-ratio: 1;
        border-radius: 6px;
        background: var(--pp-bg);
        display: grid;
        place-items: center;
        overflow: hidden;
        color: var(--pp-muted);
      }
      .thumb img {
        width: 100%;
        height: 100%;
        object-fit: cover;
      }
      .thumb svg.icon {
        width: 40px;
        height: 40px;
      }
      .tick {
        position: absolute;
        top: 4px;
        right: 4px;
        color: var(--pp-accent);
        background: var(--pp-surface);
        border-radius: 50%;
        display: grid;
      }
      .tick svg.icon {
        width: 24px;
        height: 24px;
      }
      .label {
        font-size: 13px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
      .msg {
        padding: 0 16px 8px;
      }
      .spacer {
        flex: 1;
      }
    `
];
I([
  d({ attribute: !1 })
], y.prototype, "hass", 2);
I([
  d({ attribute: !1 })
], y.prototype, "frame", 2);
I([
  l()
], y.prototype, "item", 2);
I([
  l()
], y.prototype, "stack", 2);
I([
  l()
], y.prototype, "selected", 2);
I([
  l()
], y.prototype, "loading", 2);
I([
  l()
], y.prototype, "importing", 2);
I([
  l()
], y.prototype, "error", 2);
y = I([
  C("pp-media-import")
], y);
var Ft = Object.defineProperty, zt = Object.getOwnPropertyDescriptor, w = (t, e, s, i) => {
  for (var a = i > 1 ? void 0 : i ? zt(e, s) : e, r = t.length - 1, p; r >= 0; r--)
    (p = t[r]) && (a = (i ? p(e, s, a) : p(a)) || a);
  return i && a && Ft(e, s, a), a;
};
const q = "application/x-paperlessoffline-photo";
let b = class extends M {
  constructor() {
    super(...arguments), this.photos = [], this.dropActive = !1, this.uploading = 0, this.uploadErrors = [], this.error = null, this.importOpen = !1, this.dragId = null, this.dragOverId = null;
  }
  async upload(t) {
    const e = t.filter((s) => s.type.startsWith("image/") || /\.(heic|heif)$/i.test(s.name));
    if (e.length) {
      this.uploading = e.length, this.uploadErrors = [], this.error = null;
      try {
        const s = await Tt(this.hass, this.frame.entry_id, e);
        this.uploadErrors = s.errors;
      } catch (s) {
        this.error = u(s);
      } finally {
        this.uploading = 0;
      }
    }
  }
  onFileInput(t) {
    const e = t.target;
    this.upload([...e.files ?? []]), e.value = "";
  }
  onDragOver(t) {
    t.dataTransfer?.types.includes("Files") && (t.preventDefault(), this.dropActive = !0);
  }
  onDrop(t) {
    t.dataTransfer?.types.includes("Files") && (t.preventDefault(), this.dropActive = !1, this.upload([...t.dataTransfer.files]));
  }
  onTileDragStart(t, e) {
    this.dragId = e.photo_id, t.dataTransfer?.setData(q, e.photo_id), t.dataTransfer && (t.dataTransfer.effectAllowed = "move");
  }
  onTileDragOver(t, e) {
    !this.dragId || !t.dataTransfer?.types.includes(q) || (t.preventDefault(), this.dragOverId = e.photo_id);
  }
  async onTileDrop(t, e) {
    const s = t.dataTransfer?.getData(q);
    if (this.dragOverId = null, this.dragId = null, !s || s === e.photo_id) return;
    t.preventDefault(), t.stopPropagation();
    const i = this.photos.map((r) => r.photo_id).filter((r) => r !== s);
    i.splice(i.indexOf(e.photo_id), 0, s);
    const a = new Map(this.photos.map((r) => [r.photo_id, r]));
    this.photos = i.map((r) => a.get(r));
    try {
      await kt(this.hass, this.frame.entry_id, i);
    } catch (r) {
      this.error = u(r);
    }
  }
  async toggleEnabled(t, e) {
    t.stopPropagation();
    try {
      await Q(this.hass, this.frame.entry_id, e.photo_id, { enabled: !e.enabled });
    } catch (s) {
      this.error = u(s);
    }
  }
  async setOrder(t) {
    try {
      await Z(this.hass, this.frame.entry_id, { order: t });
    } catch (e) {
      this.error = u(e);
    }
  }
  edit(t) {
    this.dispatchEvent(new CustomEvent("edit-photo", { detail: { photo: t }, bubbles: !0, composed: !0 }));
  }
  render() {
    const t = g(this.hass), e = this.frame.current.kind === "photo" ? this.frame.current.photo_id : null, s = this.frame.up_next.kind === "photo" ? this.frame.up_next.photo_id : null;
    return o`
      <div class="toolbar">
        <label class="btn primary">
          ${c(ot)} ${t("upload")}
          <input type="file" accept="image/*,.heic,.heif" multiple hidden @change=${this.onFileInput} />
        </label>
        <button class="btn" @click=${() => this.importOpen = !0}>${c(nt)} ${t("import")}</button>
        <span class="spacer"></span>
        <label class="order">
          <span class="muted">${t("order")}</span>
          <select @change=${(i) => this.setOrder(i.target.value)}>
            ${["sequential", "shuffle"].map(
      (i) => o`<option value=${i} ?selected=${this.frame.order === i}>${t(`order_${i}`)}</option>`
    )}
          </select>
        </label>
      </div>
      <p class="muted summary">
        ${t("photos_count", { enabled: this.frame.enabled_count, total: this.frame.photo_count })}
        ${this.photos.length > 1 && this.frame.order === "sequential" ? o` · ${t("drag_hint")}` : n}
      </p>
      ${this.uploading ? o`<p class="chip">${t("uploading", { n: this.uploading })}</p>` : n}
      ${this.uploadErrors.length ? o`<div class="error">
            ${t("upload_errors")}
            <ul>
              ${this.uploadErrors.map((i) => o`<li>${i.file}: ${i.error}</li>`)}
            </ul>
          </div>` : n}
      ${this.error ? o`<p class="error">${t("error", { error: this.error })}</p>` : n}
      <div
        class="drop ${this.dropActive ? "active" : ""}"
        @dragover=${this.onDragOver}
        @dragleave=${() => this.dropActive = !1}
        @drop=${this.onDrop}
      >
        ${this.photos.length ? o`<div class="grid">
              ${this.photos.map((i) => {
      const a = Object.keys(i.overrides ?? {}).length > 0;
      return o`<div
                  class="tile ${i.enabled ? "" : "disabled"} ${this.dragOverId === i.photo_id ? "over" : ""}"
                  draggable="true"
                  tabindex="0"
                  @click=${() => this.edit(i)}
                  @keydown=${(r) => r.key === "Enter" && this.edit(i)}
                  @dragstart=${(r) => this.onTileDragStart(r, i)}
                  @dragover=${(r) => this.onTileDragOver(r, i)}
                  @dragleave=${() => this.dragOverId = null}
                  @drop=${(r) => this.onTileDrop(r, i)}
                  @dragend=${() => (this.dragId = null, this.dragOverId = null)}
                >
                  <img src=${i.thumb_url} alt="" loading="lazy" draggable="false" />
                  <div class="badges">
                    ${i.photo_id === e ? o`<span class="chip ok">${t("showing")}</span>` : n}
                    ${i.photo_id === s ? o`<span class="chip">${t("up_next")}</span>` : n}
                    ${a ? o`<span class="chip" title=${t("custom")}>${c(lt)}</span>` : n}
                  </div>
                  <div class="caption">
                    <span class="name" title=${i.name}>${i.name}</span>
                    <button
                      class="icon-btn small"
                      title=${i.enabled ? t("in_rotation") : t("not_in_rotation")}
                      @click=${(r) => this.toggleEnabled(r, i)}
                    >
                      ${c(i.enabled ? pt : dt)}
                    </button>
                  </div>
                </div>`;
    })}
            </div>` : o`<div class="empty muted">${t("empty_library")}</div>`}
        ${this.dropActive ? o`<div class="drop-hint">${t("drop_here")}</div>` : n}
      </div>
      ${this.importOpen ? o`<pp-media-import
            .hass=${this.hass}
            .frame=${this.frame}
            @closed=${() => this.importOpen = !1}
          ></pp-media-import>` : n}
    `;
  }
};
b.styles = [
  A,
  E`
      :host {
        display: block;
      }
      .toolbar {
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        gap: 8px;
      }
      .spacer {
        flex: 1;
      }
      .order {
        display: inline-flex;
        align-items: center;
        gap: 8px;
      }
      .summary {
        margin: 12px 0;
        font-size: 14px;
      }
      .drop {
        position: relative;
        min-height: 200px;
        border-radius: var(--pp-radius);
        border: 2px dashed transparent;
        transition: border-color 0.15s;
      }
      .drop.active {
        border-color: var(--pp-accent);
      }
      .drop-hint {
        position: absolute;
        inset: 0;
        display: grid;
        place-items: center;
        background: color-mix(in srgb, var(--pp-accent) 12%, transparent);
        border-radius: var(--pp-radius);
        font-weight: 500;
        pointer-events: none;
      }
      .empty {
        display: grid;
        place-items: center;
        min-height: 200px;
        text-align: center;
        padding: 24px;
        border: 2px dashed var(--pp-border);
        border-radius: var(--pp-radius);
      }
      .grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
        gap: 12px;
      }
      .tile {
        position: relative;
        border-radius: 10px;
        overflow: hidden;
        background: var(--pp-surface);
        border: 1px solid var(--pp-border);
        cursor: pointer;
        transition: transform 0.1s, box-shadow 0.1s;
      }
      .tile:hover,
      .tile:focus-visible {
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.15);
        outline: none;
      }
      .tile.over {
        outline: 2px solid var(--pp-accent);
        transform: scale(0.97);
      }
      .tile.disabled img {
        opacity: 0.35;
        filter: grayscale(1);
      }
      .tile img {
        display: block;
        width: 100%;
        aspect-ratio: 1;
        object-fit: cover;
        background: var(--pp-bg);
      }
      .badges {
        position: absolute;
        top: 6px;
        left: 6px;
        right: 6px;
        display: flex;
        flex-wrap: wrap;
        gap: 4px;
      }
      .badges .chip {
        background: var(--pp-surface);
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
      }
      .badges .chip.ok {
        background: var(--pp-ok);
        color: #fff;
      }
      .badges svg.icon {
        width: 14px;
        height: 14px;
      }
      .caption {
        display: flex;
        align-items: center;
        gap: 4px;
        padding: 4px 4px 4px 10px;
      }
      .name {
        flex: 1;
        font-size: 14px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
      .icon-btn.small {
        width: 32px;
        height: 32px;
      }
      ul {
        margin: 4px 0 12px;
      }
    `
];
w([
  d({ attribute: !1 })
], b.prototype, "hass", 2);
w([
  d({ attribute: !1 })
], b.prototype, "frame", 2);
w([
  d({ attribute: !1 })
], b.prototype, "photos", 2);
w([
  l()
], b.prototype, "dropActive", 2);
w([
  l()
], b.prototype, "uploading", 2);
w([
  l()
], b.prototype, "uploadErrors", 2);
w([
  l()
], b.prototype, "error", 2);
w([
  l()
], b.prototype, "importOpen", 2);
w([
  l()
], b.prototype, "dragId", 2);
w([
  l()
], b.prototype, "dragOverId", 2);
b = w([
  C("pp-library")
], b);
var Nt = Object.defineProperty, qt = Object.getOwnPropertyDescriptor, j = (t, e, s, i) => {
  for (var a = i > 1 ? void 0 : i ? qt(e, s) : e, r = t.length - 1, p; r >= 0; r--)
    (p = t[r]) && (a = (i ? p(e, s, a) : p(a)) || a);
  return i && a && Nt(e, s, a), a;
};
const K = 5, D = (t, e = 0, s = 1) => Math.min(s, Math.max(e, t));
let P = class extends M {
  constructor() {
    super(...arguments), this.src = "", this.crop = null, this.focal = { x: 0.5, y: 0.5 }, this.aspect = null, this.draft = null, this.start = null;
  }
  point(t) {
    const e = this.img.getBoundingClientRect();
    return { x: D((t.clientX - e.left) / e.width), y: D((t.clientY - e.top) / e.height), r: e };
  }
  inside(t, e, s) {
    return !!t && e >= t[0] && e <= t[0] + t[2] && s >= t[1] && s <= t[1] + t[3];
  }
  onDown(t) {
    if (t.button !== 0) return;
    const e = this.point(t);
    t.currentTarget.setPointerCapture(t.pointerId);
    const s = this.inside(this.crop, e.x, e.y);
    this.start = { x: e.x, y: e.y, px: t.clientX, py: t.clientY, mode: s ? "move" : "new", orig: this.crop ?? void 0 };
  }
  onMove(t) {
    if (!this.start || Math.hypot(t.clientX - this.start.px, t.clientY - this.start.py) < K) return;
    const e = this.point(t);
    if (this.start.mode === "move" && this.start.orig) {
      const [F, et, J, B] = this.start.orig;
      this.draft = [D(F + e.x - this.start.x, 0, 1 - J), D(et + e.y - this.start.y, 0, 1 - B), J, B];
      return;
    }
    let s = Math.abs(e.x - this.start.x), i = Math.abs(e.y - this.start.y);
    if (this.aspect) {
      const F = this.aspect * e.r.height / e.r.width;
      s / i > F ? s = i * F : i = s / F;
    }
    const a = e.x < this.start.x ? this.start.x - s : this.start.x, r = e.y < this.start.y ? this.start.y - i : this.start.y, p = D(a, 0, 1 - s), Y = D(r, 0, 1 - i);
    this.draft = [p, Y, Math.min(s, 1 - p), Math.min(i, 1 - Y)];
  }
  onUp(t) {
    if (!this.start) return;
    const e = Math.hypot(t.clientX - this.start.px, t.clientY - this.start.py) >= K;
    if (e && this.draft && this.draft[2] > 0.02 && this.draft[3] > 0.02)
      this.fire("crop-changed", { crop: this.draft.map((s) => Math.round(s * 1e4) / 1e4) });
    else if (!e) {
      const s = this.point(t), [i, a, r, p] = this.crop ?? [0, 0, 1, 1];
      this.fire("focal-changed", {
        x: Math.round(D((s.x - i) / r) * 1e3) / 1e3,
        y: Math.round(D((s.y - a) / p) * 1e3) / 1e3
      });
    }
    this.start = null, this.draft = null;
  }
  fire(t, e) {
    this.dispatchEvent(new CustomEvent(t, { detail: e, bubbles: !0, composed: !0 }));
  }
  render() {
    const t = this.draft ?? this.crop, [e, s, i, a] = t ?? [0, 0, 1, 1], r = e + this.focal.x * i, p = s + this.focal.y * a;
    return o`<div
      class="wrap"
      @pointerdown=${this.onDown}
      @pointermove=${this.onMove}
      @pointerup=${this.onUp}
      @pointercancel=${() => (this.start = null, this.draft = null)}
    >
      <img src=${this.src} draggable="false" alt="" @load=${() => this.requestUpdate()} />
      ${t ? o`<div
            class="box"
            style="left:${e * 100}%;top:${s * 100}%;width:${i * 100}%;height:${a * 100}%"
          ></div>` : n}
      <div class="focal" style="left:${r * 100}%;top:${p * 100}%"></div>
    </div>`;
  }
};
P.styles = E`
    :host {
      display: flex;
      justify-content: center;
      user-select: none;
      touch-action: none;
    }
    .wrap {
      position: relative;
      display: inline-block;
      overflow: hidden;
      border-radius: 8px;
      cursor: crosshair;
      line-height: 0;
      background: repeating-conic-gradient(#ccc 0 25%, #eee 0 50%) 0 0 / 16px 16px;
    }
    img {
      display: block;
      max-width: 100%;
      max-height: min(56vh, 560px);
      pointer-events: none;
    }
    .box {
      position: absolute;
      box-shadow: 0 0 0 9999px rgba(0, 0, 0, 0.5);
      outline: 2px solid #fff;
      outline-offset: -1px;
      cursor: move;
    }
    .focal {
      position: absolute;
      width: 18px;
      height: 18px;
      margin: -9px 0 0 -9px;
      border-radius: 50%;
      border: 2px solid #fff;
      box-shadow: 0 0 0 2px rgba(0, 0, 0, 0.6);
      pointer-events: none;
    }
  `;
j([
  d()
], P.prototype, "src", 2);
j([
  d({ attribute: !1 })
], P.prototype, "crop", 2);
j([
  d({ attribute: !1 })
], P.prototype, "focal", 2);
j([
  d({ attribute: !1 })
], P.prototype, "aspect", 2);
j([
  l()
], P.prototype, "draft", 2);
j([
  xt("img")
], P.prototype, "img", 2);
P = j([
  C("pp-crop-area")
], P);
var Wt = Object.defineProperty, Rt = Object.getOwnPropertyDescriptor, z = (t, e, s, i) => {
  for (var a = i > 1 ? void 0 : i ? Rt(e, s) : e, r = t.length - 1, p; r >= 0; r--)
    (p = t[r]) && (a = (i ? p(e, s, a) : p(a)) || a);
  return i && a && Wt(e, s, a), a;
};
const W = {
  dither: ["floyd_steinberg", "atkinson", "jarvis_judice_ninke", "sierra2", "bayer", "none"],
  fit: ["cover", "contain", "stretch"],
  background: ["white", "black"],
  palette: ["perceived", "pure"]
}, Ut = ["brightness", "contrast", "saturation"];
let T = class extends M {
  constructor() {
    super(...arguments), this.value = {}, this.withPalette = !1;
  }
  get fields() {
    const t = [];
    return this.withPalette && t.push("palette"), t.push("dither", "serpentine", "fit", "background", ...Ut), t;
  }
  label(t, e) {
    const s = g(this.hass);
    return typeof e == "boolean" ? s(e ? "on" : "off") : typeof e == "number" ? e.toFixed(2) : W[t] ? s(`${t}_${e}`) : String(e);
  }
  emit(t) {
    this.dispatchEvent(new CustomEvent("value-changed", { detail: { value: t }, bubbles: !0, composed: !0 }));
  }
  setInherit(t, e) {
    const s = { ...this.value };
    e ? delete s[t] : s[t] = this.inherited[t], this.emit(s);
  }
  setField(t, e) {
    this.emit({ ...this.value, [t]: e });
  }
  control(t, e, s) {
    const i = g(this.hass);
    if (W[t])
      return o`<select
        .value=${String(e)}
        ?disabled=${s}
        @change=${(r) => this.setField(t, r.target.value)}
      >
        ${W[t].map(
        (r) => o`<option value=${r} ?selected=${r === e}>${i(`${t}_${r}`)}</option>`
      )}
      </select>`;
    if (t === "serpentine")
      return o`<select
        ?disabled=${s}
        @change=${(r) => this.setField(t, r.target.value === "on")}
      >
        <option value="on" ?selected=${e === !0}>${i("on")}</option>
        <option value="off" ?selected=${e !== !0}>${i("off")}</option>
      </select>`;
    const a = Number(e);
    return o`<div class="slider">
      <input
        type="range"
        min="0"
        max="2"
        step="0.05"
        .value=${String(a)}
        ?disabled=${s}
        @input=${(r) => this.setField(t, Number(r.target.value))}
      />
      <span class="num">${a.toFixed(2)}</span>
    </div>`;
  }
  render() {
    if (!this.inherited) return n;
    const t = g(this.hass);
    return o`${this.fields.map((e) => {
      const s = this.value[e] !== void 0, i = s ? this.value[e] : this.inherited[e];
      return o`<div class="row">
        <div class="head">
          <span class="name">${t(e)}</span>
          <label class="inherit">
            <input
              type="checkbox"
              .checked=${!s}
              @change=${(a) => this.setInherit(e, a.target.checked)}
            />
            ${t("inherited_value", { value: this.label(e, this.inherited[e]) })}
          </label>
        </div>
        <div class=${s ? "ctl" : "ctl inherited"}>${this.control(e, i, !s)}</div>
      </div>`;
    })}`;
  }
};
T.styles = [
  A,
  E`
      :host {
        display: grid;
        gap: 14px;
      }
      .row {
        display: grid;
        gap: 6px;
      }
      .head {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 8px;
        flex-wrap: wrap;
      }
      .name {
        font-weight: 500;
      }
      .inherit {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        font-size: 13px;
        color: var(--pp-muted);
        cursor: pointer;
      }
      .ctl select {
        width: 100%;
      }
      .ctl.inherited {
        opacity: 0.55;
      }
      .slider {
        display: flex;
        align-items: center;
        gap: 10px;
      }
      .slider input {
        flex: 1;
      }
      .num {
        font-variant-numeric: tabular-nums;
        min-width: 3.2em;
        text-align: right;
      }
    `
];
z([
  d({ attribute: !1 })
], T.prototype, "hass", 2);
z([
  d({ attribute: !1 })
], T.prototype, "value", 2);
z([
  d({ attribute: !1 })
], T.prototype, "inherited", 2);
z([
  d({ type: Boolean, attribute: "with-palette" })
], T.prototype, "withPalette", 2);
T = z([
  C("pp-render-settings")
], T);
function U(t, ...e) {
  const s = { ...t };
  for (const i of e)
    for (const [a, r] of Object.entries(i ?? {}))
      r != null && a in t && (s[a] = r);
  return s;
}
var Lt = Object.defineProperty, Yt = Object.getOwnPropertyDescriptor, v = (t, e, s, i) => {
  for (var a = i > 1 ? void 0 : i ? Yt(e, s) : e, r = t.length - 1, p; r >= 0; r--)
    (p = t[r]) && (a = (i ? p(e, s, a) : p(a)) || a);
  return i && a && Lt(e, s, a), a;
};
const Jt = 350, H = ["dither", "serpentine", "fit", "background", "brightness", "contrast", "saturation"];
let f = class extends M {
  constructor() {
    super(...arguments), this.frames = [], this.draft = {}, this.name = "", this.enabled = !0, this.preview = null, this.rendering = !1, this.lockAspect = !0, this.error = null, this.notice = null, this.busy = !1, this.previewSeq = 0, this.onKey = (t) => {
      t.key === "Escape" && this.close();
    };
  }
  connectedCallback() {
    super.connectedCallback(), window.addEventListener("keydown", this.onKey);
  }
  disconnectedCallback() {
    super.disconnectedCallback(), window.removeEventListener("keydown", this.onKey), window.clearTimeout(this.previewTimer);
  }
  willUpdate(t) {
    t.has("photo") && this.photo && (this.draft = structuredClone(this.photo.overrides ?? {}), this.name = this.photo.name, this.enabled = this.photo.enabled, this.lockAspect = !0, this.schedulePreview(0));
  }
  get resolved() {
    return U(this.inherited, this.draft);
  }
  get rotation() {
    return this.draft.rotation ?? 0;
  }
  get aspect() {
    return this.frame.canvas.width / this.frame.canvas.height;
  }
  get dirty() {
    return this.name !== this.photo.name || this.enabled !== this.photo.enabled || JSON.stringify(this.draft) !== JSON.stringify(this.photo.overrides ?? {});
  }
  setDraft(t, e = []) {
    const s = { ...this.draft, ...t };
    for (const i of e) delete s[i];
    this.draft = s, this.schedulePreview();
  }
  schedulePreview(t = Jt) {
    window.clearTimeout(this.previewTimer), this.previewTimer = window.setTimeout(() => this.loadPreview(), t);
  }
  async loadPreview() {
    const t = ++this.previewSeq;
    this.rendering = !0;
    try {
      const e = await tt(this.hass, this.frame.entry_id, this.photo.photo_id, {
        overrides: this.draft
      });
      t === this.previewSeq && (this.preview = e.image);
    } catch (e) {
      t === this.previewSeq && (this.error = u(e));
    } finally {
      t === this.previewSeq && (this.rendering = !1);
    }
  }
  rotate(t) {
    const e = ((this.rotation + t) % 360 + 360) % 360;
    this.setDraft(e ? { rotation: e } : {}, [
      ...e ? [] : ["rotation"],
      "crop",
      "focal_x",
      "focal_y"
    ]);
  }
  onSettings(t) {
    const e = t.detail.value, s = { ...this.draft };
    for (const i of H)
      e[i] === void 0 ? delete s[i] : s[i] = e[i];
    this.draft = s, this.schedulePreview();
  }
  async save() {
    this.busy = !0, this.error = null;
    try {
      await Q(this.hass, this.frame.entry_id, this.photo.photo_id, {
        name: this.name.trim() || this.photo.name,
        enabled: this.enabled,
        overrides: this.draft
      }), this.close();
    } catch (t) {
      this.error = u(t);
    } finally {
      this.busy = !1;
    }
  }
  async deleteClicked() {
    const t = g(this.hass);
    if (confirm(t("delete_confirm", { name: this.photo.name })))
      try {
        await _t(this.hass, this.frame.entry_id, this.photo.photo_id), this.close();
      } catch (e) {
        this.error = u(e);
      }
  }
  async showNext() {
    try {
      await Ot(this.hass, this.frame.entry_id, this.photo.photo_id), this.notice = g(this.hass)("pending");
    } catch (t) {
      this.error = u(t);
    }
  }
  async copyTo(t) {
    const e = t.target, s = this.frames.find((i) => i.entry_id === e.value);
    if (e.value = "", !!s)
      try {
        await Pt(this.hass, this.frame.entry_id, this.photo.photo_id, s.entry_id), this.notice = g(this.hass)("copied", { frame: s.title });
      } catch (i) {
        this.error = u(i);
      }
  }
  close() {
    this.dispatchEvent(new CustomEvent("closed", { bubbles: !0, composed: !0 }));
  }
  render() {
    if (!this.photo) return n;
    const t = g(this.hass), e = this.resolved.fit === "cover", s = this.frames.filter((r) => r.entry_id !== this.frame.entry_id), i = {};
    for (const r of H)
      this.draft[r] !== void 0 && (i[r] = this.draft[r]);
    const a = `aspect-ratio:${this.frame.canvas.width}/${this.frame.canvas.height}`;
    return o`<div class="scrim" @click=${(r) => r.target === r.currentTarget && this.close()}>
      <div class="dialog card" role="dialog" aria-modal="true" aria-label=${t("edit_photo")}>
        <header>
          <input
            class="title"
            type="text"
            .value=${this.name}
            aria-label=${t("name")}
            @input=${(r) => this.name = r.target.value}
          />
          <button class="icon-btn" title=${t("close")} @click=${this.close}>${c(V)}</button>
        </header>
        <div class="body">
          <section class="visual">
            <div class="section-title">
              <span>${t("crop")}</span>
              <span class="tools">
                <button class="icon-btn" title=${t("rotate_left")} @click=${() => this.rotate(-90)}>
                  ${c(ht)}
                </button>
                <button class="icon-btn" title=${t("rotate_right")} @click=${() => this.rotate(90)}>
                  ${c(ct)}
                </button>
              </span>
            </div>
            <pp-crop-area
              .src=${this.photo.display_urls[String(this.rotation)]}
              .crop=${this.draft.crop ?? null}
              .focal=${{ x: this.draft.focal_x ?? 0.5, y: this.draft.focal_y ?? 0.5 }}
              .aspect=${e && this.lockAspect ? this.aspect : null}
              @crop-changed=${(r) => this.setDraft({ crop: r.detail.crop })}
              @focal-changed=${(r) => this.setDraft({ focal_x: r.detail.x, focal_y: r.detail.y })}
            ></pp-crop-area>
            <div class="crop-tools">
              <span class="muted hint">${t("crop_hint")}</span>
              ${e ? o`<label class="check">
                    <input
                      type="checkbox"
                      .checked=${this.lockAspect}
                      @change=${(r) => this.lockAspect = r.target.checked}
                    />
                    ${t("lock_aspect")}
                  </label>` : n}
              <button class="btn" ?disabled=${!this.draft.crop} @click=${() => this.setDraft({}, ["crop"])}>
                ${t("clear_crop")}
              </button>
              <button
                class="btn"
                ?disabled=${this.draft.focal_x === void 0}
                @click=${() => this.setDraft({}, ["focal_x", "focal_y"])}
              >
                ${t("reset_focal")}
              </button>
            </div>
          </section>
          <section class="settings">
            <div class="section-title">
              <span>${t("preview")}</span>
              ${this.rendering ? o`<span class="muted">${t("rendering")}</span>` : n}
            </div>
            <div class="preview" style=${a}>
              ${this.preview ? o`<img src=${this.preview} alt=${t("preview")} />` : n}
            </div>
            <span class="muted hint">${t("preview_hint")}</span>
            <label class="check rotation">
              <input
                type="checkbox"
                .checked=${this.enabled}
                @change=${(r) => this.enabled = r.target.checked}
              />
              ${t("in_rotation")}
            </label>
            <div class="section-title"><span>${t("rendering_settings")}</span></div>
            <pp-render-settings
              .hass=${this.hass}
              .value=${i}
              .inherited=${this.inherited}
              @value-changed=${this.onSettings}
            ></pp-render-settings>
          </section>
        </div>
        ${this.error ? o`<div class="msg error">${t("error", { error: this.error })}</div>` : n}
        ${this.notice ? o`<div class="msg">${this.notice}</div>` : n}
        <footer>
          <button class="btn danger" @click=${this.deleteClicked}>${c(ut)} ${t("delete")}</button>
          <button class="btn" @click=${this.showNext}>${c(ft)} ${t("show_next")}</button>
          ${s.length ? o`<label class="copy">
                ${c(gt)}
                <select @change=${this.copyTo} aria-label=${t("copy_to")}>
                  <option value="">${t("copy_to")}</option>
                  ${s.map((r) => o`<option value=${r.entry_id}>${r.title}</option>`)}
                </select>
              </label>` : n}
          <span class="spacer"></span>
          ${this.dirty ? o`<span class="muted">${t("unsaved")}</span>` : n}
          <button class="btn" @click=${this.close}>${t("cancel")}</button>
          <button class="btn primary" ?disabled=${this.busy || !this.dirty} @click=${this.save}>
            ${t("save")}
          </button>
        </footer>
      </div>
    </div>`;
  }
};
f.styles = [
  A,
  E`
      .scrim {
        position: fixed;
        inset: 0;
        z-index: 10;
        background: rgba(0, 0, 0, 0.45);
        display: grid;
        place-items: center;
        padding: 16px;
      }
      .dialog {
        width: min(1100px, 100%);
        max-height: calc(100vh - 32px);
        display: flex;
        flex-direction: column;
        overflow: hidden;
      }
      header,
      footer {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 12px 16px;
      }
      header {
        border-bottom: 1px solid var(--pp-border);
      }
      footer {
        border-top: 1px solid var(--pp-border);
        flex-wrap: wrap;
      }
      .title {
        flex: 1;
        font-size: 18px;
        font-weight: 500;
        border-color: transparent;
        background: transparent;
      }
      .title:hover,
      .title:focus {
        border-color: var(--pp-border);
      }
      .body {
        display: grid;
        grid-template-columns: minmax(0, 3fr) minmax(300px, 2fr);
        gap: 24px;
        padding: 16px;
        overflow: auto;
      }
      .visual,
      .settings {
        display: flex;
        flex-direction: column;
        gap: 10px;
        min-width: 0;
      }
      .section-title {
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-weight: 500;
        min-height: 40px;
      }
      .tools {
        display: flex;
      }
      .crop-tools {
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        gap: 8px;
      }
      .hint {
        font-size: 13px;
        flex-basis: 100%;
      }
      .check {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        cursor: pointer;
      }
      .rotation {
        font-weight: 500;
        padding: 8px 0;
      }
      .preview {
        flex: none;
        height: min(340px, 45vh);
        max-width: 100%;
        margin: 0 auto;
        background: #d6d6d6;
        border-radius: 6px;
        overflow: hidden;
        display: grid;
        place-items: center;
        box-shadow: inset 0 0 0 1px var(--pp-border);
      }
      .preview img {
        width: 100%;
        height: 100%;
        object-fit: contain;
        image-rendering: pixelated;
      }
      .msg {
        padding: 0 16px 8px;
      }
      .copy {
        display: inline-flex;
        align-items: center;
        gap: 4px;
      }
      .spacer {
        flex: 1;
      }
      @media (max-width: 760px) {
        .body {
          grid-template-columns: 1fr;
        }
        .scrim {
          padding: 0;
        }
        .dialog {
          max-height: 100vh;
          height: 100vh;
          border-radius: 0;
        }
      }
    `
];
v([
  d({ attribute: !1 })
], f.prototype, "hass", 2);
v([
  d({ attribute: !1 })
], f.prototype, "frame", 2);
v([
  d({ attribute: !1 })
], f.prototype, "frames", 2);
v([
  d({ attribute: !1 })
], f.prototype, "photo", 2);
v([
  d({ attribute: !1 })
], f.prototype, "inherited", 2);
v([
  l()
], f.prototype, "draft", 2);
v([
  l()
], f.prototype, "name", 2);
v([
  l()
], f.prototype, "enabled", 2);
v([
  l()
], f.prototype, "preview", 2);
v([
  l()
], f.prototype, "rendering", 2);
v([
  l()
], f.prototype, "lockAspect", 2);
v([
  l()
], f.prototype, "error", 2);
v([
  l()
], f.prototype, "notice", 2);
v([
  l()
], f.prototype, "busy", 2);
f = v([
  C("pp-photo-editor")
], f);
var Bt = Object.defineProperty, Gt = Object.getOwnPropertyDescriptor, h = (t, e, s, i) => {
  for (var a = i > 1 ? void 0 : i ? Gt(e, s) : e, r = t.length - 1, p; r >= 0; r--)
    (p = t[r]) && (a = (i ? p(e, s, a) : p(a)) || a);
  return i && a && Bt(e, s, a), a;
};
const Xt = 400, Kt = ["portrait", "landscape", "portrait_flipped", "landscape_flipped"], L = class L extends M {
  constructor() {
    super(...arguments), this.preview = null, this.previewAspect = "5 / 3", this.rendering = !1, this.error = null, this.status = null, this.seq = 0;
  }
  disconnectedCallback() {
    super.disconnectedCallback(), window.clearTimeout(this.timer);
  }
  schedulePreview(e = Xt) {
    window.clearTimeout(this.timer), this.timer = window.setTimeout(() => this.loadPreview(), e);
  }
  async loadPreview() {
    const e = this.previewRequest();
    if (!e) {
      this.preview = null;
      return;
    }
    const s = ++this.seq;
    this.rendering = !0;
    try {
      const i = await tt(this.hass, e.frame.entry_id, e.photoId, e.settings);
      s === this.seq && (this.preview = i.image, this.previewAspect = `${i.width} / ${i.height}`);
    } catch (i) {
      s === this.seq && (this.error = u(i));
    } finally {
      s === this.seq && (this.rendering = !1);
    }
  }
  renderPreviewPane(e) {
    const s = g(this.hass);
    return o`<div class="preview-pane">
      <div class="pane-head">
        <span class="h">${s("preview")}</span>
        ${this.rendering ? o`<span class="muted">${s("rendering")}</span>` : n}
      </div>
      ${e}
      <div class="preview" style="aspect-ratio:${this.previewAspect}">
        ${this.preview ? o`<img src=${this.preview} alt=${s("preview")} />` : n}
      </div>
      <span class="muted hint">${s("preview_hint")}</span>
    </div>`;
  }
};
L.styles = [
  A,
  E`
      :host {
        display: grid;
        grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
        gap: 24px;
        align-items: start;
      }
      .form {
        display: grid;
        gap: 16px;
        padding: 16px;
      }
      .form h3 {
        margin: 8px 0 0;
        font-size: 16px;
        font-weight: 500;
      }
      .preview-pane {
        position: sticky;
        top: 16px;
        display: grid;
        gap: 10px;
        padding: 16px;
      }
      .pane-head {
        display: flex;
        justify-content: space-between;
        align-items: center;
      }
      .h {
        font-weight: 500;
      }
      .preview {
        height: min(440px, 55vh);
        max-width: 100%;
        margin: 0 auto;
        background: #d6d6d6;
        border-radius: 6px;
        overflow: hidden;
        box-shadow: inset 0 0 0 1px var(--pp-border);
      }
      .preview img {
        width: 100%;
        height: 100%;
        object-fit: contain;
        image-rendering: pixelated;
      }
      .hint {
        font-size: 13px;
      }
      .actions {
        display: flex;
        align-items: center;
        justify-content: flex-end;
        gap: 8px;
      }
      @media (max-width: 860px) {
        :host {
          grid-template-columns: 1fr;
        }
        .preview-pane {
          position: static;
        }
      }
    `
];
let x = L;
h([
  d({ attribute: !1 })
], x.prototype, "hass", 2);
h([
  l()
], x.prototype, "preview", 2);
h([
  l()
], x.prototype, "previewAspect", 2);
h([
  l()
], x.prototype, "rendering", 2);
h([
  l()
], x.prototype, "error", 2);
h([
  l()
], x.prototype, "status", 2);
let O = class extends x {
  constructor() {
    super(...arguments), this.photos = [], this.draft = {}, this.mounting = "portrait", this.intervalMin = 60, this.sampleId = null;
  }
  willUpdate(t) {
    t.has("frame") && t.get("frame")?.entry_id !== this.frame.entry_id && this.reset(), t.has("photos") && !this.photos.some((e) => e.photo_id === this.sampleId) && (this.sampleId = this.photos[0]?.photo_id ?? null, this.schedulePreview(0));
  }
  reset() {
    this.draft = structuredClone(this.frame.render_defaults ?? {}), this.mounting = this.frame.mounting, this.intervalMin = Math.round(this.frame.interval / 60), this.status = null, this.schedulePreview(0);
  }
  get dirty() {
    return JSON.stringify(this.draft) !== JSON.stringify(this.frame.render_defaults ?? {}) || this.mounting !== this.frame.mounting || this.intervalMin * 60 !== this.frame.interval;
  }
  previewRequest() {
    return this.sampleId ? { frame: this.frame, photoId: this.sampleId, settings: { frame_defaults: this.draft } } : null;
  }
  async save() {
    this.error = null;
    try {
      await Z(this.hass, this.frame.entry_id, {
        render_defaults: this.draft,
        mounting: this.mounting,
        interval: Math.max(1, this.intervalMin) * 60
      }), this.status = "saved", this.schedulePreview(200);
    } catch (t) {
      this.error = u(t);
    }
  }
  render() {
    if (!this.defaults) return n;
    const t = g(this.hass), e = U(this.defaults.builtin, this.defaults.defaults), s = this.photos.length ? o`<label class="field">
          <span class="muted">${t("sample_photo")}</span>
          <select
            @change=${(i) => {
      this.sampleId = i.target.value, this.schedulePreview(0);
    }}
          >
            ${this.photos.map(
      (i) => o`<option value=${i.photo_id} ?selected=${i.photo_id === this.sampleId}>${i.name}</option>`
    )}
          </select>
        </label>` : n;
    return o`
      <div class="form card">
        <h3>${t("frame_settings")}</h3>
        <label class="field">
          ${t("mounting")}
          <select @change=${(i) => this.mounting = i.target.value}>
            ${Kt.map(
      (i) => o`<option value=${i} ?selected=${i === this.mounting}>${t(`mounting_${i}`)}</option>`
    )}
          </select>
        </label>
        <label class="field">
          ${t("interval")}
          <input
            type="number"
            min="1"
            max="10080"
            .value=${String(this.intervalMin)}
            @input=${(i) => this.intervalMin = Number(i.target.value) || 1}
          />
        </label>
        <h3>${t("frame_defaults")}</h3>
        <span class="muted">${t("frame_defaults_hint")}</span>
        <pp-render-settings
          with-palette
          .hass=${this.hass}
          .value=${this.draft}
          .inherited=${e}
          @value-changed=${(i) => {
      this.draft = i.detail.value, this.status = null, this.schedulePreview();
    }}
        ></pp-render-settings>
        <span class="muted hint">${t("more_options")}</span>
        ${this.error ? o`<span class="error">${t("error", { error: this.error })}</span>` : n}
        <div class="actions">
          ${this.dirty ? o`<span class="muted">${t("unsaved")}</span>` : n}
          ${!this.dirty && this.status === "saved" ? o`<span class="chip ok">${t("saved")}</span>` : n}
          <button class="btn" ?disabled=${!this.dirty} @click=${this.reset}>${t("cancel")}</button>
          <button class="btn primary" ?disabled=${!this.dirty} @click=${this.save}>${t("save")}</button>
        </div>
      </div>
      ${this.renderPreviewPane(s)}
    `;
  }
};
h([
  d({ attribute: !1 })
], O.prototype, "frame", 2);
h([
  d({ attribute: !1 })
], O.prototype, "photos", 2);
h([
  d({ attribute: !1 })
], O.prototype, "defaults", 2);
h([
  l()
], O.prototype, "draft", 2);
h([
  l()
], O.prototype, "mounting", 2);
h([
  l()
], O.prototype, "intervalMin", 2);
h([
  l()
], O.prototype, "sampleId", 2);
O = h([
  C("pp-frame-settings")
], O);
let S = class extends x {
  constructor() {
    super(...arguments), this.frames = [], this.draft = {}, this.sampleFrameId = null, this.samplePhotos = [], this.samplePhotoId = null;
  }
  willUpdate(t) {
    t.has("defaults") && this.defaults && !t.get("defaults") && (this.draft = structuredClone(this.defaults.defaults ?? {})), t.has("frames") && !this.sampleFrameId && this.frames.length && this.pickFrame(this.frames.find((e) => e.photo_count)?.entry_id ?? this.frames[0].entry_id);
  }
  async pickFrame(t) {
    this.sampleFrameId = t, this.samplePhotos = await R(this.hass, t), this.samplePhotoId = this.samplePhotos[0]?.photo_id ?? null, this.schedulePreview(0);
  }
  get dirty() {
    return JSON.stringify(this.draft) !== JSON.stringify(this.defaults?.defaults ?? {});
  }
  previewRequest() {
    const t = this.frames.find((e) => e.entry_id === this.sampleFrameId);
    return !t || !this.samplePhotoId ? null : { frame: t, photoId: this.samplePhotoId, settings: { global_defaults: this.draft } };
  }
  async save() {
    this.error = null;
    try {
      const t = await Et(this.hass, this.draft);
      this.defaults = { ...this.defaults, defaults: t.defaults }, this.status = "saved";
    } catch (t) {
      this.error = u(t);
    }
  }
  render() {
    if (!this.defaults) return n;
    const t = g(this.hass), e = o`<div class="sample">
      <select
        aria-label=${t("frames")}
        @change=${(s) => this.pickFrame(s.target.value)}
      >
        ${this.frames.map(
      (s) => o`<option value=${s.entry_id} ?selected=${s.entry_id === this.sampleFrameId}>${s.title}</option>`
    )}
      </select>
      <select
        aria-label=${t("sample_photo")}
        @change=${(s) => {
      this.samplePhotoId = s.target.value, this.schedulePreview(0);
    }}
      >
        ${this.samplePhotos.map(
      (s) => o`<option value=${s.photo_id} ?selected=${s.photo_id === this.samplePhotoId}>${s.name}</option>`
    )}
      </select>
    </div>`;
    return o`
      <div class="form card">
        <h3>${t("global_defaults")}</h3>
        <span class="muted">${t("global_defaults_hint")}</span>
        <pp-render-settings
          with-palette
          .hass=${this.hass}
          .value=${this.draft}
          .inherited=${this.defaults.builtin}
          @value-changed=${(s) => {
      this.draft = s.detail.value, this.status = null, this.schedulePreview();
    }}
        ></pp-render-settings>
        ${this.error ? o`<span class="error">${t("error", { error: this.error })}</span>` : n}
        <div class="actions">
          ${this.dirty ? o`<span class="muted">${t("unsaved")}</span>` : n}
          ${!this.dirty && this.status === "saved" ? o`<span class="chip ok">${t("saved")}</span>` : n}
          <button
            class="btn"
            ?disabled=${!this.dirty}
            @click=${() => {
      this.draft = structuredClone(this.defaults.defaults ?? {}), this.schedulePreview(0);
    }}
          >
            ${t("cancel")}
          </button>
          <button class="btn primary" ?disabled=${!this.dirty} @click=${this.save}>${t("save")}</button>
        </div>
      </div>
      ${this.renderPreviewPane(this.frames.length ? e : n)}
    `;
  }
};
S.styles = [
  ...x.styles,
  E`
      .sample {
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
      }
      .sample select {
        flex: 1;
        min-width: 0;
      }
    `
];
h([
  d({ attribute: !1 })
], S.prototype, "frames", 2);
h([
  d({ attribute: !1 })
], S.prototype, "defaults", 2);
h([
  l()
], S.prototype, "draft", 2);
h([
  l()
], S.prototype, "sampleFrameId", 2);
h([
  l()
], S.prototype, "samplePhotos", 2);
h([
  l()
], S.prototype, "samplePhotoId", 2);
S = h([
  C("pp-global-settings")
], S);
var Ht = Object.defineProperty, Vt = Object.getOwnPropertyDescriptor, _ = (t, e, s, i) => {
  for (var a = i > 1 ? void 0 : i ? Vt(e, s) : e, r = t.length - 1, p; r >= 0; r--)
    (p = t[r]) && (a = (i ? p(e, s, a) : p(a)) || a);
  return i && a && Ht(e, s, a), a;
};
const k = "global", Qt = 250;
let $ = class extends M {
  constructor() {
    super(...arguments), this.narrow = !1, this.frames = null, this.selected = null, this.tab = "photos", this.photos = [], this.defaults = null, this.editing = null, this.error = null, this.dirtyEntries = /* @__PURE__ */ new Set();
  }
  connectedCallback() {
    super.connectedCallback(), this.hass && this.start();
  }
  disconnectedCallback() {
    super.disconnectedCallback(), this.unsubscribe?.then((t) => t()).catch(() => {
    }), this.unsubscribe = void 0, window.clearTimeout(this.refreshTimer);
  }
  willUpdate(t) {
    t.has("hass") && this.hass && !this.unsubscribe && this.isConnected && this.start();
  }
  start() {
    this.unsubscribe = wt(this.hass, (t) => {
      this.dirtyEntries.add(t), window.clearTimeout(this.refreshTimer), this.refreshTimer = window.setTimeout(() => this.refresh(), Qt);
    }), this.loadAll();
  }
  async loadAll() {
    try {
      const [t, e] = await Promise.all([G(this.hass), Dt(this.hass)]);
      this.frames = t, this.defaults = e;
      const s = this.route?.path?.replace(/^\//, "").split("/")[0], i = s && (s === k || t.some((a) => a.entry_id === s)) && s || t[0]?.entry_id || null;
      i && await this.select(i);
    } catch (t) {
      this.error = u(t);
    }
  }
  async refresh() {
    const t = new Set(this.dirtyEntries);
    this.dirtyEntries.clear();
    try {
      this.frames = await G(this.hass), this.selected && this.selected !== k && (this.frames.some((e) => e.entry_id === this.selected) ? (t.has(this.selected) || t.has(null)) && (this.photos = await R(this.hass, this.selected)) : await this.select(this.frames[0]?.entry_id ?? k));
    } catch (e) {
      this.error = u(e);
    }
  }
  async select(t) {
    if (this.selected = t, this.editing = null, history.replaceState(null, "", `/paperlessoffline/${t}`), t === k) {
      this.photos = [];
      return;
    }
    try {
      this.photos = await R(this.hass, t);
    } catch (e) {
      this.error = u(e);
    }
  }
  get frame() {
    return this.frames?.find((t) => t.entry_id === this.selected);
  }
  /** The frame's "Showing"/"Up next" image entity, for its tokenised picture URL. */
  previewUrl(t, e) {
    if (!t.device_id) return null;
    const s = Object.values(this.hass.entities ?? {}).find(
      (i) => i.device_id === t.device_id && i.platform === "paperlessoffline" && i.translation_key === e
    );
    return s && this.hass.states[s.entity_id]?.attributes.entity_picture || null;
  }
  toggleMenu() {
    this.dispatchEvent(new CustomEvent("hass-toggle-menu", { bubbles: !0, composed: !0 }));
  }
  renderNav() {
    const t = g(this.hass);
    return this.narrow ? o`<div class="nav-narrow">
        <select @change=${(e) => this.select(e.target.value)}>
          ${(this.frames ?? []).map(
      (e) => o`<option value=${e.entry_id} ?selected=${e.entry_id === this.selected}>${e.title}</option>`
    )}
          <option value=${k} ?selected=${this.selected === k}>${t("global_defaults")}</option>
        </select>
      </div>` : o`<nav>
      <div class="nav-title muted">${t("frames")}</div>
      ${(this.frames ?? []).map(
      (e) => o`<button
          class="nav-item ${e.entry_id === this.selected ? "active" : ""}"
          @click=${() => this.select(e.entry_id)}
        >
          ${c(mt)}
          <span class="nav-text">
            <span>${e.title}</span>
            <span class="muted small">${N(e.last_seen, this.hass, t("never"))}</span>
          </span>
          ${e.pending.length ? o`<span class="dot" title=${t("pending")}></span>` : n}
        </button>`
    )}
      <hr />
      <button
        class="nav-item ${this.selected === k ? "active" : ""}"
        @click=${() => this.select(k)}
      >
        ${c(vt)} <span class="nav-text">${t("global_defaults")}</span>
      </button>
    </nav>`;
  }
  renderStatus(t) {
    const e = g(this.hass), s = this.previewUrl(t, "preview_showing"), i = this.previewUrl(t, "preview_up_next"), a = t.up_next.kind === "override" ? e("override") : t.up_next.kind === "placeholder" ? e("placeholder") : t.up_next.name ?? "";
    return o`<div class="status card">
      <figure>
        <div class="pic" style="aspect-ratio:${t.canvas.width}/${t.canvas.height}">
          ${s ? o`<img src=${s} alt="" />` : n}
        </div>
        <figcaption><span class="muted">${e("showing")}</span> ${t.current.name ?? ""}</figcaption>
      </figure>
      <figure>
        <div class="pic" style="aspect-ratio:${t.canvas.width}/${t.canvas.height}">
          ${i ? o`<img src=${i} alt="" />` : n}
        </div>
        <figcaption><span class="muted">${e("up_next")}</span> ${a}</figcaption>
      </figure>
      <div class="facts">
        <h1>${t.title}</h1>
        <div class="muted">${t.panel.model} · ${t.client_id}</div>
        <div>
          ${e("last_seen")}: <strong>${N(t.last_seen, this.hass, e("never"))}</strong>
        </div>
        <div class="chips">
          ${t.pending.length ? o`<span class="chip warn">
                ${e("pending")}: ${t.pending.map((r) => e(`pending_${r}`)).join(", ")}
              </span>` : o`<span class="chip ok">${e("in_sync")}</span>`}
          ${t.needs_reprovision ? o`<span class="chip warn">${e("needs_urls")}</span>` : t.overdue ? o`<span class="chip warn">${e("overdue")}</span>` : n}
          ${t.ble?.voltage !== void 0 ? o`<span class="chip" title=${e("read_ago", { when: N(t.ble.read_at, this.hass, e("never")) })}>
                ${e("battery", { volts: (t.ble.voltage / 1e3).toFixed(2) })}${t.ble.charging ? ` · ${e("charging")}` : t.ble.usb ? ` · ${e("usb")}` : ""}
              </span>` : n}
          ${t.override ? o`<span class="chip">
                ${e("override")}: ${t.override.name} ·
                ${t.override.wakes_remaining === null ? e("until_cleared") : e("wakes_left", { n: t.override.wakes_remaining })}
              </span>` : n}
        </div>
        <div>
          <button
            class="btn"
            ?disabled=${t.up_next.kind !== "photo" || t.enabled_count < 2}
            @click=${() => St(this.hass, t.entry_id).catch((r) => this.error = u(r))}
          >
            ${c(bt)} ${e("skip")}
          </button>
        </div>
      </div>
    </div>`;
  }
  renderMain() {
    const t = g(this.hass);
    if (this.frames === null) return o`<p class="muted">${t("loading")}</p>`;
    if (this.selected === k)
      return o`<pp-global-settings
        .hass=${this.hass}
        .frames=${this.frames}
        .defaults=${this.defaults}
      ></pp-global-settings>`;
    const e = this.frame;
    return e ? o`
      ${this.renderStatus(e)}
      <div class="tabs" role="tablist">
        ${["photos", "settings"].map(
      (s) => o`<button
            role="tab"
            aria-selected=${this.tab === s}
            class=${this.tab === s ? "active" : ""}
            @click=${() => this.tab = s}
          >
            ${t(`tab_${s}`)}
          </button>`
    )}
      </div>
      ${this.tab === "photos" ? o`<pp-library
            .hass=${this.hass}
            .frame=${e}
            .photos=${this.photos}
            @edit-photo=${(s) => this.editing = s.detail.photo}
          ></pp-library>` : o`<pp-frame-settings
            .hass=${this.hass}
            .frame=${e}
            .photos=${this.photos}
            .defaults=${this.defaults}
          ></pp-frame-settings>`}
      ${this.editing && this.defaults ? o`<pp-photo-editor
            .hass=${this.hass}
            .frame=${e}
            .frames=${this.frames}
            .photo=${this.editing}
            .inherited=${U(this.defaults.builtin, this.defaults.defaults, e.render_defaults)}
            @closed=${() => this.editing = null}
          ></pp-photo-editor>` : n}
    ` : o`<p class="muted empty">${t("no_frames")}</p>`;
  }
  render() {
    const t = g(this.hass);
    return o`
      <header class="toolbar">
        ${this.narrow ? o`<button class="icon-btn" title="Menu" @click=${this.toggleMenu}>${c($t)}</button>` : n}
        <div class="app-title">${t("title")}</div>
      </header>
      <div class="layout">
        ${this.frames?.length ? this.renderNav() : n}
        <main>
          ${this.error ? o`<p class="error" @click=${() => this.error = null}>${t("error", { error: this.error })}</p>` : n}
          ${this.renderMain()}
        </main>
      </div>
    `;
  }
};
$.styles = [
  A,
  E`
      :host {
        display: block;
        min-height: 100vh;
        background: var(--pp-bg);
      }
      .toolbar {
        position: sticky;
        top: 0;
        z-index: 2;
        display: flex;
        align-items: center;
        gap: 8px;
        height: var(--header-height, 56px);
        padding: 0 12px;
        background: var(--app-header-background-color, var(--pp-surface));
        color: var(--app-header-text-color, var(--pp-text));
        border-bottom: var(--app-header-border-bottom, 1px solid var(--pp-border));
      }
      .app-title {
        margin-left: 12px;
        font-size: 20px;
      }
      .layout {
        display: flex;
        align-items: flex-start;
      }
      nav {
        position: sticky;
        top: var(--header-height, 56px);
        width: 260px;
        flex: none;
        padding: 12px 8px;
        display: grid;
        gap: 2px;
      }
      .nav-title {
        padding: 4px 12px 8px;
        font-size: 13px;
        text-transform: uppercase;
        letter-spacing: 0.04em;
      }
      .nav-item {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 8px 12px;
        border-radius: 10px;
        border: none;
        background: transparent;
        color: inherit;
        text-align: left;
      }
      .nav-item:hover {
        background: color-mix(in srgb, var(--pp-text) 6%, transparent);
      }
      .nav-item.active {
        background: color-mix(in srgb, var(--pp-accent) 14%, transparent);
        color: var(--pp-accent);
      }
      .nav-text {
        flex: 1;
        display: grid;
        min-width: 0;
      }
      .nav-text > span {
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
      .small {
        font-size: 12px;
      }
      .dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: var(--pp-warn);
      }
      hr {
        border: none;
        border-top: 1px solid var(--pp-border);
        margin: 8px 4px;
        width: calc(100% - 8px);
      }
      .nav-narrow {
        padding: 12px 16px 0;
      }
      .nav-narrow select {
        width: 100%;
      }
      main {
        flex: 1;
        min-width: 0;
        max-width: 1400px;
        padding: 16px 24px 48px;
        display: grid;
        gap: 16px;
      }
      :host([narrow]) .layout {
        display: block;
      }
      :host([narrow]) main {
        padding: 16px;
      }
      .status {
        display: grid;
        grid-template-columns: minmax(0, 200px) minmax(0, 200px) 1fr;
        gap: 20px;
        padding: 16px;
        align-items: start;
      }
      figure {
        margin: 0;
        display: grid;
        gap: 6px;
      }
      .pic {
        height: 240px;
        max-width: calc(100% - 12px);
        background: #d6d6d6;
        border-radius: 4px;
        overflow: hidden;
        box-shadow: 0 0 0 6px #2b2b2b, 0 2px 12px 6px rgba(0, 0, 0, 0.25);
        margin: 6px;
      }
      .pic img {
        width: 100%;
        height: 100%;
        object-fit: contain;
        display: block;
      }
      figcaption {
        font-size: 13px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        padding: 4px 6px 0;
      }
      .facts {
        display: grid;
        gap: 8px;
        align-content: start;
      }
      h1 {
        margin: 0;
        font-size: 24px;
        font-weight: 400;
      }
      .chips {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
      }
      @media (max-width: 760px) {
        .status {
          grid-template-columns: 1fr 1fr;
        }
        .pic {
          height: 170px;
        }
        .facts {
          grid-column: 1 / -1;
          grid-row: 1;
        }
      }
      .tabs {
        display: flex;
        gap: 4px;
        border-bottom: 1px solid var(--pp-border);
      }
      .tabs button {
        padding: 10px 16px;
        border: none;
        border-bottom: 2px solid transparent;
        background: transparent;
        color: var(--pp-muted);
        font-weight: 500;
      }
      .tabs button.active {
        color: var(--pp-accent);
        border-bottom-color: var(--pp-accent);
      }
      .empty {
        padding: 48px;
        text-align: center;
      }
    `
];
_([
  d({ attribute: !1 })
], $.prototype, "hass", 2);
_([
  d({ type: Boolean, reflect: !0 })
], $.prototype, "narrow", 2);
_([
  d({ attribute: !1 })
], $.prototype, "route", 2);
_([
  l()
], $.prototype, "frames", 2);
_([
  l()
], $.prototype, "selected", 2);
_([
  l()
], $.prototype, "tab", 2);
_([
  l()
], $.prototype, "photos", 2);
_([
  l()
], $.prototype, "defaults", 2);
_([
  l()
], $.prototype, "editing", 2);
_([
  l()
], $.prototype, "error", 2);
$ = _([
  C("paperlessoffline-panel")
], $);
export {
  $ as PaperlessPanel
};
