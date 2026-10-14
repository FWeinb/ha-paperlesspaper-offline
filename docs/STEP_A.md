# Overlays, Step A: engine and frame overlays

**Status (2026-10-14):** A1 to A6 done, and A7 docs done. The check on a real
frame is pending.

Design: [DESIGN.md §16](DESIGN.md#16-text-and-entity-overlays-agreed-design).

**Goal:** text, entity values and icons drawn on top of every photo a frame
shows, defined per frame, edited in the panel with a live preview, and
manageable with actions. Photo overlays, text cards and `show_text` follow in
Step B.

## Architecture

### Rendering

1. **Base image**: the photo is rendered and dithered exactly as today, and
   cached as before (BMP and preview PNG).
2. **Overlay layer**: each overlay's evaluated markdown is laid out and drawn
   with Pillow onto an RGB layer prefilled with a sentinel colour that isn't in
   the palette. Text is drawn without anti-aliasing (`fontmode = "1"`), using
   only the six pure palette colours.
3. **Compositing**: the base BMP is decoded back into canvas-oriented palette
   positions (no new cache format). Every layer pixel that isn't the sentinel
   replaces the base pixel. The result is encoded into the BMP and preview as
   usual.
4. **Cache key** of the composited image = base key + every overlay's
   evaluated text + its layout settings. The existing `Last-Modified` logic
   then redraws the frame exactly when the result changes.

### When templates are evaluated

- **Once per wake**, when the wake is detected (the settings request, or the
  first image request for frames without settings). The texts are stored in
  the frame state, so the redirect probe, the download and any retries of the
  same wake all get the same image and `Last-Modified`.
- **Redraw policy**: overlays set to *only when the photo changes* keep the
  text evaluated when the current photo started; overlays set to *every wake*
  are re-evaluated each wake.
- **"Show if"** is evaluated at the same time. A falsy or failing condition
  hides the overlay.
- **Errors**: a failing template drops that overlay from the image, logs one
  warning per overlay and wake, and is reported to the panel.
- **Previews**: "Up next" and the editor's preview evaluate templates live at
  render time, and are never sent to the frame.

### Templates

- HA `Template.async_render(variables, parse_result=False)` in the event loop.
- **Variables** in Step A: `frame` (`frame.name`) plus the helper functions
  `weather_icon(state)`, `entity_icon(entity_id)` and
  `date_local(value, preset)`. The photo variables come with Step B.

### Markdown subset

A small hand-written parser:

- **Blocks**: `#`, `##`, `###` headings, `- ` / `* ` bullet items, blank-line
  paragraphs. A single newline is a line break (not joined as in CommonMark),
  which suits sensor lists.
- **Inline**: `**bold**`, `*italic*`, colour spans `{black}`, `{white}`,
  `{red}`, `{green}`, `{blue}`, `{yellow}` … `{/…}`, and icons `:mdi:name:`.
  A backslash escapes a marker.
- **Not supported**: anything else is rendered literally.

### Layout

- **Size presets** at a 480 px short side (scaled with the panel): S 18 px,
  M 24 px, L 32 px, XL 44 px. Headings use × 1.6 / 1.35 / 1.15. Line height
  1.3.
- **Box**: one of 9 anchors, margin (default 3 % of the short side), width
  `auto` (shrink to fit, up to the canvas minus margins) or a percentage,
  alignment left / centre / right.
- **Backing**: box (padding 0.5 em, corner radius 0.3 em) in a palette colour
  (default white), halo (text outline in a contrasting colour, 1 to 2 px by
  size), or none. Default text colour is black; colour spans override it.

### Overlay model (per frame, stored in the frame store)

`id`, `name`, `enabled`, `template`, `show_if`, `anchor`, `margin`, `width`,
`align`, `size`, `text_color`, `backing` (`box | halo | none`),
`backing_color`, `redraw` (`change | photo`). Photos get
`hide_frame_overlays`.

## Milestones

### A1: Fonts and icons
- Extend `tools/build_fonts.py`:
  - Noto Sans Regular, Bold, Italic and Bold Italic;
  - the subset gains `° ± × ÷ µ ² ³ ‰`, arrows, bullet, currency and
    fractions.
- Bundle the MDI webfont TTF from `@mdi/font` 7.4.47 (Apache 2.0, licence file
  included).
- Generate `mdi-codepoints.json` (name to codepoint) from `@mdi/svg`'s
  `meta.json`.
- Tests: glyph coverage for the new symbols; icon lookup by name; unknown
  icon names render nothing.

### A2: Markdown and layout engine (pure Python)
- Parser to blocks and styled runs; layout with wrapping, the size presets,
  anchors, widths, alignment and backing.
- Output: a palette-only RGB layer plus the drawn region.
- Tests: parser cases (nesting, escapes, colours, icons); only palette
  colours plus the sentinel appear; anchors land in the right corner on
  portrait and landscape; long text wraps within the width; halo and box
  rendering.

### A3: Compositing pipeline
- Decode a BMP back into canvas positions.
- Composite the layers over the base; encode the result.
- Composite cache key and pruning.
- Tests: the BMP round trip is lossless for every mounting; text pixels
  replace base pixels exactly; the same inputs give the same key.

### A4: Overlay model, templates, wake evaluation
- Storage in the frame store, with migration (no overlays by default).
- Evaluation at wake detection, the redraw policies, "show if", error
  handling and logging.
- Helpers: `weather_icon` (full HA weather condition table), `entity_icon`,
  `date_local` (English and German presets).
- Photo option `hide_frame_overlays`.
- Tests:
  - a value change triggers a new `Last-Modified` only for `change` overlays;
  - `photo` overlays keep their text until the next photo;
  - the redirect probe and the download get the same image;
  - a failing template drops only its box;
  - "show if" hides and shows;
  - helper outputs in both languages.

### A5: Actions and websocket API
- **Actions**: `add_overlay`, `update_overlay`, `remove_overlay`,
  `move_overlay`, `copy_overlays` (to another frame), `list_overlays`
  (response).
- **Websocket**: `overlays`, `overlay/save`, `overlay/delete`,
  `overlay/reorder`, `overlays/copy`, `overlay/preview`. The preview takes
  draft overlays and a sample photo, and returns the image plus each overlay's
  evaluated text or error.
- Tests: schemas, effects, admin-only access, preview errors.

### A6: Panel overlay editor
- An "Overlays" section in the frame's Settings tab: a list with an enabled
  toggle, drag to reorder, add, copy to frame.
- **Editor dialog**:
  - template/markdown text area with an "insert entity" helper (searchable
    entity list that inserts `states()` plus the unit) and an icon hint;
  - a 3 × 3 anchor picker, size, width, alignment, colours, backing, "show if"
    and redraw policy;
  - a live preview of the frame's overlays on a sample photo, with the
    current values and any error shown next to the field.
- Photo editor: "Hide frame overlays" switch.
- Mock harness and Puppeteer checks: create an overlay, see it in the preview,
  save, reorder, toggle.

### A7: Docs, translations, hardware check
- README section with examples (temperature corner, weather with icon,
  localised date), translations in English and German, DESIGN notes on what
  was learned.
- Check on your 7" frame: readability at each size preset, halo vs box over
  busy photos, refresh behaviour with a changing sensor.

## Definition of done (Step A)

- A frame overlay such as `:mdi:thermometer: **{{ states('sensor.outdoor') }} °C**`
  appears crisply on every photo.
- The value updates at the next wake after it changes, without extra refreshes
  when it hasn't.
- Overlays are created and edited in the panel with a live preview, or with
  actions, and can be copied to another frame.
- A broken template never breaks the image.
- All checks green, including the no-dash style test.
