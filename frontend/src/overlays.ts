import { mdiClose, mdiContentCopy, mdiDelete, mdiDrag, mdiPlus, mdiTextBoxOutline } from "@mdi/js";
import { LitElement, css, html, nothing, type PropertyValues } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import {
  copyOverlays,
  copyPhotoOverlays,
  deleteOverlay,
  errorMessage,
  fetchOverlays,
  previewOverlays,
  reorderOverlays,
  saveOverlay,
} from "./api";
import { ensureCodeEditor } from "./ha-editor";
import { localizer } from "./localize";
import { PreviewQueue } from "./preview-queue";
import { icon, sharedStyles } from "./styles";
import type { Anchor, Frame, HomeAssistant, Overlay, PaletteColor, Photo } from "./types";

const ANCHORS: Anchor[] = [
  "top_left",
  "top_center",
  "top_right",
  "center_left",
  "center",
  "center_right",
  "bottom_left",
  "bottom_center",
  "bottom_right",
];
const COLORS: PaletteColor[] = ["black", "white", "red", "green", "blue", "yellow"];
const SWATCH: Record<PaletteColor, string> = {
  black: "#1f2226",
  white: "#f2f2f2",
  red: "#ea4843",
  green: "#067406",
  blue: "#416ce1",
  yellow: "#dbd529",
};
const DRAFT_ID = "draft";
const PREVIEW_DELAY = 500;
const DRAG_TYPE = "application/x-paperlessoffline-overlay";

const blank = (name: string, template: string, anchor: Anchor = "bottom_right"): Overlay => ({
  name,
  template,
  enabled: true,
  show_if: null,
  anchor,
  margin: 0.03,
  width: null,
  align: "left",
  size: "m",
  text_color: "black",
  backing: "box",
  backing_color: "white",
  redraw: "change",
});

/** Starter overlays for the "Add" menu. */
function presets(l: ReturnType<typeof localizer>, hass: HomeAssistant): Record<string, Overlay> {
  const weather = Object.keys(hass.states ?? {}).find((id) => id.startsWith("weather.")) ?? "weather.home";
  const sensor =
    Object.keys(hass.states ?? {}).find(
      (id) => id.startsWith("sensor.") && hass.states[id].attributes.device_class === "temperature",
    ) ?? "sensor.outdoor_temperature";
  return {
    sensor: blank(l("preset_sensor"), `:mdi:thermometer: **{{ states('${sensor}') }} °C**`, "top_right"),
    weather: blank(
      l("preset_weather"),
      `{{ weather_icon(states('${weather}')) }} {{ state_attr('${weather}', 'temperature') }} °`,
      "top_right",
    ),
    date: { ...blank(l("preset_date"), "{{ date_local(now(), 'long') }}", "bottom_center"), backing: "halo", text_color: "white" },
    blank: blank(l("preset_blank"), ""),
  };
}

/** The global photo overlays of a frame, or (with `photo`) one photo's overlays: add, edit, toggle, reorder, copy. */
@customElement("pp-overlays")
export class OverlayList extends LitElement {
  @property({ attribute: false }) hass!: HomeAssistant;
  @property({ attribute: false }) frame!: Frame;
  @property({ attribute: false }) frames: Frame[] = [];
  @property({ attribute: false }) photos: Photo[] = [];
  /** Set: this list is the photo's own overlays (shown in the photo editor). */
  @property({ attribute: false }) photo?: Photo;

  @state() private overlays: Overlay[] = [];
  @state() private editing: Overlay | null = null;
  @state() private menuOpen = false;
  @state() private error: string | null = null;
  @state() private notice: string | null = null;
  @state() private dragId: string | null = null;
  @state() private copyOpen = false;
  @state() private copyTargets = new Set<string>();
  @state() private copyReplace = false;
  @state() private copyFilter = "";
  @state() private copyListOpen = false;

