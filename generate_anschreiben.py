#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Anschreiben – Hamza Öztürk · Fullstack Entwickler
Premium-Design · 10.03.2026
"""

import os
import sys
import re

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
OUTPUT        = r"C:\Users\hamza\Desktop\Lebenslauf\bewerbung_software_entwicker_herr_öztürk.pdf"
SIGNATUR_PATH = r"C:\Users\hamza\Desktop\Lebenslauf\sıgnatur.png"

# ─── LAYOUT ──────────────────────────────────────────────────────────────────
L_MARGIN  = 2.5 * cm
R_MARGIN  = 2.0 * cm
T_MARGIN  = 1.4 * cm
B_MARGIN  = 1.2 * cm
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
           spaceBefore=0, spaceAfter=0, align=TA_LEFT, leftIndent=0,
           firstLineIndent=0):
        return ParagraphStyle(
            name, fontName=font, fontSize=size, textColor=color,
            leading=leading or round(size * 1.4, 1),
            spaceBefore=spaceBefore, spaceAfter=spaceAfter,
            alignment=align, leftIndent=leftIndent,
            firstLineIndent=firstLineIndent,
        )
    return {
        'name':      ps('name',      'CV-B', 18, NAVY, leading=22),
        'role':      ps('role',      'CV-R', 10, GRAY, leading=13, spaceAfter=1),
        'contact':   ps('contact',   'CV-R',  8.5, DARK, leading=12),
        'empf':      ps('empf',      'CV-R',  9.5, DARK, leading=13, leftIndent=6),
        'datum':     ps('datum',     'CV-R',  9.5, DARK, leading=13, align=TA_RIGHT),
        'betreff':   ps('betreff',   'CV-B', 10.5, NAVY, leading=14,
                        spaceBefore=2, spaceAfter=2),
        'anrede':    ps('anrede',    'CV-R',  9.5, DARK, leading=13,
                        spaceAfter=1),
        'body':      ps('body',      'CV-R',  9.5, DARK, leading=13,
                        spaceAfter=3, align=TA_JUSTIFY),
        'bullet':    ps('bullet',    'CV-R',  9.5, DARK, leading=13,
                        spaceAfter=1, leftIndent=14, firstLineIndent=-14),
        'gruss':     ps('gruss',     'CV-R',  9.5, DARK, leading=13,
                        spaceBefore=1),
        'footer':    ps('footer',    'CV-R',  8.5, LGRAY, leading=11,
                        spaceBefore=1),
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


class BadgePill(Flowable):
    """Rounded pill badge with coloured background."""
    def __init__(self, text, bg=NAVY, fg=HexColor('#FFFFFF'),
                 font='CV-R', size=8, h_pad=6, v_pad=3, radius=4):
        super().__init__()
        self._text = text
        self._bg = bg
        self._fg = fg
        self._font = font
        self._size = size
        self._hpad = h_pad
        self._vpad = v_pad
        self._radius = radius

    def wrap(self, aw, ah):
        from reportlab.pdfbase.pdfmetrics import stringWidth
        tw = stringWidth(self._text, self._font, self._size)
        self.width = tw + 2 * self._hpad
        self.height = self._size + 2 * self._vpad
        return self.width, self.height

    def draw(self):
        self.canv.saveState()
        self.canv.setFillColor(self._bg)
        self.canv.roundRect(0, 0, self.width, self.height,
                            self._radius, fill=True, stroke=False)
        self.canv.setFillColor(self._fg)
        self.canv.setFont(self._font, self._size)
        self.canv.drawString(self._hpad, self._vpad + 1, self._text)
        self.canv.restoreState()


# ─── HELPERS ─────────────────────────────────────────────────────────────────
def lnk(url, label):
    return f'<a href="{url}" color="#1B3764">{label}</a>'


def _normalize_anrede(text):
    """Apply German letter rule: salutation ends with a comma."""
    s = (text or '').strip()
    if not s:
        return 'Sehr geehrte Damen und Herren,'
    s = s.rstrip(' .;:')
    if not s.endswith(','):
        s += ','
    return s


def _lowercase_first_content_char(text):
    """Lowercase first visible letter (ignoring HTML tags/spaces)."""
    s = str(text or '')
    in_tag = False
    for i, ch in enumerate(s):
        if ch == '<':
            in_tag = True
            continue
        if ch == '>':
            in_tag = False
            continue
        if in_tag or ch.isspace():
            continue
        if ch.isalpha():
            return s[:i] + ch.lower() + s[i + 1:]
        break
    return s


def _polish_german_phrasing(text):
    """Small wording cleanup for natural German phrasing."""
    s = str(text or '')
    s = re.sub(r'\bAMBOSSs\s+Mission\b', 'zur Mission von AMBOSS', s, flags=re.IGNORECASE)
    s = re.sub(r'\bzur Mission von AMBOSS von\b', 'zur Mission von AMBOSS', s, flags=re.IGNORECASE)
    return s


def _extract_aufgaben_from_ki(cfg):
    """Extract task-like phrases from KI-generated paragraphs."""
    direct = cfg.get('aufgaben', [])
    if isinstance(direct, list):
        cleaned = [str(x).strip() for x in direct if str(x).strip()]
        if cleaned:
            return cleaned[:4]

    source = ' '.join([
        str(cfg.get('absatz_2', '')),
        str(cfg.get('absatz_3', '')),
        str(cfg.get('absatz_4', '')),
    ])
    source_l = source.lower()

    patterns = [
        (r'backend|api|rest', 'Entwicklung moderner Backend-Services und APIs'),
        (r'frontend|angular|ui', 'Weiterentwicklung performanter Frontend-Module'),
        (r'zusammenarbeit|fachbereich|stakeholder', 'enge Zusammenarbeit mit Fachbereichen und Stakeholdern'),
        (r'bug|fehler|analyse|debug', 'strukturierte Fehleranalyse und priorisierte Bugfixes'),
        (r'ci/cd|pipeline|deployment|release', 'Automatisierung von Build-, Test- und Release-Prozessen'),
        (r'dokumentation|qualität|sonarqube|code', 'Sicherstellung von Code-Qualität und technischer Dokumentation'),
    ]

    tasks = []
    for patt, phrase in patterns:
        if re.search(patt, source_l) and phrase not in tasks:
            tasks.append(phrase)

    return tasks[:4]


def _build_aufgaben_blend_paragraph(cfg):
    """Build a company-specific paragraph blending job tasks with profile strengths."""
    firma = str(cfg.get('firma', 'Ihrem Unternehmen')).strip() or 'Ihrem Unternehmen'
    tasks = _extract_aufgaben_from_ki(cfg)

    if not tasks:
        return (
            f'Bei {firma} möchte ich meine Stärken in <b>C#/.NET</b>, '
            '<b>Angular</b>, Clean Architecture und CI/CD gezielt ein, '
            'um in anspruchsvollen Produktbereichen sichtbaren Mehrwert '
            'zu schaffen.'
        )

    task_txt = '; '.join(tasks[:3])
    return (
        f'Bei {firma} möchte ich meine Stärken in <b>C#/.NET</b>, '
        '<b>Angular</b>, Clean Architecture und CI/CD gezielt einsetzen, '
        'um in anspruchsvollen Produktbereichen sichtbaren Mehrwert '
        'zu schaffen.'
    )

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
    'stelle':           'Full-Stack Developer',
    'firma':            'Musterfirma GmbH',
    'ansprechpartner':  'Frau Mustermann',
    'ansprechpartner_titel': '',
    'firma_strasse':    'Musterstraße 1',
    'firma_plz_ort':    '79098 Freiburg im Breisgau',
    'du_kultur':        False,
    'anrede':           'Sehr geehrte Damen und Herren,',
    'datum':            '02. April 2026',
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
        'In meiner aktuellen Rolle bei der Dicom GmbH habe ich '
        'zuletzt konkrete Ergebnisse erzielt:'
    ),
    'highlights': [
        'SonarQube-Violations um 99 % reduziert (2.100 → 30) in drei Wochen',
        'Deployment-Zeiten um 40 % beschleunigt durch CI/CD-Pipeline-Aufbau',
        'Monolithische ERP-Desktop-Anwendung erfolgreich auf Clean Architecture migriert',
        'Systematisches Bug-Fixing und Feature-Entwicklung – von der Anforderungsanalyse bis zum Rollout',
    ],
    'absatz_3': (
        'Diese Kombination aus technischer Tiefe, Verständnis für '
        'Unternehmensprozesse und Erfahrung im 3rd-Level-Support '
        'macht mich zu einem Entwickler, der nicht nur Code schreibt – '
        'sondern mitdenkt.'
    ),
    'absatz_4': (
        'Ich freue mich auf ein persönliches Gespräch, um Sie davon '
        'zu überzeugen, wie ich Ihre Projekte technisch und menschlich '
        'voranbringe.'
    ),
    'absatz_5': '',
    'gehalt':           '',
    'eintritt':         '',
    'arbeitsmodell':    '',
    'anlagen': '',
}


# ─── BUILD STORY ─────────────────────────────────────────────────────────────
def build(story, sty, W, cfg=None):
    cfg = {**DEFAULT_CONFIG, **(cfg or {})}
    du = cfg.get('du_kultur', False)
    SEP = '&nbsp;&nbsp;·&nbsp;&nbsp;'

    # ── 1  ABSENDER-HEADER ───────────────────────────────────────────────────
    story.append(Paragraph('Hamza Öztürk', sty['name']))
    story.append(Spacer(1, 2))
    story.append(Paragraph(
        'Bissierstr. 16, 79114 Freiburg',
        sty['contact']))

    story.append(Spacer(1, 0.15 * cm))
    story.append(AccentBar(W, thickness=1))
    story.append(Spacer(1, 0.15 * cm))

    # ── 2  EMPFÄNGER + DATUM ─────────────────────────────────────────────────
    ap = (cfg.get('ansprechpartner') or '').strip()
    ap_titel = (cfg.get('ansprechpartner_titel') or '').strip()
    if ap and ap_titel:
        ap_name = re.sub(r'^(Frau|Herrn?)\s+', '', ap).strip()
        ap_line = f'{ap_name} · {ap_titel}'
    elif ap:
        ap_line = ap
    else:
        ap_line = ''

    empf_parts = [cfg['firma']]
    if ap_line:
        empf_parts.append(ap_line)
    empf_parts.append(cfg['firma_strasse'])
    empf_parts.append(cfg['firma_plz_ort'])

    empf_para = Paragraph('<br/>'.join(empf_parts), sty['empf'])
    datum_para = Paragraph(f'Freiburg, {cfg["datum"]}', sty['datum'])

    info_table = Table(
        [[empf_para, datum_para]],
        colWidths=[W * 0.62, W * 0.38],
    )
    info_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(info_table)

    story.append(Spacer(1, 0.3 * cm))

    # ── 3  BETREFF ───────────────────────────────────────────────────────────
    story.append(Paragraph(cfg['betreff'], sty['betreff']))

    story.append(Spacer(1, 0.15 * cm))

    # ── 4  ANREDE ────────────────────────────────────────────────────────────
    anrede = cfg.get('anrede', '')
    if not anrede:
        if du and ap:
            ap_short = re.sub(r'^(Frau|Herrn?)\s+', '', ap).strip()
            anrede = f'Hallo {ap_short},'
        else:
            anrede = _normalize_anrede('')
    else:
        anrede = _normalize_anrede(anrede)
    story.append(Paragraph(anrede, sty['anrede']))

    # ── 5  FLIESSTEXT ────────────────────────────────────────────────────────
    p1 = _polish_german_phrasing(cfg.get('absatz_1', DEFAULT_CONFIG['absatz_1']))
    story.append(Paragraph(_lowercase_first_content_char(p1), sty['body']))

    # Intro before highlights (absatz_2)
    p2 = cfg.get('absatz_2', '')
    if p2 and p2.strip():
        story.append(Paragraph(_polish_german_phrasing(p2), sty['body']))

    # Bullet highlights
    highlights = cfg.get('highlights', [])
    if isinstance(highlights, list) and highlights:
        for item in highlights:
            story.append(Paragraph(f'•&nbsp;&nbsp;{item}', sty['bullet']))
        story.append(Spacer(1, 2))

    # Remaining paragraphs
    for key in ('absatz_3', 'absatz_4', 'absatz_5'):
        val = cfg.get(key, '')
        if val and val.strip():
            story.append(Paragraph(_polish_german_phrasing(val), sty['body']))

    # ── 6  GRUSSFORMEL ───────────────────────────────────────────────────────
    gruss = 'Herzliche Grüße' if du else 'Mit freundlichen Grüßen'
    story.append(Spacer(1, 0.1 * cm))
    story.append(Paragraph(gruss, sty['gruss']))

    # Signature image
    if os.path.exists(SIGNATUR_PATH):
        sig = Image(SIGNATUR_PATH, width=3.5 * cm, height=1.2 * cm)
        sig.hAlign = 'LEFT'
        story.append(Spacer(1, 0.1 * cm))
        story.append(sig)
        story.append(Spacer(1, 0.05 * cm))
    else:
        story.append(Spacer(1, 0.15 * cm))

    story.append(Paragraph('Hamza Öztürk', sty['gruss']))

    # ── 7  FOOTER (Gehalt / Eintritt / Arbeitsmodell) ──────────────────────
    gehalt = cfg.get('gehalt', '')
    eintritt = cfg.get('eintritt', '')
    arbeitsmodell = cfg.get('arbeitsmodell', '')
    has_footer = any([gehalt, eintritt, arbeitsmodell])

    if has_footer:
        story.append(Spacer(1, 0.2 * cm))
        if gehalt:
            story.append(Paragraph(f'Gehalt: {gehalt}', sty['footer']))
        if eintritt:
            story.append(Paragraph(f'Eintritt: {eintritt}', sty['footer']))
        if arbeitsmodell:
            story.append(Paragraph(f'Arbeitsmodell: {arbeitsmodell}',
                                   sty['footer']))


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
