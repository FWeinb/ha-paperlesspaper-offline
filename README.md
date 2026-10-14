# paperlesspaper (offline firmware) for Home Assistant

A Home Assistant integration for [paperlesspaper](https://paperlesspaper.de) e-paper
photo frames running the
[offline firmware](https://github.com/paperlesspaper/paperlesspaper-firmware-offline).

Each frame becomes a device in Home Assistant with its own photo library and
slideshow. Home Assistant does the image processing (cropping, colour
enhancement and dithering onto the six Spectra 6 colours) and serves the frame
a ready-to-display image. You choose the dithering per photo, with a per-frame
and a global default.

> **Status:** all three planned phases are done: core, sidebar panel and
> dashboard card, and Bluetooth extras (battery, WiFi onboarding, repairs).
> See [docs/DESIGN.md](docs/DESIGN.md).

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

For a new frame, open the **WiFi (optional)** section and enter your network.
Home Assistant sets it first and checks that the frame really connects (the
firmware only keeps credentials that work) before writing the URLs. The frame
stays in setup mode for only about 30 seconds after the button press; if setup
fails, press the button again and retry.

Home Assistant's local URL must be reachable by the frame. If it is
`localhost`, a loopback address (`127.0.0.1`) or a `*.local` name, Home
Assistant gives the frame its LAN IP address instead: loopback would point at
the frame itself, and the frame can't resolve mDNS names.

**Address the frame uses.** If Home Assistant is reachable on several
networks or IPs (e.g. a separate IoT VLAN), choose which one goes into the
frame's URLs. You can pick it during setup and change it later in the frame's
options. The list offers *Automatic* plus every IPv4 address of the Home
Assistant host, and you can also type an IP or a hostname the frame can
resolve. After changing it, press the frame's button once: Home Assistant
gives the frame the new URLs over Bluetooth (or use the repair notice).

**Manually.**

1. Add the integration and enter the frame ID shown on its screen, e.g.
   `epd7-3485188f1dc8`.
2. Home Assistant shows a *Settings URL* and an *Image URL*.
3. Enter both in the official
   [web UI](https://paperlesspaper.github.io/paperlesspaper-firmware-offline/).

## Managing photos: the Photo frames panel

Admins get a **Photo frames** entry in the sidebar. It has three parts.

**Frame status** (top of each frame's page):
- what the frame is showing and what's up next, as dithered previews
- when it was last seen
- whether it has picked up every change
- a *Skip* button

**Photos tab:**
- Upload by drag-and-drop or the *Upload* button (JPEG, PNG, WebP, HEIC; up
  to 50 MB each), or *Import from media* to pick images from any Home Assistant
  media source.
- Drag photos to change the order; the eye button takes a photo out of the
  rotation. Choose *In order* or *Shuffle*.
- Click a photo to open the editor:
  - Drag to **crop**. The box is locked to the frame's shape by default, so
    you get exactly what the frame shows.
  - Click to set the **focal point**, the part kept when cropping to fill.
  - **Rotate** in 90° steps.
  - Override **dithering, serpentine, fit, background, brightness, contrast and
    saturation** for this photo. Each setting shows the default it would
    otherwise inherit.
  - A **live preview** shows the photo dithered exactly as the frame will
    display it.
  - *Show next*, *Copy to…* another frame, or *Delete*.

**Settings tab:** the frame's mounting, refresh interval and rendering
defaults, with a preview. Quiet hours, HTTP authentication and the frame's URLs
are in the integration's options.

**Global defaults** (sidebar of the panel): rendering defaults for every
frame, previewed on any frame's photo.

The panel follows your Home Assistant theme and language (English and German).

## Dashboard card

The integration registers a **paperlesspaper frame** card
(`custom:paperlessoffline-frame-card`). Add it from the card picker and choose
a frame. It shows:
- what the frame displays, and what's up next (optional)
- the sync state and when the frame was last seen
- a *Skip* button
- for admins, a shortcut to the panel

```yaml
type: custom:paperlessoffline-frame-card
device_id: 0123456789abcdef   # the frame's device
show_up_next: true
title: Kitchen                # optional
```

## Bluetooth while the frame is in setup mode

The frame can only be reached over Bluetooth in setup mode, right after a
**single** button press. Whenever Home Assistant sees a known frame
advertising, it connects for a few seconds and:

- reads **battery voltage, charging and USB power** (and WiFi signal);
- sends **pending changes** immediately, instead of waiting for the next wake;
- gives the frame **new URLs** if they changed (see *Repairs* below).

So pressing the button once is also a way to refresh the battery reading or
apply changes right away. This needs a Bluetooth adapter or an ESPHome
Bluetooth proxy near the frame. Turn it off per frame in the options (*Update
over Bluetooth in setup mode*) if you want to use the official web UI while
the frame is in setup mode.

## Repairs

Home Assistant raises a repair notice (*Settings → System → Repairs*) when:

- **a frame hasn't checked in.** It missed its expected wake and two more
  intervals (quiet hours are taken into account). The notice clears itself
  when the frame checks in again.
- **a frame needs new URLs.** Either you generated new URLs in the options,
  or Home Assistant's local URL changed while the frame is overdue. The fix
  dialog updates the frame over Bluetooth (press its button once first), or
  shows the URLs to enter in the web UI.

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
| Sensor *Battery voltage*, binary sensors *Charging* and *USB power* | Read over Bluetooth when the frame was last in setup mode (see `last_read`) |
| Sensor *WiFi signal* | Same; disabled by default |

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
| `brightness`, `contrast`, `saturation` | 0 to 3 (1 = unchanged) | all levels |
| `palette` | `perceived` (default; matches what the panel really shows), `pure` | global and frame |
| `rotation` | 0 / 90 / 180 / 270 | photo |
| `focal_x`, `focal_y` | 0 to 1, the point kept when cropping | photo |
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

## Credits

Text on the frame (the "No photos yet" screen) is set in
[Noto Sans](https://github.com/notofonts/latin-greek-cyrillic), © The Noto
Project Authors. It is licensed under the SIL Open Font License 1.1 (see
`custom_components/paperlessoffline/render/fonts/OFL.txt`) and bundled as a
Latin subset.

## Development

```sh
uv venv --python 3.14 && uv pip install -r requirements_test.txt
.venv/bin/pytest -q
.venv/bin/ruff check . && .venv/bin/mypy custom_components
```

`strings.json`, both translation files and `services.yaml` are generated by
`tools/gen_strings.py` and `tools/gen_services_yaml.py`. Edit those scripts,
not the generated files.

### Frontend

The panel and card are Lit + TypeScript in `frontend/`. They are built with Vite
straight into `custom_components/paperlessoffline/frontend/`. That built bundle
is committed, so HACS users need no build step. Rebuild it after every frontend
change:

```sh
cd frontend
npm ci
npm run build      # typecheck + bundle
npm run dev        # mock harness at http://localhost:5199 (see dev/mock.ts)
npm run e2e        # interaction smoke test against the running harness
```

The mock harness (`dev/mock.ts`) fakes the integration's websocket API. Query
parameters such as `?frame=kitchen&edit=0`, `?tab=settings`, `?view=card`,
`?dark=1`, `?narrow=1` and `?lang=de` jump to a particular view.
