"""Generate strings.json and translations/{en,de}.json for the integration.

Keeping both languages in one place keeps their keys in sync.
"""

import json
from pathlib import Path

ROOT = Path(__file__).parents[1] / "custom_components/paperlessoffline"


def t(en: str, de: str) -> dict[str, str]:
    return {"en": en, "de": de}


DITHER = {
    "floyd_steinberg": t("Floyd–Steinberg", "Floyd–Steinberg"),
    "atkinson": t("Atkinson", "Atkinson"),
    "jarvis_judice_ninke": t("Jarvis–Judice–Ninke", "Jarvis–Judice–Ninke"),
    "sierra2": t("Sierra-2", "Sierra-2"),
    "bayer": t("Ordered (Bayer)", "Geordnet (Bayer)"),
    "none": t("None (nearest colour)", "Keines (nächste Farbe)"),
}
FIT = {
    "cover": t("Fill and crop", "Füllen und zuschneiden"),
    "contain": t("Fit with borders", "Einpassen mit Rand"),
    "stretch": t("Stretch", "Strecken"),
}
PALETTE = {
    "perceived": t("Perceived (as the panel looks)", "Wahrgenommen (wie das Panel aussieht)"),
    "pure": t("Pure RGB", "Reines RGB"),
}
BACKGROUND = {"white": t("White", "Weiß"), "black": t("Black", "Schwarz")}
ORDER = {"sequential": t("In order", "Der Reihe nach"), "shuffle": t("Shuffle", "Zufällig")}
MOUNTING = {
    "landscape": t("Landscape", "Querformat"),
    "portrait": t("Portrait", "Hochformat"),
    "landscape_flipped": t("Landscape (upside down)", "Querformat (kopfüber)"),
    "portrait_flipped": t("Portrait (upside down)", "Hochformat (kopfüber)"),
}
INHERIT = {"default": t("Use global default", "Globalen Standard verwenden")}
SERPENTINE = {**INHERIT, "on": t("On", "An"), "off": t("Off", "Aus")}

