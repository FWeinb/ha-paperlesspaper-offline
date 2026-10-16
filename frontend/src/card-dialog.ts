import { mdiClose } from "@mdi/js";
import { LitElement, css, html, nothing } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import { addCard, errorMessage } from "./api";
import "./card-background";
import type { CardBackgroundValue } from "./card-background";
import { localizer } from "./localize";
import { icon, sharedStyles } from "./styles";
import type { CardPreset, Frame, HomeAssistant, LibraryItem } from "./types";

const PRESETS: CardPreset[] = ["info", "notice", "blank"];

/** "Add card": preset, background and name. Fires `card-created` with the new card, or `closed`. */
@customElement("pp-card-dialog")
export class CardDialog extends LitElement {
  @property({ attribute: false }) hass!: HomeAssistant;
  @property({ attribute: false }) frame!: Frame;
  @property({ attribute: false }) photos: LibraryItem[] = [];

  @state() private preset: CardPreset = "info";
  @state() private background: CardBackgroundValue = { background: "white", background_photo_id: null };
  @state() private name = "";
  @state() private busy = false;
  @state() private error: string | null = null;

  override connectedCallback() {
    super.connectedCallback();
    window.addEventListener("keydown", this.onKey);
  }

  override disconnectedCallback() {
    super.disconnectedCallback();
    window.removeEventListener("keydown", this.onKey);
  }

  private onKey = (ev: KeyboardEvent) => {
    if (ev.key === "Escape") this.close();
  };

  private close() {
    this.dispatchEvent(new CustomEvent("closed", { bubbles: true, composed: true }));
  }

  private async create() {
    this.busy = true;
    this.error = null;
    try {
      const card = await addCard(this.hass, this.frame.entry_id, {
        name: this.name.trim() || undefined,
        preset: this.preset,
        ...this.background,
      });
      this.dispatchEvent(new CustomEvent("card-created", { detail: { photo: card }, bubbles: true, composed: true }));
    } catch (err) {
      this.error = errorMessage(err);
    } finally {
      this.busy = false;
    }
  }

  protected override render() {
    const l = localizer(this.hass);
    return html`<div class="scrim" @click=${(e: Event) => e.target === e.currentTarget && this.close()}>
      <div class="dialog card" role="dialog" aria-modal="true" aria-label=${l("new_card")}>
        <header>
          <h2>${l("new_card")}</h2>
          <button class="icon-btn" title=${l("close")} @click=${this.close}>${icon(mdiClose)}</button>
        </header>
        <div class="body">
          <fieldset class="presets">
            <legend>${l("card_preset")}</legend>
            ${PRESETS.map(
              (p) => html`<label class="check">
                <input
                  type="radio"
                  name="preset"
                  value=${p}
                  .checked=${this.preset === p}
                  @change=${() => (this.preset = p)}
                />
                ${l(`card_preset_${p}`)}
              </label>`,
            )}
          </fieldset>
          <div>
            <div class="label">${l("card_background")}</div>
            <pp-card-background
              .hass=${this.hass}
              .photos=${this.photos}
              .value=${this.background}
              @value-changed=${(e: CustomEvent<{ value: CardBackgroundValue }>) => (this.background = e.detail.value)}
            ></pp-card-background>
          </div>
          <label class="field">
            ${l("name")}
            <input
              type="text"
              class="card-name"
              .value=${this.name}
              placeholder=${this.preset === "blank" ? l("card_badge") : l(`card_preset_${this.preset}`).split(":")[0]}
              @input=${(e: Event) => (this.name = (e.target as HTMLInputElement).value)}
              @keydown=${(e: KeyboardEvent) => e.key === "Enter" && this.create()}
            />
          </label>
          ${this.error ? html`<p class="error">${l("error", { error: this.error })}</p>` : nothing}
        </div>
        <footer>
          <span class="spacer"></span>
          <button class="btn" @click=${this.close}>${l("cancel")}</button>
          <button class="btn primary create" ?disabled=${this.busy} @click=${this.create}>${l("create")}</button>
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
        width: min(480px, 100%);
        max-height: calc(100vh - 32px);
        display: flex;
        flex-direction: column;
        overflow: auto;
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
      header h2 {
        flex: 1;
        margin: 0;
        font-size: 18px;
        font-weight: 500;
      }
      footer {
        border-top: 1px solid var(--pp-border);
      }
      .body {
        display: flex;
        flex-direction: column;
        gap: 16px;
        padding: 16px;
      }
      .presets {
        border: none;
        margin: 0;
        padding: 0;
        display: flex;
        flex-direction: column;
        gap: 8px;
      }
      legend,
      .label {
        font-weight: 500;
        margin-bottom: 8px;
        padding: 0;
      }
      .check {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        cursor: pointer;
      }
      .spacer {
        flex: 1;
      }
    `,
  ];
}

declare global {
  interface HTMLElementTagNameMap {
    "pp-card-dialog": CardDialog;
  }
}
