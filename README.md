# paperlesspaper (offline firmware) for Home Assistant

A Home Assistant integration for [paperlesspaper](https://paperlesspaper.de) e-paper
photo frames running the
[offline firmware](https://github.com/paperlesspaper/paperlesspaper-firmware-offline).

Each frame becomes a device in Home Assistant with its own photo library and
slideshow. Home Assistant does the image processing (cropping, colour
enhancement and dithering onto the six Spectra 6 colours) and serves the frame
a ready-to-display image. You choose the dithering per photo, with a per-frame
and a global default.

> **Status:** Phase 1 (core). Photos are managed with actions and the media
> browser; a sidebar panel follows in Phase 2. See [docs/DESIGN.md](docs/DESIGN.md).

## How it works

The offline firmware is *pull only*:

1. The frame sleeps.
2. It wakes on a timer, a button press or (optionally) motion.
3. It downloads a settings file and one image from URLs you configure.
4. It goes back to sleep.

Home Assistant serves both URLs, so the frame:

- shows the next photo of its slideshow on every wake;
- picks up settings (refresh interval, motion wake-up, auto rotation, charger
  mode, HTTP credentials) on its next wake;
- sleeps through **quiet hours**, because Home Assistant stretches its sleep
  time.

Home Assistant can't reach the frame while it sleeps. Every change takes effect
at the frame's **next wake**; the *In sync* and *Pending changes* entities show
what hasn't been picked up yet. Press the frame's button twice to force a wake.

## Installation

1. In HACS, add this repository as a custom repository (category *Integration*).
2. Install **paperlesspaper (offline firmware)** and restart Home Assistant.
3. Check that Home Assistant has a local network URL (*Settings → System →
   Network*). The frame must reach it over plain HTTP.

## Adding a frame

**Over Bluetooth (recommended).**

1. Press the frame's button **once** to put it into setup mode.
2. Home Assistant discovers it (with a local Bluetooth adapter or an ESPHome
   Bluetooth proxy) and offers to set it up.
3. Confirm. Home Assistant writes its URLs to the frame.

The frame's WiFi must already be configured; WiFi onboarding from Home
Assistant is planned for Phase 3.

**Manually.**

1. Add the integration and enter the frame ID shown on its screen, e.g.
   `epd7-3485188f1dc8`.
2. Home Assistant shows a *Settings URL* and an *Image URL*.
3. Enter both in the official
   [web UI](https://paperlesspaper.github.io/paperlesspaper-firmware-offline/).

## Entities (per frame)

| Entity | Purpose |
|---|---|
| Image *Showing* / *Up next* | Dithered previews, as the panel will look |
| Select *Up next* | Choose which photo the frame shows on its next wake |
| Select *Slideshow order* | In order, or shuffle (no repeats until all photos have been shown) |
| Button *Skip photo* | Skip the photo that's up next |
| Number *Refresh interval* | Minutes between wakes |
| Switches | Motion wake-up, auto rotation, charger mode |
| Sensors | Last seen, current photo, pending changes, photos in rotation |
| Binary sensor *In sync* | Off while the frame still has changes to pick up |

There is also a **device trigger**, *Frame woke up*, and the
`paperlessoffline_frame_wake` event, whose data includes the photo that was
served.

The options flow also sets:

- the mounting orientation
- quiet hours
- rendering defaults for the frame
- HTTP Basic authentication
- new URLs, if you need to regenerate them

## Actions

All actions take `config_entry_id`, which selects the frame.

| Action | What it does |
|---|---|
| `paperlessoffline.add_photo` | Add an image from **one** of `file_path`, `url`, `media_content_id` or `image_entity_id` (camera or image entity). Optional `name`, `enabled` and per-photo render settings. Returns the `photo_id`. |
| `paperlessoffline.update_photo` | Change `name`, `enabled` or render settings; `reset` clears overrides (`all` clears every override). |
| `paperlessoffline.remove_photo` / `move_photo` / `copy_photo` | Manage the library; `copy_photo` copies to another frame. |
| `paperlessoffline.show_photo` / `next_photo` | Choose or skip the photo for the next wake. |
| `paperlessoffline.show_image` | Show a one-off image instead of the slideshow for `wakes` wakes, or until `clear_image`. The image is not added to the library. |
| `paperlessoffline.list_photos` | Returns the library and what's up next. |
| `paperlessoffline.set_defaults` | Set the global render defaults. |

Render settings are layered: **global default → frame default → photo override**.

| Setting | Values | Set at |
|---|---|---|
| `dither` | `floyd_steinberg`, `atkinson`, `jarvis_judice_ninke`, `sierra2`, `bayer`, `none` | all levels |
| `serpentine` | true / false | all levels |
| `fit` | `cover` (crop), `contain` (borders), `stretch` | all levels |
| `background` | `white`, `black` | all levels |
| `brightness`, `contrast`, `saturation` | 0–3 (1 = unchanged) | all levels |
| `palette` | `perceived` (default; matches what the panel really shows), `pure` | global and frame |
| `rotation` | 0 / 90 / 180 / 270 | photo |
| `focal_x`, `focal_y` | 0–1, the point kept when cropping | photo |
| `crop` | `[x, y, width, height]` as fractions | photo |

Example: show the doorbell camera for one wake.

```yaml
action: paperlessoffline.show_image
data:
  config_entry_id: 01J...   # the frame
  image_entity_id: camera.doorbell
  wakes: 1
  saturation: 1.3
```

For `file_path` to work, the folder must be listed under
`homeassistant: allowlist_external_dirs`.

## Security notes

- Each frame's URLs contain a long random token. Anyone who knows a frame's
  URLs can fetch its image and settings, so don't share them.
- The firmware doesn't send credentials when it fetches the settings file. If
  you enable HTTP authentication, only the image URL is protected, and the
  settings file (which contains the credentials) is protected by the token
  alone.
- Plain HTTP on the local network is expected. The firmware doesn't verify TLS
  certificates anyway.

## Hardware support

| Frame | Status |
|---|---|
| 7.3" (`epd7-…`) | Tested: image format and portrait/landscape orientation verified |
| 13.3" (`epd13-…`) | Untested. It should work, but landscape mounting may come out upside down |

If you have a 13" frame, run `tools/hw_spike.py --panel 13 --mount landscape`
(see its docstring) and report whether the arrow points up.

**Firmware build note:** the upstream firmware selects the panel at compile
time in `src/types.h` (`EPD_TYPE_13INCH` / `EPD_TYPE_7INCH`). Make sure your
frame's boot log shows the right ID prefix (`epd7-` or `epd13-`).

## Development

```sh
uv venv --python 3.14 && uv pip install -r requirements_test.txt
.venv/bin/pytest -q
.venv/bin/ruff check . && .venv/bin/mypy custom_components
```

`strings.json`, both translation files and `services.yaml` are generated by
`tools/gen_strings.py` and `tools/gen_services_yaml.py`. Edit those scripts,
not the generated files.
