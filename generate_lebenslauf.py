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
    'Ich digitalisiere <b>kaufmännische Geschäftsprozesse</b> – vom Papierbeleg '
    'über Datenmodell und API bis zum laufenden Betrieb. Als <b>Fachinformatiker '
    'für Anwendungsentwicklung (IHK)</b> verantworte ich bei Bike Haus Freiburg '
    'eine produktiv genutzte Warenwirtschafts- und Vermietungsplattform '
    '(<b>.NET 9, Angular 17</b>) auf einem selbst betriebenen Docker-Stack. '
    'Zuvor bei der Dicom GmbH: Migration eines ERP-Systems von WinForms auf '
    'eine Web-Lösung in Clean Architecture. Mit TypeScript und React decke ich '
    'auch den JavaScript-Stack ab.'
)


DEFAULT_CONFIG = {
    'stelle':        'Fullstack Entwickler',
    'datum':         datetime.now().strftime('%d.%m.%Y'),
    'kurzprofil':    DEFAULT_KURZPROFIL,
}

# ─── LEBENSLAUF-VARIANTEN ────────────────────────────────────────────────────
# Zwei Zuschnitte derselben (wahren) Laufbahn:
#   'fullstack'  – Entwicklerstellen: Architektur, Features, Code-Qualität.
#   'it-support' – IT-Support / IT-Administration: Systembetrieb, Anwender-
#                  betreuung, Netzwerk und Sicherheit; Entwicklung nur noch
#                  als technische Tiefe.
# Es werden KEINE neuen Fakten erfunden – dieselben Stationen werden anders
# gewichtet. Welche Variante greift, entscheidet erkenne_variante().
VARIANTE_FULLSTACK  = 'fullstack'
VARIANTE_IT_SUPPORT = 'it-support'
VARIANTEN = (VARIANTE_FULLSTACK, VARIANTE_IT_SUPPORT)

# Sprache des Lebenslaufs. Deutsch ist der Standard; Englisch wird genutzt,
# wenn die Stellenanzeige englisch ist oder es in der GUI eingestellt wird.
SPRACHE_DE = 'de'
SPRACHE_EN = 'en'

KURZPROFIL_IT_SUPPORT = (
    'Ich halte die IT eines Betriebs am Laufen – von der Anwenderfrage am '
    'Arbeitsplatz über Server, Mail und Netzwerk bis zur Dokumentation. Bei '
    'Bike Haus Freiburg verantworte ich die komplette Inhouse-IT: '
    '<b>Linux-Server</b> mit Docker und Nginx, eigener Mailserver mit '
    'DKIM/SPF/DMARC, automatisierte Backups und die tägliche Betreuung der '
    'Mitarbeitenden. Als <b>Fachinformatiker für Anwendungsentwicklung (IHK)</b> '
    'gehe ich dabei auf die Fehlerursache statt auf das Symptom – Logs und '
    'Datenbank zeigen mir, wo ein Fehler wirklich entsteht.'
)


_LNK_BIKEHAUS = (
    lnk('https://bikehausfreiburg.com', 'bikehausfreiburg.com')
    + '&#160;&#160;<font color="#1B3764">|</font>&#160;&#160;'
    + lnk('https://github.com/oeztuerkhamza/bikehausfreiburg', 'GitHub')
)


def _projekt_kopf(name, zusatz, status, url, label, repo):
    """Projektzeile: Name – Kurzbeschreibung (Status) + Links."""
    return (
        b(name) + zusatz
        + f' <font color="#1B3764">({status})</font>'
        + '&#160;&#160;' + lnk(url, label)
        + '&#160;&#160;<font color="#1B3764">|</font>&#160;&#160;'
        + lnk(repo, 'GitHub')
    )


_P_BENLIRAD = _projekt_kopf(
    'Benlirad', ' – Warenwirtschaft und Website für ein Fahrradgeschäft',
    'freiberuflich · Live', 'https://benlirad.de', 'benlirad.de',
    'https://github.com/oeztuerkhamza/benlirad')

_P_KULTUR = _projekt_kopf(
    'Kulturplattform Freiburg e.V.', '',
    'ehrenamtliche Arbeit · Live', 'https://kulturplattformfreiburg.org',
    'kulturplattformfreiburg.org',
    'https://github.com/oeztuerkhamza/KulturPlatform')

_P_DJVEYS = _projekt_kopf(
    'DJ Veys', ' – Website für DJ, Live-Musiker &amp; Moderator',
    'freiberuflich · Live', 'https://dj-veys.de', 'dj-veys.de',
    'https://github.com/oeztuerkhamza/veysl-music')


# ── Variante 1: Fullstack-Entwicklung (Standard) ────────────────────────────
ERFAHRUNG_FULLSTACK = [
    {
        'title':  'Bike Haus Freiburg – Full-Stack-Entwickler (Inhouse-Software)',
        'period': '03/2026 – heute',
        'sub':    _LNK_BIKEHAUS,
        'bullets': [
            'Warenwirtschafts- und Vermietungsplattform konzipiert, entwickelt '
            'und betrieben: <b>.NET 9</b>-API (40 Controller, 46 Entities), '
            'Angular 17 Admin-SPA und SSR-Homepage — produktiv im Tagesgeschäft.',

            'Beleglauf papierlos: Online-Buchung, PDF-Belege mit QR-Code, '
            'digitale Unterschrift, Kaution — <b>über 2.000 Belege</b> und '
            '405 Mietverträge in 2026.',

            'SEO-Ausbau der SSR-Homepage (12 Sprachen mit hreflang, '
            'Prerendering, IndexNow): <b>342.000 Impressionen und 13.000 '
            'organische Klicks in 6 Monaten</b>.',

            'KI-Assistenten für Gmail, WhatsApp und Kleinanzeigen '
            '(<b>OpenAI API</b>), Kleinanzeigen-Scraper mit Playwright, '
            'automatisierte Newsletter- und Backup-Services.',

            'Betrieb &amp; DevOps: 6-Container-Docker-Stack auf eigenem VPS, '
            '<b>GitHub Actions</b> CI/CD mit Zero-Downtime-Deployment, Nginx, '
            'eigener Mailserver (DKIM/SPF/DMARC).',
        ],
    },
    {
        'title':  'Dicom GmbH – Full-Stack Entwickler '
                  '(verkürzte duale Ausbildung, IHK)',
        'period': '02/2024 – 02/2026',
        'bullets': [
            'Migration eines kompletten ERP-Systems für den '
            '<b>Getränke-Großhandel</b> von WinForms zu einer C#/.NET- und '
            'Angular-Web-Lösung; Einführung einer Clean Architecture im Team.',

            'Gesamte Prozesskette umgesetzt: Stammdaten, Artikelverwaltung, '
            'Einkauf, Verkauf und Leergut-/Pfandabwicklung — von der '
            'Anforderungsanalyse bis zum Rollout beim Kunden.',

            'Datenbankmodelle neu aufgebaut und optimiert (<b>EF Core</b>, '
            'SQL Server); CI/CD mit GitHub Actions und Azure DevOps — '
            'Deployment-Zeit um <b>40 %</b> reduziert.',

            '<b>15+ Angular-Komponenten</b> mit NgRx und Reactive Forms; '
            'Unit- und Integrationstests mit xUnit und Moq, Testabdeckung '
            'auf über <b>60 %</b> gesteigert.',
        ],
    },
]


