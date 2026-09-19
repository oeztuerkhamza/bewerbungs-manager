#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Initiativbewerbung – Firmen einer Region über OpenStreetMap (Overpass) finden
und personalisierte Initiativbewerbungs-E-Mails erstellen.

Ablauf:
1. Region (Stadt/PLZ) wird per Nominatim geokodiert.
2. Overpass liefert alle Firmen/Geschäfte im Umkreis, die eine öffentliche
   E-Mail-Adresse hinterlegt haben (Tag "email" bzw. "contact:email").
3. Optional wird per Claude ein Anschreiben-Text mit {firma}-Platzhalter erzeugt.

Es werden ausschließlich bereits öffentlich veröffentlichte Kontakt-E-Mails
verwendet. Der Nutzer wählt selbst aus, wer angeschrieben wird.
"""

import json
import math
import re
import time
import urllib.error
import urllib.parse
import urllib.request

import ki_assistent as ki  # _request_claude, MEIN_PROFIL

# ─── ENDPUNKTE ───────────────────────────────────────────────────────────────
_NOMINATIM_URL = 'https://nominatim.openstreetmap.org/search'
# Reihenfolge = Versuchsreihenfolge. maps.mail.ru ist im Benchmark bei großen
# Umkreisen deutlich schneller; overpass-api.de als offizieller Fallback.
_OVERPASS_URLS = [
    'https://maps.mail.ru/osm/tools/overpass/api/interpreter',
    'https://overpass-api.de/api/interpreter',
    'https://overpass.kumi.systems/api/interpreter',
]
_USER_AGENT = 'BewerbungsManager/1.0 (Initiativbewerbung; company lookup)'

_EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')

# ─── DEUTSCHLAND-FILTER ──────────────────────────────────────────────────────
# Overpass-Gebiet "Bundesrepublik Deutschland". Wird jeder Abfrage vorangestellt,
# damit z.B. bei Freiburg keine französischen/schweizer Firmen mitkommen.
_GERMANY_AREA = 'area["ISO3166-1"="DE"][admin_level=2]->.de;'

# Länderkennungen der Nachbarländer – E-Mails darauf sind keine deutschen Firmen.
_FOREIGN_TLDS = {
    'fr', 'ch', 'at', 'it', 'nl', 'be', 'lu', 'pl', 'cz', 'dk',
    'li', 'es', 'pt', 'uk', 'se', 'no', 'fi', 'hu', 'sk', 'si', 'hr',
}


def _is_german(tags, email):
    """True, wenn die Firma als deutsch gelten kann.

    Zweite Sicherung zusätzlich zum Overpass-Gebietsfilter: explizit als
    ausländisch getaggte Objekte und E-Mail-Domains mit fremder Länderendung
    werden aussortiert. Neutrale Endungen (.de, .com, .eu, .net ...) bleiben.
    """
    country = (tags.get('addr:country') or '').strip().upper()
    if country and country != 'DE':
        return False
    tld = email.rsplit('.', 1)[-1].lower()
    return tld not in _FOREIGN_TLDS


# ─── KATEGORIEN ──────────────────────────────────────────────────────────────
# Gefiltert wird nach dem Suchlauf in Python über die OSM-Tags. So bleibt die
# Overpass-Abfrage simpel und robust.
_ALL_KEYS = ['office', 'shop', 'craft', 'industrial', 'amenity',
             'company', 'name', 'operator', 'description']


def _tag_text(tags, keys):
    return ' '.join(str(tags.get(k, '')) for k in keys).lower()


# Kurze/mehrdeutige Tokens (it, edv, web, data) nur als ganzes Wort matchen,
# damit "Arbeit"/"Kita" nicht fälschlich als IT-Firma gelten. Längere Tokens
# matchen auch als Wortanfang (z.B. "Softwarehaus").
_IT_RE = re.compile(
    r'\b(it|edv|web|data|iot)\b'
    r'|(software|computer|informatik|digital|medien|media|telekom|telecom'
    r'|systemhaus|programm|internet|cloud|hosting|netzwerk|elektronik)',
    re.IGNORECASE)
_BUERO_RE = re.compile(
    r'(büro|buero|verwaltung|consulting|beratung|agentur|kanzlei|versicherung'
    r'|steuer|immobilien|dienstleist|makler|marketing|personal)',
    re.IGNORECASE)

CATEGORY_ORDER = [
    'Alle Firmen (mit E-Mail)',
    'IT / Software / EDV',
    'Büro / Dienstleistung / Verwaltung',
    'Handel / Geschäfte',
    'Handwerk / Industrie / Gewerbe',
]


def _category_match(tags, category):
    if category == 'IT / Software / EDV':
        return bool(_IT_RE.search(_tag_text(tags, _ALL_KEYS)))
    if category == 'Büro / Dienstleistung / Verwaltung':
        return (
            'office' in tags
            or tags.get('amenity') in {
                'coworking_space', 'company', 'bureau_de_change'}
            or bool(_BUERO_RE.search(_tag_text(tags, _ALL_KEYS))))
    if category == 'Handel / Geschäfte':
        return 'shop' in tags
    if category == 'Handwerk / Industrie / Gewerbe':
        return (
            'craft' in tags
            or 'industrial' in tags
            or tags.get('landuse') == 'industrial'
            or tags.get('building') in {'industrial', 'warehouse'})
    return True  # "Alle Firmen (mit E-Mail)"


# ─── GEOCODING ───────────────────────────────────────────────────────────────
def geocode(region):
    """Region (Stadt/PLZ) → (lat, lon, anzeigename). Wirft bei Misserfolg."""
    region = (region or '').strip()
    if not region:
        raise ValueError('Bitte eine Region / Stadt angeben.')

    query = region
    if 'deutschland' not in region.lower() and 'germany' not in region.lower():
        query = f'{region}, Deutschland'

    url = _NOMINATIM_URL + '?' + urllib.parse.urlencode({
        'format': 'jsonv2', 'limit': '1', 'q': query,
    })
    req = urllib.request.Request(url, headers={'User-Agent': _USER_AGENT})
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        data = json.loads(resp.read().decode('utf-8', errors='replace'))
    except Exception as exc:
        raise RuntimeError(f'Geokodierung fehlgeschlagen: {exc}') from exc

    if not data:
        raise RuntimeError(
            f'Region "{region}" nicht gefunden. Bitte anders schreiben '
            '(z.B. "Freiburg im Breisgau").')

    lat = float(data[0]['lat'])
    lon = float(data[0]['lon'])
    name = data[0].get('display_name', region)
    return lat, lon, name


# ─── GEOMETRIE ───────────────────────────────────────────────────────────────
def _bbox(lat, lon, radius_km):
    """Bounding-Box (Süd, West, Nord, Ost) um einen Mittelpunkt."""
    dlat = radius_km / 111.32
    dlon = radius_km / (111.32 * max(0.01, math.cos(math.radians(lat))))
    return (lat - dlat, lon - dlon, lat + dlat, lon + dlon)


def circle_points(lat, lon, radius_km, n=72):
    """Punkte (lat, lon) eines Kreises um einen Mittelpunkt – für Kartenanzeige.

    Nähert den Umkreis (wie in Kleinanzeigen) als n-eckiges Polygon an.
    """
    dlat = radius_km / 111.32
    dlon = radius_km / (111.32 * max(0.01, math.cos(math.radians(lat))))
    pts = []
    for i in range(n):
        ang = 2 * math.pi * i / n
        pts.append((lat + dlat * math.cos(ang), lon + dlon * math.sin(ang)))
    return pts


def _haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = (math.sin(dp / 2) ** 2
         + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2)
    return 2 * r * math.asin(math.sqrt(a))


def _element_latlon(el):
    if 'lat' in el and 'lon' in el:
        return el['lat'], el['lon']
    center = el.get('center')
    if center:
        return center.get('lat'), center.get('lon')
    return None, None


# ─── OVERPASS ────────────────────────────────────────────────────────────────
# Nur "arbeitgeber-typische" OSM-Keys abfragen (statt aller E-Mail-Objekte).
# Das ist per Bounding-Box um ein Vielfaches schneller und liefert vollständige
# Ergebnisse, ohne an ein Ergebnis-Limit zu stoßen.
_EMPLOYER_KEYS = ['office', 'shop', 'craft', 'industrial', 'healthcare']


def _build_overpass_query(bbox):
    south, west, north, east = bbox
    box = f'{south:.5f},{west:.5f},{north:.5f},{east:.5f}'
    parts = []
    for key in _EMPLOYER_KEYS:
        # (area.de) begrenzt das Ergebnis auf deutsches Staatsgebiet.
        parts.append(f'nwr["{key}"]["email"](area.de)({box});')
        parts.append(f'nwr["{key}"]["contact:email"](area.de)({box});')
    return (
        '[out:json][timeout:180];'
        + _GERMANY_AREA +
        '(' + ''.join(parts) + ');'
        'out center tags 20000;'
    )


def _overpass_request(query, timeout=180):
    body = urllib.parse.urlencode({'data': query}).encode('utf-8')
    last_err = None
    for endpoint in _OVERPASS_URLS:
        req = urllib.request.Request(
            endpoint, data=body,
            headers={'User-Agent': _USER_AGENT,
                     'Content-Type': 'application/x-www-form-urlencoded'},
            method='POST')
        try:
            resp = urllib.request.urlopen(req, timeout=timeout)
            raw = resp.read().decode('utf-8', errors='replace')
            data = json.loads(raw)
            # Overpass meldet Timeouts/Überlast mit HTTP 200 + "remark" und
            # leerer Ergebnisliste. Ohne diese Prüfung sähe das wie "nichts
            # gefunden" aus – stattdessen den nächsten Server versuchen.
            remark = str(data.get('remark') or '')
            if remark and 'error' in remark.lower():
                raise RuntimeError(f'Overpass-Server meldet: {remark}')
            return data
        except Exception as exc:  # nächsten Endpunkt versuchen
            last_err = exc
            time.sleep(1)
            continue
    raise RuntimeError(
        f'Overpass-Abfrage fehlgeschlagen (alle Server): {last_err}')


def _first_email(value):
    """OSM-E-Mail-Tags können mehrere Adressen (; oder ,) enthalten."""
    for part in re.split(r'[;,]', value or ''):
        part = part.strip()
        if part.lower().startswith('mailto:'):
            part = part[7:].strip()
        if _EMAIL_RE.match(part):
            return part.lower()
    return ''


def _element_to_company(el):
    tags = el.get('tags', {})
    email = _first_email(tags.get('email') or tags.get('contact:email'))
    if not email:
        return None

    name = (tags.get('name') or tags.get('operator')
            or tags.get('brand') or '').strip()
    if not name:
        # Firmenname aus der E-Mail-Domain ableiten
        domain = email.split('@')[-1].split('.')[0]
        name = domain.replace('-', ' ').replace('_', ' ').title()

    street = (tags.get('addr:street') or '').strip()
    housenr = (tags.get('addr:housenumber') or '').strip()
    strasse = f'{street} {housenr}'.strip()
    plz = (tags.get('addr:postcode') or '').strip()
    ort = (tags.get('addr:city') or tags.get('addr:town')
           or tags.get('addr:village') or '').strip()
    plz_ort = f'{plz} {ort}'.strip()
    website = (tags.get('website') or tags.get('contact:website') or '').strip()

    return {
        'firma': name,
        'email': email,
        'strasse': strasse,
        'plz_ort': plz_ort,
        'website': website,
        'tags': tags,
    }


def find_companies(region, radius_km=10, category='Alle Firmen (mit E-Mail)',
                   limit=100, log=None):
    """Firmen mit öffentlicher E-Mail im Umkreis der Region finden.

    Es werden ausschließlich Firmen in Deutschland zurückgegeben (wichtig z.B.
    im Grenzgebiet um Freiburg/Aachen/Passau). Gibt eine Liste von Dicts
    (firma, email, strasse, plz_ort, website) zurück, dedupliziert nach E-Mail.
    """
    def _log(msg):
        if log:
            log(msg)

    radius_km = float(radius_km)
    lat, lon, name = geocode(region)
    _log(f'📍 Region gefunden: {name}')
    _log(f'🔎 Suche Firmen im Umkreis von {radius_km:.0f} km '
         '(nur Deutschland) ...')

    if radius_km >= 60:
        _log('⏳ Großer Umkreis – die Abfrage kann 1–3 Minuten dauern ...')
    query = _build_overpass_query(_bbox(lat, lon, radius_km))
    data = _overpass_request(query)
    elements = data.get('elements', [])
    _log(f'↓ {len(elements)} Firmen-Objekte mit E-Mail empfangen.')

    companies = []
    seen = set()
    foreign = 0
    for el in elements:
        company = _element_to_company(el)
        if not company:
            continue
        # Bounding-Box ist ein Rechteck – auf den echten Radius (Kreis) kürzen.
        el_lat, el_lon = _element_latlon(el)
        if el_lat is not None:
            if _haversine_km(lat, lon, el_lat, el_lon) > radius_km:
                continue
        if not _is_german(company['tags'], company['email']):
            foreign += 1
            continue
        if not _category_match(company['tags'], category):
            continue
        key = company['email']
        if key in seen:
            continue
        seen.add(key)
        # Koordinaten für die Kartenanzeige behalten (können None sein).
        company['lat'] = el_lat
        company['lon'] = el_lon
        company.pop('tags', None)
        companies.append(company)

    if foreign:
        _log(f'🇩🇪 {foreign} Firma(en) außerhalb Deutschlands aussortiert.')
    companies.sort(key=lambda c: c['firma'].lower())
    if limit and len(companies) > limit:
        _log(f'ℹ {len(companies)} gefunden – auf {limit} begrenzt.')
        companies = companies[:limit]

    _log(f'✓ {len(companies)} anschreibbare Firmen (Kategorie: {category}).')
    return companies


# ─── FAHRRADFIRMEN IN GANZ DEUTSCHLAND ───────────────────────────────────────
_BIKE_NAME_RE = re.compile(
    r'(fahrrad|fahrräder|fahrraeder|bike|bicycle|zweirad|velo|cycl|radhaus'
    r'|radsport|radl|e-bike|ebike|pedelec)',
    re.IGNORECASE)

# Regex für die Overpass-Namenssuche (ohne Sonderzeichen-Fallstricke).
_BIKE_NAME_OSM = 'Fahrrad|Fahrräder|Bike|Bicycle|Zweirad|Velo|Cycl|Radsport|Pedelec'


def _bike_stage_query(parts, timeout=900):
    return ('[out:json][timeout:%d];' % timeout
            + _GERMANY_AREA
            + '(' + ''.join(parts) + ');'
            'out center tags 20000;')


def _bike_name_parts(key):
    return [
        f'nwr["{key}"]["name"~"{_BIKE_NAME_OSM}",i]["email"](area.de);',
        f'nwr["{key}"]["name"~"{_BIKE_NAME_OSM}",i]["contact:email"](area.de);',
    ]


# Eine einzige Gesamtabfrage über ganz Deutschland überlastet Overpass (HTTP
# 500 bzw. "Query timed out"). Deshalb kleine Einzelstufen – Stufe 1 liefert
# nach ~30 Sekunden bereits ~90 % der Firmen, die Namenssuche ergänzt den Rest.
# Gemessene Laufzeiten: Stufe 1 ~30 s, office/craft/industrial je ~100 s,
# shop ~280 s. Der Server-Timeout liegt deshalb großzügig bei 900 s.
_BIKE_STAGES = [
    ('Fahrradläden & -werkstätten', [
        'nwr["shop"="bicycle"]["email"](area.de);',
        'nwr["shop"="bicycle"]["contact:email"](area.de);',
        'nwr["craft"="bicycle"]["email"](area.de);',
        'nwr["craft"="bicycle"]["contact:email"](area.de);',
    ]),
    ('Büros mit Fahrrad-Namen', _bike_name_parts('office')),
    ('Handwerksbetriebe mit Fahrrad-Namen', _bike_name_parts('craft')),
    ('Industrie / Hersteller mit Fahrrad-Namen', _bike_name_parts('industrial')),
    ('Weitere Geschäfte mit Fahrrad-Namen', _bike_name_parts('shop')),
]


def find_bicycle_companies_germany(limit=0, log=None, on_partial=None):
    """Alle Fahrrad-Firmen (Läden, Werkstätten, Hersteller) in Deutschland.

    Sucht bundesweit nach Betrieben mit öffentlicher Kontakt-E-Mail, die als
    shop/craft=bicycle getaggt sind oder einen fahrradtypischen Namen tragen.
    Nach jeder Stufe wird ``on_partial(companies)`` mit dem bisherigen
    Zwischenstand aufgerufen, damit die Oberfläche früh etwas anzeigen kann.
    """
    def _log(msg):
        if log:
            log(msg)

    _log('🚲 Suche alle Fahrradfirmen in Deutschland ...')
    _log(f'⏳ Bundesweite Abfrage in {len(_BIKE_STAGES)} Stufen – insgesamt ca. '
         '10–15 Minuten. Erste Ergebnisse nach ca. 30 Sekunden.')

    companies = []
    seen = set()
    foreign = 0

    for nr, (titel, parts) in enumerate(_BIKE_STAGES, start=1):
        _log(f'▶ Stufe {nr}/{len(_BIKE_STAGES)}: {titel} ...')
        try:
            data = _overpass_request(_bike_stage_query(parts), timeout=900)
        except Exception as exc:
            # Eine überlastete Stufe darf das Gesamtergebnis nicht wegwerfen.
            _log(f'⚠ Stufe {nr} fehlgeschlagen ({exc}) – wird übersprungen.')
            continue
        elements = data.get('elements', [])
        neu = 0
        for el in elements:
            company = _element_to_company(el)
            if not company:
                continue
            tags = company['tags']
            if not _is_german(tags, company['email']):
                foreign += 1
                continue
            # Namens-Treffer gegenprüfen (Overpass-Regex ist großzügig), reine
            # shop/craft=bicycle-Objekte immer akzeptieren.
            if tags.get('shop') != 'bicycle' and tags.get('craft') != 'bicycle':
                if not _BIKE_NAME_RE.search(_tag_text(tags, _ALL_KEYS)):
                    continue
            key = company['email']
            if key in seen:
                continue
            seen.add(key)
            el_lat, el_lon = _element_latlon(el)
            company['lat'] = el_lat
            company['lon'] = el_lon
            company.pop('tags', None)
            companies.append(company)
            neu += 1
        _log(f'  ↳ {len(elements)} Objekte, {neu} neue Firmen '
             f'(gesamt: {len(companies)}).')
        if on_partial:
            on_partial(sorted(companies, key=lambda c: c['firma'].lower()))

    if foreign:
        _log(f'🇩🇪 {foreign} Treffer außerhalb Deutschlands aussortiert.')
    companies.sort(key=lambda c: c['firma'].lower())
    if limit and len(companies) > limit:
        _log(f'ℹ {len(companies)} gefunden – auf {limit} begrenzt.')
        companies = companies[:limit]

    _log(f'✓ {len(companies)} Fahrradfirmen mit E-Mail in Deutschland.')
    return companies


# ─── E-MAIL-TEXT ─────────────────────────────────────────────────────────────
DEFAULT_BETREFF = ('Initiativbewerbung – Softwareentwicklung & '
                   'Digitalisierung von Abläufen')

# {firma} wird beim Versand durch den echten Firmennamen ersetzt.
DEFAULT_TEXT = (
    'Sehr geehrte Damen und Herren,\n\n'
    'ich bin Fachinformatiker für Anwendungsentwicklung (IHK) und baue '
    'Software, die Geschäftsprozesse vom Papier in ein laufendes System '
    'überführt.\n\n'
    'Für einen Fahrradhändler in Freiburg habe ich eine eigene '
    'Warenwirtschafts- und Vermietungsplattform entwickelt und betreibe sie '
    'dort im Tagesgeschäft: Vermietung, Ankauf und Verkauf laufen vollständig '
    'digital. 2026 wurden darüber über 2.000 Belege erzeugt – Mietverträge '
    'mit QR-Code und digitaler Unterschrift, Kautionsabwicklung und '
    'automatischer Mailversand inklusive. Zuvor habe ich im Team ein '
    'ERP-System für den Getränke-Großhandel von einer Desktop-Anwendung in '
    'eine Web-Architektur überführt, über die gesamte Prozesskette von '
    'Stammdaten über Einkauf und Verkauf bis zur Leergut-Abwicklung.\n\n'
    'Bei {firma} interessiert mich genau diese Art Aufgabe: Abläufe '
    'verstehen, sie digitalisieren und das Ergebnis danach stabil betreiben. '
    'Technisch arbeite ich mit C#/.NET und Angular, dazu Docker, CI/CD und '
    'eigener Server-Infrastruktur; IT-Betreuung und Systemadministration '
    'gehören für mich dazu.\n\n'
    'Meinen Lebenslauf habe ich beigefügt. Über ein Gespräch, in dem ich '
    'Ihre Abläufe kennenlernen und zeigen kann, wo sich Digitalisierung bei '
    '{firma} am schnellsten auszahlt, würde ich mich freuen.\n\n'
    'Mit freundlichen Grüßen\n'
    'Hamza Öztürk\n'
    '+49 155 66859378\n'
    'hamza@hamzaoeztuerk.de'
)


_INITIATIV_SYSTEM_PROMPT = """\
Du bist ein professioneller deutscher Bewerbungscoach. Erstelle EINE
Initiativbewerbungs-E-Mail (Plaintext, KEIN HTML) für Hamza Öztürk, die an viele
verschiedene Firmen einer Region verschickt wird.

