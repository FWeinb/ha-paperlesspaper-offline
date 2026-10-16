import { s as A, i as E, n as d, r as l, a as j, l as m, A as n, d as u, f as mt, b as o, g as K, h as vt, j as yt, k as bt, t as S, o as $t, p as xt, q as wt, u as _t, v as kt, w as lt, x as Pt, y as Ot, z as Et, B as pt, C as St, D as It, E as Dt, F as Ct, c as U, G as Tt, e as jt, H as zt } from "./chunk-DY6Sag5H.js";
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const Mt = (t, e, s) => (s.configurable = !0, s.enumerable = !0, Reflect.decorate && typeof e != "object" && Object.defineProperty(t, e, s), s);
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
function At(t, e) {
  return (s, i, r) => {
    const a = (p) => p.renderRoot?.querySelector(t) ?? null;
    return Mt(s, i, { get() {
      return a(this);
    } });
  };
}
const f = "paperlessoffline", st = (t) => t.callWS({ type: `${f}/frames` }).then((e) => e.frames), H = (t, e) => t.callWS({ type: `${f}/photos`, entry_id: e }).then((s) => s.photos), Ft = (t, e) => t.connection.subscribeMessage((s) => e(s.entry_id), {
  type: `${f}/subscribe`
}), dt = (t, e, s, i) => t.callWS({ type: `${f}/photo/update`, entry_id: e, photo_id: s, ...i }), Wt = (t, e, s) => t.callWS({ type: `${f}/photo/delete`, entry_id: e, photo_id: s }), Rt = (t, e, s) => t.callWS({ type: `${f}/photo/reorder`, entry_id: e, order: s }), Nt = (t, e, s, i) => t.callWS({
  type: `${f}/photo/copy`,
  entry_id: e,
  photo_id: s,
  target_entry_id: i
}), Lt = (t, e, s) => t.callWS({ type: `${f}/photo/show`, entry_id: e, photo_id: s }), qt = (t, e) => t.callWS({ type: `${f}/frame/skip`, entry_id: e }), ht = (t, e, s) => t.callWS({ type: `${f}/frame/update`, entry_id: e, ...s }), Ut = (t, e, s) => t.callWS({ type: `${f}/import`, entry_id: e, media_content_id: s }), ct = (t, e, s, i) => t.callWS({
  type: `${f}/preview`,
  entry_id: e,
  photo_id: s,
  ...i
}), Qt = (t) => t.callWS({ type: `${f}/defaults` }), Yt = (t, e) => t.callWS({ type: `${f}/defaults/set`, defaults: e }), Bt = (t, e) => t.callWS({
  type: "media_source/browse_media",
  ...e ? { media_content_id: e } : {}
});
async function Gt(t, e, s) {
  const i = new FormData();
  for (const a of s) i.append("file", a, a.name);
  const r = await t.fetchWithAuth(`/api/${f}/upload/${e}`, {
    method: "POST",
    body: i
  });
  if (!r.ok) throw new Error(`Upload failed (${r.status})`);
  return r.json();
}
const c = (t) => t?.message ?? String(t), ut = (t) => {
  const { overlay_id: e, last_text: s, last_error: i, ...r } = t;
  return e ? { id: e, ...r } : r;
}, q = (t, e) => e ? { entry_id: t, photo_id: e } : { entry_id: t }, Ht = (t, e, s) => t.callWS({ type: `${f}/overlays`, ...q(e, s) }).then((i) => i.overlays), ft = (t, e, s, i) => t.callWS({ type: `${f}/overlay/save`, ...q(e, i), overlay: ut(s) }), Kt = (t, e, s, i) => t.callWS({ type: `${f}/overlay/delete`, ...q(e, i), overlay_id: s }), Jt = (t, e, s, i) => t.callWS({ type: `${f}/overlay/reorder`, ...q(e, i), order: s }), Xt = (t, e, s) => t.callWS({ type: `${f}/overlays/copy`, entry_id: e, target_entry_id: s }), Vt = (t, e, s, i, r = !1) => t.callWS({
  type: `${f}/overlay/preview`,
  entry_id: e,
  photo_id: i ?? null,
  for_photo: r,
  overlays: s.map(ut)
});
var Zt = Object.defineProperty, te = Object.getOwnPropertyDescriptor, z = (t, e, s, i) => {
  for (var r = i > 1 ? void 0 : i ? te(e, s) : e, a = t.length - 1, p; a >= 0; a--)
    (p = t[a]) && (r = (i ? p(e, s, r) : p(r)) || r);
  return i && r && Zt(e, s, r), r;
};
const ee = "media-source://paperlessoffline", it = (t) => t.media_class === "image" || t.media_content_type?.startsWith("image/");
let _ = class extends j {
  constructor() {
    super(...arguments), this.item = null, this.stack = [], this.selected = /* @__PURE__ */ new Set(), this.loading = !1, this.importing = !1, this.error = null;
  }
  connectedCallback() {
    super.connectedCallback(), this.open(void 0);
  }
  async open(t, e = !0) {
    this.loading = !0, this.error = null;
    try {
      const s = await Bt(this.hass, t);
      e && this.item && (this.stack = [...this.stack, this.item.media_content_id]), this.item = s;
    } catch (s) {
      this.error = c(s);
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
        await Ut(this.hass, this.frame.entry_id, t);
      this.close();
    } catch (t) {
      this.error = c(t);
    } finally {
      this.importing = !1;
    }
  }
  close() {
    this.dispatchEvent(new CustomEvent("closed", { bubbles: !0, composed: !0 }));
  }
  render() {
    const t = m(this.hass), e = (this.item?.children ?? []).filter(
      (s) => !s.media_content_id.startsWith(ee) && (s.can_expand || it(s))
    );
    return o`<div class="scrim" @click=${(s) => s.target === s.currentTarget && this.close()}>
      <div class="dialog card" role="dialog" aria-modal="true" aria-label=${t("import")}>
        <header>
          ${this.stack.length ? o`<button class="icon-btn" title=${t("back")} @click=${this.back}>${u(mt)}</button>` : n}
          <h2>${this.item?.title || t("media_root")}</h2>
          <button class="icon-btn" title=${t("close")} @click=${this.close}>${u(K)}</button>
        </header>
        <div class="grid">
          ${this.loading ? o`<p class="muted">${t("loading")}</p>` : n}
          ${!this.loading && !e.length ? o`<p class="muted">${t("no_media")}</p>` : n}
          ${e.map((s) => {
      const i = this.selected.has(s.media_content_id), r = !s.can_expand && it(s);
      return o`<button
              class="tile ${i ? "selected" : ""}"
              @click=${() => r ? this.toggle(s.media_content_id) : this.open(s.media_content_id)}
            >
              <div class="thumb">
                ${s.thumbnail ? o`<img src=${s.thumbnail} alt="" loading="lazy" />` : u(r ? vt : yt)}
                ${i ? o`<span class="tick">${u(bt)}</span>` : n}
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
_.styles = [
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
z([
  d({ attribute: !1 })
], _.prototype, "hass", 2);
z([
  d({ attribute: !1 })
], _.prototype, "frame", 2);
z([
  l()
], _.prototype, "item", 2);
z([
  l()
], _.prototype, "stack", 2);
z([
  l()
], _.prototype, "selected", 2);
z([
  l()
], _.prototype, "loading", 2);
z([
  l()
], _.prototype, "importing", 2);
z([
  l()
], _.prototype, "error", 2);
_ = z([
  S("pp-media-import")
], _);
var se = Object.defineProperty, ie = Object.getOwnPropertyDescriptor, P = (t, e, s, i) => {
  for (var r = i > 1 ? void 0 : i ? ie(e, s) : e, a = t.length - 1, p; a >= 0; a--)
    (p = t[a]) && (r = (i ? p(e, s, r) : p(r)) || r);
  return i && r && se(e, s, r), r;
};
const Q = "application/x-paperlessoffline-photo";
let x = class extends j {
  constructor() {
    super(...arguments), this.photos = [], this.dropActive = !1, this.uploading = 0, this.uploadErrors = [], this.error = null, this.importOpen = !1, this.dragId = null, this.dragOverId = null;
  }
  async upload(t) {
    const e = t.filter((s) => s.type.startsWith("image/") || /\.(heic|heif)$/i.test(s.name));
    if (e.length) {
      this.uploading = e.length, this.uploadErrors = [], this.error = null;
      try {
        const s = await Gt(this.hass, this.frame.entry_id, e);
        this.uploadErrors = s.errors;
      } catch (s) {
        this.error = c(s);
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
    this.dragId = e.photo_id, t.dataTransfer?.setData(Q, e.photo_id), t.dataTransfer && (t.dataTransfer.effectAllowed = "move");
  }
  onTileDragOver(t, e) {
    !this.dragId || !t.dataTransfer?.types.includes(Q) || (t.preventDefault(), this.dragOverId = e.photo_id);
  }
  async onTileDrop(t, e) {
    const s = t.dataTransfer?.getData(Q);
    if (this.dragOverId = null, this.dragId = null, !s || s === e.photo_id) return;
    t.preventDefault(), t.stopPropagation();
    const i = this.photos.map((a) => a.photo_id).filter((a) => a !== s);
    i.splice(i.indexOf(e.photo_id), 0, s);
    const r = new Map(this.photos.map((a) => [a.photo_id, a]));
    this.photos = i.map((a) => r.get(a));
    try {
      await Rt(this.hass, this.frame.entry_id, i);
    } catch (a) {
      this.error = c(a);
    }
  }
  async toggleEnabled(t, e) {
    t.stopPropagation();
    try {
      await dt(this.hass, this.frame.entry_id, e.photo_id, { enabled: !e.enabled });
    } catch (s) {
      this.error = c(s);
    }
  }
  async setOrder(t) {
    try {
      await ht(this.hass, this.frame.entry_id, { order: t });
    } catch (e) {
      this.error = c(e);
    }
  }
  edit(t) {
    this.dispatchEvent(new CustomEvent("edit-photo", { detail: { photo: t }, bubbles: !0, composed: !0 }));
  }
  render() {
    const t = m(this.hass), e = this.frame.current.kind === "photo" ? this.frame.current.photo_id : null, s = this.frame.up_next.kind === "photo" ? this.frame.up_next.photo_id : null;
    return o`
      <div class="toolbar">
        <label class="btn primary">
          ${u($t)} ${t("upload")}
          <input type="file" accept="image/*,.heic,.heif" multiple hidden @change=${this.onFileInput} />
        </label>
        <button class="btn" @click=${() => this.importOpen = !0}>${u(xt)} ${t("import")}</button>
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
      const r = Object.keys(i.overrides ?? {}).length > 0;
      return o`<div
                  class="tile ${i.enabled ? "" : "disabled"} ${this.dragOverId === i.photo_id ? "over" : ""}"
                  draggable="true"
                  tabindex="0"
                  @click=${() => this.edit(i)}
                  @keydown=${(a) => a.key === "Enter" && this.edit(i)}
                  @dragstart=${(a) => this.onTileDragStart(a, i)}
                  @dragover=${(a) => this.onTileDragOver(a, i)}
                  @dragleave=${() => this.dragOverId = null}
                  @drop=${(a) => this.onTileDrop(a, i)}
                  @dragend=${() => (this.dragId = null, this.dragOverId = null)}
                >
                  <img src=${i.thumb_url} alt="" loading="lazy" draggable="false" />
                  <div class="badges">
                    ${i.photo_id === e ? o`<span class="chip ok">${t("showing")}</span>` : n}
                    ${i.photo_id === s ? o`<span class="chip">${t("up_next")}</span>` : n}
                    ${r ? o`<span class="chip" title=${t("custom")}>${u(wt)}</span>` : n}
                  </div>
                  <div class="caption">
                    <span class="name" title=${i.name}>${i.name}</span>
                    <button
                      class="icon-btn small"
                      title=${i.enabled ? t("in_rotation") : t("not_in_rotation")}
                      @click=${(a) => this.toggleEnabled(a, i)}
                    >
                      ${u(i.enabled ? _t : kt)}
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
x.styles = [
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
P([
  d({ attribute: !1 })
], x.prototype, "hass", 2);
P([
  d({ attribute: !1 })
], x.prototype, "frame", 2);
P([
  d({ attribute: !1 })
], x.prototype, "photos", 2);
P([
  l()
], x.prototype, "dropActive", 2);
P([
  l()
], x.prototype, "uploading", 2);
P([
  l()
], x.prototype, "uploadErrors", 2);
P([
  l()
], x.prototype, "error", 2);
P([
  l()
], x.prototype, "importOpen", 2);
P([
  l()
], x.prototype, "dragId", 2);
P([
  l()
], x.prototype, "dragOverId", 2);
x = P([
  S("pp-library")
], x);
const re = 3e3;
let Y = null;
const ae = (t) => new Promise((e) => setTimeout(e, t));
function oe(t) {
  return customElements.get("ha-code-editor") ? Promise.resolve(!0) : (Y || (Y = (async () => {
    let e = null;
    try {
      const s = await window.loadCardHelpers?.();
      if (s) {
        const r = await (await s.createCardElement({ type: "markdown", content: "" }))?.constructor?.getConfigElement?.();
        r && (r.hass = t, r.setConfig?.({ type: "markdown", content: "" }), e = document.createElement("div"), e.style.cssText = "position:fixed;left:-10000px;top:0;width:400px;height:300px;overflow:hidden", e.setAttribute("aria-hidden", "true"), e.append(r), document.body.append(e));
      }
      await Promise.race([customElements.whenDefined("ha-code-editor"), ae(re)]);
    } catch {
    } finally {
      e?.remove();
    }
    return !!customElements.get("ha-code-editor");
  })()), Y);
}
function ne(t, e) {
  const s = t?.codemirror;
  return !s?.dispatch || !s.state?.replaceSelection ? !1 : (s.dispatch(s.state.replaceSelection(e)), s.focus?.(), !0);
}
class J {
  /**
   * `run` reads the current draft itself and should drop its result (or error)
   * when `stale()` says a newer draft is waiting. `onBusy` reports whether work
   * is outstanding.
   */
  constructor(e, s) {
    this.run = e, this.onBusy = s, this.armed = !1, this.running = !1, this.pending = !1;
  }
  schedule(e) {
    window.clearTimeout(this.timer), this.armed = !0, this.timer = window.setTimeout(() => {
      this.armed = !1, this.fire();
    }, e);
  }
  cancel() {
    window.clearTimeout(this.timer), this.armed = !1, this.pending = !1;
  }
  async fire() {
    if (this.running) {
      this.pending = !0;
      return;
    }
    this.running = !0, this.onBusy(!0);
    try {
      do {
        this.pending = !1;
        try {
          await this.run(() => this.pending || this.armed);
        } catch {
        }
      } while (this.pending);
    } finally {
      this.running = !1, this.onBusy(!1);
    }
  }
}
var le = Object.defineProperty, pe = Object.getOwnPropertyDescriptor, h = (t, e, s, i) => {
  for (var r = i > 1 ? void 0 : i ? pe(e, s) : e, a = t.length - 1, p; a >= 0; a--)
    (p = t[a]) && (r = (i ? p(e, s, r) : p(r)) || r);
  return i && r && le(e, s, r), r;
};
const de = [
  "top_left",
  "top_center",
  "top_right",
  "center_left",
  "center",
  "center_right",
  "bottom_left",
  "bottom_center",
  "bottom_right"
], rt = ["black", "white", "red", "green", "blue", "yellow"], at = {
  black: "#1f2226",
  white: "#f2f2f2",
  red: "#ea4843",
  green: "#067406",
  blue: "#416ce1",
  yellow: "#dbd529"
}, he = "draft", ce = 500, B = "application/x-paperlessoffline-overlay", L = (t, e, s = "bottom_right") => ({
  name: t,
  template: e,
  enabled: !0,
  show_if: null,
  anchor: s,
  margin: 0.03,
  width: null,
  align: "left",
  size: "m",
  text_color: "black",
  backing: "box",
  backing_color: "white",
  redraw: "change"
});
function ue(t, e) {
  const s = Object.keys(e.states ?? {}).find((r) => r.startsWith("weather.")) ?? "weather.home", i = Object.keys(e.states ?? {}).find(
    (r) => r.startsWith("sensor.") && e.states[r].attributes.device_class === "temperature"
  ) ?? "sensor.outdoor_temperature";
  return {
    sensor: L(t("preset_sensor"), `:mdi:thermometer: **{{ states('${i}') }} °C**`, "top_right"),
    weather: L(
      t("preset_weather"),
      `{{ weather_icon(states('${s}')) }} {{ state_attr('${s}', 'temperature') }} °`,
      "top_right"
    ),
    date: { ...L(t("preset_date"), "{{ date_local(now(), 'long') }}", "bottom_center"), backing: "halo", text_color: "white" },
    blank: L(t("preset_blank"), "")
  };
}
let $ = class extends j {
  constructor() {
    super(...arguments), this.frames = [], this.photos = [], this.overlays = [], this.editing = null, this.menuOpen = !1, this.error = null, this.notice = null, this.dragId = null;
  }
  willUpdate(t) {
    (t.has("frame") || t.has("photo")) && this.load();
  }
  async load() {
    try {
      this.overlays = await Ht(this.hass, this.frame.entry_id, this.photo?.photo_id);
    } catch (t) {
      this.error = c(t);
    }
  }
  add(t) {
    this.menuOpen = !1, this.editing = { ...t };
  }
  async toggle(t, e) {
    t.stopPropagation();
    try {
      await ft(this.hass, this.frame.entry_id, { ...e, enabled: !e.enabled }, this.photo?.photo_id), await this.load();
    } catch (s) {
      this.error = c(s);
    }
  }
  async drop(t, e) {
    const s = t.dataTransfer?.getData(B);
    if (this.dragId = null, !s || s === e.overlay_id) return;
    t.preventDefault();
    const i = this.overlays.map((a) => a.overlay_id).filter((a) => a !== s);
    i.splice(i.indexOf(e.overlay_id), 0, s);
    const r = new Map(this.overlays.map((a) => [a.overlay_id, a]));
    this.overlays = i.map((a) => r.get(a));
    try {
      await Jt(this.hass, this.frame.entry_id, i, this.photo?.photo_id);
    } catch (a) {
      this.error = c(a);
    }
  }
  async copyTo(t) {
    const e = t.target, s = this.frames.find((i) => i.entry_id === e.value);
    if (e.value = "", !!s)
      try {
        const i = await Xt(this.hass, this.frame.entry_id, s.entry_id);
        this.notice = m(this.hass)("copied_overlays", { n: i.copied, frame: s.title });
      } catch (i) {
        this.error = c(i);
      }
  }
  render() {
    const t = m(this.hass), e = this.photo ? [] : this.frames.filter((i) => i.entry_id !== this.frame.entry_id), s = ue(t, this.hass);
    return o`<div class="card wrap">
      <div class="head">
        <div>
          <h3>${t(this.photo ? "photo_overlays" : "global_overlays")}</h3>
          <span class="muted">${t(this.photo ? "photo_overlays_hint" : "global_overlays_hint")}</span>
        </div>
        <div class="actions">
          ${e.length && this.overlays.length ? o`<label class="copy">
                ${u(lt)}
                <select @change=${this.copyTo} aria-label=${t("copy_overlays_to")}>
                  <option value="">${t("copy_overlays_to")}</option>
                  ${e.map((i) => o`<option value=${i.entry_id}>${i.title}</option>`)}
                </select>
              </label>` : n}
          <div class="menu-wrap">
            <button class="btn primary" @click=${() => this.menuOpen = !this.menuOpen}>
              ${u(Pt)} ${t("add_overlay")}
            </button>
            ${this.menuOpen ? o`<div class="menu card">
                  ${["sensor", "weather", "date", "blank"].map(
      (i) => o`<button @click=${() => this.add(s[i])}>${t(`preset_${i}`)}</button>`
    )}
                </div>` : n}
          </div>
        </div>
      </div>
      ${this.notice ? o`<p class="chip ok">${this.notice}</p>` : n}
      ${this.error ? o`<p class="error">${t("error", { error: this.error })}</p>` : n}
      ${this.overlays.length ? o`<ul>
            ${this.overlays.map(
      (i) => o`<li
                class=${this.dragId === i.overlay_id ? "dragging" : ""}
                draggable="true"
                @dragstart=${(r) => {
        this.dragId = i.overlay_id, r.dataTransfer?.setData(B, i.overlay_id);
      }}
                @dragover=${(r) => r.dataTransfer?.types.includes(B) && r.preventDefault()}
                @drop=${(r) => this.drop(r, i)}
                @dragend=${() => this.dragId = null}
                @click=${() => this.editing = { ...i }}
              >
                <span class="grip">${u(Ot)}</span>
                <span class="body">
                  <span class="name">${u(Et)} ${i.name}</span>
                  <code>${i.template.split(`
`)[0]}</code>
                  ${i.last_error ? o`<span class="error small">${t("overlay_error", { error: i.last_error })}</span>` : i.last_text ? o`<span class="muted small">${t("shows_now", { text: i.last_text })}</span>` : n}
                </span>
                <label class="toggle" @click=${(r) => r.stopPropagation()}>
                  <input type="checkbox" .checked=${i.enabled} @change=${(r) => this.toggle(r, i)} />
                  ${t("enabled")}
                </label>
              </li>`
    )}
          </ul>` : o`<p class="muted empty">${t(this.photo ? "no_photo_overlays" : "no_overlays")}</p>`}
      ${this.editing ? o`<pp-overlay-editor
            .hass=${this.hass}
            .frame=${this.frame}
            .photos=${this.photos}
            .photo=${this.photo}
            .overlays=${this.overlays}
            .overlay=${this.editing}
            @closed=${(i) => {
      i.stopPropagation(), this.editing = null, this.load();
    }}
          ></pp-overlay-editor>` : n}
    </div>`;
  }
};
$.styles = [
  A,
  E`
      .wrap {
        padding: 16px;
        display: grid;
        gap: 12px;
      }
      .head {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        gap: 12px;
        flex-wrap: wrap;
      }
      h3 {
        margin: 0 0 4px;
        font-size: 16px;
        font-weight: 500;
      }
      .actions {
        display: flex;
        gap: 8px;
        align-items: center;
      }
      .copy {
        display: inline-flex;
        align-items: center;
        gap: 4px;
      }
      .menu-wrap {
        position: relative;
      }
      .menu {
        position: absolute;
        right: 0;
        top: calc(100% + 4px);
        z-index: 3;
        display: grid;
        min-width: 180px;
        padding: 4px;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.18);
      }
      .menu button {
        text-align: left;
        padding: 8px 12px;
        border: none;
        background: transparent;
        color: inherit;
        border-radius: 6px;
      }
      .menu button:hover {
        background: color-mix(in srgb, var(--pp-text) 6%, transparent);
      }
      ul {
        list-style: none;
        margin: 0;
        padding: 0;
        display: grid;
        gap: 6px;
      }
      li {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 8px 10px;
        border: 1px solid var(--pp-border);
        border-radius: 10px;
        cursor: pointer;
      }
      li:hover {
        background: color-mix(in srgb, var(--pp-text) 4%, transparent);
      }
      li.dragging {
        opacity: 0.5;
      }
      .grip {
        color: var(--pp-muted);
        cursor: grab;
      }
      .body {
        flex: 1;
        display: grid;
        gap: 2px;
        min-width: 0;
      }
      .name {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        font-weight: 500;
      }
      code {
        font-size: 12px;
        color: var(--pp-muted);
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
      .small {
        font-size: 12px;
      }
      .toggle {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        font-size: 13px;
      }
      .empty {
        margin: 0;
      }
    `
];
h([
  d({ attribute: !1 })
], $.prototype, "hass", 2);
h([
  d({ attribute: !1 })
], $.prototype, "frame", 2);
h([
  d({ attribute: !1 })
], $.prototype, "frames", 2);
h([
  d({ attribute: !1 })
], $.prototype, "photos", 2);
h([
  d({ attribute: !1 })
], $.prototype, "photo", 2);
h([
  l()
], $.prototype, "overlays", 2);
h([
  l()
], $.prototype, "editing", 2);
h([
  l()
], $.prototype, "menuOpen", 2);
h([
  l()
], $.prototype, "error", 2);
h([
  l()
], $.prototype, "notice", 2);
h([
  l()
], $.prototype, "dragId", 2);
$ = h([
  S("pp-overlays")
], $);
let v = class extends j {
  constructor() {
    super(...arguments), this.photos = [], this.overlays = [], this.preview = null, this.aspect = "3 / 5", this.result = null, this.sampleId = null, this.rendering = !1, this.entityQuery = null, this.error = null, this.codeEditor = !1, this.queue = new J(
      (t) => this.loadPreview(t),
      (t) => this.rendering = t
    ), this.onKey = (t) => {
      t.key !== "Escape" || this.entityQuery !== null || t.composedPath().some((e) => e.tagName === "HA-CODE-EDITOR") || this.close();
    };
  }
  connectedCallback() {
    super.connectedCallback(), window.addEventListener("keydown", this.onKey), oe(this.hass).then((t) => this.codeEditor = t);
  }
  disconnectedCallback() {
    super.disconnectedCallback(), window.removeEventListener("keydown", this.onKey), this.queue.cancel();
  }
  willUpdate(t) {
    t.has("overlay") && (this.draft = { ...this.overlay }, this.sampleId = this.photo?.photo_id ?? this.photos[0]?.photo_id ?? null, this.schedule(0));
  }
  set(t, e) {
    this.draft = { ...this.draft, [t]: e }, this.schedule();
  }
  schedule(t = ce) {
    this.queue.schedule(t);
  }
  async loadPreview(t) {
    const e = this.draft.overlay_id ?? he, s = { ...this.draft, overlay_id: e }, i = this.overlays.some((r) => r.overlay_id === e) ? this.overlays.map((r) => r.overlay_id === e ? s : r) : [...this.overlays, s];
    try {
      const r = await Vt(this.hass, this.frame.entry_id, i, this.sampleId, !!this.photo);
      if (t()) return;
      this.preview = r.image, this.aspect = `${r.width} / ${r.height}`, this.result = r.results[e] ?? null;
    } catch (r) {
      t() || (this.error = c(r));
    }
  }
  insertEntity(t) {
    const e = this.hass.states[t]?.attributes.unit_of_measurement, s = `{{ states('${t}') }}${e ? ` ${e}` : ""}`;
    if (this.entityQuery = null, ne(this.renderRoot.querySelector("ha-code-editor.template"), s)) return;
    const i = this.renderRoot.querySelector("textarea.template"), r = this.draft.template, a = i?.selectionStart ?? r.length, p = i?.selectionEnd ?? r.length;
    this.set("template", r.slice(0, a) + s + r.slice(p)), this.entityQuery = null;
  }
  async save() {
    try {
      await ft(this.hass, this.frame.entry_id, this.draft, this.photo?.photo_id), this.close();
    } catch (t) {
      this.error = c(t);
    }
  }
  async deleteClicked() {
    if (!this.draft.overlay_id) return this.close();
    try {
      await Kt(this.hass, this.frame.entry_id, this.draft.overlay_id, this.photo?.photo_id), this.close();
    } catch (t) {
      this.error = c(t);
    }
  }
  close() {
    this.dispatchEvent(new CustomEvent("closed", { bubbles: !0, composed: !0 }));
  }
  select(t, e, s) {
    return o`<select
      @change=${(i) => this.set(t, i.target.value)}
    >
      ${e.map((i) => o`<option value=${i} ?selected=${this.draft[t] === i}>${s(i)}</option>`)}
    </select>`;
  }
  renderEntityPicker() {
    const t = m(this.hass), e = (this.entityQuery ?? "").toLowerCase(), s = Object.keys(this.hass.states ?? {}).filter((i) => {
      const r = String(this.hass.states[i].attributes.friendly_name ?? "").toLowerCase();
      return i.includes(e) || r.includes(e);
    }).sort().slice(0, 50);
    return o`<div class="picker card">
      <input
        type="text"
        placeholder=${t("search_entities")}
        .value=${this.entityQuery ?? ""}
        @input=${(i) => this.entityQuery = i.target.value}
        @keydown=${(i) => i.key === "Escape" && (this.entityQuery = null)}
      />
      <ul>
        ${s.map(
      (i) => o`<li @click=${() => this.insertEntity(i)}>
            <span>${this.hass.states[i].attributes.friendly_name ?? i}</span>
            <span class="muted">${i} · ${this.hass.states[i].state}</span>
          </li>`
    )}
      </ul>
    </div>`;
  }
  render() {
    if (!this.draft) return n;
    const t = m(this.hass), e = this.draft;
    return o`<div class="scrim" @click=${(s) => s.target === s.currentTarget && this.close()}>
      <div class="dialog card" role="dialog" aria-modal="true" aria-label=${t("edit_overlay")}>
        <header>
          <input
            class="title"
            type="text"
            .value=${e.name}
            aria-label=${t("overlay_name")}
            @input=${(s) => this.set("name", s.target.value)}
          />
          <button class="icon-btn" title=${t("close")} @click=${this.close}>${u(K)}</button>
        </header>
        <div class="body">
          <section class="fields">
            <label class="field">
              <span class="row">
                ${t("overlay_text")}
                <button class="btn small" @click=${() => this.entityQuery = this.entityQuery === null ? "" : null}>
                  ${t("insert_entity")}
                </button>
              </span>
              ${this.codeEditor ? o`<ha-code-editor
                    class="template"
                    mode="jinja2"
                    dir="ltr"
                    .hass=${this.hass}
                    .value=${e.template}
                    .autocompleteEntities=${!0}
                    .autocompleteIcons=${!0}
                    .linewrap=${!0}
                    @value-changed=${(s) => {
      s.stopPropagation(), this.set("template", s.detail.value);
    }}
                  ></ha-code-editor>` : o`<textarea
                    class="template"
                    rows="5"
                    spellcheck="false"
                    .value=${e.template}
                    @input=${(s) => this.set("template", s.target.value)}
                  ></textarea>`}
            </label>
            ${this.entityQuery !== null ? this.renderEntityPicker() : n}
            <span class="muted small">${t("overlay_help")}</span>
            ${this.result?.error ? o`<span class="error small">${t("overlay_error", { error: this.result.error })}</span>` : this.result && this.result.text === null ? o`<span class="muted small">${t("overlay_hidden")}</span>` : n}
            <div class="grid2">
              <div class="field">
                ${t("position")}
                <div class="anchors">
                  ${de.map(
      (s) => o`<button
                      class=${e.anchor === s ? "on" : ""}
                      title=${s}
                      aria-label=${s}
                      @click=${() => this.set("anchor", s)}
                    ></button>`
    )}
                </div>
              </div>
              <div class="stack">
                <label class="field">${t("text_size")} ${this.select("size", ["s", "m", "l", "xl"], (s) => t(`size_${s}`))}</label>
                <label class="field">${t("alignment")} ${this.select("align", ["left", "center", "right"], (s) => t(`align_${s}`))}</label>
              </div>
            </div>
            <div class="field">
              <span class="row">
                ${t("box_width")}
                <label class="check">
                  <input
                    type="checkbox"
                    .checked=${e.width === null}
                    @change=${(s) => this.set("width", s.target.checked ? null : 50)}
                  />
                  ${t("width_auto")}
                </label>
              </span>
              ${e.width !== null ? o`<div class="slider">
                    <input
                      type="range"
                      min="10"
                      max="100"
                      step="5"
                      .value=${String(e.width)}
                      @input=${(s) => this.set("width", Number(s.target.value))}
                    />
                    <span>${e.width} %</span>
                  </div>` : n}
            </div>
            <div class="grid2">
              <div class="field">
                ${t("text_color")}
                <div class="swatches">
                  ${rt.map(
      (s) => o`<button
                      class=${e.text_color === s ? "on" : ""}
                      style="background:${at[s]}"
                      title=${t(`color_${s}`)}
                      @click=${() => this.set("text_color", s)}
                    ></button>`
    )}
                </div>
              </div>
              <label class="field">${t("backing")} ${this.select("backing", ["box", "halo", "none"], (s) => t(`backing_${s}`))}</label>
            </div>
            ${e.backing === "box" ? o`<div class="field">
                  ${t("box_color")}
                  <div class="swatches">
                    ${rt.map(
      (s) => o`<button
                        class=${e.backing_color === s ? "on" : ""}
                        style="background:${at[s]}"
                        title=${t(`color_${s}`)}
                        @click=${() => this.set("backing_color", s)}
                      ></button>`
    )}
                  </div>
                </div>` : n}
            <label class="field">
              ${t("show_if")}
              ${this.codeEditor ? o`<ha-code-editor
                    class="show-if"
                    mode="jinja2"
                    dir="ltr"
                    .hass=${this.hass}
                    .value=${e.show_if ?? ""}
                    .autocompleteEntities=${!0}
                    .linewrap=${!0}
                    @value-changed=${(s) => {
      s.stopPropagation(), this.set("show_if", s.detail.value || null);
    }}
                  ></ha-code-editor>` : o`<textarea
                    rows="2"
                    spellcheck="false"
                    .value=${e.show_if ?? ""}
                    @input=${(s) => this.set("show_if", s.target.value || null)}
                  ></textarea>`}
            </label>
            <label class="field">${t("redraw")} ${this.select("redraw", ["change", "photo"], (s) => t(`redraw_${s}`))}</label>
            <label class="check">
              <input type="checkbox" .checked=${e.enabled} @change=${(s) => this.set("enabled", s.target.checked)} />
              ${t("enabled")}
            </label>
          </section>
          <section class="previewcol">
            <div class="row">
              <span class="h">${t("preview")}</span>
              ${this.rendering ? o`<span class="muted small">${t("rendering")}</span>` : n}
            </div>
            ${this.photos.length && !this.photo ? o`<select
                  aria-label=${t("sample_photo")}
                  @change=${(s) => {
      this.sampleId = s.target.value, this.schedule(0);
    }}
                >
                  ${this.photos.map((s) => o`<option value=${s.photo_id} ?selected=${s.photo_id === this.sampleId}>${s.name}</option>`)}
                </select>` : n}
            <div class="preview" style="aspect-ratio:${this.aspect}">
              ${this.preview ? o`<img src=${this.preview} alt=${t("preview")} />` : n}
            </div>
            <span class="muted small">${t("preview_hint")}</span>
          </section>
        </div>
        ${this.error ? o`<div class="msg error">${t("error", { error: this.error })}</div>` : n}
        <footer>
          <button class="btn danger" @click=${this.deleteClicked}>${u(pt)} ${t("delete")}</button>
          <span class="spacer"></span>
          <button class="btn" @click=${this.close}>${t("cancel")}</button>
          <button class="btn primary" @click=${this.save}>${t("save")}</button>
        </footer>
      </div>
    </div>`;
  }
};
v.styles = [
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
      }
      .title {
        flex: 1;
        font-size: 18px;
        font-weight: 500;
        border-color: transparent;
        background: transparent;
      }
      .body {
        display: grid;
        grid-template-columns: minmax(0, 3fr) minmax(260px, 2fr);
        gap: 24px;
        padding: 16px;
        overflow: auto;
      }
      .fields,
      .previewcol,
      .stack {
        display: flex;
        flex-direction: column;
        gap: 12px;
        min-width: 0;
      }
      .row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 8px;
      }
      .h {
        font-weight: 500;
      }
      textarea {
        font: 13px/1.5 ui-monospace, SFMono-Regular, Menlo, monospace;
        color: var(--pp-text);
        background: var(--pp-surface);
        border: 1px solid var(--pp-border);
        border-radius: 8px;
        padding: 8px 10px;
        resize: vertical;
        width: 100%;
      }
      div.field {
        display: grid;
        gap: 6px;
        font-size: 14px;
      }
      .field select {
        width: 100%;
      }
      ha-code-editor {
        display: block;
        border: 1px solid var(--pp-border);
        border-radius: 8px;
        overflow: hidden;
        --code-mirror-max-height: 260px;
      }
      ha-code-editor.template {
        min-height: 110px;
      }
      .small {
        font-size: 12px;
      }
      .btn.small {
        min-height: 28px;
        padding: 0 10px;
        font-size: 13px;
      }
      .grid2 {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 16px;
      }
      .anchors {
        display: grid;
        grid-template-columns: repeat(3, 32px);
        grid-template-rows: repeat(3, 24px);
        gap: 4px;
        padding: 6px;
        width: fit-content;
        border-radius: 8px;
        border: 1px solid var(--pp-border);
        background: var(--pp-bg);
      }
      .anchors button {
        border: 1px solid var(--pp-border);
        border-radius: 4px;
        background: var(--pp-surface);
      }
      .anchors button.on {
        background: var(--pp-accent);
        border-color: var(--pp-accent);
      }
      .swatches {
        display: flex;
        gap: 6px;
        flex-wrap: wrap;
      }
      .swatches button {
        width: 28px;
        height: 28px;
        border-radius: 50%;
        border: 1px solid var(--pp-border);
      }
      .swatches button.on {
        outline: 2px solid var(--pp-accent);
        outline-offset: 2px;
      }
      .check {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        font-size: 14px;
        cursor: pointer;
      }
      .slider {
        display: flex;
        align-items: center;
        gap: 10px;
      }
      .slider input {
        flex: 1;
      }
      .picker {
        padding: 8px;
        display: grid;
        gap: 6px;
      }
      .picker ul {
        list-style: none;
        margin: 0;
        padding: 0;
        max-height: 220px;
        overflow: auto;
      }
      .picker li {
        display: grid;
        padding: 6px 8px;
        border-radius: 6px;
        cursor: pointer;
        font-size: 14px;
      }
      .picker li:hover {
        background: color-mix(in srgb, var(--pp-text) 6%, transparent);
      }
      .picker li .muted {
        font-size: 12px;
      }
      .preview {
        flex: none;
        height: min(460px, 55vh);
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
      .msg {
        padding: 0 16px 8px;
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
h([
  d({ attribute: !1 })
], v.prototype, "hass", 2);
h([
  d({ attribute: !1 })
], v.prototype, "frame", 2);
h([
  d({ attribute: !1 })
], v.prototype, "photos", 2);
h([
  d({ attribute: !1 })
], v.prototype, "overlays", 2);
h([
  d({ attribute: !1 })
], v.prototype, "overlay", 2);
h([
  d({ attribute: !1 })
], v.prototype, "photo", 2);
h([
  l()
], v.prototype, "draft", 2);
h([
  l()
], v.prototype, "preview", 2);
h([
  l()
], v.prototype, "aspect", 2);
h([
  l()
], v.prototype, "result", 2);
h([
  l()
], v.prototype, "sampleId", 2);
h([
  l()
], v.prototype, "rendering", 2);
h([
  l()
], v.prototype, "entityQuery", 2);
h([
  l()
], v.prototype, "error", 2);
h([
  l()
], v.prototype, "codeEditor", 2);
v = h([
  S("pp-overlay-editor")
], v);
var fe = Object.defineProperty, ge = Object.getOwnPropertyDescriptor, W = (t, e, s, i) => {
  for (var r = i > 1 ? void 0 : i ? ge(e, s) : e, a = t.length - 1, p; a >= 0; a--)
    (p = t[a]) && (r = (i ? p(e, s, r) : p(r)) || r);
  return i && r && fe(e, s, r), r;
};
const ot = 5, M = (t, e = 0, s = 1) => Math.min(s, Math.max(e, t));
let D = class extends j {
  constructor() {
    super(...arguments), this.src = "", this.crop = null, this.focal = { x: 0.5, y: 0.5 }, this.aspect = null, this.draft = null, this.start = null;
  }
  point(t) {
    const e = this.img.getBoundingClientRect();
    return { x: M((t.clientX - e.left) / e.width), y: M((t.clientY - e.top) / e.height), r: e };
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
    if (!this.start || Math.hypot(t.clientX - this.start.px, t.clientY - this.start.py) < ot) return;
    const e = this.point(t);
    if (this.start.mode === "move" && this.start.orig) {
      const [R, gt, tt, et] = this.start.orig;
      this.draft = [M(R + e.x - this.start.x, 0, 1 - tt), M(gt + e.y - this.start.y, 0, 1 - et), tt, et];
      return;
    }
    let s = Math.abs(e.x - this.start.x), i = Math.abs(e.y - this.start.y);
    if (this.aspect) {
      const R = this.aspect * e.r.height / e.r.width;
      s / i > R ? s = i * R : i = s / R;
    }
    const r = e.x < this.start.x ? this.start.x - s : this.start.x, a = e.y < this.start.y ? this.start.y - i : this.start.y, p = M(r, 0, 1 - s), Z = M(a, 0, 1 - i);
    this.draft = [p, Z, Math.min(s, 1 - p), Math.min(i, 1 - Z)];
  }
  onUp(t) {
    if (!this.start) return;
    const e = Math.hypot(t.clientX - this.start.px, t.clientY - this.start.py) >= ot;
    if (e && this.draft && this.draft[2] > 0.02 && this.draft[3] > 0.02)
      this.fire("crop-changed", { crop: this.draft.map((s) => Math.round(s * 1e4) / 1e4) });
    else if (!e) {
      const s = this.point(t), [i, r, a, p] = this.crop ?? [0, 0, 1, 1];
      this.fire("focal-changed", {
        x: Math.round(M((s.x - i) / a) * 1e3) / 1e3,
        y: Math.round(M((s.y - r) / p) * 1e3) / 1e3
      });
    }
    this.start = null, this.draft = null;
  }
  fire(t, e) {
    this.dispatchEvent(new CustomEvent(t, { detail: e, bubbles: !0, composed: !0 }));
  }
  render() {
    const t = this.draft ?? this.crop, [e, s, i, r] = t ?? [0, 0, 1, 1], a = e + this.focal.x * i, p = s + this.focal.y * r;
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
            style="left:${e * 100}%;top:${s * 100}%;width:${i * 100}%;height:${r * 100}%"
          ></div>` : n}
      <div class="focal" style="left:${a * 100}%;top:${p * 100}%"></div>
    </div>`;
  }
};
D.styles = E`
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
W([
  d()
], D.prototype, "src", 2);
W([
  d({ attribute: !1 })
], D.prototype, "crop", 2);
W([
  d({ attribute: !1 })
], D.prototype, "focal", 2);
W([
  d({ attribute: !1 })
], D.prototype, "aspect", 2);
W([
  l()
], D.prototype, "draft", 2);
W([
  At("img")
], D.prototype, "img", 2);
D = W([
  S("pp-crop-area")
], D);
var me = Object.defineProperty, ve = Object.getOwnPropertyDescriptor, N = (t, e, s, i) => {
  for (var r = i > 1 ? void 0 : i ? ve(e, s) : e, a = t.length - 1, p; a >= 0; a--)
    (p = t[a]) && (r = (i ? p(e, s, r) : p(r)) || r);
  return i && r && me(e, s, r), r;
};
const G = {
  dither: ["floyd_steinberg", "atkinson", "jarvis_judice_ninke", "sierra2", "bayer", "none"],
  fit: ["cover", "contain", "stretch"],
  background: ["white", "black"],
  palette: ["perceived", "pure"]
}, ye = ["brightness", "contrast", "saturation"];
let F = class extends j {
  constructor() {
    super(...arguments), this.value = {}, this.withPalette = !1;
  }
  get fields() {
    const t = [];
    return this.withPalette && t.push("palette"), t.push("dither", "serpentine", "fit", "background", ...ye), t;
  }
  label(t, e) {
    const s = m(this.hass);
    return typeof e == "boolean" ? s(e ? "on" : "off") : typeof e == "number" ? e.toFixed(2) : G[t] ? s(`${t}_${e}`) : String(e);
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
    const i = m(this.hass);
    if (G[t])
      return o`<select
        .value=${String(e)}
        ?disabled=${s}
        @change=${(a) => this.setField(t, a.target.value)}
      >
        ${G[t].map(
        (a) => o`<option value=${a} ?selected=${a === e}>${i(`${t}_${a}`)}</option>`
      )}
      </select>`;
    if (t === "serpentine")
      return o`<select
        ?disabled=${s}
        @change=${(a) => this.setField(t, a.target.value === "on")}
      >
        <option value="on" ?selected=${e === !0}>${i("on")}</option>
        <option value="off" ?selected=${e !== !0}>${i("off")}</option>
      </select>`;
    const r = Number(e);
    return o`<div class="slider">
      <input
        type="range"
        min="0"
        max="2"
        step="0.05"
        .value=${String(r)}
        ?disabled=${s}
        @input=${(a) => this.setField(t, Number(a.target.value))}
      />
      <span class="num">${r.toFixed(2)}</span>
    </div>`;
  }
  render() {
    if (!this.inherited) return n;
    const t = m(this.hass);
    return o`${this.fields.map((e) => {
      const s = this.value[e] !== void 0, i = s ? this.value[e] : this.inherited[e];
      return o`<div class="row">
        <div class="head">
          <span class="name">${t(e)}</span>
          <label class="inherit">
            <input
              type="checkbox"
              .checked=${!s}
              @change=${(r) => this.setInherit(e, r.target.checked)}
            />
            ${t("inherited_value", { value: this.label(e, this.inherited[e]) })}
          </label>
        </div>
        <div class=${s ? "ctl" : "ctl inherited"}>${this.control(e, i, !s)}</div>
        ${e === "serpentine" ? o`<span class="hint">${t("serpentine_hint")}</span>` : n}
      </div>`;
    })}`;
  }
};
F.styles = [
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
      .hint {
        font-size: 12px;
        color: var(--pp-muted);
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
N([
  d({ attribute: !1 })
], F.prototype, "hass", 2);
N([
  d({ attribute: !1 })
], F.prototype, "value", 2);
N([
  d({ attribute: !1 })
], F.prototype, "inherited", 2);
N([
  d({ type: Boolean, attribute: "with-palette" })
], F.prototype, "withPalette", 2);
F = N([
  S("pp-render-settings")
], F);
function X(t, ...e) {
  const s = { ...t };
  for (const i of e)
    for (const [r, a] of Object.entries(i ?? {}))
      a != null && r in t && (s[r] = a);
  return s;
}
var be = Object.defineProperty, $e = Object.getOwnPropertyDescriptor, b = (t, e, s, i) => {
  for (var r = i > 1 ? void 0 : i ? $e(e, s) : e, a = t.length - 1, p; a >= 0; a--)
    (p = t[a]) && (r = (i ? p(e, s, r) : p(r)) || r);
  return i && r && be(e, s, r), r;
};
const xe = 350, nt = ["dither", "serpentine", "fit", "background", "brightness", "contrast", "saturation"];
let y = class extends j {
  constructor() {
    super(...arguments), this.frames = [], this.draft = {}, this.name = "", this.enabled = !0, this.hideOverlays = !1, this.preview = null, this.rendering = !1, this.lockAspect = !0, this.error = null, this.notice = null, this.busy = !1, this.previewQueue = new J(
      (t) => this.loadPreview(t),
      (t) => this.rendering = t
    ), this.onKey = (t) => {
      t.key === "Escape" && this.close();
    };
  }
  connectedCallback() {
    super.connectedCallback(), window.addEventListener("keydown", this.onKey);
  }
  disconnectedCallback() {
    super.disconnectedCallback(), window.removeEventListener("keydown", this.onKey), this.previewQueue.cancel();
  }
  willUpdate(t) {
    t.has("photo") && this.photo && (this.draft = structuredClone(this.photo.overrides ?? {}), this.name = this.photo.name, this.enabled = this.photo.enabled, this.hideOverlays = this.photo.hide_frame_overlays ?? !1, this.lockAspect = !0, this.schedulePreview(0));
  }
  get resolved() {
    return X(this.inherited, this.draft);
  }
  get rotation() {
    return this.draft.rotation ?? 0;
  }
  get aspect() {
    return this.frame.canvas.width / this.frame.canvas.height;
  }
  get dirty() {
    return this.name !== this.photo.name || this.enabled !== this.photo.enabled || this.hideOverlays !== (this.photo.hide_frame_overlays ?? !1) || JSON.stringify(this.draft) !== JSON.stringify(this.photo.overrides ?? {});
  }
  setDraft(t, e = []) {
    const s = { ...this.draft, ...t };
    for (const i of e) delete s[i];
    this.draft = s, this.schedulePreview();
  }
  schedulePreview(t = xe) {
    this.previewQueue.schedule(t);
  }
  async loadPreview(t) {
    try {
      const e = await ct(this.hass, this.frame.entry_id, this.photo.photo_id, {
        overrides: this.draft
      });
      t() || (this.preview = e.image);
    } catch (e) {
      t() || (this.error = c(e));
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
    for (const i of nt)
      e[i] === void 0 ? delete s[i] : s[i] = e[i];
    this.draft = s, this.schedulePreview();
  }
  async save() {
    this.busy = !0, this.error = null;
    try {
      await dt(this.hass, this.frame.entry_id, this.photo.photo_id, {
        name: this.name.trim() || this.photo.name,
        enabled: this.enabled,
        overrides: this.draft,
        hide_frame_overlays: this.hideOverlays
      }), this.close();
    } catch (t) {
      this.error = c(t);
    } finally {
      this.busy = !1;
    }
  }
  async deleteClicked() {
    const t = m(this.hass);
    if (confirm(t("delete_confirm", { name: this.photo.name })))
      try {
        await Wt(this.hass, this.frame.entry_id, this.photo.photo_id), this.close();
      } catch (e) {
        this.error = c(e);
      }
  }
  async showNext() {
    try {
      await Lt(this.hass, this.frame.entry_id, this.photo.photo_id), this.notice = m(this.hass)("pending");
    } catch (t) {
      this.error = c(t);
    }
  }
  async copyTo(t) {
    const e = t.target, s = this.frames.find((i) => i.entry_id === e.value);
    if (e.value = "", !!s)
      try {
        await Nt(this.hass, this.frame.entry_id, this.photo.photo_id, s.entry_id), this.notice = m(this.hass)("copied", { frame: s.title });
      } catch (i) {
        this.error = c(i);
      }
  }
  close() {
    this.dispatchEvent(new CustomEvent("closed", { bubbles: !0, composed: !0 }));
  }
  render() {
    if (!this.photo) return n;
    const t = m(this.hass), e = this.resolved.fit === "cover", s = this.frames.filter((a) => a.entry_id !== this.frame.entry_id), i = {};
    for (const a of nt)
      this.draft[a] !== void 0 && (i[a] = this.draft[a]);
    const r = `aspect-ratio:${this.frame.canvas.width}/${this.frame.canvas.height}`;
    return o`<div class="scrim" @click=${(a) => a.target === a.currentTarget && this.close()}>
      <div class="dialog card" role="dialog" aria-modal="true" aria-label=${t("edit_photo")}>
        <header>
          <input
            class="title"
            type="text"
            .value=${this.name}
            aria-label=${t("name")}
            @input=${(a) => this.name = a.target.value}
          />
          <button class="icon-btn" title=${t("close")} @click=${this.close}>${u(K)}</button>
        </header>
        <div class="body">
          <section class="visual">
            <div class="section-title">
              <span>${t("crop")}</span>
              <span class="tools">
                <button class="icon-btn" title=${t("rotate_left")} @click=${() => this.rotate(-90)}>
                  ${u(St)}
                </button>
                <button class="icon-btn" title=${t("rotate_right")} @click=${() => this.rotate(90)}>
                  ${u(It)}
                </button>
              </span>
            </div>
            <pp-crop-area
              .src=${this.photo.display_urls[String(this.rotation)]}
              .crop=${this.draft.crop ?? null}
              .focal=${{ x: this.draft.focal_x ?? 0.5, y: this.draft.focal_y ?? 0.5 }}
              .aspect=${e && this.lockAspect ? this.aspect : null}
              @crop-changed=${(a) => this.setDraft({ crop: a.detail.crop })}
              @focal-changed=${(a) => this.setDraft({ focal_x: a.detail.x, focal_y: a.detail.y })}
            ></pp-crop-area>
            <div class="crop-tools">
              <span class="muted hint">${t("crop_hint")}</span>
              ${e ? o`<label class="check">
                    <input
                      type="checkbox"
                      .checked=${this.lockAspect}
                      @change=${(a) => this.lockAspect = a.target.checked}
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
            <div class="preview" style=${r}>
              ${this.preview ? o`<img src=${this.preview} alt=${t("preview")} />` : n}
            </div>
            <span class="muted hint">${t("preview_hint")}</span>
            <label class="check rotation">
              <input
                type="checkbox"
                .checked=${this.enabled}
                @change=${(a) => this.enabled = a.target.checked}
              />
              ${t("in_rotation")}
            </label>
            <label class="check">
              <input
                type="checkbox"
                .checked=${this.hideOverlays}
                @change=${(a) => this.hideOverlays = a.target.checked}
              />
              ${t("hide_frame_overlays")}
            </label>
            <pp-overlays .hass=${this.hass} .frame=${this.frame} .photos=${[this.photo]} .photo=${this.photo}></pp-overlays>
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
          <button class="btn danger" @click=${this.deleteClicked}>${u(pt)} ${t("delete")}</button>
          <button class="btn" @click=${this.showNext}>${u(Dt)} ${t("show_next")}</button>
          ${s.length ? o`<label class="copy">
                ${u(lt)}
                <select @change=${this.copyTo} aria-label=${t("copy_to")}>
                  <option value="">${t("copy_to")}</option>
                  ${s.map((a) => o`<option value=${a.entry_id}>${a.title}</option>`)}
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
b([
  d({ attribute: !1 })
], y.prototype, "hass", 2);
b([
  d({ attribute: !1 })
], y.prototype, "frame", 2);
b([
  d({ attribute: !1 })
], y.prototype, "frames", 2);
b([
  d({ attribute: !1 })
], y.prototype, "photo", 2);
b([
  d({ attribute: !1 })
], y.prototype, "inherited", 2);
b([
  l()
], y.prototype, "draft", 2);
b([
  l()
], y.prototype, "name", 2);
b([
  l()
], y.prototype, "enabled", 2);
b([
  l()
], y.prototype, "hideOverlays", 2);
b([
  l()
], y.prototype, "preview", 2);
b([
  l()
], y.prototype, "rendering", 2);
b([
  l()
], y.prototype, "lockAspect", 2);
b([
  l()
], y.prototype, "error", 2);
b([
  l()
], y.prototype, "notice", 2);
b([
  l()
], y.prototype, "busy", 2);
y = b([
  S("pp-photo-editor")
], y);
var we = Object.defineProperty, _e = Object.getOwnPropertyDescriptor, g = (t, e, s, i) => {
  for (var r = i > 1 ? void 0 : i ? _e(e, s) : e, a = t.length - 1, p; a >= 0; a--)
    (p = t[a]) && (r = (i ? p(e, s, r) : p(r)) || r);
  return i && r && we(e, s, r), r;
};
const ke = 400, Pe = ["portrait", "landscape", "portrait_flipped", "landscape_flipped"], V = class V extends j {
  constructor() {
    super(...arguments), this.preview = null, this.previewAspect = "5 / 3", this.rendering = !1, this.error = null, this.status = null, this.queue = new J(
      (e) => this.loadPreview(e),
      (e) => this.rendering = e
    );
  }
  disconnectedCallback() {
    super.disconnectedCallback(), this.queue.cancel();
  }
  schedulePreview(e = ke) {
    this.queue.schedule(e);
  }
  async loadPreview(e) {
    const s = this.previewRequest();
    if (!s) {
      this.preview = null;
      return;
    }
    try {
      const i = await ct(this.hass, s.frame.entry_id, s.photoId, s.settings);
      if (e()) return;
      this.preview = i.image, this.previewAspect = `${i.width} / ${i.height}`;
    } catch (i) {
      e() || (this.error = c(i));
    }
  }
  renderPreviewPane(e) {
    const s = m(this.hass);
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
V.styles = [
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
let k = V;
g([
  d({ attribute: !1 })
], k.prototype, "hass", 2);
g([
  l()
], k.prototype, "preview", 2);
g([
  l()
], k.prototype, "previewAspect", 2);
g([
  l()
], k.prototype, "rendering", 2);
g([
  l()
], k.prototype, "error", 2);
g([
  l()
], k.prototype, "status", 2);
let C = class extends k {
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
      await ht(this.hass, this.frame.entry_id, {
        render_defaults: this.draft,
        mounting: this.mounting,
        interval: Math.max(1, this.intervalMin) * 60
      }), this.status = "saved", this.schedulePreview(200);
    } catch (t) {
      this.error = c(t);
    }
  }
  render() {
    if (!this.defaults) return n;
    const t = m(this.hass), e = X(this.defaults.builtin, this.defaults.defaults), s = this.photos.length ? o`<label class="field">
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
            ${Pe.map(
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
g([
  d({ attribute: !1 })
], C.prototype, "frame", 2);
g([
  d({ attribute: !1 })
], C.prototype, "photos", 2);
g([
  d({ attribute: !1 })
], C.prototype, "defaults", 2);
g([
  l()
], C.prototype, "draft", 2);
g([
  l()
], C.prototype, "mounting", 2);
g([
  l()
], C.prototype, "intervalMin", 2);
g([
  l()
], C.prototype, "sampleId", 2);
C = g([
  S("pp-frame-settings")
], C);
let T = class extends k {
  constructor() {
    super(...arguments), this.frames = [], this.draft = {}, this.sampleFrameId = null, this.samplePhotos = [], this.samplePhotoId = null;
  }
  willUpdate(t) {
    t.has("defaults") && this.defaults && !t.get("defaults") && (this.draft = structuredClone(this.defaults.defaults ?? {})), t.has("frames") && !this.sampleFrameId && this.frames.length && this.pickFrame(this.frames.find((e) => e.photo_count)?.entry_id ?? this.frames[0].entry_id);
  }
  async pickFrame(t) {
    this.sampleFrameId = t, this.samplePhotos = await H(this.hass, t), this.samplePhotoId = this.samplePhotos[0]?.photo_id ?? null, this.schedulePreview(0);
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
      const t = await Yt(this.hass, this.draft);
      this.defaults = { ...this.defaults, defaults: t.defaults }, this.status = "saved";
    } catch (t) {
      this.error = c(t);
    }
  }
  render() {
    if (!this.defaults) return n;
    const t = m(this.hass), e = o`<div class="sample">
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
T.styles = [
  ...k.styles,
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
g([
  d({ attribute: !1 })
], T.prototype, "frames", 2);
g([
  d({ attribute: !1 })
], T.prototype, "defaults", 2);
g([
  l()
], T.prototype, "draft", 2);
g([
  l()
], T.prototype, "sampleFrameId", 2);
g([
  l()
], T.prototype, "samplePhotos", 2);
g([
  l()
], T.prototype, "samplePhotoId", 2);
T = g([
  S("pp-global-settings")
], T);
var Oe = Object.defineProperty, Ee = Object.getOwnPropertyDescriptor, O = (t, e, s, i) => {
  for (var r = i > 1 ? void 0 : i ? Ee(e, s) : e, a = t.length - 1, p; a >= 0; a--)
    (p = t[a]) && (r = (i ? p(e, s, r) : p(r)) || r);
  return i && r && Oe(e, s, r), r;
};
const I = "global", Se = 250;
let w = class extends j {
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
    this.unsubscribe = Ft(this.hass, (t) => {
      this.dirtyEntries.add(t), window.clearTimeout(this.refreshTimer), this.refreshTimer = window.setTimeout(() => this.refresh(), Se);
    }), this.loadAll();
  }
  async loadAll() {
    try {
      const [t, e] = await Promise.all([st(this.hass), Qt(this.hass)]);
      this.frames = t, this.defaults = e;
      const s = this.route?.path?.replace(/^\//, "").split("/")[0], i = s && (s === I || t.some((r) => r.entry_id === s)) && s || t[0]?.entry_id || null;
      i && await this.select(i);
    } catch (t) {
      this.error = c(t);
    }
  }
  async refresh() {
    const t = new Set(this.dirtyEntries);
    this.dirtyEntries.clear();
    try {
      this.frames = await st(this.hass), this.selected && this.selected !== I && (this.frames.some((e) => e.entry_id === this.selected) ? (t.has(this.selected) || t.has(null)) && (this.photos = await H(this.hass, this.selected)) : await this.select(this.frames[0]?.entry_id ?? I));
    } catch (e) {
      this.error = c(e);
    }
  }
  async select(t) {
    if (this.selected = t, this.editing = null, history.replaceState(null, "", `/paperlessoffline/${t}`), t === I) {
      this.photos = [];
      return;
    }
    try {
      this.photos = await H(this.hass, t);
    } catch (e) {
      this.error = c(e);
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
    const t = m(this.hass);
    return this.narrow ? o`<div class="nav-narrow">
        <select @change=${(e) => this.select(e.target.value)}>
          ${(this.frames ?? []).map(
      (e) => o`<option value=${e.entry_id} ?selected=${e.entry_id === this.selected}>${e.title}</option>`
    )}
          <option value=${I} ?selected=${this.selected === I}>${t("global_defaults")}</option>
        </select>
      </div>` : o`<nav>
      <div class="nav-title muted">${t("frames")}</div>
      ${(this.frames ?? []).map(
      (e) => o`<button
          class="nav-item ${e.entry_id === this.selected ? "active" : ""}"
          @click=${() => this.select(e.entry_id)}
        >
          ${u(Ct)}
          <span class="nav-text">
            <span>${e.title}</span>
            <span class="muted small">${U(e.last_seen, this.hass, t("never"))}</span>
          </span>
          ${e.pending.length ? o`<span class="dot" title=${t("pending")}></span>` : n}
        </button>`
    )}
      <hr />
      <button
        class="nav-item ${this.selected === I ? "active" : ""}"
        @click=${() => this.select(I)}
      >
        ${u(Tt)} <span class="nav-text">${t("global_defaults")}</span>
      </button>
    </nav>`;
  }
  renderStatus(t) {
    const e = m(this.hass), s = this.previewUrl(t, "preview_showing"), i = this.previewUrl(t, "preview_up_next"), r = t.up_next.kind === "override" ? e("override") : t.up_next.kind === "placeholder" ? e("placeholder") : t.up_next.name ?? "";
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
        <figcaption><span class="muted">${e("up_next")}</span> ${r}</figcaption>
      </figure>
      <div class="facts">
        <h1>${t.title}</h1>
        <div class="muted">${t.panel.model} · ${t.client_id}</div>
        <div>
          ${e("last_seen")}: <strong>${U(t.last_seen, this.hass, e("never"))}</strong>
        </div>
        <div class="chips">
          ${t.pending.length ? o`<span class="chip warn">
                ${e("pending")}: ${t.pending.map((a) => e(`pending_${a}`)).join(", ")}
              </span>` : o`<span class="chip ok">${e("in_sync")}</span>`}
          ${t.needs_reprovision ? o`<span class="chip warn">${e("needs_urls")}</span>` : t.overdue ? o`<span class="chip warn">${e("overdue")}</span>` : n}
          ${t.ble?.voltage !== void 0 ? o`<span class="chip" title=${e("read_ago", { when: U(t.ble.read_at, this.hass, e("never")) })}>
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
            @click=${() => qt(this.hass, t.entry_id).catch((a) => this.error = c(a))}
          >
            ${u(jt)} ${e("skip")}
          </button>
        </div>
      </div>
    </div>`;
  }
  renderMain() {
    const t = m(this.hass);
    if (this.frames === null) return o`<p class="muted">${t("loading")}</p>`;
    if (this.selected === I)
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
            ></pp-frame-settings>
            <pp-overlays
              .hass=${this.hass}
              .frame=${e}
              .frames=${this.frames}
              .photos=${this.photos}
            ></pp-overlays>`}
      ${this.editing && this.defaults ? o`<pp-photo-editor
            .hass=${this.hass}
            .frame=${e}
            .frames=${this.frames}
            .photo=${this.editing}
            .inherited=${X(this.defaults.builtin, this.defaults.defaults, e.render_defaults)}
            @closed=${() => this.editing = null}
          ></pp-photo-editor>` : n}
    ` : o`<p class="muted empty">${t("no_frames")}</p>`;
  }
  render() {
    const t = m(this.hass);
    return o`
      <header class="toolbar">
        ${this.narrow ? o`<button class="icon-btn" title="Menu" @click=${this.toggleMenu}>${u(zt)}</button>` : n}
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
w.styles = [
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
O([
  d({ attribute: !1 })
], w.prototype, "hass", 2);
O([
  d({ type: Boolean, reflect: !0 })
], w.prototype, "narrow", 2);
O([
  d({ attribute: !1 })
], w.prototype, "route", 2);
O([
  l()
], w.prototype, "frames", 2);
O([
  l()
], w.prototype, "selected", 2);
O([
  l()
], w.prototype, "tab", 2);
O([
  l()
], w.prototype, "photos", 2);
O([
  l()
], w.prototype, "defaults", 2);
O([
  l()
], w.prototype, "editing", 2);
O([
  l()
], w.prototype, "error", 2);
w = O([
  S("paperlessoffline-panel")
], w);
export {
  w as PaperlessPanel
};
