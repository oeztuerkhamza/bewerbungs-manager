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
    BaseDocTemplate, PageTemplate, Frame, FrameBreak,
    Paragraph, Spacer, KeepTogether, Image, Flowable,
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

# ─── LAYOUT ──────────────────────────────────────────────────────────────────
L_MARGIN  = 1.30 * cm
R_MARGIN  = 1.30 * cm
T_MARGIN  = 0.95 * cm
B_MARGIN  = 0.75 * cm
SEC_GAP   = 0.38 * cm

# Die dunkle Spalte laeuft randabfallend von x=0 bis RAIL_BG_W ueber die
# ganze Seitenhoehe; das Foto sitzt oben darin, ebenfalls randabfallend.
RAIL_BG_W = 6.10 * cm          # Breite der Farbflaeche
RAIL_X    = 0.95 * cm          # linker Satzspiegel innerhalb der Flaeche
RAIL_W    = 4.45 * cm          # Textbreite in der Spalte
FOTO_H    = 6.60 * cm          # Hoehe des randabfallenden Fotos
FOTO_GAP  = 0.70 * cm          # Abstand Foto -> erster Block
MAIN_X    = RAIL_BG_W + 0.75 * cm
MAIN_W    = A4[0] - MAIN_X - R_MARGIN

# ─── COLOURS ─────────────────────────────────────────────────────────────────
# Ein Navy traegt das Dokument: als Flaeche links, als Schriftfarbe rechts.
NAVY      = HexColor('#15314F')   # Flaeche der Seitenspalte, Abschnitte
ACCENT    = HexColor('#2C5AA0')   # Links in der Hauptspalte
DARK      = HexColor('#1E1E1E')   # Fliesstext
GRAY      = HexColor('#55595F')   # Zweitzeilen
LGRAY     = HexColor('#8A8F97')   # Zeitraeume, Fusszeile
BULLET_C  = HexColor('#8694AB')   # Aufzaehlungspunkte
RULE_HD   = HexColor('#A9B6C8')   # Linie unter Abschnittstiteln (hell)
RULE_C    = HexColor('#DFE3E9')   # Haarlinien

# Auf der dunklen Flaeche gelten eigene Werte: reines Weiss nur fuer das,
# was wirklich zuerst gelesen werden soll.
RAIL_HEAD = HexColor('#FFFFFF')
RAIL_LBL  = HexColor('#FFFFFF')
RAIL_TXT  = HexColor('#C9D4E3')
RAIL_LINK = HexColor('#9FC3EC')
RAIL_RULE = HexColor('#3E5F86')

# ─── FONTS ───────────────────────────────────────────────────────────────────
WIN_FONTS = r"C:\Windows\Fonts"
_FONT_MAP = {
    'CV-R':  os.path.join(WIN_FONTS, 'segoeui.ttf'),
    'CV-B':  os.path.join(WIN_FONTS, 'segoeuib.ttf'),
    'CV-I':  os.path.join(WIN_FONTS, 'segoeuii.ttf'),
    'CV-BI': os.path.join(WIN_FONTS, 'segoeuiz.ttf'),
}

