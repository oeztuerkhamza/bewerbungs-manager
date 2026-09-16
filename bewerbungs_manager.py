#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bewerbungs-Manager – GUI zum Erstellen von Lebenslauf & Anschreiben
Hamza Öztürk · 10.03.2026
"""

import json
import math
import os
import csv
import re
import imaplib
import smtplib
import email
from email.header import decode_header
from email.utils import parsedate_to_datetime, parseaddr
from email.message import EmailMessage
import html
import mimetypes
import subprocess
import sys
import threading
import time
import tkinter as tk
from datetime import date, timedelta
from tkinter import filedialog, messagebox, ttk

try:
    from openpyxl import Workbook, load_workbook
except Exception:
    Workbook = None
    load_workbook = None

# ─── MODULE IMPORTS ──────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

def _ensure_reportlab():
    try:
        import reportlab  # noqa: F401
        return
    except Exception:
        pass

    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'reportlab'])
    except Exception as exc:
        raise RuntimeError(
            'ReportLab not installed and auto-install failed. '
            'Please run: pip install reportlab'
        ) from exc

    import reportlab  # noqa: F401


try:
    import generate_anschreiben as gen_a
    import generate_lebenslauf as gen_l
    import generate_kapak as gen_k
except Exception:
    _ensure_reportlab()
    import generate_anschreiben as gen_a
    import generate_lebenslauf as gen_l
    import generate_kapak as gen_k

import ki_assistent as ki
import initiativ_bewerbung as initiativ

try:
    import tkintermapview
    MAP_AVAILABLE = True
except Exception:
    tkintermapview = None
    MAP_AVAILABLE = False

try:
    from PyPDF2 import PdfReader, PdfWriter, Transformation, PageObject
    PDF_LIBS_LOADED = True
except Exception:
    PdfReader, PdfWriter, Transformation, PageObject = None, None, None, None
    PDF_LIBS_LOADED = False

# ─── CONSTANTS ───────────────────────────────────────────────────────────────
PROFILES_DIR  = os.path.join(SCRIPT_DIR, 'bewerbungen')
OUTPUT_DIR    = SCRIPT_DIR
APPLICATIONS_CSV = os.path.join(SCRIPT_DIR, 'Bewerbungen.csv')
APPLICATIONS_XLSX = os.path.join(SCRIPT_DIR, 'Bewerbungen.xlsx')
IMAP_SETTINGS_FILE = os.path.join(SCRIPT_DIR, '.imap_settings.json')
SMTP_SETTINGS_FILE = os.path.join(SCRIPT_DIR, '.smtp_settings.json')
INITIATIV_SENT_FILE = os.path.join(SCRIPT_DIR, '.initiativ_sent.json')
API_KEY_FILE  = os.path.join(SCRIPT_DIR, '.claude_api_key')
MAIL_PDF_DIR = os.path.join(SCRIPT_DIR, 'mail_pdfs')
ZEUGNIS_DIR = os.path.join(SCRIPT_DIR, 'Zeugnis')
# Zeugnis-Anhänge werden NICHT mehr über exakte (fehleranfällige) Dateinamen,
# sondern per Schlüsselwort im Zeugnis-Ordner aufgelöst. Reihenfolge =
# Anhang-Reihenfolge im finalen Bewerbungs-PDF.
_ZEUGNIS_KEYWORDS = [
    ('arbeitszeugnis',),
    ('ihk',),
    ('berufschule', 'berufsschule'),
    ('data_analyst', 'zertifikat', 'zertifikate'),
    ('zeugnisse',),
]
# ─── PREMIUM COLOR PALETTE ───────────────────────────────────────────────────
NAVY       = '#0D1B2A'
NAVY_MID   = '#1B2838'
NAVY_LIGHT = '#274060'
WHITE      = '#FFFFFF'
BG         = '#F0F2F5'
BG2        = '#E8ECF1'
BG_CARD    = '#FFFFFF'
FG         = '#1E293B'
FG_LIGHT   = '#475569'
GRAY       = '#94A3B8'
ACCENT     = '#C9A84C'      # premium gold
ACCENT_HVR = '#B8963F'
ACCENT2    = '#2563EB'       # action blue
ACCENT2_HVR= '#1D4ED8'
SUCCESS    = '#059669'
CARD_BD    = '#E2E8F0'
DIVIDER    = '#CBD5E1'
FONT       = 'Segoe UI'
FONT_MONO  = 'Cascadia Code'


# ─── HELPER ──────────────────────────────────────────────────────────────────
def today_de():
    """Return today's date as DD.MM.YYYY."""
    d = date.today()
    return f'{d.day:02d}.{d.month:02d}.{d.year}'


def safe_filename(text):
    """Turn arbitrary text into a safe filename component."""
    keep = set('abcdefghijklmnopqrstuvwxyz0123456789_-')
    return ''.join(c if c.lower() in keep else '_' for c in text).strip('_')[:60]