  protected override willUpdate(changed: PropertyValues) {
    // Reload when the frame changes or the panel refreshed it (e.g. after a wake).
    if (changed.has("frame") || changed.has("photo")) this.load();
  }

  private async load() {
    try {
      this.overlays = await fetchOverlays(this.hass, this.frame.entry_id, this.photo?.photo_id);
    } catch (err) {
      this.error = errorMessage(err);
    }
  }

  private add(preset: Overlay) {
    this.menuOpen = false;
    this.editing = { ...preset };
  }

  private async toggle(ev: Event, overlay: Overlay) {
    ev.stopPropagation();
    try {
      await saveOverlay(this.hass, this.frame.entry_id, { ...overlay, enabled: !overlay.enabled }, this.photo?.photo_id);
      await this.load();
    } catch (err) {
      this.error = errorMessage(err);
    }
  }

  private async drop(ev: DragEvent, target: Overlay) {
    const id = ev.dataTransfer?.getData(DRAG_TYPE);
    this.dragId = null;
    if (!id || id === target.overlay_id) return;
    ev.preventDefault();
    const order = this.overlays.map((o) => o.overlay_id!).filter((o) => o !== id);
    order.splice(order.indexOf(target.overlay_id!), 0, id);
    const byId = new Map(this.overlays.map((o) => [o.overlay_id, o]));
    this.overlays = order.map((o) => byId.get(o)!);
    try {
      await reorderOverlays(this.hass, this.frame.entry_id, order, this.photo?.photo_id);
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
      const res = await copyOverlays(this.hass, this.frame.entry_id, target.entry_id);
      this.notice = localizer(this.hass)("copied_overlays", { n: res.copied, frame: target.title });
    } catch (err) {
      this.error = errorMessage(err);
    }
  }

  private toggleTarget(id: string, on: boolean) {
    const next = new Set(this.copyTargets);
    if (on) next.add(id);
    else next.delete(id);
    this.copyTargets = next;
  }

  private async copyToPhotos() {
    if (!this.photo || !this.copyTargets.size) return;
    try {
      const res = await copyPhotoOverlays(
        this.hass,
        this.frame.entry_id,
        this.photo.photo_id,
        [...this.copyTargets],
        this.copyReplace,
      );
      this.notice = localizer(this.hass)("copied_photo_overlays", { n: res.copied, photos: this.copyTargets.size });
      this.copyOpen = false;
      this.copyTargets = new Set();
      this.copyReplace = false;
      this.copyFilter = "";
      this.copyListOpen = false;
      this.dispatchEvent(new CustomEvent("overlays-copied", { bubbles: true, composed: true }));
    } catch (err) {
      this.error = errorMessage(err);
    }
  }

