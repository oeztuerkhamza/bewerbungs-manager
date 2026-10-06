#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stellenanzeigen – Jobsuche der Bundesagentur für Arbeit

Fragt mehrere Suchbegriffe deutschlandweit ab, entfernt Duplikate, filtert
Einstiegspositionen heraus und schreibt eine eigenständige HTML-Seite.

    py jobsuche.py              # alle Anzeigen
    py jobsuche.py 14           # nur die letzten 14 Tage

Datenquelle: https://www.arbeitsagentur.de/jobsuche/suche
Die Seite liefert ihre Trefferliste als Angular-Transfer-State (Script-Tag
"ng-state") mit; daraus wird das JSON gelesen. Kein API-Schlüssel nötig.
"""

import io
import json
import math
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT = os.path.join(BASE_DIR, 'junior_stellen.html')
# Dieselbe Liste maschinenlesbar - davon lebt bewerbung_pipeline.py.
OUTPUT_JSON = os.path.join(BASE_DIR, 'stellen.json')
BEWERBUNGEN_CSV = os.path.join(BASE_DIR, 'Bewerbungen.csv')

SUCHE_URL = 'https://www.arbeitsagentur.de/jobsuche/suche'
DETAIL_URL = 'https://www.arbeitsagentur.de/jobsuche/jobdetail/'
USER_AGENT = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
              '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
PAUSE = 0.5          # Sekunden zwischen zwei Anfragen, um höflich zu bleiben

# Die Jobsuche der BA kennt nur diese Werte für "veröffentlicht seit". Jeder
# andere Wert wird stillschweigend ignoriert und liefert ALLE Anzeigen -
# "py jobsuche.py 3" brachte deshalb mehr Treffer als "py jobsuche.py 7".
# Geprüft: 1 → 115, 7 → 461, 14 → 835, 28 → 1358 Treffer; 2, 3, 5, 21, 30
# und 100 liefern unverändert 3015, also die ungefilterte Gesamtmenge.
ERLAUBTE_TAGE = (1, 7, 14, 28)

# Wohnort als Bezugspunkt für die Entfernungsspalte
HEIMAT = ('Freiburg im Breisgau', 47.9990, 7.8421)

# Die Jobsuche der BA listet auch österreichische Stellen mit. Auf None
# setzen, wenn alle Länder erscheinen sollen.
NUR_LAND = 'DEUTSCHLAND'

# Die API liefert Bundesländer transliteriert (BADEN_WUERTTEMBERG). Für die
# Anzeige zurück auf die richtige Schreibweise bringen.
REGION_NAMEN = {
    'BADEN_WUERTTEMBERG': 'Baden-Württemberg',
    'BAYERN': 'Bayern',
    'BERLIN': 'Berlin',
    'BRANDENBURG': 'Brandenburg',
    'BREMEN': 'Bremen',
    'HAMBURG': 'Hamburg',
    'HESSEN': 'Hessen',
    'MECKLENBURG_VORPOMMERN': 'Mecklenburg-Vorpommern',
    'NIEDERSACHSEN': 'Niedersachsen',
    'NORDRHEIN_WESTFALEN': 'Nordrhein-Westfalen',
    'RHEINLAND_PFALZ': 'Rheinland-Pfalz',
    'SAARLAND': 'Saarland',
    'SACHSEN': 'Sachsen',
    'SACHSEN_ANHALT': 'Sachsen-Anhalt',
    'SCHLESWIG_HOLSTEIN': 'Schleswig-Holstein',
    'THUERINGEN': 'Thüringen',
}

# Begriffe, bei denen "Junior" meist im Titel steht -> tief paginieren.
# Suchbegriffe: (Begriff, Seitenbudget, Bereich).
# Das Budget bremst breite Begriffe - "Softwareentwickler" liefert sonst
# tausende Treffer, von denen die hinteren Seiten nichts mehr beitragen.
# Der Bereich entscheidet spaeter, welche Lebenslauf-Variante passt.
BEGRIFFE = [
    # ── Entwicklung ────────────────────────────────────────────────────
    ('Softwareentwickler',                   10, 'Entwicklung'),
    ('Fullstack Entwickler',                  8, 'Entwicklung'),
    ('Anwendungsentwickler',                  6, 'Entwicklung'),
    ('Webentwickler',                         5, 'Entwicklung'),
    ('Softwareentwickler C#',                 5, 'Entwicklung'),
    ('.NET Entwickler',                       5, 'Entwicklung'),
    ('Angular Entwickler',                    4, 'Entwicklung'),
    ('Frontend Entwickler',                   4, 'Entwicklung'),
    ('Backend Entwickler',                    4, 'Entwicklung'),
    ('DevOps Engineer',                       4, 'Entwicklung'),
    ('Fachinformatiker Anwendungsentwicklung', 5, 'Entwicklung'),
    ('Softwareentwickler Berufseinsteiger',   3, 'Entwicklung'),
    # ── IT-Support und Administration ──────────────────────────────────
    ('IT-Support',                            8, 'IT-Support'),
    ('IT-Systemadministrator',                6, 'IT-Support'),
    ('Systemadministrator',                   6, 'IT-Support'),
    ('IT-Administrator',                      5, 'IT-Support'),
    ('Fachinformatiker Systemintegration',    5, 'IT-Support'),
    ('IT-Mitarbeiter',                        4, 'IT-Support'),
    ('Anwendungsbetreuer',                    3, 'IT-Support'),
    ('IT-Techniker',                          3, 'IT-Support'),
]

# Signale im Titel. Reihenfolge egal, alles wird kleingeschrieben verglichen.
EINSTIEG_SIGNALE = (
    'junior', 'einsteiger', 'berufseinsteiger', 'absolvent', 'einstieg',
    'trainee', 'nachwuchs', 'graduate', 'entry level', 'fachinformatiker',
)
# Titel mit diesen Wörtern passen nicht: zu weit oben oder falsche Art Stelle.
AUSSCHLUSS_SIGNALE = (
    'senior', 'lead', 'teamleit', 'architekt', 'principal', 'head of',
    'ausbildung', 'auszubildende', 'praktik', 'werkstudent', 'duales studium',
    'dualer student', 'bachelorand', 'masterand', 'abschlussarbeit',
    'professor', 'dozent', 'ausbilder',
)


# ─── DATENABRUF ──────────────────────────────────────────────────────────────
def hole_seite(was, page, veroeffentlicht_seit=None):
    """Eine Trefferseite abrufen. Gibt das 'suchergebnis'-Objekt zurück."""
    params = {'angebotsart': 1, 'was': was, 'page': page}
    if veroeffentlicht_seit:
        params['veroeffentlichtseit'] = veroeffentlicht_seit
    url = SUCHE_URL + '?' + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        html = resp.read().decode('utf-8', 'replace')
    treffer = re.search(r'<script[^>]*id="ng-state"[^>]*>(.*?)</script>',
                        html, re.S)
    if not treffer:
        return {}
    daten = json.loads(treffer.group(1)) or {}
    return daten.get('suchergebnis') or {}


def sammle(veroeffentlicht_seit=None):
    """Alle Suchbegriffe abklappern und nach Referenznummer entduplizieren."""
    gefunden = {}
    for was, max_seiten, bereich in BEGRIFFE:
        neu_fuer_begriff = 0
        for page in range(1, max_seiten + 1):
            try:
                ergebnis = hole_seite(was, page, veroeffentlicht_seit)
            except (urllib.error.URLError, urllib.error.HTTPError,
                    TimeoutError, ValueError) as fehler:
                print('    ! %s Seite %d: %s' % (was, page, fehler))
                break

            liste = ergebnis.get('ergebnisliste') or []
            if not liste:
                break
            for eintrag in liste:
                refnr = eintrag.get('referenznummer')
                if refnr and refnr not in gefunden:
                    eintrag['_begriff'] = was
                    eintrag['_bereich'] = bereich
                    gefunden[refnr] = eintrag
                    neu_fuer_begriff += 1

            gesamt = ergebnis.get('maxErgebnisse') or 0
            groesse = ergebnis.get('size') or 25
            if page * groesse >= gesamt:
                break
            time.sleep(PAUSE)

        print('  %-42s %4d neu  (gesamt %d)'
              % (was, neu_fuer_begriff, len(gefunden)))
        time.sleep(PAUSE)

    return list(gefunden.values())


# ─── FILTER UND AUFBEREITUNG ─────────────────────────────────────────────────
def ist_ausgeschlossen(titel):
    t = (titel or '').lower()
    return any(wort in t for wort in AUSSCHLUSS_SIGNALE)


def hat_einstieg_signal(titel):
    t = (titel or '').lower()
    return any(wort in t for wort in EINSTIEG_SIGNALE)


def region_name(rohwert):
    """Bundesland lesbar machen; unbekannte Werte nur entstrichen."""
    if not rohwert:
        return ''
    return REGION_NAMEN.get(rohwert, rohwert.replace('_', '-').title())


def entfernung_km(breite, laenge):
    """Luftlinie zum Wohnort (Haversine), gerundet auf ganze Kilometer."""
    if breite is None or laenge is None:
        return None
    _, lat0, lon0 = HEIMAT
    r = 6371.0
    d_lat = math.radians(breite - lat0)
    d_lon = math.radians(laenge - lon0)
    a = (math.sin(d_lat / 2) ** 2
         + math.cos(math.radians(lat0)) * math.cos(math.radians(breite))
         * math.sin(d_lon / 2) ** 2)
    return int(round(2 * r * math.asin(math.sqrt(a))))


def lade_beworbene_firmen():
    """Firmennamen aus dem Bewerbungs-Tracker, normalisiert für den Vergleich."""
    if not os.path.isfile(BEWERBUNGEN_CSV):
        return set()
    namen = set()
    try:
        import csv
        with io.open(BEWERBUNGEN_CSV, encoding='utf-8-sig',
                     errors='replace', newline='') as f:
            for zeile in csv.reader(f):
                if zeile and zeile[0].strip():
                    namen.add(normalisiere_firma(zeile[0]))
    except (OSError, UnicodeError) as fehler:
        print('  ! Bewerbungen.csv konnte nicht gelesen werden: %s' % fehler)
        return set()
    namen.discard('')
    return namen


def normalisiere_firma(name):
    """Rechtsformen und Zusätze weglassen, damit Namen vergleichbar werden."""
    n = (name or '').lower()
    n = re.sub(r'[^a-zäöüß0-9 ]+', ' ', n)
    for wort in ('gmbh', 'co kg', 'kg', 'ag', 'se', 'mbh', 'ohg', 'ug',
                 'e v', 'und', 'niederlassung', 'deutschland', 'group',
                 'holding', 'international'):
        n = re.sub(r'\b' + wort + r'\b', ' ', n)
    return ' '.join(n.split())


def aufbereiten(rohdaten, beworbene):
    """Rohtreffer in flache Datensätze für die HTML-Seite überführen."""
    zeilen = []
    for e in rohdaten:
        titel = e.get('stellenangebotsTitel') or ''
        if ist_ausgeschlossen(titel):
            continue

        lokation = (e.get('stellenlokationen') or [{}])[0]
        adresse = lokation.get('adresse') or {}
        if NUR_LAND and (adresse.get('land') or NUR_LAND) != NUR_LAND:
            continue
        firma = e.get('firma') or ''

        zeilen.append({
            'titel': titel,
            'firma': firma,
            'ort': adresse.get('ort') or '',
            'plz': adresse.get('plz') or '',
            'land': region_name(adresse.get('region')),
            'km': entfernung_km(lokation.get('breite'), lokation.get('laenge')),
            'gehalt_von': e.get('gehaltsspanneVon'),
            'gehalt_bis': e.get('gehaltsspanneBis'),
            'gehalt_art': e.get('verguetungsangabe') or '',
            'vollzeit': bool(e.get('arbeitszeitVollzeit')),
            'unbefristet': (e.get('vertragsdauer') or '') == 'UNBEFRISTET',
            'eintritt': (e.get('eintrittszeitraum') or {}).get('von') or '',
            'veroeffentlicht': ((e.get('veroeffentlichungszeitraum') or {})
                                .get('von') or ''),
            'beruf': e.get('hauptberuf') or '',
            'url': DETAIL_URL + urllib.parse.quote(e.get('referenznummer') or ''),
            'einstieg': hat_einstieg_signal(titel),
            'beworben': normalisiere_firma(firma) in beworbene if firma else False,
            'begriff': e.get('_begriff') or '',
            'bereich': e.get('_bereich') or '',
        })

    # Explizite Einstiegsstellen zuerst, danach die neuesten Anzeigen.
    zeilen.sort(key=lambda z: (not z['einstieg'], z['veroeffentlicht'] or ''),
                reverse=False)
    return zeilen


# ─── BEWERTUNG GEGEN DAS EIGENE PROFIL ───────────────────────────────────────
# Die Trefferliste allein hilft wenig, wenn 259 Anzeigen darin stehen. Mit
# dem Volltext laesst sich je Anzeige sagen, wie viel von dem Geforderten
# im Profil belegt ist - und danach kann sortiert werden.
CACHE_DATEI = os.path.join(BASE_DIR, '.anzeigen_cache.json')

# Jede Bewertung holt den Anzeigentext einzeln. Bei ueber tausend Treffern
# waere der erste Lauf eine Viertelstunde beschaeftigt, deshalb eine Grenze.
# Die Texte bleiben gespeichert, ein zweiter Lauf geht also deutlich weiter.
STANDARD_GRENZE = 300


def _cache_laden():
    try:
        with io.open(CACHE_DATEI, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _cache_speichern(cache):
    try:
        with io.open(CACHE_DATEI, 'w', encoding='utf-8') as f:
            json.dump(cache, f, ensure_ascii=False)
    except OSError:
        pass        # Cache ist Beschleunigung, kein Muss


def bewerte(zeilen, nur_unbeworbene=True, hoechstens=0):
    """Holt den Anzeigentext und vergleicht ihn mit dem eigenen Profil.

    Gibt die Anzahl bewerteter Anzeigen zurueck. Texte werden zwischen zwei
    Laeufen gespeichert, ein zweiter Durchgang ist deshalb sofort fertig.
    """
    try:
        import stellen_abgleich
        import ki_assistent
    except ImportError as fehler:
        print('Bewertung nicht moeglich: %s' % fehler)
        return 0

    offen = [z for z in zeilen if not (nur_unbeworbene and z['beworben'])]
    # Bereits zwischengespeicherte Anzeigen kosten nichts und zaehlen daher
    # nicht gegen die Grenze - so waechst die Abdeckung mit jedem Lauf.
    cache_vorab = _cache_laden()
    frisch = [z for z in offen if z['url'] not in cache_vorab]
    if hoechstens and len(frisch) > hoechstens:
        behalten = set(id(z) for z in frisch[:hoechstens])
        offen = [z for z in offen
                 if z['url'] in cache_vorab or id(z) in behalten]
        print('  %d von %d noch nicht geladen – diesmal %d; erneut aufrufen '
              'holt die naechsten.' % (len(frisch), len(zeilen), hoechstens))

    cache = _cache_laden()
    geholt = 0
    for nr, z in enumerate(offen, 1):
        text = cache.get(z['url'])
        if text is None:
            try:
                text = ki_assistent.fetch_job_text(z['url'])
            except Exception:
                text = ''
            cache[z['url']] = text
            geholt += 1
            time.sleep(PAUSE)
            if geholt % 25 == 0:
                print('  %d von %d geladen ...' % (nr, len(offen)))
                _cache_speichern(cache)
        if not text:
            continue

        treffer, luecken, _ = stellen_abgleich.abgleich(text)
        nah = [n for n, _e in stellen_abgleich.verwandte(luecken, naehe='nah')]
        echte = [n for n in luecken if n not in nah]
        gefordert = len(treffer) + len(nah) + len(echte)
        z['n_treffer'] = len(treffer)
        z['treffer'] = sorted(treffer)[:8]
        z['nah'] = nah
        z['luecken'] = echte
        # Unter drei erkannten Anforderungen sagt eine Quote nichts aus -
        # dann lieber keine Zahl als eine, die Sicherheit vortaeuscht.
        z['gefordert'] = gefordert
        z['passung'] = (round(100.0 * (len(treffer) + 0.5 * len(nah))
                              / gefordert) if gefordert >= 4 else None)

    _cache_speichern(cache)
    bewertet = sum(1 for z in zeilen if z.get('passung') is not None)
    print('%d Anzeigen bewertet (%d neu geladen, Rest aus dem Zwischenspeicher).'
          % (bewertet, geholt))
    return bewertet


# ─── HTML ────────────────────────────────────────────────────────────────────
HTML_KOPF = """<!doctype html>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Passende Stellen</title>
<style>
:root{
  --bg:#f5f6f8; --karte:#ffffff; --text:#1c1f26; --leise:#666c78;
  --linie:#dfe3ea; --navy:#1B3764; --akzent:#2C5AA0;
  --treffer:#e8f0fc; --warnung:#8a5a00; --warnung-bg:#fff6e0;
}
@media (prefers-color-scheme: dark){
  :root{
    --bg:#15181d; --karte:#1d2128; --text:#e8eaee; --leise:#9aa2b1;
    --linie:#2c323c; --navy:#8ab0e8; --akzent:#9dc0f0;
    --treffer:#1f2a3d; --warnung:#e0b24d; --warnung-bg:#332a12;
  }
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);
  font:14px/1.5 "Segoe UI",system-ui,-apple-system,sans-serif}
