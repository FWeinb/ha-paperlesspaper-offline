# paperlessoffline

A Home Assistant integration that drives paperlesspaper e-paper photo frames
running the offline firmware: it picks, renders and serves the image each frame
shows on its next wake.

## Frames and what they show

**Frame**:
One paperlesspaper e-paper device, set up in Home Assistant with its own photo library and settings.
_Avoid_: Device, display, panel (the panel is the frame's screen hardware)

**Wake**:
One moment where a frame wakes from deep sleep, fetches its image and goes back to sleep.
_Avoid_: Refresh, poll, update

**Library item**:
A photo or a card in a frame's library; library items take part in the rotation.
_Avoid_: Entry, slide, media

**Photo**:
A library item made from a picture.
_Avoid_: Image, picture, item

**Card**:
A library item made of text on a background, with no picture of its own.
_Avoid_: Text card (fine in prose), slide, text photo

**Card background**:
What a card's text is drawn on: a solid panel colour, or a photo from the same library.
_Avoid_: Backdrop, card image

**Preset**:
A starting point for a new card that fills in its first overlays ("Blank", "Info", "Notice").
_Avoid_: Template (a template is the text of an overlay), layout

**One-off image**:
An image sent to a frame from outside its library (with `show_image`) and shown for a number of wakes or until cleared.
_Avoid_: Override, temporary photo

**One-off text**:
A card sent to a frame from outside its library (with `show_text`) and shown for a number of wakes or until cleared; a frame shows at most one one-off image or one-off text at a time.
_Avoid_: Notification, alert, override

**Placeholder**:
The generated image a frame shows when it has no library item to show.
_Avoid_: Default image, empty screen

**Up next**:
The library item the frame will show on its next wake.
_Avoid_: Current photo, queued photo

**Base image**:
A photo, card background, one-off image or one-off text background rendered for a frame's panel, before any overlays are drawn.
_Avoid_: Raw image, dithered image

## Overlays

**Overlay**:
A named text box, written as a template, drawn on top of a base image.
_Avoid_: Label, widget, caption (a caption is one use of an overlay)

**Photo overlay**:
An overlay that belongs to one library item and is drawn only on it; a card's photo overlays are its content.
_Avoid_: Picture overlay, caption, card body

**Global photo overlay**:
An overlay that belongs to a frame and is drawn on every library item of that frame unless the item hides them (cards hide them unless switched on).
_Avoid_: Frame overlay, global overlay

**Photo variables**:
What an overlay's template knows about the library item it is drawn on: its name, and for photos the capture date and capture location.
_Avoid_: Metadata, EXIF fields

**Capture location**:
Where a photo was taken, as raw coordinates from the camera; never a place name.
_Avoid_: GPS, place, address

**Show if**:
An optional template on an overlay that decides at each wake whether the overlay is drawn.
_Avoid_: Condition, visibility rule

**Redraw policy**:
Whether an overlay's new text is drawn at every wake where it changed, or only when the library item changes anyway.
_Avoid_: Refresh mode, update interval
