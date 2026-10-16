/** Minimal slice of Home Assistant's frontend `hass` object that we use. */
export interface HomeAssistant {
  language: string;
  states: Record<string, { state: string; attributes: Record<string, any>; last_changed: string }>;
  entities: Record<
    string,
    { entity_id: string; device_id?: string; platform?: string; translation_key?: string }
  >;
  devices: Record<string, { id: string; name?: string; name_by_user?: string }>;
  callWS<T>(msg: Record<string, unknown>): Promise<T>;
  callService(domain: string, service: string, data?: Record<string, unknown>): Promise<unknown>;
  fetchWithAuth(path: string, init?: RequestInit): Promise<Response>;
  connection: {
    subscribeMessage<T>(
      callback: (msg: T) => void,
      msg: Record<string, unknown>,
    ): Promise<() => Promise<void>>;
  };
  user?: { is_admin: boolean };
  themes?: { darkMode?: boolean };
}

export type Dither =
  | "floyd_steinberg"
  | "atkinson"
  | "jarvis_judice_ninke"
  | "sierra2"
  | "bayer"
  | "none";
export type Fit = "cover" | "contain" | "stretch";
export type Palette = "perceived" | "pure";
export type Background = "white" | "black";
export type Mounting = "landscape" | "portrait" | "landscape_flipped" | "portrait_flipped";
export type Order = "sequential" | "shuffle";

/** Settings that can be set at global, frame and photo level. */
export interface SharedSettings {
  dither?: Dither;
  serpentine?: boolean;
  fit?: Fit;
  background?: Background;
  brightness?: number;
  contrast?: number;
  saturation?: number;
}
export interface FrameSettings extends SharedSettings {
  palette?: Palette;
}
export interface PhotoSettings extends SharedSettings {
  rotation?: 0 | 90 | 180 | 270;
  focal_x?: number;
  focal_y?: number;
  crop?: [number, number, number, number];
}
export type ResolvedSettings = Required<FrameSettings>;

export interface Frame {
  entry_id: string;
  title: string;
  client_id: string;
  device_id: string | null;
  panel: { model: string; width: number; height: number };
  canvas: { width: number; height: number };
  mounting: Mounting;
  order: Order;
  interval: number;
  render_defaults: FrameSettings;
  last_seen: string | null;
  last_wake: string | null;
  wake_count: number;
  pending: string[];
  current: { kind: string | null; photo_id: string | null; name: string | null };
  up_next: { kind: string; photo_id: string | null; name: string | null };
  override: { name: string; wakes_remaining: number | null } | null;
  photo_count: number;
  enabled_count: number;
  ble: { voltage?: number; usb?: boolean; charging?: boolean; rssi?: number; read_at: string | null };
  overdue: boolean;
  needs_reprovision: boolean;
}

export type CardBackground = PaletteColor | "photo";
export type CardPreset = "blank" | "info" | "notice";

/** A library item: a photo, or a card (text on a background, no file). */
export interface LibraryItem {
  photo_id: string;
  kind: "photo" | "card";
  name: string;
  enabled: boolean;
  added: string;
  overrides: PhotoSettings;
  hide_frame_overlays: boolean;
  overlay_count?: number;
  /** Cards only. */
  background?: CardBackground;
  background_photo_id?: string | null;
  thumb_url: string;
  display_urls: Record<string, string>;
}

export interface Defaults {
  defaults: FrameSettings;
  builtin: ResolvedSettings;
}

export interface MediaItem {
  title: string;
  media_content_id: string;
  media_class: string;
  media_content_type: string;
  can_expand: boolean;
  can_play: boolean;
  thumbnail: string | null;
  children?: MediaItem[];
}

export type Anchor =
  | "top_left"
  | "top_center"
  | "top_right"
  | "center_left"
  | "center"
  | "center_right"
  | "bottom_left"
  | "bottom_center"
  | "bottom_right";
export type PaletteColor = "black" | "white" | "red" | "green" | "blue" | "yellow";

/** A text box drawn over photos: a global photo overlay (every photo of a frame) or a photo overlay (one photo). */
export interface Overlay {
  overlay_id?: string;
  name: string;
  template: string;
  enabled: boolean;
  show_if: string | null;
  anchor: Anchor;
  margin: number;
  width: number | null;
  align: "left" | "center" | "right";
  size: "s" | "m" | "l" | "xl" | "xxl";
  text_color: PaletteColor;
  backing: "box" | "halo" | "none";
  backing_color: PaletteColor;
  redraw: "change" | "photo";
  last_text?: string | null;
  last_error?: string | null;
}

export interface OverlayPreview {
  image: string;
  width: number;
  height: number;
  results: Record<string, { text: string | null; error: string | null }>;
}
