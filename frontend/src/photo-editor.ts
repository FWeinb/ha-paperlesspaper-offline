import { mdiClose, mdiContentCopy, mdiDelete, mdiImageCheck, mdiRotateLeft, mdiRotateRight } from "@mdi/js";
import { LitElement, css, html, nothing, type PropertyValues } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import { copyPhoto, deletePhoto, errorMessage, renderPreview, showPhoto, updatePhoto } from "./api";
import "./crop-area";
import type { Crop } from "./crop-area";
import { localizer } from "./localize";
import "./render-settings";
import { resolveSettings } from "./render-settings";
import { icon, sharedStyles } from "./styles";
import type { Frame, FrameSettings, HomeAssistant, Photo, PhotoSettings, ResolvedSettings } from "./types";

const PREVIEW_DELAY = 350;
const SHARED_KEYS = ["dither", "serpentine", "fit", "background", "brightness", "contrast", "saturation"] as const;

/** Modal editor for one photo: crop/focal/rotation, render overrides, live preview. */
@customElement("pp-photo-editor")
export class PhotoEditor extends LitElement {
  @property({ attribute: false }) hass!: HomeAssistant;
  @property({ attribute: false }) frame!: Frame;
  @property({ attribute: false }) frames: Frame[] = [];
  @property({ attribute: false }) photo!: Photo;
  /** Resolved frame-level settings the photo inherits from. */
  @property({ attribute: false }) inherited!: ResolvedSettings;

  @state() private draft: PhotoSettings = {};
  @state() private name = "";
  @state() private enabled = true;
  @state() private preview: string | null = null;
  @state() private rendering = false;
  @state() private lockAspect = true;
  @state() private error: string | null = null;
  @state() private notice: string | null = null;
  @state() private busy = false;

  private previewTimer?: number;
  private previewSeq = 0;

  override connectedCallback() {
    super.connectedCallback();
    window.addEventListener("keydown", this.onKey);
  }

  override disconnectedCallback() {
    super.disconnectedCallback();
    window.removeEventListener("keydown", this.onKey);
    window.clearTimeout(this.previewTimer);
  }

  private onKey = (ev: KeyboardEvent) => {
    if (ev.key === "Escape") this.close();
  };

  protected override willUpdate(changed: PropertyValues) {
    if (changed.has("photo") && this.photo) {
      this.draft = structuredClone(this.photo.overrides ?? {});
      this.name = this.photo.name;
      this.enabled = this.photo.enabled;
      this.lockAspect = true;
      this.schedulePreview(0);
    }
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
      JSON.stringify(this.draft) !== JSON.stringify(this.photo.overrides ?? {})
    );
  }

  private setDraft(changes: Partial<PhotoSettings>, remove: (keyof PhotoSettings)[] = []) {
    const next = { ...this.draft, ...changes } as Record<string, unknown>;
    for (const key of remove) delete next[key];
    this.draft = next as PhotoSettings;
    this.schedulePreview();
  }

  private schedulePreview(delay = PREVIEW_DELAY) {
    window.clearTimeout(this.previewTimer);
    this.previewTimer = window.setTimeout(() => this.loadPreview(), delay);
  }

  private async loadPreview() {
    const seq = ++this.previewSeq;
    this.rendering = true;
    try {
      const result = await renderPreview(this.hass, this.frame.entry_id, this.photo.photo_id, {
        overrides: this.draft,
      });
      if (seq === this.previewSeq) this.preview = result.image;
    } catch (err) {
      if (seq === this.previewSeq) this.error = errorMessage(err);
    } finally {
      if (seq === this.previewSeq) this.rendering = false;
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
        overrides: this.draft,
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
    if (!confirm(l("delete_confirm", { name: this.photo.name }))) return;
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

  protected override render() {
    if (!this.photo) return nothing;
    const l = localizer(this.hass);
    const coverFit = this.resolved.fit === "cover";
    const otherFrames = this.frames.filter((f) => f.entry_id !== this.frame.entry_id);
    const shared: FrameSettings = {};
    for (const key of SHARED_KEYS) {
      if (this.draft[key] !== undefined) (shared as Record<string, unknown>)[key] = this.draft[key];
    }
    const previewStyle = `aspect-ratio:${this.frame.canvas.width}/${this.frame.canvas.height}`;
    return html`<div class="scrim" @click=${(e: Event) => e.target === e.currentTarget && this.close()}>
      <div class="dialog card" role="dialog" aria-modal="true" aria-label=${l("edit_photo")}>
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
        <div class="body">
          <section class="visual">
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
          </section>
          <section class="settings">
            <div class="section-title">
              <span>${l("preview")}</span>
              ${this.rendering ? html`<span class="muted">${l("rendering")}</span>` : nothing}
            </div>
            <div class="preview" style=${previewStyle}>
              ${this.preview ? html`<img src=${this.preview} alt=${l("preview")} />` : nothing}
            </div>
            <span class="muted hint">${l("preview_hint")}</span>
            <label class="check rotation">
              <input
                type="checkbox"
                .checked=${this.enabled}
                @change=${(e: Event) => (this.enabled = (e.target as HTMLInputElement).checked)}
              />
              ${l("in_rotation")}
            </label>
            <div class="section-title"><span>${l("rendering_settings")}</span></div>
            <pp-render-settings
              .hass=${this.hass}
              .value=${shared}
              .inherited=${this.inherited}
              @value-changed=${this.onSettings}
            ></pp-render-settings>
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
    `,
  ];
}

declare global {
  interface HTMLElementTagNameMap {
    "pp-photo-editor": PhotoEditor;
  }
}