RENDER_FIELDS = {
    "dither": (t("Dithering", "Dithering"), t("Dithering algorithm.", "Dithering-Verfahren.")),
    "serpentine": (
        t("Serpentine scanning", "Serpentinen-Abtastung"),
        t(
            "Alternate the scan direction per row; reduces directional artefacts.",
            "Abtastrichtung je Zeile wechseln; reduziert Richtungsartefakte.",
        ),
    ),
    "fit": (
        t("Fit", "Einpassung"),
        t("How the photo is fitted to the frame.", "Wie das Foto in den Rahmen eingepasst wird."),
    ),
    "background": (
        t("Background", "Hintergrund"),
        t(
            "Border colour for 'fit with borders' and transparency.",
            "Randfarbe für „Einpassen mit Rand“ und Transparenz.",
        ),
    ),
    "brightness": (t("Brightness", "Helligkeit"), t("1 = unchanged.", "1 = unverändert.")),
    "contrast": (t("Contrast", "Kontrast"), t("1 = unchanged.", "1 = unverändert.")),
    "saturation": (
        t("Saturation", "Sättigung"),
        t(
            "1 = unchanged. Values above 1 often look better on e-paper.",
            "1 = unverändert. Werte über 1 wirken auf E-Paper oft besser.",
        ),
    ),
    "rotation": (
        t("Rotation", "Drehung"),
        t("Rotate the photo clockwise (degrees).", "Foto im Uhrzeigersinn drehen (Grad)."),
    ),
    "focal_x": (
        t("Focal point X", "Fokuspunkt X"),
        t(
            "Horizontal point to keep when cropping (0 = left, 1 = right).",
            "Horizontaler Punkt, der beim Zuschneiden erhalten bleibt (0 = links, 1 = rechts).",
        ),
    ),
    "focal_y": (
        t("Focal point Y", "Fokuspunkt Y"),
        t(
            "Vertical point to keep when cropping (0 = top, 1 = bottom).",
            "Vertikaler Punkt, der beim Zuschneiden erhalten bleibt (0 = oben, 1 = unten).",
        ),
    ),
    "crop": (
        t("Crop", "Ausschnitt"),
        t(
            "Crop box as [x, y, width, height] fractions of the photo.",
            "Ausschnitt als [x, y, Breite, Höhe] in Anteilen des Fotos.",
        ),
    ),
}
COMMON_FIELDS = {
    "config_entry_id": (t("Frame", "Rahmen"), t("The frame to act on.", "Der betroffene Rahmen.")),
    "photo_id": (
        t("Photo ID", "Foto-ID"),
        t(
            "ID of the photo (see the list photos action).",
            "ID des Fotos (siehe Aktion „Fotos auflisten“).",
        ),
    ),
    "target_config_entry_id": (
        t("Target frame", "Zielrahmen"),
        t("Frame to copy the photo to.", "Rahmen, in den das Foto kopiert wird."),
    ),
    "file_path": (
        t("File path", "Dateipfad"),
        t(
            "Local file (must be in an allowed directory).",
            "Lokale Datei (muss in einem erlaubten Verzeichnis liegen).",
        ),
    ),
    "url": (t("URL", "URL"), t("Image URL to download.", "Bild-URL zum Herunterladen.")),
    "media_content_id": (
        t("Media", "Medien"),
        t("Image from a media source.", "Bild aus einer Medienquelle."),
    ),
    "image_entity_id": (
        t("Camera or image entity", "Kamera- oder Bild-Entität"),
        t(
            "Take the current image of a camera or image entity.",
            "Aktuelles Bild einer Kamera- oder Bild-Entität verwenden.",
        ),
    ),
    "name": (t("Name", "Name"), t("Display name.", "Anzeigename.")),
    "enabled": (
        t("In rotation", "In der Rotation"),
        t(
            "Whether the photo takes part in the slideshow.",
            "Ob das Foto an der Diashow teilnimmt.",
        ),
    ),
    "reset": (
        t("Reset", "Zurücksetzen"),
        t(
            "Settings to reset to the inherited default (or 'all').",
            "Einstellungen, die auf den geerbten Standard zurückgesetzt werden (oder „all“).",
        ),
    ),
    "position": (
        t("Position", "Position"),
        t("New 0-based position in the rotation.", "Neue Position in der Rotation (ab 0)."),
    ),
    "wakes": (
        t("Wakes", "Aufwachvorgänge"),
        t(
            "Show for this many wakes, then return to the slideshow. Empty = until cleared.",
            "So viele Aufwachvorgänge anzeigen, dann zurück zur Diashow. Leer = bis zum Entfernen.",
        ),
    ),
    "palette": (
        t("Palette", "Palette"),
        t("Colours the dithering targets.", "Zielfarben des Ditherings."),
    ),
}
FIELDS = {**COMMON_FIELDS, **RENDER_FIELDS}