PROJEKTE_FULLSTACK = [
    {
        'head': _P_BENLIRAD,
        'bullets': [
            '<b>.NET 9</b>-API in Clean Architecture, Angular 17 Admin-SPA '
            'und SSR-Website, die den Bestand live aus derselben Datenbank '
            'zieht (EF Core, SQLite, JWT).',

            'Viersprachig (DE/EN/FR/TR) mit hreflang; Betrieb mit Docker und '
            'Nginx auf eigenem Server, Chrome-Erweiterung für die Pflege der '
            'Inserate.',
        ],
    },
    {
        'head': _P_KULTUR,
        'bullets': [
            '<b>.NET 10</b>, React 19, Docker Compose — Admin-Panel, '
            'Newsletter-System, Bildverarbeitung, DE/TR-Zweisprachigkeit.',
        ],
    },
    {
        'head': _P_DJVEYS,
        'bullets': [
            '<b>Next.js 16</b>/React 19 mit Payload CMS 3, TypeScript und '
            'Tailwind 4 — redaktionell pflegbare Inhalte, Anfragestrecke mit '
            'Zod-Validierung; 9-sprachig mit Landing-Pages je Region.',
        ],
    },
]


SKILLS_FULLSTACK = [
    ('Backend',
     'C#, .NET Core, ASP.NET Core, Clean Architecture, EF Core, Web-Scraping, '
     'RESTful APIs, xUnit'),
    ('Frontend',
     'Angular (17–19), TypeScript, React 19, Tailwind CSS, NgRx, HTML, '
     'Infragistics'),
    ('Datenbanken',
     'SQL Server, SQLite, PostgreSQL'),
    ('DevOps &amp; Tools',
     'Docker, GitHub Actions, Azure DevOps, Azure Cloud, '
     'Git, CI/CD, Python'),
    ('KI &amp; Analytics',
     'OpenAI API, Claude, Prompt Engineering'),
]


# ── Variante 2: IT-Support / IT-Administration ──────────────────────────────
ERFAHRUNG_IT_SUPPORT = [
    {
        'title':  'Bike Haus Freiburg – Inhouse-IT: Systembetrieb, '
                  'Anwenderbetreuung &amp; Entwicklung',
        'period': '03/2026 – heute',
        'sub':    _LNK_BIKEHAUS,
        'bullets': [
            'Betrieb der kompletten Firmen-IT: <b>Linux-Server</b> (VPS) mit '
            '6-Container-Docker-Stack, Nginx als Reverse Proxy (TLS, '
            'HSTS/CSP), automatisierte Backups und Monitoring.',

            'Eigener <b>Mailserver</b> (Mailcow) inklusive DNS-Einrichtung mit '
            'DKIM, SPF und DMARC: Postfächer, Weiterleitungen und Spam-Filter.',

            '<b>Anwenderbetreuung</b> im Tagesgeschäft: Einweisung der '
            'Mitarbeitenden, Störungsanalyse anhand von Logs und Datenbank, '
            'Umsetzung von Änderungswünschen.',

            'Papierlose Abläufe eingeführt (Online-Buchung, PDF-Belege mit '
            'QR-Code, digitale Unterschrift): <b>über 2.000 Belege</b> digital '
            'erzeugt (2026).',

            'Automatisierung und Entwicklung: <b>GitHub Actions</b> CI/CD mit '
            'Zero-Downtime-Deployment, Python-Skripte; die genutzte Plattform '
            '(.NET 9, Angular 17) selbst gebaut und gewartet.',
        ],
    },
    {
        'title':  'Dicom GmbH – Fachinformatiker für Anwendungsentwicklung '
                  '(verkürzte duale Ausbildung, IHK)',
        'period': '02/2024 – 02/2026',
        'bullets': [
            'ERP-Einführung für den <b>Getränke-Großhandel</b> bis zum Rollout '
            'beim Kunden begleitet: Fehlermeldungen aus dem Fachbereich '
            'aufgenommen, nachgestellt und behoben.',

            'Mitbetreuung der <b>Azure</b>-Umgebungen für Dev, Staging und '
            'Produktion; CI/CD mit GitHub Actions und Azure DevOps — '
            'Deployment-Zeit um <b>40 %</b> reduziert.',

            'Wartung und Fehleranalyse im laufenden ERP-Betrieb über die '
            'gesamte Prozesskette; Datenbankmodelle und Abfragen optimiert '
            '(<b>SQL Server</b>, EF Core).',

            'Qualitätssicherung im Team: Unit- und Integrationstests mit xUnit '
            'und Moq, Testabdeckung auf über <b>60 %</b> gesteigert.',
        ],
    },
]


