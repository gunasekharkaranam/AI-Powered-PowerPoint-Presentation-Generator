"""Command line:  python -m slidegen "Climate change" -n 8 --theme paper"""
import argparse
import json
import re

from .llm import get_llm
from .pipeline import Request, SlideGen
from .render.themes import THEMES


def main():
    ap = argparse.ArgumentParser(description="AI presentation generator")
    ap.add_argument("topic")
    ap.add_argument("-n", "--slides", type=int, default=8, help="number of content slides (3-15)")
    ap.add_argument("--audience", default="general audience")
    ap.add_argument("--tone", default="clear and professional")
    ap.add_argument("--theme", default="midnight", choices=list(THEMES))
    ap.add_argument("--provider", choices=["gemini", "openai", "demo"], help="default: first one with a key")
    ap.add_argument("--no-images", action="store_true")
    ap.add_argument("--no-research", action="store_true")
    ap.add_argument("-o", "--out", help="output .pptx path")
    a = ap.parse_args()

    req = Request(a.topic, a.audience, max(3, min(a.slides, 15)), a.tone, a.theme,
                  images=not a.no_images, web_research=not a.no_research)
    out = a.out or re.sub(r"[^\w-]+", "_", a.topic).strip("_")[:60] + ".pptx"
    llm = get_llm(a.provider)
    print(f"Provider: {llm.name}")
    deck, report = SlideGen(llm=llm).run(req, out, progress=lambda m: print("  " + m))
    print(f"\nSaved {out}\nQuality report:\n{json.dumps(report, indent=2)}")


if __name__ == "__main__":
    main()