WICHTIG – Positionierung:
- Kern des Bewerbers ist die DIGITALISIERUNG VON GESCHÄFTSPROZESSEN: bestehende,
  oft papiergebundene Abläufe aufnehmen, als System bauen UND anschließend
  betreiben. Das gehört in den ersten Absatz, nicht die Technologieliste.
- Nenne mindestens ein konkretes Ergebnis mit Zahl aus dem Profil (z.B. über
  2.000 papierlos erzeugte Belege, 35.000 EUR Mietumsatz, ERP-Migration über
  die gesamte Prozesskette). Ohne eine solche Zahl ist die E-Mail unbrauchbar.
- IT-Betreuung und Systemadministration dürfen als Ergänzung vorkommen, aber
  NICHT als Hauptangebot. Schreibe nicht, der Bewerber sei "für jede
  computergestützte Tätigkeit offen", und biete keine "allgemeine Büro- und
  Verwaltungsarbeit" an – das widerspricht dem Lebenslauf und verkauft ihn
  unter Wert.
- Verzichte auf Floskeln ohne Beleg ("zuverlässig", "lernbereit", "teamfähig",
  "arbeite mich schnell ein"). Der Ton ist selbstbewusst, freundlich, seriös.
- Der Schluss soll etwas anbieten – die Abläufe der Firma kennenlernen und
  Ansatzpunkte für Digitalisierung zeigen – statt um eine Chance zu bitten.