PROJEKTE_IT_SUPPORT = [
    {
        'head': _P_BENLIRAD,
        'bullets': [
            'Betrieb auf eigenem Server mit <b>Docker</b> und Nginx: '
            'Deployment, TLS-Zertifikate, Backups und laufende Wartung.',

            'Viersprachig (DE/EN/FR/TR); .NET 9-API und Angular 17 greifen auf '
            'dieselbe Datenbank zu, Chrome-Erweiterung für die Inserate.',
        ],
    },
    {
        'head': _P_KULTUR,
        'bullets': [
            '<b>.NET 10</b>, React 19 und Docker Compose — Aufbau und Betrieb '
            'inklusive Admin-Panel und Newsletter-System; ehrenamtlich betreut.',
        ],
    },
    {
        'head': _P_DJVEYS,
        'bullets': [
            '<b>Next.js 16</b> mit Payload CMS 3: redaktionell pflegbare '
            'Inhalte, 9-sprachig — Betrieb und Updates laufend betreut.',
        ],
    },
]


SKILLS_IT_SUPPORT = [
    ('Systeme &amp; Server',
     'Linux (Ubuntu/Debian, VPS), Windows, Docker &amp; Docker Compose, '
     'Nginx (Reverse Proxy), Azure Cloud'),
    ('Netzwerk &amp; Sicherheit',
     "TLS/Let's Encrypt, HSTS/CSP, Rate Limiting, DNS (A/MX/SPF/DKIM/DMARC), "
     'Backup- und Wiederherstellungskonzepte'),
    ('Mail &amp; Anwender',
     'Mailcow (Postfix/Dovecot), IMAP/SMTP, Postfach- und Kontenverwaltung, '
     'Anwendereinweisung, Störungsanalyse'),
    ('Automatisierung',
     'Python, Bash, Git, GitHub Actions, Azure DevOps, CI/CD, '
     'Playwright (Web-Scraping)'),
    ('Datenbanken',
     'SQL Server, SQLite, PostgreSQL – Abfragen, Migrationen, Backups'),
    ('Entwicklung',
     'C#, .NET Core, ASP.NET Core, EF Core, Angular (17–19), TypeScript, '
     'React 19, OpenAI API'),
]


INHALT_DE = {
    VARIANTE_FULLSTACK: {
        'stelle':     'Fullstack Entwickler',
        'kurzprofil': DEFAULT_KURZPROFIL,
        'erfahrung':  ERFAHRUNG_FULLSTACK,
        'projekte':   PROJEKTE_FULLSTACK,
        'skills':     SKILLS_FULLSTACK,
    },
    VARIANTE_IT_SUPPORT: {
        'stelle':     'IT-Support / IT-Administration',
        'kurzprofil': KURZPROFIL_IT_SUPPORT,
        'erfahrung':  ERFAHRUNG_IT_SUPPORT,
        'projekte':   PROJEKTE_IT_SUPPORT,
        'skills':     SKILLS_IT_SUPPORT,
    },
}


# ─── VARIANTEN-ERKENNUNG ─────────────────────────────────────────────────────
# Stichworte aus Stellenanzeigen. Es zaehlt der fruehste Treffer im Titel:
# "IT-Administrator" -> Support, "Softwareentwickler" -> Fullstack.
# Bindestriche und Schraegstriche werden vorher zu Leerzeichen normalisiert,
# damit "IT-Support", "IT/Support" und "IT Support" gleich behandelt werden.
_KW_IT_SUPPORT = (
    'it support', 'itsupport', 'support mitarbeiter', 'support techniker',
    'supporter', 'helpdesk', 'help desk', 'servicedesk', 'service desk',
    '1st level', 'first level', '2nd level', 'second level',
    'anwendersupport', 'anwenderbetreuung', 'anwenderunterstuetzung',
    'benutzersupport', 'user support', 'desktop support', 'onsite support',
    'it administrator', 'it administration', 'systemadministrator',
    'system administrator', 'systemadministration', 'netzwerkadministrator',
    'netzwerkadministration', 'administrator', 'administration',
    'systembetreuer', 'systembetreuung', 'systemintegration',
    'systemelektroniker', 'it techniker', 'it servicetechniker',
    'it betreuung', 'it koordination', 'it koordinator', 'it operations',
    'edv betreuung', 'edv administrator', 'clientmanagement',
    'client management', 'client support', 'it fachkraft', 'it allrounder',
)

_KW_ENTWICKLUNG = (
    'softwareentwickler', 'software entwickler', 'software engineer',
    'anwendungsentwickler', 'anwendungsentwicklung', 'fullstack',
    'full stack', 'frontend entwickler', 'backend entwickler',
    'webentwickler', 'web entwickler', 'programmierer', 'developer',
    'entwickler', 'softwareentwicklung', 'software developer',
)


def _normalisiere(text):
    """Klein schreiben, Umlaute zu ASCII, Trennzeichen zu Leerzeichen."""
    t = (text or '').lower()
    for alt, neu in (('ä', 'ae'), ('ö', 'oe'), ('ü', 'ue'), ('ß', 'ss')):
        t = t.replace(alt, neu)
    for zeichen in '-–—_/|(),.:;!?*&\n\r\t':
        t = t.replace(zeichen, ' ')
    return ' ' + ' '.join(t.split()) + ' '


def _erster_treffer(text, keywords):
    """Kleinster Index, an dem eines der Stichworte vorkommt (oder None)."""
    treffer = [text.find(' ' + kw + ' ') for kw in keywords]
    treffer += [text.find(' ' + kw) for kw in keywords]
    treffer = [i for i in treffer if i >= 0]
    return min(treffer) if treffer else None


def _anzahl_treffer(text, keywords):
    return sum(text.count(' ' + kw) for kw in keywords)


