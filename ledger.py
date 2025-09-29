import sqlite3
import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
from datetime import date

try:
    from tkcalendar import DateEntry as _DateEntry  # type: ignore
except Exception:
    _DateEntry = None  # type: ignore

DB_NAME = "coop.db"


class LedgerFrame(tk.Frame):
    def __init__(self, parent: tk.Misc, controller) -> None:
        super().__init__(parent)
        self.controller = controller

        tk.Label(self, text="Gelir/Gider Kaydi", font=("Arial", 16, "bold")).pack(pady=(20, 10))

        # Form
        form = tk.Frame(self)
        form.pack(fill="x", padx=20)

        tk.Label(form, text="Tur").grid(row=0, column=0, sticky="w")
        self.combo_type = ttk.Combobox(form, values=["GELİR", "GİDER"], state="readonly")
        self.combo_type.set("gelir")
        self.combo_type.grid(row=0, column=1, sticky="w", padx=(6, 20))

        tk.Label(form, text="Tarih").grid(row=0, column=2, sticky="w")
        # Prefer a date picker if tkcalendar is available
        if _DateEntry is not None:
            self.entry_date = _DateEntry(form, date_pattern="yyyy-mm-dd")
            self._has_datepicker = True
            try:
                self.entry_date.set_date(date.today())
            except Exception:
                pass
        else:
            self.entry_date = tk.Entry(form)
            self._has_datepicker = False
        self.entry_date.grid(row=0, column=3, sticky="ew", padx=(6, 20))

        tk.Label(form, text="Tutar").grid(row=1, column=0, sticky="w")
        self.entry_amount = tk.Entry(form)
        self.entry_amount.grid(row=1, column=1, sticky="ew", padx=(6, 20))

        tk.Label(form, text="Aciklama").grid(row=1, column=2, sticky="w")
        self.entry_desc = tk.Entry(form)
        self.entry_desc.grid(row=1, column=3, sticky="ew", padx=(6, 20))

        tk.Label(form, text="Fatura No (gider)").grid(row=2, column=0, sticky="w")
        self.entry_invoice = tk.Entry(form)
        self.entry_invoice.grid(row=2, column=1, sticky="ew", padx=(6, 20))

        tk.Label(form, text="Firma Adi (gider)").grid(row=2, column=2, sticky="w")
        self.entry_company = tk.Entry(form)
        self.entry_company.grid(row=2, column=3, sticky="ew", padx=(6, 20))
        # Toggle expense-only fields by type
        self.combo_type.bind("<<ComboboxSelected>>", lambda _e: self._toggle_invoice())

        form.columnconfigure(1, weight=1)
        form.columnconfigure(3, weight=2)

        # Buttons
        btns = tk.Frame(self)
        btns.pack(fill="x", padx=20, pady=(6, 8))
        tk.Button(btns, text="Ekle", command=self.add_entry).pack(side="left")
        tk.Button(btns, text="Guncelle", command=self.update_entry).pack(side="left", padx=8)
        tk.Button(btns, text="Sil", command=self.delete_entry).pack(side="left")
        tk.Button(btns, text="Geri", command=self.go_back).pack(side="right")

        # List
        columns = ("id", "date", "type", "amount", "description", "invoice_no", "company")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=12)
        self.tree.heading("id", text="ID")
        self.tree.heading("date", text="Tarih")
        self.tree.heading("type", text="Tur")
        self.tree.heading("amount", text="Tutar")
        self.tree.heading("description", text="Aciklama")
        self.tree.heading("invoice_no", text="Fatura No")
        self.tree.heading("company", text="Firma Adi")
        self.tree.column("id", width=40, anchor="center")
        self.tree.column("date", width=110)
        self.tree.column("type", width=80, anchor="center")
        self.tree.column("amount", width=120, anchor="e")
        self.tree.column("description", width=260)
        self.tree.column("invoice_no", width=120)
        self.tree.column("company", width=160)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        self.tree.pack(fill="both", expand=True, padx=20)

        # Set initial state for invoice field
        self._toggle_invoice()

        self.refresh()

    def on_show(self, **kwargs) -> None:
        self.controller.title("Kooperatif - Gelir/Gider Kaydi")
        self.refresh()

    def go_back(self) -> None:
        user = getattr(self.controller, "active_user", None)
        if user and "username" in user and "role" in user:
            self.controller.show_role_screen(user["role"], user["username"])
        else:
            self.controller.logout()

    # Helpers
    def _parse_amount(self, s: str) -> float:
        try:
            s = s.replace(",", ".")
            return float(s)
        except Exception:
            return float("nan")

    def _selected_id(self):
        sel = self.tree.selection()
        if not sel:
            return None
        vals = self.tree.item(sel[0], "values")
        return int(vals[0])

    def on_select(self, _e=None) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        _id, date, typ, amount, desc, invoice_no, company = self.tree.item(sel[0], "values")
        self.combo_type.set(typ)
        self.entry_date.delete(0, tk.END)
        self.entry_date.insert(0, date)
        self.entry_amount.delete(0, tk.END)
        self.entry_amount.insert(0, amount)
        self.entry_desc.delete(0, tk.END)
        self.entry_desc.insert(0, desc)
        self.entry_invoice.delete(0, tk.END)
        self.entry_invoice.insert(0, invoice_no)
        self.entry_company.delete(0, tk.END)
        self.entry_company.insert(0, company)
        self._toggle_invoice()

    # CRUD
    def refresh(self) -> None:
        for row in self.tree.get_children():
            self.tree.delete(row)
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS ledger (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL DEFAULT (date('now')),
                type TEXT NOT NULL CHECK(type IN ('gelir','gider')),
                amount REAL NOT NULL,
                description TEXT,
                invoice_no TEXT,
                company TEXT
            )
            """
        )
        # Migration: add invoice_no if missing
        cur.execute("PRAGMA table_info(ledger)")
        _cols = [r[1] for r in cur.fetchall()]
        if 'invoice_no' not in _cols:
            cur.execute("ALTER TABLE ledger ADD COLUMN invoice_no TEXT")
        if 'company' not in _cols:
            cur.execute("ALTER TABLE ledger ADD COLUMN company TEXT")
        cur.execute("SELECT id, date, type, amount, COALESCE(description,''), COALESCE(invoice_no,''), COALESCE(company,'') FROM ledger ORDER BY date DESC, id DESC LIMIT 200")
        for _id, d, t, a, desc, inv, comp in cur.fetchall():
            self.tree.insert("", "end", values=(_id, d, t, f"{float(a):.2f}", desc, inv, comp))
        conn.close()

        # Default date to today
        try:
            if getattr(self, "_has_datepicker", False):
                self.entry_date.set_date(date.today())
            else:
                if not self.entry_date.get().strip():
                    conn = sqlite3.connect(DB_NAME)
                    cur = conn.cursor()
                    try:
                        cur.execute("SELECT date('now')")
                        today = cur.fetchone()[0]
                    finally:
                        conn.close()
                    self.entry_date.insert(0, today)
        except Exception:
            pass

    def add_entry(self) -> None:
        typ = self.combo_type.get().strip() or "gelir"
        date = self.entry_date.get().strip()
        amount = self._parse_amount(self.entry_amount.get().strip())
        desc = self.entry_desc.get().strip() or None
        invoice_no = (self.entry_invoice.get().strip() or None) if typ == 'gider' else None
        company = (self.entry_company.get().strip() or None) if typ == 'gider' else None
        if typ not in ("gelir", "gider"):
            messagebox.showwarning("Gecersiz tur", "Tur 'gelir' veya 'gider' olmali.")
            return
        if amount != amount or amount <= 0:  # NaN or non-positive
            messagebox.showwarning("Gecersiz tutar", "Pozitif bir tutar girin.")
            return
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        if date:
            cur.execute("INSERT INTO ledger (date, type, amount, description, invoice_no, company) VALUES (?, ?, ?, ?, ?, ?)", (date, typ, amount, desc, invoice_no, company))
        else:
            cur.execute("INSERT INTO ledger (type, amount, description, invoice_no, company) VALUES (?, ?, ?, ?, ?)", (typ, amount, desc, invoice_no, company))
        conn.commit()
        conn.close()
        self.entry_amount.delete(0, tk.END)
        self.entry_desc.delete(0, tk.END)
        self.refresh()

    def update_entry(self) -> None:
        lid = self._selected_id()
        if lid is None:
            messagebox.showinfo("Secim yok", "Guncellenecek kaydi secin.")
            return
        typ = self.combo_type.get().strip() or "gelir"
        date = self.entry_date.get().strip()
        amount = self._parse_amount(self.entry_amount.get().strip())
        desc = self.entry_desc.get().strip() or None
        invoice_no = (self.entry_invoice.get().strip() or None) if typ == 'gider' else None
        company = (self.entry_company.get().strip() or None) if typ == 'gider' else None
        if typ not in ("gelir", "gider"):
            messagebox.showwarning("Gecersiz tur", "Tur 'gelir' veya 'gider' olmali.")
            return
        if amount != amount or amount <= 0:
            messagebox.showwarning("Gecersiz tutar", "Pozitif bir tutar girin.")
            return
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("UPDATE ledger SET date = ?, type = ?, amount = ?, description = ?, invoice_no = ?, company = ? WHERE id = ?", (date or None, typ, amount, desc, invoice_no, company, lid))
        conn.commit()
        conn.close()
        self.refresh()

    def _toggle_invoice(self) -> None:
        typ = self.combo_type.get().strip()
        try:
            if typ == 'gider':
                self.entry_invoice.configure(state='normal')
                self.entry_company.configure(state='normal')
            else:
                self.entry_invoice.configure(state='disabled')
                self.entry_company.configure(state='disabled')
        except Exception:
            pass

    def delete_entry(self) -> None:
        lid = self._selected_id()
        if lid is None:
            messagebox.showinfo("Secim yok", "Silinecek kaydi secin.")
            return
        if not messagebox.askyesno("Onay", "Secili kaydi silmek istiyor musunuz?"):
            return
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("DELETE FROM ledger WHERE id = ?", (lid,))
        conn.commit()
        conn.close()
        self.refresh()

