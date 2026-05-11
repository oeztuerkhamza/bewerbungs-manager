#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Eingang ↔ Sonuç Abgleich
bewerbungen/ klasörleri ile Bewerbungen.csv arasındaki eşleştirme
"""

import os
import csv
import json
import re
from difflib import SequenceMatcher

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROFILES_DIR = os.path.join(SCRIPT_DIR, 'bewerbungen')
CSV_FILE = os.path.join(SCRIPT_DIR, 'Bewerbungen.csv')


def normalize(text):
    """Normalize text for fuzzy matching."""
    text = text.lower().strip()
    # Common replacements
    replacements = {
        'ä': 'ae', 'ö': 'oe', 'ü': 'ue', 'ß': 'ss',
        'é': 'e', 'è': 'e', '&': 'und',
        '_': ' ', '-': ' ', '/': ' ', '.': ' ',
        '(': '', ')': '', ',': '', "'": '',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def extract_firma_from_folder(folder_name):
    """Extract company name from folder name (before the ' - ')."""
    parts = folder_name.split(' - ', 1)
    return parts[0].strip() if parts else folder_name


def extract_position_from_folder(folder_name):
    """Extract position from folder name (after the ' - ')."""
    parts = folder_name.split(' - ', 1)
    return parts[1].strip() if len(parts) > 1 else ''


def similarity(a, b):
    """Calculate similarity ratio between two strings."""
    return SequenceMatcher(None, normalize(a), normalize(b)).ratio()


def load_csv():
    """Load CSV entries."""
    entries = []
    with open(CSV_FILE, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Try both possible header variants
            firma = (row.get('Şirket / Kurum') or row.get('\ufeffŞirket / Kurum') or '').strip()
            position = (row.get('Pozisyon / Konu') or '').strip()
            durum = (row.get('Durum / Sonuç') or '').strip()
            tarih = (row.get('Tarih') or '').strip()
            entries.append({
                'firma': firma,
                'position': position,
                'durum': durum,
                'tarih': tarih,
            })
    return entries


def load_folders():
    """Load folder names from bewerbungen/."""
    folders = []
    for item in sorted(os.listdir(PROFILES_DIR)):
        full_path = os.path.join(PROFILES_DIR, item)
        if os.path.isdir(full_path):
            folders.append({
                'folder': item,
                'firma': extract_firma_from_folder(item),
                'position': extract_position_from_folder(item),
            })
    return folders


def match_entries(folders, csv_entries):
    """Match folders with CSV entries."""
    matched = []
    unmatched_folders = []
    used_csv = set()

    for folder in folders:
        best_match = None
        best_score = 0

        for i, entry in enumerate(csv_entries):
            if i in used_csv:
                continue

            # Compare firma names
            firma_score = similarity(folder['firma'], entry['firma'])

            # Compare positions
            pos_score = similarity(folder['position'], entry['position'])

            # Combined score (firma more important)
            combined = firma_score * 0.6 + pos_score * 0.4

            if combined > best_score:
                best_score = combined
                best_match = (i, entry)

        if best_match and best_score >= 0.35:
            idx, entry = best_match
            used_csv.add(idx)
            matched.append({
                'folder_firma': folder['firma'],
                'folder_position': folder['position'],
                'csv_firma': entry['firma'],
                'csv_position': entry['position'],
                'durum': entry['durum'],
                'tarih': entry['tarih'],
                'score': best_score,
            })
        else:
            unmatched_folders.append(folder)

    unmatched_csv = [csv_entries[i] for i in range(len(csv_entries)) if i not in used_csv]
    return matched, unmatched_folders, unmatched_csv


def print_section(title, char='═'):
    width = 100
    print(f"\n{char * width}")
    print(f"  {title}")
    print(f"{char * width}")


def main():
    folders = load_folders()
    csv_entries = load_csv()

    matched, unmatched_folders, unmatched_csv = match_entries(folders, csv_entries)

    # ── SUMMARY ──
    print_section("EINGANG ↔ SONUÇ ABGLEICH - ÖZET")
    print(f"  📂 bewerbungen/ klasör sayısı : {len(folders)}")
    print(f"  📋 CSV kayıt sayısı           : {len(csv_entries)}")
    print(f"  ✅ Eşleşen                     : {len(matched)}")
    print(f"  ❌ Klasör var, CSV yok          : {len(unmatched_folders)}")
    print(f"  ❌ CSV var, Klasör yok          : {len(unmatched_csv)}")

    # ── MATCHED ──
    print_section("✅ EŞLEŞEN BAŞVURULAR (Klasör ↔ CSV)")
    # Group by status
    status_groups = {}
    for m in matched:
        d = m['durum']
        status_groups.setdefault(d, []).append(m)

    for durum, items in sorted(status_groups.items()):
        print(f"\n  ── {durum} ({len(items)}) ──")
        for m in items:
            score_pct = int(m['score'] * 100)
            print(f"    [{score_pct:3d}%] {m['csv_firma'][:40]:<40} | {m['csv_position'][:50]:<50} | {m['tarih']}")

    # ── UNMATCHED FOLDERS ──
    if unmatched_folders:
        print_section("❌ KLASÖR VAR AMA CSV'DE YOK (Eingang eksik)")
        for f in unmatched_folders:
            print(f"    📂 {f['firma'][:40]:<40} | {f['position'][:60]}")

    # ── UNMATCHED CSV ──
    if unmatched_csv:
        print_section("❌ CSV'DE VAR AMA KLASÖR YOK (Sonuç var, Eingang yok)")
        for e in unmatched_csv:
            print(f"    📋 {e['firma'][:40]:<40} | {e['position'][:50]:<50} | {e['durum']:<25} | {e['tarih']}")

    print(f"\n{'═' * 100}")


if __name__ == '__main__':
    main()
