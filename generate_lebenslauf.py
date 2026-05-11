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
L_MARGIN  = 1.6 * cm
R_MARGIN  = 1.5 * cm
T_MARGIN  = 1.2 * cm
B_MARGIN  = 1.2 * cm
SIDEBAR_W = 4 * mm
SEC_GAP   = 0.14 * cm

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

def register_fonts():
    for name, path in _FONT_MAP.items():
        if os.path.exists(path):
            pdfmetrics.registerFont(TTFont(name, path))
        else:
            # fallback to Arial
            fb = path
            if 'calibrib' in path: fb = path.replace('calibrib', 'arialbd')
            elif 'calibriz' in path: fb = path.replace('calibriz', 'arialbi')
            elif 'calibrii' in path: fb = path.replace('calibrii', 'ariali')
            else: fb = path.replace('calibri', 'arial')
            
            if os.path.exists(fb):
                pdfmetrics.registerFont(TTFont(name, fb))


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
        'entry_sub':   ps('entry_sub',   'CV-I', 8.0, GRAY, leading=9.8, spaceAfter=0.3, leftIndent=8),
        'period':      ps('period',      'CV-R', 8.0, LGRAY, leading=10.0, align=TA_RIGHT),
        'bullet':      ps('bullet',      'CV-R', 8.3, DARK, leading=10.2,
                          spaceAfter=0.4, leftIndent=14, align=TA_JUSTIFY),
        'profile':     ps('profile',     'CV-R', 8.5, DARK, leading=10.4,
                          spaceAfter=0.4, leftIndent=8, align=TA_JUSTIFY),
        'footer':      ps('footer',      'CV-R', 8, LGRAY, leading=10, spaceBefore=0.5),
        'skill_lbl':   ps('skill_lbl',   'CV-B', 8.3, NAVY, leading=10.2),
        'skill_val':   ps('skill_val',   'CV-R', 8.2, DARK, leading=10.2),
        # Ausbildung-specific (lower indent to keep current alignment)
        'edu_title':   ps('edu_title',   'CV-B', 8.8, DARK, leading=10.8, leftIndent=4),
        'edu_bullet':  ps('edu_bullet',  'CV-R', 8.3, DARK, leading=10.2,
                          spaceAfter=0.4, leftIndent=10, align=TA_JUSTIFY),
    }


# ─── CUSTOM FLOWABLES ───────────────────────────────────────────────────────
class SectionHeading(Flowable):
    """Premium heading: text + short thick navy underline + thin gray continuation."""
    def __init__(self, text, style):
        super().__init__()
        self._para = Paragraph(text, style)

    def wrap(self, aw, ah):
        pw, ph = self._para.wrap(aw, ah)
        self.height = ph + 3.5
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
        # Clip to frame area
        c.saveState()
        p = c.beginPath()
        p.rect(b, b, self.img_w, self.img_h)
        c.clipPath(p, stroke=0)
        # Draw image zoomed (centered)
        zw = self.img_w * z
        zh = self.img_h * z
        ox = b - (zw - self.img_w) / 2
        oy = b - (zh - self.img_h) / 2
        c.drawImage(self.img_path, ox, oy, zw, zh,
                    preserveAspectRatio=False)
        c.restoreState()
        # Border
        c.saveState()
        c.setStrokeColor(NAVY)
        c.setLineWidth(b)
        c.rect(b / 2, b / 2, self.img_w + b, self.img_h + b,
               fill=False, stroke=True)
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
            Spacer(1, 1.5)]


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
DEFAULT_CONFIG = {
    'stelle':        'Fullstack Entwickler',
    'datum':         datetime.now().strftime('%d.%m.%Y'),
}


