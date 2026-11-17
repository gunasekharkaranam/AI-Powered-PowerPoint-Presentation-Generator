"""Grounding guard: rules applied AFTER the LLM answers, so the deck never
shows a number that no source supports.

1. Remove citation ids that don't exist in the source list.
2. A chart or stats slide with no valid citation is turned into a bullets
   slide (the numbers are dropped). The model may have invented them.
Every change is recorded so the quality report can show it.
"""
from .schema import (BulletsSlide, Bullet, ChartSlide, Deck, QuoteSlide, StatsSlide,
                     TimelineSlide, TwoColumnSlide)


def _clean(ids, valid):
    return [i for i in dict.fromkeys(ids) if i in valid]


def ground_deck(deck: Deck, sources) -> tuple[Deck, list[str]]:
    valid = {s.id for s in sources}
    fixes, slides = [], []
    for n, s in enumerate(deck.slides, start=1):
        if isinstance(s, BulletsSlide):
            for b in s.bullets:
                b.citations = _clean(b.citations, valid)
        elif isinstance(s, TwoColumnSlide):
            for b in s.left + s.right:
                b.citations = _clean(b.citations, valid)
        elif isinstance(s, TimelineSlide):
            for e in s.events:
                e.citations = _clean(e.citations, valid)
        elif isinstance(s, QuoteSlide):
            s.citations = _clean(s.citations, valid)
            if not s.citations:
                fixes.append(f"slide {n}: quote has no source - kept, but marked unverified")
        elif isinstance(s, StatsSlide):
            for st in s.stats:
                st.citations = _clean(st.citations, valid)
            if not any(st.citations for st in s.stats):
                fixes.append(f"slide {n}: stats had no source - numbers removed, shown as bullets")
                s = BulletsSlide(title=s.title, notes=s.notes,
                                 bullets=[Bullet(text=st.label) for st in s.stats])
        elif isinstance(s, ChartSlide):
            s.citations = _clean(s.citations, valid)
            ok_shape = all(len(se.values) == len(s.categories) for se in s.series)
            if not s.citations or not ok_shape:
                why = "no source" if not s.citations else "data shape mismatch"
                fixes.append(f"slide {n}: chart removed ({why}) - kept its takeaway as text")
                s = BulletsSlide(title=s.title, notes=s.notes, bullets=[Bullet(text=s.takeaway)])
        slides.append(s)
    return Deck(title=deck.title, subtitle=deck.subtitle, slides=slides), fixes


def used_source_ids(deck: Deck) -> list[int]:
    ids = []
    for s in deck.slides:
        ids += slide_citations(s)
    return sorted(set(ids))


def slide_citations(s) -> list[int]:
    if isinstance(s, BulletsSlide):
        return [c for b in s.bullets for c in b.citations]
    if isinstance(s, TwoColumnSlide):
        return [c for b in s.left + s.right for c in b.citations]
    if isinstance(s, StatsSlide):
        return [c for st in s.stats for c in st.citations]
    if isinstance(s, TimelineSlide):
        return [c for e in s.events for c in e.citations]
    if isinstance(s, (ChartSlide, QuoteSlide)):
        return list(s.citations)
    return []