def erkenne_variante(*texte):
    """Bestimmt die Lebenslauf-Variante aus Stellentitel und Anzeigetext.

    Aufruf von 'wichtig' nach 'unwichtig', z.B.
    erkenne_variante(stelle, betreff, stellentext). Der erste Text, der eine
    Entscheidung erlaubt, gewinnt – so schlaegt der Stellentitel den
    Fliesstext der Anzeige, in dem oft beide Schwerpunkte vorkommen.
    """
    titel_texte = list(texte[:-1]) if len(texte) > 1 else list(texte)
    for text in titel_texte:
        norm = _normalisiere(text)
        if not norm.strip():
            continue
        i_sup = _erster_treffer(norm, _KW_IT_SUPPORT)
        i_dev = _erster_treffer(norm, _KW_ENTWICKLUNG)
        if i_sup is not None and (i_dev is None or i_sup < i_dev):
            return VARIANTE_IT_SUPPORT
        if i_dev is not None:
            return VARIANTE_FULLSTACK

    # Kein Titel-Treffer: im langen Anzeigetext zaehlen, welcher Schwerpunkt
    # ueberwiegt. Support muss klar vorne liegen, sonst bleibt es beim
    # Standard-Lebenslauf.
    if len(texte) > 1:
        norm = _normalisiere(texte[-1])
        n_sup = _anzahl_treffer(norm, _KW_IT_SUPPORT)
        n_dev = _anzahl_treffer(norm, _KW_ENTWICKLUNG)
        if n_sup >= 2 and n_sup > n_dev:
            return VARIANTE_IT_SUPPORT
    return VARIANTE_FULLSTACK


# Werte, die in der GUI 'bitte selbst erkennen' bedeuten.
_AUTO_WERTE = ('', 'auto', 'automatik', 'automatisch')


def variante_aus_cfg(cfg):
    """Variante aus der Konfiguration: explizit gesetzt oder erkannt."""
    cfg = cfg or {}
    explizit = (cfg.get('variante') or '').strip().lower()
    if explizit in VARIANTEN:
        return explizit
    if explizit not in _AUTO_WERTE:
        # Auch 'IT-Support (m/w/d)' oder 'itsupport' akzeptieren.
        return erkenne_variante(explizit)
    return erkenne_variante(
        cfg.get('stelle'), cfg.get('betreff'), cfg.get('stellentext'))


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
]

# ── Englische Fassung: Kurzprofile ──────────────────────────────────────────
PROFILE_FULLSTACK_EN = (
    'I digitalise <b>commercial business processes</b> – from the paper '
    'document through data model and API to day-to-day operation. As a '
    'qualified <b>IT Specialist in Application Development (IHK)</b> I am '
    'responsible for a production inventory and rental platform at Bike Haus '
    'Freiburg (<b>.NET 9, Angular 17</b>) running on a self-hosted Docker '
    'stack. Before that at Dicom GmbH: migration of an ERP system from '
    'WinForms to a web solution in Clean Architecture. With TypeScript and '
    'React I also cover the JavaScript stack.'
)


PROFILE_IT_SUPPORT_EN = (
    "I keep a company's IT running – from the question at the user's desk "
    'through servers, mail and network to proper documentation. At Bike Haus '
    'Freiburg I am responsible for the entire in-house IT: <b>Linux servers</b> '
    'with Docker and Nginx, an own mail server with DKIM/SPF/DMARC, automated '
    'backups and day-to-day user support. As an <b>IT Specialist in '
    'Application Development (IHK)</b> I work towards the root cause instead '
    'of the symptom – logs and database show me where an error really '
    'originates.'
)



_P_BENLIRAD_EN = _projekt_kopf(
    'Benlirad', ' – inventory management and website for a bicycle shop',
    'freelance · live', 'https://benlirad.de', 'benlirad.de',
    'https://github.com/oeztuerkhamza/benlirad')

_P_KULTUR_EN = _projekt_kopf(
    'Kulturplattform Freiburg e.V.', '',
    'voluntary work · live', 'https://kulturplattformfreiburg.org',
    'kulturplattformfreiburg.org',
    'https://github.com/oeztuerkhamza/KulturPlatform')

_P_DJVEYS_EN = _projekt_kopf(
    'DJ Veys', ' – website for a DJ, live musician &amp; host',
    'freelance · live', 'https://dj-veys.de', 'dj-veys.de',
    'https://github.com/oeztuerkhamza/veysl-music')


# ── Englische Fassung: Variante 1 (Entwicklung) ─────────────────────────────
ERFAHRUNG_FULLSTACK_EN = [
    {
        'title':  'Bike Haus Freiburg – Full-Stack Developer (In-House Software)',
        'period': '03/2026 – present',
        'sub':    _LNK_BIKEHAUS,
        'bullets': [
            'Designed, built and operate an in-house inventory and rental '
            'platform: <b>.NET 9</b> API (40 controllers, 46 entities), '
            'Angular 17 admin SPA and SSR website — in productive daily use.',

            'Paperless document flow: online booking, PDF documents with QR '
            'code, digital signature, deposit — <b>more than 2,000 '
            'documents</b> and 405 rental contracts in 2026.',

            'SEO work on the SSR website (12 languages with hreflang, '
            'prerendering, IndexNow): <b>342,000 impressions and 13,000 '
            'organic clicks within 6 months</b>.',

            'AI assistants for Gmail, WhatsApp and Kleinanzeigen '
            '(<b>OpenAI API</b>), Kleinanzeigen scraper with Playwright, '
            'automated newsletter and backup services.',

            'Operations &amp; DevOps: 6-container Docker stack on an own VPS, '
            '<b>GitHub Actions</b> CI/CD with zero-downtime deployment, '
            'Nginx, own mail server (DKIM/SPF/DMARC).',
        ],
    },
    {
        'title':  'Dicom GmbH – Full-Stack Developer '
                  '(accelerated dual vocational training, IHK)',
        'period': '02/2024 – 02/2026',
        'bullets': [
            'Migrated a complete ERP system for <b>beverage wholesale</b> '
            'from WinForms to a C#/.NET and Angular web solution; introduced '
            'Clean Architecture within the team.',

            'Implemented the full business process chain: master data, '
            'article management, purchasing, sales and deposit handling — '
            'from requirements analysis to rollout at the customer.',

            'Rebuilt and optimised the database models (<b>EF Core</b>, '
            'SQL Server); CI/CD with GitHub Actions and Azure DevOps — '
            'deployment time reduced by <b>40%</b>.',

            '<b>15+ Angular components</b> with NgRx and reactive forms; '
            'unit and integration tests with xUnit and Moq, test coverage '
            'raised above <b>60%</b>.',
        ],
    },
]


