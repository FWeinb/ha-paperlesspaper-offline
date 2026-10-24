import {
  mdiCardTextOutline,
  mdiEye,
  mdiEyeOff,
  mdiImageMultiple,
  mdiLayersOff,
  mdiLayersOutline,
  mdiTune,
  mdiUpload,
} from "@mdi/js";
import { LitElement, css, html, nothing } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import { errorMessage, reorderPhotos, updateFrame, updatePhoto, uploadPhotos } from "./api";
import "./card-dialog";
import { localizer } from "./localize";
import "./media-import";
import { icon, sharedStyles } from "./styles";
import type { Frame, HomeAssistant, LibraryItem, Order } from "./types";

const DRAG_TYPE = "application/x-paperlessoffline-photo";

/** A frame's photo grid: upload, import, reorder, toggle rotation, open editor. */
@customElement("pp-library")
export class Library extends LitElement {
  @property({ attribute: false }) hass!: HomeAssistant;
  @property({ attribute: false }) frame!: Frame;
  @property({ attribute: false }) photos: LibraryItem[] = [];

  @state() private dropActive = false;
  @state() private uploading = 0;
  @state() private uploadErrors: { file: string; error: string }[] = [];
  @state() private error: string | null = null;
  @state() private importOpen = false;
  @state() private cardOpen = false;
  @state() private dragId: string | null = null;
  @state() private dragOverId: string | null = null;

  private async upload(files: File[]) {
    const images = files.filter((f) => f.type.startsWith("image/") || /\.(heic|heif)$/i.test(f.name));
    if (!images.length) return;
    this.uploading = images.length;
    this.uploadErrors = [];
    this.error = null;
    try {
      const result = await uploadPhotos(this.hass, this.frame.entry_id, images);
      this.uploadErrors = result.errors;
    } catch (err) {
      this.error = errorMessage(err);
    } finally {
      this.uploading = 0;
    }
  }

  private onFileInput(ev: Event) {
    const input = ev.target as HTMLInputElement;
    this.upload([...(input.files ?? [])]);
    input.value = "";
  }

  private onDragOver(ev: DragEvent) {
    if (ev.dataTransfer?.types.includes("Files")) {
      ev.preventDefault();
      this.dropActive = true;
    }
  }

  private onDrop(ev: DragEvent) {
    if (!ev.dataTransfer?.types.includes("Files")) return;
    ev.preventDefault();
    this.dropActive = false;
    this.upload([...ev.dataTransfer.files]);
  }

  private onTileDragStart(ev: DragEvent, photo: LibraryItem) {
    this.dragId = photo.photo_id;
    ev.dataTransfer?.setData(DRAG_TYPE, photo.photo_id);
    if (ev.dataTransfer) ev.dataTransfer.effectAllowed = "move";
  }

  private onTileDragOver(ev: DragEvent, photo: LibraryItem) {
    if (!this.dragId || !ev.dataTransfer?.types.includes(DRAG_TYPE)) return;
    ev.preventDefault();
    this.dragOverId = photo.photo_id;
  }

  private async onTileDrop(ev: DragEvent, target: LibraryItem) {
    const id = ev.dataTransfer?.getData(DRAG_TYPE);
    this.dragOverId = null;
    this.dragId = null;
    if (!id || id === target.photo_id) return;
    ev.preventDefault();
    ev.stopPropagation();
    const order = this.photos.map((p) => p.photo_id).filter((p) => p !== id);
    order.splice(order.indexOf(target.photo_id), 0, id);
    // Optimistic update; the subscription refresh will confirm.
    const byId = new Map(this.photos.map((p) => [p.photo_id, p]));
    this.photos = order.map((p) => byId.get(p)!);
    try {
      await reorderPhotos(this.hass, this.frame.entry_id, order);
    } catch (err) {
      this.error = errorMessage(err);
    }
  }

  private async toggleEnabled(ev: Event, photo: LibraryItem) {
    ev.stopPropagation();
    try {
      await updatePhoto(this.hass, this.frame.entry_id, photo.photo_id, { enabled: !photo.enabled });
    } catch (err) {
      this.error = errorMessage(err);
    }
  }

  private async setOrder(order: Order) {
    try {
      await updateFrame(this.hass, this.frame.entry_id, { order });
    } catch (err) {
      this.error = errorMessage(err);
    }
  }

  /** A photo's own overlays: how many, and whether any is enabled. Cards are made of them. */
  private renderOverlayBadge(photo: LibraryItem) {
    const count = photo.overlay_count ?? 0;
    if (photo.kind === "card" || !count) return nothing;
    const l = localizer(this.hass);
    const on = photo.overlays_enabled ?? 0;
    return html`<span
      class="chip overlay-badge ${on ? "" : "off"}"
      title=${on ? l("overlays_on", { on, count }) : l("overlays_off", { count })}
    >
      ${icon(on ? mdiLayersOutline : mdiLayersOff)} ${on ? on : count}
    </span>`;
  }

  private edit(photo: LibraryItem) {
    this.dispatchEvent(new CustomEvent("edit-photo", { detail: { photo }, bubbles: true, composed: true }));
  }