  private renderCopyToPhotos(l: ReturnType<typeof localizer>) {
    const others = this.photos.filter((p) => p.photo_id !== this.photo?.photo_id);
    const query = this.copyFilter.trim().toLowerCase();
    const matches = others.filter((p) => p.name.toLowerCase().includes(query));
    const chosen = others.filter((p) => this.copyTargets.has(p.photo_id));
    return html`<div class="copy-photos">
      <strong>${l("copy_to_photos")}</strong>
      <div
        class="combo"
        @focusout=${(e: FocusEvent) => {
          if (!(e.currentTarget as HTMLElement).contains(e.relatedTarget as Node | null)) this.copyListOpen = false;
        }}
      >
        <div class="combo-field" @click=${(e: Event) => (e.currentTarget as HTMLElement).querySelector("input")?.focus()}>
          ${chosen.map(
            (p) => html`<span class="chip sel">
              ${p.name}
              <button
                class="icon-btn"
                title=${l("delete")}
                @click=${(e: Event) => {
                  e.stopPropagation();
                  this.toggleTarget(p.photo_id, false);
                }}
              >
                ${icon(mdiClose)}
              </button>
            </span>`,
          )}
          <input
            type="text"
            role="combobox"
            aria-expanded=${this.copyListOpen}
            aria-controls="copy-options"
            placeholder=${l("copy_search")}
            .value=${this.copyFilter}
            @focus=${() => (this.copyListOpen = true)}
            @input=${(e: Event) => {
              this.copyFilter = (e.target as HTMLInputElement).value;
              this.copyListOpen = true;
            }}
            @keydown=${(e: KeyboardEvent) => {
              if (e.key === "Escape") this.copyListOpen = false;
              else if (e.key === "Enter" && matches.length) {
                e.preventDefault();
                const first = matches[0]!;
                this.toggleTarget(first.photo_id, !this.copyTargets.has(first.photo_id));
              } else if (e.key === "Backspace" && !this.copyFilter && chosen.length) {
                this.toggleTarget(chosen[chosen.length - 1]!.photo_id, false);
              }
            }}
          />
        </div>
        ${this.copyListOpen
          ? html`<ul class="options" id="copy-options" role="listbox" aria-multiselectable="true">
              ${matches.length
                ? matches.map((p) => {
                    const on = this.copyTargets.has(p.photo_id);
                    return html`<li
                      class="option"
                      role="option"
                      aria-selected=${on}
                      @mousedown=${(e: Event) => e.preventDefault()}
                      @click=${() => this.toggleTarget(p.photo_id, !on)}
                    >
                      <input type="checkbox" tabindex="-1" .checked=${on} />
                      ${p.name}
                    </li>`;
                  })
                : html`<li class="none">${l("copy_no_match")}</li>`}
            </ul>`
          : nothing}
      </div>
      <label>
        <input
          type="checkbox"
          class="replace"
          .checked=${this.copyReplace}
          @change=${(e: Event) => (this.copyReplace = (e.target as HTMLInputElement).checked)}
        />
        ${l("copy_replace")}
      </label>
      <div class="actions">
        <button class="btn" @click=${() => (this.copyOpen = false)}>${l("cancel")}</button>
        <button class="btn primary do-copy" ?disabled=${!this.copyTargets.size} @click=${this.copyToPhotos}>
          ${l("copy")}
        </button>
      </div>
    </div>`;
  }

