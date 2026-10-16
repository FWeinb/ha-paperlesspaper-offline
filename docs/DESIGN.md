# paperlessoffline: Home Assistant integration design

Home Assistant custom integration (domain `paperlessoffline`) for paperlesspaper
e-paper photo frames running the
[offline firmware](https://github.com/paperlesspaper/paperlesspaper-firmware-offline)
(researched at commit `4e4ddf7`, 2026-09-24).

## 1. Firmware facts this design is built on

- **Pull-only device.** The frame deep-sleeps, wakes on a fixed timer
  (`timeout`, default 3600 s), a button press or (optionally) motion, then makes
  an HTTP `GET` for one image URL (`downloadUrl`) and optionally one settings
  JSON (`settingsUrl`), and sleeps again. It has no HTTP server, mDNS, MQTT or
  push channel. HA can only influence what the frame sees on its *next* wake.
- **Identity.** `CLIENT_ID` = `epd7-<mac12>` or `epd13-<mac12>` (lowercase STA
  MAC). The prefix gives the panel size. It is used as the BLE name and shown on
  the frame's screen overlay. HTTP requests carry nothing that identifies the
  frame.
- **Panels.**
  - 7.3" Spectra 6: 800×480 native buffer.
  - 13.3" Spectra 6: 1200×1600 native buffer.
  - Device colour indices: `0` black, `1` blue, `2` green, `3` red, `5` yellow,
    `6` white.
- **Image formats accepted.**
  - JPEG and 24-bit BMP: dithered on the device with Floyd-Steinberg only.
    JPEGs are stretched without keeping the aspect ratio. The 13" on-device
    path looks broken.
  - Pre-dithered top-down 4-bit BMP whose nibbles are device indices.
  - Raw packed 4bpp, which must start with `0x66 0x66`.
  - We always serve a **pre-dithered 4-bit BMP**.
- **Change detection.** The frame compares the response's `Last-Modified` with
  the value it stored. If they're equal it skips the redraw. 302 redirects are
  not followed. The image request supports optional HTTP Basic auth and ignores
  TLS certificates.
- **Settings JSON keys:** `timeout`, `motionWakeup`, `chargerMode`,
  `autoRotation`, `downloadUrl`, `httpAuthUser`, `httpAuthPassword`. The
  frame fetches it with `If-Modified-Since`, and a 304 response is honoured.
- **BLE.** Only available during the ~30 s setup mode that follows a single
  button press; there is no pairing.
  - Writable: WiFi SSID and password, every setting including the URLs, and
    commands such as `SAVE_SETTINGS` and `EXIT_SETUP`.
  - Readable: system info `{"voltage", "usb", "charging"}`.
- **No WiFi telemetry.** The frame never reports battery level, firmware
  version or status over WiFi.
- **One image is stored on the frame**, so any slideshow has to be driven by
  the server.
- **No licence** in the firmware repo. We reimplement the protocols and the
  dithering ourselves and copy no code.

## 2. Packaging

- A HACS-installable custom integration: `custom_components/paperlessoffline`.
- HA 2026.x and newer only.
- Configured through the UI only. Built on config entries, `entry.runtime_data`,
  translations and diagnostics.
- Translations: English and German.
- CI (GitHub Actions): hassfest, HACS validation, ruff, mypy, and
  `pytest-homeassistant-custom-component`.
- Sidebar panel: Lit + TypeScript + Vite. The built bundle is committed under
  `custom_components/paperlessoffline/frontend/`, so HACS users need no build
  step.

## 3. Frames and setup

- **One config entry per frame.** Each entry is one device, identified by its
  `CLIENT_ID`.
- **Primary setup: BLE discovery** through HA's Bluetooth stack (a local
  adapter or ESPHome proxies), matching local name `epd*`.
  1. The user presses the frame's button once.
  2. HA discovers the frame and starts the config flow.
  3. The flow writes `downloadUrl`, `settingsUrl`, `timeout` and the auth
     settings to the frame, then sends `SAVE_SETTINGS` and `EXIT_SETUP`.
  4. Optionally, the same flow sets the WiFi SSID and password, which lets a
     factory-fresh frame be onboarded entirely from HA.
- **Manual fallback:** the user enters the Client ID shown on the frame. HA
  displays the URLs to paste into the official web UI.
- **Endpoints**, served at HA's internal URL over plain HTTP:
  - `/api/paperlessoffline/<token>/image.bmp`
  - `/api/paperlessoffline/<token>/settings.json`
- **Endpoint security.**
  - The token is unguessable and per frame. It is also how HA tells frames
    apart.
  - HTTP Basic auth is optional (off by default).
  - HA's own authentication is not used, because the frame cannot send a
    bearer token.
  - Query parameters such as `?battery=` are parsed, so a future firmware that
    sends telemetry works automatically.

