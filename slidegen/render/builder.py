"""Turn a Deck into an editable .pptx.

Every slide type has its own layout function. All text goes through
`fit_size`, so nothing overflows; every slide gets speaker notes and a
citation line; the deck ends with an automatic Sources slide.
"""
from datetime import date

from lxml import etree
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION, XL_LABEL_POSITION
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, MSO_AUTO_SIZE, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

from ..grounding import slide_citations, used_source_ids
from ..schema import (BulletsSlide, ChartSlide, Deck, QuoteSlide, SectionSlide, StatsSlide,
                      TimelineSlide, TitleSlide, TwoColumnSlide)
from .fit import fit_size
from .themes import Theme

W, H, M = 13.333, 7.5, 0.7          # slide size and side margin (inches)
CT, CB = 1.95, 6.45                  # content top / bottom
CHART_TYPES = {"bar": XL_CHART_TYPE.BAR_CLUSTERED, "column": XL_CHART_TYPE.COLUMN_CLUSTERED,
               "line": XL_CHART_TYPE.LINE_MARKERS, "pie": XL_CHART_TYPE.PIE}


def rgb(hex_: str) -> RGBColor:
    return RGBColor.from_string(hex_)


class DeckBuilder:
    def __init__(self, theme: Theme, photo_finder=None):
        self.t = theme
        self.photo_finder = photo_finder      # callable(query, ratio) -> Photo | None
        self.prs = Presentation()
        self.prs.slide_width, self.prs.slide_height = Inches(W), Inches(H)
        self.blank = self.prs.slide_layouts[6]
        self.report = {"overflows": [], "photos": 0, "photo_credits": []}
        self._n = 0

    # ---------------- low-level helpers ----------------
    def _new_slide(self, bg: str = None):
        s = self.prs.slides.add_slide(self.blank)
        s.background.fill.solid()
        s.background.fill.fore_color.rgb = rgb(bg or self.t.bg)
        self._n += 1
        return s

    def _box(self, s, x, y, w, h, fill, shape=MSO_SHAPE.RECTANGLE, radius=None):
        shp = s.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
        shp.fill.solid()
        shp.fill.fore_color.rgb = rgb(fill)
        shp.line.fill.background()
        shp.shadow.inherit = False
        if radius is not None and shape == MSO_SHAPE.ROUNDED_RECTANGLE:
            shp.adjustments[0] = radius
        return shp

    def _text(self, s, x, y, w, h, paras, size, color=None, bold=False, italic=False,
              align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, bullets=False, gap=0.5, where=""):
        """paras: list of strings or list of [(text, style_dict), ...] runs."""
        plain = ["".join(r[0] for r in p) if isinstance(p, list) else p for p in paras]
        size, ok = fit_size(plain, w, h, size[0], size[1], bold, gap, 1.1 if bullets else 0)
        if not ok:
            self.report["overflows"].append(f"slide {self._n}: {where or 'text'}")
        tb = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
        tf = tb.text_frame
        tf.word_wrap = True
        tf.auto_size = MSO_AUTO_SIZE.NONE
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
        tf.vertical_anchor = anchor
        for i, p in enumerate(paras):
            para = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            para.alignment = align
            para.line_spacing = 1.0
            if i:
                para.space_before = Pt(size * gap * 1.2)
            runs = p if isinstance(p, list) else [(p, {})]
            for text, st in runs:
                r = para.add_run()
                r.text = text
                f = r.font
                f.name = self.t.font
                f.size = Pt(st.get("size", size * st.get("size_rel", 1)))
                f.bold = st.get("bold", bold)
                f.italic = italic
                f.color.rgb = rgb(st.get("color", color or self.t.text))
                if st.get("sup"):
                    r._r.get_or_add_rPr().set("baseline", "30000")
            if bullets:
                self._bullet(para, size)
        return tb

    def _bullet(self, para, size):
        pPr = para._p.get_or_add_pPr()
        indent = int(Pt(size * 1.1))
        pPr.set("marL", str(indent))
        pPr.set("indent", str(-indent))
        clr = etree.SubElement(pPr, qn("a:buClr"))
        etree.SubElement(clr, qn("a:srgbClr")).set("val", self.t.accent)
        etree.SubElement(pPr, qn("a:buFont")).set("typeface", "Arial")
        etree.SubElement(pPr, qn("a:buChar")).set("char", "•")

    def _cite_runs(self, ids):
        if not ids:
            return []
        return [("  [" + ", ".join(map(str, ids)) + "]", {"color": self.t.muted, "size_rel": 0.6, "sup": False})]

    def _bullet_paras(self, bullets):
        return [[(b.text, {})] + self._cite_runs(b.citations) for b in bullets]

    def _title(self, s, title):
        self._text(s, M, 0.5, W - 2 * M, 1.05, [title], (36, 24), bold=True,
                   anchor=MSO_ANCHOR.BOTTOM, where="title")
        self._box(s, M, 1.68, 0.9, 0.07, self.t.accent)

    def _footer(self, s, slide_obj, deck_title):
        ids = slide_citations(slide_obj)
        left = deck_title if not ids else f"Sources: {', '.join(f'[{i}]' for i in sorted(set(ids)))} (see last slide)"
        self._text(s, M, 6.9, 9.5, 0.35, [left], (11, 9), color=self.t.muted, where="footer")
        self._text(s, W - M - 1.5, 6.9, 1.5, 0.35, [str(self._n)], (11, 9),
                   color=self.t.muted, align=PP_ALIGN.RIGHT)

    @staticmethod
    def _notes(s, text):
        if text:
            s.notes_slide.notes_text_frame.text = text

    # ---------------- slide layouts ----------------
    def title_slide(self, d: TitleSlide, deck: Deck):
        s = self._new_slide()
        self._box(s, 0, 0, 0.28, H, self.t.accent)
        self._box(s, W - 4.2, 0, 4.2, H, self.t.surface)
        self._box(s, W - 3.2, 1.6, 2.2, 2.2, self.t.accent, MSO_SHAPE.OVAL)
        self._box(s, W - 2.4, 3.3, 1.4, 1.4, self.t.accent2, MSO_SHAPE.OVAL)
        self._text(s, M + 0.3, 1.7, 7.9, 2.4, [d.title or deck.title], (54, 32), bold=True,
                   anchor=MSO_ANCHOR.BOTTOM, where="title")
        self._box(s, M + 0.3, 4.3, 1.2, 0.08, self.t.accent)
        self._text(s, M + 0.3, 4.6, 7.9, 1.2, [d.subtitle or deck.subtitle], (24, 16), color=self.t.muted,
                   where="subtitle")
        self._text(s, M + 0.3, 6.6, 7.9, 0.4, [f"{date.today():%B %Y}  ·  AI-generated, with sources"],
                   (12, 10), color=self.t.muted)
        self._notes(s, d.notes)

    def section_slide(self, d: SectionSlide, deck: Deck):
        s = self._new_slide(bg=self.t.accent)
        self._text(s, M + 0.3, 2.2, W - 2 * M - 0.6, 1.8, [d.title], (54, 32), bold=True,
                   color=self.t.on_accent, anchor=MSO_ANCHOR.BOTTOM, where="title")
        if d.subtitle:
            self._text(s, M + 0.3, 4.2, W - 2 * M - 0.6, 1.0, [d.subtitle], (26, 16),
                       color=self.t.on_accent, where="subtitle")
        self._notes(s, d.notes)

    def bullets_slide(self, d: BulletsSlide, deck: Deck):
        s = self._new_slide()
        self._title(s, d.title)
        photo = None
        if d.image_query and self.photo_finder:
            photo = self.photo_finder(d.image_query, 4.9 / (CB - CT - 0.35))
        text_w = 6.75 if photo else W - 2 * M
        self._text(s, M, CT + 0.1, text_w, CB - CT - 0.1, self._bullet_paras(d.bullets), (28, 16),
                   bullets=True, gap=0.7, where="bullets")
        if photo:
            s.shapes.add_picture(photo.path, Inches(W - M - 4.9), Inches(CT), Inches(4.9), Inches(CB - CT - 0.35))
            self._text(s, W - M - 4.9, CB - 0.28, 4.9, 0.3, [photo.credit], (9, 7), color=self.t.muted)
            self.report["photos"] += 1
            self.report["photo_credits"].append(photo.credit + (f" - {photo.source_url}" if photo.source_url else ""))
        self._footer(s, d, deck.title)
        self._notes(s, d.notes)

    def two_column_slide(self, d: TwoColumnSlide, deck: Deck):
        s = self._new_slide()
        self._title(s, d.title)
        cw = (W - 2 * M - 0.4) / 2
        for i, (head, items) in enumerate(((d.left_heading, d.left), (d.right_heading, d.right))):
            x = M + i * (cw + 0.4)
            self._box(s, x, CT, cw, CB - CT, self.t.surface, MSO_SHAPE.ROUNDED_RECTANGLE, 0.05)
            self._box(s, x, CT, cw, 0.09, self.t.accent if i == 0 else self.t.accent2)
            self._text(s, x + 0.35, CT + 0.3, cw - 0.7, 0.6, [head], (26, 18), bold=True,
                       color=self.t.accent if i == 0 else self.t.accent2, where="column heading")
            self._text(s, x + 0.35, CT + 1.05, cw - 0.7, CB - CT - 1.3, self._bullet_paras(items), (22, 14),
                       bullets=True, gap=0.6, where="column bullets")
        self._footer(s, d, deck.title)
        self._notes(s, d.notes)

    def stats_slide(self, d: StatsSlide, deck: Deck):
        s = self._new_slide()
        self._title(s, d.title)
        n = len(d.stats)
        gap = 0.35
        cw = (W - 2 * M - gap * (n - 1)) / n
        top, ch = CT + 0.35, 3.6
        # same font size on every card looks calmer: use the size that fits the longest value
        vsize, _ = fit_size([max((st.value for st in d.stats), key=len)], cw - 0.6, 1.3, 60, 28, bold=True)
        for i, st in enumerate(d.stats):
            x = M + i * (cw + gap)
            self._box(s, x, top, cw, ch, self.t.surface, MSO_SHAPE.ROUNDED_RECTANGLE, 0.06)
            self._text(s, x + 0.3, top + 0.35, cw - 0.6, 1.3, [st.value], (vsize, 28), bold=True,
                       color=self.t.accent, anchor=MSO_ANCHOR.MIDDLE, where="stat value")
            self._box(s, x + 0.3, top + 1.8, 0.6, 0.05, self.t.accent2)
            label = [[(st.label, {})] + self._cite_runs(st.citations)]
            self._text(s, x + 0.3, top + 2.0, cw - 0.6, ch - 2.2, label, (20, 12), where="stat label")
        self._footer(s, d, deck.title)
        self._notes(s, d.notes)

    def timeline_slide(self, d: TimelineSlide, deck: Deck):
        s = self._new_slide()
        self._title(s, d.title)
        n = len(d.events)
        line_y = 3.75
        self._box(s, M, line_y, W - 2 * M, 0.05, self.t.muted)
        step = (W - 2 * M) / n
        for i, ev in enumerate(d.events):
            cx = M + step * (i + 0.5)
            self._box(s, cx - 0.17, line_y - 0.145, 0.34, 0.34, self.t.accent, MSO_SHAPE.OVAL)
            self._text(s, cx - step / 2 + 0.1, line_y - 1.05, step - 0.2, 0.75, [ev.when], (28, 16),
                       bold=True, color=self.t.accent, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.BOTTOM,
                       where="timeline date")
            body = [[(ev.text, {})] + self._cite_runs(ev.citations)]
            self._text(s, cx - step / 2 + 0.12, line_y + 0.45, step - 0.24, CB - line_y - 0.45, body, (18, 11),
                       align=PP_ALIGN.CENTER, where="timeline text")
        self._footer(s, d, deck.title)
        self._notes(s, d.notes)

    def chart_slide(self, d: ChartSlide, deck: Deck):
        s = self._new_slide()
        self._title(s, d.title)
        data = CategoryChartData()
        data.categories = d.categories
        for se in d.series:
            data.add_series(se.name, se.values)
        gf = s.shapes.add_chart(CHART_TYPES[d.chart_type], Inches(M), Inches(CT), Inches(8.3),
                                Inches(CB - CT), data)
        self._style_chart(gf.chart, d)
        x = M + 8.7
        cw = W - M - x
        self._box(s, x, CT, cw, CB - CT, self.t.surface, MSO_SHAPE.ROUNDED_RECTANGLE, 0.06)
        self._text(s, x + 0.3, CT + 0.3, cw - 0.6, 0.45, ["KEY TAKEAWAY"], (14, 11), bold=True,
                   color=self.t.accent)
        self._text(s, x + 0.3, CT + 0.9, cw - 0.6, CB - CT - 1.2, [d.takeaway], (24, 14), where="takeaway")
        self._footer(s, d, deck.title)
        self._notes(s, d.notes)

    def _style_chart(self, chart, d: ChartSlide):
        t = self.t
        chart.font.size = Pt(13)
        chart.font.name = t.font
        chart.font.color.rgb = rgb(t.muted)
        chart.has_title = False          # the slide title already says what the chart shows
        chart.has_legend = len(d.series) > 1 or d.chart_type == "pie"
        if chart.has_legend:
            chart.legend.position = XL_LEGEND_POSITION.BOTTOM
            chart.legend.include_in_layout = False
            chart.legend.font.color.rgb = rgb(t.text)
        plot = chart.plots[0]
        if d.chart_type == "pie":
            for i, point in enumerate(plot.series[0].points):
                point.format.fill.solid()
                point.format.fill.fore_color.rgb = rgb(t.chart[i % len(t.chart)])
            plot.has_data_labels = True
            plot.data_labels.number_format = '0%'
            plot.data_labels.show_percentage = True
            plot.data_labels.show_value = False
            plot.data_labels.position = XL_LABEL_POSITION.OUTSIDE_END
            return
        for i, series in enumerate(plot.series):
            c = rgb(t.chart[i % len(t.chart)])
            if d.chart_type == "line":
                series.format.line.color.rgb = c
                series.format.line.width = Pt(3)
                series.smooth = False
                series.marker.format.fill.solid()
                series.marker.format.fill.fore_color.rgb = c
                series.marker.format.line.color.rgb = c
            else:
                series.format.fill.solid()
                series.format.fill.fore_color.rgb = c
        if d.chart_type in ("bar", "column"):
            plot.gap_width = 60
        va = chart.value_axis
        va.has_major_gridlines = True
        va.major_gridlines.format.line.color.rgb = rgb(t.surface)
        va.format.line.fill.background()
        if d.unit:
            va.has_title = True
            va.axis_title.text_frame.text = d.unit
            va.axis_title.text_frame.paragraphs[0].runs[0].font.color.rgb = rgb(t.muted)
            va.axis_title.text_frame.paragraphs[0].runs[0].font.size = Pt(12)
        if d.chart_type == "line":
            lo = min(v for se in d.series for v in se.values)
            hi = max(v for se in d.series for v in se.values)
            if lo > 0 and (hi - lo) < 0.6 * hi:   # don't waste the plot on empty space near zero
                pad = (hi - lo) * 0.1
                va.minimum_scale = round(lo - pad, -1 if lo > 50 else 0)
        chart.category_axis.format.line.color.rgb = rgb(t.muted)
        chart.category_axis.tick_labels.font.color.rgb = rgb(t.muted)

    def quote_slide(self, d: QuoteSlide, deck: Deck):
        s = self._new_slide()
        self._text(s, M, 0.3, 2, 2.1, ["“"], (120, 120), bold=True, color=self.t.accent, where="quote mark")
        self._text(s, M + 0.5, 2.0, W - 2 * M - 1.0, 3.0, [d.quote], (40, 22), italic=True,
                   anchor=MSO_ANCHOR.MIDDLE, where="quote")
        who = [[("— " + (d.author or "Unknown"), {"color": self.t.accent, "bold": True})]
               + self._cite_runs(d.citations)]
        self._text(s, M + 0.5, 5.3, W - 2 * M - 1.0, 0.6, who, (24, 16), where="quote author")
        self._footer(s, d, deck.title)
        self._notes(s, d.notes)

    def sources_slide(self, deck: Deck, sources):
        used = set(used_source_ids(deck))
        items = [src for src in sources if src.id in used]
        credits = self.report["photo_credits"]
        if not items and not credits:
            return
        s = self._new_slide()
        self._title(s, "Sources")
        paras = [[(f"[{src.id}] ", {"bold": True, "color": self.t.accent}), (src.title, {}),
                  ("  " + src.url, {"color": self.t.muted})] for src in items]
        paras += [[("Image: ", {"bold": True, "color": self.t.accent}), (c, {"color": self.t.muted})]
                  for c in credits]
        self._text(s, M, CT, W - 2 * M, CB - CT + 0.3, paras, (18, 10), gap=0.5, where="sources")
        self._notes(s, "All facts and numbers in this deck are linked to these sources.")

    # ---------------- main ----------------
    def build(self, deck: Deck, sources, path: str) -> dict:
        layouts = {"title": self.title_slide, "section": self.section_slide, "bullets": self.bullets_slide,
                   "two_column": self.two_column_slide, "stats": self.stats_slide,
                   "timeline": self.timeline_slide, "chart": self.chart_slide, "quote": self.quote_slide}
        for sl in deck.slides:
            layouts[sl.type](sl, deck)
        self.sources_slide(deck, sources)
        self.prs.save(path)
        self.report["slides"] = len(self.prs.slides)
        return self.report
