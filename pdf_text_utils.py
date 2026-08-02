#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gemeinsame Hilfsfunktionen zum sicheren Einfügen von Text in ReportLab-
Paragraphen. ReportLab parst Paragraph-Text als Mini-XML, d.h. ein einzelnes
ungeschütztes '&', '<' oder '>' (z.B. in einem Firmennamen wie "Müller & Sohn"
oder einem Betreff "C# & Angular") führt zu einem Render-Absturz.
"""

import re
from xml.sax.saxutils import escape as _xml_escape


def esc(text):
    """Vollständiges Escaping für reinen Text (keine Tags erwartet).

    Wandelt & < > in Entities um. Für Felder wie Firmenname, Adresse,
    Betreff, Anrede, Stellenbezeichnung – also alles, was vom Nutzer,
    der KI oder einer Web-Suche kommt und KEINE HTML-Auszeichnung haben soll.
    """
    if text is None:
        return ''
    return _xml_escape(str(text))


def esc_rich(text):
    """Escaping für Felder, die absichtlich Tags (<b>…</b>) enthalten dürfen.

    Schützt nur 'nackte' Ampersands (die nicht Teil einer Entity wie
    &amp; oder &#160; sind), lässt gewollte Tags/Entities aber intakt.
    Für KI-Fließtext wie absatz_1…5 und kurzprofil.
    """
    if text is None:
        return ''
    return re.sub(r'&(?!#?\w+;)', '&amp;', str(text))
