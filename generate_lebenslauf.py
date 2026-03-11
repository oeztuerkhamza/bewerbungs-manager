#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lebenslauf – Hamza Öztürk · Fullstack Entwickler
Premium-Design · 09.03.2026
"""

import os
import sys

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, HRFlowable,
    Table, TableStyle, KeepTogether, Image, Flowable,
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.colors import HexColor, white, Color
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ─── PATHS ────────────────────────────────────────────────────────────────────
OUTPUT        = r"C:\Users\hamza\Desktop\Lebenslauf\Hamza_Oeztuerk_Lebenslauf_Fullstack_Entwickler.pdf"
FOTO_PATH     = r"C:\Users\hamza\Desktop\Lebenslauf\foto.jpeg"
SIGNATUR_PATH = r"C:\Users\hamza\Desktop\Lebenslauf\sıgnatur.png"

# ─── LAYOUT ──────────────────────────────────────────────────────────────────
L_MARGIN  = 2.5 * cm
R_MARGIN  = 2.0 * cm
T_MARGIN  = 1.6 * cm
B_MARGIN  = 1.6 * cm
SIDEBAR_W = 4 * mm           # left decorative stripe width
SEC_GAP   = 0.35 * cm        # consistent gap before each section

# ─── COLOURS ─────────────────────────────────────────────────────────────────
NAVY      = HexColor('#1B3764')
NAVY_L    = HexColor('#2A4F8A')   # lighter navy for accents
DARK      = HexColor('#1F1F1F')
GRAY      = HexColor('#4A4A4A')
LGRAY     = HexColor('#777777')
RULE_C    = HexColor('#D0D4DD')
BG_LIGHT  = HexColor('#F5F6F8')   # subtle background for skill area
PHOTO_BRD = HexColor('#1B3764')   # photo border colour

# ─── FONTS ───────────────────────────────────────────────────────────────────
WIN_FONTS = r"C:\Windows\Fonts"
_FONT_MAP = {
    'CV-R':  os.path.join(WIN_FONTS, 'calibri.ttf'),
    'CV-B':  os.path.join(WIN_FONTS, 'calibrib.ttf'),
    'CV-I':  os.path.join(WIN_FONTS, 'calibrii.ttf'),
    'CV-BI': os.path.join(WIN_FONTS, 'calibriz.ttf'),
}

def register_fonts():
    for name, path in _FONT_MAP.items():
        if os.path.exists(path):
            pdfmetrics.registerFont(TTFont(name, path))
        else:
            # fallback to Arial
            fb = path.replace('calibri', 'arial').replace('calibrib', 'arialbd').replace('calibrii', 'ariali').replace('calibriz', 'arialbi')
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
        'name':        ps('name',        'CV-B', 26, NAVY, leading=30),
        'role':        ps('role',        'CV-R', 12, GRAY, leading=16, spaceAfter=2),
        'contact':     ps('contact',     'CV-R',  9, DARK, leading=14),
        'contact_i':   ps('contact_i',   'CV-R',  9, LGRAY, leading=14),
        'section':     ps('section',     'CV-B', 11.5, NAVY, leading=15),
        'entry_title': ps('entry_title', 'CV-B', 10, DARK, leading=13.5, spaceAfter=0.5),
        'entry_sub':   ps('entry_sub',   'CV-I',  9, GRAY, leading=12.5, spaceAfter=1),
        'period':      ps('period',      'CV-R',  9, LGRAY, leading=12, align=TA_RIGHT),
        'body':        ps('body',        'CV-R',  9.5, DARK, leading=13.5),
        'bullet':      ps('bullet',      'CV-R',  9.5, DARK, leading=13.5,
                          spaceAfter=2, leftIndent=10),
        'profile':     ps('profile',     'CV-R', 10, DARK, leading=15, spaceAfter=2),
        'footer':      ps('footer',      'CV-R',  9, LGRAY, leading=12, spaceBefore=2),
        'skill_lbl':   ps('skill_lbl',   'CV-B',  9.5, NAVY, leading=14),
        'skill_val':   ps('skill_val',   'CV-R',  9.5, DARK, leading=14),
    }


# ─── CUSTOM FLOWABLES ───────────────────────────────────────────────────────
class SectionHeading(Flowable):
    """Section heading with a left navy accent bar."""
    def __init__(self, text, style, bar_w=3, bar_gap=8):
        super().__init__()
        self.text = text
        self.style = style
        self.bar_w = bar_w
        self.bar_gap = bar_gap
        self._para = Paragraph(text, style)

    def wrap(self, aw, ah):
        pw, ph = self._para.wrap(aw - self.bar_w - self.bar_gap, ah)
        self.height = ph + 2
        self.width = aw
        return self.width, self.height

    def draw(self):
        self.canv.saveState()
        self.canv.setFillColor(NAVY)
        self.canv.rect(0, 0, self.bar_w, self.height, fill=True, stroke=False)
        self.canv.restoreState()
        self._para.drawOn(self.canv, self.bar_w + self.bar_gap, 1)


class PhotoFrame(Flowable):
    """Photo with a thin navy border."""
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
        # clip image to frame so it fills completely
        c.saveState()
        c.clipPath(c.beginPath().rect(b, b, self.img_w, self.img_h),
                   stroke=0, fill=0) if False else None
        c.drawImage(self.img_path, b, b, self.img_w, self.img_h,
                    preserveAspectRatio=False)
        c.restoreState()
        # navy border on top
        c.saveState()
        c.setStrokeColor(PHOTO_BRD)
        c.setLineWidth(b)
        c.rect(b/2, b/2, self.img_w + b, self.img_h + b,
               fill=False, stroke=True)
        c.restoreState()


# ─── HELPERS ─────────────────────────────────────────────────────────────────
def thin_rule():
    return HRFlowable(width='100%', thickness=0.35, color=RULE_C,
                      spaceBefore=4, spaceAfter=4)

def b(t):   return f'<b>{t}</b>'
def it(t):  return f'<i>{t}</i>'
def lnk(url, label):
    return f'<a href="{url}" color="#1B3764">{label}</a>'

def _build_role_line(stelle, detail):
    """Build the role subtitle, e.g. 'Fullstack Entwickler | C# | .NET'."""
    parts = [p.strip() for p in detail.split('|')]
    sep = '&#160;&#160;<font color="#1B3764">|</font>&#160;&#160;'
    role_parts = [stelle] + parts
    return sep.join(role_parts)

def bul(text, sty):
    """Bullet with a small navy square marker."""
    return Paragraph(
        f'<font color="#1B3764">&#x25AA;</font>&#160;&#160;{text}', sty)

# Two-column entry table style
_ENTRY_TS = TableStyle([
    ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
    ('LEFTPADDING',   (0, 0), (-1, -1), 0),
    ('RIGHTPADDING',  (0, 0), (0, -1),  6),
    ('RIGHTPADDING',  (1, 0), (1, -1),  0),
    ('TOPPADDING',    (0, 0), (-1, -1), 0),
    ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
])

def entry_row(left, date_str, sty, cw, dw):
    t = Table([[left, Paragraph(date_str, sty['period'])]], colWidths=[cw, dw])
    t.setStyle(_ENTRY_TS)
    return t

def sec(title, sty):
    """Section heading with accent bar + spacing."""
    return [Spacer(1, SEC_GAP), SectionHeading(title, sty['section']),
            Spacer(1, 3)]


# ─── PAGE DECORATION ────────────────────────────────────────────────────────
def _draw_page(canvas, doc):
    """Navy sidebar stripe + subtle header background."""
    w, h = A4
    canvas.saveState()
    # Left sidebar stripe
    canvas.setFillColor(NAVY)
    canvas.rect(0, 0, SIDEBAR_W, h, fill=True, stroke=False)
    # Thin line at page bottom
    canvas.setStrokeColor(RULE_C)
    canvas.setLineWidth(0.5)
    canvas.line(L_MARGIN, B_MARGIN - 6*mm, w - R_MARGIN, B_MARGIN - 6*mm)
    canvas.restoreState()


# ─── DEFAULT CONFIG ──────────────────────────────────────────────────────────
DEFAULT_CONFIG = {
    'stelle':        'Fullstack Entwickler',
    'stelle_detail': 'C#  |  .NET  |  Angular',
    'datum':         '09.03.2026',
}


# ─── BUILD STORY ─────────────────────────────────────────────────────────────
def build(story, sty, W, cfg=None):
    cfg = {**DEFAULT_CONFIG, **(cfg or {})}
    CW = W * 0.78
    DW = W * 0.22

    # ── 1  HEADER ────────────────────────────────────────────────────────────
    PHOTO_W = 3.0 * cm
    PHOTO_H = 4.0 * cm
    HDR_W   = W - PHOTO_W - 1.0 * cm

    # Contact info with bold navy label prefixes – each on its own line
    c_ort = (
        '<font color="#1B3764"><b>Ort:</b></font>&#160;'
        'Bissierstr. 16, 79114 Freiburg im Breisgau'
    )
    c_tel = (
        '<font color="#1B3764"><b>Tel.:</b></font>&#160;'
        '+49 155 66859378'
    )
    c_email = (
        '<font color="#1B3764"><b>E-Mail:</b></font>&#160;'
        'oeztuerk.hamza@web.de'
    )
    c_linkedin = (
        '<font color="#1B3764"><b>LinkedIn:</b></font>&#160;'
        + lnk('https://linkedin.com/in/hamzaoeztuerk',
              'linkedin.com/in/hamzaoeztuerk')
    )
    c_github = (
        '<font color="#1B3764"><b>GitHub:</b></font>&#160;'
        + lnk('https://github.com/oeztuerkhamza',
              'github.com/oeztuerkhamza')
    )
    c_geb = (
        '<font color="#1B3764"><b>Geb.:</b></font>&#160;'
        '18.02.1996, Groß-Gerau'
    )

    left_hdr = [
        Paragraph('Hamza Öztürk', sty['name']),
        Spacer(1, 2),
        Paragraph(
            _build_role_line(cfg['stelle'], cfg['stelle_detail']),
            sty['role'],
        ),
        Spacer(1, 6),
        Paragraph(c_ort, sty['contact']),
        Paragraph(c_tel, sty['contact']),
        Paragraph(c_email, sty['contact']),
        Paragraph(c_linkedin, sty['contact']),
        Paragraph(c_github, sty['contact']),
        Paragraph(c_geb, sty['contact']),
    ]

    photo = PhotoFrame(FOTO_PATH, PHOTO_W, PHOTO_H, border=1.5)
    hdr = Table(
        [[left_hdr, photo]],
        colWidths=[HDR_W, PHOTO_W + 1.0 * cm],
    )
    hdr.setStyle(TableStyle([
        ('VALIGN',       (0, 0), (-1, -1), 'TOP'),
        ('ALIGN',        (1, 0), (1, 0),   'RIGHT'),
        ('LEFTPADDING',  (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING',   (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 0),
    ]))
    story.append(hdr)
    story.append(Spacer(1, 0.15 * cm))
    story.append(HRFlowable(width='100%', thickness=1, color=NAVY,
                            spaceBefore=2, spaceAfter=2))

    # ── 2  KURZPROFIL ────────────────────────────────────────────────────────
    story.extend(sec('KURZPROFIL', sty))
    story.append(Paragraph(
        'Nach einem beruflichen Neustart in Deutschland mit gezielter '
        'Weiterbildung (Bootcamp, Sprachkurs, verkürzte Ausbildung) '
        'habe ich mich als <b>Full-Stack-Entwickler</b> mit '
        '<b>C#/.NET</b> und <b>Angular</b> etabliert. '
        'Bei Dicom GmbH habe ich SonarQube-Violations innerhalb von '
        '<b>3 Wochen von 2.100 auf 30</b> gesenkt, CI/CD-Pipelines aufgebaut und '
        'eine Legacy-ERP-Anwendung auf <b>Clean Architecture</b> migriert. '
        'Nebenbei betreibe ich eigene Open-Source-Projekte – '
        'von Warenwirtschaftssystemen bis zu '
        'KI-gestützten Webanwendungen.',
        sty['profile'],
    ))

    # ── 3  BERUFSERFAHRUNG ───────────────────────────────────────────────────
    story.extend(sec('BERUFSERFAHRUNG', sty))
    exp = [
        Paragraph(
            b('Fachinformatiker für Anwendungsentwicklung')
            + '&#160;(Softwareentwickler-Niveau)',
            sty['entry_title'],
        ),
        Paragraph(it('Dicom GmbH, Freiburg im Breisgau'), sty['entry_sub']),
        bul(
            b('Full-Stack &amp; Architektur:')
            + ' Feature-Entwicklung in <b>C#/.NET</b> (Backend) und '
            '<b>Angular</b> (Frontend); Migration monolithischer '
            'Desktop-Apps auf Clean Architecture.',
            sty['bullet'],
        ),
        bul(
            b('CI/CD &amp; Code-Qualität:')
            + ' GitHub Actions-Pipelines aufgebaut – Deployment-Zeit '
            '<b>40 % schneller</b>; SonarQube-Violations innerhalb von '
            '<b>3 Wochen von 2.100 auf 30</b> reduziert.',
            sty['bullet'],
        ),
        bul(
            b('KI &amp; API:')
            + ' RESTful APIs designed; KI-Tools und '
            '<b>Prompt Engineering</b> zur Code-Generierung und '
            'Fehleranalyse eingesetzt.',
            sty['bullet'],
        ),
       ]
    story.append(entry_row(exp, '02/2024 – 02/2026', sty, CW, DW))

    # ── 4  IT-KENNTNISSE ─────────────────────────────────────────────────────
    story.extend(sec('IT-KENNTNISSE', sty))
    skills = [
        ('Backend',
         'C#, .NET Core, ASP.NET Core, Clean Architecture, EF Core, '
         'RESTful APIs, SQLite, SQL Server'),
        ('Frontend',
         'Angular (17/19), TypeScript, React 19, Tailwind CSS, NgRx, '
         'Infragistics'),
        ('DevOps &amp; Tools',
         'Docker, GitHub Actions, Azure Pipelines, SonarQube / Cloud, '
         'Git, CI/CD, Netcup VPS'),
        ('KI &amp; Analytics',
         'OpenAI API, Prompt Engineering, Python, SQL, Tableau, '
         'Web-Scraping'),
    ]
    rows = [[Paragraph(b(l), sty['skill_lbl']),
             Paragraph(v, sty['skill_val'])] for l, v in skills]
    sk = Table(rows, colWidths=[W * 0.22, W * 0.78])
    sk.setStyle(TableStyle([
        ('VALIGN',       (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING',  (0, 0), (0, -1),  0),
        ('LEFTPADDING',  (1, 0), (1, -1),  6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING',   (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 3),
        ('LINEBELOW',    (0, 0), (-1, -2), 0.3, RULE_C),
        ('BACKGROUND',   (0, 0), (-1, -1), BG_LIGHT),
    ]))
    story.append(sk)

    # ── 5  PROJEKTE ──────────────────────────────────────────────────────────
    story.extend(sec('PROJEKTE', sty))

    # — Bikehaus
    story.append(Paragraph(
        b('Bikehaus Freiburg') + '&#160;&#160;'
        + lnk('https://bikehausfreiburg.com', 'bikehausfreiburg.com')
        + '&#160;&#160;<font color="#1B3764">|</font>&#160;&#160;'
        + lnk('https://github.com/oeztuerkhamza/bikehausfreiburg', 'GitHub'),
        sty['entry_title'],
    ))
    story.append(Paragraph(
        it('Eigenes Produkt / Live im Einsatz'), sty['entry_sub']))
    story.append(bul(
        'Digitale Warenwirtschaft für ein Fahrradgeschäft: '
        'C#/.NET-API, Angular 17 Admin-Client + Electron Desktop-App, '
        'Playwright-Scraper und <b>Chrome Extension (MV3)</b>.',
        sty['bullet'],
    ))
    story.append(bul(
        b('Stack:') + ' C#/.NET, SQLite, EF Core, QuestPDF, Angular 17, '
        'Playwright, Electron, Docker, Nginx.',
        sty['bullet'],
    ))
    story.append(thin_rule())

    # — Kulturplattform
    story.append(Paragraph(
        b('Kulturplattform Freiburg e.V.') + '&#160;&#160;'
        + lnk('https://kulturplattformfreiburg.org',
              'kulturplattformfreiburg.org')
        + '&#160;&#160;<font color="#1B3764">|</font>&#160;&#160;'
        + lnk('https://github.com/oeztuerkhamza/KulturPlatform',
              'GitHub'),
        sty['entry_title'],
    ))
    story.append(Paragraph(
        it('Full-Stack Web-Entwicklung (Ehrenamtlich)'), sty['entry_sub']))
    story.append(bul(
        'Vereinswebsite mit Admin-Panel, Newsletter, '
        'Bildverarbeitung und DE/TR-Zweisprachigkeit. '
        '<b>.NET 10</b> Clean Architecture, React 19, '
        'Docker Compose – live.',
        sty['bullet'],
    ))
    story.append(thin_rule())

    # — DI-ONE
    story.append(Paragraph(
        b('DI-ONE') + ' – Enterprise Getränke-ERP',
        sty['entry_title'],
    ))
    story.append(Paragraph(
        it('Dicom GmbH, 02/2024 – 02/2026'), sty['entry_sub']))
    story.append(bul(
        'ERP-Neuentwicklung (Legacy → Web): '
        '<b>.NET 9, Clean Architecture</b>, 40+ API-Controller, '
        '<b>OpenAI Assistants v2</b>. '
        'Frontend: <b>Angular 19</b>, NgRx, MSAL SSO. '
        'CI/CD: Azure Pipelines, SonarCloud.',
        sty['bullet'],
    ))
    story.append(thin_rule())

    # — DI-FLUX
    story.append(KeepTogether([
        Paragraph(
            b('DI-FLUX') + ' – Zeiterfassungssystem&#160;('
            + it('IHK-Abschlussprojekt') + ')',
            sty['entry_title'],
        ),
        bul(
            'Webbasierte Arbeitszeiterfassung mit Soll/Ist-Vergleich, '
            'Urlaubsverwaltung und PDF-Monatsexport. '
            + b('Stack:') + ' Angular, C#/.NET, SQL Server, '
            'JWT-Authentifizierung.',
            sty['bullet'],
        ),
    ]))

    # ── 6  AUSBILDUNG ────────────────────────────────────────────────────────
    story.extend(sec('AUSBILDUNG', sty))
    edu = [
        ('09/2024 – 12/2025',
         'Berufsschule – Fachinformatiker für Anwendungsentwicklung',
         'Walther-Rathenau-Gewerbeschule, Freiburg'),
        ('02/2023 – 12/2023',
         'Sprachausbildung Deutsch',
         'Deutsches Kolleg Stuttgart'),
        ('05/2022 – 12/2022',
         'Zertifikat: Data Analytics &amp; Visualization (260 Std.)',
         'Clarusway IT School – Abschlusszertifikat · Python, SQL, Tableau'),
        ('10/2019 – 08/2022',
         'Studium Wirtschaftsingenieurwesen',
         'Technische Universität Istanbul (ITÜ)'),
        ('08/2018 – 07/2019',
         'Prüfungsvorbereitung &amp; Universitätsstudium',
         'Istanbul'),
        ('08/2015 – 07/2018',
         'Studium der Militärwissenschaften',
         'Türkische Luftwaffenakademie, Istanbul'),
    ]
    for idx, (period, title, inst) in enumerate(edu):
        story.append(entry_row(
            [Paragraph(title, sty['entry_title']),
             Paragraph(it(inst), sty['entry_sub'])],
            period, sty, CW, DW,
        ))
        if idx < len(edu) - 1:
            story.append(thin_rule())

    # ── 7  SPRACHEN ──────────────────────────────────────────────────────────
    story.extend(sec('SPRACHEN', sty))
    lang_rows = [
        [Paragraph(b('Türkisch'),  sty['skill_lbl']),
         Paragraph('Muttersprache', sty['skill_val'])],
        [Paragraph(b('Deutsch'),   sty['skill_lbl']),
         Paragraph('B2, fließend in Wort und Schrift',
                   sty['skill_val'])],
        [Paragraph(b('Englisch'),  sty['skill_lbl']),
         Paragraph('B2 – Gute IT-Fachkenntnisse in Wort und Schrift',
                   sty['skill_val'])],
    ]
    lt = Table(lang_rows, colWidths=[W * 0.22, W * 0.78])
    lt.setStyle(TableStyle([
        ('VALIGN',       (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING',  (0, 0), (0, -1),  0),
        ('LEFTPADDING',  (1, 0), (1, -1),  6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING',   (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 3),
    ]))
    story.append(lt)

    # ── 8  HOBBYS ────────────────────────────────────────────────────────────
    story.extend(sec('HOBBYS', sty))
    story.append(Paragraph(
        'Radfahren&#160;&#160;'
        '<font color="#1B3764">|</font>&#160;&#160;'
        'Hallenfußball&#160;&#160;'
        '<font color="#1B3764">|</font>&#160;&#160;'
        'Schwimmen',
        sty['body'],
    ))

    # ── 9  UNTERSCHRIFT ─────────────────────────────────────────────────────
    story.append(Spacer(1, 0.5 * cm))
    story.append(Image(SIGNATUR_PATH, width=4.0*cm, height=1.5*cm,
                       hAlign='LEFT'))
    story.append(Paragraph(f'Freiburg im Breisgau, {cfg["datum"]}', sty['footer']))
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