SERVICES = {
    "add_photo": t("Add photo", "Foto hinzufügen"),
    "remove_photo": t("Remove photo", "Foto entfernen"),
    "update_photo": t("Update photo", "Foto bearbeiten"),
    "move_photo": t("Move photo", "Foto verschieben"),
    "copy_photo": t("Copy photo to frame", "Foto in Rahmen kopieren"),
    "show_photo": t("Show photo next", "Foto als Nächstes zeigen"),
    "next_photo": t("Skip to next photo", "Zum nächsten Foto springen"),
    "show_image": t("Show image", "Bild anzeigen"),
    "clear_image": t("Clear shown image", "Angezeigtes Bild entfernen"),
    "list_photos": t("List photos", "Fotos auflisten"),
    "set_defaults": t("Set global defaults", "Globale Standards setzen"),
}
SERVICE_DESC = {
    "add_photo": t(
        "Adds an image to a frame's library. Give exactly one source.",
        "Fügt der Bibliothek eines Rahmens ein Bild hinzu. Genau eine Quelle angeben.",
    ),
    "remove_photo": t(
        "Deletes a photo from a frame's library.",
        "Löscht ein Foto aus der Bibliothek eines Rahmens.",
    ),
    "update_photo": t(
        "Changes a photo's name, rotation membership or render settings.",
        "Ändert Name, Rotationsteilnahme oder Darstellungseinstellungen eines Fotos.",
    ),
    "move_photo": t(
        "Moves a photo within the rotation order.", "Verschiebt ein Foto in der Reihenfolge."
    ),
    "copy_photo": t(
        "Copies a photo and its settings to another frame.",
        "Kopiert ein Foto samt Einstellungen in einen anderen Rahmen.",
    ),
    "show_photo": t(
        "Shows this photo on the frame's next wake.",
        "Zeigt dieses Foto beim nächsten Aufwachen des Rahmens.",
    ),
    "next_photo": t(
        "Skips the photo that is up next.", "Überspringt das als Nächstes geplante Foto."
    ),
    "show_image": t(
        "Shows a one-off image instead of the slideshow, without adding it to the library.",
        "Zeigt ein einmaliges Bild statt der Diashow, ohne es der Bibliothek hinzuzufügen.",
    ),
    "clear_image": t(
        "Returns to the slideshow on the next wake.",
        "Kehrt beim nächsten Aufwachen zur Diashow zurück.",
    ),
    "list_photos": t(
        "Returns the frame's photos and what is up next.",
        "Gibt die Fotos des Rahmens und das nächste Foto zurück.",
    ),
    "set_defaults": t(
        "Sets render defaults shared by all frames.", "Setzt Darstellungsstandards für alle Rahmen."
    ),
}

SERVICE_FIELDS = {
    "add_photo": [
        "config_entry_id",
        "file_path",
        "url",
        "media_content_id",
        "image_entity_id",
        "name",
        "enabled",
        *RENDER_FIELDS,
    ],
    "remove_photo": ["config_entry_id", "photo_id"],
    "update_photo": ["config_entry_id", "photo_id", "name", "enabled", "reset", *RENDER_FIELDS],
    "move_photo": ["config_entry_id", "photo_id", "position"],
    "copy_photo": ["config_entry_id", "photo_id", "target_config_entry_id"],
    "show_photo": ["config_entry_id", "photo_id"],
    "next_photo": ["config_entry_id"],
    "show_image": [
        "config_entry_id",
        "file_path",
        "url",
        "media_content_id",
        "image_entity_id",
        "name",
        "wakes",
        *RENDER_FIELDS,
    ],
    "clear_image": ["config_entry_id"],
    "list_photos": ["config_entry_id"],
    "set_defaults": [
        "palette",
        "dither",
        "serpentine",
        "fit",
        "background",
        "brightness",
        "contrast",
        "saturation",
        "reset",
    ],
}

URL_DESC = t(
    "In the official paperlesspaper web UI, set:\n\n**Settings URL:** `{settings_url}`\n\n**Image URL:** `{image_url}`\n\nThe frame must be able to reach Home Assistant at this address over plain HTTP.",
    "Im offiziellen paperlesspaper-Web-UI eintragen:\n\n**Settings-URL:** `{settings_url}`\n\n**Bild-URL:** `{image_url}`\n\nDer Rahmen muss Home Assistant unter dieser Adresse per HTTP erreichen können.",
)


