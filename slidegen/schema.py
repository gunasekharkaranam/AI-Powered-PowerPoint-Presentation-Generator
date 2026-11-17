"""The data contract between the AI and the slide renderer.

The LLM must return JSON that matches these Pydantic models. If it doesn't,
`llm.generate_structured` shows the validation error to the model and asks
it to fix its answer (a "repair loop").
"""
from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field

SLIDE_TYPES = ("title", "section", "bullets", "two_column", "stats", "timeline", "chart", "quote")


class Source(BaseModel):
    id: int
    title: str
    url: str
    snippet: str = ""


class Bullet(BaseModel):
    text: str = Field(..., max_length=220)
    citations: list[int] = Field(default_factory=list, description="ids of sources that support this point")


class _Base(BaseModel):
    title: str = Field(..., max_length=90)
    notes: str = Field("", description="speaker notes: what the presenter says, 2-4 sentences")


class TitleSlide(_Base):
    type: Literal["title"] = "title"
    subtitle: str = ""


class SectionSlide(_Base):
    type: Literal["section"] = "section"
    subtitle: str = ""


class BulletsSlide(_Base):
    type: Literal["bullets"] = "bullets"
    bullets: list[Bullet] = Field(..., min_length=1, max_length=7)
    image_query: str = Field("", description="2-5 word photo search, or empty for no image")


class TwoColumnSlide(_Base):
    type: Literal["two_column"] = "two_column"
    left_heading: str
    left: list[Bullet] = Field(..., min_length=1, max_length=6)
    right_heading: str
    right: list[Bullet] = Field(..., min_length=1, max_length=6)


class Stat(BaseModel):
    value: str = Field(..., max_length=16, description='short number, e.g. "1.1°C", "42%", "$3.2B"')
    label: str = Field(..., max_length=90)
    citations: list[int] = Field(default_factory=list)


class StatsSlide(_Base):
    type: Literal["stats"] = "stats"
    stats: list[Stat] = Field(..., min_length=2, max_length=4)


class Event(BaseModel):
    when: str = Field(..., max_length=20)
    text: str = Field(..., max_length=120)
    citations: list[int] = Field(default_factory=list)


class TimelineSlide(_Base):
    type: Literal["timeline"] = "timeline"
    events: list[Event] = Field(..., min_length=3, max_length=6)


class Series(BaseModel):
    name: str
    values: list[float]


class ChartSlide(_Base):
    type: Literal["chart"] = "chart"
    chart_type: Literal["bar", "column", "line", "pie"] = "column"
    categories: list[str] = Field(..., min_length=2, max_length=12)
    series: list[Series] = Field(..., min_length=1, max_length=3)
    unit: str = ""
    takeaway: str = Field(..., max_length=200, description="one sentence: what the chart shows")
    citations: list[int] = Field(default_factory=list)


class QuoteSlide(_Base):
    type: Literal["quote"] = "quote"
    quote: str = Field(..., max_length=300)
    author: str = ""
    citations: list[int] = Field(default_factory=list)


Slide = Annotated[Union[TitleSlide, SectionSlide, BulletsSlide, TwoColumnSlide, StatsSlide,
                        TimelineSlide, ChartSlide, QuoteSlide], Field(discriminator="type")]


class Deck(BaseModel):
    title: str
    subtitle: str = ""
    slides: list[Slide] = Field(..., min_length=1)


# ----- Outline (step 1, the user can edit it before slides are written) -----
class OutlineItem(BaseModel):
    title: str = Field(..., max_length=90)
    type: Literal["section", "bullets", "two_column", "stats", "timeline", "chart", "quote"]
    key_message: str = Field(..., max_length=240, description="the one idea this slide must get across")


class Outline(BaseModel):
    title: str
    subtitle: str = ""
    items: list[OutlineItem] = Field(..., min_length=1, max_length=20)