  protected override render() {
    const l = localizer(this.hass);
    // Frame overlays copy to other frames; a photo's overlays copy to other photos of this frame.
    const others = this.photo ? [] : this.frames.filter((f) => f.entry_id !== this.frame.entry_id);
    const otherPhotos = this.photo ? this.photos.filter((p) => p.photo_id !== this.photo!.photo_id) : [];
    const p = presets(l, this.hass);
    return html`<div class="card wrap">
      <div class="head">
        <div>
          <h3>${l(this.photo ? "photo_overlays" : "global_overlays")}</h3>
          <span class="muted">${l(this.photo ? "photo_overlays_hint" : "global_overlays_hint")}</span>
        </div>
        <div class="actions">
          ${others.length && this.overlays.length
            ? html`<label class="copy">
                ${icon(mdiContentCopy)}
                <select @change=${this.copyTo} aria-label=${l("copy_overlays_to")}>
                  <option value="">${l("copy_overlays_to")}</option>
                  ${others.map((f) => html`<option value=${f.entry_id}>${f.title}</option>`)}
                </select>
              </label>`
            : nothing}
          ${otherPhotos.length && this.overlays.length
            ? html`<button class="btn open-copy" @click=${() => (this.copyOpen = !this.copyOpen)}>
                ${icon(mdiContentCopy)} ${l("copy_to_photos")}
              </button>`
            : nothing}
          <div class="menu-wrap">
            <button class="btn primary" @click=${() => (this.menuOpen = !this.menuOpen)}>
              ${icon(mdiPlus)} ${l("add_overlay")}
            </button>
            ${this.menuOpen
              ? html`<div class="menu card">
                  ${(["sensor", "weather", "date", "blank"] as const).map(
                    (key) => html`<button @click=${() => this.add(p[key])}>${l(`preset_${key}`)}</button>`,
                  )}
                </div>`
              : nothing}
          </div>
        </div>
      </div>
      ${this.copyOpen ? this.renderCopyToPhotos(l) : nothing}
      ${this.notice ? html`<p class="chip ok">${this.notice}</p>` : nothing}
      ${this.error ? html`<p class="error">${l("error", { error: this.error })}</p>` : nothing}
      ${this.overlays.length
        ? html`<ul>
            ${this.overlays.map(
              (o) => html`<li
                class=${this.dragId === o.overlay_id ? "dragging" : ""}
                draggable="true"
                @dragstart=${(e: DragEvent) => {
                  this.dragId = o.overlay_id!;
                  e.dataTransfer?.setData(DRAG_TYPE, o.overlay_id!);
                }}
                @dragover=${(e: DragEvent) => e.dataTransfer?.types.includes(DRAG_TYPE) && e.preventDefault()}
                @drop=${(e: DragEvent) => this.drop(e, o)}
                @dragend=${() => (this.dragId = null)}
                @click=${() => (this.editing = { ...o })}
              >
                <span class="grip">${icon(mdiDrag)}</span>
                <span class="body">
                  <span class="name">${icon(mdiTextBoxOutline)} ${o.name}</span>
                  <code>${o.template.split("\n")[0]}</code>
                  ${o.last_error
                    ? html`<span class="error small">${l("overlay_error", { error: o.last_error })}</span>`
                    : o.last_text
                      ? html`<span class="muted small">${l("shows_now", { text: o.last_text })}</span>`
                      : nothing}
                </span>
                <label class="toggle" @click=${(e: Event) => e.stopPropagation()}>
                  <input type="checkbox" .checked=${o.enabled} @change=${(e: Event) => this.toggle(e, o)} />
                  ${l("enabled")}
                </label>
              </li>`,
            )}
          </ul>`
        : html`<p class="muted empty">${l(this.photo ? "no_photo_overlays" : "no_overlays")}</p>`}
      ${this.editing
        ? html`<pp-overlay-editor
            .hass=${this.hass}
            .frame=${this.frame}
            .photos=${this.photos}
            .photo=${this.photo}
            .overlays=${this.overlays}
            .overlay=${this.editing}
            @closed=${(e: Event) => {
              // Don't let it reach a photo editor this list may sit in.
              e.stopPropagation();
              this.editing = null;
              this.load();
            }}
          ></pp-overlay-editor>`
        : nothing}
    </div>`;
  }

