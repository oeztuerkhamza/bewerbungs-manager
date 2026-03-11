#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bewerbungs-Manager – GUI zum Erstellen von Lebenslauf & Anschreiben
Hamza Öztürk · 10.03.2026
"""

import json
import os
import subprocess
import sys
import threading
import tkinter as tk
from datetime import date
from tkinter import filedialog, messagebox, ttk

# ─── MODULE IMPORTS ──────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

import generate_anschreiben as gen_a
import generate_lebenslauf as gen_l
import ki_assistent as ki

# ─── CONSTANTS ───────────────────────────────────────────────────────────────
PROFILES_DIR  = os.path.join(SCRIPT_DIR, 'bewerbungen')
OUTPUT_DIR    = SCRIPT_DIR
API_KEY_FILE  = os.path.join(SCRIPT_DIR, '.claude_api_key')
NAVY  = '#1B3764'
WHITE = '#FFFFFF'
BG    = '#F5F6F8'
BG2   = '#EBEDF2'
FG    = '#1F1F1F'
GRAY  = '#777777'
ACCENT = '#2A4F8A'


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
        self.title('Bewerbungs-Manager – Hamza Öztürk')
        self.configure(bg=BG)
        self.minsize(960, 780)
        self.resizable(True, True)

        # Centre on screen
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        w, h = 1020, 830
        self.geometry(f'{w}x{h}+{(sw-w)//2}+{(sh-h)//2}')

        self._build_ui()
        self._load_defaults()

    # ── UI BUILDING ──────────────────────────────────────────────────────────
    def _build_ui(self):
        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure('Navy.TButton',
                        background=NAVY, foreground=WHITE,
                        font=('Calibri', 10, 'bold'), padding=(14, 6))
        style.map('Navy.TButton',
                  background=[('active', ACCENT), ('pressed', ACCENT)])
        style.configure('Accent.TButton',
                        background=ACCENT, foreground=WHITE,
                        font=('Calibri', 10), padding=(10, 5))
        style.map('Accent.TButton',
                  background=[('active', NAVY), ('pressed', NAVY)])
        style.configure('TLabel', background=BG, foreground=FG,
                        font=('Calibri', 10))
        style.configure('Header.TLabel', background=NAVY, foreground=WHITE,
                        font=('Calibri', 14, 'bold'), padding=(12, 8))
        style.configure('Section.TLabel', background=BG, foreground=NAVY,
                        font=('Calibri', 11, 'bold'))
        style.configure('TFrame', background=BG)
        style.configure('Card.TFrame', background=WHITE, relief='flat')
        style.configure('TNotebook', background=BG)
        style.configure('TNotebook.Tab', font=('Calibri', 10, 'bold'),
                        padding=(16, 6))
        style.configure('TEntry', font=('Calibri', 10))

        # ── HEADER ──
        hdr = tk.Frame(self, bg=NAVY, height=48)
        hdr.pack(fill='x')
        hdr.pack_propagate(False)
        tk.Label(hdr, text='  BEWERBUNGS-MANAGER', bg=NAVY, fg=WHITE,
                 font=('Calibri', 14, 'bold'), anchor='w').pack(
                     side='left', padx=8, fill='both', expand=True)

        # ── NOTEBOOK ──
        nb = ttk.Notebook(self)
        nb.pack(fill='both', expand=True, padx=10, pady=(8, 0))

        self._tab_ki        = self._make_tab(nb, '🤖 KI-Assistent')
        self._tab_stelle    = self._make_tab(nb, 'Stelle & Firma')
        self._tab_anschr    = self._make_tab(nb, 'Anschreiben-Text')
        self._tab_email     = self._make_tab(nb, '✉ E-Mail')
        self._tab_profile   = self._make_tab(nb, 'Profile')

        self._build_ki_tab(self._tab_ki)
        self._build_stelle_tab(self._tab_stelle)
        self._build_anschreiben_tab(self._tab_anschr)
        self._build_email_tab(self._tab_email)
        self._build_profile_tab(self._tab_profile)
        self._nb = nb

        # ── BOTTOM BUTTONS ──
        bar = tk.Frame(self, bg=BG2, height=56)
        bar.pack(fill='x', side='bottom', pady=(4, 0))
        bar.pack_propagate(False)

        inner = tk.Frame(bar, bg=BG2)
        inner.pack(expand=True)

        ttk.Button(inner, text='📄  Lebenslauf erstellen',
                   style='Navy.TButton',
                   command=self._gen_lebenslauf).pack(
                       side='left', padx=6, pady=10)
        ttk.Button(inner, text='✉  Anschreiben erstellen',
                   style='Navy.TButton',
                   command=self._gen_anschreiben).pack(
                       side='left', padx=6, pady=10)
        ttk.Button(inner, text='📑  Beide erstellen',
                   style='Navy.TButton',
                   command=self._gen_both).pack(
                       side='left', padx=6, pady=10)
        ttk.Button(inner, text='📂  Ordner öffnen',
                   style='Accent.TButton',
                   command=self._open_folder).pack(
                       side='left', padx=6, pady=10)

        # ── STATUS BAR ──
        self._status_var = tk.StringVar(value='Bereit.')
        tk.Label(self, textvariable=self._status_var, bg=NAVY, fg=WHITE,
                 font=('Calibri', 9), anchor='w', padx=8).pack(
                     fill='x', side='bottom')

    def _make_tab(self, nb, title):
        frame = ttk.Frame(nb, style='TFrame')
        nb.add(frame, text=f'  {title}  ')
        return frame

    # ── TAB 0: KI-ASSISTENT ─────────────────────────────────────────────
    def _build_ki_tab(self, parent):
        canvas = tk.Canvas(parent, bg=BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient='vertical',
                                  command=canvas.yview)
        scroll_frame = ttk.Frame(canvas, style='TFrame')
        scroll_frame.bind('<Configure>',
                          lambda e: canvas.configure(
                              scrollregion=canvas.bbox('all')))
        canvas.create_window((0, 0), window=scroll_frame, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        c = scroll_frame
        row = 0

        # Description
        desc = ttk.Label(
            c, style='TLabel', wraplength=800,
            text='Stellenanzeige einfügen (URL oder Text) \u2192 '
                 'Claude analysiert die Anforderungen und erstellt '
                 'maßgeschneiderte Bewerbungsunterlagen auf Basis '
                 'deines Lebenslaufs.')
        desc.grid(row=row, column=0, columnspan=3, sticky='w',
                  padx=12, pady=(12, 8))
        row += 1

        # API Key
        row = self._ki_section(c, 'CLAUDE API KEY', row)
        ttk.Label(c, text='API Key').grid(
            row=row, column=0, sticky='e', padx=(12, 6), pady=3)
        self._api_key_var = tk.StringVar(value=self._load_api_key())
        key_entry = ttk.Entry(c, textvariable=self._api_key_var,
                              width=60, font=('Calibri', 10), show='•')
        key_entry.grid(row=row, column=1, sticky='w', padx=(0, 6), pady=3)
        ttk.Button(c, text='Speichern', style='Accent.TButton',
                   command=self._save_api_key).grid(
                       row=row, column=2, sticky='w', padx=4, pady=3)
        row += 1

        # Visibility toggle
        self._show_key = tk.BooleanVar(value=False)
        def _toggle_key():
            key_entry.configure(show='' if self._show_key.get() else '•')
        tk.Checkbutton(c, text='Key anzeigen', variable=self._show_key,
                       command=_toggle_key, bg=BG, fg=FG,
                       font=('Calibri', 9), activebackground=BG).grid(
                           row=row, column=1, sticky='w', padx=0, pady=0)
        row += 1

        # Job URL
        row = self._ki_section(c, 'STELLENANZEIGE', row)
        ttk.Label(c, text='URL').grid(
            row=row, column=0, sticky='e', padx=(12, 6), pady=3)
        self._job_url_var = tk.StringVar()
        ttk.Entry(c, textvariable=self._job_url_var, width=70,
                  font=('Calibri', 10)).grid(
                      row=row, column=1, columnspan=2, sticky='w',
                      padx=(0, 12), pady=3)
        row += 1

        # OR: paste job text
        ttk.Label(c, text='Oder Text einfügen:',
                  style='Section.TLabel').grid(
                      row=row, column=0, columnspan=3, sticky='w',
                      padx=12, pady=(8, 2))
        row += 1
        self._job_text_widget = tk.Text(
            c, height=10, width=95, font=('Calibri', 10),
            wrap='word', bg=WHITE, fg=FG, relief='flat',
            borderwidth=1, padx=6, pady=4)
        self._job_text_widget.grid(
            row=row, column=0, columnspan=3, sticky='we',
            padx=12, pady=(0, 6))
        row += 1

        # Extra instructions
        row = self._ki_section(c, 'ZUSÄTZLICHE HINWEISE (OPTIONAL)', row)
        self._extra_instr_widget = tk.Text(
            c, height=3, width=95, font=('Calibri', 10),
            wrap='word', bg=WHITE, fg=FG, relief='flat',
            borderwidth=1, padx=6, pady=4)
        self._extra_instr_widget.insert('1.0',
            'z.B.: Betone Docker-Erfahrung stärker, '
            'erwähne Remote-Bereitschaft...')
        self._extra_instr_widget.grid(
            row=row, column=0, columnspan=3, sticky='we',
            padx=12, pady=(0, 6))
        row += 1

        # Generate button
        btn_frame = ttk.Frame(c, style='TFrame')
        btn_frame.grid(row=row, column=0, columnspan=3, pady=(8, 4))
        ttk.Button(btn_frame,
                   text='🤖  KI-Bewerbung generieren',
                   style='Navy.TButton',
                   command=self._ki_generate).pack(side='left', padx=6)
        ttk.Button(btn_frame,
                   text='🤖 + 📄  Generieren & PDFs erstellen',
                   style='Navy.TButton',
                   command=self._ki_generate_and_pdf).pack(side='left', padx=6)
        row += 1

        # Log output
        row = self._ki_section(c, 'LOG', row)
        self._ki_log = tk.Text(
            c, height=8, width=95, font=('Consolas', 9),
            wrap='word', bg='#1E1E1E', fg='#D4D4D4', relief='flat',
            borderwidth=1, padx=6, pady=4, state='disabled')
        self._ki_log.grid(row=row, column=0, columnspan=3, sticky='we',
                          padx=12, pady=(0, 12))

    def _ki_section(self, parent, title, row):
        lbl = ttk.Label(parent, text=title, style='Section.TLabel')
        lbl.grid(row=row, column=0, columnspan=3, sticky='w',
                 padx=12, pady=(14, 4))
        return row + 1

    def _log(self, msg):
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
        canvas = tk.Canvas(parent, bg=BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient='vertical',
                                  command=canvas.yview)
        scroll_frame = ttk.Frame(canvas, style='TFrame')
        scroll_frame.bind('<Configure>',
                          lambda e: canvas.configure(
                              scrollregion=canvas.bbox('all')))
        canvas.create_window((0, 0), window=scroll_frame, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        # Bind mousewheel
        def _on_mousewheel(e):
            canvas.yview_scroll(int(-1 * (e.delta / 120)), 'units')
        canvas.bind_all('<MouseWheel>', _on_mousewheel)

        c = scroll_frame
        self.vars = {}
        row = 0

        row = self._section(c, 'STELLE', row)
        row = self._field(c, 'stelle', 'Stellenbezeichnung',
                          'Fullstack Entwickler', row)
        row = self._field(c, 'stelle_detail', 'Technologien (|‑getrennt)',
                          'C# | .NET | Angular', row)
        row = self._field(c, 'betreff', 'Betreff-Zeile',
                          'Bewerbung als Fullstack Entwickler – C# / .NET / Angular',
                          row, width=70)
        row = self._field(c, 'datum', 'Datum', today_de(), row)

        row = self._section(c, 'FIRMA', row)
        row = self._field(c, 'firma', 'Firmenname', 'Musterfirma GmbH', row)
        row = self._field(c, 'ansprechpartner', 'Ansprechpartner',
                          'Frau / Herrn Mustermann', row)
        row = self._field(c, 'firma_strasse', 'Straße', 'Musterstraße 1', row)
        row = self._field(c, 'firma_plz_ort', 'PLZ + Ort',
                          '79098 Freiburg im Breisgau', row)

        row = self._section(c, 'ANREDE & ANLAGEN', row)
        row = self._field(c, 'anrede', 'Anrede',
                          'Sehr geehrte Damen und Herren,', row, width=50)
        row = self._field(c, 'anlagen', 'Anlagen',
                          'Lebenslauf, Arbeitszeugnisse, Zertifikate',
                          row, width=60)

    # ── TAB 2: ANSCHREIBEN-TEXT ──────────────────────────────────────────────
    def _build_anschreiben_tab(self, parent):
        canvas = tk.Canvas(parent, bg=BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient='vertical',
                                  command=canvas.yview)
        scroll_frame = ttk.Frame(canvas, style='TFrame')
        scroll_frame.bind('<Configure>',
                          lambda e: canvas.configure(
                              scrollregion=canvas.bbox('all')))
        canvas.create_window((0, 0), window=scroll_frame, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        c = scroll_frame
        row = 0
        note = ttk.Label(c, text='HTML-Tags wie <b>fett</b> sind erlaubt.',
                         style='TLabel', foreground=GRAY)
        note.grid(row=row, column=0, columnspan=2, sticky='w',
                  padx=12, pady=(10, 4))
        row += 1

        defaults = gen_a.DEFAULT_CONFIG
        for i in range(1, 6):
            key = f'absatz_{i}'
            row = self._textarea(c, key, f'Absatz {i}',
                                 defaults.get(key, ''), row)

    # ── TAB 3: E-MAIL ───────────────────────────────────────────────────────
    def _build_email_tab(self, parent):
        c = ttk.Frame(parent, style='TFrame')
        c.pack(fill='both', expand=True, padx=12, pady=12)

        ttk.Label(c, text='BEWERBUNGS-E-MAIL',
                  style='Section.TLabel').pack(anchor='w', pady=(0, 8))

        ttk.Label(c, text='KI generiert diesen Text automatisch. '
                  'Du kannst ihn bearbeiten und dann kopieren.',
                  style='TLabel', foreground=GRAY).pack(
                      anchor='w', pady=(0, 10))

        # Betreff
        bf = ttk.Frame(c, style='TFrame')
        bf.pack(fill='x', pady=(0, 6))
        ttk.Label(bf, text='Betreff:', style='Section.TLabel').pack(
            side='left', padx=(0, 8))
        self._email_betreff_var = tk.StringVar(
            value='Bewerbung als Fullstack Entwickler – Hamza Öztürk')
        ttk.Entry(bf, textvariable=self._email_betreff_var,
                  width=70, font=('Calibri', 10)).pack(
                      side='left', fill='x', expand=True)

        # Email body
        self._email_text_widget = tk.Text(
            c, height=18, font=('Calibri', 10), wrap='word',
            bg=WHITE, fg=FG, relief='flat', borderwidth=1,
            padx=8, pady=8)
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
        self._email_text_widget.pack(fill='both', expand=True, pady=(0, 8))

        # Buttons
        btn_frame = ttk.Frame(c, style='TFrame')
        btn_frame.pack(fill='x')
        ttk.Button(btn_frame, text='📋  Betreff kopieren',
                   style='Accent.TButton',
                   command=self._copy_email_betreff).pack(
                       side='left', padx=4)
        ttk.Button(btn_frame, text='📋  E-Mail-Text kopieren',
                   style='Navy.TButton',
                   command=self._copy_email_text).pack(
                       side='left', padx=4)
        ttk.Button(btn_frame, text='📋  Alles kopieren',
                   style='Navy.TButton',
                   command=self._copy_email_all).pack(
                       side='left', padx=4)

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

    # ── TAB 4: PROFILE ──────────────────────────────────────────────────────
    def _build_profile_tab(self, parent):
        c = ttk.Frame(parent, style='TFrame')
        c.pack(fill='both', expand=True, padx=12, pady=12)

        ttk.Label(c, text='Gespeicherte Bewerbungs-Profile',
                  style='Section.TLabel').pack(anchor='w', pady=(0, 8))

        list_frame = ttk.Frame(c)
        list_frame.pack(fill='both', expand=True)

        self._profile_list = tk.Listbox(
            list_frame, font=('Calibri', 10), selectmode='single',
            bg=WHITE, fg=FG, selectbackground=NAVY, selectforeground=WHITE,
            relief='flat', borderwidth=1)
        self._profile_list.pack(side='left', fill='both', expand=True)
        sb = ttk.Scrollbar(list_frame, orient='vertical',
                           command=self._profile_list.yview)
        sb.pack(side='right', fill='y')
        self._profile_list.configure(yscrollcommand=sb.set)

        btn_frame = ttk.Frame(c)
        btn_frame.pack(fill='x', pady=(8, 0))
        ttk.Button(btn_frame, text='Profil speichern',
                   style='Navy.TButton',
                   command=self._save_profile).pack(side='left', padx=4)
        ttk.Button(btn_frame, text='Profil laden',
                   style='Accent.TButton',
                   command=self._load_profile).pack(side='left', padx=4)
        ttk.Button(btn_frame, text='Profil löschen',
                   style='Accent.TButton',
                   command=self._delete_profile).pack(side='left', padx=4)

        self._refresh_profiles()

    # ── UI HELPERS ───────────────────────────────────────────────────────────
    def _section(self, parent, title, row):
        lbl = ttk.Label(parent, text=title, style='Section.TLabel')
        lbl.grid(row=row, column=0, columnspan=2, sticky='w',
                 padx=12, pady=(14, 4))
        return row + 1

    def _field(self, parent, key, label, default, row, width=40):
        ttk.Label(parent, text=label).grid(
            row=row, column=0, sticky='e', padx=(12, 6), pady=3)
        var = tk.StringVar(value=default)
        self.vars[key] = var
        e = ttk.Entry(parent, textvariable=var, width=width,
                      font=('Calibri', 10))
        e.grid(row=row, column=1, sticky='w', padx=(0, 12), pady=3)
        return row + 1

    def _textarea(self, parent, key, label, default, row, height=5):
        ttk.Label(parent, text=label, style='Section.TLabel').grid(
            row=row, column=0, columnspan=2, sticky='w',
            padx=12, pady=(10, 2))
        row += 1
        txt = tk.Text(parent, height=height, width=90,
                      font=('Calibri', 10), wrap='word',
                      bg=WHITE, fg=FG, relief='flat', borderwidth=1,
                      padx=6, pady=4)
        txt.insert('1.0', default)
        txt.grid(row=row, column=0, columnspan=2, sticky='we',
                 padx=12, pady=(0, 6))
        self.vars[key] = txt   # store widget reference for Text widgets
        return row + 1

    # ── CONFIG GATHERING ─────────────────────────────────────────────────────
    def _get_config(self):
        cfg = {}
        for key, widget in self.vars.items():
            if isinstance(widget, tk.StringVar):
                cfg[key] = widget.get()
            elif isinstance(widget, tk.Text):
                cfg[key] = widget.get('1.0', 'end-1c').strip()
        return cfg

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
        defaults['stelle_detail'] = 'C# | .NET | Angular'
        defaults['datum'] = today_de()
        self._set_config(defaults)

    # ── OUTPUT PATHS ─────────────────────────────────────────────────────────
    def _make_output_path(self, doc_type):
        cfg = self._get_config()
        firma = safe_filename(cfg.get('firma', 'Firma'))
        stelle = safe_filename(cfg.get('stelle', 'Stelle'))
        folder = os.path.join(OUTPUT_DIR, 'bewerbungen', f'{firma} - {stelle}')
        os.makedirs(folder, exist_ok=True)
        name = f'Hamza_Oeztuerk_{doc_type}.pdf'
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
            folder = os.path.dirname(out_l)
            self._status(f'✓  Beide PDFs erstellt in: {os.path.basename(folder)}')
            self._open_pdf(out_l)
            self._open_pdf(out_a)
        except Exception as exc:
            messagebox.showerror('Fehler', str(exc))

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
        with open(path, 'r', encoding='utf-8') as fp:
            cfg = json.load(fp)
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
        self._status_var.set(msg)
        self.update_idletasks()

    @staticmethod
    def _open_pdf(path):
        if sys.platform == 'win32':
            os.startfile(path)
        elif sys.platform == 'darwin':
            subprocess.Popen(['open', path])
        else:
            subprocess.Popen(['xdg-open', path])

    @staticmethod
    def _open_folder():
        """Open the bewerbungen base folder."""
        folder = os.path.join(OUTPUT_DIR, 'bewerbungen')
        os.makedirs(folder, exist_ok=True)
        if sys.platform == 'win32':
            os.startfile(folder)
        else:
            subprocess.Popen(['xdg-open', folder])


# ─── ENTRY POINT ─────────────────────────────────────────────────────────────
if __name__ == '__main__':
    app = BewerbungsApp()
    app.mainloop()