PROJEKTE_FULLSTACK_EN = [
    {
        'head': _P_BENLIRAD_EN,
        'bullets': [
            '<b>.NET 9</b> API in Clean Architecture, Angular 17 admin SPA '
            'and SSR website that pulls the live stock from the same database '
            '(EF Core, SQLite, JWT).',

            'Four languages (DE/EN/FR/TR) with hreflang; operated with Docker '
            'and Nginx on an own server, Chrome extension for maintaining the '
            'listings.',
        ],
    },
    {
        'head': _P_KULTUR_EN,
        'bullets': [
            '<b>.NET 10</b>, React 19, Docker Compose — admin panel, '
            'newsletter system, image processing, DE/TR bilingual content.',
        ],
    },
    {
        'head': _P_DJVEYS_EN,
        'bullets': [
            '<b>Next.js 16</b>/React 19 with Payload CMS 3, TypeScript and '
            'Tailwind 4 — editorially maintainable content, enquiry flow with '
            'Zod validation; 9 languages with landing pages per region.',
        ],
    },
]


SKILLS_FULLSTACK_EN = [
    ('Backend',
     'C#, .NET Core, ASP.NET Core, Clean Architecture, EF Core, web scraping, '
     'RESTful APIs, xUnit'),
    ('Frontend',
     'Angular (17–19), TypeScript, React 19, Tailwind CSS, NgRx, HTML, '
     'Infragistics'),
    ('Databases',
     'SQL Server, SQLite, PostgreSQL'),
    ('DevOps &amp; tools',
     'Docker, GitHub Actions, Azure DevOps, Azure Cloud, Git, CI/CD, Python'),
    ('AI &amp; analytics',
     'OpenAI API, Claude, prompt engineering'),
]


# ── Englische Fassung: Variante 2 (IT-Support) ──────────────────────────────
ERFAHRUNG_IT_SUPPORT_EN = [
    {
        'title':  'Bike Haus Freiburg – In-House IT: Systems Operation, '
                  'User Support &amp; Development',
        'period': '03/2026 – present',
        'sub':    _LNK_BIKEHAUS,
        'bullets': [
            "Operating the company's entire IT: <b>Linux servers</b> (VPS) "
            'with a 6-container Docker stack, Nginx as reverse proxy (TLS, '
            'HSTS/CSP), automated backups and monitoring.',

            'Own <b>mail server</b> (Mailcow) including DNS setup with DKIM, '
            'SPF and DMARC: mailboxes, forwarding rules and spam filtering.',

            '<b>User support</b> in daily business: introducing staff to the '
            'systems, analysing incidents from logs and database, '
            'implementing change requests.',

            'Introduced paperless workflows (online booking, PDF documents '
            'with QR code, digital signature): <b>more than 2,000 '
            'documents</b> generated digitally (2026).',

            'Automation and development: <b>GitHub Actions</b> CI/CD with '
            'zero-downtime deployment, Python scripts; built and maintain the '
            'platform in use myself (.NET 9, Angular 17).',
        ],
    },
    {
        'title':  'Dicom GmbH – IT Specialist in Application Development '
                  '(accelerated dual vocational training, IHK)',
        'period': '02/2024 – 02/2026',
        'bullets': [
            'Supported the ERP rollout for <b>beverage wholesale</b> up to '
            'go-live at the customer: took in fault reports from the '
            'departments, reproduced and fixed them.',

            'Co-maintained the <b>Azure</b> environments for dev, staging and '
            'production; CI/CD with GitHub Actions and Azure DevOps — '
            'deployment time reduced by <b>40%</b>.',

            'Maintenance and fault analysis in live ERP operation across the '
            'whole process chain; optimised data models and queries '
            '(<b>SQL Server</b>, EF Core).',

            'Quality assurance within the team: unit and integration tests '
            'with xUnit and Moq, test coverage raised above <b>60%</b>.',
        ],
    },
]


PROJEKTE_IT_SUPPORT_EN = [
    {
        'head': _P_BENLIRAD_EN,
        'bullets': [
            'Operated on an own server with <b>Docker</b> and Nginx: '
            'deployment, TLS certificates, backups and ongoing maintenance.',

            'Four languages (DE/EN/FR/TR); .NET 9 API and Angular 17 share '
            'one database, Chrome extension for maintaining the listings.',
        ],
    },
    {
        'head': _P_KULTUR_EN,
        'bullets': [
            '<b>.NET 10</b>, React 19 and Docker Compose — built and operated '
            'including admin panel and newsletter system; maintained '
            'voluntarily.',
        ],
    },
    {
        'head': _P_DJVEYS_EN,
        'bullets': [
            '<b>Next.js 16</b> with Payload CMS 3: editorially maintainable '
            'content, 9 languages — operation and updates maintained '
            'continuously.',
        ],
    },
]


SKILLS_IT_SUPPORT_EN = [
    ('Systems &amp; servers',
     'Linux (Ubuntu/Debian, VPS), Windows, Docker &amp; Docker Compose, '
     'Nginx (reverse proxy), Azure Cloud'),
    ('Network &amp; security',
     "TLS/Let's Encrypt, HSTS/CSP, rate limiting, DNS (A/MX/SPF/DKIM/DMARC), "
     'backup and recovery concepts'),
    ('Mail &amp; users',
     'Mailcow (Postfix/Dovecot), IMAP/SMTP, mailbox and account '
     'administration, user onboarding, incident analysis'),
    ('Automation',
     'Python, Bash, Git, GitHub Actions, Azure DevOps, CI/CD, '
     'Playwright (web scraping)'),
    ('Databases',
     'SQL Server, SQLite, PostgreSQL – queries, migrations, backups'),
    ('Development',
     'C#, .NET Core, ASP.NET Core, EF Core, Angular (17–19), TypeScript, '
     'React 19, OpenAI API'),
]


