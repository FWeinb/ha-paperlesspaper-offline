# Phase 1 plan — Core

## Status (2026-10-14)

| Milestone | State |
|---|---|
| M0 Hardware check | Done for 7" (formats, orientation, `--mount portrait` confirmed). 13" untested: no hardware available |
| M1 Skeleton and CI | Done (workflows not yet run on GitHub) |
| M2 Render pipeline | Done; 7 dither options; benchmark in DESIGN §11 |
| M3 Storage and library | Done |
| M4 HTTP and slideshow | Done |
| M5 Config flow (manual) and options | Done |
| M6 Entities, actions, events | Done |
| M7 BLE discovery and provisioning | Done (mocked tests; untested with hardware) |
| M8 Docs and release | README done; ready for `v0.1.0` |

Tests: 74 passing at the end of Phase 1 (98 after Phase 3). ruff and mypy are clean.

The design is in [DESIGN.md](DESIGN.md).

**Goal:** a frame can be added to HA, shows photos from its own library as a
slideshow, and can be controlled through entities and actions. There is no
custom UI yet: photos are managed through actions and the Media Browser.

## Repository layout

```
custom_components/paperlessoffline/
  __init__.py          # setup/unload entry, register views and services once, runtime_data
  manifest.json        # domain, dependencies (http, bluetooth, media_source), bluetooth matcher, pillow-heif
  const.py             # constants, BLE UUIDs, panel specs, palettes
  models.py            # dataclasses: PanelSpec, RenderSettings, Photo, FrameSettings, FrameState
  settings.py          # layered resolution: global → frame → photo
  store.py             # helpers.storage.Store wrappers: global store, per-frame store, migrations
  library.py           # originals on disk: add (bytes/path/URL/media source), delete, copy, EXIF/HEIC load
  render/
    __init__.py        # render(photo, settings, panel) -> RenderResult (bmp bytes, preview png, etag/mtime)
    pipeline.py        # orient, rotate, fit/crop, enhance, mount → native buffer
    dither.py          # FS, Atkinson, JJN, Sierra-2, Bayer, none; serpentine
    palette.py         # perceived / pure palettes, device index mapping
    bmp.py             # 4-bit top-down BMP encoder (+ raw 4bpp fallback encoder)
    placeholder.py     # "No photos yet" image
  cache.py             # on-disk render cache keyed by hash(original, resolved settings, panel)
  frame.py             # FrameManager: state, wake detection, slideshow, override, dispatcher signals
  slideshow.py         # sequential / shuffle-bag selection (pure logic)
  schedule.py          # timeout computation with quiet hours + motion suppression (pure logic)
  http.py              # ImageView, SettingsView (requires_auth=False, token lookup, Basic auth, Last-Modified, 304)
  ble.py               # BLE GATT client: write settings, commands (bleak-retry-connector)
  config_flow.py       # bluetooth discovery step, manual step, provisioning step, options flow
  services.py / services.yaml
  media_source.py      # browse per-frame libraries (originals + rendered preview)
  device_trigger.py    # "frame woke up"
  diagnostics.py       # redacted token/auth
  entity.py            # base entity (device_info from CLIENT_ID, dispatcher subscribe)
  image.py select.py button.py number.py switch.py sensor.py binary_sensor.py
  strings.json translations/en.json translations/de.json
  icons.json
tests/                 # pytest-homeassistant-custom-component
tools/hw_spike.py      # standalone test-pattern server for the hardware check (M0)
hacs.json  pyproject.toml  requirements_test.txt  .github/workflows/{validate,tests}.yml
```

## Milestones

The milestones are ordered by dependency. Each one ends with green tests.

### M0 — Hardware spike (do first; it settles the risks below)

- **What it is:** `tools/hw_spike.py`, a tiny aiohttp server that runs outside
  HA.
- **What it serves:**
  - test-pattern BMPs: an arrow pointing to the top, corner labels, palette
    swatches, a 1-px border
  - a settings JSON that can be swapped at runtime
- **Variants to try:**
  - BMP with a positive height and with a negative height
  - raw 4bpp
  - each orientation candidate, on both panels if available