## 4. Photo library

- **Separate library per frame.** Originals are stored untouched under
  `/config/paperlessoffline/<frame>/originals/`.
- **Non-destructive editing:** every edit is stored as metadata in a per-frame
  JSON store.
- **Uploads:** JPEG, PNG, WebP and HEIC (via `pillow-heif`), up to 50 MB per
  file. Photos can also be imported from any HA media source.
- **Copy to another frame:** copies the original plus its overrides, then
  re-renders for the target frame's panel.
- **Deleting a frame** deletes its library. The confirmation dialog says so.
- The library is exposed as an HA Media Source.

## 5. Rendering

- **Layered settings:** global default → frame default → photo override.

  | Setting                                      | Global | Frame | Photo |
  |----------------------------------------------|:------:|:-----:|:-----:|
  | Dithering algorithm                          | ✓      | ✓     | ✓     |
  | Serpentine scanning                          | ✓      | ✓     | ✓     |
  | Fit mode (cover / contain / stretch)         | ✓      | ✓     | ✓     |
  | Crop rectangle / focal point                 |        |       | ✓     |
  | Rotation                                     |        |       | ✓     |
  | Brightness / contrast / saturation           | ✓      | ✓     | ✓     |
  | Palette (perceived / pure)                   | ✓      | ✓     |       |
  | Mounting orientation (landscape / portrait / flipped) |  | ✓   |       |

- **Dithering algorithms:** Floyd-Steinberg, Atkinson, Jarvis-Judice-Ninke,
  Sierra-2, ordered/Bayer, and none (nearest colour), each with optional
  serpentine scanning. Implemented in numpy.
- **Target hardware**: HA often runs on slow hosts (Raspberry Pi class, 4 to
  8 GB RAM, shared with everything else). Prefer doing less work and keeping
  peak memory low over caching in RAM: no prepared images are kept in memory,
  renders and thumbnails are cached on disk only.
- **Pipeline:**
  1. Decode only what the canvas needs (shrink-first, see §18) and apply the
     EXIF orientation.
  2. Apply the photo's rotation.
  3. Fit or crop the image to the mounted canvas.
  4. Apply enhancement (brightness, contrast, saturation).
  5. Dither against the palette's RGB values.
  6. Map the result to device indices.
  7. Rotate it into the panel's native buffer.
  8. Encode as a top-down 4-bit BMP.
- **Cache.** Every render is pre-computed and cached on disk. Each render gets
  a stable `Last-Modified`, and any settings change invalidates the cache.

## 6. Slideshow and scheduling

- **Advance on each wake.** A request counts as a new wake when it comes more
  than 60 s after the previous request, so retries and redirect double-fetches
  don't count.
- **Order:** sequential, or shuffle with no repeats until every enabled photo
  has been shown.
- Photos can be enabled or disabled in the rotation, and reordered.
- **Dynamic `timeout`:** a base refresh interval plus optional quiet hours. HA
  computes the sleep length each time the frame fetches its settings.
- **Motion during quiet hours.** `motionWakeup: false` is sent for the length
  of quiet hours. This is a per-frame option, on by default.
- **`show_image` action:** shows a one-off image instead of the rotation, for N
  wakes or until cleared. Sources: URL, media-source ID, `camera`/`image`
  entity, or a local path. The image is not added to the library.
- **Empty rotation.** A frame that has never been served anything gets a
  generated placeholder (frame name, "No photos yet", a hint pointing to the
  panel). Otherwise the frame keeps its last image, served with the same
  `Last-Modified` so it isn't redrawn.
- **Deleting the photo on screen** takes effect at the next wake, when the next
  photo in the rotation is served.

## 7. Entities, events and repairs (per frame)

| Platform        | Entity                                                         |
|-----------------|----------------------------------------------------------------|
| `image`         | Preview of the current or pending rendered image               |
| `select`        | Up next: the photo the frame shows on its next wake            |
| `button`        | Next photo                                                     |
| `number`        | Refresh interval                                               |
| `switch`        | Motion wakeup, auto-rotation, charger mode                     |
| `sensor`        | Last seen, current photo, pending changes, photos in rotation, battery voltage\*, charging\* |
| `binary_sensor` | In sync: the frame has fetched the latest image and settings   |

\* Opportunistic, read over BLE: usually stale.

- **Event and trigger:** a `paperlessoffline_frame_wake` event (its data
  includes the photo served), plus a matching device trigger.
- **Opportunistic BLE.** When HA sees a known frame advertising, it connects,
  reads battery and charging status, and pushes any pending settings straight
  away.
