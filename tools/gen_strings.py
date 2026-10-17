"""Generate strings.json and translations/{en,de}.json for the integration.

Keeping both languages in one place keeps their keys in sync.
"""

import json
from pathlib import Path

ROOT = Path(__file__).parents[1] / "custom_components/paperlessoffline"


def t(en: str, de: str) -> dict[str, str]:
    return {"en": en, "de": de}


DITHER = {
    "floyd_steinberg": t("Floyd-Steinberg", "Floyd-Steinberg"),
    "atkinson": t("Atkinson", "Atkinson"),
    "jarvis_judice_ninke": t("Jarvis-Judice-Ninke", "Jarvis-Judice-Ninke"),
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
            "Alternate the scan direction per row; reduces directional artefacts. "
            "Renders much slower (several seconds on small hosts).",
            "Abtastrichtung je Zeile wechseln; reduziert Richtungsartefakte. "
            "Rendert deutlich langsamer (auf kleinen Hosts mehrere Sekunden).",
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
        "Changes a photo's name, rotation membership or render settings, or a card's name, rotation membership or background.",
        "Ändert Name, Rotationsteilnahme oder Darstellungseinstellungen eines Fotos, oder Name, Rotationsteilnahme oder Hintergrund einer Karte.",
    ),
    "move_photo": t(
        "Moves a photo within the rotation order.", "Verschiebt ein Foto in der Reihenfolge."
    ),
    "copy_photo": t(
        "Copies a photo or card with its settings and overlays to another frame. A card's background photo is copied along, or reused if that frame has it.",
        "Kopiert ein Foto oder eine Karte samt Einstellungen und Overlays in einen anderen Rahmen. Das Hintergrundfoto einer Karte wird mitkopiert, oder wiederverwendet, wenn der Rahmen es schon hat.",
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
        "Clears the one-off image or text; the slideshow returns on the next wake.",
        "Entfernt das einmalige Bild oder den einmaligen Text; die Diashow kehrt beim nächsten Aufwachen zurück.",
    ),
    "list_photos": t(
        "Returns the frame's photos and cards (each with its kind) and what is up next.",
        "Gibt die Fotos und Karten des Rahmens (jeweils mit Art) und das als Nächstes Gezeigte zurück.",
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


def _build_base(lang: str) -> dict:
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
        "reprovision_method": {
            "options": {
                "bluetooth": L(
                    t(
                        "Over Bluetooth (press the frame's button once first)",
                        "Per Bluetooth (zuerst die Taste am Rahmen einmal drücken)",
                    )
                ),
                "manual": L(
                    t(
                        "I've entered the URLs in the web UI myself",
                        "Ich habe die URLs selbst im Web-UI eingetragen",
                    )
                ),
            }
        },
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
        "issues": {
            "offline": {
                "title": L(t("{name} hasn't checked in", "{name} hat sich nicht gemeldet")),
                "description": L(
                    t(
                        "The frame {name} last contacted Home Assistant at {last_seen} and has missed several updates. Check that it has power (or battery) and WiFi, and that it can reach Home Assistant. Pressing its button twice forces an update. This notice disappears by itself once the frame checks in again.",
                        "Der Rahmen {name} hat sich zuletzt um {last_seen} bei Home Assistant gemeldet und mehrere Aktualisierungen verpasst. Prüfen, ob er Strom (oder Akku) und WLAN hat und Home Assistant erreichen kann. Zweimaliges Drücken der Taste erzwingt eine Aktualisierung. Dieser Hinweis verschwindet von selbst, sobald sich der Rahmen wieder meldet.",
                    )
                ),
            },
            "reprovision_token": {
                "title": L(t("{name} needs its new URLs", "{name} braucht die neuen URLs")),
                "fix_flow": {
                    "step": {
                        "init": {
                            "title": L(t("Update {name}'s URLs", "URLs von {name} aktualisieren")),
                            "description": L(
                                t(
                                    "To update over Bluetooth, press the button on {name} once (it then stays in setup mode for about 30 seconds) and select Submit. A Bluetooth adapter or proxy must be near the frame.\n\nOr enter these in the official web UI:\n\n**Settings URL:** `{settings_url}`\n\n**Image URL:** `{image_url}`",
                                    "Für die Aktualisierung per Bluetooth die Taste an {name} einmal drücken (der Rahmen bleibt dann etwa 30 Sekunden im Einrichtungsmodus) und Absenden wählen. Ein Bluetooth-Adapter oder -Proxy muss in der Nähe sein.\n\nOder diese im offiziellen Web-UI eintragen:\n\n**Settings-URL:** `{settings_url}`\n\n**Bild-URL:** `{image_url}`",
                                )
                            ),
                            "data": {"method": L(t("How", "Wie"))},
                        }
                    },
                    "error": {
                        "not_found": L(
                            t(
                                "The frame wasn't found over Bluetooth. Press its button once and try again.",
                                "Der Rahmen wurde per Bluetooth nicht gefunden. Taste einmal drücken und erneut versuchen.",
                            )
                        ),
                        "ble_failed": L(
                            t(
                                "Couldn't update the frame over Bluetooth. Press its button once and try again.",
                                "Der Rahmen konnte per Bluetooth nicht aktualisiert werden. Taste einmal drücken und erneut versuchen.",
                            )
                        ),
                        "no_bluetooth": L(
                            t(
                                "Bluetooth isn't set up in Home Assistant.",
                                "Bluetooth ist in Home Assistant nicht eingerichtet.",
                            )
                        ),
                        "no_url": L(
                            t(
                                "Home Assistant has no local network URL. Set one under Settings → System → Network.",
                                "Home Assistant hat keine lokale Netzwerk-URL. Unter Einstellungen → System → Netzwerk festlegen.",
                            )
                        ),
                    },
                },
            },
            "reprovision_url": {
                "title": L(
                    t("{name} can't reach Home Assistant", "{name} erreicht Home Assistant nicht")
                ),
                "fix_flow": {
                    "step": {
                        "init": {
                            "title": L(t("Update {name}'s URLs", "URLs von {name} aktualisieren")),
                            "description": L(
                                t(
                                    "To update over Bluetooth, press the button on {name} once (it then stays in setup mode for about 30 seconds) and select Submit. A Bluetooth adapter or proxy must be near the frame.\n\nOr enter these in the official web UI:\n\n**Settings URL:** `{settings_url}`\n\n**Image URL:** `{image_url}`",
                                    "Für die Aktualisierung per Bluetooth die Taste an {name} einmal drücken (der Rahmen bleibt dann etwa 30 Sekunden im Einrichtungsmodus) und Absenden wählen. Ein Bluetooth-Adapter oder -Proxy muss in der Nähe sein.\n\nOder diese im offiziellen Web-UI eintragen:\n\n**Settings-URL:** `{settings_url}`\n\n**Bild-URL:** `{image_url}`",
                                )
                            ),
                            "data": {"method": L(t("How", "Wie"))},
                        }
                    },
                    "error": {
                        "not_found": L(
                            t(
                                "The frame wasn't found over Bluetooth. Press its button once and try again.",
                                "Der Rahmen wurde per Bluetooth nicht gefunden. Taste einmal drücken und erneut versuchen.",
                            )
                        ),
                        "ble_failed": L(
                            t(
                                "Couldn't update the frame over Bluetooth. Press its button once and try again.",
                                "Der Rahmen konnte per Bluetooth nicht aktualisiert werden. Taste einmal drücken und erneut versuchen.",
                            )
                        ),
                        "no_bluetooth": L(
                            t(
                                "Bluetooth isn't set up in Home Assistant.",
                                "Bluetooth ist in Home Assistant nicht eingerichtet.",
                            )
                        ),
                        "no_url": L(
                            t(
                                "Home Assistant has no local network URL. Set one under Settings → System → Network.",
                                "Home Assistant hat keine lokale Netzwerk-URL. Unter Einstellungen → System → Netzwerk festlegen.",
                            )
                        ),
                    },
                },
            },
        },
        "device_automation": {
            "trigger_type": {"wake": L(t("Frame woke up", "Rahmen ist aufgewacht"))}
        },
        "entity": {
            "binary_sensor": {
                "in_sync": {"name": L(t("In sync", "Synchron"))},
                "charging": {"name": L(t("Charging", "Lädt"))},
                "usb_power": {"name": L(t("USB power", "USB-Strom"))},
            },
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
                "battery_voltage": {"name": L(t("Battery voltage", "Akkuspannung"))},
                "wifi_signal": {"name": L(t("WiFi signal", "WLAN-Signal"))},
                "orientation": {"name": L(t("Orientation", "Ausrichtung"))},
            },
            "switch": {
                "motion_wakeup": {
                    "name": L(t("Motion wake-up", "Aufwecken durch Bewegung")),
                    "state_attributes": {
                        "suppressed_until": {
                            "name": L(t("Off for quiet hours until", "Wegen Ruhezeit aus bis"))
                        }
                    },
                },
                "auto_rotation": {"name": L(t("Auto rotation", "Automatische Drehung"))},
                "charger_mode": {"name": L(t("Charger mode", "Lademodus"))},
                "telemetry": {"name": L(t("Telemetry", "Telemetrie"))},
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
            "image_too_many_pixels": {
                "message": L(
                    t(
                        "The image has {megapixels} megapixels; at most {limit} are allowed.",
                        "Das Bild hat {megapixels} Megapixel; erlaubt sind höchstens {limit}.",
                    )
                )
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


def _bluetooth(lang: str) -> dict:
    """Strings for Bluetooth sync, status entities and repairs, merged over the base."""
    L = lambda pair: pair[lang]  # noqa: E731
    return {
        "config": {
            "step": {
                "bluetooth_confirm": {
                    "sections": {
                        "wifi": {
                            "name": L(t("WiFi (optional)", "WLAN (optional)")),
                            "description": L(
                                t(
                                    "Set the frame's WiFi network, e.g. for a new frame. Leave empty to keep its current network.",
                                    "WLAN des Rahmens festlegen, z. B. bei einem neuen Rahmen. Leer lassen, um das aktuelle Netzwerk zu behalten.",
                                )
                            ),
                            "data": {
                                "wifi_ssid": L(t("Network name (SSID)", "Netzwerkname (SSID)")),
                                "wifi_password": L(t("Password", "Passwort")),
                            },
                        }
                    }
                }
            },
            "error": {
                "wifi_failed": L(
                    t(
                        "The frame couldn't join that WiFi network. Check the name and password, press the frame's button once, and try again.",
                        "Der Rahmen konnte sich nicht mit diesem WLAN verbinden. Name und Passwort prüfen, Taste einmal drücken und erneut versuchen.",
                    )
                )
            },
        },
        "options": {
            "step": {
                "init": {
                    "data": {
                        "ble_auto": L(
                            t(
                                "Update over Bluetooth in setup mode",
                                "Im Einrichtungsmodus per Bluetooth aktualisieren",
                            )
                        )
                    },
                    "data_description": {
                        "regenerate_token": L(
                            t(
                                "The old URLs stop working immediately. Afterwards, press the frame's button once and Home Assistant updates it over Bluetooth (or use the repair notice).",
                                "Die alten URLs funktionieren sofort nicht mehr. Danach die Taste am Rahmen einmal drücken, dann aktualisiert Home Assistant ihn per Bluetooth (oder über den Reparaturhinweis).",
                            )
                        ),
                        "ble_auto": L(
                            t(
                                "When you press the frame's button once, Home Assistant connects briefly to read battery and charging status and to send pending changes. Turn off if you use the official web UI at the same time.",
                                "Wenn die Taste am Rahmen einmal gedrückt wird, verbindet sich Home Assistant kurz, liest Akku- und Ladestatus und überträgt ausstehende Änderungen. Ausschalten, wenn gleichzeitig das offizielle Web-UI genutzt wird.",
                            )
                        ),
                    },
                }
            }
        },
        "selector": {
            "reprovision_method": {
                "options": {
                    "bluetooth": L(
                        t(
                            "Over Bluetooth (press the frame's button once first)",
                            "Per Bluetooth (zuerst die Taste am Rahmen einmal drücken)",
                        )
                    ),
                    "manual": L(
                        t(
                            "I've entered the URLs in the web UI myself",
                            "Ich habe die URLs selbst im Web-UI eingetragen",
                        )
                    ),
                }
            }
        },
        "entity": {
            "binary_sensor": {
                "charging": {"name": L(t("Charging", "Lädt"))},
                "usb_power": {"name": L(t("USB power", "USB-Strom"))},
            },
            "sensor": {
                "battery_voltage": {"name": L(t("Battery voltage", "Akkuspannung"))},
                "wifi_signal": {"name": L(t("WiFi signal", "WLAN-Signal"))},
            },
        },
    }


def _url_host(lang: str) -> dict:
    """Strings for choosing which address the frame's URLs use."""
    L = lambda pair: pair[lang]  # noqa: E731
    label = L(t("Address the frame uses", "Adresse für den Rahmen"))
    help_text = L(
        t(
            "Which of Home Assistant's addresses goes into the frame's URLs. Automatic uses Home Assistant's local network URL. Pick another IP if Home Assistant is reachable on several networks, or type an IP or hostname the frame can resolve (no .local names).",
            "Welche Adresse von Home Assistant in die URLs des Rahmens kommt. Automatisch verwendet die lokale Netzwerk-URL von Home Assistant. Eine andere IP wählen, wenn Home Assistant in mehreren Netzen erreichbar ist, oder eine IP bzw. einen Hostnamen eingeben, den der Rahmen auflösen kann (keine .local-Namen).",
        )
    )
    errors = {
        "invalid_host": L(
            t(
                "Enter an IP address or hostname, without http:// or a port.",
                "Eine IP-Adresse oder einen Hostnamen ohne http:// und Port eingeben.",
            )
        ),
        "unusable_host": L(
            t(
                "The frame can't use this address (loopback, localhost or a .local name). Choose a LAN IP address.",
                "Der Rahmen kann diese Adresse nicht nutzen (Loopback, localhost oder ein .local-Name). Eine LAN-IP-Adresse wählen.",
            )
        ),
    }
    step = {"data": {"url_host": label}, "data_description": {"url_host": help_text}}
    return {
        "config": {
            "step": {"user": step, "bluetooth_confirm": step},
            "error": errors,
        },
        "options": {
            "step": {
                "init": {
                    **step,
                    "data_description": {
                        "url_host": help_text
                        + L(
                            t(
                                " After changing it, press the frame's button once so Home Assistant can give it the new URLs.",
                                " Nach einer Änderung die Taste am Rahmen einmal drücken, damit Home Assistant ihm die neuen URLs geben kann.",
                            )
                        )
                    },
                }
            },
            "error": errors,
        },
        "selector": {"url_host": {"options": {"auto": L(t("Automatic", "Automatisch"))}}},
    }


def _overlays(lang: str) -> dict:
    """Strings for text and entity overlays."""
    L = lambda pair: pair[lang]  # noqa: E731

    def opts(pairs: dict) -> dict:
        return {"options": {k: L(v) for k, v in pairs.items()}}

    anchors = {
        "top_left": t("Top left", "Oben links"),
        "top_center": t("Top centre", "Oben Mitte"),
        "top_right": t("Top right", "Oben rechts"),
        "center_left": t("Centre left", "Mitte links"),
        "center": t("Centre", "Mitte"),
        "center_right": t("Centre right", "Mitte rechts"),
        "bottom_left": t("Bottom left", "Unten links"),
        "bottom_center": t("Bottom centre", "Unten Mitte"),
        "bottom_right": t("Bottom right", "Unten rechts"),
    }
    colors = {
        "black": t("Black", "Schwarz"),
        "white": t("White", "Weiß"),
        "red": t("Red", "Rot"),
        "green": t("Green", "Grün"),
        "blue": t("Blue", "Blau"),
        "yellow": t("Yellow", "Gelb"),
    }
    fields = {
        "config_entry_id": (
            t("Frame", "Rahmen"),
            t("The frame to act on.", "Der betroffene Rahmen."),
        ),
        "target_config_entry_id": (
            t("Target frame", "Zielrahmen"),
            t(
                "Frame to copy the frame's overlays to. Leave empty when copying a photo's overlays.",
                "Rahmen, in den die Overlays des Rahmens kopiert werden. Leer lassen, wenn die Overlays eines Fotos kopiert werden.",
            ),
        ),
        "photo_id": (
            t("Photo ID", "Foto-ID"),
            t(
                "Acts on this photo's own overlays. Leave empty for the frame's global photo overlays. ID of the photo (see the list photos action).",
                "Nur für Overlays dieses Fotos; ohne Angabe gilt die Liste des Rahmens (globale Foto-Overlays). ID des Fotos (siehe Aktion Fotos auflisten).",
            ),
        ),
        "overlay_id": (
            t("Overlay ID", "Overlay-ID"),
            t(
                "ID of the overlay (see the list overlays action).",
                "ID des Overlays (siehe Aktion „Overlays auflisten“).",
            ),
        ),
        "name": (t("Name", "Name"), t("Name shown in the panel.", "Im Panel angezeigter Name.")),
        "template": (
            t("Text", "Text"),
            t(
                "Markdown with Home Assistant templates, e.g. :mdi:thermometer: **{{ states('sensor.outdoor') }} °C**.",
                "Markdown mit Home-Assistant-Templates, z. B. :mdi:thermometer: **{{ states('sensor.outdoor') }} °C**.",
            ),
        ),
        "show_if": (
            t("Show if", "Anzeigen wenn"),
            t(
                "Optional template; the overlay is only drawn when it renders to something truthy.",
                "Optionales Template; das Overlay wird nur gezeichnet, wenn es etwas Wahres ergibt.",
            ),
        ),
        "enabled": (
            t("Enabled", "Aktiv"),
            t("Whether the overlay is drawn.", "Ob das Overlay gezeichnet wird."),
        ),
        "anchor": (
            t("Position", "Position"),
            t("Where the box sits on the frame.", "Wo die Box auf dem Rahmen sitzt."),
        ),
        "size": (
            t("Text size", "Textgröße"),
            t(
                "Scaled to the panel, so it looks the same on every frame.",
                "Passt sich dem Panel an, damit es auf jedem Rahmen gleich aussieht.",
            ),
        ),
        "width": (
            t("Width", "Breite"),
            t(
                "Box width in percent of the frame; empty to fit the text.",
                "Boxbreite in Prozent des Rahmens; leer, um sich dem Text anzupassen.",
            ),
        ),
        "margin": (
            t("Margin", "Abstand"),
            t(
                "Distance from the edge, as a fraction of the frame's short side.",
                "Abstand zum Rand als Anteil der kurzen Rahmenseite.",
            ),
        ),
        "align": (
            t("Alignment", "Ausrichtung"),
            t("Text alignment inside the box.", "Textausrichtung in der Box."),
        ),
        "text_color": (
            t("Text colour", "Textfarbe"),
            t(
                "Default text colour; colour spans override it.",
                "Standard-Textfarbe; Farbmarkierungen überschreiben sie.",
            ),
        ),
        "backing": (
            t("Backing", "Hintergrund"),
            t(
                "What sits behind the text for readability.",
                "Was für die Lesbarkeit hinter dem Text liegt.",
            ),
        ),
        "backing_color": (
            t("Box colour", "Boxfarbe"),
            t("Colour of the box behind the text.", "Farbe der Box hinter dem Text."),
        ),
        "redraw": (
            t("Update", "Aktualisieren"),
            t(
                "When changed values are sent to the frame.",
                "Wann geänderte Werte an den Rahmen gesendet werden.",
            ),
        ),
        "position": (
            t("Position", "Position"),
            t(
                "New 0-based position in the drawing order.",
                "Neue Position in der Zeichenreihenfolge (ab 0).",
            ),
        ),
        "replace": (
            t("Replace", "Ersetzen"),
            t(
                "Replace the target frame's overlays instead of adding to them.",
                "Die Overlays des Zielrahmens ersetzen statt sie zu ergänzen.",
            ),
        ),
    }
    services = {
        "add_overlay": (
            t("Add overlay", "Overlay hinzufügen"),
            t(
                "Adds a global photo overlay (a text box drawn over every photo of a frame), or with a photo ID, a photo overlay for that one photo.",
                "Fügt ein globales Foto-Overlay hinzu (eine Textbox über jedem Foto eines Rahmens) oder, mit Foto-ID, ein Foto-Overlay nur für dieses Foto.",
            ),
            [
                "config_entry_id",
                "photo_id",
                "name",
                "template",
                "show_if",
                "enabled",
                "anchor",
                "size",
                "width",
                "margin",
                "align",
                "text_color",
                "backing",
                "backing_color",
                "redraw",
            ],
        ),
        "update_overlay": (
            t("Update overlay", "Overlay bearbeiten"),
            t("Changes an overlay.", "Ändert ein Overlay."),
            [
                "config_entry_id",
                "photo_id",
                "overlay_id",
                "name",
                "template",
                "show_if",
                "enabled",
                "anchor",
                "size",
                "width",
                "margin",
                "align",
                "text_color",
                "backing",
                "backing_color",
                "redraw",
            ],
        ),
        "remove_overlay": (
            t("Remove overlay", "Overlay entfernen"),
            t("Deletes an overlay.", "Löscht ein Overlay."),
            ["config_entry_id", "photo_id", "overlay_id"],
        ),
        "move_overlay": (
            t("Move overlay", "Overlay verschieben"),
            t(
                "Changes an overlay's place in the drawing order.",
                "Ändert die Position eines Overlays in der Zeichenreihenfolge.",
            ),
            ["config_entry_id", "photo_id", "overlay_id", "position"],
        ),
        "copy_overlays": (
            t("Copy overlays to frame", "Overlays in Rahmen kopieren"),
            t(
                "Copies the frame's global photo overlays to another frame, or a photo's overlays to other photos of the same frame.",
                "Kopiert die globalen Foto-Overlays eines Rahmens in einen anderen Rahmen, oder die Overlays eines Fotos in andere Fotos desselben Rahmens.",
            ),
            ["config_entry_id", "target_config_entry_id", "photo_id", "to_photo_ids", "replace"],
        ),
        "list_overlays": (
            t("List overlays", "Overlays auflisten"),
            t(
                "Returns a frame's global photo overlays, or one photo's overlays, with their last text and error.",
                "Gibt die globalen Foto-Overlays eines Rahmens oder die Overlays eines Fotos mit letztem Text und Fehler zurück.",
            ),
            ["config_entry_id", "photo_id"],
        ),
    }
    # Fields whose texts differ from the shared ones for one action.
    copy_texts = {
        "photo_id": (
            t("Source photo ID", "Quell-Foto-ID"),
            t(
                "Copy this photo's overlays instead of the frame's overlays.",
                "Kopiert die Overlays dieses Fotos statt der Overlays des Rahmens.",
            ),
        ),
        "to_photo_ids": (
            t("Target photo IDs", "Ziel-Foto-IDs"),
            t(
                "Photos of the same frame to copy the source photo's overlays to.",
                "Fotos desselben Rahmens, in die die Overlays des Quellfotos kopiert werden.",
            ),
        ),
    }
    field_texts = {name: (copy_texts if name == "copy_overlays" else {}) for name in services}
    return {
        "selector": {
            "overlay_anchor": opts(anchors),
            "overlay_size": opts(
                {
                    "s": t("Small", "Klein"),
                    "m": t("Medium", "Mittel"),
                    "l": t("Large", "Groß"),
                    "xl": t("Extra large", "Sehr groß"),
                    "xxl": t("Huge", "Riesig"),
                }
            ),
            "overlay_align": opts(
                {
                    "left": t("Left", "Links"),
                    "center": t("Centre", "Mitte"),
                    "right": t("Right", "Rechts"),
                }
            ),
            "overlay_color": opts(colors),
            "overlay_backing": opts(
                {
                    "box": t("Box", "Box"),
                    "halo": t("Outline around letters", "Kontur um die Buchstaben"),
                    "none": t("Nothing", "Nichts"),
                }
            ),
            "overlay_redraw": opts(
                {
                    "change": t(
                        "Every wake when the text changed",
                        "Bei jedem Aufwachen, wenn sich der Text geändert hat",
                    ),
                    "photo": t("Only when the photo changes", "Nur wenn das Foto wechselt"),
                }
            ),
        },
        "exceptions": {
            "copy_overlays_needs_targets": {
                "message": L(
                    t(
                        "Give a target frame, or a source photo together with target photos.",
                        "Gib einen Zielrahmen an, oder ein Quellfoto zusammen mit Zielfotos.",
                    )
                )
            },
            "overlay_not_found": {
                "message": L(
                    t("Overlay {overlay_id} not found.", "Overlay {overlay_id} nicht gefunden.")
                )
            },
        },
        "services": {
            **{
                name: {
                    "name": L(title),
                    "description": L(desc),
                    "fields": {
                        f: {
                            "name": L((field_texts[name].get(f) or fields[f])[0]),
                            "description": L((field_texts[name].get(f) or fields[f])[1]),
                        }
                        for f in names
                    },
                }
                for name, (title, desc, names) in services.items()
            },
            "show_image": {
                "fields": {
                    "overlays": {
                        "name": L(t("Overlays", "Overlays")),
                        "description": L(
                            t(
                                "Draw the frame's overlays on this image. Off shows the bare image.",
                                "Die Overlays des Rahmens auf dieses Bild zeichnen. Aus zeigt das reine Bild.",
                            )
                        ),
                    }
                }
            },
            "update_photo": {
                "fields": {
                    "hide_frame_overlays": {
                        "name": L(t("Hide frame overlays", "Rahmen-Overlays ausblenden")),
                        "description": L(
                            t(
                                "Don't draw the frame's overlays on this photo.",
                                "Die Overlays des Rahmens nicht auf diesem Foto zeichnen.",
                            )
                        ),
                    }
                }
            },
        },
    }


def _cards(lang: str) -> dict:
    """Strings for text cards."""
    L = lambda pair: pair[lang]  # noqa: E731
    background = (
        t("Background", "Hintergrund"),
        t(
            "A colour, or 'photo' to draw the card on a photo of this frame.",
            "Eine Farbe, oder „Foto“, um die Karte auf ein Foto dieses Rahmens zu zeichnen.",
        ),
    )
    background_photo = (
        t("Background photo ID", "Hintergrundfoto-ID"),
        t(
            "The photo a card with a photo background is drawn on, with that photo's settings.",
            "Das Foto, auf das eine Karte mit Foto-Hintergrund gezeichnet wird, mit dessen Einstellungen.",
        ),
    )

    def field(pair: tuple) -> dict:
        return {"name": L(pair[0]), "description": L(pair[1])}

    return {
        "selector": {
            "card_preset": {
                "options": {
                    "blank": L(t("Blank", "Leer")),
                    "info": L(t("Info: a title and values", "Info: ein Titel und Werte")),
                    "notice": L(t("Notice: one big message", "Hinweis: eine große Nachricht")),
                }
            },
            "card_background": {
                "options": {
                    "white": L(t("White", "Weiß")),
                    "black": L(t("Black", "Schwarz")),
                    "red": L(t("Red", "Rot")),
                    "green": L(t("Green", "Grün")),
                    "blue": L(t("Blue", "Blau")),
                    "yellow": L(t("Yellow", "Gelb")),
                    "photo": L(t("Photo", "Foto")),
                }
            },
        },
        "exceptions": {
            "invalid_card_background": {
                "message": L(
                    t(
                        "A photo background needs the ID of a photo (not a card) of this frame.",
                        "Ein Foto-Hintergrund braucht die ID eines Fotos (keiner Karte) dieses Rahmens.",
                    )
                )
            },
            "card_has_no_render_settings": {
                "message": L(
                    t(
                        "Cards have no render settings; change the background instead.",
                        "Karten haben keine Darstellungseinstellungen; stattdessen den Hintergrund ändern.",
                    )
                )
            },
            "not_a_card": {
                "message": L(
                    t(
                        "{photo_id} is a photo: its background is white or black, and only cards have a background photo.",
                        "{photo_id} ist ein Foto: sein Hintergrund ist Weiß oder Schwarz, und nur Karten haben ein Hintergrundfoto.",
                    )
                )
            },
        },
        "services": {
            "add_card": {
                "name": L(t("Add card", "Karte hinzufügen")),
                "description": L(
                    t(
                        "Adds a text card to a frame's library. Its text is its overlays; edit them with the overlay actions and the card's photo ID.",
                        "Fügt der Bibliothek eines Rahmens eine Textkarte hinzu. Ihr Text sind ihre Overlays; diese mit den Overlay-Aktionen und der Foto-ID der Karte bearbeiten.",
                    )
                ),
                "fields": {
                    "config_entry_id": field(FIELDS["config_entry_id"]),
                    "name": field(FIELDS["name"]),
                    "preset": field(
                        (
                            t("Preset", "Vorlage"),
                            t(
                                "What the card starts with, in Home Assistant's language.",
                                "Womit die Karte beginnt, in der Sprache von Home Assistant.",
                            ),
                        )
                    ),
                    "background": field(background),
                    "background_photo_id": field(background_photo),
                },
            },
            "update_photo": {
                "fields": {
                    "background": field(
                        (
                            t("Background", "Hintergrund"),
                            t(
                                "On a photo: the border colour for 'fit with borders' (white or black). On a card: its background.",
                                "Bei einem Foto: die Randfarbe für „Einpassen mit Rand“ (Weiß oder Schwarz). Bei einer Karte: ihr Hintergrund.",
                            ),
                        )
                    ),
                    "background_photo_id": field(background_photo),
                }
            },
        },
    }


def _show_text(lang: str) -> dict:
    """Strings for show_text."""
    L = lambda pair: pair[lang]  # noqa: E731

    def field(name: tuple, desc: tuple) -> dict:
        return {"name": L(name), "description": L(desc)}

    return {
        "services": {
            "show_text": {
                "name": L(t("Show text", "Text anzeigen")),
                "description": L(
                    t(
                        "Shows a one-off text instead of the slideshow, like a card that is not in the library. It is evaluated again on every wake and replaces a one-off image.",
                        "Zeigt einen einmaligen Text statt der Diashow, wie eine Karte, die nicht in der Bibliothek ist. Er wird bei jedem Aufwachen neu ausgewertet und ersetzt ein einmaliges Bild.",
                    )
                ),
                "fields": {
                    "config_entry_id": field(*FIELDS["config_entry_id"]),
                    "text": field(
                        t("Text", "Text"),
                        t(
                            "Markdown with Home Assistant templates; the variable photo is empty.",
                            "Markdown mit Home-Assistant-Templates; die Variable photo ist leer.",
                        ),
                    ),
                    "name": field(
                        t("Name", "Name"),
                        t(
                            "Shown in Home Assistant while the text is on the frame. Default: its first line.",
                            "Wird in Home Assistant angezeigt, solange der Text auf dem Rahmen ist. Standard: seine erste Zeile.",
                        ),
                    ),
                    "background": field(
                        t("Background", "Hintergrund"),
                        t(
                            "White, black or a panel colour. The text is white on dark colours.",
                            "Weiß, Schwarz oder eine Panelfarbe. Auf dunklen Farben ist der Text weiß.",
                        ),
                    ),
                    "size": field(
                        t("Text size", "Textgröße"),
                        t(
                            "Scaled to the panel, so it looks the same on every frame.",
                            "Passt sich dem Panel an, damit es auf jedem Rahmen gleich aussieht.",
                        ),
                    ),
                    "anchor": field(
                        t("Position", "Position"),
                        t("Where the text sits on the frame.", "Wo der Text auf dem Rahmen sitzt."),
                    ),
                    "align": field(
                        t("Alignment", "Ausrichtung"),
                        t("Alignment of the text lines.", "Ausrichtung der Textzeilen."),
                    ),
                    "wakes": field(*FIELDS["wakes"]),
                    "overlays": field(
                        t("Overlays", "Overlays"),
                        t(
                            "Draw the frame's overlays over the text. Off shows the text only.",
                            "Die Overlays des Rahmens über den Text zeichnen. Aus zeigt nur den Text.",
                        ),
                    ),
                },
            },
        },
    }


def _merge(base: dict, extra: dict) -> dict:
    for key, value in extra.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _merge(base[key], value)
        else:
            base[key] = value
    return base


def build(lang: str) -> dict:
    merged = _merge(_merge(_build_base(lang), _bluetooth(lang)), _url_host(lang))
    merged = _merge(_merge(merged, _overlays(lang)), _cards(lang))
    return _merge(merged, _show_text(lang))


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
