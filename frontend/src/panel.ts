import { mdiCog, mdiImageFrame, mdiMenu, mdiSkipNext } from "@mdi/js";
import { LitElement, css, html, nothing, type PropertyValues } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import { errorMessage, fetchDefaults, fetchFrames, fetchPhotos, skipPhoto, subscribeChanges } from "./api";
import "./library";
import "./overlays";
import { localizer, relativeTime } from "./localize";
import "./photo-editor";
import { resolveSettings } from "./render-settings";
import "./settings-views";
import { icon, sharedStyles } from "./styles";
import type { Defaults, Frame, HomeAssistant, Photo } from "./types";

const GLOBAL = "global";
const REFRESH_DELAY = 250;

/** Sidebar panel: frames, their libraries and settings, plus global defaults. */
@customElement("paperlessoffline-panel")
export class PaperlessPanel extends LitElement {
  @property({ attribute: false }) hass!: HomeAssistant;
  @property({ type: Boolean, reflect: true }) narrow = false;
  @property({ attribute: false }) route?: { prefix: string; path: string };

  @state() private frames: Frame[] | null = null;
  @state() private selected: string | null = null;
  @state() private tab: "photos" | "settings" = "photos";
  @state() private photos: Photo[] = [];
  @state() private defaults: Defaults | null = null;
  @state() private editing: Photo | null = null;
  @state() private error: string | null = null;

  private unsubscribe?: Promise<() => Promise<void>>;
  private refreshTimer?: number;
  private dirtyEntries = new Set<string | null>();

  override connectedCallback() {
    super.connectedCallback();
    if (this.hass) this.start();
  }

  override disconnectedCallback() {
    super.disconnectedCallback();
    this.unsubscribe?.then((unsub) => unsub()).catch(() => undefined);
    this.unsubscribe = undefined;
    window.clearTimeout(this.refreshTimer);
  }

  protected override willUpdate(changed: PropertyValues) {
    if (changed.has("hass") && this.hass && !this.unsubscribe && this.isConnected) this.start();
  }

  private start() {
    this.unsubscribe = subscribeChanges(this.hass, (entryId) => {
      this.dirtyEntries.add(entryId);
      window.clearTimeout(this.refreshTimer);
      this.refreshTimer = window.setTimeout(() => this.refresh(), REFRESH_DELAY);
    });
    this.loadAll();
  }

