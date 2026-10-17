import { mdiClose, mdiContentCopy, mdiDelete, mdiImageCheck, mdiRotateLeft, mdiRotateRight } from "@mdi/js";
import { LitElement, css, html, nothing, type PropertyValues } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import { copyPhoto, deletePhoto, errorMessage, renderPreview, showPhoto, updatePhoto } from "./api";
import "./card-background";
import type { CardBackgroundValue } from "./card-background";
import "./crop-area";
import "./overlays";
import type { Crop } from "./crop-area";
import { localizer } from "./localize";
import { PreviewQueue } from "./preview-queue";
import "./render-settings";
import { resolveSettings } from "./render-settings";
import { icon, sharedStyles } from "./styles";
import type { Frame, FrameSettings, HomeAssistant, LibraryItem, PhotoSettings, ResolvedSettings } from "./types";

const PREVIEW_DELAY = 350;
const SHARED_KEYS = ["dither", "serpentine", "fit", "background", "brightness", "contrast", "saturation"] as const;

/**
 * Modal editor for one library item. A photo gets crop/focal/rotation and render
 * overrides; a card (card mode) gets its background instead. Both get overlays
 * and a live preview.
 */
@customElement("pp-photo-editor")
export class PhotoEditor extends LitElement {
  @property({ attribute: false }) hass!: HomeAssistant;
  @property({ attribute: false }) frame!: Frame;
  @property({ attribute: false }) frames: Frame[] = [];
  @property({ attribute: false }) photos: LibraryItem[] = [];
  @property({ attribute: false }) photo!: LibraryItem;
  /** Resolved frame-level settings the photo inherits from. */
  @property({ attribute: false }) inherited!: ResolvedSettings;

  @state() private draft: PhotoSettings = {};
  @state() private name = "";
  @state() private enabled = true;
  @state() private hideOverlays = false;
  @state() private background: CardBackgroundValue = { background: "white", background_photo_id: null };
  @state() private preview: string | null = null;
  @state() private rendering = false;
  @state() private lockAspect = true;
  @state() private error: string | null = null;
  @state() private notice: string | null = null;
  @state() private busy = false;

  private previewQueue = new PreviewQueue(
    (stale) => this.loadPreview(stale),
    (busy) => (this.rendering = busy),
  );

  override connectedCallback() {
    super.connectedCallback();
    window.addEventListener("keydown", this.onKey);
  }

  override disconnectedCallback() {
    super.disconnectedCallback();
    window.removeEventListener("keydown", this.onKey);
    this.previewQueue.cancel();
    this.bodyObserver.disconnect();
  }

  /** Caps the sticky right column at the dialog body's visible height. */
  private bodyObserver = new ResizeObserver(([entry]) =>
    this.style.setProperty("--pp-body-height", `${(entry.target as HTMLElement).clientHeight}px`),
  );

  protected override updated() {
    const body = this.renderRoot.querySelector(".body");
    if (body && body !== this.observedBody) {
      this.bodyObserver.disconnect();
      this.bodyObserver.observe(body);
      this.observedBody = body;
    }
  }

  private observedBody: Element | null = null;

  private onKey = (ev: KeyboardEvent) => {
    if (ev.key === "Escape") this.close();
  };

  protected override willUpdate(changed: PropertyValues) {
    if (changed.has("photo") && this.photo) {
      this.draft = structuredClone(this.photo.overrides ?? {});
      this.name = this.photo.name;
      this.enabled = this.photo.enabled;
      this.hideOverlays = this.photo.hide_frame_overlays ?? false;
      this.background = this.savedBackground;
      this.lockAspect = true;
      this.schedulePreview(0);
    } else if (changed.has("photos") && this.isCard) {
      // A card's preview shows its overlays, which may just have been edited.
      this.schedulePreview(0);
    }
  }

  private get isCard(): boolean {
    return this.photo.kind === "card";
  }

  private get savedBackground(): CardBackgroundValue {
    return {
      background: this.photo.background ?? "white",
      background_photo_id: this.photo.background_photo_id ?? null,
    };
  }

  private get resolved(): ResolvedSettings {
    return resolveSettings(this.inherited, this.draft);
  }