  static override styles = [
    sharedStyles,
    css`
      .wrap {
        padding: 16px;
        display: grid;
        gap: 12px;
      }
      .head {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        gap: 12px;
        flex-wrap: wrap;
      }
      h3 {
        margin: 0 0 4px;
        font-size: 16px;
        font-weight: 500;
      }
      .actions {
        display: flex;
        gap: 8px;
        align-items: center;
      }
      .copy-photos {
        display: grid;
        gap: 8px;
        padding: 12px;
        border: 1px solid var(--pp-border);
        border-radius: 10px;
      }
      .combo {
        position: relative;
      }
      .combo-field {
        display: flex;
        flex-wrap: wrap;
        gap: 4px;
        align-items: center;
        padding: 4px 8px;
        border: 1px solid var(--pp-border);
        border-radius: 8px;
        cursor: text;
      }
      .combo-field input {
        flex: 1;
        min-width: 120px;
        border: none;
        outline: none;
        background: transparent;
        color: inherit;
        font: inherit;
        padding: 4px 0;
      }
      .combo-field:focus-within {
        border-color: var(--pp-accent);
      }
      .chip.sel {
        display: inline-flex;
        align-items: center;
        gap: 2px;
      }
      .chip.sel .icon-btn {
        padding: 0;
        --mdc-icon-size: 14px;
      }
      .options {
        position: absolute;
        left: 0;
        right: 0;
        top: calc(100% + 4px);
        z-index: 3;
        max-height: 220px;
        overflow-y: auto;
        margin: 0;
        padding: 4px;
        list-style: none;
        background: var(--pp-surface);
        border: 1px solid var(--pp-border);
        border-radius: 8px;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.18);
      }
      .options li {
        display: flex;
        gap: 8px;
        align-items: center;
        padding: 6px 8px;
        border: none;
        border-radius: 6px;
        cursor: pointer;
      }
      .options li:hover {
        background: var(--pp-bg);
      }
      .options li.none {
        cursor: default;
        color: var(--pp-muted);
      }
      .copy-photos .actions {
        justify-content: flex-end;
      }
      .copy {
        display: inline-flex;
        align-items: center;
        gap: 4px;
      }
      .menu-wrap {
        position: relative;
      }
      .menu {
        position: absolute;
        right: 0;
        top: calc(100% + 4px);
        z-index: 3;
        display: grid;
        min-width: 180px;
        padding: 4px;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.18);
      }
      .menu button {
        text-align: left;
        padding: 8px 12px;
        border: none;
        background: transparent;
        color: inherit;
        border-radius: 6px;
      }
      .menu button:hover {
        background: color-mix(in srgb, var(--pp-text) 6%, transparent);
      }
      ul {
        list-style: none;
        margin: 0;
        padding: 0;
        display: grid;
        gap: 6px;
      }
      li {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 8px 10px;
        border: 1px solid var(--pp-border);
        border-radius: 10px;
        cursor: pointer;
      }
      li:hover {
        background: color-mix(in srgb, var(--pp-text) 4%, transparent);
      }
      li.dragging {
        opacity: 0.5;
      }
      .grip {
        color: var(--pp-muted);
        cursor: grab;
      }
      .body {
        flex: 1;
        display: grid;
        gap: 2px;
        min-width: 0;
      }
      .name {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        font-weight: 500;
      }
      code {
        font-size: 12px;
        color: var(--pp-muted);
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
      .small {
        font-size: 12px;
      }
      .toggle {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        font-size: 13px;
      }
      .empty {
        margin: 0;
      }
    `,
  ];
}

/** Modal editor for one overlay, with a live preview using current values. */
@customElement("pp-overlay-editor")
export class OverlayEditor extends LitElement {
  @property({ attribute: false }) hass!: HomeAssistant;
  @property({ attribute: false }) frame!: Frame;
  @property({ attribute: false }) photos: Photo[] = [];
  @property({ attribute: false }) overlays: Overlay[] = [];
  @property({ attribute: false }) overlay!: Overlay;
  /** Set: the overlay belongs to this photo, which is also the preview's sample. */
  @property({ attribute: false }) photo?: Photo;

  @state() private draft!: Overlay;
  @state() private preview: string | null = null;
  @state() private aspect = "3 / 5";
  @state() private result: { text: string | null; error: string | null } | null = null;
  @state() private sampleId: string | null = null;
  @state() private rendering = false;
  @state() private error: string | null = null;
  /** Whether HA's code editor is available (else plain text fields). */
  @state() private codeEditor = false;
  private queue = new PreviewQueue(
    (stale) => this.loadPreview(stale),
    (busy) => (this.rendering = busy),
  );

  override connectedCallback() {
    super.connectedCallback();
    window.addEventListener("keydown", this.onKey);
    ensureCodeEditor(this.hass).then((ok) => (this.codeEditor = ok));
  }

  override disconnectedCallback() {
    super.disconnectedCallback();
    window.removeEventListener("keydown", this.onKey);
    this.queue.cancel();
  }

  private onKey = (ev: KeyboardEvent) => {
    if (ev.key !== "Escape") return;
    // In the code editor, Escape belongs to CodeMirror (e.g. closing autocompletion).
    if ((ev.composedPath() as Element[]).some((el) => el.tagName === "HA-CODE-EDITOR")) return;
    this.close();
  };