# ─── BUILD STORY ─────────────────────────────────────────────────────────────
def build(story, sty, W, cfg=None):
    cfg = {**DEFAULT_CONFIG, **(cfg or {})}
    DW = W * 0.20
    CW = W - DW - 0.3 * cm
    DW_EXP = W * 0.13
    CW_EXP = W - DW_EXP

    # ── 1  HEADER ────────────────────────────────────────────────────────────
    PHOTO_W = 2.5 * cm
    PHOTO_H = 3.5 * cm
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
            cfg['stelle'],
            sty['role'],
        ),
        Spacer(1, 2),
        contact_table,
    ]

    photo = PhotoFrame(FOTO_PATH, PHOTO_W, PHOTO_H, border=1.1, zoom=1.40)
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
        Spacer(1, 0.04 * cm),
        SectionHeading('KURZPROFIL', sty['section']),
        Spacer(1, 1.5),
    ])
    story.append(Paragraph(
        'Full-Stack-Entwickler mit Fokus auf <b>C#/.NET</b>, <b>Angular</b>, '
        '<b>Azure</b> und <b>CI/CD</b>. Über 2 Jahre Erfahrung in der '
        'Modernisierung von ERP-Systemen, inkl. vollständiger Migration einer '
        'Legacy-Desktop-Anwendung in eine skalierbare Web-Architektur. '
        'Starke End-to-End-Kompetenz: Datenbankmodellierung, API-Design, '
        'Frontend-Entwicklung, Cloud-Infrastruktur, Testautomatisierung. '
        'Nachweisbare Verbesserungen in Performance, Code-Qualität und '
        'Deployment-Geschwindigkeit.',
        sty['profile'],
    ))

    # ── 3  BERUFSERFAHRUNG ───────────────────────────────────────────────────
    story.extend(sec('BERUFSERFAHRUNG', sty))

    # Title row: company/role left, date right – same line
    exp_hdr = Table(
        [[Paragraph(b('Dicom GmbH - Full-Stack Entwickler'), sty['entry_title']),
          Paragraph('02/2024&nbsp;–&nbsp;02/2026', sty['period'])]],
        colWidths=[W * 0.79, W * 0.18],
    )
    exp_hdr.setStyle(TableStyle([
        ('VALIGN',       (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING',  (0, 0), (0, -1),  0),
        ('LEFTPADDING',  (1, 0), (1, -1),  0),
        ('RIGHTPADDING', (0, 0), (0, -1),  0),
        ('RIGHTPADDING', (1, 0), (1, -1),  0),
        ('TOPPADDING',   (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 0),
    ]))

    # Bullets use full width (no date column reservation)
    story.append(KeepTogether([
        exp_hdr,
        bul(
            'Migration eines kompletten ERP-Systems von WinForms zu einer '
            '<b>C#/.NET 10</b> + <b>Angular</b> Web-Lösung.',
            sty['bullet'],
        ),
        bul(
            'Einführung einer <b>Clean Architecture</b> und modularen API-Struktur.',
            sty['bullet'],
        ),
        bul(
            'Neuaufbau und Optimierung der Datenbankmodelle (<b>EF Core</b>, '
            'SQL Server); Verbesserung kritischer SQL-Queries.',
            sty['bullet'],
        ),
        bul(
            'Aufbau von CI/CD-Pipelines (<b>GitHub Actions</b>, <b>Azure DevOps</b>): '
            'Deployment-Zeit um <b>40 %</b> reduziert, '
            'SonarQube-Violations um <b>99 %</b> gesenkt.',
            sty['bullet'],
        ),
        bul(
            'Betrieb der gesamten Infrastruktur in der <b>Azure Cloud</b> '
            '(Dev/Staging/Prod).',
            sty['bullet'],
        ),
        bul(
            'Entwicklung und Wartung von REST-APIs, inkl. KI-gestützter Tools '
            'zur Beschleunigung von Entwicklungszyklen.',
            sty['bullet'],
        ),
        bul(
            'Lösung mehrerer kritischer Bugs in produktiven ERP-Modulen.',
            sty['bullet'],
        ),
    ]))

    # ── 4  PROJEKTE ──────────────────────────────────────────────────────────
    story.extend(sec('PROJEKTE', sty))

    # — Fahrrad-Warenwirtschaftssystem (3× Live)
    story.append(KeepTogether([
        Paragraph(
            b('Fahrrad-Warenwirtschaftssystem')
            + ' <font color="#1B3764">(3× Live)</font>',
            sty['entry_title'],
        ),
        Paragraph(
            lnk('https://bikehausfreiburg.com', 'bikehausfreiburg.com')
            + ' ' + lnk('https://github.com/oeztuerkhamza/bikehausfreiburg', '(GitHub)')
            + '&#160;&#160;<font color="#1B3764">|</font>&#160;&#160;'
            + lnk('https://karaarslan-bike.de', 'karaarslan-bike.de')
            + ' ' + lnk('https://github.com/oeztuerkhamza/karaarslan-bike', '(GitHub)')
            + '&#160;&#160;<font color="#1B3764">|</font>&#160;&#160;'
            + lnk('https://benlirad.de', 'benlirad.de')
            + ' ' + lnk('https://github.com/oeztuerkhamza/benlirad', '(GitHub)'),
            sty['entry_sub'],
        ),
        bul(
            '<b>.NET 9</b> API (30+ Endpoints, 35+ Domain-Entities), '
            '<b>Angular 17/19</b> Admin-SPA + SSR-Homepage, '
            'SQLite/EF Core 8 — eigenentwickeltes Full-Stack-System '
            'für Fahrradgeschäfte; 3× produktiv deployed.',
            sty['bullet'],
        ),
        bul(
            'Buchung &amp; Vermietung, Kundenverwaltung, Verkauf/Einkauf, '
            'PDF-Verträge mit QR-Code (QuestPDF), dynamische Preisstaffelung, '
            'Kleinanzeigen-Scraper (Playwright), Google-Reviews-API, '
            'digitale Unterschriften.',
            sty['bullet'],
        ),
        bul(
            '5-Container Docker-Setup: API, Admin-SPA, SSR-Homepage, '
            'Nginx (Rate Limiting, Brotli/Gzip, HSTS/CSP, Let\'s Encrypt), Certbot; '
            'JWT-Auth mit rotierbaren Secrets; Background-Services '
            'für Sync, Backup und E-Mail.',
            sty['bullet'],
        ),
        bul(
            'GitHub Actions CI/CD: pfadbasierte Change-Detection, '
            'atomare Deployments (Zero Downtime), Healthcheck-Jobs; '
            'Mailcow E-Mail-Server (DKIM/SPF/DMARC); '
            'SEO: Prerendering, IndexNow, stadtbasierte Landing-Pages, '
            'mehrsprachig (DE/FR/TR).',
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

    # — Bewerbungs-Manager
    story.append(KeepTogether([
        Paragraph(
            b('Bewerbungs-Manager')
            + ' – KI-gestützte Bewerbungsautomatisierung',
            sty['entry_title'],
        ),
        bul(
            'Python, OpenAI API — Tool zur PDF-Erstellung, '
            'Profilverwaltung und automatisierten Analyse von Stellenanzeigen.',
            sty['bullet'],
        ),
    ]))

    # ── 5  IT-KENNTNISSE ─────────────────────────────────────────────────────
    story.extend(sec('IT-KENNTNISSE', sty))
    skills = [
        ('Backend',
         'C#, .NET Core, ASP.NET Core, Clean Architecture, EF Core,Web-Scraping, '
         'RESTful APIs, xUnit'),
        ('Frontend',
         'Angular (17/19), TypeScript, React 19, Tailwind CSS, NgRx,HTML,Bulma '
         'Infragistics'),
        ('Datenbanken',
         'SQL Server, SQLite, SQL ,PostgreSQL'),
        ('DevOps &amp; Tools',
         'Docker, GitHub Actions, Azure DevOps, Azure Cloud, '
         'SonarQube, Git, CI/CD, Python '),
        ('KI &amp; Analytics',
         'OpenAI API, Claude, Prompt Engineering, Tableau,Copilot '
         ),
    ]
    rows = [[Paragraph(b(l), sty['skill_lbl']),
             Paragraph(v, sty['skill_val'])] for l, v in skills]
    sk = Table(rows, colWidths=[W * 0.21, W * 0.78],
               rowHeights=[14.6] * len(rows))
    sk.setStyle(TableStyle([
        ('VALIGN',       (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING',  (0, 0), (0, -1),  8),
        ('LEFTPADDING',  (1, 0), (1, -1),  8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING',   (0, 0), (-1, -1), 2.2),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 2.2),
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
        ('10/2019 – 08/2022',
         'Wirtschaftsingenieurwesen',
         'Technische Universität Istanbul (ITÜ)'),
        ('08/2015 – 07/2018',
         'Wirtschaftsingenieurwesen und Offizierausbildung',
         'Türkische Luftwaffenakademie, Istanbul'),
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
    story.append(Spacer(1, 0.4))

    for idx, (period, title, inst) in enumerate(edu):
        story.append(KeepTogether(entry_row(
            Paragraph(f'{title} — {inst}', sty['edu_title']),
            period, sty, CW, DW,
        )))
        if idx < len(edu) - 1:
            story.append(Spacer(1, 0.1))

    # ── 7  SPRACHEN ─────────────────────────────────────────────────────────
    story.extend([
        Spacer(1, 0.04 * cm),
        SectionHeading('SPRACHEN', sty['section']),
        Spacer(1, 1.5),
    ])
    lang_rows = [
        ('Türkisch',  'Muttersprache'),
        ('Deutsch',   'Fließend in Wort und Schrift'),
        ('Englisch',  'Fließend in Wort und Schrift'),
    ]
    lang_data = [[Paragraph(b(l), sty['skill_lbl']),
                  Paragraph(v, sty['skill_val'])] for l, v in lang_rows]
    lang_tbl = Table(lang_data, colWidths=[W * 0.21, W * 0.78],
                     rowHeights=[14.6] * len(lang_data))
    lang_tbl.setStyle(TableStyle([
        ('VALIGN',       (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING',  (0, 0), (0, -1),  8),
        ('LEFTPADDING',  (1, 0), (1, -1),  8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING',   (0, 0), (-1, -1), 2.2),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 2.2),
        ('LINEBELOW',    (0, 0), (-1, -1), 0.25, RULE_C),
        ('BACKGROUND',   (0, 0), (-1, 0), BG_SKILL),
        ('BACKGROUND',   (0, 1), (-1, 1), BG_SKILL2),
        ('BACKGROUND',   (0, 2), (-1, 2), BG_SKILL),
    ]))
    story.append(lang_tbl)

    # ── 8  UNTERSCHRIFT ─────────────────────────────────────────────────────
    story.append(Spacer(1, 0.35 * cm))
    story.append(Image(SIGNATUR_PATH, width=3.6*cm, height=1.3*cm,
                       hAlign='LEFT'))
    story.append(Paragraph(f'Freiburg, {cfg["datum"]}', sty['footer']))
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
