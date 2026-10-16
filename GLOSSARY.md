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

**Photo**:
A picture in a frame's library that takes part in the rotation.
_Avoid_: Image, picture, item

**One-off image**:
An image sent to a frame from outside its library (with `show_image`) and shown for a number of wakes or until cleared.
_Avoid_: Override, temporary photo

**Placeholder**:
The generated image a frame shows when it has no photo to show.
_Avoid_: Default image, empty screen

**Up next**:
The photo the frame will show on its next wake.
_Avoid_: Current photo, queued photo

**Base image**:
A photo or one-off image rendered for a frame's panel, before any overlays are drawn.
_Avoid_: Raw image, dithered image

## Overlays

**Overlay**:
A named text box, written as a template, drawn on top of a base image.
_Avoid_: Label, widget, caption (a caption is one use of an overlay)

**Photo overlay**:
An overlay that belongs to one photo and is drawn only on that photo.
_Avoid_: Picture overlay, caption

**Global photo overlay**:
An overlay that belongs to a frame and is drawn on every photo of that frame unless the photo hides them.
_Avoid_: Frame overlay, global overlay

**Show if**:
An optional template on an overlay that decides at each wake whether the overlay is drawn.
_Avoid_: Condition, visibility rule

**Redraw policy**:
Whether an overlay's new text is drawn at every wake where it changed, or only when the photo changes anyway.
_Avoid_: Refresh mode, update interval
