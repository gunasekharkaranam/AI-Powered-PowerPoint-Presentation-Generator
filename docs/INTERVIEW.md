# Interview notes

## 30-second pitch

> "I built an AI presentation generator. The first version was one prompt that returned 7 identical bullet slides, and it often broke on bad JSON. I rebuilt it as a pipeline: research with numbered sources, an outline the user can edit, slide generation against a Pydantic schema with a self-repair loop, and then a rule-based grounding guard, so a chart or statistic without a source is removed. The renderer draws 8 layouts from scratch, including native editable charts, and measures text with real font metrics so nothing overflows. Every deck comes with citations, speaker notes and an automatic quality score."

## Likely questions

**How do you stop the LLM from inventing facts?**
Three layers. (1) The prompt says to use only the given sources and cite ids. (2) Code checks afterwards: unknown ids are removed, and uncited charts or stats are turned into plain text. (3) The user sees every source on the slide and on the Sources slide.

**How do you get reliable JSON?**
A Pydantic schema with a discriminated union. If validation fails, I send the exact error and the bad answer back to the model (a repair loop, max 3 tries). Gemini also runs in JSON mode. The quality report counts the retries.

**Why two steps (outline, then slides)?**
Human-in-the-loop. Editing 8 lines of outline is cheap; fixing 10 finished slides is not. It also gives the second LLM call a clear plan, which makes the output more consistent.

**How does text fitting work?**
python-pptx can't measure text. I use Carlito, which has the same letter widths as Calibri, simulate word wrapping, and pick the largest font size that fits the box. If it still doesn't fit at the minimum size, the overflow is reported.

**Why draw slides from scratch instead of using a template?**
Full control over layout and fitting, any number of themes, and no breakage when a template's placeholders change. The output is still a normal, editable .pptx.

**How do you test something that uses an LLM?**
Dependency injection: the pipeline takes any object with `complete()`. Tests use a scripted fake LLM (for example "bad JSON first, good JSON second" to test the repair loop) and the offline demo LLM. The tests are fast and free, and CI runs them on every push.

**How do you measure quality?**
`quality.py` gives a score from overflows, long bullets, citation coverage, layout variety and retries. `scripts/evaluate.py` runs 5 topics, so I can compare prompts or models with numbers.

**Scaling / production?**
Move jobs from threads to a queue (Celery/RQ) with Redis, store files in S3, cache research per topic, add rate limits and authentication, and stream progress with Server-Sent Events.

**What would you add next?**
Use the user's own company template, generate diagrams, add multi-language support, and an "improve this slide" button that re-generates one slide only.

**Security?**
Keys only in environment variables (v1 had a key in git history, and I rotated it), input length limits, safe image search, size limits on downloads, XSS-safe frontend, and Docker running as a non-root user.