# Fehlt Segoe UI, greift Calibri; fehlt auch das, Arial.
_FALLBACK_CHAIN = (
    {'CV-R': 'calibri.ttf', 'CV-B': 'calibrib.ttf',
     'CV-I': 'calibrii.ttf', 'CV-BI': 'calibriz.ttf'},
    {'CV-R': 'arial.ttf', 'CV-B': 'arialbd.ttf',
     'CV-I': 'ariali.ttf', 'CV-BI': 'arialbi.ttf'},
)

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
        for stufe in _FALLBACK_CHAIN:
            fb = os.path.join(WIN_FONTS, stufe[name])
            if os.path.exists(fb):
                pdfmetrics.registerFont(TTFont(name, fb))
                break
        else:
            # Gar keine TTF gefunden -> Alias auf eine Standard-Schrift,
            # damit kein "Can't find font"-Fehler beim ersten Paragraph kommt.
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
        'name':        ps('name',        'CV-B', 22, NAVY, leading=23.5),
        'section':     ps('section',     'CV-B', 9.6, NAVY, leading=11.4),
        'section_rail': ps('section_rail', 'CV-B', 8.5, RAIL_HEAD, leading=10.4),
        # Hauptspalte
        'profile':     ps('profile',     'CV-R', 8.5, DARK, leading=11.4,
                          align=TA_LEFT),
        'entry_title': ps('entry_title', 'CV-B', 9.2, DARK, leading=11.2),
        'entry_meta':  ps('entry_meta',  'CV-R', 7.8, LGRAY, leading=10.0,
                          spaceAfter=2.5),
        'bullet':      ps('bullet',      'CV-R', 8.5, DARK, leading=11.2,
                          spaceAfter=0.4, leftIndent=9, align=TA_LEFT,
                          bulletIndent=0, bulletFontName='CV-R',
                          bulletFontSize=7.4, bulletColor=BULLET_C),
        'edu_title':   ps('edu_title',   'CV-B', 9.2, DARK, leading=11.2),
        'edu_bullet':  ps('edu_bullet',  'CV-R', 8.5, DARK, leading=11.2,
                          spaceAfter=0.4, leftIndent=9, align=TA_LEFT,
                          bulletIndent=0, bulletFontName='CV-R',
                          bulletFontSize=7.4, bulletColor=BULLET_C),
        'footer':      ps('footer',      'CV-R', 7.8, LGRAY, leading=10.2),
        # Seitenspalte: heller Text auf dunkler Flaeche
        'rail_txt':    ps('rail_txt',    'CV-R', 7.8, RAIL_TXT, leading=10.4),
        'rail_lbl':    ps('rail_lbl',    'CV-B', 8.0, RAIL_LBL, leading=10.4),
        'rail_val':    ps('rail_val',    'CV-R', 7.8, RAIL_TXT, leading=9.6),
    }

# ─── CUSTOM FLOWABLES ───────────────────────────────────────────────────────
class TrackedLine(Flowable):
    """Eine gesperrt gesetzte Zeile – optional mit Linie darunter.

    ReportLab kann Sperrung (letter-spacing) nicht im Paragraph, deshalb wird
    die Zeile direkt auf das Canvas gezeichnet. Gesperrte Versalien sind das,
    was Abschnittstitel ruhig und gesetzt aussehen laesst – im Gegensatz zu
    farbigen Balken.
    """

    def __init__(self, text, font, size, color, track=1.1,
                 rule=None, rule_width=0.7, gap=4.0, space_after=0.0):
        super().__init__()
        self.text = text
        self.font = font
        self.size = size
        self.color = color
        self.track = track
        self.rule = rule
        self.rule_width = rule_width
        self.gap = gap
        self.space_after = space_after

    def wrap(self, aw, ah):
        self.width = aw
        unten = (self.gap + self.rule_width) if self.rule else 0
        self.height = self.size + unten + self.space_after
        return self.width, self.height

    def draw(self):
        c = self.canv
        c.saveState()
        basis = self.space_after + (self.gap + self.rule_width
                                    if self.rule else 0)
        # Sperrung kann nur das Textobjekt, nicht das Canvas selbst.
        t = c.beginText(0, basis)
        t.setFont(self.font, self.size)
        t.setFillColor(self.color)
        t.setCharSpace(self.track)
        t.textOut(self.text)
        c.drawText(t)
        if self.rule:
            c.setStrokeColor(self.rule)
            c.setLineWidth(self.rule_width)
            y = self.space_after + self.rule_width / 2
            c.line(0, y, self.width, y)
        c.restoreState()


# Ab etwa 0,14 Punkt Sperrung je Punkt Schriftgrad schieben PDF-Leser
# Leerzeichen zwischen die Buchstaben: aus "IT-KENNTNISSE" wird dann
# "I T - K E N N T N I S S E". Bewerbungsportale lesen den Lebenslauf so
# aus, deshalb bleibt die Sperrung mit 0,10 klar darunter.
TRACK_RATIO = 0.10


class SectionHeading(TrackedLine):
    """Abschnittstitel: gesperrte Versalien ueber einer Haarlinie."""

    def __init__(self, text, style, rule=None):
        super().__init__(text, style.fontName, style.fontSize,
                         style.textColor,
                         track=round(style.fontSize * TRACK_RATIO, 2),
                         rule=rule or RULE_HD, rule_width=0.7, gap=4.2)


class HRule(Flowable):
    """Einzelne waagerechte Linie als Flowable."""

    def __init__(self, color=RULE_C, width=0.7, space_before=0, space_after=0):
        super().__init__()
        self.color = color
        self.lw = width
        self.sb = space_before
        self.sa = space_after

    def wrap(self, aw, ah):
        self.width = aw
        self.height = self.lw + self.sb + self.sa
        return self.width, self.height

    def draw(self):
        c = self.canv
        c.saveState()
        c.setStrokeColor(self.color)
        c.setLineWidth(self.lw)
        y = self.sa + self.lw / 2
        c.line(0, y, self.width, y)
        c.restoreState()