  private async loadAll() {
    try {
      const [frames, defaults] = await Promise.all([fetchFrames(this.hass), fetchDefaults(this.hass)]);
      this.frames = frames;
      this.defaults = defaults;
      const fromUrl = this.route?.path?.replace(/^\//, "").split("/")[0];
      const initial =
        (fromUrl && (fromUrl === GLOBAL || frames.some((f) => f.entry_id === fromUrl)) && fromUrl) ||
        frames[0]?.entry_id ||
        null;
      if (initial) await this.select(initial);
    } catch (err) {
      this.error = errorMessage(err);
    }
  }

  private async refresh() {
    const entries = new Set(this.dirtyEntries);
    this.dirtyEntries.clear();
    try {
      this.frames = await fetchFrames(this.hass);
      if (this.selected && this.selected !== GLOBAL) {
        if (!this.frames.some((f) => f.entry_id === this.selected)) {
          await this.select(this.frames[0]?.entry_id ?? GLOBAL);
        } else if (entries.has(this.selected) || entries.has(null)) {
          this.photos = await fetchPhotos(this.hass, this.selected);
        }
      }
    } catch (err) {
      this.error = errorMessage(err);
    }
  }

  private async select(id: string) {
    this.selected = id;
    this.editing = null;
    history.replaceState(null, "", `/paperlessoffline/${id}`);
    if (id === GLOBAL) {
      this.photos = [];
      return;
    }
    try {
      this.photos = await fetchPhotos(this.hass, id);
    } catch (err) {
      this.error = errorMessage(err);
    }
  }

  private get frame(): Frame | undefined {
    return this.frames?.find((f) => f.entry_id === this.selected);
  }

  /** The frame's "Showing"/"Up next" image entity, for its tokenised picture URL. */
  private previewUrl(frame: Frame, key: "preview_showing" | "preview_up_next"): string | null {
    if (!frame.device_id) return null;
    const entity = Object.values(this.hass.entities ?? {}).find(
      (e) => e.device_id === frame.device_id && e.platform === "paperlessoffline" && e.translation_key === key,
    );
    return (entity && this.hass.states[entity.entity_id]?.attributes.entity_picture) || null;
  }

  private toggleMenu() {
    this.dispatchEvent(new CustomEvent("hass-toggle-menu", { bubbles: true, composed: true }));
  }

  private renderNav() {
    const l = localizer(this.hass);
    if (this.narrow) {
      return html`<div class="nav-narrow">
        <select @change=${(e: Event) => this.select((e.target as HTMLSelectElement).value)}>
          ${(this.frames ?? []).map(
            (f) => html`<option value=${f.entry_id} ?selected=${f.entry_id === this.selected}>${f.title}</option>`,
          )}
          <option value=${GLOBAL} ?selected=${this.selected === GLOBAL}>${l("global_defaults")}</option>
        </select>
      </div>`;
    }
    return html`<nav>
      <div class="nav-title muted">${l("frames")}</div>
      ${(this.frames ?? []).map(
        (f) => html`<button
          class="nav-item ${f.entry_id === this.selected ? "active" : ""}"
          @click=${() => this.select(f.entry_id)}
        >
          ${icon(mdiImageFrame)}
          <span class="nav-text">
            <span>${f.title}</span>
            <span class="muted small">${relativeTime(f.last_seen, this.hass, l("never"))}</span>
          </span>
          ${f.pending.length ? html`<span class="dot" title=${l("pending")}></span>` : nothing}
        </button>`,
      )}
      <hr />
      <button
        class="nav-item ${this.selected === GLOBAL ? "active" : ""}"
        @click=${() => this.select(GLOBAL)}
      >
        ${icon(mdiCog)} <span class="nav-text">${l("global_defaults")}</span>
      </button>
    </nav>`;
  }

  private renderStatus(frame: Frame) {
    const l = localizer(this.hass);
    const showing = this.previewUrl(frame, "preview_showing");
    const upNext = this.previewUrl(frame, "preview_up_next");
    const upNextLabel =
      frame.up_next.kind === "override"
        ? l("override")
        : frame.up_next.kind === "placeholder"
          ? l("placeholder")
          : (frame.up_next.name ?? "");
    return html`<div class="status card">
      <figure>
        <div class="pic" style="aspect-ratio:${frame.canvas.width}/${frame.canvas.height}">
          ${showing ? html`<img src=${showing} alt="" />` : nothing}
        </div>
        <figcaption><span class="muted">${l("showing")}</span> ${frame.current.name ?? ""}</figcaption>
      </figure>
      <figure>
        <div class="pic" style="aspect-ratio:${frame.canvas.width}/${frame.canvas.height}">
          ${upNext ? html`<img src=${upNext} alt="" />` : nothing}
        </div>
        <figcaption><span class="muted">${l("up_next")}</span> ${upNextLabel}</figcaption>
      </figure>
      <div class="facts">
        <h1>${frame.title}</h1>
        <div class="muted">${frame.panel.model} · ${frame.client_id}</div>
        <div>
          ${l("last_seen")}: <strong>${relativeTime(frame.last_seen, this.hass, l("never"))}</strong>
        </div>
        <div class="chips">
          ${frame.pending.length
            ? html`<span class="chip warn">
                ${l("pending")}: ${frame.pending.map((p) => l(`pending_${p}` as never)).join(", ")}
              </span>`
            : html`<span class="chip ok">${l("in_sync")}</span>`}
          ${frame.needs_reprovision
            ? html`<span class="chip warn">${l("needs_urls")}</span>`
            : frame.overdue
              ? html`<span class="chip warn">${l("overdue")}</span>`
              : nothing}
          ${frame.ble?.voltage !== undefined
            ? html`<span class="chip" title=${l("read_ago", { when: relativeTime(frame.ble.read_at, this.hass, l("never")) })}>
                ${l("battery", { volts: (frame.ble.voltage / 1000).toFixed(2) })}${frame.ble.charging
                  ? ` · ${l("charging")}`
                  : frame.ble.usb
                    ? ` · ${l("usb")}`
                    : ""}
              </span>`
            : nothing}
          ${frame.override
            ? html`<span class="chip">
                ${l("override")}: ${frame.override.name} ·
                ${frame.override.wakes_remaining === null
                  ? l("until_cleared")
                  : l("wakes_left", { n: frame.override.wakes_remaining })}
              </span>`
            : nothing}
        </div>
        <div>
          <button
            class="btn"
            ?disabled=${frame.up_next.kind !== "photo" || frame.enabled_count < 2}
            @click=${() => skipPhoto(this.hass, frame.entry_id).catch((e) => (this.error = errorMessage(e)))}
          >
            ${icon(mdiSkipNext)} ${l("skip")}
          </button>
        </div>
      </div>
    </div>`;
  }

  private renderMain() {
    const l = localizer(this.hass);
    if (this.frames === null) return html`<p class="muted">${l("loading")}</p>`;
    if (this.selected === GLOBAL) {
      return html`<pp-global-settings
        .hass=${this.hass}
        .frames=${this.frames}
        .defaults=${this.defaults}
      ></pp-global-settings>`;
    }
    const frame = this.frame;
    if (!frame) return html`<p class="muted empty">${l("no_frames")}</p>`;
    return html`
      ${this.renderStatus(frame)}
      <div class="tabs" role="tablist">
        ${(["photos", "settings"] as const).map(
          (t) => html`<button
            role="tab"
            aria-selected=${this.tab === t}
            class=${this.tab === t ? "active" : ""}
            @click=${() => (this.tab = t)}
          >
            ${l(`tab_${t}`)}
          </button>`,
        )}
      </div>
      ${this.tab === "photos"
        ? html`<pp-library
            .hass=${this.hass}
            .frame=${frame}
            .photos=${this.photos}
            @edit-photo=${(e: CustomEvent<{ photo: Photo }>) => (this.editing = e.detail.photo)}
          ></pp-library>`
        : html`<pp-frame-settings
              .hass=${this.hass}
              .frame=${frame}
              .photos=${this.photos}
              .defaults=${this.defaults}
            ></pp-frame-settings>
            <pp-overlays
              .hass=${this.hass}
              .frame=${frame}
              .frames=${this.frames}
              .photos=${this.photos}
            ></pp-overlays>`}
      ${this.editing && this.defaults
        ? html`<pp-photo-editor
            .hass=${this.hass}
            .frame=${frame}
            .frames=${this.frames}
            .photo=${this.editing}
            .inherited=${resolveSettings(this.defaults.builtin, this.defaults.defaults, frame.render_defaults)}
            @closed=${() => (this.editing = null)}
          ></pp-photo-editor>`
        : nothing}
    `;
  }

  protected override render() {
    const l = localizer(this.hass);
    return html`
      <header class="toolbar">
        ${this.narrow
          ? html`<button class="icon-btn" title="Menu" @click=${this.toggleMenu}>${icon(mdiMenu)}</button>`
          : nothing}
        <div class="app-title">${l("title")}</div>
      </header>
      <div class="layout">
        ${this.frames?.length ? this.renderNav() : nothing}
        <main>
          ${this.error
            ? html`<p class="error" @click=${() => (this.error = null)}>${l("error", { error: this.error })}</p>`
            : nothing}
          ${this.renderMain()}
        </main>
      </div>
    `;
  }

  static override styles = [
    sharedStyles,
    css`
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
    `,
  ];
}

declare global {
  interface HTMLElementTagNameMap {
    "paperlessoffline-panel": PaperlessPanel;
  }
}
