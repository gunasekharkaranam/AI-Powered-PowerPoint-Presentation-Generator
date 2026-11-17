import json

import pytest
from PIL import Image
from pydantic import ValidationError

from slidegen.grounding import ground_deck
from slidegen.llm import LLMError, extract_json, generate_structured, get_llm
from slidegen.prompts import deck_prompt, outline_prompt
from slidegen.render.fit import count_lines, fit_size
from slidegen.render.images import crop_to_ratio
from slidegen.research import research
from slidegen.schema import Deck, Outline, Source

SRC = [Source(id=1, title="A", url="https://a.example", snippet="fact one"),
       Source(id=2, title="B", url="https://b.example", snippet="fact two")]


class ScriptedLLM:
    """Returns the given answers one by one (to test the repair loop)."""
    name = "scripted"

    def __init__(self, *answers):
        self.answers, self.prompts = list(answers), []

    def complete(self, system, prompt):
        self.prompts.append(prompt)
        return self.answers.pop(0)


GOOD_OUTLINE = {"title": "T", "items": [{"title": "One", "type": "bullets", "key_message": "m"}]}


# ---------- schema + JSON ----------
def test_discriminated_union_picks_right_slide_type():
    d = Deck.model_validate({"title": "T", "slides": [
        {"type": "title", "title": "T"},
        {"type": "stats", "title": "S", "stats": [{"value": "1", "label": "a"}, {"value": "2", "label": "b"}]}]})
    assert [type(s).__name__ for s in d.slides] == ["TitleSlide", "StatsSlide"]


def test_schema_rejects_too_many_bullets():
    with pytest.raises(ValidationError):
        Deck.model_validate({"title": "T", "slides": [
            {"type": "bullets", "title": "x", "bullets": [{"text": "b"}] * 9}]})


def test_extract_json_strips_fences_and_chatter():
    assert extract_json('Sure! ```json\n{"a": 1}\n``` hope it helps') == {"a": 1}


# ---------- repair loop ----------
def test_repair_loop_fixes_bad_answer():
    llm = ScriptedLLM("not json at all", json.dumps({"title": "T", "items": []}), json.dumps(GOOD_OUTLINE))
    log = []
    out = generate_structured(llm, "sys", "PROMPT", Outline, retries=2, log=log)
    assert out.items[0].title == "One"
    assert [e["ok"] for e in log] == [False, False, True]
    assert "ERROR" in llm.prompts[1] and "PREVIOUS ANSWER" in llm.prompts[1]


def test_repair_loop_gives_up():
    with pytest.raises(LLMError):
        generate_structured(ScriptedLLM("x", "y", "z"), "sys", "p", Outline, retries=2)


def test_get_llm_defaults_to_demo_without_keys(monkeypatch):
    for k in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "OPENAI_API_KEY", "SLIDEGEN_PROVIDER"):
        monkeypatch.delenv(k, raising=False)
    assert get_llm().name == "demo"


# ---------- grounding guard ----------
def _deck(*slides):
    return Deck.model_validate({"title": "T", "slides": [{"type": "title", "title": "T"}, *slides]})


def test_invented_citation_ids_are_removed():
    d, fixes = ground_deck(_deck({"type": "bullets", "title": "b",
                                   "bullets": [{"text": "x", "citations": [1, 99]}]}), SRC)
    assert d.slides[1].bullets[0].citations == [1] and not fixes


def test_uncited_chart_becomes_text():
    chart = {"type": "chart", "title": "c", "categories": ["a", "b"], "series": [{"name": "s", "values": [1, 2]}],
             "takeaway": "it went up", "citations": [7]}
    d, fixes = ground_deck(_deck(chart), SRC)
    assert d.slides[1].type == "bullets" and d.slides[1].bullets[0].text == "it went up"
    assert "chart removed (no source)" in fixes[0]


def test_chart_with_wrong_data_shape_becomes_text():
    chart = {"type": "chart", "title": "c", "categories": ["a", "b", "c"],
             "series": [{"name": "s", "values": [1, 2]}], "takeaway": "t", "citations": [1]}
    d, fixes = ground_deck(_deck(chart), SRC)
    assert d.slides[1].type == "bullets" and "shape" in fixes[0]


def test_uncited_stats_lose_their_numbers():
    stats = {"type": "stats", "title": "s", "stats": [{"value": "99%", "label": "made up"},
                                                       {"value": "5x", "label": "also made up"}]}
    d, fixes = ground_deck(_deck(stats), SRC)
    assert d.slides[1].type == "bullets" and "99%" not in d.slides[1].model_dump_json()


# ---------- prompts + research ----------
def test_prompts_include_sources_and_schema():
    p = outline_prompt("Solar", "students", 6, "fun", SRC)
    assert "[1] A" in p and '"items"' in p and "students" in p
    o = Outline.model_validate(GOOD_OUTLINE)
    assert "Never invent statistics" in deck_prompt(o, "x", "y", SRC)
    assert "Do not use stats or chart" in outline_prompt("Solar", "a", 5, "t", [])


def test_research_numbers_and_dedupes():
    fake = [{"title": "One", "href": "https://1", "body": "b1"}, {"title": "Dup", "href": "https://1", "body": "b"},
            {"title": "Two", "href": "https://2", "body": "b2"}, {"title": "NoBody", "href": "https://3"}]
    out = research("x", search=lambda q: fake)
    assert [(s.id, s.url) for s in out] == [(1, "https://1"), (2, "https://2")]


def test_research_survives_search_failure():
    def boom(q):
        raise ConnectionError
    assert research("x", search=boom) == []


# ---------- text fitting + images ----------
def test_long_text_gets_smaller_font():
    short, _ = fit_size(["Short point"], 6, 1, 32, 12)
    long_, _ = fit_size(["A much longer bullet point that will need to wrap over several lines " * 3], 6, 1, 32, 12)
    assert short == 32 and long_ < short


def test_overflow_is_reported():
    assert fit_size(["word " * 500], 3, 1, 20, 12) == (12, False)


def test_wrapping_counts_lines():
    assert count_lines("hello", 500, 20) == 1
    assert count_lines("hello " * 40, 200, 20) > 3


def test_crop_keeps_aspect_ratio_without_stretching():
    img = Image.new("RGB", (2000, 1000))
    assert crop_to_ratio(img, 1.0).size == (1000, 1000)
    assert crop_to_ratio(Image.new("RGB", (800, 1200)), 4 / 3).size == (800, 600)
