import sqlite3
import tkinter as tk
from tkinter import ttk
from ui import make_back_arrow

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

        body = tk.Frame(self)
        body.pack(fill='x', padx=20, pady=10)

        tk.Label(body, text="Okul Adı (Rapor Başlığı)").grid(row=0, column=0, sticky='w')
        self.entry_school = tk.Entry(body, width=40)
        self.entry_school.grid(row=0, column=1, sticky='w', padx=(8, 20))

        tk.Button(body, text="Kaydet", command=self.save).grid(row=0, column=2, sticky='w')

        body.columnconfigure(1, weight=1)

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
        cur.execute("SELECT value FROM settings WHERE key='report_school_name'")
        row = cur.fetchone()
        conn.close()
        self.entry_school.delete(0, tk.END)
        if row and row[0]:
            self.entry_school.insert(0, row[0])

    def save(self) -> None:
        name = (self.entry_school.get() or "").strip()
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
        cur.execute(
            "INSERT INTO settings(key, value) VALUES('report_school_name', ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (name,),
        )
        conn.commit()
        conn.close()
        self.status_var.set("Kaydedildi.")

