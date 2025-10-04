import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox
from ui import make_back_arrow, apply_theme, rounded_outline, smart_tinted_bg, create_card, refresh_card_tints, ensure_card_control_backgrounds, ensure_ttk_contrast_styles, ensure_ttk_label_contrast
from tkinter import ttk
import os
import shutil
from datetime import datetime
import importlib
import sys

DB_NAME = "coop.db"


class IOSSwitch(tk.Frame):
    """Minimal iOS‑style switch built on a Canvas.
    variable: tk.BooleanVar; command: callable; bg: parent bg.
    """
    def __init__(self, parent, variable: tk.BooleanVar, command=None, bg: str | None = None):
        super().__init__(parent, bd=0, highlightthickness=0, bg=bg or (parent.cget('bg') if hasattr(parent,'cget') else '#fff'))
        self.var = variable
        self.command = command
        self.canvas = tk.Canvas(self, width=56, height=30, bd=0, highlightthickness=0, bg=self.cget('bg'))
        self.canvas.pack()
        self.canvas.bind('<Button-1>', self._toggle)
        try:
            self.var.trace_add('write', lambda *a: self.redraw())
        except Exception:
            pass
        self.redraw()

    def set_bg(self, color: str) -> None:
        try:
            self.configure(bg=color)
            self.canvas.configure(bg=color)
        except Exception:
            pass
        self.redraw()

    def _toggle(self, _e=None):
        try:
            self.var.set(not bool(self.var.get()))
        except Exception:
            pass
        try:
            if callable(self.command):
                self.command()
        except Exception:
            pass
        self.redraw()

    def redraw(self) -> None:
        on = bool(self.var.get())
        w, h, r = 56, 30, 14
        track_on, track_off, knob = '#34C759', '#d5d5d5', '#ffffff'
        try:
            self.canvas.delete('all')
            x0, y0, x1, y1 = 2, 2, w-2, h-2
            color = track_on if on else track_off
            self.canvas.create_oval(x0, y0, y0+2*r, y0+2*r, fill=color, outline=color)
            self.canvas.create_oval(x1-2*r, y0, x1, y0+2*r, fill=color, outline=color)
            self.canvas.create_rectangle(x0+r, y0, x1-r, y0+2*r, fill=color, outline=color)
            kx = x1 - r - 2 if on else x0 + r + 2
            self.canvas.create_oval(kx-r, y0, kx+r, y0+2*r, fill=knob, outline='#cccccc')
        except Exception:
            pass


