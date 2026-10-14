import { LitElement, css, html, nothing, type PropertyValues } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import { errorMessage, fetchPhotos, renderPreview, saveDefaults, updateFrame } from "./api";
import { localizer } from "./localize";
import "./render-settings";
import { resolveSettings } from "./render-settings";
import { sharedStyles } from "./styles";
import type { Defaults, Frame, FrameSettings, HomeAssistant, Mounting, Photo } from "./types";

const PREVIEW_DELAY = 400;
const MOUNTINGS: Mounting[] = ["portrait", "landscape", "portrait_flipped", "landscape_flipped"];

/** Debounced dithered preview of one sample photo. */
abstract class PreviewingView extends LitElement {
  @property({ attribute: false }) hass!: HomeAssistant;
  @state() protected preview: string | null = null;
  @state() protected previewAspect = "5 / 3";
  @state() protected rendering = false;
  @state() protected error: string | null = null;
  @state() protected status: "saved" | null = null;
  private timer?: number;
  private seq = 0;

  override disconnectedCallback() {
    super.disconnectedCallback();
    window.clearTimeout(this.timer);
  }

  protected abstract previewRequest(): { frame: Frame; photoId: string; settings: object } | null;

  protected schedulePreview(delay = PREVIEW_DELAY) {
    window.clearTimeout(this.timer);
    this.timer = window.setTimeout(() => this.loadPreview(), delay);
  }

  private async loadPreview() {
    const req = this.previewRequest();
    if (!req) {
      this.preview = null;
      return;
    }
    const seq = ++this.seq;
    this.rendering = true;
    try {
      const res = await renderPreview(this.hass, req.frame.entry_id, req.photoId, req.settings);
      if (seq === this.seq) {
        this.preview = res.image;
        this.previewAspect = `${res.width} / ${res.height}`;
      }
    } catch (err) {
      if (seq === this.seq) this.error = errorMessage(err);
    } finally {
      if (seq === this.seq) this.rendering = false;
    }
  }

  protected renderPreviewPane(sampleSelect: unknown) {
    const l = localizer(this.hass);
    return html`<div class="preview-pane">
      <div class="pane-head">
        <span class="h">${l("preview")}</span>
        ${this.rendering ? html`<span class="muted">${l("rendering")}</span>` : nothing}
      </div>
      ${sampleSelect}
      <div class="preview" style="aspect-ratio:${this.previewAspect}">
        ${this.preview ? html`<img src=${this.preview} alt=${l("preview")} />` : nothing}
      </div>
      <span class="muted hint">${l("preview_hint")}</span>
    </div>`;
  }

  static override styles = [
    sharedStyles,
    css`
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
    `,
  ];
}

/** Per-frame settings: order, mounting, interval and rendering defaults. */
@customElement("pp-frame-settings")
export class FrameSettingsView extends PreviewingView {
  @property({ attribute: false }) frame!: Frame;
  @property({ attribute: false }) photos: Photo[] = [];
  @property({ attribute: false }) defaults!: Defaults;

  @state() private draft: FrameSettings = {};
  @state() private mounting: Mounting = "portrait";
  @state() private intervalMin = 60;
  @state() private sampleId: string | null = null;

  protected override willUpdate(changed: PropertyValues) {
    if (changed.has("frame") && (changed.get("frame") as Frame | undefined)?.entry_id !== this.frame.entry_id) {
      this.reset();
    }
    if (changed.has("photos") && !this.photos.some((p) => p.photo_id === this.sampleId)) {
      this.sampleId = this.photos[0]?.photo_id ?? null;
      this.schedulePreview(0);
    }
  }

  private reset() {
    this.draft = structuredClone(this.frame.render_defaults ?? {});
    this.mounting = this.frame.mounting;
    this.intervalMin = Math.round(this.frame.interval / 60);
    this.status = null;
    this.schedulePreview(0);
  }