def foto_zeichnen(c, pfad, x, y, w, h, focus=0.60):
    """Foto formatfuellend in ein Rechteck zeichnen (Ueberstand beschnitten).

    'focus' verschiebt den Ausschnitt nach oben, damit das Gesicht sitzt.
    """
    if not os.path.isfile(pfad):
        return
    c.saveState()
    p = c.beginPath()
    p.rect(x, y, w, h)
    c.clipPath(p, stroke=0)
    try:
        from reportlab.lib.utils import ImageReader
        nat_w, nat_h = ImageReader(pfad).getSize()
    except Exception:
        nat_w, nat_h = w, h
    if nat_w <= 0 or nat_h <= 0:
        nat_w, nat_h = w, h
    skal = max(w / nat_w, h / nat_h)
    bw, bh = nat_w * skal, nat_h * skal
    c.drawImage(pfad, x + (w - bw) / 2, y - (bh - h) * (1.0 - focus),
                bw, bh, preserveAspectRatio=True, mask='auto')
    c.restoreState()


# ─── HELPERS ─────────────────────────────────────────────────────────────────
def b(t):   return f'<b>{t}</b>'
def it(t):  return f'<i>{t}</i>'
def lnk(url, label, farbe='#2C5AA0'):
    return f'<a href="{url}" color="{farbe}">{label}</a>'


# Trenner zwischen den Angaben einer Kontaktzeile. Die bunten PNG-Icons
# (roter Pin, blaues LinkedIn-Badge) sind entfallen: fuenf Fremdfarben neben
# einer Navy-Palette waren der groesste Bruch im Gesamtbild.
SEP = '&#160;&#160;<font color="#B4BAC3">|</font>&#160;&#160;'

def bul(text, sty):
    """Aufzählung mit echtem Hängeeinzug: Folgezeilen stehen unter dem
    Text, nicht unter dem Punkt."""
    return Paragraph(text, sty, bulletText=chr(0x2022))


def sec(title, sty, key='section', rule=None, gap=None, nach=3.5):
    """Abschnittstitel mit Luft davor und darunter."""
    return [Spacer(1, SEC_GAP if gap is None else gap),
            SectionHeading(title, sty[key], rule=rule), Spacer(1, nach)]


def rail_block(titel, sty, zeilen, gap=0.45 * cm):
    """Ein Block der Seitenspalte: Titel, darunter einzeilige Angaben."""
    out = sec(titel, sty, 'section_rail', rule=RAIL_RULE,
              gap=0.24 * cm, nach=2.5)
    out += [Paragraph(z, sty['rail_txt']) for z in zeilen]
    out.append(Spacer(1, gap))
    return out


def rail_paare(titel, sty, paare, gap=0.45 * cm):
    """Ein Block der Seitenspalte aus Label/Wert-Paaren (Kenntnisse, Sprachen).

    Label ueber dem Wert statt daneben: in 5,4 cm Breite waere eine
    zweispaltige Tabelle nicht lesbar.
    """
    out = sec(titel, sty, 'section_rail', rule=RAIL_RULE,
              gap=0.24 * cm, nach=2.5)
    for i, (label, wert) in enumerate(paare):
        if i:
            out.append(Spacer(1, 2))
        out.append(Paragraph(b(label), sty['rail_lbl']))
        out.append(Paragraph(wert, sty['rail_val']))
    out.append(Spacer(1, gap))
    return out


# ─── PAGE DECORATION ────────────────────────────────────────────────────────
def _draw_page(canvas, doc):
    """Dunkle Spalte ueber die volle Seitenhoehe, Foto randabfallend oben.

    Das Foto ist eine dunkle Studioaufnahme; auf weissem Grund war es ein
    schwarzer Block. In der Farbflaeche gehen Anzug und Hintergrund in die
    Flaeche ueber, sichtbar bleibt das Gesicht.
    """
    w, h = A4
    canvas.saveState()
    canvas.setFillColor(NAVY)
    canvas.rect(0, 0, RAIL_BG_W, h, fill=True, stroke=False)
    canvas.restoreState()
    foto_zeichnen(canvas, FOTO_PATH, 0, h - FOTO_H, RAIL_BG_W, FOTO_H,
                  focus=0.60)



