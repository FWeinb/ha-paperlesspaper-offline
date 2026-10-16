"""Generate custom_components/paperlessoffline/services.yaml (keeps field order explicit)."""

from pathlib import Path

import yaml

DITHER = ["floyd_steinberg", "atkinson", "jarvis_judice_ninke", "sierra2", "bayer", "none"]

FRAME = {"required": True, "selector": {"config_entry": {"integration": "paperlessoffline"}}}
PHOTO_ID = {"required": True, "example": "a1b2c3d4e5f6", "selector": {"text": {}}}
FACTOR = {"selector": {"number": {"min": 0, "max": 3, "step": 0.05, "mode": "slider"}}}
UNIT = {"selector": {"number": {"min": 0, "max": 1, "step": 0.01, "mode": "slider"}}}


def select(options, key=None, **extra):
    sel = {"options": options, **extra}
    if key:
        sel["translation_key"] = key
    return {"selector": {"select": sel}}


SOURCE = {
    "file_path": {"example": "/media/photos/beach.jpg", "selector": {"text": {}}},
    "url": {"example": "https://example.com/photo.jpg", "selector": {"text": {"type": "url"}}},
    "media_content_id": {"selector": {"media": {"accept": ["image/*"]}}},
    "image_entity_id": {"selector": {"entity": {"domain": ["camera", "image"]}}},
}
SHARED = {
    "dither": select(DITHER, "dither"),
    "serpentine": {"selector": {"boolean": {}}},
    "fit": select(["cover", "contain", "stretch"], "fit"),
    "background": select(["white", "black"], "background"),
    "brightness": FACTOR,
    "contrast": FACTOR,
    "saturation": FACTOR,
}
PHOTO_RENDER = {
    **SHARED,
    "rotation": select(["0", "90", "180", "270"]),
    "focal_x": UNIT,
    "focal_y": UNIT,
    "crop": {"example": "[0.1, 0.0, 0.8, 1.0]", "selector": {"object": {}}},
}
PHOTO_KEYS = ["all", *SHARED, "rotation", "focal_x", "focal_y", "crop"]
FRAME_KEYS = ["all", "palette", *SHARED]
NAME = {"selector": {"text": {}}}

ANCHORS = [
    "top_left", "top_center", "top_right",
    "center_left", "center", "center_right",
    "bottom_left", "bottom_center", "bottom_right",
]  # fmt: skip
COLORS = ["black", "white", "red", "green", "blue", "yellow"]
PHOTO_ID_OPTIONAL = {"example": "a1b2c3d4e5f6", "selector": {"text": {}}}
OVERLAY_ID = {"required": True, "example": "a1b2c3d4e5f6", "selector": {"text": {}}}
OVERLAY_FIELDS = {
    "template": {
        "example": ":mdi:thermometer: **{{ states('sensor.outdoor') }} °C**",
        "selector": {"text": {"multiline": True}},
    },
    "show_if": {"selector": {"text": {"multiline": True}}},
    "enabled": {"selector": {"boolean": {}}},
    "anchor": select(ANCHORS, "overlay_anchor"),
    "size": select(["s", "m", "l", "xl"], "overlay_size"),
    "width": {"selector": {"number": {"min": 5, "max": 100, "unit_of_measurement": "%"}}},
    "margin": {"selector": {"number": {"min": 0, "max": 0.3, "step": 0.01, "mode": "box"}}},
    "align": select(["left", "center", "right"], "overlay_align"),
    "text_color": select(COLORS, "overlay_color"),
    "backing": select(["box", "halo", "none"], "overlay_backing"),
    "backing_color": select(COLORS, "overlay_color"),
    "redraw": select(["change", "photo"], "overlay_redraw"),
}

SERVICES = {
    "add_photo": {
        "config_entry_id": FRAME,
        **SOURCE,
        "name": NAME,
        "enabled": {"default": True, "selector": {"boolean": {}}},
        **PHOTO_RENDER,
    },
    "remove_photo": {"config_entry_id": FRAME, "photo_id": PHOTO_ID},
    "update_photo": {
        "config_entry_id": FRAME,
        "photo_id": PHOTO_ID,
        "name": NAME,
        "enabled": {"selector": {"boolean": {}}},
        "hide_frame_overlays": {"selector": {"boolean": {}}},
        "reset": select(PHOTO_KEYS, multiple=True),
        **PHOTO_RENDER,
    },
    "move_photo": {
        "config_entry_id": FRAME,
        "photo_id": PHOTO_ID,
        "position": {
            "required": True,
            "selector": {"number": {"min": 0, "max": 10000, "mode": "box"}},
        },
    },
    "copy_photo": {
        "config_entry_id": FRAME,
        "photo_id": PHOTO_ID,
        "target_config_entry_id": FRAME,
    },
    "show_photo": {"config_entry_id": FRAME, "photo_id": PHOTO_ID},
    "next_photo": {"config_entry_id": FRAME},
    "show_image": {
        "config_entry_id": FRAME,
        **SOURCE,
        "name": NAME,
        "wakes": {"selector": {"number": {"min": 1, "max": 1000, "mode": "box"}}},
        "overlays": {"default": True, "selector": {"boolean": {}}},
        **PHOTO_RENDER,
    },
    "clear_image": {"config_entry_id": FRAME},
    "list_photos": {"config_entry_id": FRAME},
    "add_overlay": {
        "config_entry_id": FRAME,
        "photo_id": PHOTO_ID_OPTIONAL,
        "name": {"required": True, "selector": {"text": {}}},
        **{
            k: ({**v, "required": True} if k == "template" else v)
            for k, v in OVERLAY_FIELDS.items()
        },
    },
    "update_overlay": {
        "config_entry_id": FRAME,
        "photo_id": PHOTO_ID_OPTIONAL,
        "overlay_id": OVERLAY_ID,
        "name": NAME,
        **OVERLAY_FIELDS,
    },
    "remove_overlay": {
        "config_entry_id": FRAME,
        "photo_id": PHOTO_ID_OPTIONAL,
        "overlay_id": OVERLAY_ID,
    },
    "move_overlay": {
        "config_entry_id": FRAME,
        "photo_id": PHOTO_ID_OPTIONAL,
        "overlay_id": OVERLAY_ID,
        "position": {
            "required": True,
            "selector": {"number": {"min": 0, "max": 1000, "mode": "box"}},
        },
    },
    "copy_overlays": {
        "config_entry_id": FRAME,
        "target_config_entry_id": {**FRAME, "required": False},
        "photo_id": {"selector": {"text": {}}},
        "to_photo_ids": {"selector": {"text": {"multiple": True}}},
        "replace": {"default": False, "selector": {"boolean": {}}},
    },
    "list_overlays": {"config_entry_id": FRAME, "photo_id": PHOTO_ID_OPTIONAL},
    "set_defaults": {
        "palette": select(["perceived", "pure"], "palette"),
        **SHARED,
        "reset": select(FRAME_KEYS, multiple=True),
    },
}


class _Dumper(yaml.SafeDumper):
    def ignore_aliases(self, data):
        return True


def main() -> None:
    out = {name: {"fields": fields} for name, fields in SERVICES.items()}
    target = Path(__file__).parents[1] / "custom_components/paperlessoffline/services.yaml"
    target.write_text(
        "# Generated by tools/gen_services_yaml.py - edit that file instead.\n"
        + yaml.dump(out, Dumper=_Dumper, sort_keys=False)
    )


if __name__ == "__main__":
    main()