INHALT_EN = {
    VARIANTE_FULLSTACK: {
        'stelle':     'Full-Stack Developer',
        'kurzprofil': PROFILE_FULLSTACK_EN,
        'erfahrung':  ERFAHRUNG_FULLSTACK_EN,
        'projekte':   PROJEKTE_FULLSTACK_EN,
        'skills':     SKILLS_FULLSTACK_EN,
    },
    VARIANTE_IT_SUPPORT: {
        'stelle':     'IT Support / IT Administration',
        'kurzprofil': PROFILE_IT_SUPPORT_EN,
        'erfahrung':  ERFAHRUNG_IT_SUPPORT_EN,
        'projekte':   PROJEKTE_IT_SUPPORT_EN,
        'skills':     SKILLS_IT_SUPPORT_EN,
    },
}

# Inhalte nach Sprache und Variante.
INHALT = {
    SPRACHE_DE: INHALT_DE,
    SPRACHE_EN: INHALT_EN,
}


# ─── AUSBILDUNG (englische Fassung) ─────────────────────────────────────────
BILDUNGSWEG_EN = [
    {
        'period': '02/2024 – 02/2026',
        'title':  'IT Specialist in Application Development (IHK) – '
                  'accelerated dual vocational training',
        'inst':   'Walther-Rathenau-Gewerbeschule, Freiburg · '
                  'Training company: Dicom GmbH',
        'detail': b('Final project DI-Flux:')
                  + ' enterprise web time tracking with Angular, JWT auth, '
                    'C#/.NET and SQL Server.',
    },
    {
        'period': '02/2023 – 12/2023',
        'title':  'German language training – C1 certificate',
        'inst':   'Deutschkolleg Stuttgart',
    },
    {
        'period': '05/2022 – 03/2023',
        'title':  'Certificate: Data Analytics &amp; Visualization (260 hours)',
        'inst':   'Clarusway IT School',
    },
    {
        'period': '10/2019 – 08/2022',
        'title':  'Industrial Engineering',
        'inst':   'Istanbul Technical University (İTÜ)',
    },
    {
        'period': '08/2015 – 07/2019',
        'title':  'Military Sciences',
        'inst':   'Turkish Air Force Academy, Istanbul',
    },
]


# ─── SPRACHABHAENGIGE BESCHRIFTUNGEN ────────────────────────────────────────
# Alles, was nicht aus INHALT kommt: Abschnittstitel, Kontaktzeilen,
# Ausbildung, Sprachtabelle und die PDF-Metadaten.
TEXTE = {
    SPRACHE_DE: {
        'h_profil':     'KURZPROFIL',
        'h_erfahrung':  'BERUFSERFAHRUNG',
        'h_projekte':   'PROJEKTE',
        'h_skills':     'IT-KENNTNISSE',
        'h_ausbildung': 'AUSBILDUNG',
        'h_sprachen':   'SPRACHEN',
        'c_geb':        '<font color="#1B3764"><b>Geb.:</b></font>&#160;'
                        '18.02.1996, Groß-Gerau'
                        '&#160;&#160;<font color="#1B3764">·</font>&#160;&#160;'
                        '<font color="#1B3764"><b>Führerschein:</b></font>'
                        '&#160;Klasse B',
        'c_visa':       '<font color="#1B3764"><b>Status:</b></font>&#160;'
                        'Aufenthalts- &amp; Arbeitserlaubnis',
        'bildungsweg':  BILDUNGSWEG,
        'sprachen': [
            ('Türkisch',  'Muttersprache'),
            ('Deutsch',   'C1 – verhandlungssicher (Sprachausbildung und '
                          'IHK-Ausbildung auf Deutsch abgeschlossen)'),
            ('Englisch',  'B2 – sicher in Wort und Schrift'),
        ],
        'pdf_titel':    'Lebenslauf – Hamza Öztürk',
        'pdf_betreff':  'Bewerbung als %s',
    },
    SPRACHE_EN: {
        'h_profil':     'PROFILE',
        'h_erfahrung':  'PROFESSIONAL EXPERIENCE',
        'h_projekte':   'PROJECTS',
        'h_skills':     'TECHNICAL SKILLS',
        'h_ausbildung': 'EDUCATION',
        'h_sprachen':   'LANGUAGES',
        'c_geb':        '<font color="#1B3764"><b>Born:</b></font>&#160;'
                        '18 Feb 1996, Groß-Gerau'
                        '&#160;&#160;<font color="#1B3764">·</font>&#160;&#160;'
                        '<font color="#1B3764"><b>Driving licence:</b></font>'
                        '&#160;category B',
        'c_visa':       '<font color="#1B3764"><b>Status:</b></font>&#160;'
                        'German residence &amp; work permit',
        'bildungsweg':  BILDUNGSWEG_EN,
        'sprachen': [
            ('Turkish',  'native speaker'),
            ('German',   'C1 – full professional proficiency (language '
                         'training and IHK vocational training completed '
                         'in German)'),
            ('English',  'B2 – confident in speech and writing'),
        ],
        'pdf_titel':    'Curriculum Vitae – Hamza Öztürk',
        'pdf_betreff':  'Application for %s',
    },
}

# Dateiname je Sprache und Variante (CLI-Aufruf ohne GUI).
OUTPUT_DATEI = {
    SPRACHE_DE: {
        VARIANTE_FULLSTACK:  'Hamza_Oeztuerk_Lebenslauf_Fullstack_Entwickler.pdf',
        VARIANTE_IT_SUPPORT: 'Hamza_Oeztuerk_Lebenslauf_IT_Support.pdf',
    },
    SPRACHE_EN: {
        VARIANTE_FULLSTACK:  'Hamza_Oeztuerk_CV_Full_Stack_Developer.pdf',
        VARIANTE_IT_SUPPORT: 'Hamza_Oeztuerk_CV_IT_Support.pdf',
    },
}


