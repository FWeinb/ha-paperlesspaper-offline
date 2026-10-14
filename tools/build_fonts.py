"""Build the bundled fonts used for on-frame text (placeholder screen).

Source: Noto Sans variable font from https://github.com/google/fonts
(ofl/notosans, SIL Open Font License 1.1). Static Regular and Bold instances
are cut and subset to Latin (Basic, Latin-1, Extended-A) plus common
punctuation to keep the integration small.

    uv pip install fonttools
    python tools/build_fonts.py path/to/NotoSans[wdth,wght].ttf
"""

from pathlib import Path
import sys

from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

OUT = Path(__file__).parents[1] / "custom_components/paperlessoffline/render/fonts"
UNICODES = [
    *range(0x20, 0x7F),  # Basic Latin
    *range(0xA0, 0x180),  # Latin-1 Supplement, Latin Extended-A
    *range(0x2010, 0x2028),  # dashes, quotes, bullet, ellipsis
    0x20AC,  # euro
    0x2192,  # rightwards arrow
]


def build(source: Path) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, weight in (("Regular", 400), ("Bold", 700)):
        font = instancer.instantiateVariableFont(TTFont(source), {"wght": weight, "wdth": 100})
        options = subset.Options()
        options.layout_features = ["kern", "liga"]
        options.name_IDs = ["*"]
        subsetter = subset.Subsetter(options)
        subsetter.populate(unicodes=UNICODES)
        subsetter.subset(font)
        target = OUT / f"NotoSans-{name}.ttf"
        font.save(target)
        print(target, target.stat().st_size)


if __name__ == "__main__":
    build(Path(sys.argv[1]))
