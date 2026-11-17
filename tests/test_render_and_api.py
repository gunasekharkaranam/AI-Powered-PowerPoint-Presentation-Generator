import time

import pytest
from fastapi.testclient import TestClient
from pptx import Presentation

from slidegen.demo import DemoLLM
from slidegen.pipeline import Request, SlideGen
from slidegen.render.builder import DeckBuilder
from slidegen.render.images import Photo, crop_to_ratio
from slidegen.render.themes import THEMES, get_theme
from slidegen.schema import Deck, Source

ALL_TYPES = Deck.model_validate({"title": "Every layout", "slides": [
    {"type": "title", "title": "Every layout", "subtitle": "test", "notes": "hello"},
    {"type": "section", "title": "Part one", "subtitle": "s"},
    {"type": "bullets", "title": "Bullets", "image_query": "cat",
     "bullets": [{"text": "one", "citations": [1]}, {"text": "two"}]},
    {"type": "two_column", "title": "Compare", "left_heading": "A", "left": [{"text": "a"}],
     "right_heading": "B", "right": [{"text": "b"}]},
    {"type": "stats", "title": "Stats", "stats": [{"value": "10%", "label": "x", "citations": [1]},
                                                  {"value": "2x", "label": "y"}]},
    {"type": "timeline", "title": "Time", "events": [{"when": "2000", "text": "a"}, {"when": "2010", "text": "b"},
                                                     {"when": "2020", "text": "c"}]},
    {"type": "chart", "title": "Bar", "chart_type": "bar", "categories": ["a", "b"],
     "series": [{"name": "s", "values": [1, 2]}], "takeaway": "b wins", "citations": [1]},
    {"type": "chart", "title": "Pie", "chart_type": "pie", "categories": ["a", "b"],
     "series": [{"name": "s", "values": [30, 70]}], "takeaway": "b is bigger", "citations": [1]},
    {"type": "chart", "title": "Line", "chart_type": "line", "categories": ["a", "b", "c"],
     "series": [{"name": "s", "values": [300, 320, 340]}, {"name": "t", "values": [310, 315, 330]}],
     "unit": "ppm", "takeaway": "up", "citations": [1]},
    {"type": "quote", "title": "Quote", "quote": "Be the change.", "author": "Someone", "citations": [1]},
]})
SRC = [Source(id=1, title="Source one", url="https://example.org/1")]


@pytest.fixture
def fake_photo(tmp_path):
    from PIL import Image
    path = tmp_path / "p.jpg"
    crop_to_ratio(Image.new("RGB", (900, 600), "red"), 1.2).save(path)
    return lambda q, ratio: Photo(str(path), "Photo: tester (CC BY 4.0) via Openverse", "https://example.org/p")


@pytest.mark.parametrize("theme", list(THEMES))
def test_every_layout_renders_in_every_theme(tmp_path, theme, fake_photo):
    out = tmp_path / "all.pptx"
    report = DeckBuilder(get_theme(theme), fake_photo).build(ALL_TYPES, SRC, str(out))
    prs = Presentation(out)
    assert len(prs.slides) == len(ALL_TYPES.slides) + 1            # + Sources slide
    assert report["overflows"] == [] and report["photos"] == 1
    charts = [sh for s in prs.slides for sh in s.shapes if sh.has_chart]
    assert len(charts) == 3                                         # native, editable charts
    last = " ".join(sh.text_frame.text for sh in prs.slides[-1].shapes if sh.has_text_frame)
    assert "Source one" in last and "tester" in last                # sources + photo credit
    assert prs.slides[0].notes_slide.notes_text_frame.text == "hello"


def test_unknown_theme():
    with pytest.raises(ValueError):
        get_theme("rainbow")


def test_demo_pipeline_end_to_end(tmp_path):
    deck, report = SlideGen(llm=DemoLLM(), photo_finder=None).run(
        Request("Climate change", theme="paper"), str(tmp_path / "c.pptx"), progress=lambda m: None)
    assert report["score"] >= 90 and report["text_overflows"] == []
    assert report["content_slides_with_citation"] == "7/7"
    assert {"chart", "stats", "timeline", "two_column"} <= set(report["layouts_used"])


def test_title_slide_added_if_model_forgets(tmp_path):
    class NoTitle(DemoLLM):
        def complete(self, system, prompt):
            if prompt.startswith("Plan"):
                return super().complete(system, prompt)
            return '{"title": "X", "slides": [{"type": "bullets", "title": "b", "bullets": [{"text": "t"}]}]}'
    deck, _ = SlideGen(llm=NoTitle(), photo_finder=None).run(Request("x topic"), str(tmp_path / "x.pptx"),
                                                             progress=lambda m: None)
    assert deck.slides[0].type == "title"


# ---------- web API ----------
@pytest.fixture
def client(monkeypatch):
    import app.main as m
    monkeypatch.setattr(m, "make_previews", lambda pptx, d: 0)
    return TestClient(m.app)


def test_api_full_flow(client):
    assert "SlideGen" in client.get("/").text
    r = client.post("/api/plan", json={"topic": "Climate change", "provider": "demo"})
    assert r.status_code == 200
    plan = r.json()
    outline = plan["outline"]
    outline["items"] = outline["items"][:3]                     # user deletes slides in the editor
    outline["items"][0]["title"] = "My edited title"
    job = client.post("/api/build", json={"plan_id": plan["plan_id"], "outline": outline,
                                          "theme": "forest", "images": False}).json()["job_id"]
    for _ in range(100):
        st = client.get(f"/api/jobs/{job}").json()
        if st["status"] != "running":
            break
        time.sleep(0.1)
    assert st["status"] == "done", st
    dl = client.get(f"/api/jobs/{job}/download")
    assert dl.status_code == 200 and dl.content[:2] == b"PK"      # a real .pptx (zip) file


def test_api_validation(client):
    assert client.post("/api/plan", json={"topic": "x"}).status_code == 422
    assert client.post("/api/plan", json={"topic": "valid topic", "n_slides": 99}).status_code == 422
    bad = {"plan_id": "nope", "outline": {"title": "t", "items": [{"title": "a", "type": "bullets",
                                                                     "key_message": "k"}]}}
    assert client.post("/api/build", json=bad).status_code == 404
    assert client.post("/api/build", json={**bad, "theme": "rainbow"}).status_code == 422
    assert client.get("/api/jobs/unknown").status_code == 404