- **What to record:**
  - the mapping from native buffer to glass orientation
  - which BMP header form works
  - whether `If-Modified-Since`/304 on the settings fetch works
  - the timing between the settings and image requests
- **Output:** a "verified on hardware" table in DESIGN.md §10, plus the
  constants in `const.py`.
- **Needs:** you to point a frame at the spike URL (via the official web UI)
  and report what the glass shows.

### M1 — Skeleton and CI

- `manifest.json`, `hacs.json`, `pyproject.toml` (ruff and mypy config), and
  test requirements.
- GitHub workflows: hassfest, HACS action, ruff, mypy, pytest.
- An empty integration that loads and unloads cleanly, with a smoke test.

### M2 — Render pipeline (pure Python; no HA needed)

- `palette.py`: perceived palette (`#1f2226`, `#d6d6d6`, `#416ce1`,
  `#067406`, `#ea4843`, `#dbd529`) and the pure palette, mapped to device
  indices 0/1/2/3/5/6.
- `dither.py`:
  - Error diffusion through a generic kernel walker (one loop over rows; the
    inner loop is vectorised where possible). Kernels for Floyd–Steinberg,
    Atkinson, JJN and Sierra-2, with optional serpentine.
  - Bayer as fully vectorised ordered dithering.
  - None: nearest colour.
- **Performance.**
  - Target: under 10 s for a 13" frame on a Raspberry Pi 4, rendering in an
    executor.
  - Benchmark early.
  - Fallback if too slow: Pillow's C `quantize(dither=FLOYDSTEINBERG)` for
    Floyd–Steinberg, with a documented note that the other kernels are slower.
- `pipeline.py`:
  1. EXIF transpose (and load HEIC through `pillow-heif`)
  2. photo rotation
  3. fit: cover with a focal point or crop rectangle, contain, or stretch
  4. enhancement
  5. mount orientation
  6. transform to the native buffer (constants from M0)
- `bmp.py`: 4-bit BMP encoder, plus the raw encoder.
- **Tests:**
  - golden-image tests on small inputs
  - every output pixel is a valid device index
  - correct BMP size and header
  - orientation maths

### M3 — Storage and library

- **Global store:** default render settings.
- **Per-frame store:**
  - frame settings
  - photos, in rotation order: id, filename, enabled flag, overrides, added
    timestamp
  - slideshow state: current id, shuffle bag, last wake, last served
    `Last-Modified`
  - override state
- `library.py`:
  - **Add** from bytes, a local path (checked against
    `allowlist_external_dirs`), a URL, or a media-source ID.
  - **Validation:** formats JPEG, PNG, WebP, HEIC; 50 MB cap.
  - Delete, and copy to another frame.
  - Remove a frame's directory when its entry is removed
    (`async_remove_entry`).
- `cache.py`:
  - Renders are keyed by a content hash.
  - `Last-Modified` = the time the render was first created, persisted so it
    stays stable across restarts.
  - Stale renders are pruned.

### M4 — HTTP and slideshow core

- `slideshow.py`: sequential, and shuffle-bag with no repeats.
- `schedule.py`:
  - next `timeout` = the base interval, or the time until quiet hours end
  - motion suppressed during quiet hours
  - DST-safe, using HA's time zone
- `frame.py` (`FrameManager`):
  - **On an image request:**
    - wake detection (more than 60 s since the last request)
    - advance, or keep, the current photo
    - pick in priority order: override → rotation → placeholder/last image
    - render through the cache, in an executor
  - **Records:** last seen, served `Last-Modified`, in-sync flag.
  - **Fires** `paperlessoffline_frame_wake`.
  - **Notifies** entities through the dispatcher.
  - **Pre-renders** the *next* photo after each wake, so the next request is
    fast.
- `http.py`:
  - The token maps to a frame; an unknown token returns 404.
  - Optional Basic auth.
  - Image response: `Content-Type: image/bmp`, `Content-Length`,
    `Last-Modified`. No redirects.
  - Settings response: honours `If-Modified-Since` with a 304; the JSON's
    `Last-Modified` changes whenever the computed settings change.
  - Query parameters are parsed and logged, ready for the future telemetry
    hook.
