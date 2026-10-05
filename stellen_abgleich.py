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

import re
import sys

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


def _treffer(text, muster):
    """Welche Eintraege aus 'muster' kommen im Text vor?"""
    klein = (text or '').lower()
    gefunden = []
    for name, regex in muster.items():
        if re.search(regex, klein):
            gefunden.append(name)
    return gefunden


def abgleich(stellentext):
    """Gibt (treffer, luecken) fuer eine Stellenanzeige zurueck."""
    return (_treffer(stellentext, KANN),
            _treffer(stellentext, KANN_NICHT))


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


# ─── BERICHT ─────────────────────────────────────────────────────────────────
def bericht(stellentext):
    """Mehrzeiliger Text zum Mitlesen - fuer die Oberflaeche oder das Terminal."""
    treffer, luecken = abgleich(stellentext)
    zeilen = []
    zeilen.append('TREFFER – in deinem Profil belegt (%d)' % len(treffer))
    zeilen.append('  ' + (', '.join(treffer) if treffer else '–'))
    zeilen.append('')
    zeilen.append('LÜCKEN – in der Anzeige gefordert, bei dir nicht belegt (%d)'
                  % len(luecken))
    zeilen.append('  ' + (', '.join(luecken) if luecken else '–'))
    if luecken:
        zeilen.append('')
        zeilen.append('  Diese Punkte kommen NICHT automatisch in den Lebenslauf.')
        zeilen.append('  Entweder im Anschreiben ansprechen (vergleichbare')
        zeilen.append('  Erfahrung benennen) oder stehen lassen.')
    return '\n'.join(zeilen)


def main():
    if len(sys.argv) > 1:
        with open(sys.argv[1], encoding='utf-8') as f:
            text = f.read()
    else:
        text = sys.stdin.read()
    print(bericht(text))


if __name__ == '__main__':
    main()