class SettingsFrame(tk.Frame):
    def __init__(self, parent: tk.Misc, controller) -> None:
        super().__init__(parent)
        self.controller = controller
        # Guard to prevent programmatic updates from firing change handlers
        self._suspend_base_pt_events = False

        header = tk.Frame(self)
        header.pack(fill='x')
        # Keep a reference for theme refreshes
        self.header_frame = header
        self.back_arrow = make_back_arrow(header, self.go_back)
        self.back_arrow.pack(side='left', padx=(10,6), pady=(10,6))
        tk.Label(header, text="Ayarlar", font='TkHeadingFont').pack(side='left', pady=(16,6))

        # Tabs container
        nb = ttk.Notebook(self)
        nb.pack(fill='both', expand=True)
        self.nb = nb

        tab_name = tk.Frame(nb)
        tab_style = tk.Frame(nb)
        tab_db = tk.Frame(nb)
        self.tab_db = tab_db
        nb.add(tab_name, text='Okul Adı')
        nb.add(tab_style, text='Yazı Boyutu ve Tema')
        nb.add(tab_db, text='Veri Tabanı')

        # PERM HOOK
        try:
            perms = getattr(self.controller, 'user_permissions', None)
            if (perms is not None) and ('db' not in perms):
                try:
                    nb.forget(tab_db)
                except Exception:
                    pass
        except Exception:
            pass
        def _autosize_card(card: tk.Frame, inner: tk.Frame, min_w: int = 560, pad: int = 12, min_h=None) -> None:
            try:
                inner.update_idletasks()
                req_h = inner.winfo_reqheight()
                req_w = max(min_w, inner.winfo_reqwidth() + 2*pad)
                height = req_h + 2*pad
                try:
                    if min_h is not None:
                        height = max(height, int(min_h))
                except Exception:
                    pass
                card.configure(width=req_w, height=height)
            except Exception:
                # Ölçüm başarısız olursa güvenli bir yükseklik kullan
                card.configure(width=min_w, height=200)
        name_holder = tk.Frame(tab_name)
        name_holder.pack(fill='x', padx=20, pady=(10, 4))
        name_card, name_inner = create_card(name_holder, radius=12, padding=12, border='#888')
        self.name_card = name_card
        self.name_inner = name_inner
        name_card.pack(anchor='center', fill='x')
        tint_name = name_inner.cget('bg')
        tk.Label(name_inner, text="Okul adı (Rapor Başlığı)", font='TkHeadingFont', bg=tint_name).pack(anchor='center')
        row_name = tk.Frame(name_inner, bg=tint_name)
        row_name.pack(pady=(6, 0), anchor='center')
        self.entry_school = ttk.Entry(row_name, width=40)
        # Metin kutusu ile buton arasÄ±nÄ± aÃ§mak iÃ§in boÅŸluklarÄ± artÄ±r
        self.entry_school.pack(side='left', padx=(0, 12))
        ttk.Button(row_name, text="Kaydet", command=self.save, style='Solid.TButton').pack(side='right', padx=(12, 0))
        # Kart yÃ¼ksekliÄŸini iÃ§eriÄŸe gÃ¶re ayarla (Kaydet butonu gÃ¶rÃ¼nÃ¼r kalsÄ±n)
        _autosize_card(name_card, name_inner, min_w=560, pad=12, min_h=180)
        name_card.pack_propagate(False)

        # === Theme Card (Tab 2) ===
        theme_holder = tk.Frame(tab_style)
        theme_holder.pack(fill='x', padx=20, pady=(4, 8))
        theme_card, theme_inner = create_card(theme_holder, radius=12, padding=12, border='#888')
        self.theme_card = theme_card
        self.theme_inner = theme_inner
        theme_card.pack(anchor='center', fill='x')
        tint_theme = theme_inner.cget('bg')
        tk.Label(theme_inner, text="Tema", font='TkHeadingFont', bg=tint_theme).pack(anchor='center')
        self.var_dark = tk.BooleanVar(value=False)
        sw_row = tk.Frame(theme_inner, bg=tint_theme)
        sw_row.pack(anchor='center', pady=(6, 0))
        tk.Label(sw_row, text="Koyu Tema", bg=tint_theme).pack(side='left', padx=(0, 8))
        self.theme_switch = IOSSwitch(sw_row, variable=self.var_dark, command=self.on_theme_toggle, bg=tint_theme)
        self.theme_switch.pack(side='left')
        # Tema değişimini anında uygula (yeniden başlatma gerekmez)
        _autosize_card(theme_card, theme_inner, min_w=560, pad=12, min_h=180)
        theme_card.pack_propagate(False)

        # === Scale Card (Tab 2) ===
        scale_holder = tk.Frame(tab_style)
        scale_holder.pack(fill='x', padx=20, pady=(4, 8))
        scale_card, scale_inner = create_card(scale_holder, radius=12, padding=12, border='#888')
        self.scale_card = scale_card
        self.scale_inner = scale_inner
        scale_card.pack(anchor='center', fill='x')
        tint_scale = scale_inner.cget('bg')
        tk.Label(scale_inner, text="Yazı Boyutu", font='TkHeadingFont', bg=tint_scale).pack(anchor='center')
        self.var_scale = tk.StringVar(value='2.0')
        # Place scale radios and base font spinbox side-by-side in a single row
        row = tk.Frame(scale_inner, bg=tint_scale)
        row.pack(pady=(6, 0))
        radios = tk.Frame(row, bg=tint_scale)
        radios.pack(side='left')
        for label, val in (("1x", '1.0'), ("1.5x", '1.5'), ("2x", '2.0')):
            tk.Radiobutton(radios, text=label, variable=self.var_scale, value=val, command=self.on_scale_change, bg=tint_scale).pack(side='left', padx=8)
        row_base = tk.Frame(row, bg=tint_scale)
        row_base.pack(side='left', padx=(16, 0))
        tk.Label(row_base, text="Temel yazı boyutu (pt):", bg=tint_scale).pack(side='left')
        self.var_base_pt = tk.StringVar(value='12')
        try:
            # Prefer ttk.Spinbox for better theming support. Avoid using the
            # built-in 'command' callback because some Tk builds fire it at a
            # surprising moment when switching arrow direction, which looks like
            # a reversed first step. We'll instead commit changes on Enter/blur.
            from tkinter import ttk as _ttk
            self.spin_base = _ttk.Spinbox(row_base, from_=8, to=32, width=4, textvariable=self.var_base_pt, increment=1)
        except Exception:
            # Fallback to classic Spinbox
            self.spin_base = tk.Spinbox(row_base, from_=8, to=32, width=4, textvariable=self.var_base_pt, increment=1)
        self.spin_base.pack(side='left', padx=(6, 0))
        # Apply on Enter or when the control loses focus; also normalize value
        self.spin_base.bind('<Return>', lambda _e: self.on_base_pt_change())
        self.spin_base.bind('<FocusOut>', lambda _e: self.on_base_pt_change())
        # Also apply live when arrows change the value (debounced)
        try:
            self._base_pt_job = None
            def _debounce_apply(*_a):
                try:
                    if self._base_pt_job is not None:
                        self.after_cancel(self._base_pt_job)
                except Exception:
                    pass
                try:
                    self._base_pt_job = self.after(120, self.on_base_pt_change)
                except Exception:
                    self.on_base_pt_change()
            # Only react to user-initiated changes; ignore programmatic loads
            self.var_base_pt.trace_add('write', lambda *a: (None if getattr(self, '_suspend_base_pt_events', False) else _debounce_apply()))
        except Exception:
            pass
        _autosize_card(scale_card, scale_inner, min_w=560, pad=12, min_h=160)
        scale_card.pack_propagate(False)

        # === DB utils (Tab 3) ===
        # DB card centered and compact (just fits 3 buttons)
        db_holder = tk.Frame(tab_db)
        db_holder.pack(fill='x', padx=20, pady=(12,0))
        db_card, db_inner = create_card(db_holder, radius=12, padding=12, border='#888')
        self.db_card = db_card
        self.db_inner = db_inner
        db_card.pack(anchor='center', fill='x')
        tint = db_inner.cget('bg')
        # Title + buttons centered inside card
        tk.Label(db_inner, text="Veri Tabanı", font='TkHeadingFont', bg=tint).pack(pady=(2, 6), anchor='center')
        btn_row = tk.Frame(db_inner, bg=tint)
        btn_row.pack(pady=4, anchor='center')
        ttk.Button(btn_row, text="Yedekle", command=self.backup_db, style='Solid.TButton').pack(side='left', padx=6)
        ttk.Button(btn_row, text="Sıfırla", command=self.reset_db, style='Solid.TButton').pack(side='left', padx=6)
        # Restart button (hidden until reset)
        self.btn_restart = ttk.Button(btn_row, text="Uygulamayı Yeniden Başlat", command=self.restart_app, style='Solid.TButton')

        _autosize_card(db_card, db_inner, min_w=560, pad=12, min_h=180)
        db_card.pack_propagate(False)
        self.status_var = tk.StringVar(value="")
        tk.Label(self, textvariable=self.status_var, fg="#444").pack(fill='x', padx=20, pady=(4, 0))

        self._ensure_table()
        self._load()

    def on_show(self, **kwargs) -> None:
        self.controller.title("Kooperatif - Ayarlar")
        try:
            self._apply_db_tab_permission()
        except Exception:
            pass
        self._load()

    def _apply_db_tab_permission(self) -> None:
        nb = getattr(self, 'nb', None)
        tab = getattr(self, 'tab_db', None)
        if not nb or not tab:
            return
        try:
            perms = getattr(self.controller, 'user_permissions', None)
        except Exception:
            perms = None
        # Admin (perms None) => show; others require 'db' key
        allow = (perms is None) or ('db' in perms)
        try:
            present = str(tab) in set(nb.tabs())
        except Exception:
            present = True
        if not allow and present:
            try:
                nb.forget(tab)
            except Exception:
                pass

    def on_theme_changed(self) -> None:
        """Refresh tinted card backgrounds and local container bg when theme changes.
        Also enforce fixed button/checkbutton/label styles for settings screen."""
        try:
            # Match this frame's bg to app bg
            app_bg = self.controller.cget('bg') if hasattr(self.controller, 'cget') else None
            if app_bg:
                self.configure(bg=app_bg)
        except Exception:
            pass
        try:
            refresh_card_tints(self)
            ensure_card_control_backgrounds(self)
        except Exception:
            pass

        # Ensure header bg matches app bg before recoloring children
        try:
            if hasattr(self, 'header_frame') and self.header_frame:
                self.header_frame.configure(bg=self.cget('bg'))
        except Exception:
            pass

        # Enforce fixed style for all Buttons, Checkbuttons, Labels (classic tk widgets) in this screen
        def _update_widget_style_recursive(widget):
            # Only classic tk widgets, skip ttk widgets
            import tkinter
            is_dark = bool(self.var_dark.get())
            for child in widget.winfo_children():
                try:
                    cls = str(child.winfo_class())
                    # Only classic widgets, not ttk
                    if not cls.startswith('T'):
                        parent_bg = widget.cget("bg") if hasattr(widget, "cget") else "#1e2023"
                        # Button: special style for Kaydet, default for others
                        if isinstance(child, tk.Button):
                            btn_text = ""
                            try:
                                btn_text = child.cget("text")
                            except Exception:
                                pass
                            # Classic buttons: adapt to theme for readability
                            if is_dark:
                                # Dark app theme uses light card surface; use dark text on light bg
                                child.configure(bg="#ffffff", fg="black",
                                                activebackground="#dddddd", activeforeground="black")
                            else:
                                # Light app theme uses dark card surface; use light text on dark bg
                                child.configure(bg="#1e2023", fg="white",
                                                activebackground="#2a2f33", activeforeground="white")
                        # Checkbutton: parent bg, fg depends on theme, selectcolor=parent_bg
                        elif isinstance(child, tk.Checkbutton):
                            if is_dark:
                                child.configure(bg=parent_bg, fg="white", selectcolor=parent_bg)
                            else:
                                child.configure(bg=parent_bg, fg="black", selectcolor=parent_bg)
                        # Radiobutton: parent bg, fg depends on theme, selectcolor=parent_bg
                        elif isinstance(child, tk.Radiobutton):
                            if is_dark:
                                child.configure(bg=parent_bg, fg="white", selectcolor=parent_bg)
                            else:
                                child.configure(bg=parent_bg, fg="black", selectcolor=parent_bg)
                        # Label: parent bg, fg depends on theme
                        elif isinstance(child, tk.Label):
                            if is_dark:
                                child.configure(bg=parent_bg, fg="white")
                            else:
                                child.configure(bg=parent_bg, fg="black")
                        # Frame: parent bg
                        elif isinstance(child, tk.Frame):
                            child.configure(bg=parent_bg)
                    # Recurse for all children
                    _update_widget_style_recursive(child)
                except Exception:
                    pass
        try:
            _update_widget_style_recursive(self)
        except Exception:
            pass

        # Ensure ttk widgets (Buttons, Labels, Entries, etc.) have contrasting text
        try:
            ensure_ttk_contrast_styles(self)
            ensure_ttk_label_contrast(self)
        except Exception:
            pass

        # Refresh back arrow icon/colors to match new theme
        try:
            if hasattr(self, 'back_arrow') and self.back_arrow:
                if hasattr(self.back_arrow, 'refresh_theme'):
                    self.back_arrow.refresh_theme()
        except Exception:
            pass

    def go_back(self) -> None:
        user = getattr(self.controller, "active_user", None)
        if user and "username" in user and "role" in user:
            self.controller.show_role_screen(user["role"], user["username"])
        else:
            self.controller.logout()

    def _ensure_table(self) -> None:
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
        conn.commit()
        conn.close()

    def _load(self) -> None:
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
        # school name
        cur.execute("SELECT value FROM settings WHERE key='report_school_name'")
        row = cur.fetchone()
        conn.close()
        self.entry_school.delete(0, tk.END)
        if row and row[0]:
            self.entry_school.insert(0, row[0])
        # theme switch
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("SELECT value FROM settings WHERE key='ui_theme'")
        r_theme = cur.fetchone()
        conn.close()
        self._set_theme_var_safely(bool(r_theme and (str(r_theme[0]).lower() == 'dark')))
        # scale value
        try:
            conn = sqlite3.connect(DB_NAME)
            cur = conn.cursor()
            cur.execute("SELECT value FROM settings WHERE key='ui_scale'")
            r_scale = cur.fetchone()
            conn.close()
            if hasattr(self, 'var_scale'):
                self.var_scale.set(str(r_scale[0]) if r_scale and r_scale[0] else '2.0')
        except Exception:
            pass
        # base font point size
        try:
            conn = sqlite3.connect(DB_NAME)
            cur = conn.cursor()
            cur.execute("SELECT value FROM settings WHERE key='ui_base_pt'")
            r_base = cur.fetchone()
            conn.close()
            val = str(r_base[0]) if r_base and r_base[0] else '12'
            if hasattr(self, 'var_base_pt'):
                try:
                    self._suspend_base_pt_events = True
                except Exception:
                    pass
                try:
                    self.var_base_pt.set(val)
                finally:
                    try:
                        self._suspend_base_pt_events = False
                    except Exception:
                        pass
        except Exception:
            pass

    def save(self) -> None:
        # Only save the school name
        name = (self.entry_school.get() or "").strip()
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
        cur.execute(
            "INSERT INTO settings(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            ('report_school_name', name),
        )
        conn.commit()
        conn.close()
        self.status_var.set("Okul adı kaydedildi.")

    def on_theme_toggle(self) -> None:
        # Temayı kaydet ve anında uygula (yeniden başlatma yok)
        theme_key = 'dark' if self.var_dark.get() else 'light'
        # Kaydet
        try:
            conn = sqlite3.connect(DB_NAME)
            cur = conn.cursor()
            cur.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
            cur.execute(
                "INSERT INTO settings(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                ('ui_theme', theme_key),
            )
            conn.commit()
            conn.close()
        except Exception:
            pass
        # Anında uygula: önce controller kayıtlarını güncelle, sonra refresh_theme çağır
        try:
            try:
                scale_val = float(self.var_scale.get()) if hasattr(self, 'var_scale') else getattr(self.controller, 'saved_scale', 1.5)
            except Exception:
                scale_val = getattr(self.controller, 'saved_scale', 1.5)
            try:
                base_pt = int(self.var_base_pt.get()) if hasattr(self, 'var_base_pt') else getattr(self.controller, 'saved_base_pt', 12)
            except Exception:
                base_pt = getattr(self.controller, 'saved_base_pt', 12)
            # Kaydı önce güncelle ki refresh_theme doğru temayı uygulasın
            try:
                self.controller.saved_theme = theme_key
                self.controller.saved_scale = float(scale_val)
                self.controller.ui_scale = float(scale_val)
                self.controller.saved_base_pt = int(base_pt)
            except Exception:
                pass
            if hasattr(self.controller, 'refresh_theme'):
                self.controller.refresh_theme()
            self.status_var.set("Tema uygulandı.")
        except Exception:
            pass
    
    def _on_theme_toggle_no_prompt(self) -> None:
        # Save theme and apply live; show info that full effect is on restart
        theme_key = 'dark' if self.var_dark.get() else 'light'
        try:
            conn = sqlite3.connect(DB_NAME)
            cur = conn.cursor()
            cur.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
            cur.execute(
                "INSERT INTO settings(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                ('ui_theme', theme_key),
            )
            conn.commit()
            conn.close()
        except Exception:
            pass
        try:
            try:
                scale_val = float(self.var_scale.get()) if hasattr(self, 'var_scale') else getattr(self.controller, 'saved_scale', 1.5)
            except Exception:
                scale_val = getattr(self.controller, 'saved_scale', 1.5)
            try:
                base_pt = int(self.var_base_pt.get()) if hasattr(self, 'var_base_pt') else getattr(self.controller, 'saved_base_pt', 12)
            except Exception:
                base_pt = getattr(self.controller, 'saved_base_pt', 12)
            if hasattr(self.controller, 'refresh_theme'):
                self.controller.refresh_theme()
            try:
                self.controller.saved_theme = theme_key
                self.controller.saved_scale = float(scale_val)
                self.controller.ui_scale = float(scale_val)
                self.controller.saved_base_pt = int(base_pt)
            except Exception:
                pass
            try:
                messagebox.showinfo("Tema", "Tema değiştirildi. Temanız uygulamayı yeniden başlattığınızda tam olarak uygulanacaktır.")
            except Exception:
                pass
            self.status_var.set("Tema kaydedildi. Yeniden başlatınca tam uygulanır.")
        except Exception:
            pass
    def _init_theme_list(self) -> None:
        pass

    def on_scale_change(self) -> None:
        # Persist and apply scaling when radio changes
        try:
            scale_val = float(self.var_scale.get())
        except Exception:
            scale_val = 2.0
        try:
            if scale_val <= 0:
                scale_val = 1.5
        except Exception:
            scale_val = 1.5
        # Save to DB
        try:
            conn = sqlite3.connect(DB_NAME)
            cur = conn.cursor()
            cur.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
            cur.execute(
                "INSERT INTO settings(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                ('ui_scale', str(scale_val)),
            )
            conn.commit()
            conn.close()
        except Exception:
            pass
        # Set scale in controller before applying theme
        try:
            self.controller.saved_scale = float(scale_val)
            self.controller.ui_scale = float(scale_val)
        except Exception:
            pass
        # Apply only font scaling with current theme (no tk scaling)
        try:
            theme_key = 'dark' if self.var_dark.get() else 'light'
            base_pt = int(self.var_base_pt.get()) if hasattr(self, 'var_base_pt') else getattr(self.controller, 'saved_base_pt', 12)
            if hasattr(self.controller, 'refresh_theme'):
                self.controller.refresh_theme()
            # Keep window size policy independent from font scale
            if hasattr(self.controller, 'set_min_window_for_scale'):
                self.controller.set_min_window_for_scale(1.0)
        except Exception:
            pass
        # Only update status message at the end
        self.status_var.set(f"Ölçek uygulandı: {scale_val}x")

    def on_base_pt_change(self) -> None:
        # Persist and apply base font point size.
        # Also rescale using scale factor so the effective size updates canlı.
        try:
            new_base = int(self.var_base_pt.get())
            if new_base < 8:
                new_base = 8
        except Exception:
            new_base = 12
        # Keep current scale from radio selection or controller
        try:
            new_scale = float(self.var_scale.get()) if hasattr(self, 'var_scale') else float(getattr(self.controller, 'saved_scale', 1.5))
        except Exception:
            new_scale = float(getattr(self.controller, 'saved_scale', 1.5))
        # Persist both settings
        try:
            conn = sqlite3.connect(DB_NAME)
            cur = conn.cursor()
            cur.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
            cur.execute(
                "INSERT INTO settings(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                ('ui_base_pt', str(new_base)),
            )
            # Persisted scale remains unchanged here
            conn.commit()
            conn.close()
        except Exception:
            pass
        # Update controller memory and apply theme
        try:
            self.controller.saved_base_pt = int(new_base)
            self.controller.saved_scale = float(new_scale)
            self.controller.ui_scale = float(new_scale)
        except Exception:
            pass
        try:
            # Update scale radio var to reflect new value textually
            if hasattr(self, 'var_scale'):
                self.var_scale.set(str(new_scale))
        except Exception:
            pass
        try:
            if hasattr(self.controller, 'refresh_theme'):
                self.controller.refresh_theme()
        except Exception:
            pass
        # Avoid re-showing the screen to prevent refresh loops/blinking
        self.status_var.set(f"Temel yazı: {new_base} pt, ölçek: {new_scale}x")

    # --- DB Utils ---
    def backup_db(self) -> None:
        try:
            if not os.path.exists(DB_NAME):
                messagebox.showwarning("Yedekleme", "VeriTabanı bulunamadı.")
                return
            # ensure backups folder
            bdir = os.path.join(os.getcwd(), 'backups')
            os.makedirs(bdir, exist_ok=True)
            base, ext = os.path.splitext(os.path.basename(DB_NAME))
            ts = datetime.now().strftime('%Y%m%d_%H%M%S')
            dst = os.path.join(bdir, f"{base}_{ts}{ext or ''}")
            shutil.copy2(DB_NAME, dst)
            messagebox.showinfo("Yedekleme", f"Yedek alındı:\n{dst}")
        except Exception as e:
            messagebox.showerror("Yedekleme HatasÄ±", str(e))

    def reset_db(self) -> None:
        if not messagebox.askyesno("Sıfırlama", "Veri Tabanını Sıfırlamak istediğinize emin misiniz?\nMevcut dosya yedek kopyası alınacaktır."):
            return
        try:
            # Backup first
            if os.path.exists(DB_NAME):
                bdir = os.path.join(os.getcwd(), 'backups')
                os.makedirs(bdir, exist_ok=True)
                base, ext = os.path.splitext(os.path.basename(DB_NAME))
                ts = datetime.now().strftime('%Y%m%d_%H%M%S')
                dst = os.path.join(bdir, f"{base}_backup_{ts}{ext or ''}")
                shutil.copy2(DB_NAME, dst)
                os.remove(DB_NAME)
            # Re-initialize
            try:
                main = importlib.import_module('main')
                if hasattr(main, 'init_db'):
                    main.init_db()
            except Exception:
                pass
            messagebox.showinfo("Sıfırlama", "Veri Tabanı Sıfırlandı.")
            try:
                # Show restart button after reset (centered row)
                if hasattr(self, 'btn_restart') and str(self.btn_restart) not in (None, ''):
                    self.btn_restart.pack(side='left', padx=6)
            except Exception:
                pass
        except Exception as e:
            messagebox.showerror("Sıfırlama HatasÄ±", str(e))

    def restart_app(self) -> None:
        if not messagebox.askyesno("Yeniden Başlat", "Uygulama yeniden başlatılsın mı?"):
            return
        import subprocess, time
        try:
            exe = sys.executable
            args = [exe] + list(sys.argv) if exe else None
            if exe and args:
                subprocess.Popen(args, close_fds=True)
            else:
                # Fallbacks
                try:
                    subprocess.Popen(["python", *sys.argv], close_fds=True)
                except Exception:
                    try:
                        os.startfile(sys.argv[0])
                    except Exception as _e:
                        messagebox.showerror("Yeniden BaÅŸlatma HatasÄ±", str(_e))
                        return
        except Exception as e:
            messagebox.showerror("Yeniden BaÅŸlatma HatasÄ±", str(e))
            return
        try:
            self.controller.destroy()
        except Exception:
            pass
        os._exit(0)

    def _set_theme_var_safely(self, value: bool):
        # Prevent triggering on_theme_toggle while updating programmatically
        try:
            self._suspend_theme_toggle = True
        except Exception:
            pass
        try:
            self.var_dark.set(value)
            if hasattr(self, 'theme_switch'):
                self.theme_switch.redraw()
        finally:
            try:
                self._suspend_theme_toggle = False
            except Exception:
                pass