def build(lang: str) -> dict:
    L = lambda pair: pair[lang]  # noqa: E731

    def states(options: dict) -> dict:
        return {"state": {k: L(v) for k, v in options.items()}}

    selector = {
        "dither": {"options": {k: L(v) for k, v in {**INHERIT, **DITHER}.items()}},
        "fit": {"options": {k: L(v) for k, v in {**INHERIT, **FIT}.items()}},
        "palette": {"options": {k: L(v) for k, v in {**INHERIT, **PALETTE}.items()}},
        "background": {"options": {k: L(v) for k, v in {**INHERIT, **BACKGROUND}.items()}},
        "serpentine": {"options": {k: L(v) for k, v in SERPENTINE.items()}},
        "order": {"options": {k: L(v) for k, v in ORDER.items()}},
        "mounting": {"options": {k: L(v) for k, v in MOUNTING.items()}},
    }
    render_section = {
        "name": L(
            t("Rendering defaults for this frame", "Darstellungsstandards für diesen Rahmen")
        ),
        "description": L(
            t(
                "Overrides the global defaults; photos can override these again.",
                "Überschreibt die globalen Standards; Fotos können diese erneut überschreiben.",
            )
        ),
        "data": {
            "palette": L(t("Palette", "Palette")),
            **{
                k: L(RENDER_FIELDS[k][0])
                for k in (
                    "dither",
                    "serpentine",
                    "fit",
                    "background",
                    "brightness",
                    "contrast",
                    "saturation",
                )
            },
        },
        "data_description": {
            "brightness": L(
                t(
                    "Leave empty to use the global default.",
                    "Leer lassen für den globalen Standard.",
                )
            ),
            "contrast": L(
                t(
                    "Leave empty to use the global default.",
                    "Leer lassen für den globalen Standard.",
                )
            ),
            "saturation": L(
                t(
                    "Leave empty to use the global default.",
                    "Leer lassen für den globalen Standard.",
                )
            ),
        },
    }
    return {
        "config": {
            "flow_title": "{name}",
            "step": {
                "user": {
                    "title": L(t("Add a paperlesspaper frame", "paperlesspaper-Rahmen hinzufügen")),
                    "description": L(
                        t(
                            "Enter the ID shown on the frame's screen (for example `epd7-3485188f1dc8`).",
                            "Die auf dem Rahmen angezeigte ID eingeben (z. B. `epd7-3485188f1dc8`).",
                        )
                    ),
                    "data": {
                        "client_id": L(t("Frame ID", "Rahmen-ID")),
                        "name": L(t("Name", "Name")),
                    },
                },
                "urls": {
                    "title": L(
                        t(
                            "Point the frame at Home Assistant",
                            "Rahmen auf Home Assistant zeigen lassen",
                        )
                    ),
                    "description": L(URL_DESC),
                },
                "bluetooth_confirm": {
                    "title": L(t("Set up {client_id}", "{client_id} einrichten")),
                    "description": L(
                        t(
                            "Home Assistant will configure the frame over Bluetooth to fetch its pictures from `{base_url}`. Keep the frame in setup mode (press its button once).",
                            "Home Assistant konfiguriert den Rahmen per Bluetooth, damit er seine Bilder von `{base_url}` abruft. Den Rahmen im Einrichtungsmodus halten (Taste einmal drücken).",
                        )
                    ),
                    "data": {
                        "name": L(t("Name", "Name")),
                        "provision": L(
                            t(
                                "Configure the frame over Bluetooth now",
                                "Rahmen jetzt per Bluetooth konfigurieren",
                            )
                        ),
                    },
                },
            },
            "error": {
                "invalid_client_id": L(
                    t(
                        "This doesn't look like a frame ID (epd7-… or epd13- followed by 12 hex digits).",
                        "Das sieht nicht nach einer Rahmen-ID aus (epd7-… oder epd13- gefolgt von 12 Hex-Ziffern).",
                    )
                ),
                "provision_failed": L(
                    t(
                        "Couldn't configure the frame over Bluetooth. Press its button once and try again, or untick the option to set it up manually.",
                        "Der Rahmen konnte nicht per Bluetooth konfiguriert werden. Taste einmal drücken und erneut versuchen oder die Option abwählen, um ihn manuell einzurichten.",
                    )
                ),
            },
            "abort": {
                "already_configured": L(
                    t("This frame is already set up.", "Dieser Rahmen ist bereits eingerichtet.")
                ),
                "no_internal_url": L(
                    t(
                        "Home Assistant has no local network URL. Set one under Settings → System → Network.",
                        "Home Assistant hat keine lokale Netzwerk-URL. Unter Einstellungen → System → Netzwerk festlegen.",
                    )
                ),
                "not_supported": L(
                    t(
                        "This Bluetooth device isn't a supported frame.",
                        "Dieses Bluetooth-Gerät ist kein unterstützter Rahmen.",
                    )
                ),
            },
        },
        "options": {
            "step": {
                "init": {
                    "title": L(t("Frame settings", "Rahmeneinstellungen")),
                    "description": L(URL_DESC),
                    "data": {
                        "interval": L(t("Refresh interval", "Aktualisierungsintervall")),
                        "order": L(t("Slideshow order", "Reihenfolge der Diashow")),
                        "mounting": L(t("Mounting", "Ausrichtung")),
                        "regenerate_token": L(
                            t("Generate new frame URLs", "Neue Rahmen-URLs erzeugen")
                        ),
                    },
                    "data_description": {
                        "interval": L(
                            t(
                                "How long the frame sleeps between updates (minutes). Applied at its next wake.",
                                "Wie lange der Rahmen zwischen Aktualisierungen schläft (Minuten). Wird beim nächsten Aufwachen übernommen.",
                            )
                        ),
                        "mounting": L(
                            t(
                                "How the frame hangs on the wall.",
                                "Wie der Rahmen an der Wand hängt.",
                            )
                        ),
                        "regenerate_token": L(
                            t(
                                "The old URLs stop working immediately; the frame must be set up again via Bluetooth or the web UI.",
                                "Die alten URLs funktionieren sofort nicht mehr; der Rahmen muss per Bluetooth oder Web-UI neu eingerichtet werden.",
                            )
                        ),
                    },
                    "sections": {
                        "quiet_hours": {
                            "name": L(t("Quiet hours", "Ruhezeiten")),
                            "description": L(
                                t(
                                    "The frame sleeps through quiet hours instead of updating.",
                                    "Der Rahmen schläft während der Ruhezeiten durch, statt zu aktualisieren.",
                                )
                            ),
                            "data": {
                                "quiet_enabled": L(
                                    t("Enable quiet hours", "Ruhezeiten aktivieren")
                                ),
                                "quiet_start": L(t("Start", "Beginn")),
                                "quiet_end": L(t("End", "Ende")),
                                "quiet_suppress_motion": L(
                                    t(
                                        "Disable motion wake-up during quiet hours",
                                        "Aufwecken durch Bewegung während der Ruhezeiten deaktivieren",
                                    )
                                ),
                            },
                        },
                        "rendering": render_section,
                        "authentication": {
                            "name": L(t("HTTP authentication", "HTTP-Authentifizierung")),
                            "description": L(
                                t(
                                    "Require HTTP Basic credentials for the image URL. They are sent to the frame on its next wake.",
                                    "HTTP-Basic-Zugangsdaten für die Bild-URL verlangen. Sie werden dem Rahmen beim nächsten Aufwachen übermittelt.",
                                )
                            ),
                            "data": {
                                "auth_enabled": L(
                                    t("Require credentials", "Zugangsdaten verlangen")
                                ),
                                "auth_user": L(t("Username", "Benutzername")),
                                "auth_password": L(t("Password", "Passwort")),
                            },
                        },
                    },
                }
            },
            "error": {
                "auth_incomplete": L(
                    t(
                        "Enter both a username and a password.",
                        "Benutzername und Passwort eingeben.",
                    )
                )
            },
        },
        "selector": selector,
        "device_automation": {
            "trigger_type": {"wake": L(t("Frame woke up", "Rahmen ist aufgewacht"))}
        },
        "entity": {
            "binary_sensor": {"in_sync": {"name": L(t("In sync", "Synchron"))}},
            "button": {"skip": {"name": L(t("Skip photo", "Foto überspringen"))}},
            "image": {
                "preview_showing": {"name": L(t("Showing", "Angezeigt"))},
                "preview_up_next": {"name": L(t("Up next", "Als Nächstes"))},
            },
            "number": {"interval": {"name": L(t("Refresh interval", "Aktualisierungsintervall"))}},
            "select": {
                "up_next": {"name": L(t("Up next", "Als Nächstes"))},
                "order": {
                    "name": L(t("Slideshow order", "Reihenfolge der Diashow")),
                    **states(ORDER),
                },
            },
            "sensor": {
                "last_seen": {"name": L(t("Last seen", "Zuletzt gesehen"))},
                "current_photo": {"name": L(t("Current photo", "Aktuelles Foto"))},
                "pending_changes": {"name": L(t("Pending changes", "Ausstehende Änderungen"))},
                "photos": {"name": L(t("Photos in rotation", "Fotos in der Rotation"))},
            },
            "switch": {
                "motion_wakeup": {"name": L(t("Motion wake-up", "Aufwecken durch Bewegung"))},
                "auto_rotation": {"name": L(t("Auto rotation", "Automatische Drehung"))},
                "charger_mode": {"name": L(t("Charger mode", "Lademodus"))},
            },
        },
        "exceptions": {
            "frame_not_loaded": {
                "message": L(
                    t("Frame {entry_id} is not loaded.", "Rahmen {entry_id} ist nicht geladen.")
                )
            },
            "photo_not_found": {
                "message": L(t("Photo {photo_id} not found.", "Foto {photo_id} nicht gefunden."))
            },
            "image_too_large": {
                "message": L(t("The image is larger than 50 MB.", "Das Bild ist größer als 50 MB."))
            },
            "invalid_image": {
                "message": L(
                    t(
                        "The file is not a readable image: {error}",
                        "Die Datei ist kein lesbares Bild: {error}",
                    )
                )
            },
            "unsupported_format": {
                "message": L(
                    t(
                        "Unsupported image format {format}; use JPEG, PNG, WebP or HEIC.",
                        "Nicht unterstütztes Bildformat {format}; JPEG, PNG, WebP oder HEIC verwenden.",
                    )
                )
            },
            "exactly_one_source": {
                "message": L(
                    t(
                        "Give exactly one of file path, URL, media or camera/image entity.",
                        "Genau eine Quelle angeben: Dateipfad, URL, Medien oder Kamera-/Bild-Entität.",
                    )
                )
            },
            "path_not_allowed": {
                "message": L(
                    t(
                        "{path} is not in an allowed directory (allowlist_external_dirs).",
                        "{path} liegt nicht in einem erlaubten Verzeichnis (allowlist_external_dirs).",
                    )
                )
            },
            "source_failed": {
                "message": L(
                    t(
                        "Couldn't get the image: {error}",
                        "Bild konnte nicht abgerufen werden: {error}",
                    )
                )
            },
        },
        "services": {
            name: {
                "name": L(SERVICES[name]),
                "description": L(SERVICE_DESC[name]),
                "fields": {
                    f: {"name": L(FIELDS[f][0]), "description": L(FIELDS[f][1])} for f in fields
                },
            }
            for name, fields in SERVICE_FIELDS.items()
        },
    }


def main() -> None:
    en = build("en")
    (ROOT / "strings.json").write_text(json.dumps(en, indent=2, ensure_ascii=False) + "\n")
    (ROOT / "translations").mkdir(exist_ok=True)
    (ROOT / "translations/en.json").write_text(json.dumps(en, indent=2, ensure_ascii=False) + "\n")
    (ROOT / "translations/de.json").write_text(
        json.dumps(build("de"), indent=2, ensure_ascii=False) + "\n"
    )


if __name__ == "__main__":
    main()
