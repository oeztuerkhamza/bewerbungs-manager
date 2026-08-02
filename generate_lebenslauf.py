#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lebenslauf – Hamza Öztürk · Fullstack Entwickler
Premium-Design · 23.03.2026
"""

import os
import sys
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer,
    Table, TableStyle, KeepTogether, Image, Flowable,
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.colors import HexColor, white
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER, TA_JUSTIFY
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from pdf_text_utils import esc, esc_rich

# ─── PATHS ────────────────────────────────────────────────────────────────────
BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
OUTPUT        = os.path.join(BASE_DIR, "Hamza_Oeztuerk_Lebenslauf_Fullstack_Entwickler.pdf")
FOTO_PATH     = os.path.join(BASE_DIR, "foto_small.jpeg")
SIGNATUR_PATH = os.path.join(BASE_DIR, "sıgnatur.png")
ICONS_DIR     = os.path.join(BASE_DIR, "icons")
ICON_LOCATION = os.path.join(ICONS_DIR, 'location.png')
ICON_EMAIL    = os.path.join(ICONS_DIR, 'email.png')
ICON_LINKEDIN = os.path.join(ICONS_DIR, 'linkedin.png')
ICON_GITHUB   = os.path.join(ICONS_DIR, 'github.png')
ICON_PHONE    = os.path.join(ICONS_DIR, 'phone.png')
ICON_WEBSITE  = os.path.join(ICONS_DIR, 'website.png')

# ─── LAYOUT ──────────────────────────────────────────────────────────────────
L_MARGIN  = 1.3 * cm
R_MARGIN  = 1.2 * cm
T_MARGIN  = 0.7 * cm
B_MARGIN  = 0.6 * cm
SIDEBAR_W = 4 * mm
SEC_GAP   = 0.07 * cm

# ─── COLOURS ─────────────────────────────────────────────────────────────────
NAVY      = HexColor('#1B3764')
ACCENT    = HexColor('#2C5AA0')
DARK      = HexColor('#222222')
GRAY      = HexColor('#555555')
LGRAY     = HexColor('#888888')
RULE_C    = HexColor('#C8CDD6')
BG_SKILL  = HexColor('#F4F6F9')
BG_SKILL2 = HexColor('#FAFBFD')
HDR_BG    = HexColor('#EBF0F8')

# ─── FONTS ───────────────────────────────────────────────────────────────────
WIN_FONTS = r"C:\Windows\Fonts"
_FONT_MAP = {
    'CV-R':  os.path.join(WIN_FONTS, 'calibri.ttf'),
    'CV-B':  os.path.join(WIN_FONTS, 'calibrib.ttf'),
    'CV-I':  os.path.join(WIN_FONTS, 'calibrii.ttf'),
    'CV-BI': os.path.join(WIN_FONTS, 'calibriz.ttf'),
}

_FALLBACK_TTF = {
    'CV-R':  os.path.join(WIN_FONTS, 'arial.ttf'),
    'CV-B':  os.path.join(WIN_FONTS, 'arialbd.ttf'),
    'CV-I':  os.path.join(WIN_FONTS, 'ariali.ttf'),
    'CV-BI': os.path.join(WIN_FONTS, 'arialbi.ttf'),
}
# Letzter Ausweg: eingebaute Standard-Schriften, damit nie eine Schrift fehlt.
_STD_FALLBACK = {
    'CV-R':  'Helvetica',
    'CV-B':  'Helvetica-Bold',
    'CV-I':  'Helvetica-Oblique',
    'CV-BI': 'Helvetica-BoldOblique',
}

def register_fonts():
    for name, path in _FONT_MAP.items():
        if os.path.exists(path):
            pdfmetrics.registerFont(TTFont(name, path))
            continue
        fb = _FALLBACK_TTF.get(name)
        if fb and os.path.exists(fb):
            pdfmetrics.registerFont(TTFont(name, fb))
            continue
        # Weder Calibri noch Arial vorhanden -> Alias auf Standard-Font,
        # damit kein "Can't find font"-Fehler beim ersten Paragraph auftritt.
        pdfmetrics.registerFont(
            pdfmetrics.Font(name, _STD_FALLBACK[name], 'WinAnsiEncoding'))


# ─── PARAGRAPH STYLES ────────────────────────────────────────────────────────
def make_styles():
    def ps(name, font='CV-R', size=10, color=DARK, leading=None,
           spaceBefore=0, spaceAfter=0, align=TA_LEFT, leftIndent=0, **kw):
        return ParagraphStyle(
            name, fontName=font, fontSize=size, textColor=color,
            leading=leading or round(size * 1.4, 1),
            spaceBefore=spaceBefore, spaceAfter=spaceAfter,
            alignment=align, leftIndent=leftIndent, **kw,
        )
    return {
        'name':        ps('name',        'CV-B', 22, NAVY, leading=24),
        'role':        ps('role',        'CV-R', 10.5, GRAY, leading=12, spaceAfter=0.5),
        'contact':     ps('contact',     'CV-R', 8.2, DARK, leading=10.6),
        'section':     ps('section',     'CV-B', 10.2, NAVY, leading=12),
        'entry_title': ps('entry_title', 'CV-B', 8.8, DARK, leading=10.8, leftIndent=8),
        'entry_sub':   ps('entry_sub',   'CV-I', 7.8, GRAY, leading=9.0, spaceAfter=0.1, leftIndent=8),
        'period':      ps('period',      'CV-R', 8.0, LGRAY, leading=10.0, align=TA_RIGHT),
        'bullet':      ps('bullet',      'CV-R', 8.1, DARK, leading=8.9,
                          spaceAfter=0.1, leftIndent=14, align=TA_JUSTIFY),
        'profile':     ps('profile',     'CV-R', 8.3, DARK, leading=9.8,
                          spaceAfter=0.2, leftIndent=8, align=TA_JUSTIFY),
        'footer':      ps('footer',      'CV-R', 8, LGRAY, leading=10, spaceBefore=0.5),
        'skill_lbl':   ps('skill_lbl',   'CV-B', 8.3, NAVY, leading=10.2),
        'skill_val':   ps('skill_val',   'CV-R', 8.2, DARK, leading=10.2),
        # Ausbildung-specific (lower indent to keep current alignment)
        'edu_title':   ps('edu_title',   'CV-B', 8.8, DARK, leading=10.8, leftIndent=4),
        'edu_bullet':  ps('edu_bullet',  'CV-R', 8.1, DARK, leading=9.6,
                          spaceAfter=0.2, leftIndent=10, align=TA_JUSTIFY),
    }


# ─── CUSTOM FLOWABLES ───────────────────────────────────────────────────────
class SectionHeading(Flowable):
    """Premium heading: text + short thick navy underline + thin gray continuation."""
    def __init__(self, text, style):
        super().__init__()
        self._para = Paragraph(text, style)

    def wrap(self, aw, ah):
        pw, ph = self._para.wrap(aw, ah)
        self.height = ph + 2.5
        self.width = aw
        return self.width, self.height

    def draw(self):
        c = self.canv
        self._para.drawOn(c, 0, 3)
        c.saveState()
        c.setStrokeColor(NAVY)
        c.setLineWidth(1.5)
        c.line(0, 0.8, self.width * 0.24, 0.8)
        c.setStrokeColor(RULE_C)
        c.setLineWidth(0.3)
        c.line(self.width * 0.24, 0.8, self.width, 0.8)
        c.restoreState()


class PhotoFrame(Flowable):
    """Photo with clean thin navy border – zoom crops the image inside the frame."""
    def __init__(self, path, w, h, border=1.2, zoom=4.0):
        super().__init__()
        self.img_path = path
        self.img_w = w
        self.img_h = h
        self.border = border
        self.zoom = zoom
        self.width = w + 2 * border
        self.height = h + 2 * border

    def wrap(self, aw, ah):
        return self.width, self.height

    def draw(self):
        c = self.canv
        b = self.border
        z = self.zoom
        # Bild fehlt? -> nur den Rahmen zeichnen, nicht abstürzen.
        if os.path.isfile(self.img_path):
            # Clip to frame area
            c.saveState()
            p = c.beginPath()
            p.rect(b, b, self.img_w, self.img_h)
            c.clipPath(p, stroke=0)
            # "Cover"-Fit: Bild unter Beibehaltung des Seitenverhältnisses so
            # skalieren, dass es den Rahmen voll ausfüllt; Überstand wird
            # mittig beschnitten (kein Verzerren, kein leerer Rand).
            try:
                from reportlab.lib.utils import ImageReader
                nat_w, nat_h = ImageReader(self.img_path).getSize()
            except Exception:
                nat_w, nat_h = self.img_w, self.img_h
            if nat_w <= 0 or nat_h <= 0:
                nat_w, nat_h = self.img_w, self.img_h
            scale = max(self.img_w / nat_w, self.img_h / nat_h) * z
            draw_w = nat_w * scale
            draw_h = nat_h * scale
            ox = b + (self.img_w - draw_w) / 2
            oy = b + (self.img_h - draw_h) / 2
            c.drawImage(self.img_path, ox, oy, draw_w, draw_h,
                        preserveAspectRatio=True)
            c.restoreState()
        # Border
        c.saveState()
        c.setStrokeColor(NAVY)
        c.setLineWidth(b)
        c.rect(b / 2, b / 2, self.img_w + b, self.img_h + b,
               fill=False, stroke=True)
        c.restoreState()


def make_round_photo(src_path, focus=0.62, size_px=900):
    """Erzeugt eine quadratische PNG-Datei, in der nur der Kreis sichtbar ist.

    Der Zuschnitt wird fest ins Bild gebrannt (transparente Ecken), statt ihn
    nur per Clipping-Pfad im PDF zu setzen. Grund: manche Betrachter und vor
    allem PDF-Editoren (LibreOffice Draw, Illustrator) ignorieren beim Import
    den Clipping-Pfad und zeigen dann wieder das volle Rechteck.

    ``focus`` steuert den vertikalen Zuschnitt: 0.5 = mittig, grössere Werte
    zeigen mehr vom oberen Bildbereich, damit der Kopf nicht angeschnitten wird.
    Gibt den Pfad zur erzeugten Datei zurück – oder ``None``, wenn Pillow fehlt.
    """
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return None
    if not os.path.isfile(src_path):
        return None

    out_path = os.path.join(BASE_DIR, '.foto_rund.png')
    # Nur neu bauen, wenn Quelle neuer ist als der Cache.
    if (os.path.isfile(out_path)
            and os.path.getmtime(out_path) >= os.path.getmtime(src_path)):
        return out_path

    img = Image.open(src_path).convert('RGB')
    side = min(img.width, img.height)
    left = (img.width - side) // 2
    top = int(round((img.height - side) * (1.0 - focus)))
    top = max(0, min(top, img.height - side))
    img = img.crop((left, top, left + side, top + side))
    img = img.resize((size_px, size_px), Image.LANCZOS)

    # Kreismaske mit 4x Supersampling -> weiche, saubere Kante.
    ss = 4
    mask = Image.new('L', (size_px * ss, size_px * ss), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size_px * ss - 1, size_px * ss - 1),
                                 fill=255)
    mask = mask.resize((size_px, size_px), Image.LANCZOS)

    img.putalpha(mask)
    img.save(out_path, 'PNG')
    return out_path


class CirclePhotoFrame(Flowable):
    """Rundes Portrait: Bild kreisförmig beschnitten, dünner Navy-Ring aussen.

    ``focus`` steuert den vertikalen Bildausschnitt: 0.5 = mittig,
    Werte darüber zeigen mehr vom oberen Bildbereich (bei Portraits sinnvoll,
    damit der Kopf nicht angeschnitten wird).
    """
    def __init__(self, path, diameter, border=1.1, gap=2.2, focus=0.62):
        super().__init__()
        self.img_path = path
        self.d = diameter
        self.border = border
        self.gap = gap          # Abstand zwischen Bildkante und Aussenring
        self.focus = focus
        pad = border + gap
        self.width = diameter + 2 * pad
        self.height = diameter + 2 * pad

    def wrap(self, aw, ah):
        return self.width, self.height

    def draw(self):
        c = self.canv
        d = self.d
        pad = self.border + self.gap
        cx = cy = pad + d / 2          # Kreismittelpunkt
        r = d / 2

        # Bevorzugt das fertig freigestellte Rund-PNG: dann ist der Zuschnitt
        # Teil des Bildes und geht in keinem Betrachter/Editor verloren.
        round_png = make_round_photo(self.img_path, focus=self.focus)
        if round_png:
            c.saveState()
            c.drawImage(round_png, cx - r, cy - r, d, d,
                        preserveAspectRatio=True, mask='auto')
            c.restoreState()
        elif os.path.isfile(self.img_path):
            # Fallback ohne Pillow: Clipping-Pfad im PDF.
            c.saveState()
            p = c.beginPath()
            p.circle(cx, cy, r)
            c.clipPath(p, stroke=0)
            try:
                from reportlab.lib.utils import ImageReader
                nat_w, nat_h = ImageReader(self.img_path).getSize()
            except Exception:
                nat_w, nat_h = d, d
            if nat_w <= 0 or nat_h <= 0:
                nat_w, nat_h = d, d
            scale = max(d / nat_w, d / nat_h)
            draw_w = nat_w * scale
            draw_h = nat_h * scale
            ox = cx - draw_w / 2
            # Überstand nach oben verschieben, damit das Gesicht sitzt.
            oy = cy - r - (draw_h - d) * (1.0 - self.focus)
            c.drawImage(self.img_path, ox, oy, draw_w, draw_h,
                        preserveAspectRatio=True, mask='auto')
            c.restoreState()

        # Feiner heller Aussenring + kräftiger Navy-Ring direkt am Bild.
        c.saveState()
        c.setStrokeColor(RULE_C)
        c.setLineWidth(0.4)
        c.circle(cx, cy, r + self.gap + self.border / 2, stroke=1, fill=0)
        c.setStrokeColor(NAVY)
        c.setLineWidth(self.border)
        c.circle(cx, cy, r + self.border / 2, stroke=1, fill=0)
        c.restoreState()


# ─── HELPERS ─────────────────────────────────────────────────────────────────
def b(t):   return f'<b>{t}</b>'
def it(t):  return f'<i>{t}</i>'
def lnk(url, label):
    return f'<a href="{url}" color="#2C5AA0">{label}</a>'


def icon_prefix(icon_path, fallback_label):
    """Render image icon if available, else fallback to a short text symbol."""
    if os.path.isfile(icon_path):
        src = icon_path.replace('\\', '/')
        return f'<img src="{src}" width="10" height="10" valign="middle"/>'
    return f'<font color="#1B3764"><b>{fallback_label}</b></font>'

def bul(text, sty):
    """Bullet with clean navy dot."""
    return Paragraph(
        f'<font color="#1B3764">\u2022</font>&#160;&#160;{text}', sty)

# Two-column entry table style
_ENTRY_TS = TableStyle([
    ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
    ('LEFTPADDING',   (0, 0), (0, -1),  0),
    ('LEFTPADDING',   (1, 0), (1, -1),  0),
    ('RIGHTPADDING',  (0, 0), (0, -1),  2),
    ('RIGHTPADDING',  (1, 0), (1, -1),  0),
    ('TOPPADDING',    (0, 0), (-1, -1), 0),
    ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
])

def entry_row(left, date_str, sty, cw, dw):
    # Keep period text on one visual line for consistent top alignment.
    safe_date = str(date_str).replace(' – ', '&nbsp;–&nbsp;').replace(' - ', '&nbsp;-&nbsp;')
    t = Table([[left, Paragraph(safe_date, sty['period'])]], colWidths=[cw, dw])
    t.hAlign = 'LEFT'
    t.setStyle(_ENTRY_TS)
    return t

def sec(title, sty):
    """Section heading with accent bar + spacing."""
    return [Spacer(1, SEC_GAP), SectionHeading(title, sty['section']),
            Spacer(1, 1.0)]


# ─── PAGE DECORATION ────────────────────────────────────────────────────────
def _draw_page(canvas, doc):
    """Clean premium: solid navy sidebar + header tint + footer."""
    w, h = A4
    canvas.saveState()
    # Header background tint (full width, behind sidebar)
    hdr_h = 3.6 * cm
    y_hdr = h - T_MARGIN - hdr_h + 0.3 * cm
    canvas.setFillColor(HDR_BG)
    canvas.rect(0, y_hdr, w, hdr_h, fill=True, stroke=False)
    # Solid navy sidebar (drawn on top of header band)
    canvas.setFillColor(NAVY)
    canvas.rect(0, 0, SIDEBAR_W, h, fill=True, stroke=False)
    # Thin navy line under header
    canvas.setStrokeColor(NAVY)
    canvas.setLineWidth(0.5)
    canvas.line(L_MARGIN, y_hdr, w - R_MARGIN, y_hdr)
    # Footer line
    canvas.setStrokeColor(RULE_C)
    canvas.setLineWidth(0.35)
    canvas.line(L_MARGIN, B_MARGIN - 6 * mm, w - R_MARGIN, B_MARGIN - 6 * mm)
    canvas.restoreState()


# ─── DEFAULT CONFIG ──────────────────────────────────────────────────────────
DEFAULT_KURZPROFIL = (
    'Full-Stack-Entwickler mit Fokus auf <b>C#/.NET</b>, <b>Angular</b>, '
    '<b>Docker/Azure</b> und <b>CI/CD</b>. Über 3 Jahre Erfahrung in der '
    'Modernisierung von ERP-Systemen inkl. vollständiger Migration einer '
    'Legacy-Desktop-Anwendung in eine Web-Architektur; aktuell verantwortlich '
    'für eine selbst entwickelte, produktiv genutzte Warenwirtschafts- und '
    'Vermietungsplattform. End-to-End von Datenmodellierung und API-Design '
    'über Frontend und SEO bis zu Cloud-Betrieb und '
    'Deployment-Automatisierung — mit messbaren Ergebnissen in Performance '
    'und Code-Qualität.'
)

DEFAULT_CONFIG = {
    'stelle':        'Fullstack Entwickler',
    'datum':         datetime.now().strftime('%d.%m.%Y'),
    'kurzprofil':    DEFAULT_KURZPROFIL,
}


# ─── BUILD STORY ─────────────────────────────────────────────────────────────
def build(story, sty, W, cfg=None):
    cfg = {**DEFAULT_CONFIG, **(cfg or {})}
    DW = W * 0.20
    CW = W - DW - 0.3 * cm
    DW_EXP = W * 0.13
    CW_EXP = W - DW_EXP

    # ── 1  HEADER ────────────────────────────────────────────────────────────
    PHOTO_D = 3.1 * cm          # Durchmesser des runden Portraits
    PHOTO_W = PHOTO_D
    HDR_W   = W - PHOTO_W - 1.0 * cm

    # Contact info with bold navy label prefixes – each on its own line
    c_ort = (
        icon_prefix(ICON_LOCATION, '⌂:') + '&#160;'
        'Freiburg'
    )
    c_tel = (
        icon_prefix(ICON_PHONE, '☎:') + '&#160;'
        + lnk('https://wa.me/4915566859378', '+49 155 66859378')
    )
    c_email = (
        icon_prefix(ICON_EMAIL, '@:') + '&#160;'
        + lnk('mailto:oeztuerk.hamza@web.de', 'oeztuerk.hamza@web.de')
    )
    c_linkedin = (
        icon_prefix(ICON_LINKEDIN, 'in:') + '&#160;'
        + lnk('https://linkedin.com/in/hamzaoeztuerk',
              'linkedin.com/in/hamzaoeztuerk')
    )
    c_github = (
        icon_prefix(ICON_GITHUB, '&lt;/&gt;:') + '&#160;'
        + lnk('https://github.com/oeztuerkhamza',
              'github.com/oeztuerkhamza')
    )
    c_website = (
        icon_prefix(ICON_WEBSITE, '🌐:') + '&#160;'
        + lnk('https://hamzaoeztuerk.de',
              'hamzaoeztuerk.de')
    )
    c_geb = (
        '<font color="#1B3764"><b>Geb.:</b></font>&#160;'
        ' 1996'
    )
    c_visa = (
        '<font color="#1B3764"><b>Visum:</b></font>&#160;'
        'kein Visum nötig'
    )

    contact_table = Table(
        [
            [Paragraph(c_ort, sty['contact']), Paragraph(c_geb, sty['contact'])],
            [Paragraph(c_email, sty['contact']), Paragraph(c_tel, sty['contact'])],
            [Paragraph(c_linkedin, sty['contact']), Paragraph(c_github, sty['contact'])],
            [Paragraph(c_website, sty['contact']), Paragraph(c_visa, sty['contact'])],
        ],
        colWidths=[HDR_W * 0.56, HDR_W * 0.44],
    )
    contact_table.setStyle(TableStyle([
        ('VALIGN',       (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING',  (0, 0), (0, -1),  0),
        ('LEFTPADDING',  (1, 0), (1, -1),  8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING',   (0, 0), (-1, -1), 0.5),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 0.5),
    ]))

    left_hdr = [
        Paragraph('Hamza Öztürk', sty['name']),
        Spacer(1, 2),
        Paragraph(
            esc(cfg['stelle']),
            sty['role'],
        ),
        Spacer(1, 2),
        contact_table,
    ]

    photo = CirclePhotoFrame(FOTO_PATH, PHOTO_D, border=1.1, gap=2.2, focus=0.62)
    hdr = Table(
        [[left_hdr, photo]],
        colWidths=[HDR_W, PHOTO_W + 1.0 * cm],
    )
    hdr.setStyle(TableStyle([
        ('VALIGN',       (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING',  (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING',   (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 0),
    ]))
    story.append(hdr)
    story.append(Spacer(1, 0.01 * cm))

    # ── 2  KURZPROFIL ────────────────────────────────────────────────────────
    story.extend([
        Spacer(1, 0.02 * cm),
        SectionHeading('KURZPROFIL', sty['section']),
        Spacer(1, 1.0),
    ])
    story.append(Paragraph(
        esc_rich((cfg.get('kurzprofil') or '').strip() or DEFAULT_KURZPROFIL),
        sty['profile'],
    ))

    # ── 3  BERUFSERFAHRUNG ───────────────────────────────────────────────────
    story.extend(sec('BERUFSERFAHRUNG', sty))

    def exp_header(title, period):
        """Company/role left, period right – same line."""
        t = Table(
            [[Paragraph(b(title), sty['entry_title']),
              Paragraph(period.replace(' – ', '&nbsp;–&nbsp;'), sty['period'])]],
            colWidths=[W * 0.79, W * 0.18],
        )
        t.setStyle(TableStyle([
            ('VALIGN',       (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING',  (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING',   (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING',(0, 0), (-1, -1), 0),
        ]))
        return t

    # — Bike Haus Freiburg (aktuell)
    story.append(KeepTogether([
        exp_header('Bike Haus Freiburg – Full-Stack Entwickler (Inhouse-Software)',
                   '03/2026 – heute'),
        Paragraph(
            lnk('https://bikehausfreiburg.com', 'bikehausfreiburg.com')
            + '&#160;&#160;<font color="#1B3764">|</font>&#160;&#160;'
            + lnk('https://github.com/oeztuerkhamza/bikehausfreiburg', 'GitHub'),
            sty['entry_sub'],
        ),
        bul(
            'Konzeption, Entwicklung und Betrieb einer eigenen Warenwirtschafts- '
            'und Vermietungsplattform: <b>.NET 9</b>-API (40 Controller, '
            '46 Domain-Entities, 130+ EF-Core-Migrationen), <b>Angular 17</b> '
            'Admin-SPA und SSR-Homepage — im täglichen Geschäftsbetrieb produktiv.',
            sty['bullet'],
        ),
        bul(
            'Vermietung vollständig digitalisiert (Online-Buchung, PDF-Verträge '
            'mit QR-Code, digitale Unterschrift, Kaution, automatische E-Mails): '
            '<b>190 Mietverträge, 1.097 Miettage und 16.716 € Mietumsatz</b> '
            'papierlos abgewickelt (2026).',
            sty['bullet'],
        ),
        bul(
            'SEO-Ausbau der SSR-Homepage (12 Sprachen mit hreflang, Prerendering, '
            'IndexNow, stadtbasierte Landing-Pages): in 6 Monaten auf '
            '<b>222.000 Impressionen und 9.700 Klicks</b> gewachsen '
            '(CTR 4,4 %, Ø-Position 9,3).',
            sty['bullet'],
        ),
        bul(
            'KI-Assistenten für Gmail, WhatsApp und Kleinanzeigen (<b>OpenAI API</b>) '
            'mit mehrsprachigen Antwortentwürfen; Kleinanzeigen-Scraper '
            '(<b>Playwright</b>), automatisierte Google-Reviews-Kampagne, '
            'Newsletter- und Backup-Services.',
            sty['bullet'],
        ),
        bul(
            'Betrieb &amp; DevOps: 6-Container-<b>Docker</b>-Stack auf eigenem VPS, '
            '<b>GitHub Actions</b> CI/CD mit Change-Detection und '
            'Zero-Downtime-Deployment, Nginx (Rate Limiting, HSTS/CSP, '
            'Let\'s Encrypt), Mailcow-Mailserver (DKIM/SPF/DMARC), '
            'Android-App via Capacitor.',
            sty['bullet'],
        ),
    ]))
    story.append(Spacer(1, 2))

    # — Dicom GmbH
    story.append(KeepTogether([
        exp_header('Dicom GmbH – Full-Stack Entwickler', '02/2024 – 02/2026'),
        bul(
            'Migration eines kompletten ERP-Systems von WinForms zu einer '
            '<b>C#/.NET 10</b> + <b>Angular</b> Web-Lösung; Einführung einer '
            '<b>Clean Architecture</b> und modularen API-Struktur.',
            sty['bullet'],
        ),
        bul(
            'Neuaufbau und Optimierung der Datenbankmodelle (<b>EF Core</b>, '
            'SQL Server); deutliche Verbesserung von API-Antwortzeiten und '
            'Seitenladegeschwindigkeit durch gezielte Query- und '
            'Bundle-Optimierung.',
            sty['bullet'],
        ),
        bul(
            'Aufbau von CI/CD-Pipelines (<b>GitHub Actions</b>, <b>Azure DevOps</b>): '
            'Deployment-Zeit um <b>40 %</b> reduziert, '
            'SonarQube-Violations um <b>99 %</b> gesenkt.',
            sty['bullet'],
        ),
        bul(
            'Entwicklung von <b>15+ Angular-Komponenten</b> mit <b>NgRx</b> und '
            'Reactive Forms; Unit- und Integrationstests mit <b>xUnit</b> und '
            '<b>Moq</b>, Testabdeckung auf über <b>60 %</b> gesteigert.',
            sty['bullet'],
        ),
        bul(
            'Betrieb der gesamten Infrastruktur in der <b>Azure Cloud</b> '
            '(Dev/Staging/Prod); REST-APIs inkl. KI-gestützter Tools zur '
            'Beschleunigung von Entwicklungszyklen; Lösung mehrerer kritischer '
            'Bugs in produktiven ERP-Modulen.',
            sty['bullet'],
        ),
    ]))

    # ── 4  PROJEKTE ──────────────────────────────────────────────────────────
    story.extend(sec('PROJEKTE', sty))

    # — Ausrollung der Fahrrad-Plattform auf weitere Geschäfte
    story.append(KeepTogether([
        Paragraph(
            b('Rollout der Fahrrad-Plattform')
            + ' <font color="#1B3764">(2× weitere Live-Installationen)</font>'
            + '&#160;&#160;'
            + lnk('https://karaarslan-bike.de', 'karaarslan-bike.de')
            + '&#160;&#160;<font color="#1B3764">|</font>&#160;&#160;'
            + lnk('https://benlirad.de', 'benlirad.de'),
            sty['entry_title'],
        ),
        bul(
            'Ausrollung des eigenen Warenwirtschaftssystems als wiederverwendbares '
            'Produkt für zwei weitere Fahrradgeschäfte: eigenes Branding, '
            'Standort- und Preislogik, separate Docker-Deployments inkl. '
            'Mailserver und CI/CD.',
            sty['bullet'],
        ),
    ]))

    # — Kulturplattform
    story.append(KeepTogether([
        Paragraph(
            b('Kulturplattform Freiburg e.V.')
            + ' <font color="#1B3764">(Live)</font>'
            + '&#160;&#160;'
            + lnk('https://kulturplattformfreiburg.org',
                  'kulturplattformfreiburg.org')
            + '&#160;&#160;<font color="#1B3764">|</font>&#160;&#160;'
            + lnk('https://github.com/oeztuerkhamza/KulturPlatform',
                  'GitHub'),
            sty['entry_title'],
        ),
        bul(
            '.NET 10, React 19, Docker Compose — Ehrenamtliche '
            'Full-Stack-Entwicklung: Admin-Panel, Newsletter-System, '
            'Bildverarbeitung, DE/TR-Zweisprachigkeit.',
            sty['bullet'],
        ),
    ]))

    # — Zerin Gold
    story.append(KeepTogether([
        Paragraph(
            b('Zerin Gold')
            + ' – Premium-Website für Goldhändler &amp; Juwelier'
            + ' <font color="#1B3764">(Live)</font>'
            + '&#160;&#160;'
            + lnk('https://zerin-gold.de', 'zerin-gold.de')
            + '&#160;&#160;<font color="#1B3764">|</font>&#160;&#160;'
            + lnk('https://github.com/oeztuerkhamza/zerin-gold',
                  'GitHub'),
            sty['entry_title'],
        ),
        bul(
            '<b>Next.js 16</b> (App Router, Server Components/Actions), '
            'TypeScript (strict), Tailwind 4 + shadcn/ui + Framer Motion, '
            '<b>PostgreSQL 16</b>/Prisma 7, Redis; Auth.js v5 (Argon2 + 2FA), '
            'getestet mit Vitest &amp; Playwright.',
            sty['bullet'],
        ),
        bul(
            '7-sprachig inkl. RTL (Arabisch), White-Label-Architektur '
            '(DB-gesteuerte Mandanten-Konfiguration), Live-Goldpreis-Engine mit '
            'Margen-System und Karat-/Altgold-Rechner; Docker-Deployment.',
            sty['bullet'],
        ),
    ]))

    # ── 5  IT-KENNTNISSE ─────────────────────────────────────────────────────
    story.extend(sec('IT-KENNTNISSE', sty))
    skills = [
        ('Backend',
         'C#, .NET Core, ASP.NET Core, Clean Architecture, EF Core, Web-Scraping, '
         'RESTful APIs, xUnit'),
        ('Frontend',
         'Angular (17/19), TypeScript, React 19, Tailwind CSS, NgRx, HTML, Bulma, '
         'Infragistics'),
        ('Datenbanken',
         'SQL Server, SQLite, PostgreSQL'),
        ('DevOps &amp; Tools',
         'Docker, GitHub Actions, Azure DevOps, Azure Cloud, '
         'SonarQube, Git, CI/CD, Python'),
        ('KI &amp; Analytics',
         'OpenAI API, Claude, Prompt Engineering, Tableau, Copilot'
         ),
    ]
    rows = [[Paragraph(b(l), sty['skill_lbl']),
             Paragraph(v, sty['skill_val'])] for l, v in skills]
    # Keine feste rowHeights: lange Skill-Werte dürfen umbrechen statt
    # abgeschnitten zu werden (Tabelle wächst automatisch mit dem Inhalt).
    sk = Table(rows, colWidths=[W * 0.21, W * 0.78])
    sk.setStyle(TableStyle([
        ('VALIGN',       (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING',  (0, 0), (0, -1),  8),
        ('LEFTPADDING',  (1, 0), (1, -1),  8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING',   (0, 0), (-1, -1), 1.6),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 1.6),
        ('LINEBELOW',    (0, 0), (-1, -1), 0.25, RULE_C),
        ('BACKGROUND',   (0, 0), (-1, 0), BG_SKILL),
        ('BACKGROUND',   (0, 1), (-1, 1), BG_SKILL2),
        ('BACKGROUND',   (0, 2), (-1, 2), BG_SKILL),
        ('BACKGROUND',   (0, 3), (-1, 3), BG_SKILL2),
        ('BACKGROUND',   (0, 4), (-1, 4), BG_SKILL),
    ]))
    story.append(sk)

    # ── 6  AUSBILDUNG ────────────────────────────────────────────────────────
    story.extend(sec('AUSBILDUNG', sty))
    edu = [
        ('05/2022 – 03/2023',
         'Zertifikat: Data Analytics',
         'Clarusway IT School'),
       
    ]

    # Fachinformatiker with Abschlussprojekt detail
    story.append(KeepTogether(entry_row(
        [Paragraph(
            'Fachinformatiker für Anwendungsentwicklung (IHK) — '
            'Walther-Rathenau-Gewerbeschule, Freiburg',
            sty['edu_title']),
         bul(
            b('Abschlussprojekt DI-Flux:')
            + ' Enterprise-Web-Zeiterfassung mit Angular, JWT-Auth, '
            'C#/.NET und SQL Server.',
            sty['edu_bullet']),
        ],
        '02/2024 – 02/2026', sty, CW, DW,
    )))
    story.append(Spacer(1, 0.1))

    for idx, (period, title, inst) in enumerate(edu):
        story.append(KeepTogether(entry_row(
            Paragraph(f'{title} — {inst}', sty['edu_title']),
            period, sty, CW, DW,
        )))
        if idx < len(edu) - 1:
            story.append(Spacer(1, 0.1))

    # ── 7  SPRACHEN ─────────────────────────────────────────────────────────
    story.extend([
        Spacer(1, 0.02 * cm),
        SectionHeading('SPRACHEN', sty['section']),
        Spacer(1, 1.0),
    ])
    lang_rows = [
        ('Türkisch',  'Muttersprache'),
        ('Deutsch',   'Fließend in Wort und Schrift'),
        ('Englisch',  'Fließend in Wort und Schrift'),
    ]
    lang_data = [[Paragraph(b(l), sty['skill_lbl']),
                  Paragraph(v, sty['skill_val'])] for l, v in lang_rows]
    lang_tbl = Table(lang_data, colWidths=[W * 0.21, W * 0.78])
    lang_tbl.setStyle(TableStyle([
        ('VALIGN',       (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING',  (0, 0), (0, -1),  8),
        ('LEFTPADDING',  (1, 0), (1, -1),  8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING',   (0, 0), (-1, -1), 1.6),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 1.6),
        ('LINEBELOW',    (0, 0), (-1, -1), 0.25, RULE_C),
        ('BACKGROUND',   (0, 0), (-1, 0), BG_SKILL),
        ('BACKGROUND',   (0, 1), (-1, 1), BG_SKILL2),
        ('BACKGROUND',   (0, 2), (-1, 2), BG_SKILL),
    ]))
    story.append(lang_tbl)

    # ── 8  UNTERSCHRIFT ─────────────────────────────────────────────────────
    story.append(Spacer(1, 0.04 * cm))
    if os.path.isfile(SIGNATUR_PATH):
        story.append(Image(SIGNATUR_PATH, width=2.8*cm, height=0.95*cm,
                           hAlign='LEFT'))
    story.append(Paragraph(f'Freiburg, {esc(cfg["datum"])}', sty['footer']))
    story.append(Paragraph('Hamza Öztürk', sty['footer']))


# ─── MAIN ────────────────────────────────────────────────────────────────────
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
        title='Lebenslauf – Hamza Öztürk',
        author='Hamza Öztürk',
        subject='Bewerbung als Fullstack Entwickler',
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
        title='Lebenslauf – Hamza Öztürk', author='Hamza Öztürk',
        subject=f'Bewerbung als {(cfg or {}).get("stelle", "Fullstack Entwickler")}',
        creator='Python / ReportLab',
    )
    story = []
    build(story, sty, doc.width, cfg)
    doc.build(story, onFirstPage=_draw_page, onLaterPages=_draw_page)
    return out


if __name__ == '__main__':
    sys.exit(main())
