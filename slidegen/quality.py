"""Automatic quality report for a generated deck.

Checks that a human reviewer would do, turned into numbers:
* text fit       - did any text overflow its box?
* density        - bullets per slide, words per bullet
* grounding      - share of content slides that cite a source; fixes the guard made
* variety        - how many different layouts were used
* reliability    - how many LLM attempts were needed (repair loop)
"""
from .grounding import slide_citations
from .schema import BulletsSlide, Deck, SectionSlide, TitleSlide, TwoColumnSlide


def quality_report(deck: Deck, render: dict, fixes: list, llm_log: list, sources) -> dict:
    content = [s for s in deck.slides if not isinstance(s, (TitleSlide, SectionSlide))]
    bullets = [b for s in deck.slides if isinstance(s, BulletsSlide) for b in s.bullets]
    bullets += [b for s in deck.slides if isinstance(s, TwoColumnSlide) for b in s.left + s.right]
    words = [len(b.text.split()) for b in bullets]
    cited = sum(1 for s in content if slide_citations(s))
    types = {s.type for s in deck.slides}
    attempts = sum(1 for e in llm_log if "attempt" in e)
    calls = sum(1 for e in llm_log if e.get("ok"))

    r = {
        "slides": render.get("slides"),
        "layouts_used": sorted(types),
        "sources_found": len(sources),
        "content_slides_with_citation": f"{cited}/{len(content)}",
        "max_bullets_on_a_slide": max((len(s.bullets) for s in deck.slides if isinstance(s, BulletsSlide)), default=0),
        "avg_words_per_bullet": round(sum(words) / len(words), 1) if words else 0,
        "long_bullets_over_20_words": sum(w > 20 for w in words),
        "text_overflows": render.get("overflows", []),
        "photos": render.get("photos", 0),
        "grounding_fixes": fixes,
        "llm_attempts": f"{attempts} for {calls} steps",
        "speaker_notes": f"{sum(1 for s in deck.slides if s.notes)}/{len(deck.slides)}",
    }
    # Simple 0-100 score so different decks/prompts can be compared.
    score = 100
    score -= 10 * len(r["text_overflows"])
    score -= 5 * r["long_bullets_over_20_words"]
    score -= 5 * len(fixes)
    score -= 10 * max(0, 3 - len(types))                      # too few layouts = boring deck
    if content and sources:
        score -= int(30 * (1 - cited / len(content)))         # uncited content
    score -= 5 * max(0, attempts - calls)                     # each repair costs a little
    r["score"] = max(score, 0)
    return r