  private get rotation(): number {
    return this.draft.rotation ?? 0;
  }

  private get aspect(): number {
    return this.frame.canvas.width / this.frame.canvas.height;
  }

  private get dirty(): boolean {
    return (
      this.name !== this.photo.name ||
      this.enabled !== this.photo.enabled ||
      this.hideOverlays !== (this.photo.hide_frame_overlays ?? false) ||
      JSON.stringify(this.draft) !== JSON.stringify(this.photo.overrides ?? {}) ||
      (this.isCard && JSON.stringify(this.background) !== JSON.stringify(this.savedBackground))
    );
  }

  private setDraft(changes: Partial<PhotoSettings>, remove: (keyof PhotoSettings)[] = []) {
    const next = { ...this.draft, ...changes } as Record<string, unknown>;
    for (const key of remove) delete next[key];
    this.draft = next as PhotoSettings;
    this.schedulePreview();
  }

  private schedulePreview(delay = PREVIEW_DELAY) {
    this.previewQueue.schedule(delay);
  }

  private async loadPreview(stale: () => boolean) {
    try {
      const result = await renderPreview(
        this.hass,
        this.frame.entry_id,
        this.photo.photo_id,
        this.isCard ? { ...this.background } : { overrides: this.draft },
      );
      if (!stale()) this.preview = result.image;
    } catch (err) {
      if (!stale()) this.error = errorMessage(err);
    }
  }

  private rotate(delta: number) {
    const rotation = (((this.rotation + delta) % 360) + 360) % 360;
    // Crop and focal point are relative to the rotated image, so reset them.
    this.setDraft(rotation ? { rotation: rotation as PhotoSettings["rotation"] } : {}, [
      ...(rotation ? [] : (["rotation"] as const)),
      "crop",
      "focal_x",
      "focal_y",
    ]);
  }

  private onSettings(ev: CustomEvent<{ value: FrameSettings }>) {
    const value = ev.detail.value;
    const next: Record<string, unknown> = { ...this.draft };
    for (const key of SHARED_KEYS) {
      if ((value as Record<string, unknown>)[key] === undefined) delete next[key];
      else next[key] = (value as Record<string, unknown>)[key];
    }
    this.draft = next as PhotoSettings;
    this.schedulePreview();
  }

  private async save() {
    this.busy = true;
    this.error = null;
    try {
      await updatePhoto(this.hass, this.frame.entry_id, this.photo.photo_id, {
        name: this.name.trim() || this.photo.name,
        enabled: this.enabled,
        hide_frame_overlays: this.hideOverlays,
        ...(this.isCard ? this.background : { overrides: this.draft }),
      });
      this.close();
    } catch (err) {
      this.error = errorMessage(err);
    } finally {
      this.busy = false;
    }
  }

  private async deleteClicked() {
    const l = localizer(this.hass);
    const cards = this.photos.filter(
      (p) => p.kind === "card" && p.background === "photo" && p.background_photo_id === this.photo.photo_id,
    ).length;
    const warning = cards === 1 ? l("used_as_background_one") : cards ? l("used_as_background", { n: cards }) : "";
    if (!confirm([l("delete_confirm", { name: this.photo.name }), warning].filter(Boolean).join("\n\n"))) return;
    try {
      await deletePhoto(this.hass, this.frame.entry_id, this.photo.photo_id);
      this.close();
    } catch (err) {
      this.error = errorMessage(err);
    }
  }

  private async showNext() {
    try {
      await showPhoto(this.hass, this.frame.entry_id, this.photo.photo_id);
      this.notice = localizer(this.hass)("pending");
    } catch (err) {
      this.error = errorMessage(err);
    }
  }

  private async copyTo(ev: Event) {
    const select = ev.target as HTMLSelectElement;
    const target = this.frames.find((f) => f.entry_id === select.value);
    select.value = "";
    if (!target) return;
    try {
      await copyPhoto(this.hass, this.frame.entry_id, this.photo.photo_id, target.entry_id);
      this.notice = localizer(this.hass)("copied", { frame: target.title });
    } catch (err) {
      this.error = errorMessage(err);
    }
  }

