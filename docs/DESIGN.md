# paperlessoffline — Home Assistant integration design

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
  - JPEG and 24-bit BMP: dithered on the device with Floyd–Steinberg only.
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

- **Dithering algorithms:** Floyd–Steinberg, Atkinson, Jarvis–Judice–Ninke,
  Sierra-2, ordered/Bayer, and none (nearest colour), each with optional
  serpentine scanning. Implemented in numpy.
- **Pipeline:**
  1. Decode the image and apply its EXIF orientation.
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

1. **Core**
   - config flow (manual and BLE provisioning)
   - HTTP views
   - render and dither pipeline with BMP output
   - storage
   - slideshow and scheduling
   - entities, actions, events, device trigger, media source, diagnostics
   - tests and CI
   - an early real-device check of the image format and orientation
2. **Panel and card.**
3. **BLE extras:** battery sensors, opportunistic push, WiFi onboarding,
   repairs.

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
  - On an M-series Mac, a 13" render takes about 0.6 s for Floyd–Steinberg and
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
