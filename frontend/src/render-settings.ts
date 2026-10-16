import { LitElement, css, html, nothing } from "lit";
import { customElement, property } from "lit/decorators.js";
import { localizer } from "./localize";
import { sharedStyles } from "./styles";
import type { FrameSettings, HomeAssistant, ResolvedSettings } from "./types";

type Key = keyof FrameSettings;

const OPTIONS: Partial<Record<Key, string[]>> = {
  dither: ["floyd_steinberg", "atkinson", "jarvis_judice_ninke", "sierra2", "bayer", "none"],
  fit: ["cover", "contain", "stretch"],
  background: ["white", "black"],
  palette: ["perceived", "pure"],
};
const SLIDERS: Key[] = ["brightness", "contrast", "saturation"];

/**
 * Editor for one level of the layered render settings. Each field is either
 * inherited ("Default: …", shown from `inherited`) or set explicitly.
 * Fires `value-changed` with the new partial settings object.
 */
@customElement("pp-render-settings")
export class RenderSettingsForm extends LitElement {
  @property({ attribute: false }) hass!: HomeAssistant;
  @property({ attribute: false }) value: FrameSettings = {};
  @property({ attribute: false }) inherited!: ResolvedSettings;
  /** Whether to offer the palette (global and frame level only). */
  @property({ type: Boolean, attribute: "with-palette" }) withPalette = false;

  private get fields(): Key[] {
    const keys: Key[] = [];
    if (this.withPalette) keys.push("palette");
    keys.push("dither", "serpentine", "fit", "background", ...SLIDERS);
    return keys;
  }

  private label(key: Key, value: unknown): string {
    const l = localizer(this.hass);
    if (typeof value === "boolean") return l(value ? "on" : "off");
    if (typeof value === "number") return value.toFixed(2);
    if (OPTIONS[key]) return l(`${key}_${value}` as never);
    return String(value);
  }

  private emit(value: FrameSettings) {
    this.dispatchEvent(new CustomEvent("value-changed", { detail: { value }, bubbles: true, composed: true }));
  }

  private setInherit(key: Key, inherit: boolean) {
    const value = { ...this.value } as Record<string, unknown>;
    if (inherit) delete value[key];
    else value[key] = this.inherited[key];
    this.emit(value as FrameSettings);
  }

  private setField(key: Key, raw: unknown) {
    this.emit({ ...this.value, [key]: raw } as FrameSettings);
  }

  private control(key: Key, current: unknown, disabled: boolean) {
    const l = localizer(this.hass);
    if (OPTIONS[key]) {
      return html`<select
        .value=${String(current)}
        ?disabled=${disabled}
        @change=${(e: Event) => this.setField(key, (e.target as HTMLSelectElement).value)}
      >
        ${OPTIONS[key]!.map(
          (opt) => html`<option value=${opt} ?selected=${opt === current}>${l(`${key}_${opt}` as never)}</option>`,
        )}
      </select>`;
    }
    if (key === "serpentine") {
      return html`<select
        ?disabled=${disabled}
        @change=${(e: Event) => this.setField(key, (e.target as HTMLSelectElement).value === "on")}
      >
        <option value="on" ?selected=${current === true}>${l("on")}</option>
        <option value="off" ?selected=${current !== true}>${l("off")}</option>
      </select>`;
    }
    const num = Number(current);
    return html`<div class="slider">
      <input
        type="range"
        min="0"
        max="2"
        step="0.05"
        .value=${String(num)}
        ?disabled=${disabled}
        @input=${(e: Event) => this.setField(key, Number((e.target as HTMLInputElement).value))}
      />
      <span class="num">${num.toFixed(2)}</span>
    </div>`;
  }

  protected override render() {
    if (!this.inherited) return nothing;
    const l = localizer(this.hass);
    return html`${this.fields.map((key) => {
      const explicit = this.value[key] !== undefined;
      const current = explicit ? this.value[key] : this.inherited[key];
      return html`<div class="row">
        <div class="head">
          <span class="name">${l(key as never)}</span>
          <label class="inherit">
            <input
              type="checkbox"
              .checked=${!explicit}
              @change=${(e: Event) => this.setInherit(key, (e.target as HTMLInputElement).checked)}
            />
            ${l("inherited_value", { value: this.label(key, this.inherited[key]) })}
          </label>
        </div>
        <div class=${explicit ? "ctl" : "ctl inherited"}>${this.control(key, current, !explicit)}</div>
        ${key === "serpentine" ? html`<span class="hint">${l("serpentine_hint")}</span>` : nothing}
      </div>`;
    })}`;
  }

  static override styles = [
    sharedStyles,
    css`
      :host {
        display: grid;
        gap: 14px;
      }
      .row {
        display: grid;
        gap: 6px;
      }
      .head {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 8px;
        flex-wrap: wrap;
      }
      .name {
        font-weight: 500;
      }
      .inherit {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        font-size: 13px;
        color: var(--pp-muted);
        cursor: pointer;
      }
      .ctl select {
        width: 100%;
      }
      .hint {
        font-size: 12px;
        color: var(--pp-muted);
      }
      .ctl.inherited {
        opacity: 0.55;
      }
      .slider {
        display: flex;
        align-items: center;
        gap: 10px;
      }
      .slider input {
        flex: 1;
      }
      .num {
        font-variant-numeric: tabular-nums;
        min-width: 3.2em;
        text-align: right;
      }
    `,
  ];
}

declare global {
  interface HTMLElementTagNameMap {
    "pp-render-settings": RenderSettingsForm;
  }
}

/** Merge layers into fully resolved settings (mirrors settings.resolve in Python). */
export function resolveSettings(
  builtin: ResolvedSettings,
  ...layers: (FrameSettings | undefined)[]
): ResolvedSettings {
  const out = { ...builtin } as Record<string, unknown>;
  for (const layer of layers) {
    for (const [k, v] of Object.entries(layer ?? {})) {
      if (v !== undefined && v !== null && k in builtin) out[k] = v;
    }
  }
  return out as unknown as ResolvedSettings;
}
