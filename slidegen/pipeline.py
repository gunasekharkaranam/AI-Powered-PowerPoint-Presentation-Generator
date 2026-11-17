"""The whole flow, in two steps so a human can review the plan:

  1. plan(topic)          research -> outline           (user can edit the outline)
  2. build(outline, ...)  write slides -> ground -> render -> quality report
"""
from dataclasses import dataclass, field
import time

from .demo import demo_sources
from .grounding import ground_deck
from .llm import generate_structured, get_llm
from .prompts import SYSTEM, deck_prompt, outline_prompt
from .quality import quality_report
from .render.builder import DeckBuilder
from .render.images import openverse_photo
from .render.themes import get_theme
from .research import research
from .schema import Deck, Outline, Source


@dataclass
class Request:
    topic: str
    audience: str = "general audience"
    n_slides: int = 8
    tone: str = "clear and professional"
    theme: str = "midnight"
    images: bool = True
    web_research: bool = True


@dataclass
class Plan:
    request: Request
    outline: Outline
    sources: list = field(default_factory=list)
    log: list = field(default_factory=list)


class SlideGen:
    def __init__(self, llm=None, searcher=None, photo_finder=openverse_photo):
        self.llm = llm or get_llm()
        self.searcher = searcher            # None = real web search
        self.photo_finder = photo_finder

    def _sources(self, req: Request) -> list[Source]:
        if self.llm.name == "demo":
            return demo_sources(req.topic)
        if not req.web_research:
            return []
        return research(req.topic, search=self.searcher) if self.searcher else research(req.topic)

    def plan(self, req: Request, progress=print) -> Plan:
        progress("Researching sources...")
        sources = self._sources(req)
        progress(f"Found {len(sources)} sources. Planning the outline...")
        log = []
        outline = generate_structured(self.llm, SYSTEM,
                                      outline_prompt(req.topic, req.audience, req.n_slides, req.tone, sources),
                                      Outline, log=log)
        return Plan(req, outline, sources, log)

    def build(self, plan: Plan, out_path: str, progress=print) -> tuple[Deck, dict]:
        req, t0 = plan.request, time.time()
        progress("Writing the slides...")
        deck = generate_structured(self.llm, SYSTEM, deck_prompt(plan.outline, req.audience, req.tone, plan.sources),
                                   Deck, log=plan.log)
        if deck.slides[0].type != "title":   # the renderer expects a title slide first
            from .schema import TitleSlide
            deck.slides.insert(0, TitleSlide(title=deck.title, subtitle=deck.subtitle))
        deck, fixes = ground_deck(deck, plan.sources)
        progress("Designing the slides" + (" and finding photos..." if req.images else "..."))
        builder = DeckBuilder(get_theme(req.theme), self.photo_finder if req.images else None)
        render = builder.build(deck, plan.sources, out_path)
        report = quality_report(deck, render, fixes, plan.log, plan.sources)
        report["seconds"] = round(time.time() - t0, 1)
        progress("Done.")
        return deck, report

    def run(self, req: Request, out_path: str, progress=print):
        return self.build(self.plan(req, progress), out_path, progress)