# --- Runtime patch: add selective data delete dialog and override reset action ---
def _settings_show_clear_data_dialog(self):
    dlg = tk.Toplevel(self)
    dlg.title("Verileri Temizle")
    dlg.transient(self)
    dlg.grab_set()
    try:
        dlg.resizable(False, False)
    except Exception:
        pass
    # Center the dialog on screen
    # Defer centering until content is laid out to avoid cropping
    def _center_after_layout():
        try:
            dlg.update_idletasks()
            sw = dlg.winfo_screenwidth()
            sh = dlg.winfo_screenheight()
            w = dlg.winfo_width()
            h = dlg.winfo_height()
            x = int((sw - w) / 2)
            y = int((sh - h) / 2)
            # Only move: keep computed size so buttons remain visible
            dlg.geometry(f"+{x}+{y}")
            # Prevent shrinking smaller than content
            try:
                dlg.minsize(w, h)
            except Exception:
                pass
        except Exception:
            pass
    try:
        dlg.after(0, _center_after_layout)
    except Exception:
        pass

    container = tk.Frame(dlg, padx=14, pady=12)
    container.pack(fill='both', expand=True)
    tk.Label(container, text="Hangi verileri silmek istersiniz?", font='TkHeadingFont').pack(anchor='w', pady=(0,8))

    self.var_del_users = tk.BooleanVar(value=False)
    self.var_del_products = tk.BooleanVar(value=False)
    self.var_del_sales = tk.BooleanVar(value=False)
    self.var_del_ledger = tk.BooleanVar(value=False)
    self.var_del_cash = tk.BooleanVar(value=False)
    self.var_del_bank = tk.BooleanVar(value=False)

    tk.Checkbutton(container, text="Kullanicilar (admin haric)", variable=self.var_del_users).pack(anchor='w')
    tk.Checkbutton(container, text="Urunler", variable=self.var_del_products).pack(anchor='w')
    tk.Checkbutton(container, text="Satislar (kalemlerle birlikte)", variable=self.var_del_sales).pack(anchor='w')
    tk.Checkbutton(container, text="Gelir/Gider", variable=self.var_del_ledger).pack(anchor='w')
    tk.Checkbutton(container, text="Kasa Hareketleri", variable=self.var_del_cash).pack(anchor='w')
    tk.Checkbutton(container, text="Banka Hareketleri", variable=self.var_del_bank).pack(anchor='w')

    hint = (
        "Notlar:\n"
        "- Satislar silinirse, satis kalemleri de silinir.\n"
        "- Urunleri silmek mevcut satis raporlarini etkileyebilir."
    )
    tk.Label(container, text=hint, justify='left', fg='#555').pack(anchor='w', pady=(8,6))

    btns = tk.Frame(container)
    btns.pack(fill='x', pady=(12,0))

    def _confirm():
        u = bool(self.var_del_users.get())
        p = bool(self.var_del_products.get())
        s = bool(self.var_del_sales.get())
        l = bool(self.var_del_ledger.get())
        c = bool(self.var_del_cash.get())
        b = bool(self.var_del_bank.get())
        if not any([u, p, s, l, c, b]):
            messagebox.showwarning("Verileri Temizle", "Lutfen en az bir secenek isaretleyin.")
            return
        try:
            _settings_clear_selected_data(self, users=u, products=p, sales=s, ledger=l, cashbook=c, bankbook=b)
        except Exception as e:
            messagebox.showerror("Silme Hatasi", str(e))
            return
        try:
            dlg.destroy()
        except Exception:
            pass

    # Use grid to make buttons equal width
    btns.columnconfigure(0, weight=1)
    btns.columnconfigure(1, weight=1)
    b_cancel = ttk.Button(btns, text="İptal", command=dlg.destroy, style='Solid.TButton')
    b_delete = ttk.Button(btns, text="Sil", command=_confirm, style='Solid.TButton')
    b_cancel.grid(row=0, column=0, sticky='ew', padx=(0,6))
    b_delete.grid(row=0, column=1, sticky='ew', padx=(6,0))