  private close() {
    this.dispatchEvent(new CustomEvent("closed", { bubbles: true, composed: true }));
  }

  private renderPreview() {
    const l = localizer(this.hass);
    return html`<div class="section-title">
        <span>${l("preview")}</span>
        ${this.rendering ? html`<span class="muted">${l("rendering")}</span>` : nothing}
      </div>
      <div class="preview" style="aspect-ratio:${this.frame.canvas.width}/${this.frame.canvas.height}">
        ${this.preview ? html`<img src=${this.preview} alt=${l("preview")} />` : nothing}
      </div>
      <span class="muted hint">${l("preview_hint")}</span>`;
  }

  /** Card mode: the preview takes the crop area's place; the background is picked beside it. */
  private renderBackground() {
    const l = localizer(this.hass);
    return html`<div class="section-title"><span>${l("card_background")}</span></div>
      <pp-card-background
        .hass=${this.hass}
        .photos=${this.photos}
        .value=${this.background}
        @value-changed=${(e: CustomEvent<{ value: CardBackgroundValue }>) => {
          this.background = e.detail.value;
          this.schedulePreview(0);
        }}
      ></pp-card-background>`;
  }

  private renderCrop() {
    const l = localizer(this.hass);
    const coverFit = this.resolved.fit === "cover";
    const shared: FrameSettings = {};
    for (const key of SHARED_KEYS) {
      if (this.draft[key] !== undefined) (shared as Record<string, unknown>)[key] = this.draft[key];
    }
    return html`<section class="visual">
      <div class="section-title">
        <span>${l("crop")}</span>
        <span class="tools">
          <button class="icon-btn" title=${l("rotate_left")} @click=${() => this.rotate(-90)}>
            ${icon(mdiRotateLeft)}
          </button>
          <button class="icon-btn" title=${l("rotate_right")} @click=${() => this.rotate(90)}>
            ${icon(mdiRotateRight)}
          </button>
        </span>
      </div>
      <pp-crop-area
        .src=${this.photo.display_urls[String(this.rotation)]}
        .crop=${(this.draft.crop as Crop) ?? null}
        .focal=${{ x: this.draft.focal_x ?? 0.5, y: this.draft.focal_y ?? 0.5 }}
        .aspect=${coverFit && this.lockAspect ? this.aspect : null}
        @crop-changed=${(e: CustomEvent<{ crop: Crop }>) => this.setDraft({ crop: e.detail.crop })}
        @focal-changed=${(e: CustomEvent<{ x: number; y: number }>) =>
          this.setDraft({ focal_x: e.detail.x, focal_y: e.detail.y })}
      ></pp-crop-area>
      <div class="crop-tools">
        <span class="muted hint">${l("crop_hint")}</span>
        ${coverFit
          ? html`<label class="check">
              <input
                type="checkbox"
                .checked=${this.lockAspect}
                @change=${(e: Event) => (this.lockAspect = (e.target as HTMLInputElement).checked)}
              />
              ${l("lock_aspect")}
            </label>`
          : nothing}
        <button class="btn" ?disabled=${!this.draft.crop} @click=${() => this.setDraft({}, ["crop"])}>
          ${l("clear_crop")}
        </button>
        <button
          class="btn"
          ?disabled=${this.draft.focal_x === undefined}
          @click=${() => this.setDraft({}, ["focal_x", "focal_y"])}
        >
          ${l("reset_focal")}
        </button>
      </div>
      <div class="render">
        <div class="section-title"><span>${l("rendering_settings")}</span></div>
        <pp-render-settings
          .hass=${this.hass}
          .value=${shared}
          .inherited=${this.inherited}
          @value-changed=${this.onSettings}
        ></pp-render-settings>
      </div>
    </section>`;
  }