# ─── SPRACH-ERKENNUNG ───────────────────────────────────────────────────────
# Sehr haeufige Funktionswoerter. Eine Stellenanzeige ist lang genug, dass
# das Zaehlen reicht – einzelne englische Fachbegriffe in einem deutschen
# Text kippen die Entscheidung nicht.
_STOPP_DE = (
    'und', 'der', 'die', 'das', 'mit', 'fuer', 'wir', 'sie', 'ist', 'eine',
    'einen', 'zu', 'den', 'als', 'von', 'bei', 'im', 'auf', 'nicht', 'auch',
    'werden', 'haben', 'sind', 'oder', 'dem', 'des', 'ihre', 'unser',
)
_STOPP_EN = (
    'and', 'the', 'with', 'for', 'we', 'you', 'is', 'are', 'to', 'of', 'as',
    'our', 'your', 'in', 'on', 'not', 'also', 'have', 'will', 'or', 'their',
    'this', 'that', 'be', 'an',
)


def erkenne_sprache(*texte):
    """'en', wenn der Text klar englisch ist, sonst 'de' (Standard).

    Gedacht fuer den Volltext einer Stellenanzeige. Englisch muss deutlich
    ueberwiegen, damit aus einer deutschen Anzeige mit englischen Begriffen
    kein englischer Lebenslauf wird.
    """
    worte = []
    for text in texte:
        worte.extend(_normalisiere(text).split())
    if len(worte) < 20:
        return SPRACHE_DE
    n_de = sum(1 for w in worte if w in _STOPP_DE)
    n_en = sum(1 for w in worte if w in _STOPP_EN)
    if n_en >= 5 and n_en > n_de * 1.5:
        return SPRACHE_EN
    return SPRACHE_DE


def sprache_aus_cfg(cfg):
    """Sprache aus der Konfiguration: explizit gesetzt oder erkannt."""
    cfg = cfg or {}
    explizit = (cfg.get('sprache') or '').strip().lower()
    if explizit in INHALT:
        return explizit
    if explizit in ('englisch', 'english', 'en-gb', 'en-us'):
        return SPRACHE_EN
    if explizit in ('deutsch', 'german', 'de-de'):
        return SPRACHE_DE
    if explizit not in _AUTO_WERTE:
        return SPRACHE_DE
    # Ohne Vorgabe entscheidet der Text der Anzeige; ohne Anzeige Deutsch.
    return erkenne_sprache(cfg.get('stellentext') or '')


