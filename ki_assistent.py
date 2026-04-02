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
import urllib.parse
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
Ich liefere als Full-Stack-Entwickler messbare Ergebnisse mit C#/.NET und
Angular. Mit gezielter Weiterbildung (Bootcamp, Sprachkurs, verkürzte
Ausbildung) und praktischer Projektarbeit habe ich mein Profil geschärft. Bei
Dicom GmbH habe
ich SonarQube-Violations innerhalb von 3 Wochen um ~99 % (2.100 → 30) gesenkt,
CI/CD-Pipelines aufgebaut und eine Legacy-ERP-Anwendung auf Clean Architecture
migriert. Nebenbei betreibe ich eigene Open-Source-Projekte.

BERUFSERFAHRUNG:
Fachinformatiker für Anwendungsentwicklung (Softwareentwickler-Niveau)
Dicom GmbH, Freiburg im Breisgau | 02/2024 – 02/2026
• Full-Stack & Architektur: Feature-Entwicklung in C#/.NET (Backend) und
  Angular (Frontend); Migration monolithischer Desktop-Apps auf Clean Architecture.
• CI/CD & Code-Qualität: GitHub Actions-Pipelines aufgebaut – Deployment-Zeit
  40% schneller; SonarQube-Violations innerhalb von 3 Wochen um ~99 % (2.100 → 30).
• KI & API: RESTful APIs designed; KI-Tools und Prompt Engineering zur
  Code-Generierung und Fehleranalyse eingesetzt.

IT-KENNTNISSE:
Backend: C#, .NET Core, ASP.NET Core, Clean Architecture, EF Core, RESTful APIs, SQLite, SQL Server
Frontend: Angular (17/19), TypeScript, React 19, Tailwind CSS, NgRx, Infragistics
DevOps & Tools: Docker, GitHub Actions, Azure Pipelines, SonarQube/Cloud, Git, CI/CD, Netcup VPS
KI & Analytics: OpenAI API, Prompt Engineering, Python, SQL, Tableau, Web-Scraping

PROJEKTE:
1) Bikehaus Freiburg (bikehausfreiburg.com) – Live Produkt
   Digitale Warenwirtschaft: 
    selbstentwickelte ERP-Software mit C#/.NET Backend, Angular Frontend, SQLite DB.
   Stack: C#/.NET, SQLite, EF Core, QuestPDF, Angular 19, Docker, Nginx.

2) Kulturplattform Freiburg e.V. (kulturplattformfreiburg.org) – Ehrenamtlich
   Vereinswebsite mit Admin-Panel, Newsletter, DE/TR-Zweisprachigkeit.
   .NET 10 Clean Architecture, React 19, Docker Compose.

3) DI-ONE – Enterprise Getränke-ERP (Dicom GmbH)
   .NET 9, Clean Architecture, 40+ API-Controller, OpenAI Assistants v2.
   Angular 19, NgRx. CI/CD: Azure Pipelines, SonarCloud.

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


def _is_placeholder_address(value):
    v = (value or '').strip().lower()
    if not v:
        return True
    placeholders = [
        'musterstraße', 'musterstrasse', 'straße nr', 'strasse nr',
        'plz ort', '00000', 'stadt', 'unknown', 'n/a'
    ]
    return any(p in v for p in placeholders)


def _extract_address_from_job_text(job_text):
    """Try to extract address lines directly from job text."""
    text = (job_text or '').replace('\r', '\n')

    street_match = re.search(
        r'([A-ZÄÖÜ][\wÄÖÜäöüß\-./ ]{2,}'
        r'(?:straße|strasse|weg|platz|allee|ring|gasse|ufer|damm|chaussee)\s+\d+[a-zA-Z]?)',
        text,
        flags=re.IGNORECASE,
    )
    plz_match = re.search(
        r'(\d{5}\s+[A-ZÄÖÜ][A-Za-zÄÖÜäöüß\- ]{2,})',
        text,
    )

    street = street_match.group(1).strip() if street_match else ''
    plz_ort = plz_match.group(1).strip() if plz_match else ''
    return street, plz_ort


def _lookup_company_address(company, city_hint=''):
    """Lookup company address via Nominatim (OpenStreetMap)."""
    company = (company or '').strip()
    if not company:
        return '', ''

    query = f'{company} {city_hint} Deutschland'.strip()
    url = (
        'https://nominatim.openstreetmap.org/search?format=jsonv2&limit=1&q='
        + urllib.parse.quote_plus(query)
    )
    req = urllib.request.Request(url, headers={
        'User-Agent': 'BewerbungsManager/1.0 (address lookup)'
    })

    try:
        resp = urllib.request.urlopen(req, timeout=12)
        data = json.loads(resp.read().decode('utf-8', errors='replace'))
    except Exception:
        return '', ''

    if not data:
        return '', ''

    addr = data[0].get('address', {})
    road = (addr.get('road') or addr.get('pedestrian') or '').strip()
    number = (addr.get('house_number') or '').strip()
    postcode = (addr.get('postcode') or '').strip()
    city = (addr.get('city') or addr.get('town') or addr.get('village') or '').strip()

    street = f'{road} {number}'.strip() if road else ''
    plz_ort = f'{postcode} {city}'.strip() if (postcode or city) else ''
    return street, plz_ort


