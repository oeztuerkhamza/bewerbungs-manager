#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KI-Bewerbungsassistent – Claude API Integration
Liest Stellenanzeigen und erstellt maßgeschneiderte Bewerbungsunterlagen.
"""

import json
import re
import urllib.request
import urllib.error
from html.parser import HTMLParser

# ─── LEBENSLAUF-PROFIL (Basis) ───────────────────────────────────────────────
MEIN_PROFIL = """
HAMZA ÖZTÜRK – Fullstack Entwickler

KONTAKT:
Bissierstr. 16, 79114 Freiburg im Breisgau
+49 155 66859378 | oeztuerk.hamza@web.de
LinkedIn: linkedin.com/in/hamzaoeztuerk
GitHub: github.com/oeztuerkhamza
Geb.: 18.02.1996, Groß-Gerau

KURZPROFIL:
Nach einem beruflichen Neustart in Deutschland mit gezielter Weiterbildung
(Bootcamp, Sprachkurs, verkürzte Ausbildung) habe ich mich als
Full-Stack-Entwickler mit C#/.NET und Angular etabliert. Bei Dicom GmbH habe
ich SonarQube-Violations innerhalb von 3 Wochen von 2.100 auf 30 gesenkt,
CI/CD-Pipelines aufgebaut und eine Legacy-ERP-Anwendung auf Clean Architecture
migriert. Nebenbei betreibe ich eigene Open-Source-Projekte.

BERUFSERFAHRUNG:
Fachinformatiker für Anwendungsentwicklung (Softwareentwickler-Niveau)
Dicom GmbH, Freiburg im Breisgau | 02/2024 – 02/2026
• Full-Stack & Architektur: Feature-Entwicklung in C#/.NET (Backend) und
  Angular (Frontend); Migration monolithischer Desktop-Apps auf Clean Architecture.
• CI/CD & Code-Qualität: GitHub Actions-Pipelines aufgebaut – Deployment-Zeit
  40% schneller; SonarQube-Violations innerhalb von 3 Wochen von 2.100 auf 30.
• KI & API: RESTful APIs designed; KI-Tools und Prompt Engineering zur
  Code-Generierung und Fehleranalyse eingesetzt.

IT-KENNTNISSE:
Backend: C#, .NET Core, ASP.NET Core, Clean Architecture, EF Core, RESTful APIs, SQLite, SQL Server
Frontend: Angular (17/19), TypeScript, React 19, Tailwind CSS, NgRx, Infragistics
DevOps & Tools: Docker, GitHub Actions, Azure Pipelines, SonarQube/Cloud, Git, CI/CD, Netcup VPS
KI & Analytics: OpenAI API, Prompt Engineering, Python, SQL, Tableau, Web-Scraping

PROJEKTE:
1) Bikehaus Freiburg (bikehausfreiburg.com) – Live Produkt
   Digitale Warenwirtschaft: C#/.NET-API, Angular 17, Electron, Playwright, Chrome Extension MV3.
   Stack: C#/.NET, SQLite, EF Core, QuestPDF, Angular 17, Docker, Nginx.

2) Kulturplattform Freiburg e.V. (kulturplattformfreiburg.org) – Ehrenamtlich
   Vereinswebsite mit Admin-Panel, Newsletter, DE/TR-Zweisprachigkeit.
   .NET 10 Clean Architecture, React 19, Docker Compose.

3) DI-ONE – Enterprise Getränke-ERP (Dicom GmbH)
   .NET 9, Clean Architecture, 40+ API-Controller, OpenAI Assistants v2.
   Angular 19, NgRx, MSAL SSO. CI/CD: Azure Pipelines, SonarCloud.

4) DI-FLUX – Zeiterfassungssystem (IHK-Abschlussprojekt)
   Angular, C#/.NET, SQL Server, JWT-Authentifizierung.

AUSBILDUNG:
• 09/2024 – 12/2025: Berufsschule Fachinformatiker, Walther-Rathenau-Gewerbeschule Freiburg
• 02/2023 – 12/2023: Sprachausbildung Deutsch, Deutsches Kolleg Stuttgart
• 05/2022 – 12/2022: Data Analytics & Visualization (260 Std.), Clarusway IT School
• 10/2019 – 08/2022: Wirtschaftsingenieurwesen, TU Istanbul (ITÜ)
• 08/2015 – 07/2018: Militärwissenschaften, Türkische Luftwaffenakademie Istanbul

