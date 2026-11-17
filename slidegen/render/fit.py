"""Make text fit its box.

v1 used a fixed 18 pt for everything, so long titles ran into the bullets.
Here we MEASURE text with real font metrics (Carlito has exactly the same
letter widths as Calibri), wrap it like PowerPoint does, and pick the
largest font size that fits. If even the smallest size doesn't fit, we
report an overflow so the quality check can flag it.
"""
from functools import lru_cache
import os

from PIL import ImageFont

FONT_DIRS = ["/usr/share/fonts/truetype/crosextra", "/usr/share/fonts/truetype/carlito",
             "/Library/Fonts", "C:/Windows/Fonts", os.path.join(os.path.dirname(__file__), "fonts")]
FONT_FILES = {False: ["Carlito-Regular.ttf", "calibri.ttf", "Calibri.ttf"],
              True: ["Carlito-Bold.ttf", "calibrib.ttf", "Calibri Bold.ttf"]}
LINE_SPACING = 1.2


@lru_cache(maxsize=4)
def _font(bold: bool):
    for d in FONT_DIRS:
        for f in FONT_FILES[bold]:
            p = os.path.join(d, f)
            if os.path.exists(p):
                return ImageFont.truetype(p, 100)
    return None  # no font file: fall back to an average-width estimate


def text_width(text: str, size_pt: float, bold: bool = False) -> float:
    """Width of one line of text in points."""
    f = _font(bold)
    if f is None:
        return len(text) * size_pt * (0.53 if bold else 0.5)
    return f.getlength(text) * size_pt / 100


def count_lines(text: str, width_pt: float, size_pt: float, bold: bool = False) -> int:
    """Greedy word wrap, like PowerPoint."""
    lines = 0
    for para in text.split("\n"):
        line = ""
        lines += 1
        for word in para.split():
            trial = f"{line} {word}".strip()
            if text_width(trial, size_pt, bold) <= width_pt or not line:
                line = trial
            else:
                lines += 1
                line = word
    return lines


def block_height(paragraphs, width_pt, size_pt, bold=False, para_gap=0.5, indent_pt=0.0) -> float:
    """Height in points of several paragraphs (para_gap is in lines)."""
    lines = sum(count_lines(p, width_pt - indent_pt, size_pt, bold) for p in paragraphs)
    gaps = max(len(paragraphs) - 1, 0) * para_gap
    return (lines + gaps) * size_pt * LINE_SPACING


def fit_size(paragraphs, width_in, height_in, max_pt, min_pt, bold=False, para_gap=0.5, indent_ratio=0.0):
    """Largest size in [min_pt, max_pt] that fits. Returns (size, fits)."""
    w, h = width_in * 72, height_in * 72
    size = max_pt
    while size >= min_pt:
        if block_height(paragraphs, w, size, bold, para_gap, indent_ratio * size) <= h:
            return size, True
        size -= 1
    return min_pt, False