# ─── DEFAULT CONFIG ──────────────────────────────────────────────────────────
# Das Kurzprofil soll nicht wiederholen, was zwei Zentimeter tiefer in der
# Berufserfahrung steht. Es nennt deshalb den Verantwortungsbogen und eine
# Zahl als Beleg - die Technik steht ohnehin in den IT-Kenntnissen.
DEFAULT_KURZPROFIL = (
    'Ich digitalisiere <b>kaufmännische Geschäftsprozesse</b> – vom Papierbeleg '
    'über Datenmodell und API bis zu dem Server, auf dem das Ganze läuft. '
    'Bei Bike Haus Freiburg verantworte ich die Warenwirtschafts- und '
    'Vermietungsplattform von der Konzeption bis zum Betrieb; sie bildet den '
    'gesamten Belegfluss ab, <b>über 2.000 Belege in 2026</b>. Als '
    '<b>Fachinformatiker für Anwendungsentwicklung (IHK)</b> arbeite ich mit '
    '.NET, Angular und Docker, daneben mit TypeScript und React.'
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
    'Arbeitsplatz über Server und Mail bis zur Dokumentation. Bei Bike Haus '
    'Freiburg verantworte ich die <b>komplette Inhouse-IT</b> – vom '
    'Linux-Server bis zum Arbeitsplatz – und habe das Tagesgeschäft auf '
    'digitale Belege umgestellt: <b>über 2.000 in 2026</b>. Weil ich die '
    'eingesetzte Software als <b>Fachinformatiker für Anwendungsentwicklung '
    '(IHK)</b> selbst gebaut habe, verfolge ich eine Störung bis zur Ursache '
    '– Konfiguration, Daten oder Anwendung.'
)


_LNK_BIKEHAUS = (
    lnk('https://bikehausfreiburg.com', 'bikehausfreiburg.com')
    + '&#160;&#160;<font color="#B4BAC3">|</font>&#160;&#160;'
    + lnk('https://github.com/oeztuerkhamza/bikehausfreiburg', 'GitHub')
)


def _projekt_kopf(name, zusatz, status, url, label, repo):
    """(Titelzeile, Metazeile) eines Projekts.

    In der schmalen Hauptspalte passt nicht alles in eine Zeile: Name und
    Kurzbeschreibung stehen oben, Status und Links in einer ruhigen
    zweiten Zeile darunter.
    """
    return (b(name) + zusatz,
            status + SEP + lnk(url, label) + SEP + lnk(repo, 'GitHub'))


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
        'inst':   'Walther-Rathenau-Gewerbeschule · '
                  'Ausbildungsbetrieb: Dicom GmbH',
        'detail': b('Abschlussprojekt DI-Flux:')
                  + ' Enterprise-Web-Zeiterfassung mit Angular, JWT-Auth, '
                    'C#/.NET und SQL Server.',
    },
    {
        'period': '05/2022 – 03/2023',
        'title':  'Zertifikat: Data Analytics &amp; Visualization (260 Std.)',
        'inst':   'Clarusway IT School',
    },
]

# ── Englische Fassung: Kurzprofile ──────────────────────────────────────────
PROFILE_FULLSTACK_EN = (
    'I digitalise <b>commercial business processes</b> – from the paper '
    'document through data model and API to the server it all runs on. At '
    'Bike Haus Freiburg I am responsible for the inventory and rental '
    'platform from concept to operation; it carries the entire document '
    'flow, <b>more than 2,000 documents in 2026</b>. As a qualified '
    '<b>IT Specialist in Application Development (IHK)</b> I work with .NET, '
    'Angular and Docker, alongside TypeScript and React.'
)


