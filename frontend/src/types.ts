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
}

export interface Photo {
  photo_id: string;
  name: string;
  enabled: boolean;
  added: string;
  overrides: PhotoSettings;
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
