import { s as $, i as C, n as S, r as O, a as j, A as o, l as P, b as r, c as k, d as g, m as z, e as E, t as F } from "./chunk-Cxvkc_S1.js";
var D = Object.defineProperty, I = Object.getOwnPropertyDescriptor, u = (e, n, a, s) => {
  for (var i = s > 1 ? void 0 : s ? I(n, a) : n, t = e.length - 1, p; t >= 0; t--)
    (p = e[t]) && (i = (s ? p(n, a, i) : p(i)) || i);
  return s && i && D(n, a, i), i;
};
const d = "paperlessoffline";
function _(e, n, a, s) {
  const i = Object.values(e.entities ?? {}).filter(
    (t) => t.device_id === n && t.platform === d && t.entity_id.startsWith(`${a}.`)
  );
  return i.find((t) => t.translation_key === s)?.entity_id ?? i.find((t) => t.entity_id.endsWith(`_${s.replace(/^preview_/, "")}`))?.entity_id;
}
let c = class extends j {
  static getConfigForm() {
    return {
      schema: [
        { name: "device_id", required: !0, selector: { device: { integration: d } } },
        { name: "title", selector: { text: {} } },
        { name: "show_up_next", selector: { boolean: {} } }
      ],
      computeLabel: (e) => ({ device_id: "Frame", title: "Title", show_up_next: "Show up next" })[e.name] ?? e.name
    };
  }
  static getStubConfig(e) {
    return { device_id: Object.values(e.entities ?? {}).find((a) => a.platform === d && a.device_id)?.device_id ?? "", show_up_next: !0 };
  }
  setConfig(e) {
    if (!e.device_id) throw new Error("Choose a frame (device_id)");
    this.config = { show_up_next: !0, ...e };
  }
  getCardSize() {
    return 6;
  }
  getGridOptions() {
    return { columns: 6, rows: "auto", min_columns: 4 };
  }
  press(e) {
    e && this.hass.callService("button", "press", { entity_id: e });
  }
  openPanel(e) {
    history.pushState(null, "", `/${d}/${e ?? ""}`), window.dispatchEvent(new CustomEvent("location-changed", { detail: { replace: !1 } }));
  }
  render() {
    if (!this.config || !this.hass) return o;
    const e = P(this.hass), n = this.config.device_id, a = this.hass.devices?.[n], s = (l, b) => {
      const m = _(this.hass, n, l, b);
      return m ? this.hass.states[m] : void 0;
    }, i = s("image", "preview_showing"), t = s("image", "preview_up_next"), p = s("sensor", "last_seen"), w = s("sensor", "current_photo"), f = s("binary_sensor", "in_sync"), v = s("select", "up_next"), h = _(this.hass, n, "button", "skip"), x = f?.attributes.pending ?? [], y = this.config.title || a?.name_by_user || a?.name || "Frame";
    return i ? r`<ha-card>
      <div class="head">
        <span class="title">${y}</span>
        ${f?.state === "on" ? r`<span class="chip ok">${e("in_sync")}</span>` : r`<span class="chip warn" title=${x.map((l) => e(`pending_${l}`)).join(", ")}>
              ${e("pending")}
            </span>`}
      </div>
      <div class="frames ${this.config.show_up_next ? "two" : ""}">
        <figure>
          <div class="pic ${i.attributes.entity_picture ? "" : "empty"}">
            ${i.attributes.entity_picture ? r`<img src=${i.attributes.entity_picture} alt=${e("showing")} />` : o}
          </div>
          <figcaption><span class="muted">${e("showing")}</span> ${w?.state ?? "–"}</figcaption>
        </figure>
        ${this.config.show_up_next && t ? r`<figure class="next">
              <div class="pic ${t.attributes.entity_picture ? "" : "empty"}">
                ${t.attributes.entity_picture ? r`<img src=${t.attributes.entity_picture} alt=${e("up_next")} />` : o}
              </div>
              <figcaption>
                <span class="muted">${e("up_next")}</span> ${v?.state ?? "–"}
              </figcaption>
            </figure>` : o}
      </div>
      <div class="foot">
        <span class="muted">
          ${e("last_seen")}: ${k(p?.state && p.state !== "unknown" ? p.state : null, this.hass, e("never"))}
        </span>
        <span class="spacer"></span>
        ${this.hass.user?.is_admin ? r`<button
              class="icon-btn"
              title=${e("manage")}
              @click=${() => this.openPanel(a?.config_entries?.[0])}
            >
              ${g(z)}
            </button>` : o}
        <button class="btn" ?disabled=${!h} @click=${() => this.press(h)}>
          ${g(E)} ${e("skip")}
        </button>
      </div>
    </ha-card>` : r`<ha-card><div class="missing">Frame not found: ${n}</div></ha-card>`;
  }
};
c.styles = [
  $,
  C`
      ha-card {
        padding: 16px;
        display: grid;
        gap: 12px;
      }
      .head {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 8px;
      }
      .title {
        font-size: 18px;
        font-weight: 500;
      }
      .frames {
        display: grid;
        gap: 16px;
        align-items: end;
      }
      .frames.two {
        grid-template-columns: 2fr 1fr;
      }
      figure {
        margin: 0;
        display: grid;
        gap: 6px;
        min-width: 0;
      }
      .pic {
        background: #d6d6d6;
        border-radius: 3px;
        overflow: hidden;
        box-shadow: 0 0 0 5px #2b2b2b, 0 2px 10px 5px rgba(0, 0, 0, 0.22);
        margin: 5px;
        line-height: 0;
      }
      .pic img {
        width: 100%;
        display: block;
      }
      .pic.empty {
        aspect-ratio: 3 / 5;
      }
      .next .pic {
        opacity: 0.85;
      }
      figcaption {
        font-size: 13px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
      .foot {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 14px;
      }
      .spacer {
        flex: 1;
      }
      .missing {
        padding: 16px;
      }
    `
];
u([
  S({ attribute: !1 })
], c.prototype, "hass", 2);
u([
  O()
], c.prototype, "config", 2);
c = u([
  F("paperlessoffline-frame-card")
], c);
window.customCards = window.customCards ?? [];
window.customCards.some((e) => e.type === "paperlessoffline-frame-card") || window.customCards.push({
  type: "paperlessoffline-frame-card",
  name: "paperlesspaper frame",
  description: "What an e-paper frame shows, what's up next, and whether it is in sync.",
  preview: !0
});
export {
  c as FrameCard
};