header{background:var(--karte);border-bottom:1px solid var(--linie);
  padding:18px 20px 14px}
h1{margin:0 0 4px;font-size:19px;color:var(--navy)}
.meta{color:var(--leise);font-size:12.5px}
.meta code{background:var(--bg);padding:1px 5px;border-radius:3px}
.filter{display:flex;flex-wrap:wrap;gap:10px;align-items:center;
  padding:12px 20px;background:var(--karte);
  border-bottom:1px solid var(--linie)}
.filter input[type=text],.filter input[type=number],.filter select{
  font:inherit;padding:6px 9px;border:1px solid var(--linie);border-radius:5px;
  background:var(--bg);color:var(--text)}
.filter input[type=text]{min-width:210px;flex:1 1 210px}
.filter label{display:flex;align-items:center;gap:5px;font-size:13px;
  color:var(--leise);white-space:nowrap}
.wrap{padding:14px 20px 40px;overflow-x:auto}
table{border-collapse:collapse;width:100%;background:var(--karte);
  border:1px solid var(--linie);border-radius:6px;font-size:13px}
th,td{padding:8px 10px;text-align:left;border-bottom:1px solid var(--linie);
  vertical-align:top}
th{background:var(--bg);font-weight:600;color:var(--navy);cursor:pointer;
  white-space:nowrap;position:sticky;top:0;z-index:4}
