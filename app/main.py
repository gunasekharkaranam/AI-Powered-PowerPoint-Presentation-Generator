"""Web app: topic -> editable outline -> slides -> preview -> download.

Run:  uvicorn app.main:app --reload    then open http://127.0.0.1:8000
"""
from collections import OrderedDict
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import uuid

from fastapi import FastAPI, HTTPException, Request as HTTPRequest
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from slidegen.llm import LLMError, get_llm
from slidegen.pipeline import Plan, Request, SlideGen
from slidegen.render.themes import THEMES
from slidegen.schema import Outline

ROOT = Path(__file__).resolve().parent


def load_env_file(path: Path = ROOT.parent / ".env") -> None:
    if path.exists():
        for line in path.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                if v.strip():
                    os.environ.setdefault(k.strip(), v.strip())


load_env_file()
app = FastAPI(title="SlideGen", version="2.0", description="AI presentation generator with sources")
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
templates = Jinja2Templates(directory=ROOT / "templates")
WORK = Path(tempfile.mkdtemp(prefix="slidegen_jobs_"))
MAX_KEEP = 50


class LRU(OrderedDict):
    """Keep only the newest MAX_KEEP plans/jobs in memory."""
    def put(self, key, value):
        self[key] = value
        while len(self) > MAX_KEEP:
            _, old = self.popitem(last=False)
            if isinstance(old, dict) and old.get("dir"):
                shutil.rmtree(old["dir"], ignore_errors=True)


PLANS, JOBS = LRU(), LRU()


def make_gen(provider: str | None) -> SlideGen:
    try:
        return SlideGen(llm=get_llm(provider))
    except LLMError as e:
        raise HTTPException(400, str(e))


class PlanIn(BaseModel):
    topic: str = Field(..., min_length=3, max_length=200)
    audience: str = Field("general audience", max_length=120)
    tone: str = Field("clear and professional", max_length=80)
    n_slides: int = Field(8, ge=3, le=15)
    provider: str | None = Field(None, pattern="^(gemini|openai|demo)$")
    web_research: bool = True


class BuildIn(BaseModel):
    plan_id: str
    outline: Outline
    theme: str = Field("midnight", pattern="^(" + "|".join(THEMES) + ")$")
    images: bool = True


@app.get("/", response_class=HTMLResponse)
def home(request: HTTPRequest):
    return templates.TemplateResponse(request, "index.html", {"themes": list(THEMES)})


@app.get("/health")
def health():
    return {"status": "ok", "provider": get_llm().name, "previews": bool(shutil.which("soffice"))}


@app.post("/api/plan")
def plan(body: PlanIn):
    gen = make_gen(body.provider)
    req = Request(body.topic, body.audience, body.n_slides, body.tone, web_research=body.web_research)
    try:
        p = gen.plan(req, progress=lambda m: None)
    except LLMError as e:
        raise HTTPException(502, str(e))
    pid = uuid.uuid4().hex
    PLANS.put(pid, {"plan": p, "provider": gen.llm.name})
    return {"plan_id": pid, "provider": gen.llm.name, "outline": p.outline.model_dump(),
            "sources": [s.model_dump() for s in p.sources]}


@app.post("/api/build")
def build(body: BuildIn):
    entry = PLANS.get(body.plan_id)
    if not entry:
        raise HTTPException(404, "Plan expired. Please create the outline again.")
    old: Plan = entry["plan"]
    req = Request(**{**old.request.__dict__, "theme": body.theme, "images": body.images})
    p = Plan(req, body.outline, old.sources, list(old.log))
    jid = uuid.uuid4().hex
    job = {"status": "running", "messages": [], "dir": str(WORK / jid)}
    os.makedirs(job["dir"])
    JOBS.put(jid, job)
    threading.Thread(target=_run_job, args=(job, entry["provider"], p), daemon=True).start()
    return {"job_id": jid}


def _run_job(job, provider, p: Plan):
    try:
        gen = SlideGen(llm=get_llm(provider))
        out = os.path.join(job["dir"], "deck.pptx")
        deck, report = gen.build(p, out, progress=job["messages"].append)
        job["previews"] = make_previews(out, job["dir"])
        job.update(status="done", report=report, title=deck.title,
                   filename=_safe_name(deck.title) + ".pptx", path=out)
    except Exception as e:
        job.update(status="error", error=f"{type(e).__name__}: {e}"[:400])


def _safe_name(title: str) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in title).strip("_")[:60] or "deck"


def make_previews(pptx: str, out_dir: str) -> int:
    """PNG thumbnails via LibreOffice (optional: skipped if it is not installed)."""
    if not shutil.which("soffice"):
        return 0
    try:
        subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", out_dir, pptx],
                       check=True, timeout=120, capture_output=True)
        from pdf2image import convert_from_path
        pages = convert_from_path(os.path.join(out_dir, "deck.pdf"), dpi=60)
        for i, img in enumerate(pages):
            img.save(os.path.join(out_dir, f"p{i}.png"))
        return len(pages)
    except Exception:
        return 0


def _job(jid):
    job = JOBS.get(jid)
    if not job:
        raise HTTPException(404, "Job not found.")
    return job


@app.get("/api/jobs/{jid}")
def job_status(jid: str):
    j = _job(jid)
    return {k: j.get(k) for k in ("status", "messages", "report", "title", "previews", "error")}


@app.get("/api/jobs/{jid}/download")
def download(jid: str):
    j = _job(jid)
    if j.get("status") != "done":
        raise HTTPException(409, "Not ready yet.")
    return FileResponse(j["path"], filename=j["filename"],
                        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation")


@app.get("/api/jobs/{jid}/preview/{n}.png")
def preview(jid: str, n: int):
    j = _job(jid)
    if not (0 <= n < (j.get("previews") or 0)):
        raise HTTPException(404, "No preview.")
    return FileResponse(os.path.join(j["dir"], f"p{n}.png"), media_type="image/png")