def _settings_clear_selected_data(self, *, users: bool, products: bool, sales: bool, ledger: bool, cashbook: bool, bankbook: bool) -> None:
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    summary = []
    try:
        # Single transaction for consistency; relax FK to avoid blockage
        try:
            cur.execute("PRAGMA foreign_keys=OFF")
        except Exception:
            pass
        cur.execute("BEGIN IMMEDIATE")

        # Users (keep admin)
        if users:
            # user_permissions is optional; ignore if missing
            if _table_exists(cur, 'user_permissions'):
                cur.execute("DELETE FROM user_permissions WHERE LOWER(username) <> 'admin'")
            cur.execute("DELETE FROM users WHERE LOWER(username) <> 'admin'")
            summary.append("Kullanicilar (admin haric)")

        # Sales and items (and returns if present)
        if sales:
            # Delete children first, then parents
            if _table_exists(cur, 'sale_items'):
                cur.execute("DELETE FROM sale_items")
            if _table_exists(cur, 'returns'):
                cur.execute("DELETE FROM returns")
            if _table_exists(cur, 'sales'):
                cur.execute("DELETE FROM sales")
            summary.append("Satislar")

        # Products
        if products:
            if _table_exists(cur, 'products'):
                cur.execute("DELETE FROM products")
            summary.append("Urunler")

        # Ledger / Cashbook / Bankbook
        if ledger:
            if _table_exists(cur, 'ledger'):
                cur.execute("DELETE FROM ledger")
            summary.append("Gelir/Gider")
        if cashbook:
            if _table_exists(cur, 'cashbook'):
                cur.execute("DELETE FROM cashbook")
            summary.append("Kasa Hareketleri")
        if bankbook:
            if _table_exists(cur, 'bankbook'):
                cur.execute("DELETE FROM bankbook")
            summary.append("Banka Hareketleri")

        conn.commit()
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        messagebox.showerror("Silme Hatasi", str(e))
        return
    finally:
        try:
            conn.close()
        except Exception:
            pass
    if summary:
        messagebox.showinfo("Verileri Temizle", "Silinen: " + ", ".join(summary))
        try:
            _refresh_related_views(self)
        except Exception:
            pass

def _table_exists(cur, name: str) -> bool:
    try:
        cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,))
        return cur.fetchone() is not None
    except Exception:
        return False

def _refresh_related_views(self) -> None:
    ctrl = getattr(self, 'controller', None)
    if ctrl is None:
        return
    try:
        frames = dict(getattr(ctrl, 'frames', {}))
    except Exception:
        frames = {}
    for fr in frames.values():
        try:
            cname = type(fr).__name__
        except Exception:
            continue
        # Refresh reports/products/ledger if loaded
        if cname in ("ReportsFrame", "ProductsFrame", "LedgerFrame"):
            try:
                if hasattr(fr, 'refresh') and callable(getattr(fr, 'refresh')):
                    fr.refresh()
            except Exception:
                pass
        # SalesFrame is volatile and rebuilt on show; no action needed here

# Bind as methods and override reset action
try:
    SettingsFrame.show_clear_data_dialog = _settings_show_clear_data_dialog  # type: ignore[attr-defined]
    SettingsFrame._clear_selected_data = _settings_clear_selected_data       # type: ignore[attr-defined]
    SettingsFrame.reset_db = _settings_show_clear_data_dialog                # type: ignore[attr-defined]
except Exception:
    pass