PROFILE_IT_SUPPORT_EN = (
    "I keep a company's IT running – from the question at the user's desk "
    'through servers and mail to proper documentation. At Bike Haus Freiburg '
    'I am responsible for the <b>entire in-house IT</b> – from the Linux '
    'server to the desk – and moved daily business onto digital documents: '
    '<b>more than 2,000 in 2026</b>. Because I built the software in use '
    'myself as an <b>IT Specialist in Application Development (IHK)</b>, I '
    'trace a fault to where it originates – configuration, data or '
    'application.'
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
        'inst':   'Walther-Rathenau-Gewerbeschule · '
                  'Training company: Dicom GmbH',
        'detail': b('Final project DI-Flux:')
                  + ' enterprise web time tracking with Angular, JWT auth, '
                    'C#/.NET and SQL Server.',
    },
    {
        'period': '05/2022 – 03/2023',
        'title':  'Certificate: Data Analytics &amp; Visualization (260 hours)',
        'inst':   'Clarusway IT School',
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
        'h_kontakt':    'KONTAKT',
        'h_person':     'PERSÖNLICH',
        'person': [
            'Geb. 18.02.1996, Groß-Gerau',
            'Führerschein Klasse B',
            'Aufenthalts- &amp; Arbeitserlaubnis',
        ],
        'bildungsweg':  BILDUNGSWEG,
        # Stufe plus kurze Einordnung. Der Klammerzusatz dahinter stand
        # ohnehin doppelt: die IHK-Ausbildung auf Deutsch steht in der
        # Ausbildung.
        'sprachen': [
            ('Türkisch',  'Muttersprache'),
            ('Deutsch',   'C1 – verhandlungssicher'),
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
        'h_kontakt':    'CONTACT',
        'h_person':     'PERSONAL',
        'person': [
            'Born 18 Feb 1996, Groß-Gerau',
            'Driving licence category B',
            'German residence &amp; work permit',
        ],
        'bildungsweg':  BILDUNGSWEG_EN,
        'sprachen': [
            ('Turkish',  'native speaker'),
            ('German',   'C1 – full professional proficiency'),
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
def baue_spalten(sty, cfg=None):
    """Liefert (Seitenspalte, Hauptspalte) als zwei Flowable-Listen."""
    cfg = {**DEFAULT_CONFIG, **(cfg or {})}
    variante = variante_aus_cfg(cfg)
    sprache = sprache_aus_cfg(cfg)
    inhalt = INHALT[sprache][variante]
    texte = TEXTE[sprache]

    # Steht im Feld noch die Fullstack-Vorgabe, obwohl die Anzeige eine
    # Support-Stelle ist, greift die Bezeichnung der Support-Variante.
    stelle_titel = (cfg.get('stelle') or '').strip()
    if not stelle_titel or ((variante != VARIANTE_FULLSTACK
                             or sprache != SPRACHE_DE)
                            and stelle_titel == DEFAULT_CONFIG['stelle']):
        stelle_titel = inhalt['stelle']

    # Gleiche Logik beim Kurzprofil: unveraenderter Standardtext wird durch
    # den der jeweiligen Variante ersetzt.
    kurzprofil = (cfg.get('kurzprofil') or '').strip()
    if not kurzprofil or kurzprofil == DEFAULT_KURZPROFIL.strip():
        kurzprofil = inhalt['kurzprofil']
    elif sprache == SPRACHE_EN and erkenne_sprache(kurzprofil) == SPRACHE_DE:
        # Deutscher KI-Text im englischen Lebenslauf waere ein Sprachmix.
        kurzprofil = inhalt['kurzprofil']

    # ══ SEITENSPALTE ════════════════════════════════════════════════════
    # Das Foto zeichnet _draw_page randabfallend; der Fluss beginnt darunter.
    hell = '#9FC3EC'
    rail = rail_block(texte['h_kontakt'], sty, [
        'Bissierstr. 16, 79114 Freiburg',
        lnk('https://wa.me/4915566859378', '+49 155 66859378', hell),
        lnk('mailto:oeztuerk.hamza@web.de', 'oeztuerk.hamza@web.de', hell),
        lnk('https://linkedin.com/in/hamzaoeztuerk',
            'linkedin.com/in/hamzaoeztuerk', hell),
        lnk('https://github.com/oeztuerkhamza', 'github.com/oeztuerkhamza',
            hell),
    ])
    rail += rail_block(texte['h_person'], sty, texte['person'])
    rail += rail_paare(texte['h_skills'], sty, inhalt['skills'])
    rail += rail_paare(texte['h_sprachen'], sty, texte['sprachen'], gap=0)

    # ══ HAUPTSPALTE ═════════════════════════════════════════════════════
    main = [
        Paragraph('Hamza Öztürk', sty['name']),
        Spacer(1, 1.5),
        # Gesperrte Versalien geben der Berufsbezeichnung Gewicht, ohne sie
        # fett oder farbig setzen zu muessen.
        TrackedLine(esc(stelle_titel).upper(), 'CV-R', 9.8, GRAY,
                    track=round(9.8 * TRACK_RATIO, 2)),
        Spacer(1, 5),
        HRule(NAVY, 0.9, space_after=0.26 * cm),
        SectionHeading(texte['h_profil'], sty['section']),
        Spacer(1, 2.5),
        Paragraph(esc_rich(kurzprofil), sty['profile']),
    ]

    def eintrag(titel, meta, bullets, titel_stil='entry_title',
                bullet_stil='bullet'):
        """Titelzeile, graue Metazeile (Zeitraum, Links), dann die Punkte."""
        teile = [Paragraph(titel, sty[titel_stil])]
        if meta:
            teile.append(Paragraph(meta, sty['entry_meta']))
        teile += [bul(t, sty[bullet_stil]) for t in bullets]
        return KeepTogether(teile)

    # ── Berufserfahrung ──────────────────────────────────────────────────
    main += sec(texte['h_erfahrung'], sty)
    for idx, job in enumerate(inhalt['erfahrung']):
        meta = job['period']
        if job.get('sub'):
            meta += SEP + job['sub']
        main.append(eintrag(b(job['title']), meta, job['bullets']))
        if idx < len(inhalt['erfahrung']) - 1:
            main.append(Spacer(1, 7))

    # ── Projekte ─────────────────────────────────────────────────────────
    main += sec(texte['h_projekte'], sty)
    for idx, projekt in enumerate(inhalt['projekte']):
        titel, meta = projekt['head']
        main.append(eintrag(titel, meta, projekt['bullets']))
        if idx < len(inhalt['projekte']) - 1:
            main.append(Spacer(1, 6))

    # ── Ausbildung ───────────────────────────────────────────────────────
    main += sec(texte['h_ausbildung'], sty)
    bildungsweg = texte['bildungsweg']
    for idx, e in enumerate(bildungsweg):
        meta = e['period']
        if e.get('inst'):
            meta += SEP + e['inst']
        detail = [e['detail']] if e.get('detail') else []
        main.append(eintrag(b(e['title']), meta, detail,
                            titel_stil='edu_title', bullet_stil='edu_bullet'))
        if idx < len(bildungsweg) - 1:
            main.append(Spacer(1, 5))

    # ── Ort, Datum, Unterschrift ─────────────────────────────────────────
    main.append(Spacer(1, 0.34 * cm))
    datum_txt = (cfg['datum'] if sprache == SPRACHE_DE
                 else _datum_englisch(cfg['datum']))
    main.append(Paragraph(f'Freiburg, {esc(datum_txt)}', sty['footer']))
    if os.path.isfile(SIGNATUR_PATH):
        main.append(Image(SIGNATUR_PATH, width=2.3 * cm, height=0.78 * cm,
                          hAlign='LEFT'))

    return rail, main


# ─── SEITENANPASSUNG ─────────────────────────────────────────────────────────
# Der Inhalt passt knapp auf eine Seite. Wird aus der GUI ein längeres
# Kurzprofil übergeben, wird der Zeilenabstand stufenweise nachgezogen,
# statt eine zweite Seite mit nur der Unterschrift anzufangen.
_FIT_STUFEN = (0.0, 0.2, 0.4, 0.6, 0.8, 1.0)


def _baue_pdf(out, cfg, tighten, subject):
    """Baut das PDF einmal und gibt die Seitenzahl zurück.

    Zwei Frames nebeneinander. Die Seitenspalte wird zuerst gefuellt, dann
    schickt ein FrameBreak den Rest in die Hauptspalte. Dadurch steht der
    Text auch im PDF in dieser Reihenfolge - wichtig, damit Bewerbungs-
    portale beim Auslesen nicht zwischen den Spalten hin und her springen.
    """
    H = A4[1]
    rand = dict(leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    # Die Spalte beginnt unter dem randabfallenden Foto, die Hauptspalte
    # nutzt die volle Seitenhoehe - deshalb kostet die Spalte sie nichts.
    rail_h = H - FOTO_H - FOTO_GAP - B_MARGIN
    f_rail = Frame(RAIL_X, B_MARGIN, RAIL_W, rail_h, id='rail', **rand)
    f_main = Frame(MAIN_X, B_MARGIN, MAIN_W, H - T_MARGIN - B_MARGIN,
                   id='main', **rand)

    doc = BaseDocTemplate(
        out, pagesize=A4,
        leftMargin=L_MARGIN, rightMargin=R_MARGIN,
        topMargin=T_MARGIN, bottomMargin=B_MARGIN,
        title=TEXTE[sprache_aus_cfg(cfg)]['pdf_titel'], author='Hamza Öztürk',
        subject=subject, creator='Python / ReportLab',
    )
    doc.addPageTemplates([
        PageTemplate(id='cv', frames=[f_rail, f_main], onPage=_draw_page),
    ])

    rail, main = baue_spalten(make_styles(tighten), cfg)
    doc.build(rail + [FrameBreak()] + main)
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
