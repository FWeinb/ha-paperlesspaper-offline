import { mdiCheck, mdiImage, mdiImageSyncOutline } from "@mdi/js";
import { LitElement, css, html, nothing } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import { ensureCodeEditor } from "./ha-editor";
import { localizer } from "./localize";
import { icon, sharedStyles } from "./styles";
import type { BackgroundFit, CardBackground, HomeAssistant, LibraryItem, PaletteColor } from "./types";

/** Panel colours roughly as they look on the panel. */
const SWATCHES: Record<PaletteColor, string> = {
  white: "#f4f4f4",
  black: "#1f2226",
  red: "#ea4843",
  green: "#067406",
  blue: "#416ce1",
  yellow: "#dbd529",
};

export interface CardBackgroundValue {
  background: CardBackground;
  background_photo_id: string | null;
  /** The picture background's source template ("" unless the background is "image"). */
  background_image: string;
  /** The picture background's fit. */
  background_fit: BackgroundFit;
  /** With fit "contain": space around the picture, in percent of the short side. */
  background_padding: number;
}

/**
 * Picks a card background: a panel colour, a photo of the library, or a picture from a
 * camera or image entity or a URL. Fires `value-changed`.
 */
@customElement("pp-card-background")
export class CardBackgroundPicker extends LitElement {
  @property({ attribute: false }) hass!: HomeAssistant;
  /** The library; only photos (not cards) can be a background. */
  @property({ attribute: false }) photos: LibraryItem[] = [];
  @property({ attribute: false }) value: CardBackgroundValue = {
    background: "white",
    background_photo_id: null,
    background_image: "",
    background_fit: "default",
    background_padding: 0,
  };
  /** Why the picture background couldn't be fetched, if it couldn't. */
  @property({ attribute: false }) error: string | null = null;
  /** Whether HA's code editor is available (else a plain text field). */
  @state() private codeEditor = false;

  override connectedCallback() {
    super.connectedCallback();
    ensureCodeEditor(this.hass).then((ok) => (this.codeEditor = ok));
  }

  private get candidates(): LibraryItem[] {
    return this.photos.filter((p) => p.kind !== "card");
  }

  private set(value: CardBackgroundValue) {
    this.dispatchEvent(new CustomEvent("value-changed", { detail: { value } }));
  }

  private pickPhoto() {
    const id = this.value.background_photo_id ?? this.candidates[0]?.photo_id ?? null;
    if (id) this.set({ ...this.value, background: "photo", background_photo_id: id, background_image: "" });
  }

  private pickImage() {
    const camera =
      Object.keys(this.hass.states ?? {}).find((id) => id.startsWith("camera.") || id.startsWith("image.")) ??
      "camera.garden";
    this.set({
      ...this.value,
      background: "image",
      background_photo_id: null,
      background_image: this.value.background_image || camera,
    });
  }

  private setImage(source: string) {
    this.set({ ...this.value, background: "image", background_photo_id: null, background_image: source });
  }

  private renderImage() {
    const l = localizer(this.hass);
    const source = this.value.background_image;
    return html`<label class="field">
        ${l("background_image")}
        ${this.codeEditor
          ? html`<ha-code-editor
              class="bg-image"
              mode="jinja2"
              dir="ltr"
              .hass=${this.hass}
              .value=${source}
              .autocompleteEntities=${true}
              .linewrap=${true}
              @value-changed=${(e: CustomEvent<{ value: string }>) => {
                e.stopPropagation();
                this.setImage(e.detail.value);
              }}
            ></ha-code-editor>`
          : html`<textarea
              class="bg-image"
              rows="2"
              spellcheck="false"
              .value=${source}
              @input=${(e: Event) => this.setImage((e.target as HTMLTextAreaElement).value)}
            ></textarea>`}
      </label>
      <span class="muted hint">${l("background_image_hint")}</span>
      <label class="field">
        ${l("background_fit")}
        <select
          class="bg-fit"
          @change=${(e: Event) =>
            this.set({ ...this.value, background_fit: (e.target as HTMLSelectElement).value as BackgroundFit })}
        >
          ${(["default", "cover", "contain"] as const).map(
            (fit) =>
              html`<option value=${fit} ?selected=${this.value.background_fit === fit}>
                ${l(fit === "default" ? "background_fit_default" : `fit_${fit}`)}
              </option>`,
          )}
        </select>
      </label>
      ${this.value.background_fit === "contain"
        ? html`<label class="field">
            ${l("background_padding")}
            <div class="slider">
              <input
                class="bg-padding"
                type="range"
                min="0"
                max="25"
                step="1"
                .value=${String(this.value.background_padding)}
                @input=${(e: Event) =>
                  this.set({ ...this.value, background_padding: Number((e.target as HTMLInputElement).value) })}
              />
              <span>${this.value.background_padding} %</span>
            </div>
          </label>`
        : nothing}
      ${this.error ? html`<span class="error hint">${l("background_image_error", { error: this.error })}</span>` : nothing}`;
  }