  protected override willUpdate(changed: PropertyValues) {
    if (changed.has("overlay")) {
      this.draft = { ...this.overlay };
      this.sampleId = this.photo?.photo_id ?? this.photos[0]?.photo_id ?? null;
      this.schedule(0);
    }
  }

  private set<K extends keyof Overlay>(key: K, value: Overlay[K]) {
    this.draft = { ...this.draft, [key]: value };
    this.schedule();
  }

  private schedule(delay = PREVIEW_DELAY) {
    this.queue.schedule(delay);
  }

  private async loadPreview(stale: () => boolean) {
    const editedId = this.draft.overlay_id ?? DRAFT_ID;
    const draft = { ...this.draft, overlay_id: editedId };
    const list = this.overlays.some((o) => o.overlay_id === editedId)
      ? this.overlays.map((o) => (o.overlay_id === editedId ? draft : o))
      : [...this.overlays, draft];
    try {
      const res = await previewOverlays(this.hass, this.frame.entry_id, list, this.sampleId, !!this.photo);
      if (stale()) return;
      this.preview = res.image;
      this.aspect = `${res.width} / ${res.height}`;
      this.result = res.results[editedId] ?? null;
    } catch (err) {
      if (!stale()) this.error = errorMessage(err);
    }
  }

  private async save() {
    try {
      await saveOverlay(this.hass, this.frame.entry_id, this.draft, this.photo?.photo_id);
      this.close();
    } catch (err) {
      this.error = errorMessage(err);
    }
  }

  private async deleteClicked() {
    if (!this.draft.overlay_id) return this.close();
    try {
      await deleteOverlay(this.hass, this.frame.entry_id, this.draft.overlay_id, this.photo?.photo_id);
      this.close();
    } catch (err) {
      this.error = errorMessage(err);
    }
  }

  private close() {
    this.dispatchEvent(new CustomEvent("closed", { bubbles: true, composed: true }));
  }

  private select<K extends keyof Overlay>(key: K, options: string[], label: (o: string) => string) {
    return html`<select
      @change=${(e: Event) => this.set(key, (e.target as HTMLSelectElement).value as Overlay[K])}
    >
      ${options.map((o) => html`<option value=${o} ?selected=${this.draft[key] === o}>${label(o)}</option>`)}
    </select>`;
  }

