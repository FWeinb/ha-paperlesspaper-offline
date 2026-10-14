import type {
  Defaults,
  Frame,
  FrameSettings,
  HomeAssistant,
  MediaItem,
  Mounting,
  Order,
  Photo,
  PhotoSettings,
} from "./types";

const D = "paperlessoffline";

export const fetchFrames = (hass: HomeAssistant) =>
  hass.callWS<{ frames: Frame[] }>({ type: `${D}/frames` }).then((r) => r.frames);

export const fetchPhotos = (hass: HomeAssistant, entryId: string) =>
  hass.callWS<{ photos: Photo[] }>({ type: `${D}/photos`, entry_id: entryId }).then((r) => r.photos);

export const subscribeChanges = (hass: HomeAssistant, cb: (entryId: string | null) => void) =>
  hass.connection.subscribeMessage<{ entry_id: string | null }>((m) => cb(m.entry_id), {
    type: `${D}/subscribe`,
  });

export const updatePhoto = (
  hass: HomeAssistant,
  entryId: string,
  photoId: string,
  changes: { name?: string; enabled?: boolean; overrides?: PhotoSettings },
) => hass.callWS<Photo>({ type: `${D}/photo/update`, entry_id: entryId, photo_id: photoId, ...changes });

export const deletePhoto = (hass: HomeAssistant, entryId: string, photoId: string) =>
  hass.callWS({ type: `${D}/photo/delete`, entry_id: entryId, photo_id: photoId });

export const reorderPhotos = (hass: HomeAssistant, entryId: string, order: string[]) =>
  hass.callWS({ type: `${D}/photo/reorder`, entry_id: entryId, order });

export const copyPhoto = (hass: HomeAssistant, entryId: string, photoId: string, target: string) =>
  hass.callWS<Photo>({
    type: `${D}/photo/copy`,
    entry_id: entryId,
    photo_id: photoId,
    target_entry_id: target,
  });

export const showPhoto = (hass: HomeAssistant, entryId: string, photoId: string) =>
  hass.callWS({ type: `${D}/photo/show`, entry_id: entryId, photo_id: photoId });

export const skipPhoto = (hass: HomeAssistant, entryId: string) =>
  hass.callWS({ type: `${D}/frame/skip`, entry_id: entryId });

export const updateFrame = (
  hass: HomeAssistant,
  entryId: string,
  changes: { order?: Order; mounting?: Mounting; interval?: number; render_defaults?: FrameSettings },
) => hass.callWS<Frame>({ type: `${D}/frame/update`, entry_id: entryId, ...changes });

export const importMedia = (hass: HomeAssistant, entryId: string, mediaContentId: string) =>
  hass.callWS<Photo>({ type: `${D}/import`, entry_id: entryId, media_content_id: mediaContentId });

export const renderPreview = (
  hass: HomeAssistant,
  entryId: string,
  photoId: string,
  settings: {
    overrides?: PhotoSettings;
    frame_defaults?: FrameSettings;
    global_defaults?: FrameSettings;
  },
) =>
  hass.callWS<{ image: string; width: number; height: number }>({
    type: `${D}/preview`,
    entry_id: entryId,
    photo_id: photoId,
    ...settings,
  });

export const fetchDefaults = (hass: HomeAssistant) => hass.callWS<Defaults>({ type: `${D}/defaults` });

export const saveDefaults = (hass: HomeAssistant, defaults: FrameSettings) =>
  hass.callWS<{ defaults: FrameSettings }>({ type: `${D}/defaults/set`, defaults });

export const browseMedia = (hass: HomeAssistant, mediaContentId?: string) =>
  hass.callWS<MediaItem>({
    type: "media_source/browse_media",
    ...(mediaContentId ? { media_content_id: mediaContentId } : {}),
  });

export interface UploadResult {
  added: { photo_id: string; name: string }[];
  errors: { file: string; error: string }[];
}

export async function uploadPhotos(
  hass: HomeAssistant,
  entryId: string,
  files: File[],
): Promise<UploadResult> {
  const form = new FormData();
  for (const file of files) form.append("file", file, file.name);
  const resp = await hass.fetchWithAuth(`/api/${D}/upload/${entryId}`, {
    method: "POST",
    body: form,
  });
  if (!resp.ok) throw new Error(`Upload failed (${resp.status})`);
  return resp.json();
}

/** Extract a readable message from a websocket error. */
export const errorMessage = (err: unknown): string =>
  (err as { message?: string })?.message ?? String(err);
