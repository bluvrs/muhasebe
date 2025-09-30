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
        def _autosize_card(card: tk.Frame, inner: tk.Frame, min_w: int = 560, pad: int = 12) -> None:
            try:
                inner.update_idletasks()
                req_h = inner.winfo_reqheight()
                req_w = max(min_w, inner.winfo_reqwidth() + 2*pad)
                card.configure(width=req_w, height=req_h + 2*pad)
            except Exception:
                # Ölçüm başarısız olursa güvenli bir yükseklik kullan
                card.configure(width=min_w, height=200)
        name_holder = tk.Frame(self)
        name_holder.pack(fill='x', padx=20, pady=(10, 4))
        name_card, name_inner = rounded_outline(name_holder, radius=12, padding=12, border='#888')
        name_card.pack(anchor='center', fill='x')
        tint_name = smart_tinted_bg(self)
        name_inner.configure(bg=tint_name)
        tk.Label(name_inner, text="Okul Adı (Rapor Başlığı)", font=("Arial", 12, "bold"), bg=tint_name).pack(anchor='center')
        row_name = tk.Frame(name_inner, bg=tint_name)
        row_name.pack(pady=(6, 0), anchor='center')
        self.entry_school = tk.Entry(row_name, width=40)
        self.entry_school.pack(side='left', padx=(0, 8))
        tk.Button(row_name, text="Kaydet", command=self.save).pack(side='left')
        # Kart yüksekliğini içeriğe göre ayarla (Kaydet butonu görünür kalsın)
        _autosize_card(name_card, name_inner, min_w=560, pad=12)
        name_card.pack_propagate(False)

        # === Theme Card ===
        theme_holder = tk.Frame(self)
        theme_holder.pack(fill='x', padx=20, pady=(4, 8))
        theme_card, theme_inner = rounded_outline(theme_holder, radius=12, padding=12, border='#888')
        theme_card.pack(anchor='center', fill='x')
        tint_theme = smart_tinted_bg(self)
        theme_inner.configure(bg=tint_theme)
        tk.Label(theme_inner, text="Tema", font=("Arial", 12, "bold"), bg=tint_theme).pack(anchor='center')
        self.var_dark = tk.BooleanVar(value=False)
        tk.Checkbutton(theme_inner, text="Koyu Tema", variable=self.var_dark, command=self.on_theme_toggle, bg=tint_theme).pack(anchor='center', pady=(6, 0))
        _autosize_card(theme_card, theme_inner, min_w=560, pad=12)
        theme_card.pack_propagate(False)

        # DB utils
        # DB card centered and compact (just fits 3 buttons)
        db_holder = tk.Frame(self)
        db_holder.pack(fill='x', padx=20, pady=(12,0))
        db_card, db_inner = rounded_outline(db_holder, radius=12, padding=12, border='#888')
        db_card.pack(anchor='center', fill='x')
        tint = smart_tinted_bg(self)
        db_inner.configure(bg=tint)
        # Title + buttons centered inside card
        tk.Label(db_inner, text="Veri Tabanı", font=("Arial", 12, "bold"), bg=tint).pack(pady=(2, 6), anchor='center')
        btn_row = tk.Frame(db_inner, bg=tint)
        btn_row.pack(pady=4, anchor='center')
        ttk.Button(btn_row, text="Yedekle", command=self.backup_db).pack(side='left', padx=6)
        ttk.Button(btn_row, text="Sıfırla", command=self.reset_db).pack(side='left', padx=6)
        # Restart button (hidden until reset)
        self.btn_restart = ttk.Button(btn_row, text="Uygulamayı Yeniden Başlat", command=self.restart_app)

        _autosize_card(db_card, db_inner, min_w=560, pad=12)
        db_card.pack_propagate(False)
        self.status_var = tk.StringVar(value="")
        tk.Label(self, textvariable=self.status_var, fg="#444").pack(fill='x', padx=20, pady=(4, 0))

        self._ensure_table()
        self._load()

    def on_show(self, **kwargs) -> None:
        self.controller.title("Kooperatif - Ayarlar")
        self._load()

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
        self.var_dark.set(bool(r_theme and (str(r_theme[0]).lower() == 'dark')))

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
        # Apply immediately
        try:
            apply_theme(self.controller, scale=2.0, theme_name=theme_key)
            if hasattr(self.controller, 'refresh_theme'):
                self.controller.refresh_theme()
        except Exception:
            pass
        # Offer restart (uses existing method that asks for confirmation)
        try:
            self.restart_app()
        except Exception:
            pass

    def _init_theme_list(self) -> None:
        pass

    # --- DB Utils ---
    def backup_db(self) -> None:
        try:
            if not os.path.exists(DB_NAME):
                messagebox.showwarning("Yedekleme", "Veritabanı bulunamadı.")
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
            messagebox.showerror("Yedekleme Hatası", str(e))

    def reset_db(self) -> None:
        if not messagebox.askyesno("Sıfırlama", "Veritabanını sıfırlamak istediğinize emin misiniz?\nMevcut dosya yedek kopyası alınacaktır."):
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
            messagebox.showinfo("Sıfırlama", "Veritabanı sıfırlandı.")
            try:
                # Show restart button after reset (centered row)
                if hasattr(self, 'btn_restart') and str(self.btn_restart) not in (None, ''):
                    self.btn_restart.pack(side='left', padx=6)
            except Exception:
                pass
        except Exception as e:
            messagebox.showerror("Sıfırlama Hatası", str(e))

    def restart_app(self) -> None:
        if not messagebox.askyesno("Yeniden Başlat", "Uygulama yeniden başlatılsın mı?"):
            return
        try:
            python = sys.executable
            os.execl(python, python, *sys.argv)
        except Exception as e:
            messagebox.showerror("Yeniden Başlatma Hatası", str(e))