def _autofill_missing_company_address(cfg, job_text):
    """Fill missing company address from job text, then web lookup fallback."""
    firma = (cfg.get('firma') or '').strip()
    strasse = (cfg.get('firma_strasse') or '').strip()
    plz_ort = (cfg.get('firma_plz_ort') or '').strip()

    needs_street = _is_placeholder_address(strasse)
    needs_plz = _is_placeholder_address(plz_ort)
    if not (needs_street or needs_plz):
        return cfg

    jt_street, jt_plz_ort = _extract_address_from_job_text(job_text)
    if needs_street and jt_street:
        cfg['firma_strasse'] = jt_street
    if needs_plz and jt_plz_ort:
        cfg['firma_plz_ort'] = jt_plz_ort

    # Fallback: web research if still incomplete
    strasse = (cfg.get('firma_strasse') or '').strip()
    plz_ort = (cfg.get('firma_plz_ort') or '').strip()
    needs_street = _is_placeholder_address(strasse)
    needs_plz = _is_placeholder_address(plz_ort)
    if needs_street or needs_plz:
        city_hint = ''
        m = re.search(r'(\d{5}\s+[^\n,]+)', job_text or '')
        if m:
            city_hint = m.group(1)
        wb_street, wb_plz_ort = _lookup_company_address(firma, city_hint)
        if needs_street and wb_street:
            cfg['firma_strasse'] = wb_street
        if needs_plz and wb_plz_ort:
            cfg['firma_plz_ort'] = wb_plz_ort

    # Keep warnings in sync after autofill
    warnungen = cfg.get('warnungen', [])
    if not isinstance(warnungen, list):
        warnungen = [str(warnungen)]

    final_street = (cfg.get('firma_strasse') or '').strip()
    final_plz_ort = (cfg.get('firma_plz_ort') or '').strip()
    still_missing = _is_placeholder_address(final_street) or _is_placeholder_address(final_plz_ort)

    if still_missing:
        if not any('Firma-Adresse' in w for w in warnungen):
            warnungen.append('Firma-Adresse nicht gefunden – bitte manuell ergänzen.')
    else:
        warnungen = [w for w in warnungen if 'Firma-Adresse' not in w]

    cfg['warnungen'] = warnungen
    return cfg


def _extract_json_candidate(text):
    """Extract the first balanced JSON object from arbitrary text."""
    s = (text or '').strip()
    if not s:
        return ''

    if s.startswith('```'):
        s = re.sub(r'^```\w*\n?', '', s)
        s = re.sub(r'\n?```$', '', s)
        s = s.strip()

    # Fast path: already a raw JSON object
    if s.startswith('{') and s.endswith('}'):
        return s

    start = s.find('{')
    if start == -1:
        return ''

    depth = 0
    in_str = False
    escape = False
    for i, ch in enumerate(s[start:], start=start):
        if in_str:
            if escape:
                escape = False
            elif ch == '\\':
                escape = True
            elif ch == '"':
                in_str = False
            continue

        if ch == '"':
            in_str = True
        elif ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                return s[start:i + 1]

    return ''


def _parse_claude_json(text):
    """Parse Claude response and tolerate wrappers around JSON."""
    candidate = _extract_json_candidate(text)
    if not candidate:
        raise json.JSONDecodeError('No JSON object found in response', text or '', 0)
    return json.loads(candidate)


def _request_claude(api_key, system_prompt, user_msg, max_tokens=8192):
    body = json.dumps({
        "model": "claude-sonnet-4-20250514",
        "max_tokens": max_tokens,
        "system": system_prompt,
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
        resp = urllib.request.urlopen(req, timeout=90)
    except urllib.error.HTTPError as e:
        err_body = e.read().decode('utf-8', errors='replace')
        raise RuntimeError(f'Claude API Fehler {e.code}: {err_body}') from e

    data = json.loads(resp.read().decode('utf-8'))
    text = ''
    for block in data.get('content', []):
        if block.get('type') == 'text':
            text += block.get('text', '')
    return text.strip()


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
- Das Kurzprofil (stelle) soll auf die Anforderungen der Stelle zugeschnitten sein.
- Verwende NUR Fähigkeiten und Erfahrungen, die der Bewerber TATSÄCHLICH HAT (siehe Profil).
- Erfinde KEINE neuen Erfahrungen oder Technologien. Betone stattdessen die
  relevanten vorhandenen Fähigkeiten stärker.
- Der Bewerber ist C#/.NET-Entwickler, NICHT Java-Entwickler.
  Verwende NIEMALS Java, JavaEE, Spring Boot oder ähnliche Java-Technologien
    im Text. Verwende stattdessen immer C#, .NET, ASP.NET Core etc.
- Wenn die Stellenanzeige Java verlangt, betone die Parallelen zu C#/.NET
  (z.B. "C#/.NET als stark vergleichbare Plattform zu Java/.NET").

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
  "anlagen": "'Anschreiben, Lebenslauf, Arbeitszeugnis,  Zeugnisse, Zertifikate'",
  "email_betreff": "Bewerbung als ...",
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

    # 1) First try
    text = _request_claude(api_key, SYSTEM_PROMPT, user_msg, max_tokens=8192)
    try:
        cfg = _parse_claude_json(text)
    except json.JSONDecodeError:
        # 2) One strict retry when response is malformed/truncated
        retry_msg = (
            user_msg
            + '\n\nWICHTIGER RETRY: Deine letzte Antwort war kein gültiges JSON. '
              'Antworte jetzt ausschließlich mit einem vollständigen, '
              'valide parsebaren JSON-Objekt gemäß Schema. Kein Fließtext.'
        )
        text_retry = _request_claude(api_key, SYSTEM_PROMPT, retry_msg, max_tokens=8192)
        try:
            cfg = _parse_claude_json(text_retry)
        except json.JSONDecodeError as e:
            preview = (text_retry or text)[:700]
            raise RuntimeError(
                'Claude-Antwort ist kein gültiges JSON (auch nach Retry).\n'
                f'Vorschau:\n{preview}'
            ) from e

    cfg = _autofill_missing_company_address(cfg, job_text)
    return cfg