- **Repairs:**
  - "Frame hasn't checked in": raised after 3× the expected interval (allowing
    for quiet hours); clears itself on the next request.
  - "HA URL changed": offers a guided BLE re-provision of each frame.
- **Out of scope:** firmware OTA.

## 8. Sidebar panel (admin-only) and card

- Frame list with status, last seen, in sync and current photo.
- Per-frame library grid:
  - drag-and-drop upload
  - import from a media source
  - delete
  - copy to another frame
- Photo editor:
  - crop and focal point
  - rotation and fit
  - dithering and enhancement overrides
  - a live dithered preview, rendered by HA in the perceived palette
- Rotation list: reorder, enable/disable, choose sequential or shuffle.
- Editors for global defaults and per-frame defaults.
- A small Lovelace card showing frame status, with a "next photo" control.

## 9. Phases

1. **Core** (done, v0.1.0)
   - config flow (manual and BLE provisioning)
   - HTTP views
   - render and dither pipeline with BMP output
   - storage
   - slideshow and scheduling
   - entities, actions, events, device trigger, media source, diagnostics
   - tests and CI
   - an early real-device check of the image format and orientation
2. **Panel and card** (done, v0.2.0; see §12).
3. **BLE extras** (done, v0.3.0; see §13): battery sensors, opportunistic
   push, WiFi onboarding, repairs.

## 10. Risks to verify on hardware

- How a client buffer is oriented on the physical glass, for both panels.
- Whether the frame accepts our 4-bit BMP, including how it handles the header
  height sign. The fallback is raw 4bpp starting with `0x66 0x66`.
- Whether the settings-JSON fetch works as the code suggests, including how
  `If-Modified-Since` and 304 responses behave.
- Upstream CI may build 13" firmware for both panel sizes, so be careful which
  firmware gets flashed.
- Performance of error-diffusion dithering on a 13" buffer (1.92 M pixels) in
  pure Python/numpy.

## 11. Implementation notes (Phase 1)

### Firmware behaviour confirmed by reading the code (not yet on hardware)

- Every wake requests the settings JSON (if `settingsUrl` is set) **before**
  the image. Any request more than 60 s after the previous one marks a new
  wake.
- For BMPs, the frame only reads `bfOffBits` and then reads `width/2`-byte rows
  top-down. The header's width, height and colour table are ignored. Our
  top-down BMP with a negative height is therefore correct for both the frame
  and ordinary image viewers.
- The settings fetch uses plain `http.begin()` without credentials. Basic auth
  therefore only protects the image endpoint; the settings endpoint is
  protected by the token alone.

### Implementation choices

- **`downloadUrl` in the settings JSON** is built from the host the frame used
  for the settings request, rather than from HA's configured URL. It can never
  point the frame somewhere unreachable.
- **"Up next" replaces "current photo" as the select entity.** Because the
  frame only changes at its next wake, the select chooses what the frame shows
  *next*. A separate *Current photo* sensor shows what it was last served. The
  *Skip* button advances "up next".
