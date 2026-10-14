import { mdiImageEdit, mdiSkipNext } from "@mdi/js";
import { LitElement, css, html, nothing } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import { localizer, relativeTime } from "./localize";
import { icon, sharedStyles } from "./styles";
import type { HomeAssistant } from "./types";

interface CardConfig {
  type: string;
  device_id: string;
  show_up_next?: boolean;
  title?: string;
}

type Hass = HomeAssistant & {
  devices: Record<string, { id: string; name?: string; name_by_user?: string; config_entries?: string[] }>;
};

const DOMAIN = "paperlessoffline";

/** Find one of the frame's entities by its translation key (falling back to the entity id). */
function findEntity(hass: Hass, deviceId: string, domain: string, key: string): string | undefined {
  const entries = Object.values(hass.entities ?? {}).filter(
    (e) => e.device_id === deviceId && e.platform === DOMAIN && e.entity_id.startsWith(`${domain}.`),
  );
  return (
    entries.find((e) => e.translation_key === key)?.entity_id ??
    entries.find((e) => e.entity_id.endsWith(`_${key.replace(/^preview_/, "")}`))?.entity_id
  );
}

/** Lovelace card showing what a frame displays, what's next, and its sync state. */
@customElement("paperlessoffline-frame-card")
export class FrameCard extends LitElement {
  @property({ attribute: false }) hass!: Hass;
  @state() private config!: CardConfig;

  static getConfigForm() {
    return {
      schema: [
        { name: "device_id", required: true, selector: { device: { integration: DOMAIN } } },
        { name: "title", selector: { text: {} } },
        { name: "show_up_next", selector: { boolean: {} } },
      ],
      computeLabel: (schema: { name: string }) =>
        ({ device_id: "Frame", title: "Title", show_up_next: "Show up next" })[schema.name] ?? schema.name,
    };
  }

  static getStubConfig(hass: Hass): Partial<CardConfig> {
    const entity = Object.values(hass.entities ?? {}).find((e) => e.platform === DOMAIN && e.device_id);
    return { device_id: entity?.device_id ?? "", show_up_next: true };
  }

  setConfig(config: CardConfig) {
    if (!config.device_id) throw new Error("Choose a frame (device_id)");
    this.config = { show_up_next: true, ...config };
  }

  getCardSize() {
    return 6;
  }

  getGridOptions() {
    return { columns: 6, rows: "auto", min_columns: 4 };
  }

  private press(entityId: string | undefined) {
    if (entityId) this.hass.callService("button", "press", { entity_id: entityId });
  }

  private openPanel(entryId: string | undefined) {
    history.pushState(null, "", `/${DOMAIN}/${entryId ?? ""}`);
    window.dispatchEvent(new CustomEvent("location-changed", { detail: { replace: false } }));
  }

  protected override render() {
    if (!this.config || !this.hass) return nothing;
    const l = localizer(this.hass);
    const id = this.config.device_id;
    const device = this.hass.devices?.[id];
    const state = (domain: string, key: string) => {
      const entityId = findEntity(this.hass, id, domain, key);
      return entityId ? this.hass.states[entityId] : undefined;
    };
    const showing = state("image", "preview_showing");
    const upNext = state("image", "preview_up_next");
    const lastSeen = state("sensor", "last_seen");
    const current = state("sensor", "current_photo");
    const inSync = state("binary_sensor", "in_sync");
    const nextSelect = state("select", "up_next");
    const skipId = findEntity(this.hass, id, "button", "skip");
    const pending: string[] = inSync?.attributes.pending ?? [];
    const title = this.config.title || device?.name_by_user || device?.name || "Frame";

    if (!showing) {
      return html`<ha-card><div class="missing">Frame not found: ${id}</div></ha-card>`;
    }
    return html`<ha-card>
      <div class="head">
        <span class="title">${title}</span>
        ${inSync?.state === "on"
          ? html`<span class="chip ok">${l("in_sync")}</span>`
          : html`<span class="chip warn" title=${pending.map((p) => l(`pending_${p}` as never)).join(", ")}>
              ${l("pending")}
            </span>`}
      </div>
      <div class="frames ${this.config.show_up_next ? "two" : ""}">
        <figure>
          <div class="pic ${showing.attributes.entity_picture ? "" : "empty"}">
            ${showing.attributes.entity_picture
              ? html`<img src=${showing.attributes.entity_picture} alt=${l("showing")} />`
              : nothing}
          </div>
          <figcaption><span class="muted">${l("showing")}</span> ${current?.state ?? ""}</figcaption>
        </figure>
        ${this.config.show_up_next && upNext
          ? html`<figure class="next">
              <div class="pic ${upNext.attributes.entity_picture ? "" : "empty"}">
                ${upNext.attributes.entity_picture
                  ? html`<img src=${upNext.attributes.entity_picture} alt=${l("up_next")} />`
                  : nothing}
              </div>
              <figcaption>
                <span class="muted">${l("up_next")}</span> ${nextSelect?.state ?? ""}
              </figcaption>
            </figure>`
          : nothing}
      </div>
      <div class="foot">
        <span class="muted">
          ${l("last_seen")}: ${relativeTime(lastSeen?.state && lastSeen.state !== "unknown" ? lastSeen.state : null, this.hass, l("never"))}
        </span>
        <span class="spacer"></span>
        ${this.hass.user?.is_admin
          ? html`<button
              class="icon-btn"
              title=${l("manage")}
              @click=${() => this.openPanel(device?.config_entries?.[0])}
            >
              ${icon(mdiImageEdit)}
            </button>`
          : nothing}
        <button class="btn" ?disabled=${!skipId} @click=${() => this.press(skipId)}>
          ${icon(mdiSkipNext)} ${l("skip")}
        </button>
      </div>
    </ha-card>`;
  }

  static override styles = [
    sharedStyles,
    css`
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
    `,
  ];
}

declare global {
  interface Window {
    customCards?: { type: string; name: string; description: string; preview?: boolean }[];
  }
}

window.customCards = window.customCards ?? [];
if (!window.customCards.some((c) => c.type === "paperlessoffline-frame-card")) {
  window.customCards.push({
    type: "paperlessoffline-frame-card",
    name: "paperlesspaper frame",
    description: "What an e-paper frame shows, what's up next, and whether it is in sync.",
    preview: true,
  });
}
