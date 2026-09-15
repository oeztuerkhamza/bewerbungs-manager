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
B_MARGIN  = 0.5 * cm
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

    # Ohne Familie greifen <b>/<i> im Fliesstext ins Leere: ReportLab findet
    # dann keine fette/kursive Variante und setzt alles normal.
    pdfmetrics.registerFontFamily(
        'CV-R', normal='CV-R', bold='CV-B', italic='CV-I', boldItalic='CV-BI')
    pdfmetrics.registerFontFamily(
        'CV-B', normal='CV-B', bold='CV-B', italic='CV-BI', boldItalic='CV-BI')


# ─── PARAGRAPH STYLES ────────────────────────────────────────────────────────
def make_styles(tighten=0.0):
    """tighten zieht jeden Zeilenabstand um X pt nach – siehe _passt_auf_eine_seite."""
    def ps(name, font='CV-R', size=10, color=DARK, leading=None,
           spaceBefore=0, spaceAfter=0, align=TA_LEFT, leftIndent=0, **kw):
        lead = leading or round(size * 1.4, 1)
        lead = max(size + 0.4, lead - tighten)
        return ParagraphStyle(
            name, fontName=font, fontSize=size, textColor=color,
            leading=lead,
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
        'bullet':      ps('bullet',      'CV-R', 8.1, DARK, leading=8.6,
                          spaceAfter=0.1, leftIndent=15, align=TA_LEFT,
                          bulletIndent=6, bulletFontName='CV-R',
                          bulletFontSize=8.1, bulletColor=NAVY),
        'profile':     ps('profile',     'CV-R', 8.3, DARK, leading=9.8,
                          spaceAfter=0.2, leftIndent=8, align=TA_LEFT),
        'footer':      ps('footer',      'CV-R', 8, LGRAY, leading=10, spaceBefore=0.5),
        'skill_lbl':   ps('skill_lbl',   'CV-B', 8.3, NAVY, leading=10.2),
        'skill_val':   ps('skill_val',   'CV-R', 8.2, DARK, leading=10.2),
        # Ausbildung-specific (lower indent to keep current alignment)
        'edu_title':   ps('edu_title',   'CV-R', 8.8, DARK, leading=10.8, leftIndent=4),
        'edu_bullet':  ps('edu_bullet',  'CV-R', 8.1, DARK, leading=9.3,
                          spaceAfter=0.2, leftIndent=11, align=TA_LEFT,
                          bulletIndent=3, bulletFontName='CV-R',
                          bulletFontSize=8.1, bulletColor=NAVY),
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
    """Aufzählung mit echtem Hängeeinzug: Folgezeilen stehen unter dem
    Text, nicht unter dem Punkt."""
    return Paragraph(text, sty, bulletText=chr(0x2022))

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
    canvas.restoreState()


# ─── DEFAULT CONFIG ──────────────────────────────────────────────────────────
DEFAULT_KURZPROFIL = (
    'Full-Stack-Entwickler mit Schwerpunkt auf der <b>Digitalisierung von '
    'Geschäftsprozessen</b> — vom bisherigen Papierweg über Datenmodell, API '
    'und Frontend bis zum laufenden Cloud-Betrieb. Technischer Kern: '
    '<b>C#/.NET</b>, <b>Angular</b>, <b>Docker/Azure</b> und <b>CI/CD</b>. '
    'Aktuell verantwortlich für eine selbst entwickelte Warenwirtschafts- und '
    'Vermietungsplattform, die Vermietung, An- und Verkauf eines Handels'
    'betriebs vollständig papierlos abwickelt; zuvor Mitarbeit an der '
    'Migration eines ERP-Systems für den Getränke-Großhandel von WinForms in '
    'eine Web-Architektur — mit messbaren Ergebnissen in Durchlaufzeit, '
    'Performance und Code-Qualität.'
)

DEFAULT_CONFIG = {
    'stelle':        'Fullstack Entwickler',
    'datum':         datetime.now().strftime('%d.%m.%Y'),
    'kurzprofil':    DEFAULT_KURZPROFIL,
}


# ─── BILDUNGSWEG ────────────────────────────────────────────────
# Marker fuer noch unbestaetigte Angaben. Solange einer davon im Lebenslauf
# steht, warnt der Build – so geht nichts Unfertiges an einen Arbeitgeber raus.
TODO = '‹?›'

# Chronologisch absteigend. 'inst' und 'detail' sind optional.
BILDUNGSWEG = [
    {
        'period': '02/2024 – 02/2026',
        'title':  'Fachinformatiker für Anwendungsentwicklung (IHK) – '
                  'verkürzte duale Ausbildung',
        'inst':   'Walther-Rathenau-Gewerbeschule, Freiburg · '
                  'Ausbildungsbetrieb: Dicom GmbH',
        'detail': b('Abschlussprojekt DI-Flux:')
                  + ' Enterprise-Web-Zeiterfassung mit Angular, JWT-Auth, '
                    'C#/.NET und SQL Server.',
    },
    {
        'period': '02/2023 – 12/2023',
        'title':  'Deutsch-Sprachausbildung – Abschluss C1',
        'inst':   'Deutschkolleg Stuttgart',
    },
    {
        'period': '05/2022 – 03/2023',
        'title':  'Zertifikat: Data Analytics &amp; Visualization (260 Std.)',
        'inst':   'Clarusway IT School',
    },
    {
        'period': '10/2019 – 08/2022',
        'title':  'Wirtschaftsingenieurwesen',
        'inst':   'Technische Universität Istanbul (İTÜ)',
    },
    {
        'period': '08/2015 – 07/2019',
        'title':  'Militärwissenschaften',
        'inst':   'Türkische Luftwaffenakademie, Istanbul',
    },
    {
        'period': '2010 – 2015',
        'title':  'Schulabschluss (Lise-Diplom)',
        'inst':   'Işıklar Militärgymnasium der Luftwaffe, Bursa (Türkei)',
    },
]

# Widersprueche und fehlende Angaben, die NICHT im PDF stehen, aber vor dem
# Versand geklaert werden muessen. Werden beim Build ausgegeben.
# Bewusst NICHT im Lebenslauf: IHK-Abschlussnote 2,8 (befriedigend). Note wird
# nur genannt, wenn sie gut ist; die Zeugnisse liegen der Bewerbung ohnehin bei.
# Alles bestätigt. Neue offene Punkte hier eintragen, sie werden nach dem
# Build ausgegeben (siehe warne_offene_punkte).
OFFENE_FRAGEN = []


def _cprint(text):
    """Konsolenausgabe, die auch bei cp1252-Terminals nicht abstürzt."""
    enc = (getattr(sys.stdout, 'encoding', None) or 'ascii')
    print(text.encode(enc, 'replace').decode(enc, 'replace'))


def warne_offene_punkte():
    """Gibt Platzhalter und offene Fragen nach dem Build auf der Konsole aus."""
    offen = []
    for e in BILDUNGSWEG:
        txt = ''.join(str(e.get(k) or '') for k in ('period', 'title', 'inst', 'detail'))
        if TODO in txt:
            offen.append('{}  {}'.format(e['period'], e['title']))
    if offen:
        _cprint('')
        _cprint('  !! Noch unbestaetigte Angaben IM PDF (' + TODO + '):')
        for o in offen:
            _cprint('     - ' + o)
    if OFFENE_FRAGEN:
        _cprint('')
        _cprint('  !! Vor dem Versand klaeren:')
        for f in OFFENE_FRAGEN:
            _cprint('     - ' + f)
    if offen or OFFENE_FRAGEN:
        print('')


# ─── BUILD STORY ─────────────────────────────────────────────────────────────
def build(story, sty, W, cfg=None):
    cfg = {**DEFAULT_CONFIG, **(cfg or {})}
    DW = W * 0.20
    CW = W - DW - 0.3 * cm
    DW_EXP = W * 0.13
    CW_EXP = W - DW_EXP

    # ── 1  HEADER ────────────────────────────────────────────────────────────
    PHOTO_D = 2.85 * cm         # Durchmesser des runden Portraits
    PHOTO_W = PHOTO_D
    HDR_W   = W - PHOTO_W - 1.0 * cm

    # Contact info with bold navy label prefixes – each on its own line
    c_ort = (
        icon_prefix(ICON_LOCATION, '⌂:') + '&#160;'
        'Bissierstr. 16, 79114 Freiburg'
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
        '18.02.1996, Groß-Gerau'
        '&#160;&#160;<font color="#1B3764">·</font>&#160;&#160;'
        '<font color="#1B3764"><b>Führerschein:</b></font>&#160;Klasse B'
    )
    c_visa = (
        '<font color="#1B3764"><b>Status:</b></font>&#160;'
        'Aufenthalts- &amp; Arbeitserlaubnis'
    )

    contact_table = Table(
        [
            [Paragraph(c_ort, sty['contact']), Paragraph(c_geb, sty['contact'])],
            [Paragraph(c_email, sty['contact']), Paragraph(c_tel, sty['contact'])],
            [Paragraph(c_linkedin, sty['contact']), Paragraph(c_github, sty['contact'])],
            [Paragraph(c_website, sty['contact']), Paragraph(c_visa, sty['contact'])],
        ],
        colWidths=[HDR_W * 0.48, HDR_W * 0.52],
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
        exp_header('Bike Haus Freiburg – Full-Stack Entwickler (Festanstellung)',
                   '03/2026 – heute'),
        Paragraph(
            lnk('https://bikehausfreiburg.com', 'bikehausfreiburg.com')
            + '&#160;&#160;<font color="#1B3764">|</font>&#160;&#160;'
            + lnk('https://github.com/oeztuerkhamza/bikehausfreiburg', 'GitHub'),
            sty['entry_sub'],
        ),
        bul(
            'Konzeption, Entwicklung und Betrieb einer eigenen Warenwirtschafts- '
            'und Vermietungsplattform: <b>.NET 10</b>-API (40 Controller, '
            '46 Domain-Entities, 130+ EF-Core-Migrationen), <b>Angular 22</b> '
            'Admin-SPA und SSR-Homepage — im täglichen Geschäftsbetrieb produktiv.',
            sty['bullet'],
        ),
        bul(
            'Vermietung und Warenwirtschaft papierlos abgewickelt (Online-Buchung, '
            'PDF-Belege mit QR-Code, digitale Unterschrift, Kaution, automatische '
            'E-Mails): <b>405 Mietverträge mit 35.000 € Mietumsatz</b>, 696 Ankäufe '
            'und 990 Verkäufe '
            '— über 2.000 Belege digital erzeugt (2026).',
            sty['bullet'],
        ),
        bul(
            'SEO-Ausbau der SSR-Homepage (12 Sprachen mit hreflang, Prerendering, '
            'IndexNow, stadtbasierte Landing-Pages): in 6 Monaten auf '
            '<b>342.000 Impressionen und 13.000 Klicks</b> gewachsen '
            '(CTR 3,8 %, Ø-Position 9).',
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
        exp_header('Dicom GmbH – Full-Stack Entwickler '
                   '(verkürzte duale Ausbildung, IHK)', '02/2024 – 02/2026'),
        bul(
            'Mitarbeit an der Migration eines kompletten ERP-Systems für den '
            '<b>Getränke-Großhandel</b> von WinForms zu einer '
            '<b>C#/.NET 10</b> + <b>Angular 19</b> Web-Lösung; Einführung einer '
            '<b>Clean Architecture</b> und modularen API-Struktur im Team.',
            sty['bullet'],
        ),
        bul(
            'Fachlich über die gesamte Prozesskette umgesetzt: '
            '<b>Stammdaten, Artikelverwaltung, Einkauf, Verkauf und '
            'Leergut-/Pfandabwicklung</b> — von der Anforderungsanalyse über '
            'die Entwicklung bis zum Rollout beim Kunden.',
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
            'Mitbetreuung der <b>Azure</b>-Umgebungen (Dev/Staging/Prod); '
            'REST-APIs inkl. KI-gestützter Tools zur Beschleunigung von '
            'Entwicklungszyklen.',
            sty['bullet'],
        ),
    ]))

    # ── 4  PROJEKTE ──────────────────────────────────────────────────────────
    story.extend(sec('PROJEKTE', sty))

    # — Kulturplattform (ehrenamtlich)
    story.append(KeepTogether([
        Paragraph(
            b('Kulturplattform Freiburg e.V.')
            + ' <font color="#1B3764">(ehrenamtliche Arbeit · Live)</font>'
            + '&#160;&#160;'
            + lnk('https://kulturplattformfreiburg.org',
                  'kulturplattformfreiburg.org')
            + '&#160;&#160;<font color="#1B3764">|</font>&#160;&#160;'
            + lnk('https://github.com/oeztuerkhamza/KulturPlatform',
                  'GitHub'),
            sty['entry_title'],
        ),
        bul(
            '<b>.NET 10</b>, <b>React 19</b>, Docker Compose — '
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
            + ' <font color="#1B3764">(freiberuflich · Live)</font>'
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
         'Angular (19–22), TypeScript, React 19, Tailwind CSS, NgRx, HTML, '
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
        ('TOPPADDING',   (0, 0), (-1, -1), 1.2),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 1.2),
        ('LINEBELOW',    (0, 0), (-1, -1), 0.25, RULE_C),
        ('BACKGROUND',   (0, 0), (-1, 0), BG_SKILL),
        ('BACKGROUND',   (0, 1), (-1, 1), BG_SKILL2),
        ('BACKGROUND',   (0, 2), (-1, 2), BG_SKILL),
        ('BACKGROUND',   (0, 3), (-1, 3), BG_SKILL2),
        ('BACKGROUND',   (0, 4), (-1, 4), BG_SKILL),
    ]))
    story.append(sk)

    # ── 6  AUSBILDUNG ──────────────────────────────────────────────
    story.extend(sec('AUSBILDUNG', sty))
    for idx, e in enumerate(BILDUNGSWEG):
        head = b(e['title'])
        if e.get('inst'):
            head += ' — ' + e['inst']
        left = [Paragraph(head, sty['edu_title'])]
        if e.get('detail'):
            left.append(bul(e['detail'], sty['edu_bullet']))
        story.append(KeepTogether(entry_row(left, e['period'], sty, CW, DW)))
        if idx < len(BILDUNGSWEG) - 1:
            story.append(Spacer(1, 0.1))


    # ── 7  SPRACHEN ─────────────────────────────────────────────────────────
    story.extend([
        Spacer(1, 0.02 * cm),
        SectionHeading('SPRACHEN', sty['section']),
        Spacer(1, 1.0),
    ])
    lang_rows = [
        ('Türkisch',  'Muttersprache'),
        ('Deutsch',   'C1 – verhandlungssicher (Sprachausbildung und '
                      'IHK-Ausbildung auf Deutsch abgeschlossen)'),
        ('Englisch',  'B2 – sicher in Wort und Schrift'),
    ]
    lang_data = [[Paragraph(b(l), sty['skill_lbl']),
                  Paragraph(v, sty['skill_val'])] for l, v in lang_rows]
    lang_tbl = Table(lang_data, colWidths=[W * 0.21, W * 0.78])
    lang_tbl.setStyle(TableStyle([
        ('VALIGN',       (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING',  (0, 0), (0, -1),  8),
        ('LEFTPADDING',  (1, 0), (1, -1),  8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING',   (0, 0), (-1, -1), 1.2),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 1.2),
        ('LINEBELOW',    (0, 0), (-1, -1), 0.25, RULE_C),
        ('BACKGROUND',   (0, 0), (-1, 0), BG_SKILL),
        ('BACKGROUND',   (0, 1), (-1, 1), BG_SKILL2),
        ('BACKGROUND',   (0, 2), (-1, 2), BG_SKILL),
    ]))
    story.append(lang_tbl)

    # ── 8  UNTERSCHRIFT ─────────────────────────────────────────────────────
    story.append(Spacer(1, 0.04 * cm))
    if os.path.isfile(SIGNATUR_PATH):
        story.append(Image(SIGNATUR_PATH, width=2.5*cm, height=0.85*cm,
                           hAlign='LEFT'))
    story.append(Paragraph(f'Freiburg, {esc(cfg["datum"])}', sty['footer']))
    story.append(Paragraph('Hamza Öztürk', sty['footer']))


# ─── SEITENANPASSUNG ─────────────────────────────────────────────────────────
# Der Inhalt passt knapp auf eine Seite. Wird aus der GUI ein längeres
# Kurzprofil übergeben, wird der Zeilenabstand stufenweise nachgezogen,
# statt eine zweite Seite mit nur der Unterschrift anzufangen.
_FIT_STUFEN = (0.0, 0.2, 0.4, 0.6, 0.8, 1.0)


def _baue_pdf(out, cfg, tighten, subject):
    """Baut das PDF einmal und gibt die Seitenzahl zurück."""
    doc = SimpleDocTemplate(
        out, pagesize=A4,
        leftMargin=L_MARGIN, rightMargin=R_MARGIN,
        topMargin=T_MARGIN, bottomMargin=B_MARGIN,
        title='Lebenslauf – Hamza Öztürk', author='Hamza Öztürk',
        subject=subject, creator='Python / ReportLab',
    )
    story = []
    build(story, make_styles(tighten), doc.width, cfg)
    doc.build(story, onFirstPage=_draw_page, onLaterPages=_draw_page)
    return doc.page


def _passt_auf_eine_seite(out, cfg, subject):
    """Baut das PDF und zieht nach, bis es auf eine Seite passt.

    Gibt (seiten, tighten) des zuletzt geschriebenen PDFs zurück.
    """
    seiten = 0
    for tighten in _FIT_STUFEN:
        seiten = _baue_pdf(out, cfg, tighten, subject)
        if seiten <= 1:
            return seiten, tighten
    return seiten, _FIT_STUFEN[-1]


# ─── MAIN ────────────────────────────────────────────────────────────────────
def main():
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    register_fonts()
    seiten, tighten = _passt_auf_eine_seite(
        OUTPUT, None, 'Bewerbung als Fullstack Entwickler')
    if tighten:
        _cprint('  (Zeilenabstand um %.1f pt nachgezogen, damit es auf eine '
                'Seite passt)' % tighten)
    if seiten > 1:
        _cprint('  !! Passt trotz Nachziehen nicht auf eine Seite (%d Seiten).'
                % seiten)
    print(f"PDF erfolgreich erstellt:\n  {OUTPUT}")
    warne_offene_punkte()
    return 0


def generate(output_path=None, cfg=None):
    """Public API – called from the GUI app."""
    register_fonts()
    out = output_path or OUTPUT
    os.makedirs(os.path.dirname(out), exist_ok=True)
    _passt_auf_eine_seite(
        out, cfg,
        f'Bewerbung als {(cfg or {}).get("stelle", "Fullstack Entwickler")}')
    return out


if __name__ == '__main__':
    sys.exit(main())