- **Mounting directions (verified on a 7" frame, hardware run 3).**
  - Held in portrait, the 7" frame shows its native 800×480 buffer rotated 90°
    counter-clockwise: the buffer's top edge on the left, its left edge at the
    bottom.
  - "portrait" on a landscape panel is therefore `rot90(canvas, 3)`, i.e. the
    canvas is rotated clockwise into the buffer. "portrait_flipped" is
    `rot90(canvas, 1)`.
  - The 13" (native portrait) uses the same convention for "landscape", but
    that is unverified.
  - Both panels default to portrait.
  - If the frame's own `autoRotation` is on, the frame may add a further 180°
    when it's upside down, so leave that off when using a flipped mounting.
- **Dithering speed.**
  - Error diffusion without serpentine runs as numpy batches along
    anti-diagonal wavefronts (`t = x + 3y`). The output is identical to a
    raster scan, which the tests check.
  - On an M-series Mac, a 13" render takes about 0.6 s for Floyd-Steinberg and
    1.2 s for JJN.
  - Serpentine uses a scalar loop, about 0.5 s for 7" and about 2.5 s for 13".
  - A Raspberry Pi will be several times slower. Renders run in the executor
    and are pre-rendered after each change and wake.
- **`Last-Modified`.** The frame skips the redraw when `Last-Modified` matches.
  Each frame therefore keeps a monotonic per-frame `Last-Modified`: it is
  bumped whenever the served content changes, and stays stable otherwise
  (including across restarts).
- **Validation library.** Home Assistant 2026.10 uses `probatio` in place of
  voluptuous (`import probatio as vol`).

### Hardware run 1 (2026-10-14, 13" frame `epd13-…`, spike run with `--panel 7` by mistake)

Confirmed on the device:
- Each wake fetches the settings JSON first. The frame sends back the exact
  `Last-Modified` string we served as `If-Modified-Since`.
- The image is requested **twice** per wake, about 0.4 s apart: once by
  `getRedirect()`, which only follows 301s, and once for the real download.
  The 60 s wake debounce covers this, and both requests get the same
  `Last-Modified`.
- `User-Agent: ESP32HTTPClient`. Nothing in the request identifies the frame.
- The 13" firmware detects our 4-bit BMP ("Already dithered"), reads pixels
  from `bfOffBits = 118` and expects 1200×1600 (`H: 1200 W: 1600` in its log
  means rows of 600 bytes). This matches `PANELS["epd13"]`.

Not yet confirmed: what appears on the glass, because the 800×480 test image
didn't fit the 13" buffer. The display driver's busy waits also reported
`powerOn : 5`, `refresh : 2` and `powerOff : 2` (microseconds), which means
the BUSY line never held during a refresh that should take about 20 s or more.
To be re-checked with a 13" run and with an upload from the official web UI.

### Hardware run 2 (7" frame, still flashed with the 13" build)

- **Firmware build pitfall.** `src/types.h` hard-codes `#define
  EPD_TYPE_13INCH`. The upstream CI tries to switch panels by `sed`-ing a
  `SET_DISPLAY` macro that doesn't exist, so the published "epd7" binary is
  likely a 13" build too. For a 7" frame, edit `types.h` (comment out
  `EPD_TYPE_13INCH`, uncomment `EPD_TYPE_7INCH`) and rebuild. Check: the boot
  log must say `UID: epd7-…`, and the 13"-only `[POWER] Supply ON` / `[SD]`
  lines disappear.
- **Wake detection changed.** With a 20 s sleep, requests came about 25 s
  apart, so the old "more than 60 s since the last request" rule never saw a
  new wake. The frame kept getting the same `Last-Modified` ("File not
  modified, skipping download"). New rule:
  - A **settings** request always starts a wake; the firmware makes exactly
    one per wake, before the image.
  - An **image** request starts a wake only for frames that haven't fetched
    settings within `2 × last sleep + 300 s`, and only if more than 60 s have
    passed since the previous request.
  - The spike tool uses the same rule.

### Hardware run 3 (7" frame, correct 7" build)

All four variants displayed: top-down BMP, BMP with a positive height, raw
4bpp, and JPEG. Every one had the red bar (buffer top) on the left and the blue
bar (buffer left) at the bottom when held in portrait. The firmware ignores the
BMP height sign, and our BMP is accepted. The mounting mapping was corrected
from this result and then confirmed end to end with `tools/hw_spike.py --panel
7 --mount portrait`: the arrow pointed up.

**13" frames have not been tested on hardware** (none available). Their buffer
size comes from the firmware code and hardware run 1's log; the "landscape"
rotation direction is assumed by symmetry with the 7".

## 12. Implementation notes (Phase 2: panel and card)

### Backend

- **Websocket API** (`websocket.py`). Every command requires an admin.
  - `paperlessoffline/frames`, `/photos`, `/subscribe`
  - `/photo/update` (`overrides` replaces all of a photo's overrides),
    `/photo/delete`, `/photo/reorder`, `/photo/copy`, `/photo/show`
  - `/frame/skip`, `/frame/update` (order, mounting, interval and rendering
    defaults, stored in the entry options)
  - `/import` (from a media source)
  - `/preview`: a dithered PNG rendered with *unsaved* photo, frame or global
    settings; not cached
  - `/defaults`, `/defaults/set`
  - `subscribe` pushes `{entry_id}` whenever a frame changes, and when frames
    are added or removed; the panel then refetches.
- **Upload**: `POST /api/paperlessoffline/upload/{entry_id}` (multipart,
  admins only, one or more `file` fields). Each file is validated like the
  `add_photo` action; per-file errors are reported without failing the batch.
- **Editor images**: the thumbnail view accepts `?size=320|1280&rotation=0..270`
  and caches each variant. Crop coordinates are fractions of the *rotated*
  image, so the editor shows the server-rotated version and crops map 1:1. The
  focal point is relative to the crop box, exactly as the renderer applies it.
  Image URLs in websocket responses are signed (12 h), because `<img>` tags
  can't send an auth header.
- **Registration** (`frontend.py`): the bundles are served from
  `/paperlessoffline_static/`.
  - The sidebar panel (`paperlessoffline-panel`, admin-only) is registered with
    `panel_custom`.
  - The card is auto-loaded via `frontend.add_extra_js_url`.
  - A content hash of the bundles is used as the `?v=` cache buster.
  - `frontend` and `panel_custom` are `after_dependencies`; the panel is
    skipped when the frontend isn't loaded (e.g. in tests).

### Frontend (`frontend/`)

- Lit 3 + TypeScript, built by Vite in library mode into
  `custom_components/paperlessoffline/frontend/`: two entry points (panel and
  card) plus a shared Lit chunk, about 14 kB gzipped each.
- The panel uses its own small components and native form controls styled with
  Home Assistant's CSS variables, rather than HA's internal `ha-*` elements,
  which aren't guaranteed to be loaded inside a custom panel. The card uses
  `ha-card`, which is always available on dashboards.
- Layered settings are edited with one component (`pp-render-settings`) at all
  three levels. Each field is either "Default: …", showing the inherited value,
  or set explicitly.
- The card finds the frame's entities through `hass.entities` (device id +
  translation key) and needs only a `device_id` in its config. Its editor
  comes from `getConfigForm`.
- Strings are in English and German (`localize.ts`), chosen from
  `hass.language`.

### Testing

- Python: websocket commands, upload (including rejected files), signed
  rotated editor images, admin-only enforcement, subscription events and
  panel/card registration (`tests/test_websocket.py`).
- Frontend: `npm run e2e` drives the mock harness with Puppeteer. It covers:
  - a crop locked to the frame's shape, saved with a focal point and a
    dithering override
  - live preview re-renders
  - drag-to-reorder
  - the rotation toggle
  - saving global defaults
- Checked by hand in a real browser against a real local Home Assistant
  (2026.10): the panel, editor, settings and card all work.

## 13. Implementation notes (Phase 3: Bluetooth extras)

### Firmware details used (from the code)

- **WiFi credentials.** Write the SSID first, then the password. Writing the
  password starts a connection test of up to 10 s. Credentials are stored only
  if it succeeds. The result is reported through the "WiFi connected"
  characteristic (one byte, 0/1).
- **Status characteristics**, readable only in setup mode:
  - system info `{"voltage": mV, "usb": bool, "charging": bool}`
  - WiFi info `{"ip", "rssi"}`
- **Setup mode** lasts about 30 s after one button press, or for as long as a
  client is connected.

### Design

- **`ble.FrameSession`** is one connection per sync. It offers status reads,
  WiFi setup with a connected check, settings writes, `SAVE_SETTINGS` and an
  optional `EXIT_SETUP`. `async_provision` (the config flow) is built on it.
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
- **Status entities** (battery voltage, charging, USB power, WiFi signal) are
  restored from persisted state and carry a `last_read` attribute.
- **Repairs** (`issues.py`, `repairs.py`):
  - *Overdue*: no request by `last request + last sleep sent (includes quiet
    hours) + 2 × interval + 5 min`. A never-seen frame counts from the entry's
    creation time.
  - *Provisioned* URL/token: entry data stores the token and base URL the frame
    is known to use. They are set by the config flow and refreshed by every
    successful request (from the request's origin).
  - *Reprovision* is needed when the token was regenerated, or when HA's
    current frame URL differs from the provisioned one *and* the frame is
    overdue. Otherwise an overdue frame gets the *offline* notice.
  - The fix flow either waits up to 45 s for the frame to advertise and writes
    the URLs (then exits setup), or accepts "I updated it myself".
  - Issues are rechecked every 5 minutes, after requests, BLE syncs and option
    changes, and on core config updates. They're deleted when the entry is
    removed.
- **Frame base URL** (`urls.py`): HA's internal URL, with hosts the frame
  can't use (`localhost`, loopback, unspecified or link-local IPs, `*.local`)
  replaced by the machine's LAN IP. ESP32 `HTTPClient` has no mDNS resolver,
  and loopback would point at the frame itself.
  - Request origins with such hosts (e.g. behind a local reverse proxy) are not
    recorded as the frame's provisioned URL.
  - A provisioned URL with such a host counts as "needs new URLs" immediately,
    so the next button press fixes it.
  - Found in manual testing: the dev instance had `internal_url:
    http://127.0.0.1:8124` and wrote that to the frame.
- **Chosen frame address** (option `url_host`, default `auto`): points the
  URLs at HA's own web server at that address.
  - Offered in both setup paths and in the options. The choices are HA's IPv4
    addresses from the network integration (adapters HA uses first, loopback
    and link-local excluded), plus free text.
  - Validated: a plain IP or DNS name, and not unusable for the frame.
  - When an explicit choice differs from the provisioned URL, the frame counts
    as "needs new URLs" immediately; the next button press or the repair flow
    applies it.
- **Entry migration**: v1.1 → v1.2 adds the provisioned token (the current
  token) and base URL (unknown).
- **Panel**: the frame header shows battery and charging status, and
  "hasn't checked in" / "needs new URLs" chips.

### Testing

`tests/test_ble.py` and `tests/test_phase3.py`, with BLE mocked, cover:
- status parsing
- WiFi success and failure
- the sync pushing pending settings and new URLs
- cooldown and the opt-out
- the offline / reprovision issue lifecycle
- the fix flow (manual, Bluetooth, not found)
- migration
- the `.local` rewrite

Bluetooth against real hardware still needs a manual test.

## 14. "No photos yet" screen

- Shown when a frame has never been served a photo and its rotation is
  empty. It is drawn for the six-colour panel:
  - a flat illustration (a framed picture hanging from a nail, with sun and
    hills) that uses all six colours
  - the frame name in bold, a red accent bar, "No photos yet" in red, and a
    hint pointing to the Photo frames panel
  - the frame ID in blue at the bottom
- **Layout**: stacked and centred on portrait and square canvases; the
  illustration sits beside the text on wide landscape canvases. Long names
  and hints wrap, and everything scales with the panel's short side.
- **Exact colours**: text is drawn without anti-aliasing
  (`ImageDraw.fontmode = "1"`) and only in the pure palette colours, so every
  pixel maps to a panel colour exactly, with no stray dither pixels around
  letters.
- **Font**: Pillow's built-in font lacks glyphs like `ü`, `ß` and `„` (frame
  names such as "Küche" showed boxes). Noto Sans Regular and Bold are bundled
  instead (SIL OFL 1.1, about 28 kB each). They're subset to Basic Latin,
  Latin-1 and Latin Extended-A plus common punctuation by
  `tools/build_fonts.py`.
- **Language**: the text follows HA's language (English or German).
- **Updating**: the cache key includes the text, and a frame already showing
  the placeholder gets the current version at its next wake (e.g. after a
  rename). A frame that has shown a photo keeps that photo when its rotation
  becomes empty, as before.
- **Frame name**: the screen (like `frame.name` in overlay templates, the
  panel, the media browser and repair notices) uses the frame's display name.
  - That is the device name a user set in HA (Settings → Devices), otherwise
    the device's own name, which follows the config entry title when the entry
    is renamed.
  - A device rename notifies the frame immediately: the "Up next" preview
    refreshes, the panel updates, and "renamed frame" shows as a pending
    change until the next wake serves the new screen.

## 15. Writing conventions

- **Never use the en dash (U+2013)** in any text: UI strings, translations,
  messages, code comments, docs or commit messages. Rephrase the sentence
  instead, e.g. with a comma, colon, "to" (`0 to 3`) or a plain hyphen for
  compound names (`Floyd-Steinberg`). The em dash (U+2014) is avoided the
  same way.
- This is enforced by `tests/test_style.py`, which fails if either character
  appears in a tracked text file.

## 16. Text and entity overlays (agreed design)

Render text, entity values and icons onto what the frame shows. Values are
evaluated when the image is rendered at a wake, so on the wall they are a
snapshot of that moment, not live.

### Concepts

- **Frame overlays**: text boxes defined per frame and drawn on every photo,
  e.g. sensor values in a corner. Each photo has a "hide frame overlays"
  switch.
- **Photo overlays**: text that belongs to one photo, e.g. a caption.
  `copy_photo` copies them along.
- **Text cards**: a new kind of library item that is mostly text.
  - Background: white, black, a panel colour, or a photo from the frame's
    library (rendered with that photo's own settings).
  - Presets to start from: "Info" (a title plus key values) and "Notice" (one
    big message).
  - Frame overlays are hidden on cards by default, with a per-card switch.
  - Cards behave like photos everywhere: rotation order, shuffle, the eye
    toggle, the "Up next" select, *Skip*, the media browser, and
    `list_photos` (with a `kind: photo | card` field). They are marked with a
    small badge.

### Content

- **Home Assistant templates (Jinja)** for all text.
- **Template variables**:
  - for photo overlays and for frame overlays on photos: `photo.name`,
    `photo.date` (EXIF capture date, or none) and `photo.location`;
  - everywhere: `frame.name`.
- **`photo.location`**: an object with `latitude`, `longitude` and `altitude`
  (each possibly missing). It renders as `48.1372, 11.5756` when used directly,
  is none without GPS data, and works with HA's `distance()`, e.g.
  `{{ distance(photo.location.latitude, photo.location.longitude) | round(0) }} km`.
  Raw coordinates only; no reverse geocoding.
- **Markdown subset**:
  - headings (`#`, `##`, `###`)
  - `**bold**` and `*italic*`
  - bullet lists
  - line breaks and paragraphs
  - colour spans for the six panel colours, e.g. `{red}warning{/red}`

  Not supported: images, tables, links, code blocks.
- **Icons**: Material Design Icons inline as `:mdi:weather-sunny:`, sized and
  coloured like the surrounding text. The MDI font is bundled (about 1.3 MB,
  Apache 2.0).
- **Template helpers**, passed in as functions:
  - `weather_icon(state)`: an HA weather condition to its MDI icon;
  - `entity_icon(entity_id)`: an icon explicitly set on an entity (device
    class default icons are resolved by the frontend and are not available);
  - `date_local(value, preset)`: dates with month and weekday names in HA's
    language (English or German), presets `short`, `long`, `month_year`,
    `weekday`, `time`.

  Integrations can't register filters in HA's template engine, so these are
  functions, e.g. `{{ date_local(photo.date, 'long') }}`, not filters.
- **Fonts**: the Noto Sans subset gains `° ± × ÷ µ ² ³ ‰`, arrows, bullet,
  currency and fraction characters, plus Italic and Bold Italic. No emoji.

### Layout and look

- Each frame, photo and card holds an **ordered list of named overlays**. Each
  can be enabled or disabled and has an optional **"show if"** template.
- **Box**: one of 9 anchor positions on the upright (mounted) canvas, a
  margin, auto or percentage width, text alignment, and a size preset
  (S / M / L / XL) scaled by the panel's short side.
- **Backing**: a white box with black text by default. Alternatives: a box in
  any panel colour, a contrasting halo around the letters, or nothing.
- **Order**: photo or card overlays first, then frame overlays on top. No
  automatic collision avoidance; the live preview shows overlaps.
- **Crisp text**: overlays are always composited after dithering, in exact
  panel colours and without anti-aliasing.

### Freshness and errors

- **Redraw policy per overlay**:
  - *every wake where its rendered text changed* (default);
  - *only when the photo changes anyway*.

  Rounding in templates avoids needless panel refreshes.
- **Errors**: a failing template leaves only that box out of the image and
  logs a warning. The frame still gets its image. The panel's live preview
  shows the error.

### Editing and automation

- **Panel**: an overlay editor for frame overlays (Settings tab), photo
  overlays (photo editor) and cards ("Add card" in the library). It has a
  template/markdown text field with an "insert entity" helper and an icon
  hint, the layout and backing controls, and a live preview with real current
  values on a real photo.
- **Copying**: a frame's overlays can be copied to another frame, from the
  panel or with an action.
- **Actions**: `show_text` (a one-off card for N wakes or until cleared, the
  counterpart of `show_image`) and actions to add, update, remove and copy
  overlays and cards. `show_image` and `show_text` draw frame overlays by
  default; `overlays: false` turns that off per call.

### Delivery

- **Step A**: the overlay engine, frame overlays, the panel overlay editor
  with live preview, and the overlay actions (including copying). See
  [STEP_A.md](STEP_A.md).
- **Step B**: photo overlays with photo variables, text cards with
  backgrounds and presets, `show_text`, and the overlay switch on one-off
  images.

Each step is tested on a real frame before the next.

## 17. Implementation notes (overlays, Step A)

- **Engine** (`render/overlay.py`): a hand-written parser for the markdown
  subset, then layout and drawing with Pillow.
  - Text is drawn without anti-aliasing, onto a layer prefilled with a
    sentinel colour (magenta), using only the six pure palette colours.
  - A single newline is a line break.
  - Size presets are 18 / 24 / 32 / 44 px at a 480 px short side; headings are
    × 1.6 / 1.35 / 1.15.
- **Glyph fallback**: Noto Sans has no arrows, `≤ ≥ ∞` or shapes like `▲ ●`.
  A subset of Noto Sans Math is bundled as a fallback. `coverage.json`
  (generated by `tools/build_fonts.py`) lists each font's codepoints, so text
  is split per character into runs of the first font that has the glyph,
  without fontTools at runtime. A word split across fonts stays together when
  wrapping.
- **Icons**: the full MDI webfont (1.3 MB, every icon usable), plus
  `mdi-codepoints.json` (13,659 names including aliases) generated from
  `@mdi/svg`.
- **Compositing** (`render/pipeline.py`): the cached base BMP is decoded back
  into canvas palette positions; this round trip is lossless for every
  mounting. Overlay pixels then replace base pixels, and the result is encoded
  as usual. The composite is cached under a key of base key + overlay texts +
  styles. The frame's base image is kept in the cache, so a value change only
  costs the cheap composite.
- **Evaluation**: once per wake, in the request handler right after the wake
  is detected. The texts are stored in the frame state, so the redirect probe,
  the download and retries of the same wake get the same image.
  - The *photo* redraw policy reuses stored texts while the same item is shown
    and the overlay definitions are unchanged; editing an overlay
    re-evaluates it.
  - "Up next" and the editor preview evaluate live.
- **Templates**: `Template.async_render(variables, parse_result=False)`.
  Helpers are passed in as variables (integrations can't add filters).
  - `date_local` is `date_local(value, preset)`.
  - `weather_icon` and `entity_icon` return inline `:mdi:name:` markup.
- **Not drawn on**: the "No photos yet" placeholder, and photos with
  `hide_frame_overlays`.
- **Pending changes**: an edited overlay shows as pending ("overlays") until
  the next wake evaluates it.
- **Previews**: unsaved drafts are sent with the id `draft`, so the editor can
  match the returned text or error to the field being edited.
- **Tests**: `tests/test_overlays.py` (26 tests: parser, fonts, anchors,
  palette-only output, compositing, helpers in both languages, wake
  behaviour, redraw policies, errors, show if, actions, websocket) and
  Puppeteer checks for the overlay editor.
- **Code editor** (`frontend/src/ha-editor.ts`): the overlay text and
  "show if" fields use HA's `ha-code-editor` (mode `jinja2`, with entity and
  icon autocompletion).
  - HA loads that element lazily and custom panels can't import HA internals.
    So the panel asks `window.loadCardHelpers()` for the built-in Markdown card
    editor, whose content field is a template selector, and renders it once
    off screen; that registers `ha-code-editor`.
  - If the element isn't defined within 3 s (a future frontend change, or the
    mock harness), plain text fields are used instead.
  - "Insert entity" inserts at the cursor through the editor's CodeMirror view
    (`codemirror.dispatch(state.replaceSelection(...))`).
  - Escape inside the editor is left to CodeMirror (e.g. closing
    autocompletion) instead of closing the dialog.
  - Checked against HA 2026.10 in a real browser: both fields render as
    `ha-code-editor` with highlighting, and insertion works.
- **Ports in frame URLs**: yarl writes the port whenever it isn't the scheme's
  default (80 for http, 443 for https), so configured ports such as 8123 always
  survive.
  - When the integration picks the host itself (a loopback, `localhost` or
    `.local` internal URL replaced by the LAN IP) or the user chooses an
    address, the URL uses HA's own HTTP server port and scheme
    (`hass.config.api`), not the internal URL's. Otherwise
    `http://homeassistant.local` (implicitly port 80) would have become
    `http://<ip>`, with nothing listening on port 80.
  - An internal URL with a usable host is kept exactly as configured, so a
    reverse proxy on port 80 keeps working.
  - The settings JSON's `downloadUrl` reuses the host and port the frame
    itself requested.

## 18. Implementation notes (render speed)

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
  - Enhancement and dithering run at canvas size as before.
  - Thumbnails (320 and 1280 px) use the same decode, targeting the thumb size.
  - `RENDER_VERSION` is 2, so existing cached renders are redone once.
- **Upload pixel limit**: images above 100 megapixels are refused (library
  uploads and `show_image` overrides share the validation), since decoding
  costs 3 bytes per pixel whatever the file size.
- **One preview request in flight** (`frontend/src/preview-queue.ts`): the
  photo editor, the settings views and the overlay editor send at most one
  preview at a time. Changes made meanwhile are coalesced, and only the
  latest draft is sent when the running request returns. Before, every
  debounced change was rendered in turn behind the render lock, stale or not.
- **Not done on purpose**: no prepared image in memory or on disk, stored
  originals stay untouched, dithering is unchanged.
- **Measured** (M-series Mac, 24 MP JPEG with EXIF rotation, 800x480 canvas,
  wall time and peak memory above the imported module):

  | Render                                  | Before        | After         |
  |-----------------------------------------|---------------|---------------|
  | Floyd-Steinberg                         | 0.32 s, 232 MB | 0.22 s, 63 MB  |
  | Floyd-Steinberg, serpentine             | 0.64 s, 304 MB | 0.55 s, 135 MB |
  | Bayer                                   | 0.22 s, 265 MB | 0.12 s, 100 MB |
  | 30 % crop, rotated (no shrink possible) | 0.26 s, 230 MB | 0.23 s, 131 MB |
  | 1280 px thumbnail, rotated              | 0.15 s, 230 MB | 0.11 s, 89 MB  |

  A cropped photo whose box is less than twice the canvas still needs the full
  decode; then only the transposes and copies are saved. Serpentine dithering
  remains the slowest step (about 0.4 s here, so seconds on a Pi).