  private get dirty() {
    return (
      JSON.stringify(this.draft) !== JSON.stringify(this.frame.render_defaults ?? {}) ||
      this.mounting !== this.frame.mounting ||
      this.intervalMin * 60 !== this.frame.interval
    );
  }

  protected previewRequest() {
    if (!this.sampleId) return null;
    return { frame: this.frame, photoId: this.sampleId, settings: { frame_defaults: this.draft } };
  }

  private async save() {
    this.error = null;
    try {
      await updateFrame(this.hass, this.frame.entry_id, {
        render_defaults: this.draft,
        mounting: this.mounting,
        interval: Math.max(1, this.intervalMin) * 60,
      });
      this.status = "saved";
      // Mounting changes the canvas: re-render with the saved settings.
      this.schedulePreview(200);
    } catch (err) {
      this.error = errorMessage(err);
    }
  }

  protected override render() {
    if (!this.defaults) return nothing;
    const l = localizer(this.hass);
    const inherited = resolveSettings(this.defaults.builtin, this.defaults.defaults);
    const sample = this.photos.length
      ? html`<label class="field">
          <span class="muted">${l("sample_photo")}</span>
          <select
            @change=${(e: Event) => {
              this.sampleId = (e.target as HTMLSelectElement).value;
              this.schedulePreview(0);
            }}
          >
            ${this.photos.map(
              (p) => html`<option value=${p.photo_id} ?selected=${p.photo_id === this.sampleId}>${p.name}</option>`,
            )}
          </select>
        </label>`
      : nothing;
    return html`
      <div class="form card">
        <h3>${l("frame_settings")}</h3>
        <label class="field">
          ${l("mounting")}
          <select @change=${(e: Event) => (this.mounting = (e.target as HTMLSelectElement).value as Mounting)}>
            ${MOUNTINGS.map(
              (m) => html`<option value=${m} ?selected=${m === this.mounting}>${l(`mounting_${m}`)}</option>`,
            )}
          </select>
        </label>
        <label class="field">
          ${l("interval")}
          <input
            type="number"
            min="1"
            max="10080"
            .value=${String(this.intervalMin)}
            @input=${(e: Event) => (this.intervalMin = Number((e.target as HTMLInputElement).value) || 1)}
          />
        </label>
        <h3>${l("frame_defaults")}</h3>
        <span class="muted">${l("frame_defaults_hint")}</span>
        <pp-render-settings
          with-palette
          .hass=${this.hass}
          .value=${this.draft}
          .inherited=${inherited}
          @value-changed=${(e: CustomEvent<{ value: FrameSettings }>) => {
            this.draft = e.detail.value;
            this.status = null;
            this.schedulePreview();
          }}
        ></pp-render-settings>
        <span class="muted hint">${l("more_options")}</span>
        ${this.error ? html`<span class="error">${l("error", { error: this.error })}</span>` : nothing}
        <div class="actions">
          ${this.dirty ? html`<span class="muted">${l("unsaved")}</span>` : nothing}
          ${!this.dirty && this.status === "saved" ? html`<span class="chip ok">${l("saved")}</span>` : nothing}
          <button class="btn" ?disabled=${!this.dirty} @click=${this.reset}>${l("cancel")}</button>
          <button class="btn primary" ?disabled=${!this.dirty} @click=${this.save}>${l("save")}</button>
        </div>
      </div>
      ${this.renderPreviewPane(sample)}
    `;
  }
}

/** Global rendering defaults, previewed on any frame's photo. */
@customElement("pp-global-settings")
export class GlobalSettingsView extends PreviewingView {
  @property({ attribute: false }) frames: Frame[] = [];
  @property({ attribute: false }) defaults!: Defaults;

  @state() private draft: FrameSettings = {};
  @state() private sampleFrameId: string | null = null;
  @state() private samplePhotos: Photo[] = [];
  @state() private samplePhotoId: string | null = null;

