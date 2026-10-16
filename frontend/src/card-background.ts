import { mdiCheck, mdiImage } from "@mdi/js";
import { LitElement, css, html, nothing } from "lit";
import { customElement, property } from "lit/decorators.js";
import { localizer } from "./localize";
import { icon, sharedStyles } from "./styles";
import type { CardBackground, HomeAssistant, LibraryItem, PaletteColor } from "./types";

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
}

/** Picks a card background: a panel colour or a photo of the library. Fires `value-changed`. */
@customElement("pp-card-background")
export class CardBackgroundPicker extends LitElement {
  @property({ attribute: false }) hass!: HomeAssistant;
  /** The library; only photos (not cards) can be a background. */
  @property({ attribute: false }) photos: LibraryItem[] = [];
  @property({ attribute: false }) value: CardBackgroundValue = { background: "white", background_photo_id: null };

  private get candidates(): LibraryItem[] {
    return this.photos.filter((p) => p.kind !== "card");
  }

  private set(value: CardBackgroundValue) {
    this.dispatchEvent(new CustomEvent("value-changed", { detail: { value } }));
  }

  private pickPhoto() {
    const id = this.value.background_photo_id ?? this.candidates[0]?.photo_id ?? null;
    if (id) this.set({ background: "photo", background_photo_id: id });
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
            @click=${() => this.set({ background: c, background_photo_id: null })}
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
      </div>
      ${!candidates.length ? html`<span class="muted hint">${l("no_photo_for_background")}</span>` : nothing}
      ${background === "photo"
        ? html`<label class="field">
              ${l("background_photo")}
              <select
                class="bg-photo"
                @change=${(e: Event) =>
                  this.set({ background: "photo", background_photo_id: (e.target as HTMLSelectElement).value })}
              >
                ${candidates.map(
                  (p) => html`<option value=${p.photo_id} ?selected=${p.photo_id === background_photo_id}>${p.name}</option>`,
                )}
              </select>
            </label>
            <span class="muted hint">${l("background_photo_hint")}</span>`
        : nothing}
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
      .swatch.photo {
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
    `,
  ];
}

declare global {
  interface HTMLElementTagNameMap {
    "pp-card-background": CardBackgroundPicker;
  }
}
