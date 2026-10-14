import { LitElement, css, html, nothing } from "lit";
import { customElement, property, query, state } from "lit/decorators.js";

export type Crop = [number, number, number, number];

const MIN_DRAG_PX = 5;
const clamp = (v: number, lo = 0, hi = 1) => Math.min(hi, Math.max(lo, v));

/**
 * Shows an (already rotated) photo and lets the user drag a crop box or click
 * a focal point. Coordinates are fractions of the shown image; the focal point
 * is relative to the crop box, matching how the renderer applies it.
 *
 * Fires `crop-changed` ({crop: Crop | null}) and `focal-changed` ({x, y}).
 */
@customElement("pp-crop-area")
export class CropArea extends LitElement {
  @property() src = "";
  @property({ attribute: false }) crop: Crop | null = null;
  @property({ attribute: false }) focal = { x: 0.5, y: 0.5 };
  /** Target width/height ratio to lock the box to, or null for free cropping. */
  @property({ attribute: false }) aspect: number | null = null;

  @state() private draft: Crop | null = null;
  @query("img") private img!: HTMLImageElement;

  private start: { x: number; y: number; px: number; py: number; mode: "new" | "move"; orig?: Crop } | null =
    null;

  private point(ev: PointerEvent) {
    const r = this.img.getBoundingClientRect();
    return { x: clamp((ev.clientX - r.left) / r.width), y: clamp((ev.clientY - r.top) / r.height), r };
  }

  private inside(box: Crop | null, x: number, y: number) {
    return !!box && x >= box[0] && x <= box[0] + box[2] && y >= box[1] && y <= box[1] + box[3];
  }

  private onDown(ev: PointerEvent) {
    if (ev.button !== 0) return;
    const p = this.point(ev);
    (ev.currentTarget as HTMLElement).setPointerCapture(ev.pointerId);
    const move = this.inside(this.crop, p.x, p.y);
    this.start = { x: p.x, y: p.y, px: ev.clientX, py: ev.clientY, mode: move ? "move" : "new", orig: this.crop ?? undefined };
  }

  private onMove(ev: PointerEvent) {
    if (!this.start) return;
    if (Math.hypot(ev.clientX - this.start.px, ev.clientY - this.start.py) < MIN_DRAG_PX) return;
    const p = this.point(ev);
    if (this.start.mode === "move" && this.start.orig) {
      const [x, y, w, h] = this.start.orig;
      this.draft = [clamp(x + p.x - this.start.x, 0, 1 - w), clamp(y + p.y - this.start.y, 0, 1 - h), w, h];
      return;
    }
    let w = Math.abs(p.x - this.start.x);
    let h = Math.abs(p.y - this.start.y);
    if (this.aspect) {
      // Convert the pixel aspect into fraction space of this image.
      const fracAspect = (this.aspect * p.r.height) / p.r.width;
      if (w / h > fracAspect) w = h * fracAspect;
      else h = w / fracAspect;
    }
    const x0 = p.x < this.start.x ? this.start.x - w : this.start.x;
    const y0 = p.y < this.start.y ? this.start.y - h : this.start.y;
    const x = clamp(x0, 0, 1 - w);
    const y = clamp(y0, 0, 1 - h);
    this.draft = [x, y, Math.min(w, 1 - x), Math.min(h, 1 - y)];
  }

  private onUp(ev: PointerEvent) {
    if (!this.start) return;
    const moved = Math.hypot(ev.clientX - this.start.px, ev.clientY - this.start.py) >= MIN_DRAG_PX;
    if (moved && this.draft && this.draft[2] > 0.02 && this.draft[3] > 0.02) {
      this.fire("crop-changed", { crop: this.draft.map((v) => Math.round(v * 10000) / 10000) as Crop });
    } else if (!moved) {
      const p = this.point(ev);
      const [cx, cy, cw, ch] = this.crop ?? [0, 0, 1, 1];
      this.fire("focal-changed", {
        x: Math.round(clamp((p.x - cx) / cw) * 1000) / 1000,
        y: Math.round(clamp((p.y - cy) / ch) * 1000) / 1000,
      });
    }
    this.start = null;
    this.draft = null;
  }

  private fire(name: string, detail: unknown) {
    this.dispatchEvent(new CustomEvent(name, { detail, bubbles: true, composed: true }));
  }

  protected override render() {
    const box = this.draft ?? this.crop;
    const [cx, cy, cw, ch] = box ?? [0, 0, 1, 1];
    const fx = cx + this.focal.x * cw;
    const fy = cy + this.focal.y * ch;
    return html`<div
      class="wrap"
      @pointerdown=${this.onDown}
      @pointermove=${this.onMove}
      @pointerup=${this.onUp}
      @pointercancel=${() => ((this.start = null), (this.draft = null))}
    >
      <img src=${this.src} draggable="false" alt="" @load=${() => this.requestUpdate()} />
      ${box
        ? html`<div
            class="box"
            style="left:${cx * 100}%;top:${cy * 100}%;width:${cw * 100}%;height:${ch * 100}%"
          ></div>`
        : nothing}
      <div class="focal" style="left:${fx * 100}%;top:${fy * 100}%"></div>
    </div>`;
  }

  static override styles = css`
    :host {
      display: flex;
      justify-content: center;
      user-select: none;
      touch-action: none;
    }
    .wrap {
      position: relative;
      display: inline-block;
      overflow: hidden;
      border-radius: 8px;
      cursor: crosshair;
      line-height: 0;
      background: repeating-conic-gradient(#ccc 0 25%, #eee 0 50%) 0 0 / 16px 16px;
    }
    img {
      display: block;
      max-width: 100%;
      max-height: min(56vh, 560px);
      pointer-events: none;
    }
    .box {
      position: absolute;
      box-shadow: 0 0 0 9999px rgba(0, 0, 0, 0.5);
      outline: 2px solid #fff;
      outline-offset: -1px;
      cursor: move;
    }
    .focal {
      position: absolute;
      width: 18px;
      height: 18px;
      margin: -9px 0 0 -9px;
      border-radius: 50%;
      border: 2px solid #fff;
      box-shadow: 0 0 0 2px rgba(0, 0, 0, 0.6);
      pointer-events: none;
    }
  `;
}

declare global {
  interface HTMLElementTagNameMap {
    "pp-crop-area": CropArea;
  }
}