  protected override willUpdate(changed: PropertyValues) {
    if (changed.has("defaults") && this.defaults && !changed.get("defaults")) {
      this.draft = structuredClone(this.defaults.defaults ?? {});
    }
    if (changed.has("frames") && !this.sampleFrameId && this.frames.length) {
      this.pickFrame(this.frames.find((f) => f.photo_count)?.entry_id ?? this.frames[0].entry_id);
    }
  }

  private async pickFrame(entryId: string) {
    this.sampleFrameId = entryId;
    this.samplePhotos = await fetchPhotos(this.hass, entryId);
    this.samplePhotoId = this.samplePhotos[0]?.photo_id ?? null;
    this.schedulePreview(0);
  }

  private get dirty() {
    return JSON.stringify(this.draft) !== JSON.stringify(this.defaults?.defaults ?? {});
  }

  protected previewRequest() {
    const frame = this.frames.find((f) => f.entry_id === this.sampleFrameId);
    if (!frame || !this.samplePhotoId) return null;
    return { frame, photoId: this.samplePhotoId, settings: { global_defaults: this.draft } };
  }

  private async save() {
    this.error = null;
    try {
      const res = await saveDefaults(this.hass, this.draft);
      this.defaults = { ...this.defaults, defaults: res.defaults };
      this.status = "saved";
    } catch (err) {
      this.error = errorMessage(err);
    }
  }

  protected override render() {
    if (!this.defaults) return nothing;
    const l = localizer(this.hass);
    const sample = html`<div class="sample">
      <select
        aria-label=${l("frames")}
        @change=${(e: Event) => this.pickFrame((e.target as HTMLSelectElement).value)}
      >
        ${this.frames.map(
          (f) => html`<option value=${f.entry_id} ?selected=${f.entry_id === this.sampleFrameId}>${f.title}</option>`,
        )}
      </select>
      <select
        aria-label=${l("sample_photo")}
        @change=${(e: Event) => {
          this.samplePhotoId = (e.target as HTMLSelectElement).value;
          this.schedulePreview(0);
        }}
      >
        ${this.samplePhotos.map(
          (p) => html`<option value=${p.photo_id} ?selected=${p.photo_id === this.samplePhotoId}>${p.name}</option>`,
        )}
      </select>
    </div>`;
    return html`
      <div class="form card">
        <h3>${l("global_defaults")}</h3>
        <span class="muted">${l("global_defaults_hint")}</span>
        <pp-render-settings
          with-palette
          .hass=${this.hass}
          .value=${this.draft}
          .inherited=${this.defaults.builtin}
          @value-changed=${(e: CustomEvent<{ value: FrameSettings }>) => {
            this.draft = e.detail.value;
            this.status = null;
            this.schedulePreview();
          }}
        ></pp-render-settings>
        ${this.error ? html`<span class="error">${l("error", { error: this.error })}</span>` : nothing}
        <div class="actions">
          ${this.dirty ? html`<span class="muted">${l("unsaved")}</span>` : nothing}
          ${!this.dirty && this.status === "saved" ? html`<span class="chip ok">${l("saved")}</span>` : nothing}
          <button
            class="btn"
            ?disabled=${!this.dirty}
            @click=${() => {
              this.draft = structuredClone(this.defaults.defaults ?? {});
              this.schedulePreview(0);
            }}
          >
            ${l("cancel")}
          </button>
          <button class="btn primary" ?disabled=${!this.dirty} @click=${this.save}>${l("save")}</button>
        </div>
      </div>
      ${this.renderPreviewPane(this.frames.length ? sample : nothing)}
    `;
  }

  static override styles = [
    ...PreviewingView.styles,
    css`
      .sample {
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
      }
      .sample select {
        flex: 1;
        min-width: 0;
      }
    `,
  ];
}

declare global {
  interface HTMLElementTagNameMap {
    "pp-frame-settings": FrameSettingsView;
    "pp-global-settings": GlobalSettingsView;
  }
}