  protected override render() {
    if (!this.draft) return nothing;
    const l = localizer(this.hass);
    const d = this.draft;
    return html`<div class="scrim" @click=${(e: Event) => e.target === e.currentTarget && this.close()}>
      <div class="dialog card" role="dialog" aria-modal="true" aria-label=${l("edit_overlay")}>
        <header>
          <input
            class="title"
            type="text"
            .value=${d.name}
            aria-label=${l("overlay_name")}
            @input=${(e: Event) => this.set("name", (e.target as HTMLInputElement).value)}
          />
          <button class="icon-btn" title=${l("close")} @click=${this.close}>${icon(mdiClose)}</button>
        </header>
        <div class="body">
          <section class="fields">
            <label class="field">
              ${l("overlay_text")}
              ${this.codeEditor
                ? html`<ha-code-editor
                    class="template"
                    mode="jinja2"
                    dir="ltr"
                    .hass=${this.hass}
                    .value=${d.template}
                    .autocompleteEntities=${true}
                    .autocompleteIcons=${true}
                    .linewrap=${true}
                    @value-changed=${(e: CustomEvent<{ value: string }>) => {
                      e.stopPropagation();
                      this.set("template", e.detail.value);
                    }}
                  ></ha-code-editor>`
                : html`<textarea
                    class="template"
                    rows="5"
                    spellcheck="false"
                    .value=${d.template}
                    @input=${(e: Event) => this.set("template", (e.target as HTMLTextAreaElement).value)}
                  ></textarea>`}
            </label>
            <span class="muted small">${l("overlay_help")}</span>
            ${this.result?.error
              ? html`<span class="error small">${l("overlay_error", { error: this.result.error })}</span>`
              : this.result && this.result.text === null
                ? html`<span class="muted small">${l("overlay_hidden")}</span>`
                : nothing}
            <div class="grid2">
              <div class="field">
                ${l("position")}
                <div class="anchors">
                  ${ANCHORS.map(
                    (a) => html`<button
                      class=${d.anchor === a ? "on" : ""}
                      title=${a}
                      aria-label=${a}
                      @click=${() => this.set("anchor", a)}
                    ></button>`,
                  )}
                </div>
              </div>
              <div class="stack">
                <label class="field">${l("text_size")} ${this.select("size", ["s", "m", "l", "xl"], (o) => l(`size_${o}` as never))}</label>
                <label class="field">${l("alignment")} ${this.select("align", ["left", "center", "right"], (o) => l(`align_${o}` as never))}</label>
              </div>
            </div>
            <div class="field">
              <span class="row">
                ${l("box_width")}
                <label class="check">
                  <input
                    type="checkbox"
                    .checked=${d.width === null}
                    @change=${(e: Event) => this.set("width", (e.target as HTMLInputElement).checked ? null : 50)}
                  />
                  ${l("width_auto")}
                </label>
              </span>
              ${d.width !== null
                ? html`<div class="slider">
                    <input
                      type="range"
                      min="10"
                      max="100"
                      step="5"
                      .value=${String(d.width)}
                      @input=${(e: Event) => this.set("width", Number((e.target as HTMLInputElement).value))}
                    />
                    <span>${d.width} %</span>
                  </div>`
                : nothing}
            </div>
            <div class="grid2">
              <div class="field">
                ${l("text_color")}
                <div class="swatches">
                  ${COLORS.map(
                    (c) => html`<button
                      class=${d.text_color === c ? "on" : ""}
                      style="background:${SWATCH[c]}"
                      title=${l(`color_${c}` as never)}
                      @click=${() => this.set("text_color", c)}
                    ></button>`,
                  )}
                </div>
              </div>
              <label class="field">${l("backing")} ${this.select("backing", ["box", "halo", "none"], (o) => l(`backing_${o}` as never))}</label>
            </div>
            ${d.backing === "box"
              ? html`<div class="field">
                  ${l("box_color")}
                  <div class="swatches">
                    ${COLORS.map(
                      (c) => html`<button
                        class=${d.backing_color === c ? "on" : ""}
                        style="background:${SWATCH[c]}"
                        title=${l(`color_${c}` as never)}
                        @click=${() => this.set("backing_color", c)}
                      ></button>`,
                    )}
                  </div>
                </div>`
              : nothing}
            <label class="field">
              ${l("show_if")}
              ${this.codeEditor
                ? html`<ha-code-editor
                    class="show-if"
                    mode="jinja2"
                    dir="ltr"
                    .hass=${this.hass}
                    .value=${d.show_if ?? ""}
                    .autocompleteEntities=${true}
                    .linewrap=${true}
                    @value-changed=${(e: CustomEvent<{ value: string }>) => {
                      e.stopPropagation();
                      this.set("show_if", e.detail.value || null);
                    }}
                  ></ha-code-editor>`
                : html`<textarea
                    rows="2"
                    spellcheck="false"
                    .value=${d.show_if ?? ""}
                    @input=${(e: Event) => this.set("show_if", (e.target as HTMLTextAreaElement).value || null)}
                  ></textarea>`}
            </label>
            <label class="field">${l("redraw")} ${this.select("redraw", ["change", "photo"], (o) => l(`redraw_${o}` as never))}</label>
            <label class="check">
              <input type="checkbox" .checked=${d.enabled} @change=${(e: Event) => this.set("enabled", (e.target as HTMLInputElement).checked)} />
              ${l("enabled")}
            </label>
          </section>
          <section class="previewcol">
            <div class="row">
              <span class="h">${l("preview")}</span>
              ${this.rendering ? html`<span class="muted small">${l("rendering")}</span>` : nothing}
            </div>
            ${this.photos.length && !this.photo
              ? html`<select
                  aria-label=${l("sample_photo")}
                  @change=${(e: Event) => {
                    this.sampleId = (e.target as HTMLSelectElement).value;
                    this.schedule(0);
                  }}
                >
                  ${this.photos.map((p) => html`<option value=${p.photo_id} ?selected=${p.photo_id === this.sampleId}>${p.name}</option>`)}
                </select>`
              : nothing}
            <div class="preview" style="aspect-ratio:${this.aspect}">
              ${this.preview ? html`<img src=${this.preview} alt=${l("preview")} />` : nothing}
            </div>
            <span class="muted small">${l("preview_hint")}</span>
          </section>
        </div>
        ${this.error ? html`<div class="msg error">${l("error", { error: this.error })}</div>` : nothing}
        <footer>
          <button class="btn danger" @click=${this.deleteClicked}>${icon(mdiDelete)} ${l("delete")}</button>
          <span class="spacer"></span>
          <button class="btn" @click=${this.close}>${l("cancel")}</button>
          <button class="btn primary" @click=${this.save}>${l("save")}</button>
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
      }
      .title {
        flex: 1;
        font-size: 18px;
        font-weight: 500;
        border-color: transparent;
        background: transparent;
      }
      .body {
        display: grid;
        grid-template-columns: minmax(0, 3fr) minmax(260px, 2fr);
        gap: 24px;
        padding: 16px;
        overflow: auto;
      }
      .fields,
      .previewcol,
      .stack {
        display: flex;
        flex-direction: column;
        gap: 12px;
        min-width: 0;
      }
      .row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 8px;
      }
      .h {
        font-weight: 500;
      }
      textarea {
        font: 13px/1.5 ui-monospace, SFMono-Regular, Menlo, monospace;
        color: var(--pp-text);
        background: var(--pp-surface);
        border: 1px solid var(--pp-border);
        border-radius: 8px;
        padding: 8px 10px;
        resize: vertical;
        width: 100%;
      }
      div.field {
        display: grid;
        gap: 6px;
        font-size: 14px;
      }
      .field select {
        width: 100%;
      }
      ha-code-editor {
        display: block;
        border: 1px solid var(--pp-border);
        border-radius: 8px;
        overflow: hidden;
        --code-mirror-max-height: 260px;
      }
      ha-code-editor.template {
        min-height: 110px;
      }
      .small {
        font-size: 12px;
      }
      .btn.small {
        min-height: 28px;
        padding: 0 10px;
        font-size: 13px;
      }
      .grid2 {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 16px;
      }
      .anchors {
        display: grid;
        grid-template-columns: repeat(3, 32px);
        grid-template-rows: repeat(3, 24px);
        gap: 4px;
        padding: 6px;
        width: fit-content;
        border-radius: 8px;
        border: 1px solid var(--pp-border);
        background: var(--pp-bg);
      }
      .anchors button {
        border: 1px solid var(--pp-border);
        border-radius: 4px;
        background: var(--pp-surface);
      }
      .anchors button.on {
        background: var(--pp-accent);
        border-color: var(--pp-accent);
      }
      .swatches {
        display: flex;
        gap: 6px;
        flex-wrap: wrap;
      }
      .swatches button {
        width: 28px;
        height: 28px;
        border-radius: 50%;
        border: 1px solid var(--pp-border);
      }
      .swatches button.on {
        outline: 2px solid var(--pp-accent);
        outline-offset: 2px;
      }
      .check {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        font-size: 14px;
        cursor: pointer;
      }
      .slider {
        display: flex;
        align-items: center;
        gap: 10px;
      }
      .slider input {
        flex: 1;
      }
      .preview {
        flex: none;
        height: min(460px, 55vh);
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
      .msg {
        padding: 0 16px 8px;
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
    "pp-overlays": OverlayList;
    "pp-overlay-editor": OverlayEditor;
  }
}