- **Tests:** wake debounce; one advance per wake; a double fetch inside 60 s
  doesn't advance; the 304 path; quiet-hours maths around midnight and DST;
  Basic auth.

### M5 — Config flow (manual) and options

- **Manual step:** Client ID (validated against `^epd(7|13)-[0-9a-f]{12}$`,
  which also gives the panel type) and a name.
- **Unique ID:** the Client ID.
- **After creation**, show the image and settings URLs. The flow aborts if HA
  has no internal URL.
- **Options flow:**
  - refresh interval
  - quiet hours (start/end, and whether to suppress motion)
  - mounting orientation
  - frame render defaults: palette, dither algorithm, serpentine, fit,
    enhancement
  - order mode
  - Basic auth on/off with user and password
  - regenerate token (shows the new URLs and warns that the frame must be
    re-provisioned)
- Global defaults are edited with a service in Phase 1; the panel takes this
  over in Phase 2.
- **Tests:** a full flow, duplicate abort, invalid ID, options round-trip.

### M6 — Entities, actions, events

- **Entities** as listed in DESIGN.md §7, except battery and charging, which
  are Phase 3. Each frame is one device: model "Paper 7" or "Paper L", and its
  connections include the BLE MAC.
  - `select` "current photo": choosing a photo sets it as the next one to show.
  - `number`/`switch` entities: write to the frame settings, which marks
    changes as pending.
  - `sensor` "pending changes": counts the changes the frame hasn't fetched yet.
  - `binary_sensor` "in sync".
- **Actions** (all target a frame device or entry):
  - `add_photo` (path, URL or media-source ID; optional overrides)
  - `remove_photo`
  - `copy_photo` (to another frame)
  - `set_photo_settings` (overrides; `null` clears one)
  - `set_photo_enabled`, `move_photo`
  - `show_photo`, `next_photo`
  - `show_image` (source, `wakes`, settings) and `clear_override`
  - `set_global_defaults`
  - `render_preview`: returns the preview PNG path, for debugging
- **Event and trigger:** a device trigger "frame woke up", built on the wake
  event.
- **Media source:** browse frame → photos. The thumbnail is the perceived-
  palette preview.
- **Diagnostics:** redacts the token and the password.
- **Tests:** service schemas and their effects; entity state after a simulated
  wake; device trigger.

### M7 — BLE discovery and provisioning in the config flow

- `manifest.json` gets a `bluetooth` matcher: `{"local_name": "epd*",
  "connectable": true}`.
- **Flow:** a discovery step (confirm the frame) → a provisioning step:
  1. Connect through `bleak-retry-connector`.
  2. Write `settingsUrl`, `downloadUrl`, `timeout`, and Basic auth if enabled.
  3. Send `SAVE_SETTINGS`, then `EXIT_SETUP`.
  4. On failure, offer a retry or a "configure manually" option.
- `ble.py` keeps the GATT logic isolated, so Phase 3 can add WiFi writes,
  system-info reads and opportunistic push.
- **Tests:** a mocked `BleakClient` with the write sequence asserted; a
  discovery flow, including dedupe against an existing entry.

### M8 — Docs and release prep

- README:
  - installation through HACS
  - the two setup paths
  - URLs and network requirements: the frame must reach HA's internal URL over
    HTTP
  - an actions reference
  - known firmware caveats
- German translation pass.
- Tag `v0.1.0`.

## Definition of done (Phase 1)

- Add a real frame through BLE or manually. Upload photos with actions. The
  frame cycles through them, one per wake, with the chosen dithering per photo,
  the right orientation, and no redraw when nothing changed.
- Quiet hours stretch the sleep time. Changing the refresh interval or switches
  is reflected after the next settings fetch, and the in-sync and pending
  entities show it.
- `show_image` from an automation (e.g. a camera snapshot) appears at the next
  wake and then returns to the rotation.
- CI is green: hassfest, HACS, ruff, mypy, pytest.

## Open items going in

- The M0 results decide the orientation constants and the BMP header details.
  Everything else can proceed in parallel, with those values as placeholders.
- If the dithering benchmark misses its target on a Pi, decide between the
  Pillow FS fallback and keeping all kernels with slower renders. That's your
  call once the numbers are in.
