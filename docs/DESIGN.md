# paperlessoffline: Home Assistant integration design

Home Assistant custom integration (domain `paperlessoffline`) for paperlesspaper
e-paper photo frames running the
[offline firmware](https://github.com/paperlesspaper/paperlesspaper-firmware-offline)
(researched at commit `4e4ddf7`, 2026-09-24). Terms are defined in
[GLOSSARY.md](../GLOSSARY.md); the user-facing behaviour is in the
[README](../README.md).

## 1. Firmware facts this design is built on

- **Pull-only device.** The frame deep-sleeps, wakes on a fixed timer
  (`timeout`, default 3600 s), a button press or (optionally) motion, then makes
  an HTTP `GET` for one image URL (`downloadUrl`) and optionally one settings
  JSON (`settingsUrl`), and sleeps again. It has no HTTP server, mDNS, MQTT or
  push channel. HA can only influence what the frame sees on its *next* wake.
- **Identity.** `CLIENT_ID` = `epd7-<mac12>` or `epd13-<mac12>` (lowercase STA
  MAC). The prefix gives the panel size. It is used as the BLE name and shown on
  the frame's screen overlay. HTTP requests carry nothing that identifies the
  frame (`User-Agent: ESP32HTTPClient`).
- **Panels.**
  - 7.3" Spectra 6 ("Paper 7"): 800×480 native buffer.
  - 13.3" Spectra 6 ("Paper L"): 1200×1600 native buffer.
  - Device colour indices: `0` black, `1` blue, `2` green, `3` red, `5` yellow,
    `6` white.
- **Image formats accepted.**
  - JPEG and 24-bit BMP: dithered on the device with Floyd-Steinberg only.
    JPEGs are stretched without keeping the aspect ratio. The 13" on-device
    path looks broken.
  - Pre-dithered top-down 4-bit BMP whose nibbles are device indices. The
    frame reads only `bfOffBits` and then `width/2`-byte rows top-down; the
    header's width, height (and its sign) and colour table are ignored.
  - Raw packed 4bpp, which must start with `0x66 0x66`.
  - We always serve a **pre-dithered 4-bit BMP** (top-down, negative height,
    so ordinary image viewers show it correctly too).
- **One wake, in order:** the settings JSON (if `settingsUrl` is set), then the
  image **twice**, about 0.4 s apart: once by `getRedirect()`, which only
  follows 301s, and once for the real download. 302 redirects are not
  followed.
- **Change detection.** The frame compares the image response's
  `Last-Modified` with the value it stored and skips the redraw when they are
  equal. The image request supports optional HTTP Basic auth and ignores TLS
  certificates. The settings fetch uses plain `http.begin()` without
  credentials, so Basic auth only protects the image endpoint.
- **Settings JSON keys:** `timeout`, `motionWakeup`, `chargerMode`,
  `autoRotation`, `downloadUrl`, `httpAuthUser`, `httpAuthPassword`. The frame
  sends back the exact `Last-Modified` string it was served as
  `If-Modified-Since`, and honours a 304.
- **BLE.** Only available during setup mode: about 30 s after a single button
  press, or for as long as a client is connected. There is no pairing.
  - Writable: WiFi SSID and password, every setting including the URLs, and
    commands such as `SAVE_SETTINGS` and `EXIT_SETUP`.
  - Readable: system info `{"voltage": mV, "usb": bool, "charging": bool}` and
    WiFi info `{"ip", "rssi"}`.
  - WiFi credentials: write the SSID first, then the password. Writing the
    password starts a connection test of up to 10 s; the credentials are
    stored only if it succeeds. The result is reported through the "WiFi
    connected" characteristic (one byte, 0/1).
- **Telemetry over WiFi** exists only in the
  [firmware fork](https://github.com/FWeinb/paperlesspaper-firmware-offline)
  (section 16). Upstream firmware never reports battery or firmware version
  over WiFi.
- **One image is stored on the frame**, so any slideshow has to be driven by
  the server.
- **Firmware build pitfall.** Upstream `src/types.h` hard-codes `#define
  EPD_TYPE_13INCH`, and the upstream CI tries to switch panels by `sed`-ing a
  `SET_DISPLAY` macro that doesn't exist, so the published "epd7" binary is
  likely a 13" build too. For a 7" frame, edit `types.h` (comment out
  `EPD_TYPE_13INCH`, uncomment `EPD_TYPE_7INCH`) and rebuild. Check: the boot
  log must say `UID: epd7-…`, and the 13"-only `[POWER] Supply ON` / `[SD]`
  lines disappear.
- **No licence** in the firmware repo. We reimplement the protocols and the
  dithering ourselves and copy no code.

## 2. Packaging and code layout

- A HACS-installable custom integration: `custom_components/paperlessoffline`.
- HA 2026.x and newer only. HA 2026.10 uses `probatio` in place of voluptuous
  (`import probatio as vol`).
- Configured through the UI only. Built on config entries, `entry.runtime_data`,
  translations (English and German) and diagnostics.
- CI (GitHub Actions): hassfest, HACS validation, ruff, mypy,
  `pytest-homeassistant-custom-component`, and a frontend typecheck and build.
- Sidebar panel and card: Lit + TypeScript + Vite, built into
  `custom_components/paperlessoffline/frontend/` (build output, not committed).
- Releases: publishing a GitHub release builds the frontend, sets the manifest
  version from the tag and attaches `paperlessoffline.zip`, which HACS installs
  (`zip_release`). `manifest.json` on `main` is not bumped.
- **Target hardware**: HA often runs on slow hosts (Raspberry Pi or Celeron
  class, 4 to 8 GB RAM, shared with everything else). Prefer doing less work
  and keeping peak memory low over caching in RAM: no prepared images are kept
  in memory, renders and thumbnails are cached on disk only, and work at wake
  time is kept cheap.

| Module | Contents |
|---|---|
| `frame.py` | `FrameManager`: library, slideshow, wakes, rendering, overlays, one-off slot, housekeeping |
| `store.py` | `GlobalStore`, `FrameStore`, `LibraryItem`, `OverlayDef`, `Override`, `FrameState` |
| `settings.py` | Layered render settings: global default, frame default, photo setting |
| `render/` | `pipeline.py` (decode, fit, enhance, mount), `dither.py`, `palette.py`, `bmp.py`, `overlay.py` (markdown engine), `placeholder.py`, `fonts/` |
| `cache.py`, `housekeeping.py` | On-disk render cache; deleting files no longer needed |
| `slideshow.py`, `schedule.py` | Order and sleep-time logic (pure) |
| `cards.py` | Card backgrounds, presets, overlay copies |
| `exif.py` | Capture date and location from the EXIF header |
| `templates.py`, `overlay_schema.py` | Overlay template evaluation and helpers; overlay validation |
| `views.py` | Frame endpoints (image, settings) and panel endpoints (upload, thumbnails, previews) |
| `websocket.py`, `frontend.py` | Panel API; panel and card registration |
| `services.py`, `services.yaml`, `sources.py` | Actions and the image sources they accept |
| `ble.py`, `urls.py` | Bluetooth sessions; the URLs a frame uses |
| `config_flow.py`, `issues.py`, `repairs.py` | Setup, options, repair issues and fix flows |
| `media_source.py`, `device_trigger.py`, `diagnostics.py` | HA integration points |
| `image.py`, `select.py`, `button.py`, `number.py`, `switch.py`, `sensor.py`, `binary_sensor.py`, `entity.py` | Entities |

`strings.json`, both translation files and `services.yaml` are generated by
`tools/gen_strings.py` and `tools/gen_services_yaml.py`.

## 3. Frames and setup

- **One config entry per frame.** Each entry is one device, identified by its
  `CLIENT_ID` (unique ID), with the model from the panel ("Paper 7" or
  "Paper L") and the BLE MAC among its connections.
- **Primary setup: BLE discovery** through HA's Bluetooth stack (a local
  adapter or ESPHome proxies), matching local name `epd*`.
  1. The user presses the frame's button once.
  2. HA discovers the frame and starts the config flow (deduplicated against
     existing entries).
  3. The flow writes `downloadUrl`, `settingsUrl`, `timeout` and the auth
     settings, then sends `SAVE_SETTINGS` and `EXIT_SETUP`. On failure it
     offers a retry or manual setup.
  4. Optionally, the same flow sets the WiFi SSID and password, so a
     factory-fresh frame can be onboarded entirely from HA.
- **Manual fallback:** the user enters the Client ID shown on the frame
  (validated against `^(epd7|epd13)-[0-9a-f]{12}$`, which also gives the
  panel). HA displays the URLs to paste into the official web UI.
- **Endpoints**, served over plain HTTP:
  - `/api/paperlessoffline/<token>/image.bmp`
  - `/api/paperlessoffline/<token>/settings.json`
- **Endpoint security.**
  - The token is unguessable and per frame. It is also how HA tells frames
    apart; an unknown token gets a 404.
  - HTTP Basic auth on the image is optional (off by default). The settings
    endpoint is protected by the token alone (see section 1).
  - HA's own authentication is not used, because the frame cannot send a
    bearer token.
- **Options:** mounting, quiet hours (start, end, whether to suppress motion),
  the frame's render defaults, Basic auth, the frame address (`url_host`),
  Bluetooth sync on or off, and regenerating the token (which shows the new
  URLs; the frame then needs re-provisioning). Refresh interval, order and the
  device switches are entities.
- **Frame base URL** (`urls.py`): HA's internal URL, with hosts the frame
  can't use (`localhost`, loopback, unspecified or link-local IPs, `*.local`)
  replaced by the machine's LAN IP. ESP32 `HTTPClient` has no mDNS resolver,
  and loopback would point at the frame itself (a dev instance with
  `internal_url: http://127.0.0.1:8124` wrote exactly that to a frame).
  - Request origins with such hosts (e.g. behind a local reverse proxy) are not
    recorded as the frame's provisioned URL.
  - A provisioned URL with such a host counts as "needs new URLs" immediately,
    so the next button press fixes it.
- **Chosen frame address** (option `url_host`, default `auto`): points the
  URLs at HA's own web server at that address.
  - Offered in both setup paths and in the options. The choices are HA's IPv4
    addresses from the network integration (adapters HA uses first, loopback
    and link-local excluded), plus free text.
  - Validated: a plain IP or DNS name, and not unusable for the frame.
  - When an explicit choice differs from the provisioned URL, the frame counts
    as "needs new URLs" immediately; the next button press or the repair flow
    applies it.
- **Ports in frame URLs**: yarl writes the port whenever it isn't the scheme's
  default (80 for http, 443 for https), so configured ports such as 8123 always
  survive.
  - When the integration picks the host itself (a replaced loopback,
    `localhost` or `.local` host) or the user chooses an address, the URL uses
    HA's own HTTP server port and scheme (`hass.config.api`), not the internal
    URL's. Otherwise `http://homeassistant.local` (implicitly port 80) would
    become `http://<ip>`, with nothing listening on port 80.
  - An internal URL with a usable host is kept exactly as configured, so a
    reverse proxy on port 80 keeps working.
- **`downloadUrl` in the settings JSON** reuses the host and port the frame
  used for the settings request, so it can never point the frame somewhere
  unreachable.
- **Provisioned URL and token**: entry data stores the token and base URL the
  frame is known to use. They are set by the config flow and refreshed by
  every successful request (from the request's origin). Entry version 1.2
  added them (migration from 1.1: the current token, base URL unknown).
- **Deleting a frame** deletes its library. The confirmation dialog says so.

## 4. Library

- **Separate library per frame.** Each frame has an ordered list of **library
  items** (`LibraryItem`, `kind` `photo` or `card`), stored in the per-frame
  store under the key `photos`. The public API (`photo_id`, the photo actions,
  the `photo` template variable) keeps the photo name for every item.
- **Photos**: originals are stored untouched under
  `/config/paperlessoffline/<frame>/originals/`; every edit is metadata in the
  store (non-destructive).
- **Cards** have no file (empty `filename` and `sha256`); their content is
  their own overlays list (section 12).
- **Uploads:** JPEG, PNG, WebP and HEIC (via `pillow-heif`), up to 50 MB and
  100 megapixels per file (decoding costs 3 bytes per pixel whatever the file
  size). Library uploads and `show_image` share the validation. Sources:
  upload, a local path (checked against `allowlist_external_dirs`), a URL, a
  media-source ID, or a `camera`/`image` entity.
- **Capture data** is read once when a photo is added (section 13).
- **Copy to another frame** (`copy_photo`): copies the original, its
  settings and its overlays (with new ids), then renders for the target
  frame's panel. A card is copied with its background photo (section 12).
- **Media source**: browse frame, then items; thumbnails are the 320 px
  thumbnail, playing resolves to the dithered preview PNG.

## 5. Rendering

- **Layered settings:** global default, then frame default, then the photo's
  own setting.

  | Setting                                      | Global | Frame | Photo |
  |----------------------------------------------|:------:|:-----:|:-----:|
  | Dithering algorithm                          | ✓      | ✓     | ✓     |
  | Serpentine scanning                          | ✓      | ✓     | ✓     |
  | Fit mode (cover / contain / stretch)         | ✓      | ✓     | ✓     |
  | Background (borders for contain)             | ✓      | ✓     | ✓     |
  | Crop rectangle / focal point                 |        |       | ✓     |
  | Rotation                                     |        |       | ✓     |
  | Brightness / contrast / saturation           | ✓      | ✓     | ✓     |
  | Palette (perceived / pure)                   | ✓      | ✓     |       |
  | Mounting orientation (landscape / portrait / flipped) |  | ✓   |       |

- **Palettes**: *perceived* (default; how the Spectra 6 panel really looks:
  `#1f2226`, `#416ce1`, `#067406`, `#ea4843`, `#dbd529`, `#d6d6d6`) and
  *pure* (the six full colours). Both map to device indices 0/1/2/3/5/6.
- **Dithering algorithms:** Floyd-Steinberg, Atkinson, Jarvis-Judice-Ninke,
  Sierra-2, ordered/Bayer, and none (nearest colour), each with optional
  serpentine scanning. Implemented in numpy (section 14).
- **Pipeline:**
  1. Decode only what the canvas needs (shrink-first, section 14) and apply
     the EXIF orientation.
  2. Apply the photo's rotation.
  3. Fit or crop the image to the mounted canvas.
  4. Apply enhancement (brightness, contrast, saturation).
  5. Dither against the palette's RGB values.
  6. Map the result to device indices.
  7. Rotate it into the panel's native buffer.
  8. Encode as a top-down 4-bit BMP, plus a preview PNG.
- **Mounting directions** (verified on a 7" frame):
  - Held in portrait, the 7" frame shows its native 800×480 buffer rotated 90°
    counter-clockwise: the buffer's top edge on the left, its left edge at the
    bottom.
  - "portrait" on a landscape panel is therefore `rot90(canvas, 3)`, i.e. the
    canvas is rotated clockwise into the buffer. "portrait_flipped" is
    `rot90(canvas, 1)`.
  - The 13" (native portrait) uses the same convention for "landscape",
    assumed by symmetry.
  - Both panels default to portrait.
  - If the frame's own `autoRotation` is on, the frame may add a further 180°
    when it's upside down, so leave that off when using a flipped mounting.
- **Cache.** Renders are cached on disk (BMP and preview PNG) under a key of
  the source, the resolved settings and the canvas, so any settings change
  gives a new key. Renders run in the executor behind a render lock and are
  pre-rendered after each change and wake. Files no longer needed are deleted
  once unused for a while (section 15).
- **`Last-Modified`.** Each frame keeps a monotonic per-frame `Last-Modified`:
  bumped whenever the served content changes, stable otherwise (including
  across restarts), so the frame redraws exactly when the image changed.
- **Crisp output**: text (overlays, the placeholder) is drawn without
  anti-aliasing (`ImageDraw.fontmode = "1"`) and only in the pure palette
  colours, so every pixel maps to a panel colour exactly, with no stray dither
  pixels around letters. Plain card backgrounds are solid fills, never
  dithered.

## 6. Slideshow, wakes and scheduling

- **Wake detection:**
  - A **settings** request always starts a wake; the firmware makes exactly
    one per wake, before the image.
  - An **image** request starts a wake only for frames that haven't fetched
    settings within `2 × last sleep + 300 s`, and only if more than 60 s have
    passed since the previous request. (A plain "more than 60 s since the last
    request" rule failed with short sleeps: with a 20 s sleep, requests come
    about 25 s apart.)
  - The redirect probe and the download of one wake get the same image and
    `Last-Modified`.
- **Advance on each wake.** Order is sequential, or shuffle with no repeats
  until every enabled item has been shown. Items can be enabled or disabled
  in the rotation (the eye toggle), and reordered.
- **Up next.** Because the frame only changes at its next wake, the *Up next*
  select chooses what the frame shows *next*; *Skip* advances it, and
  `show_photo` queues an item. A separate *Current photo* sensor shows what it
  was last served.
- **Dynamic `timeout`:** a base refresh interval plus optional quiet hours. HA
  computes the sleep length each time the frame fetches its settings (DST-safe,
  in HA's time zone).
- **Motion during quiet hours.** `motionWakeup: false` is sent for the length
  of quiet hours. This is a per-frame option, on by default. While it applies,
  the Motion wake-up switch shows the end of quiet hours in its
  `suppressed_until` attribute, and the frame's page in the panel shows it as
  a chip, so the switch and settings JSON don't seem to disagree. HA records the `motionWakeup` it last sent. When quiet hours start
  or end and that value is out of date, "settings" is pending until the frame
  fetches again.
- **One-off slot.** A frame has one override slot, shown instead of the
  rotation for N wakes or until `clear_image`:
  - a **one-off image** (`show_image`): from a URL, media-source ID,
    `camera`/`image` entity or local path, with optional render settings; it
    is stored as `override.<ext>` in the frame directory, not in the library;
  - a **one-off text** (`show_text`): section 12.

  Each replaces the other. Both draw the global photo overlays unless
  `overlays: false`.
- **Empty rotation.** A frame that has never been served anything gets the
  "No photos yet" screen (section 10). Otherwise the frame keeps its last
  image, served with the same `Last-Modified` so it isn't redrawn.
- **Deleting the item on screen** takes effect at the next wake, when the next
  item in the rotation is served.

## 7. Entities, events and repairs (per frame)

| Platform        | Entity                                                         |
|-----------------|----------------------------------------------------------------|
| `image`         | *Showing* and *Up next* previews                               |
| `select`        | *Up next*, *Slideshow order*                                   |
| `button`        | *Skip photo*                                                   |
| `number`        | *Refresh interval*                                             |
| `switch`        | Motion wakeup, auto-rotation, charger mode, telemetry (on by default) |
| `sensor`        | Last seen, current photo, pending changes, photos in rotation, battery voltage, WiFi signal\*, orientation\* |
| `binary_sensor` | In sync, charging, USB power                                   |

\* Disabled by default.

- **Pending changes** lists what the frame hasn't picked up yet: settings, a
  queued photo, a one-off, edited overlays, a renamed frame's placeholder.
  *In sync* is on when nothing is pending.
- **Status entities** (battery voltage, charging, USB power, WiFi signal,
  orientation) come from wake telemetry (section 16) or a Bluetooth read,
  whichever is newer. They are restored from persisted state and carry
  `last_read` and `source` attributes.
- **Event and trigger:** a `paperlessoffline_frame_wake` event (its data
  includes the item served), plus a matching device trigger "Frame woke up".
- **Repairs** (`issues.py`, `repairs.py`):
  - *Overdue* ("Frame hasn't checked in"): no request by `last request + last
    sleep sent (includes quiet hours) + 2 × interval + 5 min`. A never-seen
    frame counts from the entry's creation time. Clears itself on the next
    request.
  - *Reprovision* ("Frame needs new URLs"): needed when the token was
    regenerated, or when HA's current frame URL differs from the provisioned
    one *and* the frame is overdue. Otherwise an overdue frame gets the
    *offline* notice.
  - The fix flow either waits up to 45 s for the frame to advertise and writes
    the URLs (then exits setup), or accepts "I updated it myself".
  - Issues are rechecked every 5 minutes, after requests, BLE syncs and option
    changes, and on core config updates. They're deleted when the entry is
    removed.
- **Diagnostics** redact the token, provisioned token, Basic auth user and
  password, and photo locations; they show file counts and sizes of the
  cache, thumbnails and originals.
- **Out of scope:** firmware OTA.

## 8. Bluetooth

- **`ble.FrameSession`** is one connection per sync (through
  `bleak-retry-connector`). It offers status reads, WiFi setup with a
  connected check, settings writes, `SAVE_SETTINGS` and an optional
  `EXIT_SETUP`. `async_provision` (the config flow) is built on it.
- **Opportunistic sync.** A per-entry `bluetooth.async_register_callback`
  matches the frame's local name (`epd7-…` / `epd13-…`). On each
  advertisement, `FrameManager.async_ble_seen` starts at most one sync per
  120 s. The sync:
  1. reads status;
  2. writes the effective settings if the user's settings changed since the
     frame last fetched them;
  3. writes new URLs too, but only when reprovisioning is needed.

  It never sends `EXIT_SETUP`, so the frame stays usable for the official web
  UI. There's a per-frame option to turn this off.

## 9. Sidebar panel (admin-only) and card

### Panel

- Frame list with status, last seen, in sync, battery and charging, the
  current item and "Up next", *Skip*, and chips for a one-off ("One-off image"
  or "One-off text", with wakes left), "hasn't checked in" and "needs new
  URLs".
- **Library tab**: drag-and-drop upload, import from a media source, drag to
  reorder, the eye toggle, in order or shuffle, *Add card*; cards carry a
  *Card* badge.
- **Photo editor**: crop (locked to the frame's shape by default) and focal
  point, rotation, the photo's render settings, a live dithered preview
  rendered by HA (with the overlays at their current values and the unsaved
  hide switch; re-rendered when the library list changes, so overlay edits
  show up), *Show next*, *Copy to…*, *Delete* (warning when the photo
  is the background of cards), and the *Photo overlays* section with *Copy to
  photos…* and the hide switch. **Card mode** replaces crop, rotation and
  render settings with the card preview and a background picker (section 12).
- **Settings tab**: mounting, refresh interval, the frame's default look with
  a preview, and *Global photo overlays*. **Global defaults** have their own
  view.
- Layered settings are edited with one component (`pp-render-settings`) at all
  three levels. Each field is either "Default: …", showing the inherited value,
  or set explicitly.
- The panel follows the HA theme and language (`localize.ts`, English and
  German, from `hass.language`).
- It uses its own small components and native form controls styled with HA's
  CSS variables, rather than HA's internal `ha-*` elements, which aren't
  guaranteed to be loaded inside a custom panel. The exception is the code
  editor for overlay templates (section 11).
- **One preview request in flight** (`preview-queue.ts`): the photo editor,
  the settings views and the overlay editor send at most one preview at a
  time; changes made meanwhile are coalesced and only the latest draft is sent
  when the running request returns.

### Card

A small Lovelace card (`custom:paperlessoffline-frame-card`) with the current
image (optionally "Up next"), the sync state, *Skip* and, for admins, a link
to the panel. It uses `ha-card`, finds the frame's entities through
`hass.entities` (device id + translation key) and needs only a `device_id`;
its editor comes from `getConfigForm`.

### Backend for the panel

- **Websocket API** (`websocket.py`, every command requires an admin):
  `frames`, `photos`, `subscribe`; `card/add`; `photo/update` (`overrides`
  replaces all of an item's render settings; also the card background
  fields), `photo/delete`, `photo/reorder`, `photo/copy`, `photo/show`;
  `frame/skip`, `frame/update` (order, mounting, interval and render defaults,
  stored in the entry options); `import` (from a media source); `preview` (a
  dithered PNG with *unsaved* photo, frame, global or card background
  settings; not cached); `defaults`, `defaults/set`; `overlays`,
  `overlay/save`, `overlay/delete`, `overlay/reorder`, `overlays/copy`,
  `overlay/preview`.
  - `subscribe` pushes `{entry_id}` whenever a frame changes, and when frames
    are added or removed; the panel then refetches.
  - The frame status includes `override` (`kind` `image` or `text`, `name`,
    `wakes_remaining`).
- **Upload**: `POST /api/paperlessoffline/upload/{entry_id}` (multipart,
  admins only, one or more `file` fields). Each file is validated like
  `add_photo`; per-file errors are reported without failing the batch.
- **Editor images**: the thumbnail view accepts `?size=320|1280&rotation=0..270`
  and caches each variant. Crop coordinates are fractions of the *rotated*
  image, so the editor shows the server-rotated version and crops map 1:1. The
  focal point is relative to the crop box, exactly as the renderer applies it.
  A card's thumbnail is its rendered preview. Image URLs in websocket
  responses are signed (12 h), because `<img>` tags can't send an auth header.
- **Registration** (`frontend.py`): the bundles are served from
  `/paperlessoffline_static/`.
  - The sidebar panel (`paperlessoffline-panel`, admin-only) is registered with
    `panel_custom`.
  - The card is auto-loaded via `frontend.add_extra_js_url`.
  - A content hash of the bundles is used as the `?v=` cache buster.
  - `frontend` and `panel_custom` are `after_dependencies`; the panel is
    skipped when the frontend isn't loaded (e.g. in tests), and without a
    build the integration logs a warning and registers neither.
- **Build**: Vite in library mode, two entry points (panel and card) plus a
  shared Lit chunk.

## 10. "No photos yet" screen

- Shown when a frame has never been served an image and its rotation is
  empty. It is drawn for the six-colour panel:
  - a flat illustration (a framed picture hanging from a nail, with sun and
    hills) that uses all six colours
  - the frame name in bold, a red accent bar, "No photos yet" in red, and a
    hint pointing to the Photo frames panel
  - the frame ID in blue at the bottom
- **Layout**: stacked and centred on portrait and square canvases; the
  illustration sits beside the text on wide landscape canvases. Long names
  and hints wrap, and everything scales with the panel's short side.
- **Language**: the text follows HA's language (English or German).
- **Updating**: the cache key includes the text, and a frame already showing
  the placeholder gets the current version at its next wake (e.g. after a
  rename). A frame that has shown an image keeps it when its rotation becomes
  empty.
- **No overlays** are drawn on it.
- **Frame name**: the screen (like `frame.name` in overlay templates, the
  panel, the media browser and repair notices) uses the frame's display name.
  - That is the device name a user set in HA (Settings → Devices), otherwise
    the device's own name, which follows the config entry title when the entry
    is renamed.
  - A device rename notifies the frame immediately: the "Up next" preview
    refreshes, the panel updates, and "renamed frame" shows as a pending
    change until the next wake serves the new screen.

## 11. Overlays

Text, entity values and icons drawn onto what the frame shows. Values are
evaluated at a wake, so on the wall they are a snapshot of that moment, not
live.

### Kinds

- **Global photo overlays** (code and actions say "frame overlays",
  `FrameStore.overlays`): defined per frame and drawn on every photo, on
  one-off images and texts, and on cards that don't hide them.
- **Photo overlays** (`LibraryItem.overlays`): belong to one photo, e.g. a
  caption. On a card they are the card's content.
- **Applicable overlays** (`FrameManager._applicable_overlays`), in drawing
  order: the item's own enabled overlays first (or a one-off text's text),
  then the global ones on top. The hide switch (`hide_frame_overlays`)
  removes only the global ones; a one-off with `overlays: false` gets none of
  them. The placeholder gets nothing.

### Model

`OverlayDef`: `id`, `name`, `enabled`, `template`, `show_if`, `anchor`,
`margin`, `width`, `align`, `size`, `text_color`, `backing` (`box | halo |
none`), `backing_color`, `redraw` (`change | photo`). Items have
`hide_frame_overlays`.

### Content

- **Home Assistant templates (Jinja)** for all text:
  `Template.async_render(variables, parse_result=False)` in the event loop.
- **Variables**: `frame.name` everywhere; `photo.name`, `photo.date` and
  `photo.location` on library items (section 13). `photo` is `None` on
  one-off images and texts and the placeholder, so `{% if photo %}` works.
- **Helpers**, passed in as functions (integrations can't register filters in
  HA's template engine):
  - `weather_icon(state)`: an HA weather condition to its MDI icon (full
    condition table);
  - `entity_icon(entity_id)`: an icon explicitly set on an entity (device
    class default icons are resolved by the frontend and are not available);
  - `date_local(value, preset)`: dates with month and weekday names in HA's
    language (English or German), presets `short`, `long`, `month_year`,
    `weekday`, `time`. It keeps a datetime's own UTC offset.
  - `weather_icon` and `entity_icon` return inline `:mdi:name:` markup.
- **Markdown subset** (a hand-written parser in `render/overlay.py`):
  - blocks: `#`, `##`, `###` headings, `- ` / `* ` bullet items, blank-line
    paragraphs; a single newline is a line break (not joined as in
    CommonMark), which suits sensor lists;
  - inline: `**bold**`, `*italic*`, colour spans for the six panel colours
    (`{red}…{/red}`), and icons `:mdi:name:`; a backslash escapes a marker;
  - anything else (images, tables, links, code blocks) is rendered literally.
- **Icons**: the full MDI webfont from `@mdi/font` (about 1.3 MB, Apache 2.0,
  every icon usable), plus `mdi-codepoints.json` (13,659 names including
  aliases) generated from `@mdi/svg`. Icons are sized and coloured like the
  surrounding text; unknown names render nothing.
- **Fonts**: Noto Sans Regular, Bold, Italic and Bold Italic (SIL OFL 1.1),
  subset by `tools/build_fonts.py` to Basic Latin, Latin-1 and Latin
  Extended-A, common punctuation, `° ± × ÷ µ ² ³ ‰`, arrows, bullet, currency
  and fractions. (Pillow's built-in font lacks glyphs like `ü`, `ß` and `„`.)
  Noto Sans has no arrows, `≤ ≥ ∞` or shapes like `▲ ●`, so a subset of Noto
  Sans Math is the fallback: `coverage.json` lists each font's codepoints, text
  is split per character into runs of the first font that has the glyph
  (without fontTools at runtime), and a word split across fonts stays together
  when wrapping. No emoji.

### Layout and look

- **Size presets** at a 480 px short side, scaled with the panel: S 18, M 24,
  L 32, XL 44, XXL 72 px. Headings are × 1.6 / 1.35 / 1.15. Line height 1.3.
- **Box**: one of 9 anchors on the upright (mounted) canvas, a margin
  (default 3 % of the short side), width `auto` (shrink to fit, up to the
  canvas minus margins) or a percentage, alignment left / centre / right.
- **Backing**: a box (padding 0.5 em, corner radius 0.3 em) in a palette
  colour (default white with black text), a halo (an outline in a contrasting
  colour, 1 or 2 px by size), or none. Colour spans override the text colour.
- No automatic collision avoidance; the live preview shows overlaps.

### Rendering

1. **Base image**: the item is rendered and cached as usual.
2. **Overlay layer**: each overlay's evaluated markdown is laid out and drawn
   onto an RGB layer prefilled with a sentinel colour (magenta), without
   anti-aliasing, using only the six pure palette colours.
3. **Compositing** (`render/pipeline.py`): the cached base BMP is decoded back
   into canvas palette positions; this round trip is lossless for every
   mounting. Every layer pixel that isn't the sentinel replaces the base
   pixel, and the result is encoded as usual.
4. **Composite cache key** = base key + every overlay's evaluated text + its
   style. The frame's base image is kept in the cache, so a value change only
   costs the cheap composite, and `Last-Modified` changes exactly when the
   result does.

### Evaluation and freshness

- **Once per wake**, in the request handler right after the wake is detected.
  The texts are stored in the frame state, so the redirect probe, the
  download and retries of the same wake get the same image.
- **Redraw policy per overlay**: *every wake where its text changed*
  (`change`, default), or *only when the item changes* (`photo`). The `photo`
  policy reuses stored texts while the same item is shown and the overlay
  definitions are unchanged. The ident stored in `overlay_eval_base` is
  `kind:shown|hash`, where the hash covers the shown item's overlay
  definitions and the global ones (`overlay_defs_hash`). Rounding in
  templates avoids needless panel refreshes.
- **"Show if"** is evaluated at the same time; a falsy or failing condition
  hides the overlay.
- **Errors**: a failing template leaves only that box out, logs a warning per
  overlay and wake, and is shown in the panel. The frame still gets its image.
- **Pending changes**: an edited overlay of the shown item, or a global one,
  is pending ("overlays") until the next wake evaluates it.
- **Previews**: "Up next" and the editor preview evaluate live and are never
  sent to the frame.

### Editing and automation

- **Panel**: one list and editor component for global overlays (Settings tab),
  photo overlays and card text (photo editor): enable toggle, drag to
  reorder, add, copy; the editor has the text and "show if" fields, a 3 × 3
  anchor picker, size, width, alignment, colours, backing and redraw, and a
  live preview with current values and errors next to the field.
  - Unsaved drafts are previewed with the id `draft`, so the returned text or
    error matches the field being edited. `overlay/preview` takes `for_photo`:
    with it the drafts are the item's own overlays and the stored global ones
    are drawn on top (unless the item hides them); without it the drafts are
    global ones drawn over the item's stored overlays.
  - The editor modal's `closed` event is stopped at the list so it does not
    close the photo editor.
- **Code editor** (`frontend/src/ha-editor.ts`): the text and "show if" fields
  use HA's `ha-code-editor` (mode `jinja2`, with entity and icon
  autocompletion). HA loads that element lazily and custom panels can't
  import HA internals, so the panel asks `window.loadCardHelpers()` for the
  built-in Markdown card editor, whose content field is a template selector,
  and renders it once off screen; that registers `ha-code-editor`. If it isn't
  defined within 3 s (a future frontend change, or the mock harness), plain
  text fields are used. Escape inside the editor is left to CodeMirror.
- **Actions**: `add_overlay`, `update_overlay`, `remove_overlay`,
  `move_overlay` and `list_overlays` take an optional `photo_id`; without it
  they act on the global list. `copy_overlays` copies the global overlays to
  another frame, or with `photo_id` and `to_photo_ids` a photo's overlays to
  other items of the same frame; `replace` replaces instead of adding. Copies
  get new ids; a source listed as a target is skipped, and all ids are checked
  before anything changes.

## 12. Text cards and one-off text

### Cards

- **Model**: a library item with `kind: "card"`, `background` and
  `background_photo_id`. Their defaults make older stores load as photos.
  Cards have no render settings of their own.
- **Background**: `white`, `black`, a panel colour, or `photo` with
  `background_photo_id`.
- **Rendering branches on `kind` in one place**, `FrameManager._base_render`:
  - a plain background is `render_fill`, cached as `fill:<colour>`, with no
    dithering or enhancement, so text on it stays crisp;
  - a photo background returns that photo's own cache key and producer (its
    settings, without its overlays), so card and photo share one cache entry;
  - a missing background photo falls back to white; deleting a photo used as
    a background turns those cards white.
- **Other file-assuming paths** check `is_card`: thumbnails, housekeeping, the
  EXIF read, copying and deleting.
- **Frame overlays** are hidden on cards by default (`hide_frame_overlays`
  defaults to `true` for cards), with the usual switch.
- **Variables**: `photo.name` is the card's name; `photo.date` and
  `photo.location` are `None`, also with a photo background.
- **Thumbnail**: the card's rendered preview (background plus overlays,
  evaluated live like "Up next"), the same PNG as its preview URL. Housekeeping
  evicts it like any preview.
- **Rotation**: a new card is enabled and goes to the end, like a new photo.
  Cards work everywhere photos do: shuffle, the eye toggle, "Up next", *Skip*,
  `show_photo`, the media browser and `list_photos` (with `kind`).
- **Presets** (`cards.py`), written in HA's language when the card is created:
  - *Blank*: no overlays.
  - *Info*: a top centre L heading `# {{ frame.name }}`, and a centred M
    overlay with `{{ date_local(now(), 'long') }}` plus an example line.
  - *Notice*: one centred XXL overlay "Notice", backing `none`.
  - Notice text is white on black, blue, red and green and black otherwise
    (`text_color_on`).
- **Actions**:
  - `add_card` (`name`, `preset`, `background`, optional
    `background_photo_id`) returns the card.
  - `update_photo` `background` keeps its render meaning on photos (the
    border colour for "fit with borders", white or black only) and is the card
    background on cards. Other colours and `background_photo_id` are refused
    for photos (`not_a_card`), render settings for cards
    (`card_has_no_render_settings`).
  - `remove_photo`, `move_photo`, `show_photo` and `copy_photo` take cards as
    they are. Card text is edited with the overlay actions plus `photo_id`.
  - `copy_photo` of a card with a photo background also copies the background
    photo (added disabled), or reuses one with the same `sha256` in the target
    frame.
- **Output**: `list_photos`, the panel's list and diagnostics include
  `background` and `background_photo_id` only for cards.
- **Panel**: "Add card" opens a dialog (preset, background, name); the card
  then opens in the photo editor in card mode, which shows the preview where
  the crop area is and the background picker (colour or library photo)
  beside it.

### One-off text (`show_text`)

- **Fields**: `text` (template with markdown), optional `name`, `background`
  (white, black or a panel colour), `size` (default `xxl`), `anchor` and
  `align` (default `center`), `wakes`, `overlays` (default `true`).
- **Stored** as `Override.text` (template, background, size, anchor, align;
  older stores load as `None`). It has an empty `filename`, and its `sha256`
  hashes the payload, so the "same display" checks and the up next preview key
  work unchanged.
- **Rendering**: `FrameManager._override_base` branches on it like
  `_base_render` does for cards; the base is the same `fill:<colour>` entry.
  The text is an overlay built on the fly (`_text_overlay`, id `show_text`,
  redraw `change`, backing `none`, colour from `text_color_on`), re-evaluated
  every wake and placed first by `_applicable_overlays`; global overlays go on
  top unless `overlays` is `false`.
- **One slot**: setting a text deletes the previous one-off image's file right
  away; `show_image` replaces a text the same way, and `clear_image` clears
  either.
- **Name**: `name`, otherwise the text's first line without `#` marks (at
  most 40 characters), or "Text".
- The template is not checked when the action is called; like any overlay, an
  error leaves the text out at the wake and is logged.

## 13. Photo variables

- **Read once, at add time** (`exif.py`, `read_capture`): Pillow's
  `getexif()` reads only the header, no pixels. Wakes never read EXIF.
- **Stored** on the library item: `date` (ISO text with its UTC offset, from
  `DateTimeOriginal`), `location` (a dict from the GPS block) and `exif_read`.
  Photos stored without them are filled in once at setup, off the event loop
  (`_async_read_missing_exif`).
- **Time zone**: `OffsetTimeOriginal` when present, otherwise HA's local time
  zone. With `date_local` keeping the offset, a photo shows the clock time of
  the camera.
- **In templates**: `photo.date` is an aware `datetime`; `photo.location` is an
  object with `latitude`, `longitude` and `altitude` (each possibly missing)
  that renders as `48.1372, 11.5756` and works with HA's `distance()`. Raw
  coordinates only; no reverse geocoding.
- **No data** gives `None`. `list_photos` returns the coordinates; there is no
  setting to turn GPS reading off.

## 14. Render speed

- **Shrink-first decode** (`render/pipeline.py`, `fit_plan` and `load_region`):
  the crop and the cover/contain box around the focal point are worked out
  first, in upright coordinates, then mapped back through the photo's rotation
  and EXIF orientation to the stored pixels.
  - JPEGs are decoded at 1/2, 1/4 or 1/8 scale (`Image.draft`, DCT scaling),
    then the box (plus the pixels Lanczos reads around it) is cut out and
    shrunk by pixel averaging (`Image.reduce`). Both stop while the box is
    still at least twice the output size (`SHRINK_MARGIN`), so the final
    Lanczos resize sees enough pixels and the result matches the full decode
    (tests compare both paths: mean difference under 1 of 255 per channel).
  - EXIF orientation and the photo's rotation become lossless transposes,
    applied after shrinking, so they touch only the small image.
  - Enhancement and dithering run at canvas size.
  - Thumbnails (320 and 1280 px) use the same decode, targeting the thumb size.
  - `RENDER_VERSION` is part of the cache key, so a pipeline change redoes
    cached renders once.
- **Error diffusion** (`render/dither.py`): wavefronts along anti-diagonals
  (`t = x + 3y`). A wavefront uses only plain slices: its pixels are `w - 3`
  apart in the flat image, and the error waiting for each pixel lives in a
  ring buffer indexed by (wavefront, row). Every kernel tap is one contiguous
  slice a few wavefronts ahead, and the buffer is 9 wavefronts (87 KB), so it
  stays in cache. The nearest colour is one matrix product. The output is
  identical to a raster loop (tests compare random, gradient and tiny images,
  both palettes).
  - Why: on a Celeron N3450 (2 MB cache) dithering was about 85% of a render,
    limited by numpy calls per wavefront and by cache misses on a scattered
    4.6 MB error buffer (Sierra-2 2.07 s, serpentine 5.80 s, decode and fit
    0.04 s). On a Mac the slice version takes Sierra-2 from 0.185 s to
    0.036 s and Floyd-Steinberg from 0.131 s to 0.030 s.
  - Serpentine can't use wavefronts (a reversed row can only start once the
    row above has finished), so it stays a pixel loop, about 6x slower than
    the plain scan, and is the slowest step (seconds on a Pi).
- **Not done on purpose**: no prepared image in memory or on disk; stored
  originals stay untouched.
- **Measured** (M-series Mac, 24 MP JPEG with EXIF rotation, 800x480 canvas,
  wall time and peak memory above the imported module, full decode compared
  with shrink-first):

  | Render                                  | Full decode    | Shrink-first   |
  |-----------------------------------------|----------------|----------------|
  | Floyd-Steinberg                         | 0.32 s, 232 MB | 0.22 s, 63 MB  |
  | Floyd-Steinberg, serpentine             | 0.64 s, 304 MB | 0.55 s, 135 MB |
  | Bayer                                   | 0.22 s, 265 MB | 0.12 s, 100 MB |
  | 30 % crop, rotated (no shrink possible) | 0.26 s, 230 MB | 0.23 s, 131 MB |
  | 1280 px thumbnail, rotated              | 0.15 s, 230 MB | 0.11 s, 89 MB  |

  A cropped photo whose box is less than twice the canvas still needs the full
  decode; then only the transposes and copies are saved.

## 15. Cache and file housekeeping

- **Last use is the mtime.** `RenderCache` touches a file on every hit
  (`has`) and read; thumbnails are touched when served from disk. The
  thumbnail freshness check (`thumb mtime >= original mtime`) still holds.
- **Needed set per frame**: the image the frame shows (`served_key`), its base
  (`served_base_key`, to redraw overlays cheaply), and the next wake's base and
  composite. Everything else in `cache/` (composites of old overlay values,
  renders of other items, editor previews, `*.tmp` leftovers) is deleted once
  unused for 10 minutes (`cache.GRACE_SECONDS`). The grace period also protects
  a render between being written and being read. There is no count or size
  cap, so previews of items that are neither shown nor up next are rendered
  again after 10 minutes unused, and editor drafts stay until the next run.
- **Thumbnails** (`thumbs/{id}_{size}_{rotation}.jpg`, photos only): the
  320 px thumb at rotation 0, which the library and media browser show, is
  kept for as long as the photo exists. Editor-size (1280 px) thumbs and other
  rotations go after a day unused (`housekeeping.THUMB_GRACE_SECONDS`), thumbs
  of photos no longer in the library after the 10 minute grace period.
- **Crash leftovers**, after the grace period: originals the library doesn't
  reference, `override.*` files other than the current one-off image, and
  per-frame directories under `/config/paperlessoffline/` and
  `.storage/paperlessoffline.<entry_id>` stores of config entries that no
  longer exist. Only names that look like entry ids (ULIDs) are touched, and
  the global store is never removed.
- **When**: after each pre-render (debounced after every change), so also at
  entry setup, and per frame every hour (`FrameManager.async_housekeeping`);
  orphaned entries at integration setup and every hour. Housekeeping never
  renders: it computes the up-next keys (with overlays at their current
  values) without rendering, and it still runs when the pre-render fails.
- **Races**: each file's last use is checked again right before it is deleted,
  so an entry used during the scan stays. Orphaned entry directories and
  stores must also be unchanged for the grace period, so a frame being added
  during the scan is safe.

## 16. Firmware telemetry on image requests

With the frame's *Telemetry* switch on (the default), the firmware fork
appends `voltage` (mV), `usb`, `charging`, `orientation` (0 to 3), `width`,
`height` and `fw` to its image requests.

- Battery voltage, USB power, charging and orientation are fed from them, and
  `fw` becomes the device's software version.
- The last value is kept until the next report; `last_read` gives its age and
  `source` says whether it came from a wake or a Bluetooth read (the newer
  one wins).
- Frames on upstream firmware, or with the switch off, keep the last Bluetooth
  reading.
- `width` and `height` are ignored: the frame's client ID decides the panel.
- The raw query stays available in the `telemetry` attribute of *Last seen*.

## 17. Hardware verification

`tools/hw_spike.py` is a standalone aiohttp server (outside HA) that serves
test-pattern BMPs (an arrow pointing up, corner labels, palette swatches, a
1 px border) in each format and orientation, and a settings JSON that can be
swapped at runtime.

- **Verified on a 7" frame**: the settings-then-image request order, the
  doubled image request, `If-Modified-Since`/304, all four image formats
  (top-down BMP, BMP with a positive height, raw 4bpp, JPEG), the mounting
  directions (section 5, confirmed end to end with `--mount portrait`), wake
  detection with short sleeps, overlays (readability of S to XL, halo and box
  over busy photos, refresh behaviour with a changing sensor), photo
  variables, copying overlays and `show_image` with `overlays: false`.
- **Not yet checked on a frame**: XXL readability, cards on plain and photo
  backgrounds, and `show_text`.
- **13" frames have not been tested on hardware.** A 13" frame running a
  spike detected our 4-bit BMP ("Already dithered"), read pixels from
  `bfOffBits = 118` and expected 1200×1600 (`H: 1200 W: 1600` in its log means
  rows of 600 bytes), which matches `PANELS["epd13"]`. What appears on the
  glass is unconfirmed, and the display driver's busy waits reported
  `powerOn : 5`, `refresh : 2` and `powerOff : 2` (microseconds), so the BUSY
  line never held during a refresh that should take 20 s or more. The
  "landscape" rotation direction is assumed by symmetry with the 7".
- **Bluetooth** (provisioning, opportunistic sync, WiFi onboarding, the fix
  flow) is covered by mocked tests and still needs a manual test on real
  hardware.

## 18. Testing

- **Python** (`tests/`, `pytest-homeassistant-custom-component`): render
  pipeline and dithering (pixel-identical to the reference loops, only valid
  device indices, BMP header, orientation maths, shrink-first against full
  decode), slideshow and quiet-hours logic (midnight, DST), wake detection and
  `Last-Modified`, the config and options flows, entities, actions and their
  schemas, Bluetooth (mocked `BleakClient`: write sequence, WiFi success and
  failure, sync, cooldown, opt-out), repair issues and fix flows, entry
  migration, URLs, housekeeping, EXIF, overlays (parser, fonts, anchors,
  palette-only output, compositing, helpers in both languages, redraw
  policies, errors, show if), photo overlays, cards, `show_text`, telemetry,
  the websocket API and upload, panel registration, and the writing
  conventions.
- **Frontend**: `npm run e2e` drives the mock harness (`frontend/dev/mock.ts`,
  which fakes the websocket API and sends subscription events) with
  Puppeteer: cropping with a locked shape, focal point and a render setting,
  live preview, drag to reorder, the rotation toggle, global defaults, the
  overlay editor, copying overlays to photos, and creating and editing a card.
- Checked by hand in a real browser against HA 2026.10: the panel, editor,
  settings, card, and the code editor fields (rendered as `ha-code-editor`
  with highlighting, insertion works).

## 19. Writing conventions

- **Never use the en dash (U+2013)** in any text: UI strings, translations,
  messages, code comments, docs or commit messages. Rephrase the sentence
  instead, e.g. with a comma, colon, "to" (`0 to 3`) or a plain hyphen for
  compound names (`Floyd-Steinberg`). The em dash (U+2014) is avoided the
  same way.
- This is enforced by `tests/test_style.py`, which fails if either character
  appears in a tracked text file.
- Terms follow [GLOSSARY.md](../GLOSSARY.md) in UI strings, docs and commit
  messages.
