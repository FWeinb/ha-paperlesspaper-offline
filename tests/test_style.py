"""Repository-wide writing conventions (see docs/DESIGN.md, Writing conventions)."""

from __future__ import annotations

from pathlib import Path
import subprocess

ROOT = Path(__file__).parents[1]
FORBIDDEN = {chr(0x2013): "en dash", chr(0x2014): "em dash"}  # built with chr() on purpose
TEXT_SUFFIXES = {
    ".py",
    ".ts",
    ".js",
    ".json",
    ".yaml",
    ".yml",
    ".md",
    ".html",
    ".mjs",
    ".toml",
    ".txt",
}


def _tracked_text_files() -> list[Path]:
    out = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return [ROOT / name for name in out.splitlines() if Path(name).suffix in TEXT_SUFFIXES]


def test_no_en_or_em_dashes() -> None:
    offenders = []
    for path in _tracked_text_files():
        if not path.is_file():
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for char, name in FORBIDDEN.items():
                if char in line:
                    offenders.append(f"{path.relative_to(ROOT)}:{number}: {name}")
    assert not offenders, "Rephrase instead of using dashes:\n" + "\n".join(offenders)
