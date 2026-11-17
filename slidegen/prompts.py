"""All prompts in one place, so they are easy to read, test and improve."""
import json

from .schema import Deck, Outline

SYSTEM = (
    "You are an expert presentation designer and researcher. You write clear, specific, "
    "audience-aware slides. You only state numbers and facts that the provided sources support, "
    "and you cite them with source ids. You always answer with a single JSON object and nothing else."
)

LAYOUT_GUIDE = """Slide types you can use:
- section    : a divider that starts a new part of the talk (title + short subtitle)
- bullets    : 3-5 short points (optionally with a photo via image_query)
- two_column : compare two things (before/after, pros/cons, A vs B)
- stats      : 2-4 big numbers with labels. ONLY if sources give the numbers.
- timeline   : 3-6 dated events in order
- chart      : real data series (bar/column/line/pie). ONLY if sources give the data.
- quote      : one strong quote from a real, named person found in the sources
Pick the type that fits the message. Do not use the same type more than 3 times in a row."""

WRITING_RULES = """Writing rules:
- Slide titles: max 8 words, say the point ("Solar costs fell 90% in a decade"), not a label ("Key Aspect 1").
- Bullets: max 5 per slide, max 18 words each, concrete (names, numbers, examples). No filler.
- Citations: put source ids that support a point in "citations", e.g. [2, 5]. Use ONLY ids from the source list.
- Never invent statistics. If no source gives a number, write the point without it.
- notes: 2-4 sentences the presenter can say aloud, adding detail not on the slide."""


def sources_block(sources) -> str:
    if not sources:
        return "SOURCES: none available. Do not use stats or chart slides; avoid specific numbers."
    lines = [f"[{s.id}] {s.title} - {s.snippet[:400]}" for s in sources]
    return "SOURCES:\n" + "\n".join(lines)


def outline_prompt(topic, audience, n_slides, tone, sources) -> str:
    return f"""Plan a presentation.
TOPIC: {topic}
AUDIENCE: {audience}
TONE: {tone}
NUMBER OF CONTENT SLIDES: {n_slides} (the title slide and sources slide are added automatically)

{LAYOUT_GUIDE}

Build a clear story: context -> main ideas -> evidence -> implications -> conclusion.

{sources_block(sources)}

Return JSON matching this schema:
{json.dumps(Outline.model_json_schema())}"""


def deck_prompt(outline, audience, tone, sources) -> str:
    plan = "\n".join(f"{i + 1}. [{it.type}] {it.title} - {it.key_message}" for i, it in enumerate(outline.items))
    return f"""Write the full slides for this approved outline. Keep the order, the slide types and the
key messages (you may sharpen titles). Start with ONE slide of type "title".

DECK TITLE: {outline.title}
SUBTITLE: {outline.subtitle}
AUDIENCE: {audience}
TONE: {tone}

OUTLINE:
{plan}

{LAYOUT_GUIDE}

{WRITING_RULES}

{sources_block(sources)}

Return JSON matching this schema:
{json.dumps(Deck.model_json_schema())}"""