th:hover{color:var(--akzent)}
th .pfeil{opacity:.45;font-size:10px}
tr:last-child td{border-bottom:0}
tbody tr:hover{background:var(--treffer)}
a{color:var(--akzent);text-decoration:none}
a:hover{text-decoration:underline}
.tag{display:inline-block;font-size:10.5px;padding:1px 6px;border-radius:9px;
  border:1px solid var(--linie);color:var(--leise);margin-left:5px;
  white-space:nowrap}
.tag.einstieg{background:var(--treffer);border-color:var(--akzent);
  color:var(--akzent)}
.tag.beworben{background:var(--warnung-bg);border-color:var(--warnung);
  color:var(--warnung)}
.zahl{text-align:right;white-space:nowrap;font-variant-numeric:tabular-nums}
.leise{color:var(--leise)}
#status{padding:10px 20px;color:var(--leise);font-size:13px}
#leer{display:none;padding:40px 20px;text-align:center;color:var(--leise)}
</style>
"""


def js_zahl(wert):
    return 'null' if wert is None else str(wert)


def baue_html(zeilen, veroeffentlicht_seit):
    stand = datetime.now().strftime('%d.%m.%Y %H:%M')
    zeitraum = ('Anzeigen der letzten %d Tage' % veroeffentlicht_seit
                if veroeffentlicht_seit else 'alle aktuellen Anzeigen')
    einstieg_n = sum(1 for z in zeilen if z['einstieg'])
    je_bereich = ', '.join(
        '%d %s' % (sum(1 for z in zeilen if z.get('bereich') == b), b)
        for b in sorted({z['bereich'] for z in zeilen if z.get('bereich')}))
    beworben_n = sum(1 for z in zeilen if z['beworben'])
    laender = sorted({z['land'] for z in zeilen if z['land']})

    teile = [HTML_KOPF]
    teile.append('<header>')
    teile.append('<h1>Passende Stellen in Deutschland</h1>')
    teile.append(
        '<div class="meta">%d Anzeigen (%s) &middot; davon %d mit Junior-/'
        'Einsteiger-Signal im Titel &middot; %d bei Firmen, bei denen du dich '
        'schon beworben hast<br>Stand %s &middot; %s &middot; Quelle: '
        'Jobsuche der Bundesagentur f&uuml;r Arbeit &middot; '
        'neu laden mit <code>py jobsuche.py --bewerten</code></div>'
        % (len(zeilen), je_bereich, einstieg_n, beworben_n, stand, zeitraum))
    teile.append('</header>')

    teile.append('<div class="filter">')
    teile.append('<input type="text" id="q" placeholder="Titel, Firma oder Ort '
                 'suchen &hellip;">')
    teile.append('<select id="bereich"><option value="">Beide Bereiche'
                 '</option>')
    for bereich in sorted({z['bereich'] for z in zeilen if z.get('bereich')}):
        teile.append('<option>%s</option>' % bereich)
    teile.append('</select>')
    teile.append('<select id="land"><option value="">Alle Bundesl&auml;nder'
                 '</option>')
    for land in laender:
        teile.append('<option>%s</option>' % land)
    teile.append('</select>')
    teile.append('<label>max. km <input type="number" id="maxkm" min="0" '
                 'step="50" style="width:88px" placeholder="beliebig"></label>')
    teile.append('<label>ab &euro; <input type="number" id="mingehalt" min="0" '
                 'step="5000" style="width:104px" placeholder="beliebig">'
                 '</label>')
    teile.append('<label><input type="checkbox" id="nureinstieg"> '
                 'nur Junior/Einsteiger</label>')
    teile.append('<label><input type="checkbox" id="ohnebeworben"> '
                 'ohne bereits beworbene</label>')
    teile.append('<label><input type="checkbox" id="nurgehalt"> '
                 'nur mit Gehaltsangabe</label>')
    teile.append('<label>ab Passung <input type="number" id="minpassung" '
                 'min="0" max="100" step="10" style="width:76px" '
                 'placeholder="beliebig"> %</label>')
    teile.append('</div>')

    teile.append('<div id="status"></div>')
    teile.append('<div class="wrap"><table><thead><tr>')
    spalten = [('passung', 'Passung'), ('titel', 'Stelle'),
               ('firma', 'Firma'), ('ort', 'Ort'),
               ('km', 'km'), ('gehalt_von', 'Gehalt'),
               ('eintritt', 'Eintritt'), ('veroeffentlicht', 'Ver&ouml;ff.')]
    for feld, kopf in spalten:
        teile.append('<th data-feld="%s">%s <span class="pfeil"></span></th>'
                     % (feld, kopf))
    teile.append('</tr></thead><tbody id="tb"></tbody></table>')
    teile.append('<div id="leer">Keine Anzeige passt zu diesen Filtern.</div>')
    teile.append('</div>')

    teile.append('<script>')
    teile.append('const DATEN = %s;'
                 % json.dumps(zeilen, ensure_ascii=False, separators=(',', ':')))
    teile.append(HTML_SKRIPT)
    teile.append('</script>')
    return '\n'.join(teile)


HTML_SKRIPT = """
const $ = (id) => document.getElementById(id);
let sortFeld = null, sortAuf = true;


