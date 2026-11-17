"""LLM providers + the structured-output repair loop.

Providers (choose with --provider or SLIDEGEN_PROVIDER):
* gemini - Google Gemini (GEMINI_API_KEY)            default model: gemini-2.5-flash
* openai - any OpenAI-compatible API (OPENAI_API_KEY; OPENAI_BASE_URL for Groq/Ollama/...)
* demo   - offline, no key; returns ready-made content (for tests and demos)
"""
import json
import os
import re
import time

from pydantic import BaseModel, ValidationError


class LLMError(RuntimeError):
    pass


class GeminiLLM:
    name = "gemini"

    def __init__(self, model: str = None, api_key: str = None):
        from google import genai
        key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not key:
            raise LLMError("Set GEMINI_API_KEY (get one free at aistudio.google.com).")
        self.client = genai.Client(api_key=key)
        self.model = model or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    def complete(self, system: str, prompt: str) -> str:
        from google.genai import types
        resp = self.client.models.generate_content(
            model=self.model, contents=prompt,
            config=types.GenerateContentConfig(system_instruction=system, temperature=0.4,
                                               response_mime_type="application/json"))
        return resp.text or ""


class OpenAICompatLLM:
    name = "openai"

    def __init__(self, model: str = None, api_key: str = None, base_url: str = None):
        from openai import OpenAI
        key = api_key or os.getenv("OPENAI_API_KEY")
        if not key:
            raise LLMError("Set OPENAI_API_KEY (and OPENAI_BASE_URL for other compatible providers).")
        self.client = OpenAI(api_key=key, base_url=base_url or os.getenv("OPENAI_BASE_URL") or None)
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    def complete(self, system: str, prompt: str) -> str:
        resp = self.client.chat.completions.create(
            model=self.model, temperature=0.4, response_format={"type": "json_object"},
            messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}])
        return resp.choices[0].message.content or ""


def get_llm(provider: str = None):
    provider = (provider or os.getenv("SLIDEGEN_PROVIDER") or "").lower()
    if not provider:  # pick the first one that has a key
        provider = "gemini" if (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")) else \
                   "openai" if os.getenv("OPENAI_API_KEY") else "demo"
    if provider == "gemini":
        return GeminiLLM()
    if provider == "openai":
        return OpenAICompatLLM()
    if provider == "demo":
        from .demo import DemoLLM
        return DemoLLM()
    raise LLMError(f"Unknown provider {provider!r}: use gemini, openai or demo.")


def extract_json(text: str) -> dict:
    """Models sometimes wrap JSON in ``` fences or add a sentence; take the outer {...}."""
    text = re.sub(r"```(?:json)?", "", text).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("no JSON object found in the answer")
    return json.loads(text[start:end + 1])


def generate_structured(llm, system: str, prompt: str, model_cls: type[BaseModel],
                        retries: int = 2, log: list = None):
    """Ask for JSON, validate it with Pydantic, and on failure send the exact
    error back to the model so it can repair its own answer."""
    log = log if log is not None else []
    current = prompt
    for attempt in range(1, retries + 2):
        t0 = time.time()
        raw = llm.complete(system, current)
        try:
            obj = model_cls.model_validate(extract_json(raw))
            log.append({"step": model_cls.__name__, "attempt": attempt, "ok": True,
                        "seconds": round(time.time() - t0, 2)})
            return obj
        except (ValueError, ValidationError) as e:
            err = str(e)[:1500]
            log.append({"step": model_cls.__name__, "attempt": attempt, "ok": False, "error": err[:300]})
            current = (f"{prompt}\n\nYour previous answer was invalid.\nERROR:\n{err}\n\n"
                       f"PREVIOUS ANSWER:\n{raw[:4000]}\n\nReturn the corrected JSON only.")
    raise LLMError(f"The model did not return valid {model_cls.__name__} JSON after {retries + 1} tries.")