SPRACHEN:
Türkisch: Muttersprache | Deutsch: B2 | Englisch: B2
"""


# ─── HTML TO TEXT ────────────────────────────────────────────────────────────
class _HTMLTextExtractor(HTMLParser):
    """Simple HTML-to-text converter."""
    def __init__(self):
        super().__init__()
        self._pieces = []
        self._skip = False
        self._skip_tags = {'script', 'style', 'noscript', 'svg', 'path'}

    def handle_starttag(self, tag, attrs):
        if tag in self._skip_tags:
            self._skip = True
        if tag in ('br', 'p', 'div', 'li', 'tr', 'h1', 'h2', 'h3', 'h4'):
            self._pieces.append('\n')

    def handle_endtag(self, tag):
        if tag in self._skip_tags:
            self._skip = False

    def handle_data(self, data):
        if not self._skip:
            self._pieces.append(data)

    def get_text(self):
        raw = ''.join(self._pieces)
        # collapse whitespace
        lines = [' '.join(l.split()) for l in raw.splitlines()]
        text = '\n'.join(l for l in lines if l)
        # truncate very long pages
        if len(text) > 12000:
            text = text[:12000] + '\n[... gekürzt ...]'
        return text


def fetch_job_text(url):
    """Fetch a URL and extract visible text. Returns the text."""
    req = urllib.request.Request(url, headers={
        'User-Agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                       'AppleWebKit/537.36 (KHTML, like Gecko) '
                       'Chrome/120.0.0.0 Safari/537.36'),
        'Accept': 'text/html,application/xhtml+xml',
        'Accept-Language': 'de-DE,de;q=0.9,en;q=0.5',
    })
    resp = urllib.request.urlopen(req, timeout=15)
    html = resp.read().decode(resp.headers.get_content_charset() or 'utf-8',
                              errors='replace')
    parser = _HTMLTextExtractor()
    parser.feed(html)
    return parser.get_text()


# ─── CLAUDE API ──────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """\
Du bist ein professioneller deutscher Bewerbungsberater und Karrierecoach.

DEIN AUFTRAG:
Du erhältst:
1. Das vollständige Profil / den Lebenslauf des Bewerbers (Hamza Öztürk).
2. Eine Stellenanzeige (als Text oder URL-Inhalt).

Du musst daraus ein JSON-Objekt generieren, das ALLE folgenden Felder enthält.
Die Texte sollen in professionellem Deutsch verfasst sein.

WICHTIG – Lebenslauf-Anpassung:
- Die Stelle-Bezeichnung und Technologie-Schwerpunkte sollen zur Stellenanzeige passen.
- Das Kurzprofil (stelle, stelle_detail) soll auf die Anforderungen der Stelle zugeschnitten sein.
- Verwende NUR Fähigkeiten und Erfahrungen, die der Bewerber TATSÄCHLICH HAT (siehe Profil).
- Erfinde KEINE neuen Erfahrungen oder Technologien. Betone stattdessen die
  relevanten vorhandenen Fähigkeiten stärker.
- Der Bewerber ist C#/.NET-Entwickler, NICHT Java-Entwickler.
  Verwende NIEMALS Java, JavaEE, Spring Boot oder ähnliche Java-Technologien
  in stelle_detail oder im Text. Verwende stattdessen immer C#, .NET, ASP.NET Core etc.
- Wenn die Stellenanzeige Java verlangt, betone die Parallelen zu C#/.NET
  (z.B. "C#/.NET als stark vergleichbare Plattform zu Java/.NET").