function euro(n){ return n ? n.toLocaleString('de-DE') + ' \\u20ac' : ''; }

function passungText(z){
  if (z.passung === undefined || z.passung === null)
    return '<span class="leise">&ndash;</span>';
  // Gruen ab zwei Dritteln, rot unter der Haelfte, dazwischen neutral.
  const f = z.passung >= 67 ? '#1b7a3d' : (z.passung < 50 ? '#9a3412' : '#555');
  const hinweis = ['belegt: ' + (z.treffer || []).join(', ')]
    .concat((z.nah || []).length ? ['anderes Werkzeug: ' + z.nah.join(', ')] : [])
    .concat((z.luecken || []).length ? ['fehlt: ' + z.luecken.join(', ')] : [])
    .join(' | ').replace(/"/g, '');
  // Die Zahl der erkannten Anforderungen steht daneben: 100 % aus vier
  // Treffern sagen weniger als 85 % aus fuenfzehn.
  return '<b style="color:' + f + '" title="' + hinweis + '">'
    + z.passung + '%</b><div class="leise">' + (z.gefordert || 0) + ' Anf.</div>';
}

function gehaltText(z){
  if (!z.gehalt_von && !z.gehalt_bis) return '<span class="leise">&ndash;</span>';
  if (z.gehalt_von && z.gehalt_bis && z.gehalt_von !== z.gehalt_bis)
    return euro(z.gehalt_von) + ' &ndash; ' + euro(z.gehalt_bis);
  return euro(z.gehalt_von || z.gehalt_bis);
}

function datum(s){
  if (!s) return '<span class="leise">&ndash;</span>';
  const t = s.split('-');
  return t.length === 3 ? t[2] + '.' + t[1] + '.' + t[0] : s;
}

function passt(z){
  const q = $('q').value.trim().toLowerCase();
  if (q && !(z.titel + ' ' + z.firma + ' ' + z.ort + ' ' + z.beruf)
            .toLowerCase().includes(q)) return false;
  if ($('land').value && z.land !== $('land').value) return false;
  if ($('bereich').value && z.bereich !== $('bereich').value) return false;
  const maxkm = parseFloat($('maxkm').value);
  if (!isNaN(maxkm) && (z.km === null || z.km > maxkm)) return false;
  const ming = parseFloat($('mingehalt').value);
  if (!isNaN(ming)){
    const g = z.gehalt_bis || z.gehalt_von;
    if (!g || g < ming) return false;
  }
  if ($('nureinstieg').checked && !z.einstieg) return false;
  if ($('ohnebeworben').checked && z.beworben) return false;
  if ($('nurgehalt').checked && !z.gehalt_von && !z.gehalt_bis) return false;
  const minp = parseFloat($('minpassung').value);
  if (!isNaN(minp) && (z.passung === undefined || z.passung === null
                       || z.passung < minp)) return false;
  return true;
}

function sortiere(liste){
  if (!sortFeld){
    // Ohne eigene Sortierung: beste Passung nach oben, Unbewertetes ans Ende.
    if (liste.some((z) => z.passung !== undefined && z.passung !== null))
      return liste.slice().sort((a, b) => {
        const pa = (a.passung === null || a.passung === undefined) ? -1 : a.passung;
        const pb = (b.passung === null || b.passung === undefined) ? -1 : b.passung;
        return pb - pa || (b.gefordert || 0) - (a.gefordert || 0);
      });
    return liste;
  }
  const richtung = sortAuf ? 1 : -1;
  return liste.slice().sort((a, b) => {
    let x = a[sortFeld], y = b[sortFeld];
    if (x === null || x === undefined || x === '') return 1;
    if (y === null || y === undefined || y === '') return -1;
    if (typeof x === 'number' && typeof y === 'number') return (x - y) * richtung;
    return String(x).localeCompare(String(y), 'de') * richtung;
  });
}

function zeichne(){
  const gefiltert = sortiere(DATEN.filter(passt));
  const rows = gefiltert.map((z) => {
    const tags = (z.einstieg ? '<span class="tag einstieg">Einstieg</span>' : '')
      + (z.beworben ? '<span class="tag beworben">schon beworben</span>' : '')
      + (z.unbefristet ? '' : '<span class="tag">befristet</span>')
      + (z.vollzeit ? '' : '<span class="tag">Teilzeit</span>');
    return '<tr>'
      + '<td class="zahl">' + passungText(z) + '</td>'
      + '<td><a href="' + z.url + '" target="_blank" rel="noopener">'
        + z.titel + '</a>' + tags
        + '<div class="leise">' + [z.bereich, z.beruf].filter(Boolean).join(' \u00b7 ')
        + '</div></td>'
      + '<td>' + (z.firma || '<span class="leise">&ndash;</span>') + '</td>'
      + '<td>' + (z.plz ? z.plz + ' ' : '') + z.ort
        + (z.land ? '<div class="leise">' + z.land + '</div>' : '') + '</td>'
      + '<td class="zahl">' + (z.km === null ? '' : z.km) + '</td>'
      + '<td class="zahl">' + gehaltText(z) + '</td>'
      + '<td class="zahl">' + datum(z.eintritt) + '</td>'
      + '<td class="zahl">' + datum(z.veroeffentlicht) + '</td>'
      + '</tr>';
  });
  $('tb').innerHTML = rows.join('');
  $('leer').style.display = rows.length ? 'none' : 'block';
  $('status').textContent = rows.length + ' von ' + DATEN.length
    + ' Anzeigen sichtbar';
}

document.querySelectorAll('th[data-feld]').forEach((th) => {
  th.addEventListener('click', () => {
    const feld = th.dataset.feld;
    sortAuf = (sortFeld === feld) ? !sortAuf : true;
    sortFeld = feld;
    document.querySelectorAll('th .pfeil').forEach((p) => { p.textContent = ''; });
    th.querySelector('.pfeil').textContent = sortAuf ? '\\u25b2' : '\\u25bc';
    zeichne();
  });
});
['q', 'land', 'bereich', 'maxkm', 'mingehalt', 'nureinstieg',
 'ohnebeworben', 'nurgehalt', 'minpassung']
  .forEach((id) => {
    $(id).addEventListener('input', zeichne);
    $(id).addEventListener('change', zeichne);
  });
zeichne();
"""


# ─── MAIN ────────────────────────────────────────────────────────────────────
def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    bewerten = '--bewerten' in sys.argv
    grenze = STANDARD_GRENZE
    for a in sys.argv[1:]:
        if a.startswith('--max='):
            grenze = int(a.split('=', 1)[1] or 0)      # --max=0 = ohne Grenze
    seit = None
    if args:
        try:
            seit = int(args[0])
        except ValueError:
            print('Nutzung: py jobsuche.py [Tage] [--bewerten] [--max=N]')
            return 2

    if seit and seit not in ERLAUBTE_TAGE:
        passend = min(ERLAUBTE_TAGE, key=lambda t: abs(t - seit))
        print('Die Jobsuche kennt nur %s Tage; %d wird still ignoriert. '
              'Nutze stattdessen %d.'
              % ('/'.join(str(t) for t in ERLAUBTE_TAGE), seit, passend))
        seit = passend

    print('Suche Stellenanzeigen (%s) ...'
          % ('letzte %d Tage' % seit if seit else 'alle'))
    roh = sammle(seit)
    if not roh:
        print('Keine Daten erhalten. Laeuft die Internetverbindung, und '
              'antwortet arbeitsagentur.de?')
        return 1

    beworbene = lade_beworbene_firmen()
    if beworbene:
        print('%d Firmen aus Bewerbungen.csv zum Abgleich geladen.'
              % len(beworbene))

    zeilen = aufbereiten(roh, beworbene)
    if bewerten:
        print('')
        print('Bewerte Anzeigen gegen das eigene Profil ...')
        bewerte(zeilen, hoechstens=grenze)
    io.open(OUTPUT, 'w', encoding='utf-8', newline='\n').write(
        baue_html(zeilen, seit))
    with io.open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(zeilen, f, ensure_ascii=False, indent=1)

    print('\n%d Anzeigen nach Filter (von %d Rohtreffern).'
          % (len(zeilen), len(roh)))
    if not bewerten:
        print('Tipp: py jobsuche.py --bewerten vergleicht jede Anzeige mit '
              'deinem Profil und sortiert danach.')
    print('Seite geschrieben:\n  %s' % OUTPUT)
    return 0


if __name__ == '__main__':
    sys.exit(main())
