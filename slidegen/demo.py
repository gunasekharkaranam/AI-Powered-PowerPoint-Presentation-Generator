"""Offline demo mode: no API key, no internet.

* Topic containing "climate" -> a complete, sourced sample deck (written by hand
  from NOAA, IPCC, Copernicus, UNFCCC and IRENA figures).
* Any other topic -> a clearly labelled placeholder deck.
Used by the tests, the CI and the "try it" button in the web app.
"""
import json

from .schema import Source

CLIMATE_SOURCES = [
    Source(id=1, title="NOAA Global Monitoring Laboratory - Trends in Atmospheric CO2",
           url="https://gml.noaa.gov/ccgg/trends/",
           snippet="Mauna Loa annual mean CO2: 316.9 ppm (1960), 325.7 (1970), 338.8 (1980), 354.4 (1990), "
                   "369.7 (2000), 389.9 (2010), 414.2 (2020), 419.3 ppm (2023). Measurements began in 1958."),
    Source(id=2, title="IPCC AR6 Synthesis Report: Summary for Policymakers",
           url="https://www.ipcc.ch/report/ar6/syr/",
           snippet="Human activities, principally through emissions of greenhouse gases, have unequivocally caused "
                   "global warming, with global surface temperature reaching 1.1°C above 1850-1900 in 2011-2020."),
    Source(id=3, title="Copernicus Climate Change Service - Global Climate Highlights 2024",
           url="https://climate.copernicus.eu/global-climate-highlights-2024",
           snippet="2024 was the warmest year on record and the first calendar year more than 1.5°C above the "
                   "pre-industrial level, about 1.6°C."),
    Source(id=4, title="UNFCCC - The Paris Agreement",
           url="https://unfccc.int/process-and-meetings/the-paris-agreement",
           snippet="Adopted by 196 Parties at COP21 in Paris in December 2015. Goal: hold warming well below 2°C "
                   "and pursue efforts to limit it to 1.5°C above pre-industrial levels."),
    Source(id=5, title="IRENA - Renewable Power Generation Costs in 2023",
           url="https://www.irena.org/Publications/2024/Sep/Renewable-Power-Generation-Costs-in-2023",
           snippet="The global average cost of electricity from new solar PV fell by about 90% between 2010 and 2023; "
                   "most new renewable capacity added in 2023 was cheaper than fossil fuel alternatives."),
    Source(id=6, title="UNFCCC - What is the United Nations Framework Convention on Climate Change?",
           url="https://unfccc.int/process-and-meetings/what-is-the-united-nations-framework-convention-on-climate-change",
           snippet="The UNFCCC was adopted in 1992 (Rio Earth Summit). The Kyoto Protocol (1997) set binding "
                   "emission targets for industrialised countries."),
]

_N = "Demo content. In the real app the AI writes these notes from the research."