# ─── APPLICATION ─────────────────────────────────────────────────────────────
class BewerbungsApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Bewerbungs-Manager  ·  Premium Suite')
        self.configure(bg=BG)
        self.minsize(1080, 860)
        self.resizable(True, True)

        # Nicht-Widget-Felder aus der KI-Antwort (z.B. highlights), die
        # sonst beim _get_config()/_set_config()-Umweg verloren gingen.
        self._extra_cfg = {}
        # Registry aller scrollbaren Canvas-Bereiche. Ein einziger globaler
        # Mausrad-Handler scrollt jeweils den Bereich unter dem Mauszeiger.
        self._scroll_canvases = set()
        # Schützt die gemeinsamen Bewerbungs-Tabellen (CSV/XLSX) vor
        # gleichzeitigen Schreibzugriffen aus mehreren Hintergrund-Threads.
        self._table_lock = threading.Lock()

        # Centre on screen
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        w, h = 1140, 900
        self.geometry(f'{w}x{h}+{(sw-w)//2}+{(sh-h)//2}')

        self._build_ui()
        self._load_defaults()

        # Ein globaler Mausrad-Handler für alle scrollbaren Tabs.
        self.bind_all('<MouseWheel>', self._on_mousewheel)

    # ── SCROLL-HELFER ─────────────────────────────────────────────────────────
    def _make_scrollable(self, parent):
        """Erzeugt einen vertikal scrollbaren Bereich, gibt das Inhalts-Frame
        zurück und registriert den Canvas für das globale Mausrad-Scrollen."""
        canvas = tk.Canvas(parent, bg=BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient='vertical',
                                  command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg=BG)

        window_id = canvas.create_window((0, 0), window=scroll_frame,
                                         anchor='nw')

        scroll_frame.bind(
            '<Configure>',
            lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        # Inhalt immer auf Canvas-Breite strecken (verhindert horizontales
        # Verrutschen / abgeschnittene Karten).
        canvas.bind(
            '<Configure>',
            lambda e: canvas.itemconfigure(window_id, width=e.width))

        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        self._scroll_canvases.add(canvas)
        # Beim Zerstören wieder austragen, damit keine toten Referenzen bleiben.
        canvas.bind('<Destroy>',
                    lambda e: self._scroll_canvases.discard(canvas), add='+')
        return scroll_frame

    def _on_mousewheel(self, e):
        """Scrollt den scrollbaren Canvas unter dem Mauszeiger.

        Liegt der Zeiger über einem anderen Widget (z.B. Treeview/Listbox),
        passiert hier nichts – dessen eigenes Scrollverhalten bleibt aktiv.
        """
        w = self.winfo_containing(e.x_root, e.y_root)
        while w is not None:
            if w in self._scroll_canvases:
                w.yview_scroll(int(-1 * (e.delta / 120)), 'units')
                return
            w = getattr(w, 'master', None)

    # ── UI BUILDING ──────────────────────────────────────────────────────────
    def _build_ui(self):
        style = ttk.Style(self)
        style.theme_use('clam')

        # ── Premium Button Styles ──
        style.configure('Gold.TButton',
                        background=ACCENT, foreground=NAVY,
                        font=(FONT, 10, 'bold'), padding=(16, 8),
                        borderwidth=0)
        style.map('Gold.TButton',
                  background=[('active', ACCENT_HVR), ('pressed', ACCENT_HVR)],
                  foreground=[('active', WHITE)])

        style.configure('Navy.TButton',
                        background=NAVY, foreground=WHITE,
                        font=(FONT, 10, 'bold'), padding=(16, 8),
                        borderwidth=0)
        style.map('Navy.TButton',
                  background=[('active', NAVY_LIGHT), ('pressed', NAVY_LIGHT)])

        style.configure('Accent.TButton',
                        background=ACCENT2, foreground=WHITE,
                        font=(FONT, 10), padding=(12, 7),
                        borderwidth=0)
        style.map('Accent.TButton',
                  background=[('active', ACCENT2_HVR), ('pressed', ACCENT2_HVR)])

        style.configure('Ghost.TButton',
                        background=BG, foreground=FG,
                        font=(FONT, 10), padding=(12, 7),
                        borderwidth=1, relief='solid')
        style.map('Ghost.TButton',
                  background=[('active', CARD_BD), ('pressed', CARD_BD)])

        # ── Label Styles ──
        style.configure('TLabel', background=BG, foreground=FG,
                        font=(FONT, 10))
        style.configure('Header.TLabel', background=NAVY, foreground=WHITE,
                        font=(FONT, 15, 'bold'), padding=(14, 10))
        style.configure('Section.TLabel', background=BG, foreground=NAVY,
                        font=(FONT, 11, 'bold'))
        style.configure('SectionCard.TLabel', background=WHITE, foreground=NAVY,
                        font=(FONT, 11, 'bold'))
        style.configure('CardLabel.TLabel', background=WHITE, foreground=FG,
                        font=(FONT, 10))
        style.configure('Subtle.TLabel', background=BG, foreground=GRAY,
                        font=(FONT, 9))

        # ── Frame Styles ──
        style.configure('TFrame', background=BG)
        style.configure('Card.TFrame', background=WHITE)
        style.configure('NavyFrame.TFrame', background=NAVY)

        # ── Notebook (Premium Tabs) ──
        style.configure('TNotebook', background=BG, borderwidth=0)
        style.configure('TNotebook.Tab',
                        font=(FONT, 10, 'bold'),
                        padding=(20, 10),
                        background=BG2,
                        foreground=FG_LIGHT)
        style.map('TNotebook.Tab',
                  background=[('selected', WHITE)],
                  foreground=[('selected', NAVY)],
                  expand=[('selected', [0, 0, 0, 2])])

        # ── Entry Style ──
        style.configure('TEntry', font=(FONT, 10), padding=6)

        # ── Separator ──
        style.configure('Gold.TSeparator', background=ACCENT)

        # ═══ HEADER (Gradient Canvas) ═══
        hdr_h = 64
        hdr = tk.Canvas(self, height=hdr_h, bg=NAVY, highlightthickness=0)
        hdr.pack(fill='x')
        # Draw subtle gradient stripe at bottom
        for i in range(6):
            alpha_color = self._blend(NAVY, ACCENT, i / 5)
            hdr.create_rectangle(0, hdr_h - 6 + i, 2000, hdr_h - 5 + i,
                                 fill=alpha_color, outline='')
        # Logo / Title
        hdr.create_text(24, hdr_h // 2 - 2, anchor='w',
                        text='◆  BEWERBUNGS-MANAGER',
                        fill=WHITE, font=(FONT, 16, 'bold'))
        hdr.create_text(320, hdr_h // 2 - 2, anchor='w',
                        text='Premium Suite',
                        fill=ACCENT, font=(FONT, 11))

        # ── Gold accent line ──
        tk.Frame(self, bg=ACCENT, height=3).pack(fill='x')

        # ═══ STATUS BAR ═══  (pack bottom elements FIRST so notebook doesn't eat all space)
        status_frame = tk.Frame(self, bg=NAVY, height=28)
        status_frame.pack(fill='x', side='bottom')
        status_frame.pack_propagate(False)
        self._status_var = tk.StringVar(value='◆  Bereit.')
        tk.Label(status_frame, textvariable=self._status_var,
                 bg=NAVY, fg=ACCENT,
                 font=(FONT, 9), anchor='w', padx=12).pack(
                     side='left', fill='both', expand=True)
        tk.Label(status_frame, text='v2.0  Premium',
                 bg=NAVY, fg=GRAY,
                 font=(FONT, 8), anchor='e', padx=12).pack(side='right')

        # ═══ BOTTOM ACTION BAR ═══
        bar = tk.Frame(self, bg=NAVY_MID, height=66)
        bar.pack(fill='x', side='bottom', pady=(6, 0))
        bar.pack_propagate(False)

        inner = tk.Frame(bar, bg=NAVY_MID)
        inner.pack(expand=True)

        ttk.Button(inner, text='📄  Lebenslauf',
                   style='Gold.TButton',
                   command=self._gen_lebenslauf).pack(
                       side='left', padx=5, pady=12)
        ttk.Button(inner, text='✉  Anschreiben',
                   style='Gold.TButton',
                   command=self._gen_anschreiben).pack(
                       side='left', padx=5, pady=12)
        ttk.Button(inner, text='📑  Beide erstellen',
                   style='Gold.TButton',
                   command=self._gen_both).pack(
                       side='left', padx=5, pady=12)
        ttk.Button(inner, text='📦  Bewerbungs-PDF',
                   style='Navy.TButton',
                   command=self._gen_bewerbung_pdf).pack(
                       side='left', padx=5, pady=12)
        ttk.Button(inner, text='📂  Ordner öffnen',
                   style='Ghost.TButton',
                   command=self._open_folder).pack(
                       side='left', padx=5, pady=12)

        # ═══ NOTEBOOK ═══
        nb = ttk.Notebook(self)
        nb.pack(fill='both', expand=True, padx=16, pady=(12, 0))

        self._tab_ki        = self._make_tab(nb, '🤖  KI-Assistent')
        self._tab_stelle    = self._make_tab(nb, '📋  Stelle & Firma')
        self._tab_anschr    = self._make_tab(nb, '✍  Anschreiben')
        self._tab_email     = self._make_tab(nb, '📧  E-Mail')
        self._tab_initiativ = self._make_tab(nb, '📮  Initiativbewerbung')
        self._tab_uebersicht = self._make_tab(nb, '📊  Übersicht')
        self._tab_profile   = self._make_tab(nb, '👤  Profile')

        self._build_ki_tab(self._tab_ki)
        self._build_stelle_tab(self._tab_stelle)
        self._build_anschreiben_tab(self._tab_anschr)
        self._build_email_tab(self._tab_email)
        self._build_initiativ_tab(self._tab_initiativ)
        self._build_uebersicht_tab(self._tab_uebersicht)
        self._build_profile_tab(self._tab_profile)
        self._nb = nb

    @staticmethod
    def _blend(c1, c2, t):
        """Linearly blend two hex colours; t in [0, 1]."""
        r1, g1, b1 = int(c1[1:3], 16), int(c1[3:5], 16), int(c1[5:7], 16)
        r2, g2, b2 = int(c2[1:3], 16), int(c2[3:5], 16), int(c2[5:7], 16)
        r = int(r1 + (r2 - r1) * t)
        g = int(g1 + (g2 - g1) * t)
        b = int(b1 + (b2 - b1) * t)
        return f'#{r:02x}{g:02x}{b:02x}'

    def _make_tab(self, nb, title):
        frame = ttk.Frame(nb, style='TFrame')
        nb.add(frame, text=f'  {title}  ')
        return frame

    # ── CARD CONTAINER HELPER ────────────────────────────────────────────
    def _make_card(self, parent, title=None, padx=16, pady=8):
        """Create a white card container with optional title."""
        outer = tk.Frame(parent, bg=BG)
        outer.pack(fill='x', padx=padx, pady=pady)
        # Card with border
        card = tk.Frame(outer, bg=WHITE, highlightbackground=CARD_BD,
                        highlightthickness=1, padx=16, pady=12)
        card.pack(fill='x')
        if title:
            tk.Label(card, text=title, bg=WHITE, fg=NAVY,
                     font=(FONT, 11, 'bold'), anchor='w').pack(
                         anchor='w', pady=(0, 8))
            tk.Frame(card, bg=DIVIDER, height=1).pack(fill='x', pady=(0, 8))
        return card

    def _make_card_grid(self, parent, title=None, padx=16, pady=8):
        """Create a white card container using grid layout internally."""
        outer = tk.Frame(parent, bg=BG)
        # Card with border
        card = tk.Frame(outer, bg=WHITE, highlightbackground=CARD_BD,
                        highlightthickness=1, padx=16, pady=12)
        card.pack(fill='x')
        if title:
            tk.Label(card, text=title, bg=WHITE, fg=NAVY,
                     font=(FONT, 11, 'bold'), anchor='w').grid(
                         row=0, column=0, columnspan=3, sticky='w', pady=(0, 4))
            tk.Frame(card, bg=DIVIDER, height=1).grid(
                row=1, column=0, columnspan=3, sticky='ew', pady=(0, 8))
        return outer, card

    # ── TAB 0: KI-ASSISTENT ─────────────────────────────────────────────
    def _build_ki_tab(self, parent):
        scroll_frame = self._make_scrollable(parent)

        # ── Description card ──
        desc_card = self._make_card(scroll_frame, padx=16, pady=(12, 4))
        tk.Label(desc_card, text=(
            'Stellenanzeige einfügen (URL oder Text) \u2192 '
            'Claude analysiert die Anforderungen und erstellt '
            'maßgeschneiderte Bewerbungsunterlagen auf Basis '
            'deines Lebenslaufs.'),
            bg=WHITE, fg=FG_LIGHT, font=(FONT, 10),
            wraplength=850, justify='left', anchor='w').pack(anchor='w')

        # ── API Key Card ──
        api_outer, api_card = self._make_card_grid(scroll_frame, '🔑  CLAUDE API KEY', padx=16, pady=4)
        api_outer.pack(fill='x', padx=16, pady=4)

        row = 2
        tk.Label(api_card, text='API Key', bg=WHITE, fg=FG,
                 font=(FONT, 10)).grid(
            row=row, column=0, sticky='e', padx=(0, 8), pady=4)
        self._api_key_var = tk.StringVar(value=self._load_api_key())
        key_entry = ttk.Entry(api_card, textvariable=self._api_key_var,
                              width=60, font=(FONT, 10), show='•')
        key_entry.grid(row=row, column=1, sticky='w', padx=(0, 8), pady=4)
        ttk.Button(api_card, text='Speichern', style='Accent.TButton',
                   command=self._save_api_key).grid(
                       row=row, column=2, sticky='w', padx=4, pady=4)
        row += 1

        self._show_key = tk.BooleanVar(value=False)
        def _toggle_key():
            key_entry.configure(show='' if self._show_key.get() else '•')
        tk.Checkbutton(api_card, text='Key anzeigen', variable=self._show_key,
                       command=_toggle_key, bg=WHITE, fg=FG,
                       font=(FONT, 9), activebackground=WHITE,
                       selectcolor=WHITE).grid(
                           row=row, column=1, sticky='w', padx=0, pady=0)

        # ── Stellenanzeige Card ──
        job_outer, job_card = self._make_card_grid(scroll_frame, '📋  STELLENANZEIGE', padx=16, pady=4)
        job_outer.pack(fill='x', padx=16, pady=4)

        row = 2
        tk.Label(job_card, text='URL', bg=WHITE, fg=FG,
                 font=(FONT, 10)).grid(
            row=row, column=0, sticky='e', padx=(0, 8), pady=4)
        self._job_url_var = tk.StringVar()
        ttk.Entry(job_card, textvariable=self._job_url_var, width=70,
                  font=(FONT, 10)).grid(
                      row=row, column=1, columnspan=2, sticky='w',
                      padx=(0, 12), pady=4)
        row += 1

        tk.Label(job_card, text='oder Stellentext direkt einfügen:',
                 bg=WHITE, fg=FG_LIGHT, font=(FONT, 10)).grid(
                      row=row, column=0, columnspan=3, sticky='w',
                      padx=0, pady=(8, 2))
        row += 1
        self._job_text_widget = tk.Text(
            job_card, height=10, width=95, font=(FONT, 10),
            wrap='word', bg='#F8FAFC', fg=FG, relief='solid',
            borderwidth=1, highlightbackground=CARD_BD,
            highlightthickness=0, padx=8, pady=6)
        self._job_text_widget.grid(
            row=row, column=0, columnspan=3, sticky='we',
            padx=0, pady=(0, 6))

        # ── Extra Instructions Card ──
        extra_outer, extra_card = self._make_card_grid(scroll_frame, '💡  ZUSÄTZLICHE HINWEISE', padx=16, pady=4)
        extra_outer.pack(fill='x', padx=16, pady=4)

        row = 2
        self._extra_instr_widget = tk.Text(
            extra_card, height=3, width=95, font=(FONT, 10),
            wrap='word', bg='#F8FAFC', fg=FG, relief='solid',
            borderwidth=1, highlightbackground=CARD_BD,
            highlightthickness=0, padx=8, pady=6)
        self._extra_instr_widget.insert('1.0',
            'z.B.: Betone Docker-Erfahrung stärker, '
            'erwähne Remote-Bereitschaft...')
        self._extra_instr_widget.grid(
            row=row, column=0, columnspan=3, sticky='we',
            padx=0, pady=(0, 6))

        # ── Generate Buttons Card ──
        btn_card = self._make_card(scroll_frame, padx=16, pady=4)
        btn_inner = tk.Frame(btn_card, bg=WHITE)
        btn_inner.pack()
        ttk.Button(btn_inner,
                   text='🤖  KI-Bewerbung generieren',
                   style='Gold.TButton',
                   command=self._ki_generate).pack(side='left', padx=6)
        ttk.Button(btn_inner,
                   text='🤖 + 📄  Generieren & PDFs erstellen',
                   style='Navy.TButton',
                   command=self._ki_generate_and_pdf).pack(side='left', padx=6)

        # ── Log Card ──
        log_outer, log_card = self._make_card_grid(scroll_frame, '📊  LOG', padx=16, pady=(4, 12))
        log_outer.pack(fill='x', padx=16, pady=(4, 12))

        self._ki_log = tk.Text(
            log_card, height=8, width=95, font=(FONT_MONO, 9),
            wrap='word', bg='#0F172A', fg='#E2E8F0', relief='flat',
            borderwidth=0, padx=10, pady=8, state='disabled',
            insertbackground='#E2E8F0')
        self._ki_log.grid(row=2, column=0, columnspan=3, sticky='we',
                          padx=0, pady=(0, 4))

    def _ki_section(self, parent, title, row):
        lbl = tk.Label(parent, text=title, bg=WHITE, fg=NAVY,
                       font=(FONT, 11, 'bold'))
        lbl.grid(row=row, column=0, columnspan=3, sticky='w',
                 padx=12, pady=(14, 4))
        return row + 1

    def _log(self, msg):
        # Tkinter ist nicht thread-safe: Aufrufe aus Worker-Threads in den
        # UI-Thread marshallen.
        if threading.current_thread() is not threading.main_thread():
            self.after(0, lambda m=msg: self._log(m))
            return
        self._ki_log.configure(state='normal')
        self._ki_log.insert('end', msg + '\n')
        self._ki_log.see('end')
        self._ki_log.configure(state='disabled')
        self.update_idletasks()

    def _clear_log(self):
        self._ki_log.configure(state='normal')
        self._ki_log.delete('1.0', 'end')
        self._ki_log.configure(state='disabled')

    # ── API KEY PERSISTENCE ─────────────────────────────────────────────
    @staticmethod
    def _load_api_key():
        # 1) Umgebungsvariable hat Vorrang (GitHub Secret / .env)
        env_key = os.environ.get('ANTHROPIC_API_KEY', '').strip()
        if env_key:
            return env_key
        # 2) Fallback: lokale Datei (wird nicht ins Repository eingecheckt)
        if os.path.isfile(API_KEY_FILE):
            with open(API_KEY_FILE, 'r', encoding='utf-8') as f:
                return f.read().strip()
        return ''

    def _save_api_key(self):
        key = self._api_key_var.get().strip()
        with open(API_KEY_FILE, 'w', encoding='utf-8') as f:
            f.write(key)
        self._status('✓  API Key gespeichert.')

    # ── KI GENERATION ───────────────────────────────────────────────────
    def _ki_generate(self, then_pdf=False):
        api_key = self._api_key_var.get().strip()
        if not api_key:
            messagebox.showwarning('API Key fehlt',
                                  'Bitte zuerst einen Claude API Key eingeben.')
            return

        url = self._job_url_var.get().strip()
        pasted = self._job_text_widget.get('1.0', 'end-1c').strip()
        extra = self._extra_instr_widget.get('1.0', 'end-1c').strip()
        # Clean default placeholder
        if extra.startswith('z.B.:'):
            extra = ''

        if not url and not pasted:
            messagebox.showwarning('Stellenanzeige fehlt',
                                  'Bitte eine URL oder den Stellentext einfügen.')
            return

        self._clear_log()
        self._status('KI arbeitet...')
        self._log('▶ KI-Bewerbungsassistent gestartet...')

        def _worker():
            try:
                # 1) Get job text
                if url:
                    self._log(f'↓ Lade Stellenanzeige von: {url}')
                    job_text = ki.fetch_job_text(url)
                    self._log(f'✓ {len(job_text)} Zeichen extrahiert.')
                else:
                    job_text = pasted
                    self._log(f'✓ Eingefügter Text ({len(job_text)} Zeichen).')

                # 2) Call Claude
                self._log('↑ Sende an Claude API...')
                cfg = ki.call_claude(api_key, job_text, extra)
                self._log('✓ Claude-Antwort erhalten!')

                # 3) Add datum
                cfg['datum'] = today_de()

                # 4) Populate GUI
                self.after(0, lambda: self._apply_ki_result(cfg, then_pdf))

            except Exception as exc:
                self._log(f'✗ Fehler: {exc}')
                self.after(0, lambda: self._status(f'Fehler: {exc}'))

        threading.Thread(target=_worker, daemon=True).start()

    def _ki_generate_and_pdf(self):
        self._ki_generate(then_pdf=True)

    def _apply_ki_result(self, cfg, then_pdf=False):
        self._stash_extra_cfg(cfg)
        self._set_config(cfg)
        self._log('✓ Alle Felder ausgefüllt.')

        # Fill email fields
        email_betreff = cfg.get('email_betreff', '')
        email_text = cfg.get('email_text', '')
        if email_betreff:
            self._email_betreff_var.set(email_betreff)
        if email_text:
            self._email_text_widget.delete('1.0', 'end')
            self._email_text_widget.insert('1.0', email_text)
            self._log('✓ E-Mail-Text erstellt.')

        # Show warnings
        warnungen = cfg.get('warnungen', [])
        if warnungen:
            self._log('')
            self._log('⚠ ACHTUNG – Bitte manuell prüfen:')
            warn_lines = []
            for w in warnungen:
                self._log(f'  ⚠ {w}')
                warn_lines.append(f'• {w}')
            messagebox.showwarning(
                'KI-Hinweise – Bitte prüfen',
                'Folgende Punkte konnten nicht automatisch '
                'ermittelt werden:\n\n' + '\n'.join(warn_lines) +
                '\n\nBitte im Tab "Stelle & Firma" manuell korrigieren.')

        stelle = cfg.get('stelle', '?')
        firma = cfg.get('firma', '?')
        self._status(f'✓  KI fertig: {stelle} bei {firma}')

        # Switch to Stelle tab so user sees the result
        self._nb.select(self._tab_stelle)

        if then_pdf and not warnungen:
            self._log('📄 Erstelle PDFs...')
            self._gen_both()
            self._log('✓ PDFs erstellt und geöffnet.')
        elif then_pdf and warnungen:
            self._log('⚠ PDFs NICHT erstellt – bitte erst Warnungen beheben, '
                      'dann manuell "Beide erstellen" klicken.')

    # ── TAB 1: STELLE & FIRMA ────────────────────────────────────────────────
    def _build_stelle_tab(self, parent):
        scroll_frame = self._make_scrollable(parent)

        self.vars = {}

        # ── Stelle Card ──
        stelle_outer, stelle_card = self._make_card_grid(scroll_frame, '📋  STELLE', padx=16, pady=(12, 4))
        stelle_outer.pack(fill='x', padx=16, pady=(12, 4))
        row = 2
        row = self._field_card(stelle_card, 'stelle', 'Stellenbezeichnung',
                          'Fullstack Entwickler', row)
        row = self._field_card(stelle_card, 'bewerbung_email', 'Bewerbungs-E-Mail',
                  'jobs@example.com', row)
        row = self._field_card(stelle_card, 'betreff', 'Betreff-Zeile',
                          'Bewerbung als Fullstack Entwickler – C# / .NET / Angular',
                          row, width=70)
        row = self._field_card(stelle_card, 'datum', 'Datum', today_de(), row)

        # ── CV-Kurzprofil Card (von KI auf die Stelle zugeschnitten) ──
        kp_outer, kp_card = self._make_card_grid(scroll_frame, '🧩  CV-KURZPROFIL', padx=16, pady=4)
        kp_outer.pack(fill='x', padx=16, pady=4)
        self._textarea_card(
            kp_card, 'kurzprofil',
            'Kurzprofil im Lebenslauf (HTML <b>fett</b> erlaubt) – '
            'wird von der KI an die Stelle angepasst',
            gen_l.DEFAULT_KURZPROFIL, 2, height=6)

        # ── Firma Card ──
        firma_outer, firma_card = self._make_card_grid(scroll_frame, '🏢  FIRMA', padx=16, pady=4)
        firma_outer.pack(fill='x', padx=16, pady=4)
        row = 2
        row = self._field_card(firma_card, 'firma', 'Firmenname', 'Musterfirma GmbH', row)
        row = self._field_card(firma_card, 'ansprechpartner', 'Ansprechpartner',
                          'Frau / Herrn Mustermann', row)
        row = self._field_card(firma_card, 'firma_strasse', 'Straße', 'Musterstraße 1', row)
        row = self._field_card(firma_card, 'firma_plz_ort', 'PLZ + Ort',
                          '79098 Freiburg im Breisgau', row)

        # ── Anrede & Anlagen Card ──
        anrede_outer, anrede_card = self._make_card_grid(scroll_frame, '✍  ANREDE & ANLAGEN', padx=16, pady=(4, 12))
        anrede_outer.pack(fill='x', padx=16, pady=(4, 12))
        row = 2
        row = self._field_card(anrede_card, 'anrede', 'Anrede',
                          'Sehr geehrte Damen und Herren,', row, width=50)
        row = self._field_card(anrede_card, 'anlagen', 'Anlagen',
                          'Anschreiben, Lebenslauf, Arbeitszeugnis,  Zeugnisse, Zertifikate',
                          row, width=60)

    # ── TAB 2: ANSCHREIBEN-TEXT ──────────────────────────────────────────────
    def _build_anschreiben_tab(self, parent):
        scroll_frame = self._make_scrollable(parent)

        # Info card
        info_card = self._make_card(scroll_frame, padx=16, pady=(12, 4))
        tk.Label(info_card, text='HTML-Tags wie <b>fett</b> sind erlaubt.',
                 bg=WHITE, fg=GRAY, font=(FONT, 9)).pack(anchor='w')

        defaults = gen_a.DEFAULT_CONFIG
        for i in range(1, 6):
            key = f'absatz_{i}'
            outer, card = self._make_card_grid(scroll_frame, None, padx=16, pady=4)
            outer.pack(fill='x', padx=16, pady=4)
            row = 0
            row = self._textarea_card(card, key, f'Absatz {i}',
                                 defaults.get(key, ''), row)

    # ── TAB 3: E-MAIL ───────────────────────────────────────────────────────
    def _build_email_tab(self, parent):
        c = tk.Frame(parent, bg=BG)
        c.pack(fill='both', expand=True, padx=0, pady=0)

        # ── Email compose card ──
        compose_card = self._make_card(c, '📧  BEWERBUNGS-E-MAIL', padx=16, pady=(12, 4))

        tk.Label(compose_card,
                 text='KI generiert diesen Text automatisch. '
                 'Du kannst ihn bearbeiten und dann kopieren.',
                 bg=WHITE, fg=GRAY, font=(FONT, 9)).pack(
                      anchor='w', pady=(0, 10))

        # Betreff
        bf = tk.Frame(compose_card, bg=WHITE)
        bf.pack(fill='x', pady=(0, 8))
        tk.Label(bf, text='Betreff:', bg=WHITE, fg=NAVY,
                 font=(FONT, 10, 'bold')).pack(
            side='left', padx=(0, 8))
        self._email_betreff_var = tk.StringVar(
            value='Bewerbung als Fullstack Entwickler')
        ttk.Entry(bf, textvariable=self._email_betreff_var,
                  width=70, font=(FONT, 10)).pack(
                      side='left', fill='x', expand=True)

        # Email body
        self._email_text_widget = tk.Text(
            compose_card, height=14, font=(FONT, 10), wrap='word',
            bg='#F8FAFC', fg=FG, relief='solid', borderwidth=1,
            highlightbackground=CARD_BD, highlightthickness=0,
            padx=10, pady=8)
        self._email_text_widget.insert('1.0',
            'Sehr geehrte Damen und Herren,\n\n'
            'anbei übersende ich Ihnen meine Bewerbungsunterlagen '
            'für die ausgeschriebene Stelle als Fullstack Entwickler.\n\n'
            'Ich freue mich auf Ihre Rückmeldung und stehe für '
            'ein persönliches Gespräch gerne zur Verfügung.\n\n'
            'Mit freundlichen Grüßen\n'
            'Hamza Öztürk\n'
            '+49 155 66859378\n'
            'oeztuerk.hamza@web.de')
        self._email_text_widget.pack(fill='both', expand=True, pady=(0, 10))

        # Buttons
        btn_frame = tk.Frame(compose_card, bg=WHITE)
        btn_frame.pack(fill='x')
        ttk.Button(btn_frame, text='📋  Betreff kopieren',
                   style='Ghost.TButton',
                   command=self._copy_email_betreff).pack(
                       side='left', padx=4)
        ttk.Button(btn_frame, text='📋  E-Mail-Text kopieren',
                   style='Accent.TButton',
                   command=self._copy_email_text).pack(
                       side='left', padx=4)
        ttk.Button(btn_frame, text='📋  Alles kopieren',
                   style='Gold.TButton',
                   command=self._copy_email_all).pack(
                       side='left', padx=4)

        # IMAP sync card
        imap_card = self._make_card(c, '📨  POSTEINGANG SYNCHRONISIEREN (IMAP)', padx=16, pady=(8, 4))

        tk.Label(imap_card,
            text='Liest Bewerbungsantworten aus dem Posteingang und '
                 'aktualisiert Bewerbungen.csv automatisch.',
            bg=WHITE, fg=GRAY, font=(FONT, 9)).pack(
                      anchor='w', pady=(0, 10))

        imap_cfg = self._load_imap_settings()

        row1 = tk.Frame(imap_card, bg=WHITE)
        row1.pack(fill='x', pady=(0, 6))
        tk.Label(row1, text='E-Mail:', bg=WHITE, fg=NAVY,
                 font=(FONT, 10, 'bold')).pack(
            side='left', padx=(0, 8))
        self._imap_email_var = tk.StringVar(value=imap_cfg.get('email', ''))
        ttk.Entry(row1, textvariable=self._imap_email_var,
                  width=40, font=(FONT, 10)).pack(side='left', padx=(0, 12))

        tk.Label(row1, text='IMAP-Server:', bg=WHITE, fg=NAVY,
                 font=(FONT, 10, 'bold')).pack(
            side='left', padx=(0, 8))
        self._imap_server_var = tk.StringVar(value=imap_cfg.get('server', 'imap.web.de'))
        ttk.Entry(row1, textvariable=self._imap_server_var,
                  width=24, font=(FONT, 10)).pack(side='left')

        row2 = tk.Frame(imap_card, bg=WHITE)
        row2.pack(fill='x', pady=(0, 8))
        tk.Label(row2, text='App-Passwort:', bg=WHITE, fg=NAVY,
                 font=(FONT, 10, 'bold')).pack(
            side='left', padx=(0, 8))
        self._imap_password_var = tk.StringVar(value=imap_cfg.get('password', ''))
        ttk.Entry(row2, textvariable=self._imap_password_var, show='•',
                  width=30, font=(FONT, 10)).pack(side='left', padx=(0, 12))

        tk.Label(row2, text='Port:', bg=WHITE, fg=NAVY,
                 font=(FONT, 10, 'bold')).pack(
            side='left', padx=(0, 8))
        self._imap_port_var = tk.StringVar(value=str(imap_cfg.get('port', 993)))
        ttk.Entry(row2, textvariable=self._imap_port_var,
                  width=8, font=(FONT, 10)).pack(side='left', padx=(0, 12))

        self._imap_only_unseen_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            row2,
            text='Nur ungelesene (UNSEEN) E-Mails durchsuchen',
            variable=self._imap_only_unseen_var,
            bg=WHITE,
            fg=FG,
            font=(FONT, 9),
            activebackground=WHITE,
            selectcolor=WHITE).pack(side='left')

        row3 = tk.Frame(imap_card, bg=WHITE)
        row3.pack(fill='x', pady=(0, 4))
        ttk.Button(row3, text='IMAP-Einstellungen speichern',
                   style='Ghost.TButton',
                   command=self._save_imap_settings).pack(side='left', padx=(0, 6))
        ttk.Button(row3, text='E-Mails abrufen + CSV aktualisieren',
                   style='Accent.TButton',
                   command=self._sync_mail_statuses).pack(side='left', padx=(0, 6))
        ttk.Button(row3, text='Alle E-Mails abrufen + CSV aktualisieren',
                   style='Navy.TButton',
                   command=self._sync_all_mail_statuses).pack(side='left')

        row3b = tk.Frame(imap_card, bg=WHITE)
        row3b.pack(fill='x', pady=(6, 0))
        ttk.Button(row3b, text='Alle E-Mails als PDF herunterladen',
               style='Navy.TButton',
               command=self._download_all_mail_pdfs).pack(side='left')

        # SMTP card
        smtp_card = self._make_card(c, '📤  E-MAIL SENDEN (SMTP)', padx=16, pady=(4, 12))

        smtp_cfg = self._load_smtp_settings()
        row4 = tk.Frame(smtp_card, bg=WHITE)
        row4.pack(fill='x', pady=(0, 6))
        tk.Label(row4, text='SMTP-Server:', bg=WHITE, fg=NAVY,
                 font=(FONT, 10, 'bold')).pack(
            side='left', padx=(0, 8))
        self._smtp_server_var = tk.StringVar(value=smtp_cfg.get('server', 'smtp.web.de'))
        ttk.Entry(row4, textvariable=self._smtp_server_var,
                  width=24, font=(FONT, 10)).pack(side='left', padx=(0, 12))

        tk.Label(row4, text='SMTP-Port:', bg=WHITE, fg=NAVY,
                 font=(FONT, 10, 'bold')).pack(
            side='left', padx=(0, 8))
        self._smtp_port_var = tk.StringVar(value=str(smtp_cfg.get('port', 587)))
        ttk.Entry(row4, textvariable=self._smtp_port_var,
                  width=8, font=(FONT, 10)).pack(side='left', padx=(0, 12))

        ttk.Button(row4, text='SMTP-Einstellungen speichern',
                   style='Ghost.TButton',
                   command=self._save_smtp_settings).pack(side='left')

        row5 = tk.Frame(smtp_card, bg=WHITE)
        row5.pack(fill='x', pady=(0, 2))
        tk.Label(row5, text='Empfänger-Adresse:', bg=WHITE, fg=NAVY,
                 font=(FONT, 10, 'bold')).pack(
            side='left', padx=(0, 8))
        self._mail_to_var = self.vars.get('bewerbung_email', tk.StringVar(value=''))
        ttk.Entry(row5, textvariable=self._mail_to_var,
                  width=50, font=(FONT, 10)).pack(side='left', padx=(0, 12))
        ttk.Button(row5, text='Bewerbung per E-Mail senden',
                   style='Gold.TButton',
                   command=self._send_application_email).pack(side='left')

    def _copy_email_betreff(self):
        self.clipboard_clear()
        self.clipboard_append(self._email_betreff_var.get())
        self._status('✓  Betreff in Zwischenablage kopiert.')

    def _copy_email_text(self):
        text = self._email_text_widget.get('1.0', 'end-1c').strip()
        self.clipboard_clear()
        self.clipboard_append(text)
        self._status('✓  E-Mail-Text in Zwischenablage kopiert.')

    def _copy_email_all(self):
        betreff = self._email_betreff_var.get()
        text = self._email_text_widget.get('1.0', 'end-1c').strip()
        full = f'Betreff: {betreff}\n\n{text}'
        self.clipboard_clear()
        self.clipboard_append(full)
        self._status('✓  Betreff + E-Mail-Text in Zwischenablage kopiert.')

    @staticmethod
    def _safe_decode(payload, charset):
        """Bytes dekodieren und unbekannte/fehlerhafte Charsets tolerieren.

        Ein unbekannter Codec-Name (z.B. 'x-unknown') würde sonst LookupError
        werfen und den ganzen Sync/Export abbrechen.
        """
        for enc in (charset, 'utf-8', 'latin-1'):
            if not enc:
                continue
            try:
                return payload.decode(enc, errors='replace')
            except (LookupError, TypeError):
                continue
        return payload.decode('utf-8', errors='replace')

    @staticmethod
    def _decode_mime_header(value):
        if not value:
            return ''
        parts = []
        for part, enc in decode_header(value):
            if isinstance(part, bytes):
                parts.append(BewerbungsApp._safe_decode(part, enc or 'utf-8'))
            else:
                parts.append(part)
        return ''.join(parts).strip()

    @staticmethod
    def _extract_mail_text(msg):
        chunks = []
        if msg.is_multipart():
            for part in msg.walk():
                ctype = part.get_content_type()
                disp = str(part.get('Content-Disposition', ''))
                if 'attachment' in disp.lower():
                    continue
                if ctype in ('text/plain', 'text/html'):
                    payload = part.get_payload(decode=True)
                    if payload is None:
                        continue
                    charset = part.get_content_charset() or 'utf-8'
                    text = BewerbungsApp._safe_decode(payload, charset)
                    if ctype == 'text/html':
                        text = re.sub(r'<[^>]+>', ' ', text)
                        text = html.unescape(text)
                    chunks.append(text)
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset() or 'utf-8'
                text = BewerbungsApp._safe_decode(payload, charset)
                if msg.get_content_type() == 'text/html':
                    text = re.sub(r'<[^>]+>', ' ', text)
                    text = html.unescape(text)
                chunks.append(text)

        text = '\n'.join(chunks)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    @staticmethod
    def _norm_text(value):
        value = (value or '').lower()
        value = value.replace('ä', 'ae').replace('ö', 'oe').replace('ü', 'ue').replace('ß', 'ss')
        value = re.sub(r'[^a-z0-9 ]+', ' ', value)
        value = re.sub(r'\s+', ' ', value)
        return value.strip()

    def _detect_mail_status(self, subject, body):
        text = self._norm_text(f'{subject} {body}')

        sent_words = [
            'ihre bewerbung wurde an',
            'bewerbung wurde an',
            'application was sent to',
            'your application was sent to'
        ]
        invite_words = [
            'vorstellungsgespraech', 'einladung', 'interview',
            'kennenlernen', 'terminvorschlag', 'gespraech'
        ]
        reject_words = [
            'absage', 'leider', 'nicht beruecksichtigen', 'nicht berucksichtigen',
            'haben uns fuer andere', 'gegen sie entschieden', 'muessen ihnen mitteilen'
        ]
        ack_words = [
            'eingang', 'eingangsbestaetigung', 'eingangsbestaetigung',
            'bewerbung erhalten', 'danke fuer ihre bewerbung',
            'vielen dank fuer ihre bewerbung', 'wir haben ihre bewerbung erhalten'
        ]

        # Rückgabewerte entsprechen der kanonischen Status-Liste der Übersicht
        # (_DURUM_OPTIONS), damit Sync-Zeilen korrekt gefiltert/eingefärbt werden.
        if (any(w in text for w in sent_words) and
                ('gesendet' in text or 'sent' in text)):
            return 'Beworben'
        if any(w in text for w in invite_words):
            return 'Mülakat Daveti'
        if any(w in text for w in reject_words):
            return 'Olumsuz (Red)'
        if any(w in text for w in ack_words):
            return 'Alındı Teyidi (İşlemde)'
        return None

    @staticmethod
    def _extract_linkedin_company(subject, body):
        patterns = [
            r'Ihre\s+Bewerbung\s+wurde\s+an\s+(.+?)\s+gesendet',
            r'Your\s+application\s+was\s+sent\s+to\s+(.+?)(?:\.|$)',
        ]
        source = f'{subject} {body}'
        for pattern in patterns:
            m = re.search(pattern, source, flags=re.IGNORECASE)
            if m:
                company = m.group(1).strip(' .,-')
                if company:
                    return company
        return ''

    @staticmethod
    def _extract_linkedin_position(body, company):
        if not body:
            return ''

        # Common LinkedIn snippet: "... gesendet. <Position> <Company> · <Ort> ..."
        if company:
            pattern = rf'gesendet\.\s+(.+?)\s+{re.escape(company)}\s+[·|\\-]'
            m = re.search(pattern, body, flags=re.IGNORECASE)
            if m:
                pos = m.group(1).strip(' .,-')
                if pos:
                    return pos

        m = re.search(r'([A-Za-z0-9ÄÖÜäöüß\-/+ ]+\(m/w/d\))', body)
        if m:
            return m.group(1).strip()

        return ''

    @staticmethod
    def _guess_company_from_sender(sender_name, sender_email):
        sender_name = (sender_name or '').strip()
        if sender_name:
            return sender_name

        domain = (sender_email.split('@')[-1] if '@' in sender_email else sender_email).strip().lower()
        if domain.startswith('mail.'):
            domain = domain[5:]
        base = domain.split('.')[0] if domain else 'Unbekannt'
        return base.replace('-', ' ').replace('_', ' ').strip().title()

    def _company_score(self, company, sender_name, sender_email, subject):
        stop = {
            'gmbh', 'ag', 'kg', 'co', 'mbh', 'se', 'ug', 'der', 'die', 'das',
            'und', 'solutions', 'technology', 'technologies', 'deutschland'
        }
        c_tokens = [t for t in self._norm_text(company).split() if len(t) > 2 and t not in stop]
        if not c_tokens:
            return 0

        hay = self._norm_text(f'{sender_name} {sender_email} {subject}')
        return sum(1 for t in c_tokens if t in hay)

    def _match_csv_row(self, rows, sender_name, sender_email, subject):
        best_idx = -1
        best_score = 0
        for i in range(1, len(rows)):
            row = rows[i]
            if len(row) < 2:
                continue
            score = self._company_score(row[0], sender_name, sender_email, subject)
            if score > best_score:
                best_score = score
                best_idx = i
        return best_idx if best_score > 0 else -1

    @staticmethod
    def _mail_date_to_de(mail_date):
        try:
            dt = parsedate_to_datetime(mail_date)
            return dt.strftime('%d.%m.%Y')
        except Exception:
            return today_de()

    @staticmethod
    def _applications_header():
        return ['Firma / Unternehmen', 'Position / Stelle', 'Status / Ergebnis', 'Datum']

    def _read_applications_rows(self):
        rows = []

        xlsx_ok = load_workbook is not None and os.path.isfile(APPLICATIONS_XLSX)
        csv_ok = os.path.isfile(APPLICATIONS_CSV)

        # Die zuletzt geänderte Quelle gewinnt. So überdeckt eine veraltete
        # XLSX (z.B. weil Excel sie gesperrt hatte) NICHT die frisch
        # geschriebene CSV – sonst gingen Status-Updates verloren.
        prefer_xlsx = xlsx_ok
        if xlsx_ok and csv_ok:
            prefer_xlsx = os.path.getmtime(APPLICATIONS_XLSX) >= os.path.getmtime(APPLICATIONS_CSV)

        if prefer_xlsx:
            try:
                wb = load_workbook(APPLICATIONS_XLSX)
                ws = wb.active
                for r in ws.iter_rows(values_only=True):
                    row = [str(v).strip() if v is not None else '' for v in r]
                    if any(cell for cell in row):
                        rows.append(row)
            except Exception:
                rows = []  # XLSX defekt/gesperrt -> auf CSV ausweichen

        if not rows and csv_ok:
            with open(APPLICATIONS_CSV, 'r', encoding='utf-8-sig', newline='') as f:
                rows = list(csv.reader(f))

        if not rows:
            rows = [self._applications_header()]

        return rows

    def _write_applications_rows(self, rows):
        # CSV ist die verlässliche Quelle und wird immer zuerst geschrieben.
        with open(APPLICATIONS_CSV, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerows(rows)

        if Workbook is None:
            return

        wb = Workbook()
        ws = wb.active
        ws.title = 'Bewerbungen'
        for row in rows:
            ws.append(row)
        try:
            wb.save(APPLICATIONS_XLSX)
        except PermissionError:
            # XLSX ist in Excel geöffnet -> Backup speichern und warnen.
            # Die CSV ist bereits aktuell und wird beim nächsten Lesen
            # (neuere mtime) bevorzugt, daher gehen keine Daten verloren.
            fallback = os.path.join(SCRIPT_DIR, 'Bewerbungen_backup.xlsx')
            try:
                wb.save(fallback)
            except Exception:
                pass
            self._status('⚠ Bewerbungen.xlsx ist in Excel geöffnet – '
                         'Update in CSV gespeichert. Bitte Excel schließen.')

    @staticmethod
    def _load_imap_settings():
        defaults = {'email': '', 'server': 'imap.web.de', 'port': 993, 'password': ''}
        if os.path.isfile(IMAP_SETTINGS_FILE):
            try:
                with open(IMAP_SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    defaults.update(data)
            except (json.JSONDecodeError, OSError):
                pass  # beschädigte Datei -> Defaults verwenden
        return defaults

    @staticmethod
    def _safe_port(value, fallback):
        try:
            return int(str(value).strip())
        except (ValueError, AttributeError):
            return fallback

    def _save_imap_settings(self):
        settings = {
            'email': self._imap_email_var.get().strip(),
            'server': self._imap_server_var.get().strip() or 'imap.web.de',
            'port': self._safe_port(self._imap_port_var.get(), 993),
            'password': self._imap_password_var.get()
        }
        with open(IMAP_SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
        self._status('✓  IMAP-Einstellungen gespeichert.')

    @staticmethod
    def _load_smtp_settings():
        defaults = {'server': 'smtp.web.de', 'port': 587}
        if os.path.isfile(SMTP_SETTINGS_FILE):
            try:
                with open(SMTP_SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    defaults.update(data)
            except (json.JSONDecodeError, OSError):
                pass
        return defaults

    def _save_smtp_settings(self):
        try:
            port = int((self._smtp_port_var.get() or '587').strip() or '587')
        except ValueError:
            messagebox.showwarning('Ungültiger Port', 'SMTP-Port muss eine Zahl sein (z.B. 587).')
            return

        settings = {
            'server': self._smtp_server_var.get().strip() or 'smtp.web.de',
            'port': port
        }
        with open(SMTP_SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
        self._status('✓  SMTP-Einstellungen gespeichert.')

    @staticmethod
    def _attach_file_to_message(msg, path):
        ctype, _ = mimetypes.guess_type(path)
        if ctype:
            maintype, subtype = ctype.split('/', 1)
        else:
            maintype, subtype = 'application', 'octet-stream'

        with open(path, 'rb') as f:
            msg.add_attachment(f.read(), maintype=maintype, subtype=subtype,
                               filename=os.path.basename(path))

    def _send_application_email(self):
        sender = self._imap_email_var.get().strip()
        password = self._imap_password_var.get().strip()
        recipient = self._mail_to_var.get().strip()
        smtp_server = self._smtp_server_var.get().strip() or 'smtp.web.de'
        smtp_port_text = self._smtp_port_var.get().strip() or '587'

        if not sender or not password:
            messagebox.showwarning('Fehlende Angaben',
                                   'Bitte Absender-E-Mail und App-Passwort eingeben.')
            return
        if not recipient:
            messagebox.showwarning('Fehlende Angaben',
                                   'Bitte Bewerbungs-E-Mail-Adresse eingeben.')
            return

        try:
            smtp_port = int(smtp_port_text)
        except ValueError:
            messagebox.showwarning('Ungültiger Port', 'SMTP-Port muss eine Zahl sein (z.B. 587).')
            return

        # Persist credentials/settings so user is not asked again next time.
        self._save_imap_settings()
        self._save_smtp_settings()

        subject = self._email_betreff_var.get().strip() or 'Bewerbung'
        body = self._email_text_widget.get('1.0', 'end-1c').strip()
        if not body:
            messagebox.showwarning('Fehlender Text', 'E-Mail-Text darf nicht leer sein.')
            return

        cfg = self._get_config()
        bewerbung_pdf = self._make_output_path('Bewerbung')

        try:
            if not os.path.isfile(bewerbung_pdf):
                self._build_application_pdf(bewerbung_pdf, cfg)
        except Exception as exc:
            messagebox.showerror('PDF-Fehler', f'PDF konnte nicht erstellt werden: {exc}')
            return

        required_files = [bewerbung_pdf]
        missing = [p for p in required_files if not os.path.isfile(p)]
        if missing:
            messagebox.showerror(
                'Fehlende Datei(en)',
                'Folgende Dateien wurden nicht gefunden:\n\n' + '\n'.join(missing))
            return

        self._status('Bewerbungs-E-Mail wird gesendet...')

        def _worker():
            try:
                msg = EmailMessage()
                msg['From'] = sender
                msg['To'] = recipient
                msg['Subject'] = subject
                msg.set_content(body)

                for path in required_files:
                    self._attach_file_to_message(msg, path)

                if smtp_port == 465:
                    # Implizites TLS (z.B. web.de/GMX/Gmail auf 465)
                    with smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=30) as smtp:
                        smtp.login(sender, password)
                        smtp.send_message(msg)
                else:
                    with smtplib.SMTP(smtp_server, smtp_port, timeout=30) as smtp:
                        smtp.starttls()
                        smtp.login(sender, password)
                        smtp.send_message(msg)

                self._log_application(cfg)
                self.after(0, lambda: self._status('✓  Bewerbungs-E-Mail gesendet.'))
                self.after(0, lambda: messagebox.showinfo(
                    'Erfolgreich gesendet',
                    f'Bewerbungs-E-Mail gesendet an:\n{recipient}'))
            except Exception as exc:
                self.after(0, lambda: self._status(f'E-Mail-Fehler: {exc}'))
                self.after(0, lambda: messagebox.showerror('E-Mail-Sendefehler', str(exc)))

        threading.Thread(target=_worker, daemon=True).start()

    # ── TAB: INITIATIVBEWERBUNG ─────────────────────────────────────────────
    def _build_initiativ_tab(self, parent):
        scroll_frame = self._make_scrollable(parent)

        # State
        self._init_companies = []   # aktuell gefundene Firmen (aligned mit Tree)

        # ── Info / Hinweis ──
        info_card = self._make_card(scroll_frame, padx=16, pady=(12, 4))
        tk.Label(info_card, text=(
            'Findet Firmen mit öffentlich hinterlegter Kontakt-E-Mail in einer '
            'Region (Quelle: OpenStreetMap) und verschickt eine Initiativbewerbung '
            'mit Lebenslauf im Anhang. Der Firmenname wird automatisch in den Text '
            'eingesetzt ({firma}).'),
            bg=WHITE, fg=FG_LIGHT, font=(FONT, 10),
            wraplength=850, justify='left', anchor='w').pack(anchor='w')
        tk.Label(info_card, text=(
            '⚠  Nur an relevante Firmen senden. Nutze eine angemessene Pause '
            'zwischen den Mails, damit dein Postfach nicht als Spam eingestuft wird.'),
            bg=WHITE, fg=ACCENT_HVR, font=(FONT, 9),
            wraplength=850, justify='left', anchor='w').pack(anchor='w', pady=(6, 0))

        # ── Suche ──
        s_outer, s_card = self._make_card_grid(
            scroll_frame, '🔎  FIRMEN IN REGION SUCHEN', padx=16, pady=4)
        s_outer.pack(fill='x', padx=16, pady=4)

        tk.Label(s_card, text='Region / Stadt', bg=WHITE, fg=FG,
                 font=(FONT, 10)).grid(row=2, column=0, sticky='e',
                                       padx=(0, 8), pady=4)
        self._init_region_var = tk.StringVar(value='Freiburg im Breisgau')
        ttk.Entry(s_card, textvariable=self._init_region_var, width=36,
                  font=(FONT, 10)).grid(row=2, column=1, sticky='w', pady=4)

        tk.Label(s_card, text='Umkreis (km)', bg=WHITE, fg=FG,
                 font=(FONT, 10)).grid(row=2, column=2, sticky='e',
                                       padx=(12, 8), pady=4)
        self._init_radius_var = tk.StringVar(value='10')
        ttk.Entry(s_card, textvariable=self._init_radius_var, width=8,
                  font=(FONT, 10)).grid(row=2, column=3, sticky='w', pady=4)

        tk.Label(s_card, text='Kategorie', bg=WHITE, fg=FG,
                 font=(FONT, 10)).grid(row=3, column=0, sticky='e',
                                       padx=(0, 8), pady=4)
        self._init_cat_var = tk.StringVar(value=initiativ.CATEGORY_ORDER[0])
        ttk.Combobox(s_card, textvariable=self._init_cat_var,
                     values=initiativ.CATEGORY_ORDER, state='readonly',
                     width=34, font=(FONT, 10)).grid(
                         row=3, column=1, sticky='w', pady=4)

        tk.Label(s_card, text='Max. Anzahl', bg=WHITE, fg=FG,
                 font=(FONT, 10)).grid(row=3, column=2, sticky='e',
                                       padx=(12, 8), pady=4)
        self._init_limit_var = tk.StringVar(value='100')
        ttk.Entry(s_card, textvariable=self._init_limit_var, width=8,
                  font=(FONT, 10)).grid(row=3, column=3, sticky='w', pady=4)

        btn_row = tk.Frame(s_card, bg=WHITE)
        btn_row.grid(row=4, column=0, columnspan=4, sticky='w', pady=(8, 2))
        ttk.Button(btn_row, text='🔎  Firmen suchen', style='Navy.TButton',
                   command=self._init_search_companies).pack(side='left')
        ttk.Button(btn_row, text='🗺  Gebiet auf Karte zeigen',
                   style='Ghost.TButton',
                   command=self._init_show_area).pack(side='left', padx=6)
        ttk.Button(btn_row, text='🚲  Alle Fahrradfirmen in Deutschland',
                   style='Gold.TButton',
                   command=self._init_search_bicycles).pack(side='left', padx=6)

        # ── Karte (Suchgebiet wie bei Kleinanzeigen) ──
        map_card = self._make_card(
            scroll_frame, '🗺  SUCHGEBIET AUF DER KARTE', padx=16, pady=4)
        self._init_map = None
        self._init_map_circle = None
        self._init_map_center = None
        self._init_map_markers = []
        if MAP_AVAILABLE:
            tk.Label(map_card, text=(
                'Zeigt das gewählte Suchgebiet (Umkreis) und – nach der Suche – '
                'die gefundenen Firmen als Marker.'),
                bg=WHITE, fg=FG_LIGHT, font=(FONT, 9),
                anchor='w').pack(anchor='w', pady=(0, 6))
            self._init_map = tkintermapview.TkinterMapView(
                map_card, height=360, corner_radius=8)
            self._init_map.pack(fill='both', expand=True)
            # Deutschland als Startansicht
            self._init_map.set_position(51.1657, 10.4515)
            self._init_map.set_zoom(6)
        else:
            tk.Label(map_card, text=(
                'ℹ  Karte nicht verfügbar. Bitte einmalig installieren:\n'
                '    pip install tkintermapview\n'
                'Danach die App neu starten.'),
                bg=WHITE, fg=ACCENT_HVR, font=(FONT_MONO, 9),
                justify='left', anchor='w').pack(anchor='w', pady=4)

        # ── Ergebnisliste ──
        res_card = self._make_card(
            scroll_frame, '🏢  GEFUNDENE FIRMEN', padx=16, pady=4)

        tools = tk.Frame(res_card, bg=WHITE)
        tools.pack(fill='x', pady=(0, 6))
        ttk.Button(tools, text='Alle auswählen', style='Ghost.TButton',
                   command=self._init_select_all).pack(side='left', padx=(0, 4))
        ttk.Button(tools, text='Auswahl aufheben', style='Ghost.TButton',
                   command=self._init_select_none).pack(side='left', padx=4)
        self._init_count_var = tk.StringVar(value='0 Firmen')
        tk.Label(tools, textvariable=self._init_count_var, bg=WHITE,
                 fg=FG_LIGHT, font=(FONT, 9)).pack(side='right')

        tree_frame = tk.Frame(res_card, bg=WHITE)
        tree_frame.pack(fill='both', expand=True)
        cols = ('firma', 'email', 'adresse', 'website')
        self._init_tree = ttk.Treeview(tree_frame, columns=cols,
                                       show='headings', selectmode='extended',
                                       height=10)
        self._init_tree.heading('firma', text='Firma', anchor='w')
        self._init_tree.heading('email', text='E-Mail', anchor='w')
        self._init_tree.heading('adresse', text='Adresse', anchor='w')
        self._init_tree.heading('website', text='Website', anchor='w')
        self._init_tree.column('firma', width=220, minwidth=120, stretch=True)
        self._init_tree.column('email', width=220, minwidth=140, stretch=True)
        self._init_tree.column('adresse', width=200, minwidth=120, stretch=True)
        self._init_tree.column('website', width=160, minwidth=100, stretch=True)
        vsb = ttk.Scrollbar(tree_frame, orient='vertical',
                            command=self._init_tree.yview)
        self._init_tree.configure(yscrollcommand=vsb.set)
        self._init_tree.pack(side='left', fill='both', expand=True)
        vsb.pack(side='right', fill='y')
        self._init_tree.tag_configure('sent', foreground=GRAY)

        # ── E-Mail-Text ──
        t_outer, t_card = self._make_card_grid(
            scroll_frame, '✉  INITIATIV-E-MAIL', padx=16, pady=4)
        t_outer.pack(fill='x', padx=16, pady=4)

        tk.Label(t_card, text='Betreff', bg=WHITE, fg=FG,
                 font=(FONT, 10)).grid(row=2, column=0, sticky='e',
                                       padx=(0, 8), pady=4)
        self._init_betreff_var = tk.StringVar(value=initiativ.DEFAULT_BETREFF)
        ttk.Entry(t_card, textvariable=self._init_betreff_var, width=70,
                  font=(FONT, 10)).grid(row=2, column=1, columnspan=2,
                                        sticky='we', padx=(0, 12), pady=4)

        tk.Label(t_card, text='Der Platzhalter {firma} wird pro Firma ersetzt.',
                 bg=WHITE, fg=GRAY, font=(FONT, 9)).grid(
                     row=3, column=0, columnspan=3, sticky='w', pady=(4, 2))
        self._init_text_widget = tk.Text(
            t_card, height=13, width=95, font=(FONT, 10), wrap='word',
            bg='#F8FAFC', fg=FG, relief='solid', borderwidth=1,
            highlightbackground=CARD_BD, highlightthickness=0, padx=8, pady=6)
        self._init_text_widget.insert('1.0', initiativ.DEFAULT_TEXT)
        self._init_text_widget.grid(row=4, column=0, columnspan=3,
                                    sticky='we', pady=(0, 6))

        gen_row = tk.Frame(t_card, bg=WHITE)
        gen_row.grid(row=5, column=0, columnspan=3, sticky='w', pady=(0, 2))
        ttk.Button(gen_row, text='🤖  KI-Text erstellen', style='Gold.TButton',
                   command=self._init_generate_text).pack(side='left')
        ttk.Button(gen_row, text='↺  Standardtext', style='Ghost.TButton',
                   command=self._init_reset_text).pack(side='left', padx=6)

        # ── Versand ──
        send_card = self._make_card(
            scroll_frame, '📤  VERSAND', padx=16, pady=4)

        opt_row = tk.Frame(send_card, bg=WHITE)
        opt_row.pack(fill='x', pady=(0, 8))
        tk.Label(opt_row, text='Pause zwischen Mails (Sek.):', bg=WHITE, fg=NAVY,
                 font=(FONT, 10, 'bold')).pack(side='left', padx=(0, 8))
        self._init_delay_var = tk.StringVar(value='20')
        ttk.Entry(opt_row, textvariable=self._init_delay_var, width=6,
                  font=(FONT, 10)).pack(side='left', padx=(0, 16))

        self._init_attach_lebenslauf = tk.BooleanVar(value=True)
        tk.Checkbutton(opt_row, text='Lebenslauf anhängen',
                       variable=self._init_attach_lebenslauf, bg=WHITE, fg=FG,
                       font=(FONT, 9), activebackground=WHITE,
                       selectcolor=WHITE).pack(side='left', padx=(0, 12))
        self._init_skip_sent = tk.BooleanVar(value=True)
        tk.Checkbutton(opt_row, text='Bereits kontaktierte überspringen',
                       variable=self._init_skip_sent, bg=WHITE, fg=FG,
                       font=(FONT, 9), activebackground=WHITE,
                       selectcolor=WHITE).pack(side='left')

        tk.Label(send_card, text=(
            'Absender & App-Passwort werden aus dem Tab „E-Mail" verwendet '
            '(IMAP-Feld). SMTP-Server/Port ebenfalls dort einstellen.'),
            bg=WHITE, fg=GRAY, font=(FONT, 9)).pack(anchor='w', pady=(0, 8))

        ttk.Button(send_card, text='✉  Ausgewählte Firmen anschreiben',
                   style='Gold.TButton',
                   command=self._init_send_selected).pack(anchor='w')

        # ── Log ──
        log_outer, log_card = self._make_card_grid(
            scroll_frame, '📊  LOG', padx=16, pady=(4, 12))
        log_outer.pack(fill='x', padx=16, pady=(4, 12))
        self._init_log_widget = tk.Text(
            log_card, height=8, width=95, font=(FONT_MONO, 9), wrap='word',
            bg='#0F172A', fg='#E2E8F0', relief='flat', borderwidth=0,
            padx=10, pady=8, state='disabled', insertbackground='#E2E8F0')
        self._init_log_widget.grid(row=2, column=0, columnspan=3, sticky='we',
                                   pady=(0, 4))

    def _init_log(self, msg):
        if threading.current_thread() is not threading.main_thread():
            self.after(0, lambda m=msg: self._init_log(m))
            return
        self._init_log_widget.configure(state='normal')
        self._init_log_widget.insert('end', msg + '\n')
        self._init_log_widget.see('end')
        self._init_log_widget.configure(state='disabled')
        self.update_idletasks()

    @staticmethod
    def _init_sent_load():
        if os.path.isfile(INITIATIV_SENT_FILE):
            try:
                with open(INITIATIV_SENT_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if isinstance(data, list):
                    return {str(e).strip().lower() for e in data}
            except (json.JSONDecodeError, OSError):
                pass
        return set()

    @staticmethod
    def _init_sent_save(sent):
        try:
            with open(INITIATIV_SENT_FILE, 'w', encoding='utf-8') as f:
                json.dump(sorted(sent), f, ensure_ascii=False, indent=2)
        except OSError:
            pass

    def _init_reset_text(self):
        self._init_betreff_var.set(initiativ.DEFAULT_BETREFF)
        self._init_text_widget.delete('1.0', 'end')
        self._init_text_widget.insert('1.0', initiativ.DEFAULT_TEXT)

    def _init_show_area(self):
        """Gewähltes Suchgebiet (Umkreis) auf der Karte anzeigen."""
        if not MAP_AVAILABLE:
            messagebox.showinfo(
                'Karte nicht verfügbar',
                'Bitte einmalig installieren:\n\n    pip install tkintermapview\n\n'
                'Danach die App neu starten.')
            return
        region = self._init_region_var.get().strip()
        if not region:
            messagebox.showwarning('Region fehlt',
                                   'Bitte eine Region / Stadt eingeben.')
            return
        try:
            radius = float(self._init_radius_var.get().strip() or '10')
        except ValueError:
            messagebox.showwarning('Ungültig', 'Umkreis muss eine Zahl sein.')
            return

        self._init_log(f'🗺 Kartenausschnitt für "{region}" wird geladen ...')

        def _worker():
            try:
                lat, lon, name = initiativ.geocode(region)
                self.after(0, lambda: self._init_draw_area(
                    lat, lon, radius, name))
            except Exception as exc:
                self._init_log(f'✗ Karte: {exc}')

        threading.Thread(target=_worker, daemon=True).start()

    def _init_draw_area(self, lat, lon, radius, name):
        """Umkreis-Kreis + Mittelpunkt zeichnen und passend zoomen."""
        if not MAP_AVAILABLE or self._init_map is None:
            return
        if self._init_map_circle is not None:
            self._init_map_circle.delete()
        if self._init_map_center is not None:
            self._init_map_center.delete()

        self._init_map_circle = self._init_map.set_polygon(
            initiativ.circle_points(lat, lon, radius),
            fill_color='#1D4ED8', outline_color='#1D4ED8', border_width=2,
            name='Suchgebiet')
        self._init_map_center = self._init_map.set_marker(
            lat, lon, text=name.split(',')[0])

        # Kreis komplett einpassen (Bounding-Box des Umkreises).
        dlat = radius / 111.32
        dlon = radius / (111.32 * max(0.01, math.cos(math.radians(lat))))
        self._init_map.fit_bounding_box(
            (lat + dlat, lon - dlon), (lat - dlat, lon + dlon))
        self._init_log(f'🗺 Suchgebiet angezeigt: {name.split(",")[0]} '
                       f'· {radius:.0f} km Umkreis.')

    def _init_map_add_companies(self, companies):
        """Gefundene Firmen als Marker auf der Karte setzen."""
        if not MAP_AVAILABLE or self._init_map is None:
            return
        for m in self._init_map_markers:
            m.delete()
        self._init_map_markers = []
        # Tausende Marker würden die Karte einfrieren – Anzeige begrenzen.
        max_marker = 300
        if len(companies) > max_marker:
            self._init_log(f'🗺 Karte zeigt die ersten {max_marker} von '
                           f'{len(companies)} Firmen (Liste bleibt vollständig).')
            companies = companies[:max_marker]
        for c in companies:
            lat, lon = c.get('lat'), c.get('lon')
            if lat is None or lon is None:
                continue
            marker = self._init_map.set_marker(
                lat, lon, text=c.get('firma', ''),
                marker_color_circle='#B45309',
                marker_color_outside='#D97706')
            self._init_map_markers.append(marker)

    def _init_search_companies(self):
        region = self._init_region_var.get().strip()
        if not region:
            messagebox.showwarning('Region fehlt',
                                   'Bitte eine Region / Stadt eingeben.')
            return
        try:
            radius = float(self._init_radius_var.get().strip() or '10')
        except ValueError:
            messagebox.showwarning('Ungültig', 'Umkreis muss eine Zahl sein.')
            return
        try:
            limit = int(self._init_limit_var.get().strip() or '100')
        except ValueError:
            limit = 100
        category = self._init_cat_var.get()

        self._init_log(f'▶ Suche in "{region}" ...')
        self._status('Firmensuche läuft...')

        def _worker():
            try:
                # Suchgebiet zuerst auf der Karte anzeigen.
                if MAP_AVAILABLE:
                    try:
                        m_lat, m_lon, m_name = initiativ.geocode(region)
                        self.after(0, lambda: self._init_draw_area(
                            m_lat, m_lon, radius, m_name))
                    except Exception:
                        pass
                companies = initiativ.find_companies(
                    region, radius, category, limit, log=self._init_log)
                self.after(0, lambda: self._init_populate_tree(companies))
                self.after(0, lambda: self._init_map_add_companies(companies))
            except Exception as exc:
                self._init_log(f'✗ Fehler: {exc}')
                self.after(0, lambda: self._status(f'Fehler: {exc}'))

        threading.Thread(target=_worker, daemon=True).start()

    def _init_search_bicycles(self):
        """Bundesweite Suche nach allen Fahrradfirmen mit Kontakt-E-Mail."""
        if not messagebox.askyesno(
                'Alle Fahrradfirmen in Deutschland',
                'Es werden ALLE Fahrradläden, -werkstätten und -hersteller in '
                'Deutschland gesucht, die eine öffentliche Kontakt-E-Mail '
                'hinterlegt haben.\n\n'
                'Die Abfrage läuft in mehreren Stufen (ca. 10–15 Minuten), erste '
                'Ergebnisse erscheinen schon nach ca. 30 Sekunden. '
                '„Region", „Umkreis", „Kategorie" und „Max. Anzahl" werden '
                'dabei ignoriert.\n\nJetzt suchen?'):
            return

        self._init_log('▶ Bundesweite Fahrradfirmen-Suche gestartet ...')
        self._status('Fahrradfirmen in Deutschland werden gesucht...')

        def _partial(companies):
            # Zwischenstand nach jeder Stufe anzeigen (läuft im Worker-Thread).
            self.after(0, lambda c=companies: self._init_populate_tree(c))
            self.after(0, lambda c=companies: self._init_show_germany(c))

        def _worker():
            try:
                companies = initiativ.find_bicycle_companies_germany(
                    limit=0, log=self._init_log, on_partial=_partial)
                self.after(0, lambda: self._init_populate_tree(companies))
                self.after(0, lambda: self._init_show_germany(companies))
            except Exception as exc:
                self._init_log(f'✗ Fehler: {exc}')
                self.after(0, lambda: self._status(f'Fehler: {exc}'))

        threading.Thread(target=_worker, daemon=True).start()

    def _init_show_germany(self, companies):
        """Karte auf Deutschland stellen und die Treffer als Marker zeigen."""
        if not MAP_AVAILABLE or self._init_map is None:
            return
        if self._init_map_circle is not None:
            self._init_map_circle.delete()
            self._init_map_circle = None
        if self._init_map_center is not None:
            self._init_map_center.delete()
            self._init_map_center = None
        self._init_map.set_position(51.1657, 10.4515)
        self._init_map.set_zoom(6)
        self._init_map_add_companies(companies)

    def _init_populate_tree(self, companies):
        self._init_companies = companies
        self._init_tree.delete(*self._init_tree.get_children())
        sent = self._init_sent_load()
        new_count = 0
        for idx, c in enumerate(companies):
            adresse = ', '.join(p for p in (c.get('strasse'), c.get('plz_ort'))
                                if p)
            already = c['email'] in sent
            tags = ('sent',) if already else ()
            if not already:
                new_count += 1
            self._init_tree.insert(
                '', 'end', iid=str(idx),
                values=(c['firma'], c['email'], adresse, c.get('website', '')),
                tags=tags)
        self._init_count_var.set(
            f'{len(companies)} Firmen · {new_count} neu · '
            f'{len(companies) - new_count} bereits kontaktiert')
        self._status(f'✓  {len(companies)} Firmen gefunden.')

    def _init_select_all(self):
        self._init_tree.selection_set(self._init_tree.get_children())

    def _init_select_none(self):
        self._init_tree.selection_remove(self._init_tree.get_children())

    def _init_generate_text(self):
        api_key = self._api_key_var.get().strip()
        if not api_key:
            messagebox.showwarning('API Key fehlt',
                                   'Bitte im Tab „KI-Assistent" einen Claude '
                                   'API Key eingeben.')
            return
        region = self._init_region_var.get().strip()
        self._init_log('🤖 Erstelle Initiativ-Text mit Claude ...')
        self._status('KI erstellt Initiativ-Text...')

        def _worker():
            try:
                res = initiativ.generate_email_template(api_key, region)
                def _apply():
                    self._init_betreff_var.set(res['betreff'])
                    self._init_text_widget.delete('1.0', 'end')
                    self._init_text_widget.insert('1.0', res['text'])
                    self._init_log('✓ KI-Text übernommen.')
                    self._status('✓  Initiativ-Text erstellt.')
                self.after(0, _apply)
            except Exception as exc:
                self._init_log(f'✗ Fehler: {exc}')
                self.after(0, lambda: self._status(f'Fehler: {exc}'))

        threading.Thread(target=_worker, daemon=True).start()

    def _init_selected_companies(self):
        result = []
        for iid in self._init_tree.selection():
            try:
                result.append(self._init_companies[int(iid)])
            except (ValueError, IndexError):
                continue
        return result

    def _init_log_application(self, firma):
        """Initiativbewerbung in die Übersichts-Tabelle eintragen."""
        firma = (firma or '').strip()
        if not firma:
            return
        with self._table_lock:
            rows = self._read_applications_rows()
            rows.append([firma, 'Initiativbewerbung', 'Gönderildi', today_de()])
            self._write_applications_rows(rows)

    def _init_send_selected(self):
        companies = self._init_selected_companies()
        if not companies:
            messagebox.showinfo('Keine Auswahl',
                                'Bitte zuerst Firmen in der Liste auswählen.')
            return

        sender = self._imap_email_var.get().strip()
        password = self._imap_password_var.get().strip()
        smtp_server = self._smtp_server_var.get().strip() or 'smtp.web.de'
        smtp_port_text = self._smtp_port_var.get().strip() or '587'
        if not sender or not password:
            messagebox.showwarning(
                'Zugangsdaten fehlen',
                'Bitte im Tab „E-Mail" Absender-E-Mail und App-Passwort '
                'eingeben.')
            return
        try:
            smtp_port = int(smtp_port_text)
        except ValueError:
            messagebox.showwarning('Ungültiger Port',
                                   'SMTP-Port muss eine Zahl sein (z.B. 587).')
            return
        try:
            delay = max(0.0, float(self._init_delay_var.get().strip() or '20'))
        except ValueError:
            delay = 20.0

        betreff = self._init_betreff_var.get().strip() or initiativ.DEFAULT_BETREFF
        body_template = self._init_text_widget.get('1.0', 'end-1c').strip()
        if not body_template:
            messagebox.showwarning('Text fehlt', 'E-Mail-Text darf nicht leer sein.')
            return

        skip_sent = self._init_skip_sent.get()
        attach_cv = self._init_attach_lebenslauf.get()
        sent = self._init_sent_load()

        todo = [c for c in companies
                if not (skip_sent and c['email'] in sent)]
        skipped = len(companies) - len(todo)
        if not todo:
            messagebox.showinfo(
                'Nichts zu senden',
                'Alle ausgewählten Firmen wurden bereits kontaktiert.')
            return

        if not messagebox.askyesno(
                'Initiativbewerbungen senden',
                f'{len(todo)} Initiativbewerbung(en) werden versendet'
                + (f'\n({skipped} bereits kontaktierte übersprungen)' if skipped else '')
                + f'\n\nPause zwischen Mails: {delay:.0f} Sek.\n\nFortfahren?'):
            return

        self._save_imap_settings()
        self._save_smtp_settings()
        self._status('Initiativbewerbungen werden gesendet...')

        def _worker():
            # Lebenslauf einmalig erzeugen und für alle Mails wiederverwenden.
            lebenslauf_path = None
            if attach_cv:
                try:
                    cfg = self._get_config()
                    folder = os.path.join(OUTPUT_DIR, 'bewerbungen',
                                          'Initiativbewerbung')
                    os.makedirs(folder, exist_ok=True)
                    lebenslauf_path = os.path.join(
                        folder, 'Hamza_Oeztuerk_Lebenslauf.pdf')
                    gen_l.generate(lebenslauf_path, cfg)
                    self._init_log('✓ Lebenslauf erstellt (Anhang).')
                except Exception as exc:
                    self._init_log(f'✗ Lebenslauf-Fehler: {exc}')
                    self.after(0, lambda: self._status(f'Fehler: {exc}'))
                    return

            ok, fail = 0, 0
            total = len(todo)
            smtp = None

            # Kopie jeder gesendeten Mail in den Ordner "Gesendet" legen.
            # SMTP tut das nicht; ohne diesen Schritt ist serverseitig nicht
            # nachvollziehbar, was rausgegangen ist. Scheitert das Ablegen,
            # gilt die Mail trotzdem als gesendet - sie ist bereits raus.
            imap_conn = None
            sent_folder = None
            try:
                imap_conn = imaplib.IMAP4_SSL(
                    self._imap_server_var.get().strip() or 'imap.web.de',
                    int(self._imap_port_var.get().strip() or '993'))
                imap_conn.login(sender, password)
                sent_folder = self._imap_find_sent_folder(imap_conn)
                if sent_folder:
                    self._init_log(f'Kopien landen in "{sent_folder}".')
                else:
                    self._init_log('! Kein Sent-Ordner gefunden – es werden '
                                   'keine Kopien abgelegt.')
            except Exception as exc:
                self._init_log(f'! IMAP-Ablage nicht möglich ({exc}). '
                               'Versand läuft trotzdem.')
                imap_conn = None
            try:
                for i, c in enumerate(todo, start=1):
                    firma = c['firma']
                    recipient = c['email']
                    self._init_log(f'[{i}/{total}] → {firma} <{recipient}>')
                    try:
                        msg = EmailMessage()
                        msg['From'] = sender
                        msg['To'] = recipient
                        msg['Subject'] = betreff
                        msg.set_content(initiativ.personalize(body_template, firma))
                        if lebenslauf_path and os.path.isfile(lebenslauf_path):
                            self._attach_file_to_message(msg, lebenslauf_path)

                        # Verbindung pro Mail neu aufbauen (robust gegen Timeouts).
                        if smtp_port == 465:
                            smtp = smtplib.SMTP_SSL(smtp_server, smtp_port,
                                                    timeout=30)
                        else:
                            smtp = smtplib.SMTP(smtp_server, smtp_port,
                                                timeout=30)
                            smtp.starttls()
                        smtp.login(sender, password)
                        smtp.send_message(msg)
                        smtp.quit()
                        smtp = None

                        ok += 1
                        sent.add(recipient)
                        self._init_sent_save(sent)
                        self._init_log_application(firma)

                        kopie = ''
                        if imap_conn is not None and sent_folder:
                            try:
                                self._imap_append_sent(imap_conn, sent_folder, msg)
                                kopie = ', Kopie abgelegt'
                            except Exception as exc:
                                kopie = f', Kopie fehlgeschlagen ({exc})'
                        self._init_log(f'    ✓ gesendet ({ok} ok){kopie}')
                    except Exception as exc:
                        fail += 1
                        self._init_log(f'    ✗ Fehler: {exc}')
                        if smtp is not None:
                            try:
                                smtp.quit()
                            except Exception:
                                pass
                            smtp = None

                    if i < total and delay:
                        time.sleep(delay)
            finally:
                if smtp is not None:
                    try:
                        smtp.quit()
                    except Exception:
                        pass
                if imap_conn is not None:
                    try:
                        imap_conn.logout()
                    except Exception:
                        pass

            self.after(0, lambda: self._uebersicht_refresh())
            self.after(0, lambda: self._status(
                f'✓  Initiativversand fertig. Gesendet: {ok}, Fehler: {fail}'))
            self.after(0, lambda: messagebox.showinfo(
                'Initiativversand abgeschlossen',
                f'Erfolgreich gesendet: {ok}\nFehlgeschlagen: {fail}'))

        threading.Thread(target=_worker, daemon=True).start()

    def _sync_mail_statuses(self):
        self._sync_mail_statuses_core(scan_all=False)

    def _sync_all_mail_statuses(self):
        self._sync_mail_statuses_core(scan_all=True)

    def _download_all_mail_pdfs(self):
        email_addr = self._imap_email_var.get().strip()
        password = self._imap_password_var.get().strip()
        server = self._imap_server_var.get().strip() or 'imap.web.de'
        port_text = self._imap_port_var.get().strip() or '993'

        if not email_addr or not password:
            messagebox.showwarning('Fehlende Angaben',
                                   'Bitte E-Mail-Adresse und App-Passwort eingeben.')
            return

        try:
            port = int(port_text)
        except ValueError:
            messagebox.showwarning('Ungültiger Port', 'Port muss eine Zahl sein (z.B. 993).')
            return

        # Persist credentials/settings so user is not asked again next time.
        self._save_imap_settings()

        self._status('Alle E-Mails werden als PDF heruntergeladen...')

        def _worker():
            try:
                saved, scanned, skipped = self._run_mail_pdf_export(
                    email_addr,
                    password,
                    server,
                    port,
                )
                self.after(0, lambda: self._status(
                    f'✓  PDF-Download abgeschlossen. Gespeichert: {saved}, Durchsucht: {scanned}, Übersprungen: {skipped}'))
                self.after(0, lambda: messagebox.showinfo(
                    'PDF-Download abgeschlossen',
                    f'Gespeicherte E-Mails: {saved}\nDurchsuchte E-Mails: {scanned}\nÜbersprungen/Duplikate: {skipped}\n\nOrdner: {MAIL_PDF_DIR}'))
            except Exception as exc:
                self.after(0, lambda: messagebox.showerror('IMAP-Fehler', str(exc)))
                self.after(0, lambda: self._status(f'IMAP-Fehler: {exc}'))

        threading.Thread(target=_worker, daemon=True).start()

    def _sync_mail_statuses_core(self, scan_all=False):
        email_addr = self._imap_email_var.get().strip()
        password = self._imap_password_var.get().strip()
        server = self._imap_server_var.get().strip() or 'imap.web.de'
        port_text = self._imap_port_var.get().strip() or '993'

        if not email_addr or not password:
            messagebox.showwarning('Fehlende Angaben',
                                   'Bitte E-Mail-Adresse und App-Passwort eingeben.')
            return

        try:
            port = int(port_text)
        except ValueError:
            messagebox.showwarning('Ungültiger Port', 'Port muss eine Zahl sein (z.B. 993).')
            return

        # Persist credentials/settings so user is not asked again next time.
        self._save_imap_settings()

        status_msg = 'Alle E-Mails werden synchronisiert...' if scan_all else 'IMAP-Synchronisierung läuft...'
        self._status(status_msg)

        def _worker():
            try:
                changed, added, scanned = self._run_mail_sync(
                    email_addr,
                    password,
                    server,
                    port,
                    self._imap_only_unseen_var.get(),
                    scan_all,
                )
                self.after(0, lambda: self._status(
                    f'✓  E-Mail-Sync abgeschlossen. Durchsucht: {scanned}, Aktualisiert: {changed}, Neu: {added}'))
                self.after(0, lambda: messagebox.showinfo(
                    'IMAP-Synchronisierung abgeschlossen',
                    f'Durchsuchte E-Mails: {scanned}\nAktualisierte Einträge: {changed}\nNeue Einträge: {added}'))
            except Exception as exc:
                self.after(0, lambda: messagebox.showerror('IMAP-Fehler', str(exc)))
                self.after(0, lambda: self._status(f'IMAP-Fehler: {exc}'))

        threading.Thread(target=_worker, daemon=True).start()

    def _run_mail_sync(self, email_addr, password, server, port, only_unseen, scan_all=False):
        # Tabellen-Lock über den gesamten Read-Modify-Write halten, damit
        # parallele Sync-/Sende-Vorgänge die CSV/XLSX nicht beschädigen.
        with self._table_lock:
            return self._run_mail_sync_locked(
                email_addr, password, server, port, only_unseen, scan_all)

    def _run_mail_sync_locked(self, email_addr, password, server, port, only_unseen, scan_all=False):
        rows = self._read_applications_rows()

        changed = 0
        added = 0
        scanned = 0

        conn = imaplib.IMAP4_SSL(server, port)
        try:
            conn.login(email_addr, password)
            conn.select('INBOX', readonly=True)

            if scan_all:
                criteria = 'ALL'
            elif only_unseen:
                criteria = '(UNSEEN)'
            else:
                since_date = (date.today() - timedelta(days=60)).strftime('%d-%b-%Y')
                criteria = f'(SINCE "{since_date}")'

            status, data = conn.search(None, criteria)
            if status != 'OK':
                raise RuntimeError('IMAP-Suche fehlgeschlagen.')

            msg_ids = data[0].split()
            if not scan_all:
                msg_ids = msg_ids[-80:]

            for msg_id in reversed(msg_ids):
                f_status, f_data = conn.fetch(msg_id, '(RFC822)')
                if f_status != 'OK' or not f_data:
                    continue

                raw = f_data[0][1]
                if not raw:
                    continue

                msg = email.message_from_bytes(raw)
                subject = self._decode_mime_header(msg.get('Subject', ''))
                from_raw = self._decode_mime_header(msg.get('From', ''))
                sender_name, sender_email = parseaddr(from_raw)
                body = self._extract_mail_text(msg)
                status_value = self._detect_mail_status(subject, body)
                li_company = self._extract_linkedin_company(subject, body)
                li_position = self._extract_linkedin_position(body, li_company)

                if not status_value:
                    continue

                scanned += 1
                date_value = self._mail_date_to_de(msg.get('Date', ''))

                row_idx = self._match_csv_row(rows, sender_name, sender_email, subject)
                if row_idx < 0 and li_company:
                    row_idx = self._match_csv_row(rows, li_company, sender_email, f'{subject} {li_company}')
                if row_idx >= 0:
                    row = rows[row_idx]
                    row = (row + [''] * 4)[:4]
                    if row[2] != status_value or row[3] != date_value:
                        row[2] = status_value
                        row[3] = date_value
                        rows[row_idx] = row
                        changed += 1
                else:
                    firma = li_company or self._guess_company_from_sender(sender_name, sender_email)
                    pos = li_position or subject.strip() or '(E-Mail Rückmeldung)'
                    rows.append([firma, pos, status_value, date_value])
                    added += 1

            self._write_applications_rows(rows)
        finally:
            try:
                conn.logout()
            except Exception:
                pass

        return changed, added, scanned

    def _run_mail_pdf_export(self, email_addr, password, server, port):
        _ensure_reportlab()
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        from reportlab.lib.units import mm
        from reportlab.lib.utils import simpleSplit

        os.makedirs(MAIL_PDF_DIR, exist_ok=True)
        run_dir = os.path.join(MAIL_PDF_DIR, date.today().strftime('%Y%m%d'))
        os.makedirs(run_dir, exist_ok=True)

        pdf_path = os.path.join(run_dir, f'all_mails_{date.today().strftime("%Y%m%d")}.pdf')

        saved = 0
        scanned = 0
        skipped = 0
        seen_ids = set()

        width, height = A4
        margin = 18 * mm
        x = margin
        max_width = width - (36 * mm)
        font_name = 'Helvetica'
        font_size = 10
        leading = 12
        y = height - margin

        c = canvas.Canvas(pdf_path, pagesize=A4)
        c.setFont(font_name, font_size)

        conn = imaplib.IMAP4_SSL(server, port)
        try:
            conn.login(email_addr, password)
            mailboxes = self._imap_list_mailboxes(conn)
            for mailbox in mailboxes:
                status, _ = conn.select(mailbox, readonly=True)
                if status != 'OK':
                    continue

                status, data = conn.search(None, 'ALL')
                if status != 'OK':
                    continue

                msg_ids = data[0].split() if data and data[0] else []
                for msg_id in msg_ids:
                    f_status, f_data = conn.fetch(msg_id, '(RFC822)')
                    if f_status != 'OK' or not f_data:
                        continue

                    raw = f_data[0][1]
                    if not raw:
                        continue

                    msg = email.message_from_bytes(raw)
                    scanned += 1

                    msg_id_val = (msg.get('Message-ID') or '').strip()
                    if msg_id_val and msg_id_val in seen_ids:
                        skipped += 1
                        continue
                    if msg_id_val:
                        seen_ids.add(msg_id_val)

                    subject = self._decode_mime_header(msg.get('Subject', ''))
                    from_raw = self._decode_mime_header(msg.get('From', ''))
                    to_raw = self._decode_mime_header(msg.get('To', ''))
                    cc_raw = self._decode_mime_header(msg.get('Cc', ''))
                    date_raw = msg.get('Date', '')
                    body = self._extract_mail_text(msg)
                    attachments = self._extract_attachment_names(msg)

                    if saved > 0:
                        c.showPage()
                        c.setFont(font_name, font_size)
                        y = height - margin

                    lines = [
                        f'=== MAIL {saved + 1} ===',
                        f'Mailbox: {mailbox}',
                        f'Date: {date_raw}',
                        f'From: {from_raw}',
                        f'To: {to_raw}',
                        f'Cc: {cc_raw}',
                        f'Subject: {subject}',
                        '',
                        '--- Body ---',
                        body or '(Empty body)',
                    ]
                    if attachments:
                        lines.extend(['', '--- Attachments ---'])
                        lines.extend(attachments)

                    y = self._write_mail_pdf_block(
                        c,
                        lines,
                        y,
                        height,
                        x,
                        max_width,
                        margin,
                        font_name,
                        font_size,
                        leading,
                        simpleSplit,
                    )
                    saved += 1
        finally:
            try:
                conn.logout()
            except Exception:
                pass
            # Canvas immer schließen – auch bei einem Fehler im Schleifenkörper –
            # damit keine unvollständige/gesperrte PDF-Datei zurückbleibt.
            try:
                c.save()
            except Exception:
                pass

        return saved, scanned, skipped

    # Kandidaten für den Ordner "Gesendet", in dieser Reihenfolge geprüft.
    _SENT_KANDIDATEN = ('gesendet', 'gesendete objekte', 'sent', 'sent items',
                        'sent messages', 'inbox.sent', 'inbox.gesendet')

    @classmethod
    def _imap_find_sent_folder(cls, conn):
        """Namen des Sent-Ordners ermitteln, sonst None."""
        try:
            status, data = conn.list()
        except Exception:
            return None
        if status != 'OK' or not data:
            return None

        namen = []
        for raw in data:
            if not raw:
                continue
            line = raw.decode('utf-8', errors='replace')
            flags, name = cls._parse_imap_list_line(line)
            if '\\Noselect' in flags:
                continue
            if not name:
                continue
            # Special-Use-Flag ist der zuverlässigste Hinweis.
            if '\\Sent' in flags:
                return name
            namen.append(name)

        for kandidat in cls._SENT_KANDIDATEN:
            for name in namen:
                if name.lower() == kandidat:
                    return name
        return None

    @staticmethod
    def _imap_append_sent(conn, folder, msg):
        """Kopie der gesendeten Nachricht im Sent-Ordner ablegen."""
        import imaplib as _imaplib
        from email.utils import parsedate_tz, mktime_tz
        zeit = None
        datum = msg.get('Date')
        if datum:
            zerlegt = parsedate_tz(datum)
            if zerlegt:
                zeit = _imaplib.Time2Internaldate(mktime_tz(zerlegt))
        conn.append(folder, '(\\Seen)', zeit, msg.as_bytes())

    @staticmethod
    def _imap_list_mailboxes(conn):
        status, data = conn.list()
        if status != 'OK' or not data:
            return ['INBOX']

        mailboxes = []
        for raw in data:
            if not raw:
                continue
            line = raw.decode('utf-8', errors='replace')
            flags, name = BewerbungsApp._parse_imap_list_line(line)
            if '\\Noselect' in flags:
                continue
            if name:
                mailboxes.append(name)

        return mailboxes or ['INBOX']

    @staticmethod
    def _parse_imap_list_line(line):
        # Example: (\HasNoChildren) "/" "INBOX"
        m = re.match(r'\((?P<flags>[^)]*)\)\s+"(?P<delim>.*?)"\s+"(?P<name>.*)"', line)
        if not m:
            return set(), ''
        flags = set(f.strip() for f in m.group('flags').split())
        name = m.group('name')
        return flags, name

    @staticmethod
    def _extract_attachment_names(msg):
        names = []
        if not msg.is_multipart():
            return names
        for part in msg.walk():
            disp = str(part.get('Content-Disposition', ''))
            if 'attachment' in disp.lower():
                filename = part.get_filename()
                if filename:
                    names.append(filename)
        return names

    @staticmethod
    def _write_mail_pdf_block(canvas_obj, lines, y, page_height, x, max_width,
                              margin, font_name, font_size, leading, simple_split):
        for line in lines:
            for wrapped in simple_split(line, font_name, font_size, max_width):
                if y < margin:
                    canvas_obj.showPage()
                    canvas_obj.setFont(font_name, font_size)
                    y = page_height - margin
                canvas_obj.drawString(x, y, wrapped)
                y -= leading
        return y

    # ── TAB: ÜBERSICHT ──────────────────────────────────────────────────────
    # Status values & colours
    _DURUM_OPTIONS = [
        'Başvuruldu',
        'Gönderildi',
        'Beworben',
        'Alındı Teyidi (İşlemde)',
        'Mülakat Daveti',
        'Olumsuz (Red)',
    ]
    _DURUM_COLORS = {
        'Başvuruldu':               '#6366F1',   # indigo
        'Gönderildi':               '#8B5CF6',   # violet
        'Beworben':                 '#2563EB',   # blue
        'Alındı Teyidi (İşlemde)':  '#059669',   # green
        'Mülakat Daveti':           '#0891B2',   # cyan
        'Olumsuz (Red)':            '#DC2626',   # red
    }

    def _build_uebersicht_tab(self, parent):
        container = tk.Frame(parent, bg=BG)
        container.pack(fill='both', expand=True, padx=0, pady=0)

        # ── Top toolbar ──
        toolbar = tk.Frame(container, bg=BG)
        toolbar.pack(fill='x', padx=16, pady=(12, 4))

        tk.Label(toolbar, text='📊  Bewerbungs-Übersicht', bg=BG, fg=NAVY,
                 font=(FONT, 13, 'bold')).pack(side='left')

        ttk.Button(toolbar, text='🔄  Aktualisieren',
                   style='Accent.TButton',
                   command=self._uebersicht_refresh).pack(side='right', padx=4)
        ttk.Button(toolbar, text='➕  Neue Bewerbung',
                   style='Gold.TButton',
                   command=self._uebersicht_add).pack(side='right', padx=4)
        ttk.Button(toolbar, text='🗑  Löschen',
                   style='Ghost.TButton',
                   command=self._uebersicht_delete).pack(side='right', padx=4)

        # ── Filter bar ──
        filter_bar = tk.Frame(container, bg=BG)
        filter_bar.pack(fill='x', padx=16, pady=(4, 4))

        tk.Label(filter_bar, text='Filter:', bg=BG, fg=FG,
                 font=(FONT, 10)).pack(side='left', padx=(0, 6))
        self._ub_filter_var = tk.StringVar(value='Alle')
        filter_opts = ['Alle'] + self._DURUM_OPTIONS
        filter_cb = ttk.Combobox(filter_bar, textvariable=self._ub_filter_var,
                                 values=filter_opts, state='readonly',
                                 width=28, font=(FONT, 10))
        filter_cb.pack(side='left', padx=(0, 12))
        filter_cb.bind('<<ComboboxSelected>>', lambda e: self._uebersicht_refresh())

        tk.Label(filter_bar, text='Suche:', bg=BG, fg=FG,
                 font=(FONT, 10)).pack(side='left', padx=(0, 6))
        self._ub_search_var = tk.StringVar()
        search_entry = ttk.Entry(filter_bar, textvariable=self._ub_search_var,
                                 width=30, font=(FONT, 10))
        search_entry.pack(side='left', padx=(0, 6))
        search_entry.bind('<KeyRelease>', lambda e: self._uebersicht_refresh())

        # ── Stats bar ──
        self._ub_stats_var = tk.StringVar(value='')
        tk.Label(filter_bar, textvariable=self._ub_stats_var, bg=BG, fg=FG_LIGHT,
                 font=(FONT, 9)).pack(side='right')

        # ── Treeview ──
        tree_frame = tk.Frame(container, bg=BG)
        tree_frame.pack(fill='both', expand=True, padx=16, pady=(4, 8))

        cols = ('firma', 'position', 'durum', 'tarih')
        self._ub_tree = ttk.Treeview(tree_frame, columns=cols,
                                     show='headings', selectmode='browse')
        self._ub_tree.heading('firma',    text='Şirket / Firma',    anchor='w')
        self._ub_tree.heading('position', text='Pozisyon / Stelle', anchor='w')
        self._ub_tree.heading('durum',    text='Durum / Sonuç',     anchor='w')
        self._ub_tree.heading('tarih',    text='Tarih',             anchor='center')

        self._ub_tree.column('firma',    width=240, minwidth=120, stretch=True)
        self._ub_tree.column('position', width=320, minwidth=150, stretch=True)
        self._ub_tree.column('durum',    width=180, minwidth=100, stretch=False)
        self._ub_tree.column('tarih',    width=100, minwidth=80,  stretch=False, anchor='center')

        # Style the Treeview
        style = ttk.Style()
        style.configure('Treeview',
                        font=(FONT, 10), rowheight=28,
                        background=WHITE, fieldbackground=WHITE,
                        foreground=FG)
        style.configure('Treeview.Heading',
                        font=(FONT, 10, 'bold'),
                        background=NAVY, foreground=WHITE)
        style.map('Treeview',
                  background=[('selected', ACCENT)],
                  foreground=[('selected', NAVY)])

        # Tag colours for each status
        for durum, color in self._DURUM_COLORS.items():
            tag = durum.replace(' ', '_').replace('(', '').replace(')', '')
            self._ub_tree.tag_configure(tag, foreground=color)

        vsb = ttk.Scrollbar(tree_frame, orient='vertical',
                            command=self._ub_tree.yview)
        self._ub_tree.configure(yscrollcommand=vsb.set)
        self._ub_tree.pack(side='left', fill='both', expand=True)
        vsb.pack(side='right', fill='y')

        # Double-click to edit
        self._ub_tree.bind('<Double-1>', self._uebersicht_edit)

        # ── Edit form (hidden by default) ──
        self._ub_edit_frame = tk.Frame(container, bg=WHITE,
                                       highlightbackground=CARD_BD,
                                       highlightthickness=1,
                                       padx=16, pady=12)

        tk.Label(self._ub_edit_frame, text='✏  Bewerbung bearbeiten',
                 bg=WHITE, fg=NAVY,
                 font=(FONT, 11, 'bold')).grid(row=0, column=0, columnspan=4,
                                                sticky='w', pady=(0, 8))

        tk.Label(self._ub_edit_frame, text='Firma:', bg=WHITE, fg=FG,
                 font=(FONT, 10)).grid(row=1, column=0, sticky='e', padx=(0, 6), pady=4)
        self._ub_edit_firma = tk.StringVar()
        ttk.Entry(self._ub_edit_frame, textvariable=self._ub_edit_firma,
                  width=40, font=(FONT, 10)).grid(row=1, column=1, sticky='w', pady=4)

        tk.Label(self._ub_edit_frame, text='Position:', bg=WHITE, fg=FG,
                 font=(FONT, 10)).grid(row=1, column=2, sticky='e', padx=(12, 6), pady=4)
        self._ub_edit_position = tk.StringVar()
        ttk.Entry(self._ub_edit_frame, textvariable=self._ub_edit_position,
                  width=40, font=(FONT, 10)).grid(row=1, column=3, sticky='w', pady=4)

        tk.Label(self._ub_edit_frame, text='Durum:', bg=WHITE, fg=FG,
                 font=(FONT, 10)).grid(row=2, column=0, sticky='e', padx=(0, 6), pady=4)
        self._ub_edit_durum = tk.StringVar()
        ttk.Combobox(self._ub_edit_frame, textvariable=self._ub_edit_durum,
                     values=self._DURUM_OPTIONS, width=28,
                     font=(FONT, 10)).grid(row=2, column=1, sticky='w', pady=4)

        tk.Label(self._ub_edit_frame, text='Tarih:', bg=WHITE, fg=FG,
                 font=(FONT, 10)).grid(row=2, column=2, sticky='e', padx=(12, 6), pady=4)
        self._ub_edit_tarih = tk.StringVar()
        ttk.Entry(self._ub_edit_frame, textvariable=self._ub_edit_tarih,
                  width=14, font=(FONT, 10)).grid(row=2, column=3, sticky='w', pady=4)

        btn_row = tk.Frame(self._ub_edit_frame, bg=WHITE)
        btn_row.grid(row=3, column=0, columnspan=4, sticky='e', pady=(8, 0))
        ttk.Button(btn_row, text='💾  Kaydet / Speichern',
                   style='Gold.TButton',
                   command=self._uebersicht_save_edit).pack(side='left', padx=4)
        ttk.Button(btn_row, text='✖  İptal',
                   style='Ghost.TButton',
                   command=self._uebersicht_cancel_edit).pack(side='left', padx=4)

        self._ub_editing_iid = None

        # Initial load
        self._uebersicht_refresh()

    # ── Übersicht helpers ────────────────────────────────────────────────────
    def _uebersicht_refresh(self):
        """Reload CSV/XLSX data into the treeview."""
        self._ub_tree.delete(*self._ub_tree.get_children())

        rows = self._read_applications_rows()
        data_rows = rows[1:] if rows else []    # skip header

        filter_val = self._ub_filter_var.get()
        search_val = self._ub_search_var.get().strip().lower()

        counts = {}
        visible = 0
        for row in data_rows:
            row = (row + [''] * 4)[:4]
            firma, position, durum, tarih = row[0], row[1], row[2], row[3]
            counts[durum] = counts.get(durum, 0) + 1

            # Apply filter
            if filter_val != 'Alle' and durum != filter_val:
                continue
            # Apply search
            if search_val and search_val not in f'{firma} {position}'.lower():
                continue

            tag = durum.replace(' ', '_').replace('(', '').replace(')', '')
            self._ub_tree.insert('', 'end', values=(firma, position, durum, tarih),
                                 tags=(tag,))
            visible += 1

        # Update stats
        total = len(data_rows)
        parts = []
        for d in self._DURUM_OPTIONS:
            c = counts.get(d, 0)
            if c:
                parts.append(f'{d}: {c}')
        stats = f'Toplam: {total}  |  Gösterilen: {visible}'
        if parts:
            stats += '  ·  ' + '  |  '.join(parts)
        self._ub_stats_var.set(stats)

        # Hide edit form
        self._uebersicht_cancel_edit()

    def _uebersicht_edit(self, event=None):
        """Open edit form for the selected row."""
        sel = self._ub_tree.selection()
        if not sel:
            return
        iid = sel[0]
        vals = self._ub_tree.item(iid, 'values')
        if not vals:
            return

        self._ub_editing_iid = iid
        self._ub_edit_firma.set(vals[0])
        self._ub_edit_position.set(vals[1])
        self._ub_edit_durum.set(vals[2])
        self._ub_edit_tarih.set(vals[3])

        self._ub_edit_frame.pack(fill='x', padx=16, pady=(0, 8))

    def _uebersicht_cancel_edit(self):
        """Hide the edit form."""
        self._ub_edit_frame.pack_forget()
        self._ub_editing_iid = None

    def _uebersicht_add(self):
        """Add a new empty entry via the edit form."""
        self._ub_tree.selection_remove(*self._ub_tree.selection())
        self._ub_editing_iid = '__NEW__'
        self._ub_edit_firma.set('')
        self._ub_edit_position.set('')
        self._ub_edit_durum.set('Başvuruldu')
        self._ub_edit_tarih.set(today_de())
        self._ub_edit_frame.pack(fill='x', padx=16, pady=(0, 8))

        # Override save to append instead of update
        self._ub_editing_iid = '__NEW__'

    def _uebersicht_save_edit(self):
        """Save changes from the edit form back to CSV/XLSX."""
        if not self._ub_editing_iid:
            return

        new_firma = self._ub_edit_firma.get().strip()
        new_position = self._ub_edit_position.get().strip()
        new_durum = self._ub_edit_durum.get().strip()
        new_tarih = self._ub_edit_tarih.get().strip()

        if not new_firma or not new_position:
            messagebox.showwarning('Uyarı', 'Firma ve Pozisyon boş olamaz.')
            return

        rows = self._read_applications_rows()

        if self._ub_editing_iid == '__NEW__':
            rows.append([new_firma, new_position, new_durum, new_tarih])
            self._write_applications_rows(rows)
            self._status_var.set(f'◆  Eklendi: {new_firma} – {new_durum}')
            self._uebersicht_refresh()
            return

        old_vals = self._ub_tree.item(self._ub_editing_iid, 'values')
        found = False
        for i in range(1, len(rows)):
            row = (rows[i] + [''] * 4)[:4]
            if row[0] == old_vals[0] and row[1] == old_vals[1] and row[3] == old_vals[3]:
                rows[i] = [new_firma, new_position, new_durum, new_tarih]
                found = True
                break

        if found:
            self._write_applications_rows(rows)
            self._status_var.set(f'◆  Güncellendi: {new_firma} – {new_durum}')
            self._uebersicht_refresh()
        else:
            messagebox.showerror('Hata', 'Kayıt bulunamadı.')

    def _uebersicht_delete(self):
        """Delete the selected row after confirmation."""
        sel = self._ub_tree.selection()
        if not sel:
            messagebox.showinfo('Bilgi', 'Lütfen silinecek satırı seçin.')
            return

        vals = self._ub_tree.item(sel[0], 'values')
        if not messagebox.askyesno('Silme Onayı',
                                   f'{vals[0]} – {vals[1]}\nBu kaydı silmek istiyor musunuz?'):
            return

        rows = self._read_applications_rows()
        new_rows = [rows[0]]   # keep header
        for i in range(1, len(rows)):
            row = (rows[i] + [''] * 4)[:4]
            if row[0] == vals[0] and row[1] == vals[1] and row[3] == vals[3]:
                continue
            new_rows.append(rows[i])

        self._write_applications_rows(new_rows)
        self._status_var.set(f'◆  Silindi: {vals[0]}')
        self._uebersicht_refresh()

    # ── TAB 4: PROFILE ──────────────────────────────────────────────────────
    def _build_profile_tab(self, parent):
        c = tk.Frame(parent, bg=BG)
        c.pack(fill='both', expand=True, padx=0, pady=0)

        profile_card = self._make_card(c, '👤  Gespeicherte Bewerbungs-Profile', padx=16, pady=12)

        list_frame = tk.Frame(profile_card, bg=WHITE)
        list_frame.pack(fill='both', expand=True)

        self._profile_list = tk.Listbox(
            list_frame, font=(FONT, 10), selectmode='single',
            bg='#F8FAFC', fg=FG, selectbackground=ACCENT,
            selectforeground=NAVY, relief='solid', borderwidth=1,
            highlightbackground=CARD_BD, highlightthickness=0,
            activestyle='none')
        self._profile_list.pack(side='left', fill='both', expand=True)
        sb = ttk.Scrollbar(list_frame, orient='vertical',
                           command=self._profile_list.yview)
        sb.pack(side='right', fill='y')
        self._profile_list.configure(yscrollcommand=sb.set)

        btn_frame = tk.Frame(profile_card, bg=WHITE)
        btn_frame.pack(fill='x', pady=(10, 0))
        ttk.Button(btn_frame, text='💾  Profil speichern',
                   style='Gold.TButton',
                   command=self._save_profile).pack(side='left', padx=4)
        ttk.Button(btn_frame, text='📂  Profil laden',
                   style='Accent.TButton',
                   command=self._load_profile).pack(side='left', padx=4)
        ttk.Button(btn_frame, text='🗑  Profil löschen',
                   style='Ghost.TButton',
                   command=self._delete_profile).pack(side='left', padx=4)

        self._refresh_profiles()

    # ── UI HELPERS ───────────────────────────────────────────────────────────
    def _section(self, parent, title, row):
        lbl = tk.Label(parent, text=title, bg=BG, fg=NAVY,
                       font=(FONT, 11, 'bold'))
        lbl.grid(row=row, column=0, columnspan=2, sticky='w',
                 padx=12, pady=(14, 4))
        return row + 1

    def _field(self, parent, key, label, default, row, width=40):
        tk.Label(parent, text=label, bg=BG, fg=FG,
                 font=(FONT, 10)).grid(
            row=row, column=0, sticky='e', padx=(12, 6), pady=3)
        var = tk.StringVar(value=default)
        self.vars[key] = var
        e = ttk.Entry(parent, textvariable=var, width=width,
                      font=(FONT, 10))
        e.grid(row=row, column=1, sticky='w', padx=(0, 12), pady=3)
        return row + 1

    def _field_card(self, parent, key, label, default, row, width=40):
        """Field helper for card (white bg) containers."""
        tk.Label(parent, text=label, bg=WHITE, fg=FG,
                 font=(FONT, 10)).grid(
            row=row, column=0, sticky='e', padx=(0, 8), pady=4)
        var = tk.StringVar(value=default)
        self.vars[key] = var
        e = ttk.Entry(parent, textvariable=var, width=width,
                      font=(FONT, 10))
        e.grid(row=row, column=1, sticky='w', padx=(0, 12), pady=4)
        return row + 1

    def _textarea(self, parent, key, label, default, row, height=5):
        tk.Label(parent, text=label, bg=BG, fg=NAVY,
                 font=(FONT, 11, 'bold')).grid(
            row=row, column=0, columnspan=2, sticky='w',
            padx=12, pady=(10, 2))
        row += 1
        txt = tk.Text(parent, height=height, width=90,
                      font=(FONT, 10), wrap='word',
                      bg='#F8FAFC', fg=FG, relief='solid', borderwidth=1,
                      highlightbackground=CARD_BD, highlightthickness=0,
                      padx=8, pady=6)
        txt.insert('1.0', default)
        txt.grid(row=row, column=0, columnspan=2, sticky='we',
                 padx=12, pady=(0, 6))
        self.vars[key] = txt
        return row + 1

    def _textarea_card(self, parent, key, label, default, row, height=5):
        """Textarea helper for card (white bg) containers."""
        tk.Label(parent, text=label, bg=WHITE, fg=NAVY,
                 font=(FONT, 11, 'bold')).grid(
            row=row, column=0, columnspan=2, sticky='w',
            padx=0, pady=(4, 2))
        row += 1
        txt = tk.Text(parent, height=height, width=90,
                      font=(FONT, 10), wrap='word',
                      bg='#F8FAFC', fg=FG, relief='solid', borderwidth=1,
                      highlightbackground=CARD_BD, highlightthickness=0,
                      padx=8, pady=6)
        txt.insert('1.0', default)
        txt.grid(row=row, column=0, columnspan=2, sticky='we',
                 padx=0, pady=(0, 6))
        self.vars[key] = txt
        return row + 1

    # ── CONFIG GATHERING ─────────────────────────────────────────────────────
    def _get_config(self):
        # Mit Nicht-Widget-Feldern (z.B. highlights von der KI) starten,
        # damit diese in die PDF-Generierung gelangen. Widget-Werte haben Vorrang.
        cfg = dict(self._extra_cfg)
        for key, widget in self.vars.items():
            if isinstance(widget, tk.StringVar):
                cfg[key] = widget.get()
            elif isinstance(widget, tk.Text):
                cfg[key] = widget.get('1.0', 'end-1c').strip()
        return cfg

    def _stash_extra_cfg(self, cfg):
        """Felder ohne eigenes Widget für die spätere Generierung merken."""
        self._extra_cfg = {k: v for k, v in cfg.items() if k not in self.vars}

    def _set_config(self, cfg):
        for key, widget in self.vars.items():
            val = cfg.get(key, '')
            if isinstance(widget, tk.StringVar):
                widget.set(val)
            elif isinstance(widget, tk.Text):
                widget.delete('1.0', 'end')
                widget.insert('1.0', val)

    def _load_defaults(self):
        """Populate with merged defaults."""
        defaults = {**gen_a.DEFAULT_CONFIG}
        defaults['datum'] = today_de()
        self._set_config(defaults)

    # ── OUTPUT PATHS ─────────────────────────────────────────────────────────
    def _make_output_path(self, doc_type):
        cfg = self._get_config()
        firma = safe_filename(cfg.get('firma', 'Firma'))
        stelle = safe_filename(cfg.get('stelle', 'Stelle'))
        folder = os.path.join(OUTPUT_DIR, 'bewerbungen', f'{firma} - {stelle}')
        os.makedirs(folder, exist_ok=True)
        if doc_type == 'Anschreiben':
            name = 'bewerbung_software_entwickler_herr_öztürk_anschreiben.pdf'
        elif doc_type == 'Bewerbung':
            name = 'bewerbung_software_entwickler_herr_öztürk.pdf'
        elif doc_type == 'Lebenslauf':
            name = 'bewerbung_software_entwickler_herr_öztürk_lebenslauf.pdf'
        elif doc_type == 'Kapak':
            name = 'bewerbung_software_entwickler_herr_öztürk_deckblatt.pdf'
        else:
            name = f'bewerbung_software_entwickler_herr_öztürk_{doc_type.lower()}.pdf'
        return os.path.join(folder, name)

    # ── GENERATION ───────────────────────────────────────────────────────────
    def _gen_lebenslauf(self):
        cfg = self._get_config()
        out = self._make_output_path('Lebenslauf')
        try:
            gen_l.generate(out, cfg)
            folder = os.path.dirname(out)
            self._status(f'✓  Lebenslauf erstellt: {folder}')
            self._open_pdf(out)
        except Exception as exc:
            messagebox.showerror('Fehler', str(exc))

    def _gen_anschreiben(self):
        cfg = self._get_config()
        out = self._make_output_path('Anschreiben')
        try:
            gen_a.generate(out, cfg)
            self._log_application(cfg)
            folder = os.path.dirname(out)
            self._status(f'✓  Anschreiben erstellt: {folder}')
            self._open_pdf(out)
        except Exception as exc:
            messagebox.showerror('Fehler', str(exc))

    def _gen_both(self):
        cfg = self._get_config()
        try:
            out_l = self._make_output_path('Lebenslauf')
            gen_l.generate(out_l, cfg)
            out_a = self._make_output_path('Anschreiben')
            gen_a.generate(out_a, cfg)
            self._log_application(cfg)
            folder = os.path.dirname(out_l)
            self._status(f'✓  Beide PDFs erstellt in: {os.path.basename(folder)}')
            self._open_pdf(out_l)
            self._open_pdf(out_a)
        except Exception as exc:
            messagebox.showerror('Fehler', str(exc))

    def _gen_bewerbung_pdf(self):
        cfg = self._get_config()
        try:
            out = self._make_output_path('Bewerbung')
            self._build_application_pdf(out, cfg)
            folder = os.path.dirname(out)
            self._status(f'✓  Bewerbungs-PDF erstellt: {os.path.basename(folder)}')
            self._open_pdf(out)
        except Exception as exc:
            messagebox.showerror('Fehler', str(exc))

    @staticmethod
    def _ensure_pdf_merger():
        if PDF_LIBS_LOADED and PdfReader is not None and PdfWriter is not None and Transformation is not None and PageObject is not None:
            return PdfReader, PdfWriter, Transformation, PageObject

        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'PyPDF2'])
        except Exception as exc:
            raise RuntimeError(
                'PyPDF2-Installation fehlgeschlagen. Bitte im Terminal ausführen: '
                'pip install PyPDF2'
            ) from exc

        try:
            from PyPDF2 import PdfReader as _PdfReader, PdfWriter as _PdfWriter, Transformation as _Transformation, PageObject as _PageObject
        except Exception as exc:
            raise RuntimeError('PyPDF2 installiert, aber Import fehlgeschlagen.') from exc

        return _PdfReader, _PdfWriter, _Transformation, _PageObject

    @staticmethod
    def _resolve_zeugnis_files():
        """Zeugnis-PDFs robust über Schlüsselwörter im Ordner auflösen.

        Unabhängig von wechselnden Dateinamen; gibt die gefundenen Pfade in
        definierter Reihenfolge zurück (jede Datei höchstens einmal).
        """
        if not os.path.isdir(ZEUGNIS_DIR):
            return []
        try:
            pdfs = [f for f in sorted(os.listdir(ZEUGNIS_DIR))
                    if f.lower().endswith('.pdf')]
        except OSError:
            return []

        resolved = []
        used = set()
        for keywords in _ZEUGNIS_KEYWORDS:
            for fname in pdfs:
                if fname in used:
                    continue
                low = fname.lower()
                if any(kw in low for kw in keywords):
                    resolved.append(os.path.join(ZEUGNIS_DIR, fname))
                    used.add(fname)
                    break
        return resolved

    def _build_application_pdf(self, output_path, cfg):
        PdfReader, PdfWriter, Transformation, PageObject = self._ensure_pdf_merger()

        kapak = self._make_output_path('Kapak')
        anschreiben = self._make_output_path('Anschreiben')
        lebenslauf = self._make_output_path('Lebenslauf')

        gen_k.generate(kapak, cfg)
        gen_a.generate(anschreiben, cfg)
        gen_l.generate(lebenslauf, cfg)

        # Generierte Dokumente sind Pflicht; Zeugnisse werden so weit
        # angehängt, wie sie im Zeugnis-Ordner vorhanden sind.
        required = [kapak, anschreiben, lebenslauf]
        missing = [p for p in required if not os.path.isfile(p)]
        if missing:
            raise FileNotFoundError('Fehlende Datei(en):\n' + '\n'.join(missing))

        parts = required + self._resolve_zeugnis_files()

        writer = PdfWriter()
        a4_width = 595.276
        a4_height = 841.890

        try:
            for path in parts:
                reader = PdfReader(path)
                for page in reader.pages:
                    orig_w = float(page.mediabox.width)
                    orig_h = float(page.mediabox.height)

                    if orig_w == 0 or orig_h == 0:
                        writer.add_page(page)
                        continue

                    # Zaten A4 boyutundaysa doğrudan ekle
                    if abs(orig_w - a4_width) < 1 and abs(orig_h - a4_height) < 1:
                        writer.add_page(page)
                        continue

                    # A4'e orantılı (en-boy bozmadan) sığdırmak için scale_factor
                    scale = min(a4_width / orig_w, a4_height / orig_h)
                    scaled_w = orig_w * scale
                    scaled_h = orig_h * scale
                    tx = (a4_width - scaled_w) / 2
                    ty = (a4_height - scaled_h) / 2

                    # Boş A4 sayfa oluştur, ölçeklenmiş içeriği üstüne yerleştir
                    blank = PageObject.create_blank_page(width=a4_width, height=a4_height)
                    page.add_transformation(
                        Transformation().scale(scale, scale).translate(tx, ty)
                    )
                    page.mediabox.lower_left = (0, 0)
                    page.mediabox.upper_right = (a4_width, a4_height)
                    blank.merge_page(page)
                    writer.add_page(blank)

            with open(output_path, "wb") as f:
                writer.write(f)
        except Exception as exc:
            raise RuntimeError(f'PDF-Zusammenführungsfehler: {exc}') from exc

    def _log_application(self, cfg):
        """Write or update application status in Bewerbungen table files."""
        firma = (cfg.get('firma') or '').strip()
        stelle = (cfg.get('stelle') or '').strip()
        datum = (cfg.get('datum') or '').strip() or today_de()

        if not firma or not stelle:
            return

        # Lock: verhindert verschachtelte Schreibvorgänge, wenn Senden/Sync
        # gleichzeitig laufen.
        with self._table_lock:
            rows = self._read_applications_rows()

            updated = False
            for i in range(1, len(rows)):
                row = rows[i]
                if len(row) < 4:
                    row = (row + [''] * 4)[:4]
                    rows[i] = row

                if row[0].strip().lower() == firma.lower() and row[1].strip().lower() == stelle.lower():
                    row[2] = 'Beworben'
                    row[3] = datum
                    updated = True
                    break

            if not updated:
                rows.append([firma, stelle, 'Beworben', datum])

            self._write_applications_rows(rows)

    # ── PROFILE MANAGEMENT ───────────────────────────────────────────────────
    def _profiles_path(self):
        os.makedirs(PROFILES_DIR, exist_ok=True)
        return PROFILES_DIR

    def _refresh_profiles(self):
        self._profile_list.delete(0, 'end')
        d = self._profiles_path()
        for f in sorted(os.listdir(d)):
            if f.endswith('.json'):
                self._profile_list.insert('end', f[:-5])

    def _save_profile(self):
        cfg = self._get_config()
        firma = cfg.get('firma', 'Firma').strip()
        stelle = cfg.get('stelle', 'Stelle').strip()
        name = f'{firma} – {stelle}'
        fname = safe_filename(name) + '.json'
        path = os.path.join(self._profiles_path(), fname)
        with open(path, 'w', encoding='utf-8') as fp:
            json.dump(cfg, fp, ensure_ascii=False, indent=2)
        self._refresh_profiles()
        self._status(f'✓  Profil gespeichert: {name}')

    def _load_profile(self):
        sel = self._profile_list.curselection()
        if not sel:
            messagebox.showinfo('Hinweis', 'Bitte zuerst ein Profil auswählen.')
            return
        name = self._profile_list.get(sel[0])
        path = os.path.join(self._profiles_path(), name + '.json')
        try:
            with open(path, 'r', encoding='utf-8') as fp:
                cfg = json.load(fp)
        except (json.JSONDecodeError, OSError) as exc:
            messagebox.showerror('Profil fehlerhaft',
                                 f'Profil konnte nicht geladen werden:\n{exc}')
            return
        self._stash_extra_cfg(cfg)
        self._set_config(cfg)
        self._status(f'✓  Profil geladen: {name}')

    def _delete_profile(self):
        sel = self._profile_list.curselection()
        if not sel:
            messagebox.showinfo('Hinweis', 'Bitte zuerst ein Profil auswählen.')
            return
        name = self._profile_list.get(sel[0])
        path = os.path.join(self._profiles_path(), name + '.json')
        if messagebox.askyesno('Profil löschen',
                               f'"{name}" wirklich löschen?'):
            os.remove(path)
            self._refresh_profiles()
            self._status(f'Profil gelöscht: {name}')

    # ── MISC ─────────────────────────────────────────────────────────────────
    def _status(self, msg):
        if threading.current_thread() is not threading.main_thread():
            self.after(0, lambda m=msg: self._status(m))
            return
        self._status_var.set(f'◆  {msg}')
        self.update_idletasks()

    def _open_pdf(self, path):
        try:
            if not os.path.isfile(path):
                raise FileNotFoundError(path)
            if sys.platform == 'win32':
                os.startfile(path)
            elif sys.platform == 'darwin':
                subprocess.Popen(['open', path])
            else:
                subprocess.Popen(['xdg-open', path])
        except Exception as exc:
            self._status(f'Konnte PDF nicht öffnen: {exc}')

    def _open_folder(self):
        """Open the bewerbungen base folder."""
        folder = os.path.join(OUTPUT_DIR, 'bewerbungen')
        try:
            os.makedirs(folder, exist_ok=True)
            if sys.platform == 'win32':
                os.startfile(folder)
            elif sys.platform == 'darwin':
                subprocess.Popen(['open', folder])
            else:
                subprocess.Popen(['xdg-open', folder])
        except Exception as exc:
            self._status(f'Konnte Ordner nicht öffnen: {exc}')


# ─── ENTRY POINT ─────────────────────────────────────────────────────────────
if __name__ == '__main__':
    app = BewerbungsApp()
    app.mainloop()
