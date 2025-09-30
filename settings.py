import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox
from ui import make_back_arrow, apply_theme, rounded_outline, smart_tinted_bg
from tkinter import ttk
import os
import shutil
from datetime import datetime
import importlib
import sys

DB_NAME = "coop.db"


class SettingsFrame(tk.Frame):
    def __init__(self, parent: tk.Misc, controller) -> None:
        super().__init__(parent)
        self.controller = controller

        header = tk.Frame(self)
        header.pack(fill='x')
        back = make_back_arrow(header, self.go_back)
        back.pack(side='left', padx=(10,6), pady=(10,6))
        tk.Label(header, text="Ayarlar", font=("Arial", 16, "bold")).pack(side='left', pady=(16,6))

        # === School Name Card ===
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
        name_holder = tk.Frame(self)
        name_holder.pack(fill='x', padx=20, pady=(10, 4))
        name_card, name_inner = rounded_outline(name_holder, radius=12, padding=12, border='#888')
        self.name_card = name_card
        self.name_inner = name_inner
        name_card.pack(anchor='center', fill='x')
        tint_name = smart_tinted_bg(self)
        name_inner.configure(bg=tint_name)
        tk.Label(name_inner, text="Okul adı (Rapor Başlığı)", font=("Arial", 12, "bold"), bg=tint_name).pack(anchor='center')
        row_name = tk.Frame(name_inner, bg=tint_name)
        row_name.pack(pady=(6, 0), anchor='center')
        self.entry_school = ttk.Entry(row_name, width=40)
        # Metin kutusu ile buton arasÄ±nÄ± aÃ§mak iÃ§in boÅŸluklarÄ± artÄ±r
        self.entry_school.pack(side='left', padx=(0, 12))
        ttk.Button(row_name, text="Kaydet", command=self.save, style='Solid.TButton').pack(side='right', padx=(12, 0))
        # Kart yÃ¼ksekliÄŸini iÃ§eriÄŸe gÃ¶re ayarla (Kaydet butonu gÃ¶rÃ¼nÃ¼r kalsÄ±n)
        _autosize_card(name_card, name_inner, min_w=560, pad=12, min_h=180)
        name_card.pack_propagate(False)

        # === Theme Card ===
        theme_holder = tk.Frame(self)
        theme_holder.pack(fill='x', padx=20, pady=(4, 8))
        theme_card, theme_inner = rounded_outline(theme_holder, radius=12, padding=12, border='#888')
        self.theme_card = theme_card
        self.theme_inner = theme_inner
        theme_card.pack(anchor='center', fill='x')
        tint_theme = smart_tinted_bg(self)
        theme_inner.configure(bg=tint_theme)
        tk.Label(theme_inner, text="Tema", font=("Arial", 12, "bold"), bg=tint_theme).pack(anchor='center')
        self.var_dark = tk.BooleanVar(value=False)
        self.theme_checkbox = tk.Checkbutton(theme_inner, text="Koyu Tema", variable=self.var_dark, command=self.on_theme_toggle, bg=tint_theme)
        self.theme_checkbox.pack(anchor='center', pady=(6, 0))
        _autosize_card(theme_card, theme_inner, min_w=560, pad=12, min_h=180)
        theme_card.pack_propagate(False)

        # === Scale Card ===
        scale_holder = tk.Frame(self)
        scale_holder.pack(fill='x', padx=20, pady=(4, 8))
        scale_card, scale_inner = rounded_outline(scale_holder, radius=12, padding=12, border='#888')
        self.scale_card = scale_card
        self.scale_inner = scale_inner
        scale_card.pack(anchor='center', fill='x')
        tint_scale = smart_tinted_bg(self)
        scale_inner.configure(bg=tint_scale)
        tk.Label(scale_inner, text="Yazı Boyutu", font=("Arial", 12, "bold"), bg=tint_scale).pack(anchor='center')
        self.var_scale = tk.StringVar(value='2.0')
        radios = tk.Frame(scale_inner, bg=tint_scale)
        radios.pack(pady=(6, 0))
        for label, val in (("1x", '1.0'), ("1.5x", '1.5'), ("2x", '2.0')):
            tk.Radiobutton(radios, text=label, variable=self.var_scale, value=val, command=self.on_scale_change, bg=tint_scale).pack(side='left', padx=8)
        _autosize_card(scale_card, scale_inner, min_w=560, pad=12, min_h=160)
        scale_card.pack_propagate(False)

        # DB utils
        # DB card centered and compact (just fits 3 buttons)
        db_holder = tk.Frame(self)
        db_holder.pack(fill='x', padx=20, pady=(12,0))
        db_card, db_inner = rounded_outline(db_holder, radius=12, padding=12, border='#888')
        self.db_card = db_card
        self.db_inner = db_inner
        db_card.pack(anchor='center', fill='x')
        tint = smart_tinted_bg(self)
        db_inner.configure(bg=tint)
        # Title + buttons centered inside card
        tk.Label(db_inner, text="Veri Tabanı", font=("Arial", 12, "bold"), bg=tint).pack(pady=(2, 6), anchor='center')
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
        self._load()

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
            # Recompute tints for each card
            for inner in [getattr(self, 'name_inner', None), getattr(self, 'theme_inner', None), getattr(self, 'scale_inner', None), getattr(self, 'db_inner', None)]:
                if inner is None:
                    continue
                tint = smart_tinted_bg(self)
                try:
                    inner.configure(bg=tint)
                except Exception:
                    pass
                # Update direct children that are classic Tk widgets to use the same bg
                try:
                    for ch in inner.winfo_children():
                        try:
                            # Only touch classic widgets; ttk widgets ignore bg
                            cls = str(ch.winfo_class())
                            if not cls.startswith('T'):
                                ch.configure(bg=tint)
                        except Exception:
                            pass
                except Exception:
                    pass
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
                            # All buttons (including Kaydet) get the same dark style if is_dark,
                            # or same as dark style for light theme (per instructions)
                            if is_dark:
                                child.configure(bg="#1e2023", fg="white",
                                                activebackground="#2a2f33", activeforeground="white")
                            else:
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
        # Persist and apply theme when the checkbox changes
        theme_key = 'dark' if self.var_dark.get() else 'light'
        # Save
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
        # Ask user to restart for full theme application
        try:
            if messagebox.askyesno("Tema", "Tema değiştirildi. Uygulamayı yeniden başlatmak ister misiniz?"):
                # Persist desired scale in memory to survive restart
                try:
                    scale_val = float(self.var_scale.get()) if hasattr(self, 'var_scale') else getattr(self.controller, 'saved_scale', 1.5)
                except Exception:
                    scale_val = getattr(self.controller, 'saved_scale', 1.5)
                try:
                    self.controller.saved_theme = theme_key
                    self.controller.saved_scale = float(scale_val)
                except Exception:
                    pass
                self.restart_app()
            else:
                # Best-effort live apply without restart
                try:
                    scale_val = float(self.var_scale.get()) if hasattr(self, 'var_scale') else getattr(self.controller, 'saved_scale', 1.5)
                except Exception:
                    scale_val = getattr(self.controller, 'saved_scale', 1.5)
                apply_theme(self.controller, scale=scale_val, theme_name=theme_key)
                if hasattr(self.controller, 'refresh_theme'):
                    self.controller.refresh_theme()
                try:
                    self.controller.saved_theme = theme_key
                    self.controller.saved_scale = float(scale_val)
                    self.controller.ui_scale = float(scale_val)
                except Exception:
                    pass
                self.status_var.set("Tema uygulandı (yeniden başlatmadan).")
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
            apply_theme(self.controller, scale=scale_val, theme_name=theme_key)
            if hasattr(self.controller, 'refresh_theme'):
                self.controller.refresh_theme()
            # Keep window size policy independent from font scale
            if hasattr(self.controller, 'set_min_window_for_scale'):
                self.controller.set_min_window_for_scale(1.0)
        except Exception:
            pass
        # Only update status message at the end
        self.status_var.set(f"Ölçek uygulandı: {scale_val}x")

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
        try:
            self.theme_checkbox.configure(command=None)
            self.var_dark.set(value)
        finally:
            self.theme_checkbox.configure(command=self.on_theme_toggle)