def _datum_englisch(datum):
    """'01.10.2026' -> '1 October 2026'. Unbekannte Formate bleiben, wie sie sind."""
    monate = ('January', 'February', 'March', 'April', 'May', 'June', 'July',
              'August', 'September', 'October', 'November', 'December')
    teile = (datum or '').strip().split('.')
    if len(teile) != 3:
        return datum
    try:
        tag, monat, jahr = int(teile[0]), int(teile[1]), int(teile[2])
    except ValueError:
        return datum
    if not 1 <= monat <= 12:
        return datum
    return '%d %s %d' % (tag, monate[monat - 1], jahr)

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
    for e in list(BILDUNGSWEG) + list(BILDUNGSWEG_EN):
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
    variante = variante_aus_cfg(cfg)
    sprache = sprache_aus_cfg(cfg)
    inhalt = INHALT[sprache][variante]
    texte = TEXTE[sprache]
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
    c_geb = texte['c_geb']
    c_visa = texte['c_visa']

    contact_table = Table(
        [
            [Paragraph(c_ort, sty['contact']), Paragraph(c_geb, sty['contact'])],
            [Paragraph(c_email, sty['contact']), Paragraph(c_tel, sty['contact'])],
            [Paragraph(c_linkedin, sty['contact']), Paragraph(c_github, sty['contact'])],
            [Paragraph(c_visa, sty['contact']), ''],
        ],
        colWidths=[HDR_W * 0.48, HDR_W * 0.52],
    )
    contact_table.setStyle(TableStyle([
        # Die Status-Angabe steht allein in der letzten Reihe. Ueber beide
        # Spalten gezogen liest sie sich als eigene Zeile statt als halb
        # leere Zelle neben einem Loch.
        ('SPAN',         (0, 3), (1, 3)),
        ('VALIGN',       (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING',  (0, 0), (0, -1),  0),
        ('LEFTPADDING',  (1, 0), (1, -1),  8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING',   (0, 0), (-1, -1), 0.5),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 0.5),
    ]))

    # Steht im Feld noch die Fullstack-Vorgabe, obwohl die Anzeige eine
    # Support-Stelle ist, greift die Bezeichnung der Support-Variante.
    stelle_titel = (cfg.get('stelle') or '').strip()
    if not stelle_titel or ((variante != VARIANTE_FULLSTACK
                             or sprache != SPRACHE_DE)
                            and stelle_titel == DEFAULT_CONFIG['stelle']):
        stelle_titel = inhalt['stelle']

    left_hdr = [
        Paragraph('Hamza Öztürk', sty['name']),
        Spacer(1, 2),
        Paragraph(
            esc(stelle_titel),
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
        SectionHeading(texte['h_profil'], sty['section']),
        Spacer(1, 1.0),
    ])
    # Gleiche Logik wie beim Stellentitel: unveraendertes Standard-Kurzprofil
    # wird fuer die Support-Variante durch deren Kurzprofil ersetzt.
    kurzprofil = (cfg.get('kurzprofil') or '').strip()
    if not kurzprofil or kurzprofil == DEFAULT_KURZPROFIL.strip():
        kurzprofil = inhalt['kurzprofil']
    elif sprache == SPRACHE_EN and erkenne_sprache(kurzprofil) == SPRACHE_DE:
        # Deutscher KI-Text im englischen Lebenslauf waere ein Sprachmix –
        # dann lieber das englische Standardprofil der Variante.
        kurzprofil = inhalt['kurzprofil']
    story.append(Paragraph(esc_rich(kurzprofil), sty['profile']))

    # ── 3  BERUFSERFAHRUNG ───────────────────────────────────────────────────
    story.extend(sec(texte['h_erfahrung'], sty))

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

    for idx, job in enumerate(inhalt['erfahrung']):
        block = [exp_header(job['title'], job['period'])]
        if job.get('sub'):
            block.append(Paragraph(job['sub'], sty['entry_sub']))
        block.extend(bul(t, sty['bullet']) for t in job['bullets'])
        story.append(KeepTogether(block))
        if idx < len(inhalt['erfahrung']) - 1:
            story.append(Spacer(1, 2))

    # ── 4  PROJEKTE ──────────────────────────────────────────────────────────
    story.extend(sec(texte['h_projekte'], sty))
    # Gleicher Abstand wie zwischen den Stationen der Berufserfahrung: ohne
    # ihn laufen die drei Projekte optisch zu einem Block zusammen.
    for idx, projekt in enumerate(inhalt['projekte']):
        story.append(KeepTogether(
            [Paragraph(projekt['head'], sty['entry_title'])]
            + [bul(t, sty['bullet']) for t in projekt['bullets']]
        ))
        if idx < len(inhalt['projekte']) - 1:
            story.append(Spacer(1, 2))

    # ── 5  IT-KENNTNISSE ─────────────────────────────────────────────────────
    story.extend(sec(texte['h_skills'], sty))
    rows = [[Paragraph(b(l), sty['skill_lbl']),
             Paragraph(v, sty['skill_val'])] for l, v in inhalt['skills']]
    # Keine feste rowHeights: lange Skill-Werte dürfen umbrechen statt
    # abgeschnitten zu werden (Tabelle wächst automatisch mit dem Inhalt).
    sk = Table(rows, colWidths=[W * 0.21, W * 0.78])
    sk_style = [
        ('VALIGN',       (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING',  (0, 0), (0, -1),  8),
        ('LEFTPADDING',  (1, 0), (1, -1),  8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING',   (0, 0), (-1, -1), 1.2),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 1.2),
        ('LINEBELOW',    (0, 0), (-1, -1), 0.25, RULE_C),
    ]
    # Zebra-Streifen für beliebig viele Zeilen – die Support-Variante hat
    # eine Kategorie mehr als die Fullstack-Variante.
    for i in range(len(rows)):
        sk_style.append(('BACKGROUND', (0, i), (-1, i),
                         BG_SKILL if i % 2 == 0 else BG_SKILL2))
    sk.setStyle(TableStyle(sk_style))
    story.append(sk)

    # ── 6  AUSBILDUNG ──────────────────────────────────────────────
    story.extend(sec(texte['h_ausbildung'], sty))
    bildungsweg = texte['bildungsweg']
    for idx, e in enumerate(bildungsweg):
        head = b(e['title'])
        if e.get('inst'):
            head += ' — ' + e['inst']
        left = [Paragraph(head, sty['edu_title'])]
        if e.get('detail'):
            left.append(bul(e['detail'], sty['edu_bullet']))
        story.append(KeepTogether(entry_row(left, e['period'], sty, CW, DW)))
        if idx < len(bildungsweg) - 1:
            story.append(Spacer(1, 0.1))


    # ── 7  SPRACHEN ─────────────────────────────────────────────────────────
    story.extend([
        Spacer(1, 0.02 * cm),
        SectionHeading(texte['h_sprachen'], sty['section']),
        Spacer(1, 1.0),
    ])
    lang_rows = texte['sprachen']
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
    datum_txt = (cfg['datum'] if sprache == SPRACHE_DE
                 else _datum_englisch(cfg['datum']))
    story.append(Paragraph(f'Freiburg, {esc(datum_txt)}', sty['footer']))
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
        title=TEXTE[sprache_aus_cfg(cfg)]['pdf_titel'], author='Hamza Öztürk',
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
    # Argumente = Stellenbezeichnung, Variante und/oder Sprache, z.B.
    #   py generate_lebenslauf.py "IT-Administrator (m/w/d)"
    #   py generate_lebenslauf.py it-support
    #   py generate_lebenslauf.py en "IT Support Specialist"
    #   py generate_lebenslauf.py en it-support
    # Ohne Argument wird der Standard-Lebenslauf (Fullstack, deutsch) gebaut.
    woerter = [w for w in sys.argv[1:] if w.strip()]
    sprache = SPRACHE_DE
    rest = []
    for w in woerter:
        if w.strip('-').lower() in ('en', 'english', 'englisch'):
            sprache = SPRACHE_EN
        elif w.strip('-').lower() in ('de', 'german', 'deutsch'):
            sprache = SPRACHE_DE
        else:
            rest.append(w)
    argument = ' '.join(rest).strip()
    variante = erkenne_variante(argument) if argument else VARIANTE_FULLSTACK
    stelle = argument if argument and argument.lower() not in VARIANTEN \
        else INHALT[sprache][variante]['stelle']
    out = os.path.join(BASE_DIR, OUTPUT_DATEI[sprache][variante])
    cfg = {'variante': variante, 'sprache': sprache, 'stelle': stelle}

    os.makedirs(os.path.dirname(out), exist_ok=True)
    register_fonts()
    _cprint('  Sprache: %s   Variante: %s  (%s)' % (sprache, variante, stelle))
    seiten, tighten = _passt_auf_eine_seite(
        out, cfg, TEXTE[sprache]['pdf_betreff'] % stelle)
    if tighten:
        _cprint('  (Zeilenabstand um %.1f pt nachgezogen, damit es auf eine '
                'Seite passt)' % tighten)
    if seiten > 1:
        _cprint('  !! Passt trotz Nachziehen nicht auf eine Seite (%d Seiten).'
                % seiten)
    print(f"PDF erfolgreich erstellt:\n  {out}")
    warne_offene_punkte()
    return 0


def generate(output_path=None, cfg=None):
    """Public API – called from the GUI app."""
    register_fonts()
    out = output_path or OUTPUT
    os.makedirs(os.path.dirname(out), exist_ok=True)
    sprache = sprache_aus_cfg(cfg)
    variante = variante_aus_cfg(cfg)
    stelle = ((cfg or {}).get('stelle') or '').strip() \
        or INHALT[sprache][variante]['stelle']
    _passt_auf_eine_seite(out, cfg, TEXTE[sprache]['pdf_betreff'] % stelle)
    return out


if __name__ == '__main__':
    sys.exit(main())
