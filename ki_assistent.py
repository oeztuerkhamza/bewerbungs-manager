#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KI-Bewerbungsassistent – Claude API Integration
Liest Stellenanzeigen und erstellt maßgeschneiderte Bewerbungsunterlagen.
"""

import json
import re
import time
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
migriert. Seit 03/2026 verantworte ich in Festanstellung bei Bike Haus
Freiburg eine produktiv genutzte Warenwirtschafts- und Vermietungsplattform
(.NET 10 / Angular 22).

BERUFSERFAHRUNG:
Full-Stack Entwickler (Festanstellung)
Bike Haus Freiburg | 03/2026 – heute
• Eigene Warenwirtschafts- und Vermietungsplattform (.NET 10, Angular 22, SSR):
  40 Controller, 46 Domain-Entities, 130+ EF-Core-Migrationen, produktiv im Einsatz.
• Vermietung und Warenwirtschaft papierlos: 405 Mietverträge mit 35.000 €
  Mietumsatz, 696 Ankäufe,
  990 Verkäufe – über 2.000 Belege digital erzeugt (2026).
• SEO der SSR-Homepage (12 Sprachen mit hreflang, Prerendering, IndexNow):
  342.000 Impressionen und 13.000 Klicks in 6 Monaten (CTR 3,8 %, Ø-Position 9).
• DevOps: 6-Container-Docker-Stack auf eigenem VPS, GitHub Actions CI/CD mit
  Zero-Downtime-Deployment, Nginx, Mailcow-Mailserver (DKIM/SPF/DMARC).

Fachinformatiker für Anwendungsentwicklung (verkürzte duale Ausbildung, IHK)
Dicom GmbH, Freiburg im Breisgau | 02/2024 – 02/2026
• Fachlichkeit: ERP für den Getränke-Großhandel (DI-ONE) über die gesamte
  Prozesskette – Stammdaten, Artikelverwaltung, Einkauf, Verkauf und
  Leergut-/Pfandabwicklung; von der Anforderungsanalyse bis zum Rollout.
• Full-Stack & Architektur: Feature-Entwicklung in C#/.NET (Backend) und
  Angular (Frontend); Migration monolithischer Desktop-Apps auf Clean Architecture.
• CI/CD & Code-Qualität: GitHub Actions-Pipelines aufgebaut – Deployment-Zeit
  40% schneller; SonarQube-Violations innerhalb von 3 Wochen um ~99 % (2.100 → 30).
• KI & API: RESTful APIs designed; KI-Tools und Prompt Engineering zur
  Code-Generierung und Fehleranalyse eingesetzt.

IT-KENNTNISSE:
Backend: C#, .NET Core, ASP.NET Core, Clean Architecture, EF Core, RESTful APIs, SQLite, SQL Server
Frontend: Angular (19–22), TypeScript, React 19, Tailwind CSS, NgRx, Infragistics
DevOps & Tools: Docker, GitHub Actions, Azure Pipelines, SonarQube/Cloud, Git, CI/CD, Netcup VPS
KI & Analytics: OpenAI API, Prompt Engineering, Python, SQL, Tableau, Web-Scraping

PROJEKTE:
1) Zerin Gold (zerin-gold.de) – freiberuflich, Live
   Next.js 16, TypeScript, PostgreSQL 16/Prisma 7, Redis, Auth.js v5 (Argon2 + 2FA).
   7-sprachig inkl. RTL, White-Label-Architektur, Live-Goldpreis-Engine.

2) Kulturplattform Freiburg e.V. (kulturplattformfreiburg.org) – ehrenamtliche Arbeit
   Vereinswebsite mit Admin-Panel, Newsletter, DE/TR-Zweisprachigkeit.
   .NET 10 Clean Architecture, React 19, Docker Compose.

3) DI-ONE – Enterprise Getränke-ERP (Dicom GmbH)
   .NET 9, Clean Architecture, 40+ API-Controller, OpenAI Assistants v2.
   Angular 19, NgRx. CI/CD: Azure Pipelines, SonarCloud.

4) DI-FLUX – Zeiterfassungssystem (IHK-Abschlussprojekt)
   Angular, C#/.NET, SQL Server, JWT-Authentifizierung.

AUSBILDUNG:
• 02/2024 – 02/2026: Fachinformatiker für Anwendungsentwicklung (IHK),
  verkürzte duale Ausbildung – Walther-Rathenau-Gewerbeschule Freiburg,
  Ausbildungsbetrieb Dicom GmbH
• 02/2023 – 12/2023: Deutsch-Sprachausbildung bis C1, Deutschkolleg Stuttgart
• 05/2022 – 03/2023: Data Analytics & Visualization (260 Std.), Clarusway IT School
• 10/2019 – 08/2022: Wirtschaftsingenieurwesen, TU Istanbul (İTÜ) – ohne Abschluss
• 08/2015 – 07/2019: Militärwissenschaften – ohne Abschluss,
  Türkische Luftwaffenakademie Istanbul
• 2010 – 2015: Schulabschluss (Lise), Işıklar Militärgymnasium der Luftwaffe, Bursa

SPRACHEN:
Türkisch: Muttersprache | Deutsch: C1 (verhandlungssicher) | Englisch: B2

SONSTIGES:
Führerschein Klasse B | Aufenthalts- und Arbeitserlaubnis vorhanden
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
        "model": "claude-sonnet-4-6",
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

    # Bis zu 3 Versuche mit Backoff bei Rate-Limit/Overload/Netzwerkfehlern.
    raw = None
    max_attempts = 3
    for attempt in range(max_attempts):
        last = attempt == max_attempts - 1
        try:
            resp = urllib.request.urlopen(req, timeout=90)
            raw = resp.read().decode('utf-8', errors='replace')
            break
        except urllib.error.HTTPError as e:
            err_body = e.read().decode('utf-8', errors='replace')
            # 429 = Rate-Limit, 529 = überlastet, 5xx = transienter Serverfehler
            if e.code in (429, 500, 502, 503, 529) and not last:
                time.sleep(2 * (attempt + 1))
                continue
            raise RuntimeError(f'Claude API Fehler {e.code}: {err_body}') from e
        except urllib.error.URLError as e:
            # DNS/offline/Timeout – einige Male erneut versuchen
            if not last:
                time.sleep(2 * (attempt + 1))
                continue
            raise RuntimeError(
                f'Netzwerkfehler bei der Claude API: {e.reason}. '
                'Bitte Internetverbindung prüfen.') from e

    if raw is None:
        raise RuntimeError('Claude API: keine Antwort nach mehreren Versuchen.')

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise RuntimeError(
            f'Claude API: Antwort ist kein gültiges JSON: {raw[:300]}') from e

    if isinstance(data, dict) and data.get('type') == 'error':
        msg = (data.get('error') or {}).get('message', 'Unbekannter Fehler')
        raise RuntimeError(f'Claude API Fehler: {msg}')

    text = ''
    for block in data.get('content', []):
        if block.get('type') == 'text':
            text += block.get('text', '')

    if data.get('stop_reason') == 'max_tokens':
        raise RuntimeError(
            'Claude-Antwort wurde abgeschnitten (max_tokens erreicht). '
            'Bitte den Stellentext kürzen und erneut versuchen.')

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

WICHTIG – ZUERST: ROLLEN-FOKUS BESTIMMEN
- Analysiere die Stellenanzeige und bestimme den ECHTEN Schwerpunkt der Stelle.
  Das ist NICHT automatisch Softwareentwicklung. Mögliche Schwerpunkte z.B.:
  * Softwareentwicklung / Programmierung
  * IT-Koordination / IT-Administration / Systembetreuung / Anwender-Support
  * Digitalisierung / IT-Projektmanagement / Prozessoptimierung
  * Schul-IT / Medienkonzepte / Anwenderschulung
- Richte ALLE Texte (stelle, kurzprofil, betreff, alle Anschreiben-Absätze,
  highlights, E-Mail) an DIESEM Fokus aus. Beispiel: Ist die Stelle
  "IT-Koordination & Digitalisierung", erzeuge KEINE reine Entwickler-Bewerbung,
  sondern stelle die dazu passenden Kompetenzen des Bewerbers in den Vordergrund.
  Reine Programmier-Details werden dann nur als ergänzende technische Tiefe erwähnt.

DER BEWERBER bringt mit (je nach Rollen-Fokus unterschiedlich gewichten):
- Ausgebildeter Fachinformatiker für Anwendungsentwicklung (IHK).
- Digitalisierung & Prozessoptimierung: vollständige Digitalisierung/Modernisierung
  von Geschäftsprozessen (ERP von Desktop- zu Web-Lösung).
- IT-Infrastruktur & Systembetreuung: Azure Cloud, Docker, Linux-Server (VPS),
  Nginx, Backups, E-Mail-Server, CI/CD, Netzwerk-/IT-Sicherheitsthemen.
- Anwender-Support, Fehleranalyse und Wartung produktiver Systeme.
- Eigenständige End-to-End-Projektkoordination (Anforderung bis Rollout).
- Wissensvermittlung: Bootcamp, Berufsschule, Einarbeitung; mehrsprachig (TR/DE/EN).
- Softwareentwicklung: C#/.NET, Angular, Datenbanken (als technische Tiefe).

WICHTIG – Lebenslauf-Anpassung (Feld "kurzprofil"):
- 4–6 Sätze, professionelles Deutsch, Fließtext (KEINE Aufzählung).
- Stelle die zum ROLLEN-FOKUS passenden Kompetenzen nach vorne. Bei einer
  IT-Koordinations-/Digitalisierungsstelle also z.B. IT-Infrastruktur,
  Digitalisierung, Support, Projektkoordination und die Fachinformatiker-
  Qualifikation – Programmierung nur als ergänzende technische Stärke.
- <b>HTML-Bold-Tags</b> für die 3–4 wichtigsten Stichworte der Stelle.
- "stelle" = exakte Bezeichnung aus der Anzeige; "betreff" dazu passend
  (NICHT automatisch "C# / .NET / Angular").
- NUR wahrheitsgemäße Inhalte aus dem Profil; KEINE Fakten/Zahlen erfinden.

GRENZEN (immer gültig):
- Erfinde KEINE Erfahrungen oder Technologien; betone vorhandene stärker.
- Geht es konkret um PROGRAMMIERSPRACHEN: der Bewerber arbeitet mit C#/.NET,
  nicht mit Java. Verlangt die Stelle Java, nenne C#/.NET als stark vergleichbare
  Plattform – erfinde aber keine Java-Erfahrung.

STIL (immer gültig):
- Belege Aussagen mit konkreten Zahlen aus dem Profil statt mit Adjektiven.
  Verzichte auf Floskeln wie "teamfähig", "lernbereit", "hoch motiviert"
  oder "genau die Kombination, die Ihr Team weiterbringt".
- Bei der Digitalisierung immer beides betonen: Aufbau (Datenmodell, API,
  Frontend) und anschließender Betrieb (Docker, CI/CD, Server, Monitoring).

WICHTIG – Anschreiben-Anpassung:
- Beziehe dich konkret auf die Anforderungen der Stelle und den ROLLEN-FOKUS.
- Verwende <b>HTML-Bold-Tags</b> für Hervorhebungen. Jeder Absatz 3–5 Sätze.
- absatz_1: Einleitung – Bezug zur konkreten Stelle und passende Kernqualifikation
  (NICHT generisch "Fullstack Entwickler", sondern zum Rollen-Fokus passend).
- absatz_2: KURZER Überleitungssatz (1–2 Sätze), der die folgenden
  Erfolgs-Stichpunkte einleitet. KEINE vollständige Aufzählung im Fließtext.
- highlights: 3–4 konkrete, WAHRE Erfolge des Bewerbers, ausgewählt passend zum
  Rollen-Fokus (z.B. Digitalisierung/Infrastruktur/Support statt nur Code-Metriken).
  Kurze Stichpunkte ohne Satzzeichen am Ende, KEINE erfundenen Zahlen.
- absatz_3: relevante eigene Projekte/Erfahrungen mit Bezug zur Stelle.
- absatz_4: Arbeitsweise & relevante Kompetenzen, passend zum Rollen-Fokus.
- absatz_5: Schluss – Motivation, Gesprächswunsch.

WICHTIG – Bewerbungs-E-Mail:
- Generiere zusätzlich eine kurze, professionelle Bewerbungs-E-Mail (Plaintext, KEIN HTML).
- email_betreff: Die Betreff-Zeile der E-Mail.
- email_text: Der E-Mail-Text. Kurz (5-8 Sätze), höflich, professionell.
  Erwähne die Stelle, verweise auf die Anhänge (Lebenslauf & Anschreiben),
  und schließe mit freundlichen Grüßen.
- Die E-Mail MUSS mindestens ein konkretes Ergebnis mit Zahl aus dem Profil
  nennen (z.B. papierlose Abwicklung von über 2.000 Belegen, 35.000 EUR
  Mietumsatz, Deployment-Zeit um 40 % reduziert). Eine E-Mail, die nur
  "ich bewerbe mich und freue mich auf Ihre Antwort" sagt, ist unbrauchbar.
- Stelle einen Bezug zur Firma her: was sie tut und wo dabei
  Digitalisierung oder Systembetrieb eine Rolle spielt.
  Verwende KEINE HTML-Tags. Am Ende immer:
  Mit freundlichen Grüßen
  Hamza Öztürk
  +49 155 66859378
  oeztuerk.hamza@web.de

RÜCKGABE – EXAKT dieses JSON-Schema (keine Markdown-Codeblöcke, nur roher JSON):
{
  "stelle": "...",
  "kurzprofil": "Auf die Stelle zugeschnittenes CV-Kurzprofil, 4–6 Sätze, mit <b>Bold</b>-Tags für die wichtigsten Technologien.",
  "betreff": "Bewerbung als ... – ...",
  "firma": "Firmenname GmbH",
  "ansprechpartner": "Frau/Herrn Nachname",
  "firma_strasse": "Straße Nr",
  "firma_plz_ort": "PLZ Ort",
  "anrede": "Sehr geehrte Frau .../Sehr geehrter Herr .../Sehr geehrte Damen und Herren,",
  "absatz_1": "...",
  "absatz_2": "Kurzer Überleitungssatz zu den Erfolgs-Stichpunkten.",
  "highlights": ["Erfolg 1", "Erfolg 2", "Erfolg 3"],
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