  protected override render() {
    if (!this.photo) return nothing;
    const l = localizer(this.hass);
    const otherFrames = this.frames.filter((f) => f.entry_id !== this.frame.entry_id);
    return html`<div class="scrim" @click=${(e: Event) => e.target === e.currentTarget && this.close()}>
      <div class="dialog card" role="dialog" aria-modal="true" aria-label=${l(this.isCard ? "edit_card" : "edit_photo")}>
        <header>
          <input
            class="title"
            type="text"
            .value=${this.name}
            aria-label=${l("name")}
            @input=${(e: Event) => (this.name = (e.target as HTMLInputElement).value)}
          />
          <button class="icon-btn" title=${l("close")} @click=${this.close}>${icon(mdiClose)}</button>
        </header>
        <div class="body ${this.isCard ? "" : "photo-mode"}">
          ${this.isCard ? html`<section class="visual card-preview">${this.renderPreview()}</section>` : this.renderCrop()}
          <section class="settings">
            ${this.isCard
              ? this.renderBackground()
              : html`<div class="preview-block">${this.renderPreview()}</div>`}
            <label class="check rotation">
              <input
                type="checkbox"
                .checked=${this.enabled}
                @change=${(e: Event) => (this.enabled = (e.target as HTMLInputElement).checked)}
              />
              ${l("in_rotation")}
            </label>
            <label class="check">
              <input
                type="checkbox"
                .checked=${this.hideOverlays}
                @change=${(e: Event) => (this.hideOverlays = (e.target as HTMLInputElement).checked)}
              />
              ${l(this.isCard ? "hide_frame_overlays_card" : "hide_frame_overlays")}
            </label>
            <pp-overlays .hass=${this.hass} .frame=${this.frame} .photos=${this.photos.length ? this.photos : [this.photo]} .photo=${this.photo}></pp-overlays>
          </section>
        </div>
        ${this.error ? html`<div class="msg error">${l("error", { error: this.error })}</div>` : nothing}
        ${this.notice ? html`<div class="msg">${this.notice}</div>` : nothing}
        <footer>
          <button class="btn danger" @click=${this.deleteClicked}>${icon(mdiDelete)} ${l("delete")}</button>
          <button class="btn" @click=${this.showNext}>${icon(mdiImageCheck)} ${l("show_next")}</button>
          ${otherFrames.length
            ? html`<label class="copy">
                ${icon(mdiContentCopy)}
                <select @change=${this.copyTo} aria-label=${l("copy_to")}>
                  <option value="">${l("copy_to")}</option>
                  ${otherFrames.map((f) => html`<option value=${f.entry_id}>${f.title}</option>`)}
                </select>
              </label>`
            : nothing}
          <span class="spacer"></span>
          ${this.dirty ? html`<span class="muted">${l("unsaved")}</span>` : nothing}
          <button class="btn" @click=${this.close}>${l("cancel")}</button>
          <button class="btn primary" ?disabled=${this.busy || !this.dirty} @click=${this.save}>
            ${l("save")}
          </button>
        </footer>
      </div>
    </div>`;
  }

  static override styles = [
    sharedStyles,
    css`
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
        height: min(440px, 55vh);
        max-width: 100%;
        margin: 0 auto;
        background: #d6d6d6;
        border-radius: 6px;
        overflow: hidden;
        display: grid;
        place-items: center;
        box-shadow: inset 0 0 0 1px var(--pp-border);
      }
      .preview-block {
        display: flex;
        flex-direction: column;
        gap: 10px;
      }
      /* Photo mode: the right column stays in view while the crop and rendering settings
         scroll, and scrolls on its own when it is taller than the dialog body. */
      .photo-mode .settings {
        position: sticky;
        top: 0;
        align-self: start;
        max-height: calc(var(--pp-body-height, 100vh) - 32px);
        overflow-y: auto;
      }
      .render {
        display: flex;
        flex-direction: column;
        gap: 10px;
        margin-top: 8px;
      }
      .card-preview .preview {
        height: min(560px, 65vh);
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
        .body.photo-mode {
          gap: 10px;
        }
        /* One column: crop, preview, rendering settings, then the rest. */
        .photo-mode .visual,
        .photo-mode .settings {
          display: contents;
        }
        .photo-mode .preview-block {
          order: 1;
        }
        .photo-mode .render {
          order: 2;
        }
        .photo-mode .settings > :not(.preview-block) {
          order: 3;
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
    `,
  ];
}

declare global {
  interface HTMLElementTagNameMap {
    "pp-photo-editor": PhotoEditor;
  }
}
