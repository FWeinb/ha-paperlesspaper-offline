"""Build the bundled fonts used for on-frame text (placeholder screen, overlays).

Sources:
- Noto Sans and Noto Sans Italic variable fonts from https://github.com/google/fonts
  (ofl/notosans, SIL Open Font License 1.1). Static Regular, Bold, Italic and
  Bold Italic instances are cut and subset to Latin (Basic, Latin-1, Extended-A)
  plus punctuation and the symbols sensor values need.
- Noto Sans Math (same repository, ofl/notosansmath) as a fallback for the
  arrows, maths and shape symbols Noto Sans doesn't contain.
- Material Design Icons webfont from the npm package @mdi/font and the icon
  names from @mdi/svg (meta.json), both Apache 2.0. The icon font is copied as
  is (any icon may be used), and a name to codepoint map is generated.

    uv pip install fonttools
    npm pack @mdi/font@7.4.47 @mdi/svg@7.4.47   # then extract both
    python tools/build_fonts.py NotoSans[wdth,wght].ttf NotoSans-Italic[wdth,wght].ttf \\
        NotoSansMath-Regular.ttf mdi-font/package mdi-svg/package
"""

import json
from pathlib import Path
import shutil
import sys

from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

OUT = Path(__file__).parents[1] / "custom_components/paperlessoffline/render/fonts"
UNICODES = [
    *range(0x20, 0x7F),  # Basic Latin
    *range(0xA0, 0x180),  # Latin-1 Supplement (° ± × ÷ µ ² ³ ¼ ½ ¾), Latin Extended-A
    *range(0x2010, 0x2028),  # dashes, quotes, bullet, ellipsis
    *range(0x2030, 0x203B),  # per mille, angle quotes
    *range(0x2070, 0x209D),  # superscripts and subscripts
    *range(0x20A0, 0x20C1),  # currency
    0x2103,  # degree Celsius
    0x2109,  # degree Fahrenheit
    0x2116,  # numero
    0x2122,  # trade mark
    *range(0x2150, 0x2160),  # fractions
    *range(0x2190, 0x219A),  # arrows
    0x2212,  # minus
    0x2215,  # division slash
    0x221E,  # infinity
    0x2248,  # almost equal
    0x2260,  # not equal
    0x2264,  # less than or equal
    0x2265,  # greater than or equal
    *range(0x25B2, 0x25BE),  # triangles
    0x25CF,  # black circle
]
STYLES = (("Regular", 0, 400), ("Bold", 0, 700), ("Italic", 1, 400), ("BoldItalic", 1, 700))


def build_noto(upright: Path, italic: Path) -> None:
    sources = (upright, italic)
    for name, source, weight in STYLES:
        font = instancer.instantiateVariableFont(
            TTFont(sources[source]), {"wght": weight, "wdth": 100}
        )
        _subset(font, OUT / f"NotoSans-{name}.ttf")


def _subset(font: TTFont, target: Path) -> None:
    options = subset.Options()
    options.layout_features = ["kern", "liga"]
    options.name_IDs = ["*"]
    subsetter = subset.Subsetter(options)
    subsetter.populate(unicodes=UNICODES)
    subsetter.subset(font)
    font.save(target)
    print(target, target.stat().st_size)


def build_fallback(math: Path) -> None:
    _subset(TTFont(math), OUT / "NotoSansMath-Regular.ttf")


def write_coverage() -> None:
    """Which codepoints each text font has, so the renderer can fall back per character."""
    coverage = {}
    for path in sorted(OUT.glob("NotoSans*.ttf")):
        coverage[path.name] = sorted(TTFont(path).getBestCmap())
    target = OUT / "coverage.json"
    target.write_text(json.dumps(coverage, separators=(",", ":")))
    print(target)


def build_mdi(font_package: Path, svg_package: Path) -> None:
    shutil.copyfile(
        font_package / "fonts/materialdesignicons-webfont.ttf", OUT / "MaterialDesignIcons.ttf"
    )
    shutil.copyfile(font_package / "LICENSE", OUT / "MaterialDesignIcons-LICENSE.txt")
    meta = json.loads((svg_package / "meta.json").read_text())
    codepoints: dict[str, int] = {}
    for icon in meta:
        codepoint = int(icon["codepoint"], 16)
        codepoints[icon["name"]] = codepoint
        for alias in icon.get("aliases", []):
            codepoints.setdefault(alias, codepoint)
    target = OUT / "mdi-codepoints.json"
    target.write_text(json.dumps(codepoints, separators=(",", ":"), sort_keys=True))
    print(target, len(codepoints), "icons")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    build_noto(Path(sys.argv[1]), Path(sys.argv[2]))
    build_fallback(Path(sys.argv[3]))
    write_coverage()
    build_mdi(Path(sys.argv[4]), Path(sys.argv[5]))
