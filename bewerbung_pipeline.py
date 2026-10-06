#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Von der Trefferliste zur fertigen Bewerbungsmappe.

    py jobsuche.py 7 --bewerten        # Liste bauen und bewerten
    py bewerbung_pipeline.py           # offene Stellen anzeigen
    py bewerbung_pipeline.py 3         # Mappe fuer Eintrag 3 erstellen

Was dabei passiert: Anzeigentext holen, Kontaktadresse heraussuchen, den
KI-Assistenten darauf ansetzen, Lebenslauf, Anschreiben und Deckblatt
erzeugen - und dann aufhoeren.

Bewusst wird NICHT automatisch gesendet. In dieser Mappe liegen 7.213
Initiativbewerbungen, die an Fahrradlaeden gingen und eine einzige
Reaktion gebracht haben. Ein Knopf, der ungeprueft verschickt, baut genau
diesen Berg erneut auf. Der Versand bleibt beim Menschen: die Mappe wird
geoeffnet, gelesen und dann in der Oberflaeche verschickt.
"""

import io
import json
import os
import re
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STELLEN_JSON = os.path.join(BASE_DIR, 'stellen.json')
CACHE_DATEI = os.path.join(BASE_DIR, '.anzeigen_cache.json')
MAPPEN_DIR = os.path.join(BASE_DIR, 'bewerbungen')
API_KEY_DATEI = os.path.join(BASE_DIR, '.claude_api_key')

# Adressen, die zwar im Text stehen, aber keine Bewerbung entgegennehmen.
KEIN_EMPFAENGER = re.compile(
    r'(no[-_]?reply|noreply|datenschutz|privacy|webmaster|abuse|postmaster'
    r'|impressum|widerruf|newsletter|example|muster|ihre?-?mail)', re.I)
# Adressen, die sehr wahrscheinlich die richtigen sind.
GUTER_EMPFAENGER = re.compile(
    r'(bewerb|job|karriere|career|personal|recruit|hr@|stellen)', re.I)

EMAIL_MUSTER = re.compile(r'[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}')


def _laden(pfad, standard):
    try:
        with io.open(pfad, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return standard


def finde_empfaenger(text):
    """Beste Kontaktadresse aus dem Anzeigentext, oder None.

    Sortiert nach Brauchbarkeit statt einfach die erste zu nehmen: in vielen
    Anzeigen steht die Datenschutzadresse weiter oben als die Bewerbungs-
    adresse.
    """
    kandidaten = []
    for adresse in dict.fromkeys(EMAIL_MUSTER.findall(text or '')):
        if KEIN_EMPFAENGER.search(adresse):
            continue
        if adresse.lower().endswith(('.png', '.jpg', '.gif', '.webp')):
            continue
        kandidaten.append((0 if GUTER_EMPFAENGER.search(adresse) else 1,
                           adresse))
    kandidaten.sort()
    return kandidaten[0][1] if kandidaten else None


def offene_stellen(stellen, mindest_passung=0):
    """Noch nicht beworbene Stellen, beste Passung zuerst."""
    offen = [z for z in stellen if not z.get('beworben')]
    if mindest_passung:
        offen = [z for z in offen if (z.get('passung') or 0) >= mindest_passung]
    offen.sort(key=lambda z: (-(z.get('passung') if z.get('passung')
                                is not None else -1),
                              -(z.get('gefordert') or 0)))
    return offen


def zeige_liste(offen, anzahl=25):
    if not offen:
        print('Keine offenen Stellen. Erst "py jobsuche.py 7 --bewerten" '
              'laufen lassen.')
        return
    print('%d offene Stellen (beste Passung zuerst):\n' % len(offen))
    print('  Nr  Pass.  Bereich      Ort                  km   Stelle')
    print('  ' + '-' * 86)
    for nr, z in enumerate(offen[:anzahl], 1):
        p = ('%3d%%' % z['passung']) if z.get('passung') is not None else '  - '
        print('  %3d %s  %-12s %-20s %4s  %s'
              % (nr, p, (z.get('bereich') or '')[:12], (z.get('ort') or '')[:20],
                 z.get('km') if z.get('km') is not None else '', z['titel'][:44]))
    if len(offen) > anzahl:
        print('\n  ... und %d weitere.' % (len(offen) - anzahl))
    print('\nMappe erstellen:  py bewerbung_pipeline.py <Nr>')


def _anzeigentext(z):
    """Anzeigentext aus dem Zwischenspeicher, sonst frisch holen."""
    cache = _laden(CACHE_DATEI, {})
    text = cache.get(z['url'])
    if text:
        return text
    import ki_assistent
    text = ki_assistent.fetch_job_text(z['url'])
    cache[z['url']] = text
    try:
        with io.open(CACHE_DATEI, 'w', encoding='utf-8') as f:
            json.dump(cache, f, ensure_ascii=False)
    except OSError:
        pass
    return text


def _dateiname(teil):
    sauber = re.sub(r'[<>:"/\\|?*]', '', (teil or '').strip())
    return re.sub(r'\s+', ' ', sauber)[:70] or 'Unbekannt'


def erstelle_mappe(z):
    """Anzeigentext auswerten, Unterlagen erzeugen, Ergebnis berichten."""
    import generate_anschreiben as gen_a
    import generate_kapak as gen_k
    import generate_lebenslauf as gen_l
    import ki_assistent as ki
    import stellen_abgleich as sa

    print('Stelle   : %s' % z['titel'])
    print('Firma    : %s' % (z.get('firma') or '-'))
    print('Ort      : %s %s' % (z.get('plz') or '', z.get('ort') or ''))
    print('Anzeige  : %s' % z['url'])
    print()

    print('Anzeigentext holen ...')
    text = _anzeigentext(z)
    if not text:
        print('  Kein Text erhalten - Anzeige im Browser oeffnen.')
        return 1
    print('  %d Zeichen.' % len(text))

    empfaenger = finde_empfaenger(text)
    print('Empfaenger: %s' % (empfaenger or
                              'keine Adresse im Text (Bewerbung ueber die '
                              'Anzeige oder die Firmenseite)'))

    print('\nAbgleich mit dem Profil:')
    for zeile in sa.bericht(text).splitlines():
        print('  ' + zeile)

    api_key = ''
    if os.path.isfile(API_KEY_DATEI):
        api_key = io.open(API_KEY_DATEI, encoding='utf-8').read().strip()
    api_key = api_key or os.environ.get('ANTHROPIC_API_KEY', '')
    if not api_key:
        print('\nKein API-Schluessel (.claude_api_key oder ANTHROPIC_API_KEY).')
        print('Ohne ihn koennen Kurzprofil und Anschreiben nicht '
              'zugeschnitten werden.')
        return 2

    print('\nKI-Assistent laeuft (Modell %s) ...' % ki.MODELL)
    cfg = ki.call_claude(api_key, text)
    # Der Anzeigentext bleibt in der Konfiguration: der Lebenslauf sortiert
    # die IT-Kenntnisse danach und waehlt Variante und Sprache.
    cfg['stellentext'] = text
    cfg.setdefault('firma', z.get('firma') or '')
    cfg.setdefault('stelle', z['titel'])
    if empfaenger:
        cfg.setdefault('empfaenger_mail', empfaenger)

    variante = gen_l.variante_aus_cfg(cfg)
    sprache = gen_l.sprache_aus_cfg(cfg)
    print('  Stelle   : %s' % cfg.get('stelle'))
    print('  Variante : %s / %s' % (variante, sprache))

    ordner = os.path.join(MAPPEN_DIR, '%s - %s'
                          % (_dateiname(cfg.get('firma')),
                             _dateiname(cfg.get('stelle'))))
    os.makedirs(ordner, exist_ok=True)

    print('\nUnterlagen erzeugen ...')
    erzeugt = []
    for name, modul in (('Lebenslauf', gen_l), ('Anschreiben', gen_a),
                        ('Deckblatt', gen_k)):
        pfad = os.path.join(ordner, 'Hamza_Oeztuerk_%s.pdf' % name)
        try:
            modul.generate(pfad, cfg)
            erzeugt.append(pfad)
            print('  %s' % pfad)
        except Exception as fehler:
            print('  %s fehlgeschlagen: %s' % (name, fehler))

    with io.open(os.path.join(ordner, 'stelle.json'), 'w',
                 encoding='utf-8') as f:
        json.dump({'anzeige': z, 'empfaenger': empfaenger,
                   'betreff': cfg.get('betreff'), 'cfg': cfg},
                  f, ensure_ascii=False, indent=1)

    print('\nFertig. %d Datei(en) in:\n  %s' % (len(erzeugt), ordner))
    print('\nNicht gesendet - absichtlich. Unterlagen lesen, dann in der')
    print('Oberflaeche (py bewerbungs_manager.py) verschicken.')
    if empfaenger:
        print('Empfaenger fuer die Mail: %s' % empfaenger)
    return 0


def main():
    stellen = _laden(STELLEN_JSON, None)
    if stellen is None:
        print('stellen.json fehlt. Erst die Liste bauen:')
        print('  py jobsuche.py 7 --bewerten')
        return 1

    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    mindest = 0
    for a in sys.argv[1:]:
        if a.startswith('--ab='):
            mindest = int(a.split('=', 1)[1] or 0)

    offen = offene_stellen(stellen, mindest)
    if not args:
        zeige_liste(offen)
        return 0

    try:
        nr = int(args[0])
    except ValueError:
        print('Nutzung: py bewerbung_pipeline.py [Nr] [--ab=70]')
        return 2
    if not 1 <= nr <= len(offen):
        print('Es gibt nur %d offene Stellen.' % len(offen))
        return 2
    return erstelle_mappe(offen[nr - 1])


if __name__ == '__main__':
    sys.exit(main())