CLIMATE_DECK = {
    "title": "Climate Change: Evidence and Action",
    "subtitle": "What the data shows and what we can do",
    "slides": [
        {"type": "title", "title": "Climate Change: Evidence and Action",
         "subtitle": "What the data shows and what we can do",
         "notes": "Today: how much the planet has warmed, why, and which solutions already work."},
        {"type": "bullets", "title": "Earth has warmed 1.1°C since 1850-1900",
         "image_query": "melting glacier",
         "bullets": [
             {"text": "Human greenhouse gas emissions are the main cause, says the IPCC", "citations": [2]},
             {"text": "Global surface temperature in 2011-2020 was 1.1°C above 1850-1900", "citations": [2]},
             {"text": "2024 was the warmest year on record, about 1.6°C above pre-industrial", "citations": [3]},
             {"text": "Carbon dioxide in the air is now higher than at any point in human history", "citations": [1]}],
         "notes": "1.1 degrees sounds small, but it is a global average: land and the poles warm faster. "
                  "The IPCC calls the human cause 'unequivocal'."},
        {"type": "stats", "title": "The numbers behind the warming",
         "stats": [
             {"value": "1.1°C", "label": "warming in 2011-2020 vs 1850-1900", "citations": [2]},
             {"value": "419 ppm", "label": "CO2 at Mauna Loa in 2023 (316.9 in 1960)", "citations": [1]},
             {"value": "1.5°C", "label": "Paris Agreement aim for the long-term limit", "citations": [4]},
             {"value": "~90%", "label": "fall in solar PV power cost, 2010-2023", "citations": [5]}],
         "notes": "Four numbers to remember. Note the last one: the solution is getting cheaper fast."},
        {"type": "chart", "title": "CO2 has risen 32% since 1960",
         "chart_type": "line", "categories": ["1960", "1970", "1980", "1990", "2000", "2010", "2020", "2023"],
         "series": [{"name": "CO2 (ppm), Mauna Loa", "values": [316.9, 325.7, 338.8, 354.4, 369.7, 389.9, 414.2, 419.3]}],
         "unit": "ppm", "citations": [1],
         "takeaway": "The rise is speeding up: about 9 ppm per decade in the 1960s, over 20 ppm per decade since 2000.",
         "notes": "This is the Keeling Curve, measured since 1958. (419.3 - 316.9) / 316.9 is about 32%."},
        {"type": "timeline", "title": "Five decades of climate milestones",
         "events": [
             {"when": "1958", "text": "Continuous CO2 measurements begin at Mauna Loa", "citations": [1]},
             {"when": "1992", "text": "UN climate convention (UNFCCC) adopted at Rio", "citations": [6]},
             {"when": "1997", "text": "Kyoto Protocol sets binding targets for rich countries", "citations": [6]},
             {"when": "2015", "text": "Paris Agreement: well below 2°C, aim for 1.5°C", "citations": [4]},
             {"when": "2024", "text": "First calendar year above 1.5°C", "citations": [3]}],
         "notes": "Science came first, then agreements. A single year above 1.5 is not yet a breach of Paris, "
                  "which is about long-term averages."},
        {"type": "two_column", "title": "Two jobs: cut emissions and adapt",
         "left_heading": "Mitigation (cause)",
         "left": [{"text": "Replace coal and gas power with solar and wind", "citations": [5]},
                  {"text": "Electrify transport and heating"},
                  {"text": "Use energy more efficiently in buildings and industry"}],
         "right_heading": "Adaptation (effects)",
         "right": [{"text": "Early warning systems for heatwaves and floods"},
                   {"text": "Heat-resilient cities: shade, cooling centres"},
                   {"text": "Drought-tolerant crops and water storage"}],
         "notes": _N},
        {"type": "bullets", "title": "Clean power is now the cheap option",
         "bullets": [
             {"text": "Solar PV electricity cost fell about 90% from 2010 to 2023", "citations": [5]},
             {"text": "Most new renewables added in 2023 beat fossil fuel costs", "citations": [5]},
             {"text": "Cheaper clean power makes the Paris goals more reachable", "citations": [4, 5]}],
         "image_query": "solar panels field",
         "notes": "The economics flipped. Climate action is now often the lower-cost choice."},
        {"type": "section", "title": "What happens next", "subtitle": "Every tenth of a degree matters",
         "notes": _N},
        {"type": "bullets", "title": "Key takeaways",
         "bullets": [
             {"text": "Warming is real, measured and caused by humans", "citations": [2]},
             {"text": "CO2 keeps rising, and faster than before", "citations": [1]},
             {"text": "We already have affordable tools to cut emissions", "citations": [5]},
             {"text": "Adaptation protects people from the warming already locked in"}],
         "notes": "End with action: cut emissions and prepare at the same time."},
    ],
}

CLIMATE_OUTLINE = {
    "title": CLIMATE_DECK["title"], "subtitle": CLIMATE_DECK["subtitle"],
    "items": [{"title": s["title"], "type": s["type"],
               "key_message": (s.get("takeaway") or s.get("subtitle") or s["title"])[:200]}
              for s in CLIMATE_DECK["slides"][1:]],
}


def _generic(topic: str) -> tuple[dict, dict]:
    t = topic.strip().rstrip(".") or "Your topic"
    note = "DEMO MODE - add GEMINI_API_KEY or OPENAI_API_KEY for real, researched content."
    slides = [
        {"type": "title", "title": t, "subtitle": "Demo deck (no AI key set)", "notes": note},
        {"type": "bullets", "title": f"What is {t}?", "notes": note, "bullets": [
            {"text": "This is placeholder text from demo mode"},
            {"text": "Add an API key to get researched, cited content"},
            {"text": "The layout, theme and export are the same as the real version"}]},
        {"type": "two_column", "title": "Benefits and challenges", "notes": note,
         "left_heading": "Benefits", "left": [{"text": "Point one"}, {"text": "Point two"}],
         "right_heading": "Challenges", "right": [{"text": "Point one"}, {"text": "Point two"}]},
        {"type": "section", "title": "Looking ahead", "subtitle": "Demo section slide", "notes": note},
        {"type": "bullets", "title": "Key takeaways", "notes": note,
         "bullets": [{"text": "Takeaway one"}, {"text": "Takeaway two"}, {"text": "Takeaway three"}]},
    ]
    deck = {"title": t, "subtitle": "Demo deck (no AI key set)", "slides": slides}
    outline = {"title": t, "subtitle": deck["subtitle"],
               "items": [{"title": s["title"], "type": s["type"], "key_message": s["title"]} for s in slides[1:]]}
    return outline, deck


def demo_sources(topic: str) -> list[Source]:
    return list(CLIMATE_SOURCES) if "climate" in topic.lower() else []


class DemoLLM:
    name = "demo"

    def complete(self, system: str, prompt: str) -> str:
        first = prompt.splitlines()
        topic_line = next((l for l in first if l.startswith(("TOPIC:", "DECK TITLE:"))), "TOPIC: demo")
        topic = topic_line.split(":", 1)[1].strip()
        if "climate" in topic.lower():
            outline, deck = CLIMATE_OUTLINE, CLIMATE_DECK
        else:
            outline, deck = _generic(topic)
        return json.dumps(outline if prompt.startswith("Plan a presentation") else deck)
