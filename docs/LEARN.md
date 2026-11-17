# Learn this project step by step

Go in order. For each step: **read** the file, **run** the command, then answer the **questions** without looking.

---

## Step 1 - Run it first (15 min)

```bash
pip install -r requirements.txt
python -m slidegen "Climate change" --provider demo --no-images -o demo.pptx
```
Open `demo.pptx` in PowerPoint. Click a chart and choose "Edit data": the charts are real and editable, not pictures. Open the notes pane: every slide has speaker notes.

## Step 2 - The data contract: `slidegen/schema.py` (45 min)

- The LLM must return JSON that matches these Pydantic models.
- `Slide` is a **discriminated union**: the `"type"` field decides the model (`"chart"` → `ChartSlide`).
- Limits like `max_length=7` bullets are rules the AI must follow, checked automatically.

**Ask yourself:** Why is a schema better than "please return JSON" in the prompt? What happens if the AI sends 9 bullets?

## Step 3 - Talking to the AI: `slidegen/llm.py` (1 hour)

- `GeminiLLM`, `OpenAICompatLLM` and `DemoLLM` all have one method, `complete(system, prompt)`. Swapping provider changes nothing else (the **strategy pattern**).
- `extract_json` removes ```` ``` ```` fences and chatter.
- `generate_structured` is the **repair loop**: validate → if wrong, send the *exact error* and the bad answer back → the model fixes it. At most 3 tries.

**Run:** `pytest tests/test_core.py -k repair -v`

**Ask yourself:** Why send the error back instead of just asking again? (The model learns exactly what was wrong.)

## Step 4 - Prompts: `slidegen/prompts.py` (30 min)

Notice the parts: role (system), task, layout guide, writing rules, sources with ids, JSON schema.
The rule "Never invent statistics. If no source gives a number, write the point without it" is the first defence against made-up facts.

## Step 5 - Research and citations: `research.py`, `grounding.py` (1 hour)

- Research gives numbered sources `[1]..[10]`. The AI cites ids.
- **Grounding guard** (the second defence, in code, so it can't be ignored):
  - citation ids that don't exist are removed
  - a stats or chart slide with no valid source → turned into bullets (numbers dropped)
  - a chart whose values don't match its categories → turned into text

**Ask yourself:** Why check in code if the prompt already says "don't invent"? (Prompts are requests; code is a guarantee.)

## Step 6 - Two-step pipeline: `pipeline.py` (30 min)

`plan()` = research + outline. `build()` = slides + guard + render + report.
They are separate so a **human can edit the outline** in between. Fixing a plan is cheap; fixing 10 finished slides is not.

## Step 7 - Making text fit: `render/fit.py` (1 hour)

- PowerPoint doesn't tell python-pptx how big text is, so we measure it ourselves.
- **Carlito** has exactly the same letter widths as **Calibri**, so measuring with Carlito = measuring Calibri.
- `count_lines` wraps words like PowerPoint. `fit_size` tries 36 pt, 35, 34 … until the text fits.
- If even the minimum size doesn't fit → recorded as an overflow (the quality score drops).

**Ask yourself:** What is the time complexity of `fit_size`? (sizes × words; small and fast.)

## Step 8 - Drawing slides: `render/builder.py` (2 hours)

- Each slide type has its own function (`stats_slide`, `chart_slide` …), so a new layout means one new function.
- Everything is drawn on a blank slide: shapes, text boxes, native charts. No template file is needed.
- Bullets use real PowerPoint bullet XML (`a:buChar`) with a hanging indent.
- Stats cards all use the same font size (the one that fits the longest value), so they look consistent.

## Step 9 - Photos: `render/images.py` (30 min)

Openverse = openly licensed images, `mature=false`. `crop_to_ratio` cuts the middle so nothing is stretched. Credits go on the slide and on the Sources slide.

## Step 10 - Quality report: `quality.py` (20 min)

It turns "is this deck good?" into numbers: overflows, words per bullet, citation coverage, layout variety, retries. Use `scripts/evaluate.py` to compare prompts or models.

## Step 11 - The web app: `app/main.py`, `app/static/app.js` (1 hour)

- `/api/plan` → outline JSON → the browser editor → `/api/build` starts a **background thread** → the browser **polls** `/api/jobs/{id}`.
- Why a background job? Generation takes 20–60 s, and HTTP requests shouldn't wait that long.
- Old jobs are dropped (an LRU of 50) so memory doesn't grow forever.
- Security: input limits (Pydantic), `textContent` (no XSS), no keys in code.

## Step 12 - Tests and CI (30 min)

`tests/` uses **fake LLMs** (`ScriptedLLM`, `DemoLLM`), so the tests are fast, free and run offline. CI runs them and builds a demo deck on every push.