  protected override render() {
    const l = localizer(this.hass);
    const showing = this.frame.current.kind === "photo" ? this.frame.current.photo_id : null;
    const upNext = this.frame.up_next.kind === "photo" ? this.frame.up_next.photo_id : null;
    return html`
      <div class="toolbar">
        <label class="btn primary">
          ${icon(mdiUpload)} ${l("upload")}
          <input type="file" accept="image/*,.heic,.heif" multiple hidden @change=${this.onFileInput} />
        </label>
        <button class="btn" @click=${() => (this.importOpen = true)}>${icon(mdiImageMultiple)} ${l("import")}</button>
        <button class="btn add-card" @click=${() => (this.cardOpen = true)}>
          ${icon(mdiCardTextOutline)} ${l("add_card")}
        </button>
        <span class="spacer"></span>
        <label class="order">
          <span class="muted">${l("order")}</span>
          <select @change=${(e: Event) => this.setOrder((e.target as HTMLSelectElement).value as Order)}>
            ${(["sequential", "shuffle"] as Order[]).map(
              (o) => html`<option value=${o} ?selected=${this.frame.order === o}>${l(`order_${o}`)}</option>`,
            )}
          </select>
        </label>
      </div>
      <p class="muted summary">
        ${l("photos_count", { enabled: this.frame.enabled_count, total: this.frame.photo_count })}
        ${this.photos.length > 1 && this.frame.order === "sequential" ? html` · ${l("drag_hint")}` : nothing}
      </p>
      ${this.uploading ? html`<p class="chip">${l("uploading", { n: this.uploading })}</p>` : nothing}
      ${this.uploadErrors.length
        ? html`<div class="error">
            ${l("upload_errors")}
            <ul>
              ${this.uploadErrors.map((e) => html`<li>${e.file}: ${e.error}</li>`)}
            </ul>
          </div>`
        : nothing}
      ${this.error ? html`<p class="error">${l("error", { error: this.error })}</p>` : nothing}
      <div
        class="drop ${this.dropActive ? "active" : ""}"
        @dragover=${this.onDragOver}
        @dragleave=${() => (this.dropActive = false)}
        @drop=${this.onDrop}
      >
        ${this.photos.length
          ? html`<div class="grid">
              ${this.photos.map((photo) => {
                const custom = Object.keys(photo.overrides ?? {}).length > 0;
                const card = photo.kind === "card";
                return html`<div
                  class="tile ${photo.enabled ? "" : "disabled"} ${card ? "is-card" : ""} ${this.dragOverId === photo.photo_id ? "over" : ""}"
                  draggable="true"
                  tabindex="0"
                  @click=${() => this.edit(photo)}
                  @keydown=${(e: KeyboardEvent) => e.key === "Enter" && this.edit(photo)}
                  @dragstart=${(e: DragEvent) => this.onTileDragStart(e, photo)}
                  @dragover=${(e: DragEvent) => this.onTileDragOver(e, photo)}
                  @dragleave=${() => (this.dragOverId = null)}
                  @drop=${(e: DragEvent) => this.onTileDrop(e, photo)}
                  @dragend=${() => ((this.dragId = null), (this.dragOverId = null))}
                >
                  <img src=${photo.thumb_url} alt="" loading="lazy" draggable="false" />
                  <div class="badges">
                    ${photo.photo_id === showing ? html`<span class="chip ok">${l("showing")}</span>` : nothing}
                    ${photo.photo_id === upNext ? html`<span class="chip">${l("up_next")}</span>` : nothing}
                    ${custom ? html`<span class="chip" title=${l("custom")}>${icon(mdiTune)}</span>` : nothing}
                    ${this.renderOverlayBadge(photo)}
                    ${card ? html`<span class="chip card-badge">${l("card_badge")}</span>` : nothing}
                  </div>
                  <div class="caption">
                    <span class="name" title=${photo.name}>${photo.name}</span>
                    <button
                      class="icon-btn small"
                      title=${photo.enabled ? l("in_rotation") : l("not_in_rotation")}
                      @click=${(e: Event) => this.toggleEnabled(e, photo)}
                    >
                      ${icon(photo.enabled ? mdiEye : mdiEyeOff)}
                    </button>
                  </div>
                </div>`;
              })}
            </div>`
          : html`<div class="empty muted">${l("empty_library")}</div>`}
        ${this.dropActive ? html`<div class="drop-hint">${l("drop_here")}</div>` : nothing}
      </div>
      ${this.importOpen
        ? html`<pp-media-import
            .hass=${this.hass}
            .frame=${this.frame}
            @closed=${() => (this.importOpen = false)}
          ></pp-media-import>`
        : nothing}
      ${this.cardOpen
        ? html`<pp-card-dialog
            .hass=${this.hass}
            .frame=${this.frame}
            .photos=${this.photos}
            @closed=${() => (this.cardOpen = false)}
            @card-created=${(e: CustomEvent<{ photo: LibraryItem }>) => {
              this.cardOpen = false;
              this.edit(e.detail.photo);
            }}
          ></pp-card-dialog>`
        : nothing}
    `;
  }

  static override styles = [
    sharedStyles,
    css`
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
      .tile.is-card img {
        object-fit: contain;
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
      .badges .overlay-badge {
        display: inline-flex;
        align-items: center;
        gap: 2px;
      }
      .badges .overlay-badge.off {
        opacity: 0.6;
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
    `,
  ];
}

declare global {
  interface HTMLElementTagNameMap {
    "pp-library": Library;
  }
}