- WICHTIG für stelle_detail: Verwende NUR Technologien aus dem Profil des Bewerbers
  (C#, .NET Core, ASP.NET Core, Angular, TypeScript, React, Docker, SQL Server, etc.).
  Füge KEINE branchenspezifischen Begriffe wie "Logistics Software", "E-Commerce",
  "Automotive" etc. in stelle_detail ein! Das sind keine Technologien.

WICHTIG – Anschreiben-Anpassung:
- Das Anschreiben soll sich auf die konkreten Anforderungen der Stelle beziehen.
- Verwende <b>HTML-Bold-Tags</b> für Hervorhebungen (wird für PDF-Rendering gebraucht).
- Jeder Absatz soll 3-5 Sätze lang sein.
- absatz_1: Einleitung – warum diese Stelle, welche Qualifikation.
- absatz_2: Berufserfahrung – konkrete Erfolge aus bisheriger Arbeit, relevant für die Stelle.
- absatz_3: Projekte – eigene Projekte die zur Stelle passen.
- absatz_4: Technologien & Arbeitsweise – passend zur Stellenanfrage.
- absatz_5: Schluss – Motivation, Gesprächswunsch.

WICHTIG – Bewerbungs-E-Mail:
- Generiere zusätzlich eine kurze, professionelle Bewerbungs-E-Mail (Plaintext, KEIN HTML).
- email_betreff: Die Betreff-Zeile der E-Mail.
- email_text: Der E-Mail-Text. Kurz (5-8 Sätze), höflich, professionell.
  Erwähne die Stelle, verweise auf die Anhänge (Lebenslauf & Anschreiben),
  und schließe mit freundlichen Grüßen.
  Verwende KEINE HTML-Tags. Am Ende immer:
  Mit freundlichen Grüßen
  Hamza Öztürk
  +49 155 66859378
  oeztuerk.hamza@web.de

RÜCKGABE – EXAKT dieses JSON-Schema (keine Markdown-Codeblöcke, nur roher JSON):
{
  "stelle": "...",
  "stelle_detail": "Tech1 | Tech2 | Tech3",
  "betreff": "Bewerbung als ... – ...",
  "firma": "Firmenname GmbH",
  "ansprechpartner": "Frau/Herrn Nachname",
  "firma_strasse": "Straße Nr",
  "firma_plz_ort": "PLZ Ort",
  "anrede": "Sehr geehrte Frau .../Sehr geehrter Herr .../Sehr geehrte Damen und Herren,",
  "absatz_1": "...",
  "absatz_2": "...",
  "absatz_3": "...",
  "absatz_4": "...",
  "absatz_5": "...",
  "anlagen": "Lebenslauf, Arbeitszeugnisse, Zertifikate",
  "email_betreff": "Bewerbung als ... – Hamza Öztürk",
  "email_text": "Sehr geehrte Damen und Herren,\n\n...\n\nMit freundlichen Grüßen\nHamza Öztürk\n+49 155 66859378\noeztuerk.hamza@web.de",
  "warnungen": ["Firma-Adresse nicht gefunden – bitte manuell ergänzen.", "..."]
}

WICHTIG – Warnungen:
- Das Feld "warnungen" ist ein Array von Strings.
- Füge eine Warnung hinzu, wenn:
  1) Die Firmen-Adresse nicht aus der Stellenanzeige ermittelt werden konnte
     (also Platzhalter wie "Musterstraße 1" oder "00000 Stadt" verwendet werden).
  2) Der Ansprechpartner nicht ermittelt werden konnte.
  3) Sonstige Unsicherheiten bestehen.
- Wenn alles klar ist, setze "warnungen" auf ein leeres Array [].
"""


def call_claude(api_key, job_text, extra_instructions=""):
    """Call Claude API and return the parsed config dict."""
    user_msg = (
        f"BEWERBER-PROFIL:\n{MEIN_PROFIL}\n\n"
        f"STELLENANZEIGE:\n{job_text}"
    )
    if extra_instructions.strip():
        user_msg += f"\n\nZUSÄTZLICHE HINWEISE DES BEWERBERS:\n{extra_instructions}"

    body = json.dumps({
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 4096,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": user_msg}],
    }).encode('utf-8')

    req = urllib.request.Request(
        'https://api.anthropic.com/v1/messages',
        data=body,
        headers={
            'Content-Type': 'application/json',
            'x-api-key': api_key,
            'anthropic-version': '2023-06-01',
        },
        method='POST',
    )

    try:
        resp = urllib.request.urlopen(req, timeout=60)
    except urllib.error.HTTPError as e:
        err_body = e.read().decode('utf-8', errors='replace')
        raise RuntimeError(
            f'Claude API Fehler {e.code}: {err_body}'
        ) from e

    data = json.loads(resp.read().decode('utf-8'))

    # Extract text content
    text = ''
    for block in data.get('content', []):
        if block.get('type') == 'text':
            text += block['text']

    # Parse JSON from response (strip potential markdown fences)
    text = text.strip()
    if text.startswith('```'):
        text = re.sub(r'^```\w*\n?', '', text)
        text = re.sub(r'\n?```$', '', text)
        text = text.strip()

    try:
        cfg = json.loads(text)
    except json.JSONDecodeError as e:
        raise RuntimeError(
            f'Claude-Antwort ist kein gültiges JSON:\n{text[:500]}'
        ) from e

    return cfg
