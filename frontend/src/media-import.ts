import { mdiArrowLeft, mdiCheckCircle, mdiClose, mdiFolder, mdiImage } from "@mdi/js";
import { LitElement, css, html, nothing } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import { browseMedia, errorMessage, importMedia } from "./api";
import { localizer } from "./localize";
import { icon, sharedStyles } from "./styles";
import type { Frame, HomeAssistant, MediaItem } from "./types";

const OWN_SOURCE = "media-source://paperlessoffline";

const isImage = (item: MediaItem) =>
  item.media_class === "image" || item.media_content_type?.startsWith("image/");

/** Browse Home Assistant media sources and import images into a frame. */
@customElement("pp-media-import")
export class MediaImport extends LitElement {
  @property({ attribute: false }) hass!: HomeAssistant;
  @property({ attribute: false }) frame!: Frame;

  @state() private item: MediaItem | null = null;
  @state() private stack: string[] = [];
  @state() private selected = new Set<string>();
  @state() private loading = false;
  @state() private importing = false;
  @state() private error: string | null = null;

  override connectedCallback() {
    super.connectedCallback();
    this.open(undefined);
  }

  private async open(id: string | undefined, push = true) {
    this.loading = true;
    this.error = null;
    try {
      const item = await browseMedia(this.hass, id);
      if (push && this.item) this.stack = [...this.stack, this.item.media_content_id];
      this.item = item;
    } catch (err) {
      this.error = errorMessage(err);
    } finally {
      this.loading = false;
    }
  }

  private back() {
    const stack = [...this.stack];
    const previous = stack.pop();
    this.stack = stack;
    this.open(previous || undefined, false);
  }

  private toggle(id: string) {
    const next = new Set(this.selected);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    this.selected = next;
  }

  private async import() {
    this.importing = true;
    this.error = null;
    try {
      for (const id of this.selected) {
        await importMedia(this.hass, this.frame.entry_id, id);
      }
      this.close();
    } catch (err) {
      this.error = errorMessage(err);
    } finally {
      this.importing = false;
    }
  }

  private close() {
    this.dispatchEvent(new CustomEvent("closed", { bubbles: true, composed: true }));
  }

  protected override render() {
    const l = localizer(this.hass);
    const children = (this.item?.children ?? []).filter(
      (c) => !c.media_content_id.startsWith(OWN_SOURCE) && (c.can_expand || isImage(c)),
    );
    return html`<div class="scrim" @click=${(e: Event) => e.target === e.currentTarget && this.close()}>
      <div class="dialog card" role="dialog" aria-modal="true" aria-label=${l("import")}>
        <header>
          ${this.stack.length
            ? html`<button class="icon-btn" title=${l("back")} @click=${this.back}>${icon(mdiArrowLeft)}</button>`
            : nothing}
          <h2>${this.item?.title || l("media_root")}</h2>
          <button class="icon-btn" title=${l("close")} @click=${this.close}>${icon(mdiClose)}</button>
        </header>
        <div class="grid">
          ${this.loading ? html`<p class="muted">${l("loading")}</p>` : nothing}
          ${!this.loading && !children.length ? html`<p class="muted">${l("no_media")}</p>` : nothing}
          ${children.map((child) => {
            const selected = this.selected.has(child.media_content_id);
            const image = !child.can_expand && isImage(child);
            return html`<button
              class="tile ${selected ? "selected" : ""}"
              @click=${() => (image ? this.toggle(child.media_content_id) : this.open(child.media_content_id))}
            >
              <div class="thumb">
                ${child.thumbnail
                  ? html`<img src=${child.thumbnail} alt="" loading="lazy" />`
                  : icon(image ? mdiImage : mdiFolder)}
                ${selected ? html`<span class="tick">${icon(mdiCheckCircle)}</span>` : nothing}
              </div>
              <span class="label">${child.title}</span>
            </button>`;
          })}
        </div>
        ${this.error ? html`<div class="msg error">${l("error", { error: this.error })}</div>` : nothing}
        <footer>
          <span class="spacer"></span>
          <button class="btn" @click=${this.close}>${l("cancel")}</button>
          <button
            class="btn primary"
            ?disabled=${!this.selected.size || this.importing}
            @click=${this.import}
          >
            ${this.importing ? l("importing") : l("import_selected", { n: this.selected.size })}
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
    `,
  ];
}

declare global {
  interface HTMLElementTagNameMap {
    "pp-media-import": MediaImport;
  }
}
