#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Abgleich einer Stellenanzeige mit dem eigenen Profil.

Zwei Aufgaben, die bewusst getrennt bleiben:

1. SORTIEREN – was in der Anzeige vorkommt und im Lebenslauf schon steht,
   wandert in den IT-Kenntnissen nach vorne. Es wird nichts hinzugefuegt
   und nichts umformuliert, nur die Reihenfolge geaendert. Wer die Anzeige
   geschrieben hat, sucht beim Ueberfliegen nach seinen eigenen Begriffen;
   die sollen in der ersten Zeile stehen, nicht in der vierten.

2. BERICHTEN – was die Anzeige verlangt und im Profil NICHT belegt ist,
   wird ausgegeben, nicht eingebaut. Eine Technologie in den Lebenslauf zu
   schreiben, die man nicht kann, faellt spaetestens im Fachgespraech auf
   und kostet mehr als die fehlende Zeile.

Aufruf von Hand:
    py stellen_abgleich.py anzeige.txt
    py stellen_abgleich.py            (liest von der Standardeingabe)
"""

import io
import json
import os
import re
import sys
from datetime import date

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ─── WAS IM PROFIL BELEGT IST ────────────────────────────────────────────────
# Schluessel = Anzeigename, Wert = Schreibweisen, wie sie in Anzeigen stehen.
# Hier darf NUR auftauchen, was auch im Lebenslauf steht. Jede Zeile, die
# hier ohne Beleg landet, wuerde zu einer Behauptung im Lebenslauf fuehren.
KANN = {
    # Backend
    'C#':                 r'c#|c\s?sharp',
    '.NET':               r'\.net\b|dotnet|asp\.net',
    'ASP.NET Core':       r'asp\.net\s*core',
    'EF Core':            r'entity\s*framework|\bef\s*core\b',
    'Clean Architecture': r'clean\s*architecture|hexagonal|onion\s*architecture',
    'REST-APIs':          r'rest[-\s]?ful|rest[-\s]?api|\brest\b|webapi',
    'xUnit':              r'\bxunit\b',
    'Moq':                r'\bmoq\b',
    # Frontend
    'Angular':            r'\bangular\b',
    'TypeScript':         r'\btypescript\b',
    'React':              r'\breact\b',
    'Next.js':            r'next\.?\s?js',
    'Tailwind CSS':       r'\btailwind\b',
    'NgRx':               r'\bngrx\b|\bredux\b',
    'HTML/CSS':           r'\bhtml\b|\bcss\b',
    # Datenbanken
    'SQL Server':         r'sql[-\s]?server|\bmssql\b|t-sql',
    'SQLite':             r'\bsqlite\b',
    'PostgreSQL':         r'postgre',
    'SQL':                r'\bsql\b',
    # Betrieb und DevOps
    'Docker':             r'\bdocker\b|container',
    'GitHub Actions':     r'github\s*actions',
    'Azure DevOps':       r'azure\s*devops',
    'Azure':              r'\bazure\b',
    'CI/CD':              r'ci\s*/?\s*cd|continuous\s+(integration|delivery|deployment)',
    'Git':                r'\bgit\b|versionsverwaltung',
    'Linux':              r'\blinux\b|ubuntu|debian',
    'Nginx':              r'\bnginx\b|reverse\s*proxy',
    'Windows':            r'\bwindows\b',
    'Bash':               r'\bbash\b|shell[-\s]?skript|\bshell\b',
    'Python':             r'\bpython\b',
    'Backup/Wiederherstellung': r'backup|datensicherung|wiederherstellung|restore',
    'Monitoring':         r'monitoring|überwachung|ueberwachung',
    # Netzwerk, Mail, Sicherheit
    'DNS':                r'\bdns\b',
    'SPF/DKIM/DMARC':     r'\bdkim\b|\bspf\b|\bdmarc\b',
    'Mailserver':         r'mailserver|postfix|dovecot|imap|smtp|mail[-\s]?server',
    'TLS/Zertifikate':    r'\btls\b|\bssl\b|zertifikat|let.?s\s*encrypt',
    'IT-Sicherheit':      r'it[-\s]?sicherheit|hardening|hsts|\bcsp\b',
    # Anwender
    'Anwendersupport':    r'support|anwenderbetreuung|helpdesk|service\s?desk|ticket|störungs|stoerungs|1st[-\s]level|first[-\s]level',
    'Schulung/Einweisung': r'schulung|einweisung|anwenderschulung|wissenstransfer',
    'Dokumentation':      r'dokumentation|dokumentieren',
    # KI
    'OpenAI API / LLM':   r'\bopenai\b|\bgpt\b|\bllm\b|large\s*language|\bki\b|künstliche\s*intelligenz|kuenstliche\s*intelligenz|artificial\s*intelligence|\bai\b',
    'Prompt Engineering': r'prompt[-\s]?engineering|prompting',
    'Web-Scraping':       r'scraping|\bplaywright\b|\bselenium\b',
}

# ─── WAS HAEUFIG GEFORDERT WIRD UND NICHT BELEGT IST ─────────────────────────
# Diese Liste dient nur dem Bericht. Nichts davon darf in den Lebenslauf.
KANN_NICHT = {
    'Java':             r'\bjava\b(?!script)',
    'Spring':           r'spring\s*(boot|framework)|\bspring\b',
    'PHP':              r'\bphp\b',
    'Laravel':          r'\blaravel\b',
    'Vue':              r'\bvue\b',
    'Go':               r'\bgolang\b|\bgo\b(?=\s*(entwickl|developer))',
    'Rust':             r'\brust\b',
    'Kotlin':           r'\bkotlin\b',
    'Swift':            r'\bswift\b',
    'Kubernetes':       r'kubernetes|\bk8s\b|openshift',
    'Terraform':        r'terraform|\biac\b|infrastructure\s*as\s*code',
    'AWS':              r'\baws\b|amazon\s*web\s*services',
    'Google Cloud':     r'\bgcp\b|google\s*cloud',
    'Jenkins':          r'\bjenkins\b',
    'GitLab CI':        r'gitlab\s*ci|gitlab-ci',
    'Ansible':          r'\bansible\b|\bpuppet\b|\bchef\b',
    'MongoDB':          r'\bmongo',
    'Redis':            r'\bredis\b',
    'Kafka':            r'\bkafka\b|rabbitmq|message\s*broker',
    'GraphQL':          r'\bgraphql\b',
    'Elasticsearch':    r'elasticsearch|\bopensearch\b',
    'Active Directory': r'active\s*directory|\bad\s*ds\b|\bldap\b|gruppenrichtlinien|\bgpo\b',
    'Exchange':         r'\bexchange\b(?!\s*rate)',
    'Microsoft 365':    r'microsoft\s*365|\bm365\b|office\s*365|intune|entra',
    'VMware/Hyper-V':   r'vmware|hyper-?v|\besxi\b|virtualisierung',
    'Citrix':           r'\bcitrix\b',
    'SAP':              r'\bsap\b',
    'Salesforce':       r'salesforce',
    'ITIL':             r'\bitil\b',
    'Jira/Confluence':  r'\bjira\b|confluence',
    'Scrum/Agile':      r'\bscrum\b|\bkanban\b|agil|safe\b',
    'Firewall/VPN':     r'firewall|\bvpn\b|fortigate|sophos|\bpfsense\b',
    'Netzwerk (LAN/WAN)': r'\blan\b|\bwan\b|\bvlan\b|switch|router|netzwerkinfrastruktur',
}


# ─── VERWANDTE WERKZEUGE ─────────────────────────────────────────────────────
# Eine Anzeige nennt ein Werkzeug, der Bewerber benutzt ein anderes fuer
# dieselbe Aufgabe. Das ist keine Luecke, sondern eine andere Beschriftung -
# und genau daran scheitern Bewerbungen, die nur nach Stichworten gefiltert
# werden.
#
# 'naehe' trennt zwei Faelle sauber:
#   nah      – gleiche Aufgabe, Umstieg ist eine Frage von Tagen. Taugt als
#              Satz im Anschreiben.
#   entfernt – verwandtes Feld, aber erkennbar etwas anderes. Wird nur
#              gemeldet; wer das als gleichwertig verkauft, fliegt auf.
VERWANDT = {
    'Jira/Confluence': {
        'name': 'Jira', 'naehe': 'nah',
        'habe': ['Azure DevOps'],
        'gemeinsam': 'Tickets und Backlog im Team',
    },
    'Jenkins': {
        'name': 'Jenkins', 'naehe': 'nah',
        'habe': ['GitHub Actions', 'Azure DevOps'],
        'gemeinsam': 'CI/CD-Pipelines',
    },
    'GitLab CI': {
        'name': 'GitLab CI', 'naehe': 'nah',
        'habe': ['GitHub Actions', 'Azure DevOps'],
        'gemeinsam': 'CI/CD-Pipelines',
    },
    'AWS': {
        'name': 'AWS', 'naehe': 'nah',
        'habe': ['Azure'],
        'gemeinsam': 'den Betrieb in der Public Cloud',
    },
    'Google Cloud': {
        'name': 'Google Cloud', 'naehe': 'nah',
        'habe': ['Azure'],
        'gemeinsam': 'den Betrieb in der Public Cloud',
    },
    'Vue': {
        'name': 'Vue', 'naehe': 'nah',
        'habe': ['Angular', 'React'],
        'gemeinsam': 'komponentenbasiertes Frontend mit TypeScript',
    },
    'Spring': {
        'name': 'Spring Boot', 'naehe': 'nah',
        'habe': ['ASP.NET Core'],
        'gemeinsam': 'ein Backend mit Dependency Injection und ORM',
    },
    'Java': {
        'name': 'Java', 'naehe': 'nah',
        'habe': ['C#', '.NET'],
        'gemeinsam': 'objektorientierte Backend-Entwicklung',
    },
    'GraphQL': {
        'name': 'GraphQL', 'naehe': 'entfernt',
        'habe': ['REST-APIs'],
        'gemeinsam': 'API-Entwurf und Datenmodellierung',
    },
    'Kubernetes': {
        'name': 'Kubernetes', 'naehe': 'entfernt',
        'habe': ['Docker', 'Docker Compose'],
        'gemeinsam': 'das Bauen und Betreiben von Containern',
    },
    'Terraform': {
        'name': 'Terraform', 'naehe': 'entfernt',
        'habe': ['Docker Compose', 'GitHub Actions'],
        'gemeinsam': 'das Aufsetzen von Umgebungen aus Dateien',
    },
    'Ansible': {
        'name': 'Ansible', 'naehe': 'entfernt',
        'habe': ['Bash', 'Python'],
        'gemeinsam': 'das Automatisieren wiederkehrender Systemaufgaben',
    },
    'Exchange': {
        'name': 'Exchange', 'naehe': 'entfernt',
        'habe': ['Mailcow (Postfix/Dovecot)'],
        'gemeinsam': 'den Mailserver mit Postfaechern, SPF, DKIM und DMARC',
    },
    'MongoDB': {
        'name': 'MongoDB', 'naehe': 'entfernt',
        'habe': ['PostgreSQL', 'SQL Server'],
        'gemeinsam': 'Datenmodellierung und Abfrageoptimierung',
    },
    'VMware/Hyper-V': {
        'name': 'VMware', 'naehe': 'entfernt',
        'habe': ['Docker', 'Linux (VPS)'],
        'gemeinsam': 'das Bereitstellen isolierter Umgebungen',
    },
}


def _treffer(text, muster):
    """Welche Eintraege aus 'muster' kommen im Text vor?"""
    klein = (text or '').lower()
    gefunden = []
    for name, regex in muster.items():
        if re.search(regex, klein):
            gefunden.append(name)
    return gefunden


# ─── EIGENE ZUSATZKENNTNISSE ─────────────────────────────────────────────────
# Was in KANN fehlt, aber tatsaechlich vorhanden ist, wird hier gesammelt -
# einmal bestaetigt, gilt es fuer alle weiteren Bewerbungen. Eine Absage wird
# ebenfalls gemerkt, damit dieselbe Frage nicht bei jeder Anzeige wiederkommt.
EIGENE_DATEI = os.path.join(BASE_DIR, 'eigene_kenntnisse.json')

_LEER = {'bestaetigt': {}, 'abgelehnt': {}}


def lade_eigene():
    """Liest die gespeicherten Antworten; bei Problemen leer statt Absturz."""
    try:
        with io.open(EIGENE_DATEI, encoding='utf-8') as f:
            daten = json.load(f)
    except (OSError, ValueError):
        return dict(_LEER)
    for schluessel in _LEER:
        daten.setdefault(schluessel, {})
    return daten


def speichere_eigene(daten):
    with io.open(EIGENE_DATEI, 'w', encoding='utf-8') as f:
        json.dump(daten, f, ensure_ascii=False, indent=2, sort_keys=True)


def abgleich(stellentext, eigene=None):
    """Gibt (treffer, luecken, offen) fuer eine Stellenanzeige zurueck.

    treffer  – im Profil belegt, inklusive der bereits bestaetigten Nachtraege
    luecken  – von der Anzeige gefordert, nicht belegt
    offen    – Luecken, zu denen noch keine Antwort vorliegt (hier wird gefragt)
    """
    eigene = lade_eigene() if eigene is None else eigene
    treffer = _treffer(stellentext, KANN)
    luecken = _treffer(stellentext, KANN_NICHT)

    bestaetigt = eigene.get('bestaetigt', {})
    abgelehnt = eigene.get('abgelehnt', {})

    # Was nachtraeglich bestaetigt wurde, ist ein Treffer, keine Luecke.
    treffer += [n for n in luecken if n in bestaetigt]
    luecken = [n for n in luecken if n not in bestaetigt]
    # Abgelehntes bleibt eine Luecke - aber es wird nicht erneut gefragt.
    offen = [n for n in luecken if n not in abgelehnt]
    return treffer, luecken, offen


# ─── SKILLS NACH ANZEIGE SORTIEREN ───────────────────────────────────────────
def _teile(wert):
    """Zerlegt 'A, B (x, y), C' in ['A', 'B (x, y)', 'C'].

    Kommas innerhalb von Klammern trennen nicht - sonst zerfaellt
    'Linux (Ubuntu/Debian, VPS)' in zwei unsinnige Haelften.
    """
    teile, tiefe, aktuell = [], 0, ''
    for z in wert:
        if z == '(':
            tiefe += 1
        elif z == ')':
            tiefe = max(0, tiefe - 1)
        if z == ',' and tiefe == 0:
            teile.append(aktuell.strip())
            aktuell = ''
        else:
            aktuell += z
    if aktuell.strip():
        teile.append(aktuell.strip())
    return teile


def _passt(teil, stellentext):
    """Kommt dieser Skill-Eintrag in der Anzeige vor?"""
    klein = (stellentext or '').lower()
    # Der Eintrag selbst ('Angular (17-19)') wird auf sein Stichwort
    # reduziert und ueber die bekannten Schreibweisen gesucht.
    kern = re.sub(r'\(.*?\)', '', teil).strip().lower()
    if not kern:
        return False
    for name, regex in KANN.items():
        if name.lower() in kern or kern in name.lower():
            if re.search(regex, klein):
                return True
    return kern in klein


def sortiere_skills(skills, stellentext):
    """Stellt die IT-Kenntnisse nach der Anzeige um.

    Kategorien mit den meisten Treffern stehen oben, innerhalb einer
    Kategorie stehen die geforderten Eintraege vorne. Reihenfolge ist das
    Einzige, was sich aendert - es kommt nichts dazu und nichts weg.
    """
    if not (stellentext or '').strip():
        return list(skills)

    neu = []
    for pos, (label, wert) in enumerate(skills):
        teile = _teile(wert)
        vorne = [t for t in teile if _passt(t, stellentext)]
        hinten = [t for t in teile if t not in vorne]
        neu.append((len(vorne), pos, label, ', '.join(vorne + hinten)))

    # Nach Trefferzahl absteigend, bei Gleichstand in urspruenglicher Folge.
    neu.sort(key=lambda z: (-z[0], z[1]))
    return [(label, wert) for _, _, label, wert in neu]


# ─── BESTAETIGTE KENNTNISSE EINHAENGEN ───────────────────────────────────────
def mit_eigenen(skills, variante, sprache='de', kategorien_de=None,
                eigene=None):
    """Haengt bestaetigte Zusatzkenntnisse in die passende Kategorie ein.

    Gespeichert wird immer die deutsche Kategorie. In der englischen Fassung
    heissen die Kategorien anders ("Automatisierung" -> "Automation"), stehen
    aber an derselben Stelle - deshalb wird ueber die Position zugeordnet.
    Passt nichts, bleibt der Eintrag draussen: lieber fehlt er, als dass er
    unter der falschen Ueberschrift steht.
    """
    eigene = lade_eigene() if eigene is None else eigene
    bestaetigt = eigene.get('bestaetigt', {})
    if not bestaetigt:
        return list(skills)

    namen = kategorien_de or [l for l, _ in skills]

    def sauber(t):
        return (t or '').replace('&amp;', '&').strip().lower()

    ergebnis = []
    for pos, (label, wert) in enumerate(skills):
        kanon = sauber(namen[pos] if pos < len(namen) else label)
        zusatz = []
        for name, eintrag in sorted(bestaetigt.items()):
            if sauber((eintrag.get('kategorie') or {}).get(variante)) != kanon:
                continue
            text = (eintrag.get('label_en' if sprache == 'en' else 'label')
                    or eintrag.get('label') or name)
            if text.lower() not in wert.lower():
                zusatz.append(text)
        ergebnis.append((label, ', '.join(_teile(wert) + zusatz)))
    return ergebnis


# ─── NACHFRAGEN ──────────────────────────────────────────────────────────────
def _frage(text):
    try:
        return input(text).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return ''


def frage_offene(stellentext, kategorien_je_variante):
    """Fragt die noch offenen Luecken ab und speichert die Antworten.

    Die Frage lautet bewusst nicht "soll ich das eintragen?", sondern "wo
    hast du damit gearbeitet?". Wer darauf keine Antwort hat, kann die
    Kenntnis auch im Vorstellungsgespraech nicht belegen - dann gehoert sie
    nicht in den Lebenslauf.
    """
    eigene = lade_eigene()
    _, _, offen = abgleich(stellentext, eigene)
    if not offen:
        print('Keine offenen Punkte – alles aus dieser Anzeige ist beantwortet.')
        return eigene

    print('%d Punkt(e) aus der Anzeige sind im Lebenslauf nicht belegt.' % len(offen))
    print('Fuer jeden gilt: nur aufnehmen, was du im Gespraech belegen kannst.')
    print('Antworten werden gespeichert und nicht erneut gefragt.')
    print('[Enter] ueberspringt und fragt beim naechsten Mal wieder.\n')

    geaendert = False
    for name in offen:
        print('─' * 60)
        # Gibt es ein eigenes Werkzeug fuer dieselbe Aufgabe, steht es
        # hier - das beantwortet oft schon, ob die Frage eine ist.
        e = VERWANDT.get(name)
        if e:
            print('  Du hast %s fuer %s%s.'
                  % (_und(e['habe']), e['gemeinsam'],
                     '' if e['naehe'] == 'nah' else ' (nur verwandt)'))
        antwort = _frage('%s – wo hast du damit gearbeitet? '
                         '(leer = spaeter, "nein" = kann ich nicht)\n> ' % name)
        if not antwort:
            continue
        if antwort.lower() in ('nein', 'n', 'no', 'kann ich nicht'):
            eigene['abgelehnt'][name] = {'seit': date.today().isoformat()}
            geaendert = True
            print('  -> als Luecke vermerkt, wird nicht mehr gefragt.\n')
            continue

        label = _frage('  Wie soll es im Lebenslauf heissen? [%s]\n  > ' % name) or name
        kategorie = {}
        for variante, liste in kategorien_je_variante.items():
            print('  Kategorie in der Variante "%s":' % variante)
            for nr, kat in enumerate(liste, 1):
                print('    %d) %s' % (nr, kat))
            print('    0) nicht anzeigen')
            wahl = _frage('  > ')
            if wahl.isdigit() and 1 <= int(wahl) <= len(liste):
                kategorie[variante] = liste[int(wahl) - 1]
        eigene['bestaetigt'][name] = {
            'label': label,
            'label_en': label,
            'kategorie': kategorie,
            'beleg': antwort,
            'seit': date.today().isoformat(),
        }
        geaendert = True
        print('  -> aufgenommen.\n')

    if geaendert:
        speichere_eigene(eigene)
        print('Gespeichert in %s' % EIGENE_DATEI)
        print('Der naechste Lebenslauf enthaelt die Ergaenzungen.')
    return eigene


# ─── VERWANDTES NUTZBAR MACHEN ───────────────────────────────────────────────
def _und(teile):
    """['a', 'b', 'c'] -> 'a, b und c'"""
    teile = list(teile)
    if len(teile) < 2:
        return ''.join(teile)
    return ', '.join(teile[:-1]) + ' und ' + teile[-1]


def verwandte(luecken, naehe=None):
    """Zu welchen Luecken gibt es ein Werkzeug im Profil, das dasselbe tut?"""
    gefunden = []
    for name in luecken:
        eintrag = VERWANDT.get(name)
        if not eintrag:
            continue
        if naehe and eintrag['naehe'] != naehe:
            continue
        gefunden.append((name, eintrag))
    return gefunden


def brueckensaetze(stellentext):
    """Fertige Saetze fuers Anschreiben - nur fuer nahe Verwandtschaft.

    Der Satz nennt zuerst ehrlich, was fehlt, und dann das Eigene. So steht
    im Anschreiben, was ein Stichwortfilter im Lebenslauf nicht findet, ohne
    dass irgendwo etwas Falsches behauptet wird.
    """
    _, luecken, _ = abgleich(stellentext)
    # Nennt die Anzeige Jenkins UND GitLab CI, waere das zweimal derselbe
    # Satz. Gleiche Aufgabe und gleiche eigene Werkzeuge -> ein Satz.
    gruppen = {}
    for name, e in verwandte(luecken, naehe='nah'):
        gruppen.setdefault((e['gemeinsam'], tuple(e['habe'])), []).append(e['name'])
    return ['%s habe ich nicht im Einsatz; %s loese ich mit %s.'
            % (_und(namen), gemeinsam, _und(habe))
            for (gemeinsam, habe), namen in gruppen.items()]


def mit_vergleichen(skills, stellentext, hoechstens=2):
    """Haengt "(vergleichbar: X)" an die Kategorie mit dem eigenen Werkzeug.

    Ausdruecklich als Vergleich gekennzeichnet: im Lebenslauf steht weiter,
    womit tatsaechlich gearbeitet wird. Bewusst auf zwei begrenzt - mehr
    liest sich wie eine Rechtfertigung.
    """
    if not (stellentext or '').strip():
        return list(skills)

    offen = verwandte(abgleich(stellentext)[1], naehe='nah')[:hoechstens]
    if not offen:
        return list(skills)

    ergebnis, vergeben = [], set()
    for label, wert in skills:
        klein = wert.lower()
        passend = [e['name'] for name, e in offen
                   if name not in vergeben
                   and any(h.lower() in klein for h in e['habe'])]
        for name, e in offen:
            if e['name'] in passend:
                vergeben.add(name)
        if passend:
            wert = '%s (vergleichbar: %s)' % (wert, ', '.join(passend))
        ergebnis.append((label, wert))
    return ergebnis


# ─── BERICHT ─────────────────────────────────────────────────────────────────
def bericht(stellentext):
    """Mehrzeiliger Text zum Mitlesen - fuer die Oberflaeche oder das Terminal."""
    treffer, luecken, offen = abgleich(stellentext)
    zeilen = []
    zeilen.append('TREFFER – in deinem Profil belegt (%d)' % len(treffer))
    zeilen.append('  ' + (', '.join(sorted(treffer)) if treffer else '–'))
    zeilen.append('')
    zeilen.append('LÜCKEN – in der Anzeige gefordert, bei dir nicht belegt (%d)'
                  % len(luecken))
    zeilen.append('  ' + (', '.join(luecken) if luecken else '–'))
    nah = verwandte(luecken, naehe='nah')
    fern = verwandte(luecken, naehe='entfernt')
    if nah:
        zeilen.append('')
        zeilen.append('ANDERES WERKZEUG, GLEICHE AUFGABE (%d)' % len(nah))
        for name, e in nah:
            zeilen.append('  %s – du hast %s (%s)'
                          % (e['name'], _und(e['habe']), e['gemeinsam']))
        zeilen.append('')
        zeilen.append('  Das ist keine Luecke, nur eine andere Beschriftung.')
        zeilen.append('  Saetze fuers Anschreiben:')
        for satz in brueckensaetze(stellentext):
            zeilen.append('      ' + satz)
    if fern:
        zeilen.append('')
        zeilen.append('VERWANDT, ABER NICHT DASSELBE (%d)' % len(fern))
        for name, e in fern:
            zeilen.append('  %s – am naechsten dran: %s (%s)'
                          % (e['name'], _und(e['habe']), e['gemeinsam']))
        zeilen.append('  Nicht als gleichwertig verkaufen - das faellt auf.')
    if luecken:
        zeilen.append('')
        zeilen.append('  Nichts davon kommt automatisch in den Lebenslauf.')
    if offen:
        zeilen.append('')
        zeilen.append('  %d davon noch nicht beantwortet: %s'
                      % (len(offen), ', '.join(offen)))
        zeilen.append('  Kannst du etwas davon doch belegen? Dann:')
        zeilen.append('      py stellen_abgleich.py <anzeige.txt> --fragen')
        zeilen.append('  Einmal beantwortet, gilt es fuer alle Bewerbungen.')
    return '\n'.join(zeilen)


def _kategorien_je_variante():
    """Die Kategorien der IT-Kenntnisse, direkt aus dem Lebenslauf gelesen."""
    try:
        import generate_lebenslauf as lebenslauf
    except ImportError:
        return {}
    return {
        variante: [l.replace('&amp;', '&')
                   for l, _ in lebenslauf.INHALT['de'][variante]['skills']]
        for variante in lebenslauf.VARIANTEN
    }


def main():
    argumente = [a for a in sys.argv[1:] if not a.startswith('--')]
    fragen = '--fragen' in sys.argv

    if argumente:
        with io.open(argumente[0], encoding='utf-8') as f:
            text = f.read()
    else:
        text = sys.stdin.read()

    print(bericht(text))
    if fragen:
        print()
        frage_offene(text, _kategorien_je_variante())


if __name__ == '__main__':
    main()