- Der Firmenname ist noch nicht bekannt. Verwende an den passenden Stellen EXAKT
  den Platzhalter {firma} (mit geschweiften Klammern), der später automatisch
  durch den echten Firmennamen ersetzt wird. Der Platzhalter MUSS mindestens
  einmal vorkommen.
- Anrede immer "Sehr geehrte Damen und Herren,".
- 4 bis 6 Sätze im Hauptteil, danach Verweis auf den beigefügten Lebenslauf.
- Erfinde keine falschen Fakten.
- Beende die E-Mail IMMER mit:
  Mit freundlichen Grüßen
  Hamza Öztürk
  +49 155 66859378
  hamza@hamzaoeztuerk.de

RÜCKGABE – nur rohes JSON, kein Markdown:
{
  "betreff": "Initiativbewerbung – ...",
  "text": "Sehr geehrte Damen und Herren,\\n\\n... {firma} ...\\n\\nMit freundlichen Grüßen\\nHamza Öztürk\\n+49 155 66859378\\nhamza@hamzaoeztuerk.de"
}
"""


def generate_email_template(api_key, region='', extra=''):
    """Per Claude einen Initiativ-E-Mail-Text mit {firma}-Platzhalter erzeugen.

    Gibt {'betreff': ..., 'text': ...} zurück. Der Text enthält {firma}.
    """
    user_msg = f'BEWERBER-PROFIL:\n{ki.MEIN_PROFIL}\n\n'
    if region.strip():
        user_msg += f'ZIELREGION: {region}\n\n'
    user_msg += (
        'Erstelle jetzt die Initiativbewerbungs-E-Mail gemäß Vorgaben. '
        'Denke an den {firma}-Platzhalter.')
    if extra.strip():
        user_msg += f'\n\nZUSÄTZLICHE HINWEISE:\n{extra}'

    text = ki._request_claude(api_key, _INITIATIV_SYSTEM_PROMPT, user_msg,
                              max_tokens=2048)
    cfg = ki._parse_claude_json(text)

    betreff = (cfg.get('betreff') or DEFAULT_BETREFF).strip()
    body = (cfg.get('text') or DEFAULT_TEXT).strip()
    # Sicherstellen, dass der Platzhalter vorhanden ist (sonst Personalisierung
    # unmöglich) – notfalls in die Anrede einfügen.
    if '{firma}' not in body:
        body = body.replace(
            'Sehr geehrte Damen und Herren,',
            'Sehr geehrte Damen und Herren,\n\n(zu Händen {firma})', 1)
        if '{firma}' not in body:
            body = '(An {firma})\n\n' + body
    return {'betreff': betreff, 'text': body}


def personalize(text, firma):
    """{firma}-Platzhalter durch den echten Firmennamen ersetzen."""
    return (text or '').replace('{firma}', firma or 'Ihr Unternehmen')
