"""Generate decks for several topics and compare their quality reports.

    python -m scripts.evaluate                       # uses your API key
    python -m scripts.evaluate --provider demo       # offline check

Use it to compare prompts, models or providers with numbers instead of opinions.
"""
import argparse
import json
from pathlib import Path

from slidegen.llm import get_llm
from slidegen.pipeline import Request, SlideGen

TOPICS = ["Climate change: evidence and action", "How large language models work",
          "The history of the Indian space programme", "Microplastics and human health",
          "Electric vehicles vs petrol cars"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider")
    ap.add_argument("--slides", type=int, default=8)
    a = ap.parse_args()
    out = Path("out")
    out.mkdir(exist_ok=True)
    gen = SlideGen(llm=get_llm(a.provider))
    rows = []
    for t in TOPICS:
        _, r = gen.run(Request(t, n_slides=a.slides), str(out / (t[:30].replace(" ", "_") + ".pptx")),
                       progress=lambda m: None)
        rows.append({"topic": t, **{k: r[k] for k in ("score", "slides", "content_slides_with_citation",
                                                        "avg_words_per_bullet", "llm_attempts", "seconds")},
                     "overflows": len(r["text_overflows"]), "fixes": len(r["grounding_fixes"]),
                     "layouts": len(r["layouts_used"])})
        print(json.dumps(rows[-1]))
    (out / "evaluation.json").write_text(json.dumps(rows, indent=2))
    print(f"\naverage score: {sum(r['score'] for r in rows) / len(rows):.1f}")


if __name__ == "__main__":
    main()
