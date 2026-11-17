"""Colour themes. Slides are drawn from scratch, so no template file is needed."""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Theme:
    name: str
    bg: str
    surface: str      # cards
    text: str
    muted: str
    accent: str
    accent2: str
    on_accent: str    # text colour on top of the accent colour
    chart: tuple = field(default=())
    dark: bool = False
    font: str = "Calibri"   # measured with Carlito (same letter widths) for text fitting


THEMES = {
    "midnight": Theme("midnight", bg="0F172A", surface="1E293B", text="F1F5F9", muted="94A3B8",
                      accent="38BDF8", accent2="F472B6", on_accent="0F172A",
                      chart=("38BDF8", "F472B6", "A3E635"), dark=True),
    "paper": Theme("paper", bg="FFFFFF", surface="F1F5F9", text="0F172A", muted="64748B",
                   accent="4F46E5", accent2="F59E0B", on_accent="FFFFFF",
                   chart=("4F46E5", "F59E0B", "10B981")),
    "forest": Theme("forest", bg="F7F5EF", surface="E9E5D8", text="1F2A1F", muted="5F6B57",
                    accent="2F855A", accent2="C05621", on_accent="FFFFFF",
                    chart=("2F855A", "C05621", "2B6CB0")),
    "sunset": Theme("sunset", bg="1C1917", surface="292524", text="FAFAF9", muted="A8A29E",
                    accent="F97316", accent2="FACC15", on_accent="1C1917",
                    chart=("F97316", "FACC15", "60A5FA"), dark=True),
}


def get_theme(name: str) -> Theme:
    try:
        return THEMES[name]
    except KeyError:
        raise ValueError(f"unknown theme {name!r}; choose from {', '.join(THEMES)}")
