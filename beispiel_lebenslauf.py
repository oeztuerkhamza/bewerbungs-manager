#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Beispiel-Lebenslauf (Muster) im Design von generate_lebenslauf.py.

Alle Angaben sind frei erfunden ("Max Mustermann"). Das Skript zeigt, wie ein
fertiger Lebenslauf mit dem Layout des Bewerbungs-Managers aussieht, und
dient als Vorlage: Daten im Abschnitt BEISPIELDATEN ersetzen, ausfuehren,
fertig.

    py beispiel_lebenslauf.py            -> Beispiel_Lebenslauf_Max_Mustermann.pdf
    py beispiel_lebenslauf.py ziel.pdf   -> eigener Dateiname
"""

import os
import sys
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, FrameBreak,
    Paragraph, Spacer, KeepTogether,
)

import generate_lebenslauf as gl
from generate_lebenslauf import (
    b, lnk, bul, sec, rail_block, rail_paare, SEP,
    SectionHeading, TrackedLine, HRule, TRACK_RATIO,
    NAVY, GRAY, RAIL_RULE,
)
from pdf_text_utils import esc

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT = os.path.join(BASE_DIR, 'Beispiel_Lebenslauf_Max_Mustermann.pdf')


# ─── BEISPIELDATEN (frei erfunden) ──────────────────────────────────────────
NAME = 'Max Mustermann'
INITIALEN = 'MM'
STELLE = 'Junior Fullstack Entwickler'
ORT = 'Musterstadt'

KONTAKT = [
    'Musterstraße 12, 12345 Musterstadt',
    lnk('tel:+4915100000000', '+49 151 00000000', '#9FC3EC'),
    lnk('mailto:max.mustermann@example.com',
        'max.mustermann@example.com', '#9FC3EC'),
    lnk('https://linkedin.com/in/max-mustermann',
        'linkedin.com/in/max-mustermann', '#9FC3EC'),
    lnk('https://github.com/max-mustermann',
        'github.com/max-mustermann', '#9FC3EC'),
]

PERSOENLICH = [
    'Geb. 01.01.1998 in Musterstadt',
    'Führerschein Klasse B',
]

KURZPROFIL = (
    'Ich entwickle Webanwendungen von der Datenbank bis zur Oberfläche und '
    'achte darauf, dass sie im Alltag der Anwender funktionieren. Als '
    '<b>Fachinformatiker für Anwendungsentwicklung (IHK)</b> habe ich bei der '
    'Muster Software GmbH ein Kundenportal mit <b>über 1.500 aktiven '
    'Nutzern</b> mitentwickelt. Schwerpunkte: <b>C#/.NET</b>, Angular und '
    'saubere REST-APIs – getestet, dokumentiert und per CI/CD ausgeliefert.'
)

ERFAHRUNG = [
    {
        'title':  'Muster Software GmbH – Junior Softwareentwickler',
        'period': '08/2025 – heute',
        'sub':    'Musterstadt',
        'bullets': [
            'Weiterentwicklung eines <b>Kundenportals</b> (ASP.NET Core 8, '
            'Angular 18) mit über 1.500 aktiven Nutzern: Rechnungsübersicht, '
            'Vertragsverwaltung und Self-Service-Funktionen.',

            'REST-Schnittstelle zum ERP-System des Kunden konzipiert und '
            'umgesetzt; manuelle Datenpflege um rund <b>10 Stunden pro '
            'Woche</b> reduziert.',

            'Ladezeiten der Hauptseiten durch Caching und optimierte '
            'SQL-Abfragen um <b>35 %</b> verkürzt (EF Core, SQL Server).',

            'Code-Reviews im Team, Unit-Tests mit xUnit; Auslieferung über '
            '<b>GitHub Actions</b> und Docker auf Azure.',
        ],
    },
    {
        'title':  'Muster Software GmbH – Ausbildung zum Fachinformatiker '
                  'für Anwendungsentwicklung',
        'period': '08/2022 – 07/2025',
        'sub':    'Musterstadt',
        'bullets': [
            'Mitarbeit an internen Tools zur Zeiterfassung und '
            'Projektplanung (C#, WPF, später Migration auf Angular).',

            'Abschlussprojekt: <b>Ticket-System</b> für den IT-Support mit '
            'E-Mail-Import, Prioritäten und Auswertungen – heute im '
            'Produktivbetrieb.',

            'Anwenderbetreuung im 1st-Level-Support während der '
            'Ausbildungsrotation.',
        ],
    },
    {
        'title':  'Elektromarkt Beispiel – Verkaufsberater (Teilzeit)',
        'period': '09/2019 – 07/2022',
        'bullets': [
            'Kundenberatung zu Laptops, Smartphones und Netzwerktechnik; '
            'Einrichtung von Geräten für Kunden.',
        ],
    },
]

PROJEKTE = [
    {
        'head': (b('Vereinsverwaltung') + ' – Webanwendung für einen Sportverein',
                 'ehrenamtlich · Live' + SEP
                 + lnk('https://github.com/max-mustermann/verein', 'GitHub')),
        'bullets': [
            '<b>.NET 8</b>-API und Angular-Frontend für Mitglieder, Beiträge '
            'und Termine; Betrieb mit Docker auf einem eigenen Server.',
        ],
    },
    {
        'head': (b('Haushaltsbuch-App') + ' – privates Lernprojekt',
                 'Open Source' + SEP
                 + lnk('https://github.com/max-mustermann/haushaltsbuch',
                       'GitHub')),
        'bullets': [
            'React, TypeScript und Node.js mit PostgreSQL; Diagramme zur '
            'Ausgabenanalyse, CSV-Import von Kontoauszügen.',
        ],
    },
]

AUSBILDUNG = [
    {
        'title':  'Fachinformatiker für Anwendungsentwicklung (IHK)',
        'period': '08/2022 – 07/2025',
        'inst':   'Berufsschule Musterstadt / IHK Musterregion',
        'detail': 'Abschlussprojekt: Ticket-System für den IT-Support '
                  '(ASP.NET Core, Angular)',
    },
    {
        'title':  'Fachhochschulreife',
        'period': '08/2017 – 07/2019',
        'inst':   'Berufskolleg Musterstadt',
        'detail': 'Schwerpunkt Informatik',
    },
]

SKILLS = [
    ('Backend',      'C#, .NET 8, ASP.NET Core, EF Core, REST-APIs, xUnit'),
    ('Frontend',     'Angular, TypeScript, React, HTML, CSS, Tailwind'),
    ('Datenbanken',  'SQL Server, PostgreSQL, SQLite'),
    ('DevOps &amp; Tools', 'Git, Docker, GitHub Actions, Azure, Scrum, Jira'),
]

SPRACHEN = [
    ('Deutsch',  'Muttersprache'),
    ('Englisch', 'B2 – sicher in Wort und Schrift'),
    ('Spanisch', 'A2 – Grundkenntnisse'),
]


# ─── SEITE ──────────────────────────────────────────────────────────────────
def _seite_zeichnen(canvas, doc):
    """Navy-Spalte wie im Original; statt Foto ein Initialen-Platzhalter."""
    w, h = A4
    canvas.saveState()
    canvas.setFillColor(NAVY)
    canvas.rect(0, 0, gl.RAIL_BG_W, h, fill=True, stroke=False)

    # Platzhalter fuer das Bewerbungsfoto
    cx = gl.RAIL_BG_W / 2
    cy = h - gl.FOTO_H / 2
    r = 2.0 * cm
    canvas.setFillColor(RAIL_RULE)
    canvas.circle(cx, cy, r, fill=True, stroke=False)
    canvas.setFillColor(gl.RAIL_HEAD)
    canvas.setFont('CV-B', 30)
    canvas.drawCentredString(cx, cy - 10.5, INITIALEN)
    canvas.setFont('CV-R', 7)
    canvas.setFillColor(gl.RAIL_TXT)
    canvas.drawCentredString(cx, cy - r - 12, 'Platz für Bewerbungsfoto')
    canvas.restoreState()


def baue_spalten(sty):
    rail = rail_block('KONTAKT', sty, KONTAKT)
    rail += rail_block('PERSÖNLICH', sty, PERSOENLICH)
    rail += rail_paare('IT-KENNTNISSE', sty, SKILLS)
    rail += rail_paare('SPRACHEN', sty, SPRACHEN, gap=0)

    main = [
        Paragraph(esc(NAME), sty['name']),
        Spacer(1, 1.5),
        TrackedLine(esc(STELLE).upper(), 'CV-R', 9.8, GRAY,
                    track=round(9.8 * TRACK_RATIO, 2)),
        Spacer(1, 5),
        HRule(NAVY, 0.9, space_after=0.26 * cm),
        SectionHeading('KURZPROFIL', sty['section']),
        Spacer(1, 2.5),
        Paragraph(KURZPROFIL, sty['profile']),
    ]

    def eintrag(titel, meta, bullets, titel_stil='entry_title',
                bullet_stil='bullet'):
        teile = [Paragraph(titel, sty[titel_stil])]
        if meta:
            teile.append(Paragraph(meta, sty['entry_meta']))
        teile += [bul(t, sty[bullet_stil]) for t in bullets]
        return KeepTogether(teile)

    main += sec('BERUFSERFAHRUNG', sty)
    for i, job in enumerate(ERFAHRUNG):
        meta = job['period'] + (SEP + job['sub'] if job.get('sub') else '')
        main.append(eintrag(b(job['title']), meta, job['bullets']))
        if i < len(ERFAHRUNG) - 1:
            main.append(Spacer(1, 7))

    main += sec('PROJEKTE', sty)
    for i, p in enumerate(PROJEKTE):
        titel, meta = p['head']
        main.append(eintrag(titel, meta, p['bullets']))
        if i < len(PROJEKTE) - 1:
            main.append(Spacer(1, 6))

    main += sec('AUSBILDUNG', sty)
    for i, e in enumerate(AUSBILDUNG):
        meta = e['period'] + (SEP + e['inst'] if e.get('inst') else '')
        detail = [e['detail']] if e.get('detail') else []
        main.append(eintrag(b(e['title']), meta, detail,
                            titel_stil='edu_title', bullet_stil='edu_bullet'))
        if i < len(AUSBILDUNG) - 1:
            main.append(Spacer(1, 5))

    main.append(Spacer(1, 0.34 * cm))
    main.append(Paragraph(
        f'{ORT}, {datetime.now().strftime("%d.%m.%Y")}', sty['footer']))
    main.append(Paragraph(b(NAME), sty['footer']))
    return rail, main


def _baue_pdf(out, tighten):
    H = A4[1]
    rand = dict(leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    rail_h = H - gl.FOTO_H - gl.FOTO_GAP - gl.B_MARGIN
    f_rail = Frame(gl.RAIL_X, gl.B_MARGIN, gl.RAIL_W, rail_h,
                   id='rail', **rand)
    f_main = Frame(gl.MAIN_X, gl.B_MARGIN, gl.MAIN_W,
                   H - gl.T_MARGIN - gl.B_MARGIN, id='main', **rand)
    doc = BaseDocTemplate(
        out, pagesize=A4,
        title=f'Lebenslauf – {NAME} (Beispiel)', author=NAME,
        subject=f'Bewerbung als {STELLE}', creator='Python / ReportLab',
    )
    doc.addPageTemplates([PageTemplate(id='cv', frames=[f_rail, f_main],
                                       onPage=_seite_zeichnen)])
    rail, main = baue_spalten(gl.make_styles(tighten))
    doc.build(rail + [FrameBreak()] + main)
    return doc.page


def generate(output_path=None):
    gl.register_fonts()
    out = output_path or OUTPUT
    for tighten in gl._FIT_STUFEN:
        if _baue_pdf(out, tighten) <= 1:
            break
    return out


if __name__ == '__main__':
    ziel = sys.argv[1] if len(sys.argv) > 1 else None
    print('PDF erfolgreich erstellt:\n  ' + generate(ziel))