  protected override render() {
    const l = localizer(this.hass);
    const { background, background_photo_id } = this.value;
    const candidates = this.candidates;
    const chosen = candidates.find((p) => p.photo_id === background_photo_id);
    return html`
      <div class="swatches" role="radiogroup" aria-label=${l("card_background")}>
        ${(Object.keys(SWATCHES) as PaletteColor[]).map(
          (c) => html`<button
            class="swatch ${background === c ? "on" : ""}"
            role="radio"
            aria-checked=${background === c}
            title=${l(`color_${c}`)}
            data-bg=${c}
            style="background:${SWATCHES[c]}"
            @click=${() => this.set({ ...this.value, background: c, background_photo_id: null, background_image: "" })}
          >
            ${background === c ? icon(mdiCheck) : nothing}
          </button>`,
        )}
        <button
          class="swatch photo ${background === "photo" ? "on" : ""}"
          role="radio"
          aria-checked=${background === "photo"}
          title=${l("card_background_photo")}
          data-bg="photo"
          ?disabled=${!candidates.length}
          @click=${this.pickPhoto}
        >
          ${chosen ? html`<img src=${chosen.thumb_url} alt="" />` : icon(mdiImage)}
        </button>
        <button
          class="swatch picture ${background === "image" ? "on" : ""}"
          role="radio"
          aria-checked=${background === "image"}
          title=${l("card_background_image")}
          data-bg="image"
          @click=${this.pickImage}
        >
          ${icon(mdiImageSyncOutline)}
        </button>
      </div>
      ${!candidates.length ? html`<span class="muted hint">${l("no_photo_for_background")}</span>` : nothing}
      ${background === "photo"
        ? html`<label class="field">
              ${l("background_photo")}
              <select
                class="bg-photo"
                @change=${(e: Event) =>
                  this.set({
                    ...this.value,
                    background: "photo",
                    background_photo_id: (e.target as HTMLSelectElement).value,
                    background_image: "",
                  })}
              >
                ${candidates.map(
                  (p) => html`<option value=${p.photo_id} ?selected=${p.photo_id === background_photo_id}>${p.name}</option>`,
                )}
              </select>
            </label>
            <span class="muted hint">${l("background_photo_hint")}</span>`
        : nothing}
      ${background === "image" ? this.renderImage() : nothing}
    `;
  }

  static override styles = [
    sharedStyles,
    css`
      :host {
        display: flex;
        flex-direction: column;
        gap: 8px;
      }
      .swatches {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
      }
      .swatch {
        width: 44px;
        height: 44px;
        padding: 0;
        border-radius: 8px;
        border: 1px solid var(--pp-border);
        cursor: pointer;
        display: grid;
        place-items: center;
        overflow: hidden;
        color: #fff;
      }
      .swatch[data-bg="white"],
      .swatch[data-bg="yellow"] {
        color: #1f2226;
      }
      .swatch.on {
        outline: 3px solid var(--pp-accent);
        outline-offset: 1px;
      }
      .swatch.photo,
      .swatch.picture {
        background: var(--pp-bg);
        color: var(--pp-text);
      }
      .swatch.photo img {
        width: 100%;
        height: 100%;
        object-fit: cover;
      }
      .swatch[disabled] {
        opacity: 0.4;
        cursor: default;
      }
      .hint {
        font-size: 13px;
      }
      .slider {
        display: flex;
        align-items: center;
        gap: 8px;
      }
      .slider input {
        flex: 1;
      }
      .slider span {
        min-width: 3.5em;
        text-align: right;
      }
      textarea.bg-image {
        font-family: var(--code-font-family, monospace);
        font-size: 13px;
      }
    `,
  ];
}

declare global {
  interface HTMLElementTagNameMap {
    "pp-card-background": CardBackgroundPicker;
  }
}
