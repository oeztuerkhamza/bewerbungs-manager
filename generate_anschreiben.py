#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Anschreiben – Hamza Öztürk · Fullstack Entwickler
Premium-Design · 10.03.2026
"""

import os
import sys

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, HRFlowable,
    Table, TableStyle, Image, Flowable,
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ─── PATHS ────────────────────────────────────────────────────────────────────
OUTPUT        = r"C:\Users\hamza\Desktop\Lebenslauf\Hamza_Oeztuerk_Anschreiben_Fullstack_Entwickler.pdf"
SIGNATUR_PATH = r"C:\Users\hamza\Desktop\Lebenslauf\sıgnatur.png"

# ─── LAYOUT ──────────────────────────────────────────────────────────────────
L_MARGIN  = 2.5 * cm
R_MARGIN  = 2.0 * cm
T_MARGIN  = 1.6 * cm
B_MARGIN  = 1.6 * cm
SIDEBAR_W = 4 * mm           # left decorative stripe width

# ─── COLOURS ─────────────────────────────────────────────────────────────────
NAVY      = HexColor('#1B3764')
DARK      = HexColor('#1F1F1F')
GRAY      = HexColor('#4A4A4A')
LGRAY     = HexColor('#777777')
RULE_C    = HexColor('#D0D4DD')

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
        'name':      ps('name',      'CV-B', 22, NAVY, leading=26),
        'role':      ps('role',      'CV-R', 11, GRAY, leading=15, spaceAfter=2),
        'contact':   ps('contact',   'CV-R',  9, DARK, leading=13),
        'empf':      ps('empf',      'CV-R', 10, DARK, leading=14),
        'datum':     ps('datum',     'CV-R', 10, DARK, leading=14, align=TA_RIGHT),
        'betreff':   ps('betreff',   'CV-B', 11, NAVY, leading=15,
                        spaceBefore=6, spaceAfter=6),
        'anrede':    ps('anrede',    'CV-R', 10, DARK, leading=15,
                        spaceAfter=4),
        'body':      ps('body',      'CV-R', 10, DARK, leading=15.5,
                        spaceAfter=6, align=TA_JUSTIFY),
        'gruss':     ps('gruss',     'CV-R', 10, DARK, leading=15,
                        spaceBefore=4),
        'footer':    ps('footer',    'CV-R',  9, LGRAY, leading=12,
                        spaceBefore=2),
    }


# ─── CUSTOM FLOWABLES ───────────────────────────────────────────────────────
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


# ─── HELPERS ─────────────────────────────────────────────────────────────────
def lnk(url, label):
    return f'<a href="{url}" color="#1B3764">{label}</a>'

def _build_role_line(stelle, detail):
    """Build the role subtitle, e.g. 'Fullstack Entwickler | C# | .NET'."""
    parts = [p.strip() for p in detail.split('|')]
    sep = '&#160;&#160;<font color="#1B3764">|</font>&#160;&#160;'
    return sep.join([stelle] + parts)


# ─── PAGE DECORATION ────────────────────────────────────────────────────────
def _draw_page(canvas, doc):
    """Navy sidebar stripe + bottom rule – matching Lebenslauf design."""
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
    'stelle':           'Fullstack Entwickler',
    'stelle_detail':    'C# | .NET | Angular',
    'firma':            'Musterfirma GmbH',
    'ansprechpartner':  'Frau / Herrn Mustermann',
    'firma_strasse':    'Musterstraße 1',
    'firma_plz_ort':    '79098 Freiburg im Breisgau',
    'anrede':           'Sehr geehrte Damen und Herren,',
    'datum':            '10.03.2026',
    'betreff':          'Bewerbung als Fullstack Entwickler – C# / .NET / Angular',
    'absatz_1': (
        'mit großem Interesse habe ich Ihre Stellenausschreibung als '
        'Fullstack Entwickler gelesen. Als ausgebildeter '
        '<b>Fachinformatiker für Anwendungsentwicklung</b> mit '
        'fundierter Praxis in <b>C#/.NET</b> und <b>Angular</b> '
        'bringe ich genau die Kombination aus technischer Tiefe und '
        'Eigeninitiative mit, die Ihr Team weiterbringt.'
    ),
    'absatz_2': (
        'In meiner bisherigen Position bei der Dicom GmbH war ich '
        'maßgeblich an der <b>Neuentwicklung eines Enterprise-ERP-Systems</b> '
        'beteiligt: Ich habe über 40 API-Controller in .NET 9 mit '
        'Clean Architecture umgesetzt, das Angular-19-Frontend mit NgRx '
        'und MSAL-SSO aufgebaut und eine CI/CD-Pipeline eingeführt, die '
        'die <b>Deployment-Zeit um 40 %</b> verkürzt hat. Besonders stolz '
        'bin ich darauf, die SonarQube-Violations innerhalb von '
        '<b>drei Wochen von 2.100 auf 30</b> gesenkt zu haben – '
        'ein Ergebnis, das meine Leidenschaft für sauberen, '
        'wartbaren Code zeigt.'
    ),
    'absatz_3': (
        'Neben dem Berufsalltag betreibe ich eigene Open-Source-Projekte: '
        '<b>Bikehaus Freiburg</b> – ein produktiv eingesetztes '
        'Warenwirtschaftssystem mit .NET-API, Angular-Client, '
        'Electron-Desktop-App und Chrome Extension – sowie die '
        '<b>Kulturplattform Freiburg e.V.</b>, eine zweisprachige '
        'Vereinswebsite mit React 19 und .NET 10. Diese Projekte '
        'belegen, dass ich End-to-End-Verantwortung übernehme: '
        'von der Architektur über die Implementierung bis zum '
        'Deployment auf eigenen Servern.'
    ),
    'absatz_4': (
        'Technologisch fühle ich mich im gesamten Stack zu Hause – '
        'von Docker-Containern und GitHub Actions über RESTful APIs '
        'bis hin zu modernen Frontend-Frameworks. Darüber hinaus '
        'setze ich <b>KI-Tools und Prompt Engineering</b> gezielt '
        'ein, um Entwicklungsprozesse zu beschleunigen und '
        'Code-Qualität zu steigern.'
    ),
    'absatz_5': (
        'Ich bin überzeugt, dass mein Profil – gepaart mit meiner '
        'Motivation, mich stetig weiterzuentwickeln – einen echten '
        'Mehrwert für Ihr Unternehmen darstellt. '
        'Über die Einladung zu einem persönlichen Gespräch '
        'freue ich mich sehr.'
    ),
    'anlagen': 'Lebenslauf, Arbeitszeugnisse, Zertifikate',
}


# ─── BUILD STORY ─────────────────────────────────────────────────────────────
def build(story, sty, W, cfg=None):
    cfg = {**DEFAULT_CONFIG, **(cfg or {})}

    # ── 1  ABSENDER-HEADER ───────────────────────────────────────────────────
    story.append(Paragraph('Hamza Öztürk', sty['name']))
    story.append(Spacer(1, 1))
    story.append(Paragraph(
        _build_role_line(cfg['stelle'], cfg['stelle_detail']),
        sty['role'],
    ))
    story.append(Spacer(1, 4))

    # Contact rows – split into two lines to prevent wrapping
    sep = '&#160;&#160;<font color="#1B3764">|</font>&#160;&#160;'
    line1_parts = [
        'Bissierstr.&#160;16, 79114&#160;Freiburg',
        '+49&#160;155&#160;66859378',
        'oeztuerk.hamza@web.de',
    ]
    line2_parts = [
        lnk('https://linkedin.com/in/hamzaoeztuerk',
            'linkedin.com/in/hamzaoeztuerk'),
        lnk('https://github.com/oeztuerkhamza',
            'github.com/oeztuerkhamza'),
    ]
    story.append(Paragraph(sep.join(line1_parts), sty['contact']))
    story.append(Paragraph(sep.join(line2_parts), sty['contact']))

    story.append(Spacer(1, 2))
    story.append(AccentBar(W, thickness=1))
    story.append(Spacer(1, 0.6 * cm))

    # ── 2  EMPFÄNGER ─────────────────────────────────────────────────────────
    story.append(Paragraph(cfg['firma'], sty['empf']))
    story.append(Paragraph(f'z. Hd. {cfg["ansprechpartner"]}', sty['empf']))
    story.append(Paragraph(cfg['firma_strasse'], sty['empf']))
    story.append(Paragraph(cfg['firma_plz_ort'], sty['empf']))

    story.append(Spacer(1, 0.7 * cm))

    # ── 3  DATUM ─────────────────────────────────────────────────────────────
    story.append(Paragraph(f'Freiburg im Breisgau, {cfg["datum"]}',
                           sty['datum']))

    story.append(Spacer(1, 0.5 * cm))

    # ── 4  BETREFF ───────────────────────────────────────────────────────────
    story.append(Paragraph(cfg['betreff'], sty['betreff']))

    story.append(Spacer(1, 0.3 * cm))

    # ── 5  ANREDE ────────────────────────────────────────────────────────────
    story.append(Paragraph(cfg['anrede'], sty['anrede']))

    # ── 6  FLIESSTEXT ────────────────────────────────────────────────────────
    story.append(Paragraph(
        'mit großem Interesse habe ich Ihre Stellenausschreibung als '
        'Fullstack Entwickler gelesen. Als ausgebildeter '
        '<b>Fachinformatiker für Anwendungsentwicklung</b> mit '
        'fundierter Praxis in <b>C#/.NET</b> und <b>Angular</b> '
        'bringe ich genau die Kombination aus technischer Tiefe und '
        'Eigeninitiative mit, die Ihr Team weiterbringt.',
        sty['body'],
    ))

    story.append(Paragraph(
        'In meiner bisherigen Position bei der Dicom GmbH war ich '
        'maßgeblich an der <b>Neuentwicklung eines Enterprise-ERP-Systems</b> '
        'beteiligt: Ich habe über 40 API-Controller in .NET 9 mit '
        'Clean Architecture umgesetzt, das Angular-19-Frontend mit NgRx '
        'und MSAL-SSO aufgebaut und eine CI/CD-Pipeline eingeführt, die '
        'die <b>Deployment-Zeit um 40 %</b> verkürzt hat. Besonders stolz '
        'bin ich darauf, die SonarQube-Violations innerhalb von '
        '<b>drei Wochen von 2.100 auf 30</b> gesenkt zu haben – '
        'ein Ergebnis, das meine Leidenschaft für sauberen, '
        'wartbaren Code zeigt.',
        sty['body'],
    ))

    story.append(Paragraph(
        'Neben dem Berufsalltag betreibe ich eigene Open-Source-Projekte: '
        '<b>Bikehaus Freiburg</b> – ein produktiv eingesetztes '
        'Warenwirtschaftssystem mit .NET-API, Angular-Client, '
        'Electron-Desktop-App und Chrome Extension – sowie die '
        '<b>Kulturplattform Freiburg e.V.</b>, eine zweisprachige '
        'Vereinswebsite mit React 19 und .NET 10. Diese Projekte '
        'belegen, dass ich End-to-End-Verantwortung übernehme: '
        'von der Architektur über die Implementierung bis zum '
        'Deployment auf eigenen Servern.',
        sty['body'],
    ))

    story.append(Paragraph(
        'Technologisch fühle ich mich im gesamten Stack zu Hause – '
        'von Docker-Containern und GitHub Actions über RESTful APIs '
        'bis hin zu modernen Frontend-Frameworks. Darüber hinaus '
        'setze ich <b>KI-Tools und Prompt Engineering</b> gezielt '
        'ein, um Entwicklungsprozesse zu beschleunigen und '
        'Code-Qualität zu steigern.',
        sty['body'],
    ))

    story.append(Paragraph(
        'Ich bin überzeugt, dass mein Profil – gepaart mit meiner '
        'Motivation, mich stetig weiterzuentwickeln – einen echten '
        'Mehrwert für Ihr Unternehmen darstellt. '
        'Über die Einladung zu einem persönlichen Gespräch '
        'freue ich mich sehr.',
        sty['body'],
    ))

    # ── 7  GRUSSFORMEL & UNTERSCHRIFT ────────────────────────────────────────
    story.append(Spacer(1, 0.1 * cm))
    story.append(Paragraph('Mit freundlichen Grüßen', sty['gruss']))
    story.append(Spacer(1, 0.15 * cm))
    story.append(Image(SIGNATUR_PATH, width=4.0*cm, height=1.5*cm,
                       hAlign='LEFT'))
    story.append(Paragraph('Hamza Öztürk', sty['footer']))

    # ── 8  ANLAGEN-HINWEIS ───────────────────────────────────────────────────
    story.append(Spacer(1, 0.5 * cm))
    story.append(HRFlowable(width='100%', thickness=0.35, color=RULE_C,
                            spaceBefore=4, spaceAfter=4))
    story.append(Paragraph(
        '<font color="#1B3764"><b>Anlagen:</b></font>&#160;&#160;'
        + cfg['anlagen'],
        sty['contact'],
    ))


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
        title='Anschreiben – Hamza Öztürk',
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
        title='Anschreiben – Hamza Öztürk', author='Hamza Öztürk',
        subject=f'Bewerbung als {(cfg or {}).get("stelle", "Fullstack Entwickler")}',
        creator='Python / ReportLab',
    )
    story = []
    build(story, sty, doc.width, cfg)
    doc.build(story, onFirstPage=_draw_page, onLaterPages=_draw_page)
    return out


if __name__ == '__main__':
    sys.exit(main())
