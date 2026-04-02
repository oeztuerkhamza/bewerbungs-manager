#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Kapak sayfasi – Hamza Oezturk
Premium-Design · 15.03.2026
"""

import os
import sys

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Flowable
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ─── PATHS ───────────────────────────────────────────────────────────────────
OUTPUT = r"C:\Users\hamza\Desktop\Lebenslauf\Hamza_Oeztuerk_Kapak.pdf"
FOTO_PATH = r"C:\Users\hamza\Desktop\Lebenslauf\foto_small.jpeg"

# ─── LAYOUT ──────────────────────────────────────────────────────────────────
L_MARGIN = 2.5 * cm
R_MARGIN = 2.0 * cm
T_MARGIN = 1.6 * cm
B_MARGIN = 1.6 * cm
SIDEBAR_W = 4 * mm           # left decorative stripe width

# Cover proportions tuned to match the requested minimal layout.
PHOTO_W = 8.26 * cm    # 12.4 * (533/800) – preserves original aspect ratio
PHOTO_H = 12.4 * cm
PHOTO_TOP_GAP = 0.9 * cm
GAP_PHOTO_TO_NAME = 0.5 * cm
GAP_NAME_TO_TITLE = 0.32 * cm
GAP_TITLE_TO_ANLAGEN = 3.1 * cm

NAME_SIZE = 26
TITLE_SIZE = 20
ANLAGEN_SIZE = 12

# ─── COLOURS ─────────────────────────────────────────────────────────────────
NAVY = HexColor('#1B3764')
DARK = HexColor('#1F1F1F')
GRAY = HexColor('#4A4A4A')
LGRAY = HexColor('#777777')
RULE_C = HexColor('#D0D4DD')

# ─── FONTS ───────────────────────────────────────────────────────────────────
WIN_FONTS = r"C:\Windows\Fonts"
_FONT_MAP = {
    'CV-R': os.path.join(WIN_FONTS, 'calibri.ttf'),
    'CV-B': os.path.join(WIN_FONTS, 'calibrib.ttf'),
    'CV-I': os.path.join(WIN_FONTS, 'calibrii.ttf'),
    'CV-BI': os.path.join(WIN_FONTS, 'calibriz.ttf'),
}


def register_fonts():
    for name, path in _FONT_MAP.items():
        if os.path.exists(path):
            pdfmetrics.registerFont(TTFont(name, path))
        else:
            fb = (path.replace('calibri', 'arial')
                      .replace('calibrib', 'arialbd')
                      .replace('calibrii', 'ariali')
                      .replace('calibriz', 'arialbi'))
            pdfmetrics.registerFont(TTFont(name, fb))


# ─── PARAGRAPH STYLES ────────────────────────────────────────────────────────

def make_styles():
    def ps(name, font='CV-R', size=10, color=DARK, leading=None,
           spaceBefore=0, spaceAfter=0, align=TA_LEFT, leftIndent=0):
        return ParagraphStyle(
            name, fontName=font, fontSize=size, textColor=color,
            leading=leading or round(size * 1.4, 1),
            spaceBefore=spaceBefore, spaceAfter=spaceAfter,
            alignment=align, leftIndent=leftIndent,
        )
    return {
        'name': ps('name', 'CV-B', NAME_SIZE, NAVY, leading=30, align=TA_CENTER),
        'subtitle': ps('subtitle', 'CV-R', TITLE_SIZE, NAVY, leading=24, align=TA_CENTER),
        'anlagen': ps('anlagen', 'CV-R', ANLAGEN_SIZE, DARK, leading=14, align=TA_CENTER),
        'anlagen_list': ps('anlagen_list', 'CV-R', 10, DARK, leading=14, align=TA_CENTER),
    }


# ─── CUSTOM FLOWABLES ───────────────────────────────────────────────────────-

class AccentBar(Flowable):
    """Horizontal navy accent bar spanning the full width."""
    def __init__(self, width, thickness=1.5):
        super().__init__()
        self.bar_w = width
        self.thickness = thickness

    def wrap(self, aw, ah):
        self.width = aw
        self.height = self.thickness + 4
        return self.width, self.height

    def draw(self):
        self.canv.saveState()
        self.canv.setFillColor(NAVY)
        self.canv.rect(0, 2, self.width, self.thickness,
                       fill=True, stroke=False)
        self.canv.restoreState()


class PhotoFrame(Flowable):
    """Centered photo with a thin navy border."""
    def __init__(self, path, w, h, border=1.2):
        super().__init__()
        self.img_path = path
        self.img_w = w
        self.img_h = h
        self.border = border
        self.width = w + 2 * border
        self.height = h + 2 * border

    def wrap(self, aw, ah):
        return self.width, self.height

    def draw(self):
        c = self.canv
        b = self.border
        c.saveState()
        c.drawImage(self.img_path, b, b, self.img_w, self.img_h,
                    preserveAspectRatio=False)
        c.restoreState()
        c.saveState()
        c.setStrokeColor(NAVY)
        c.setLineWidth(b)
        c.rect(b / 2, b / 2, self.img_w + b, self.img_h + b,
               fill=False, stroke=True)
        c.restoreState()


# ─── HELPERS ─────────────────────────────────────────────────────────────────

# ─── PAGE DECORATION ───────────────────────────────────────────────────────-

def _draw_page(canvas, doc):
    """Navy sidebar stripe + bottom rule – matching Anschreiben/Lebenslauf design."""
    w, h = A4
    canvas.saveState()
    # Left sidebar stripe
    canvas.setFillColor(NAVY)
    canvas.rect(0, 0, SIDEBAR_W, h, fill=True, stroke=False)
    # Thin line at page bottom
    canvas.setStrokeColor(RULE_C)
    canvas.setLineWidth(0.5)
    canvas.line(L_MARGIN, B_MARGIN - 6 * mm, w - R_MARGIN, B_MARGIN - 6 * mm)
    canvas.restoreState()


# ─── DEFAULT CONFIG ─────────────────────────────────────────────────────────-

DEFAULT_CONFIG = {
    'stelle': 'Fullstack Entwickler',
    'datum': '15.03.2026',
    'anlagen': 'Anschreiben, Lebenslauf, Arbeitszeugnis,  Zeugnisse, Zertifikate',
}


# ─── BUILD STORY ─────────────────────────────────────────────────────────----

def build(story, sty, W, cfg=None):
    cfg = {**DEFAULT_CONFIG, **(cfg or {})}

    story.append(Spacer(1, PHOTO_TOP_GAP))
    photo = PhotoFrame(FOTO_PATH, PHOTO_W, PHOTO_H, border=1.5)
    photo.hAlign = 'CENTER'
    story.append(photo)

    story.append(Spacer(1, GAP_PHOTO_TO_NAME))
    story.append(Paragraph('Hamza Öztürk', sty['name']))
    
    story.append(Spacer(1, 0.18 * cm))
    story.append(AccentBar(W, thickness=1))
    story.append(Spacer(1, 0.18 * cm))
    
    stelle = cfg.get('stelle', 'Software Entwickler')
    story.append(Paragraph(
        f'Bewerbung als {stelle}',
        sty['subtitle'],
    ))

    story.append(Spacer(1, GAP_TITLE_TO_ANLAGEN))
    story.append(Paragraph('Anlagen:', sty['anlagen']))
    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph(cfg.get('anlagen', ''), sty['anlagen_list']))


# ─── MAIN ─────────────────────────────────────────────────────────────────---

def main():
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    register_fonts()
    sty = make_styles()
    doc = SimpleDocTemplate(
        OUTPUT,
        pagesize=A4,
        leftMargin=L_MARGIN,
        rightMargin=R_MARGIN,
        topMargin=T_MARGIN,
        bottomMargin=B_MARGIN,
        title='Kapak Sayfasi – Hamza Oezturk',
        author='Hamza Oezturk',
        subject='Bewerbungsunterlagen',
        creator='Python / ReportLab',
    )
    story = []
    build(story, sty, doc.width)
    doc.build(story, onFirstPage=_draw_page, onLaterPages=_draw_page)
    print(f"PDF erfolgreich erstellt:\n  {OUTPUT}")
    return 0


def generate(output_path=None, cfg=None):
    """Public API – called from the GUI app."""
    register_fonts()
    sty = make_styles()
    out = output_path or OUTPUT
    os.makedirs(os.path.dirname(out), exist_ok=True)
    doc = SimpleDocTemplate(
        out, pagesize=A4,
        leftMargin=L_MARGIN, rightMargin=R_MARGIN,
        topMargin=T_MARGIN, bottomMargin=B_MARGIN,
        title='Kapak Sayfasi – Hamza Oezturk',
        author='Hamza Oezturk',
        subject='Bewerbungsunterlagen',
        creator='Python / ReportLab',
    )
    story = []
    build(story, sty, doc.width, cfg)
    doc.build(story, onFirstPage=_draw_page, onLaterPages=_draw_page)
    return out


if __name__ == '__main__':
    sys.exit(main())
