import sqlite3
import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
from ui import make_back_arrow
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

        header = tk.Frame(self)
        header.pack(fill='x')
        back = make_back_arrow(header, self.go_back)
        back.pack(side='left', padx=(10,6), pady=(10,6))
        tk.Label(header, text="Gelir/Gider Kaydı", font='TkHeadingFont').pack(side='left', pady=(16,6))

        # Tabs to switch between Gelir and Gider
        self.nb = ttk.Notebook(self)
        self.tab_income = tk.Frame(self.nb)
        self.tab_expense = tk.Frame(self.nb)
        self.nb.add(self.tab_income, text="Gelir")
        self.nb.add(self.tab_expense, text="Gider")
        self.nb.pack(fill='x', padx=20, pady=(4, 0))
        self.nb.bind('<<NotebookTabChanged>>', lambda _e: self._on_tab_changed())
        self._current_type = 'gelir'

        # Form
        form = tk.Frame(self)
        form.pack(fill="x", padx=20)

        self.lbl_type = tk.Label(form, text="Tür")
        self.lbl_type.grid(row=0, column=0, sticky="w")
        self.combo_type = ttk.Combobox(form, values=["GELİR", "GİDER"], state="readonly")
        self.combo_type.set("GELİR")
        self.combo_type.grid(row=0, column=1, sticky="w", padx=(6, 20))

        tk.Label(form, text="Tarih").grid(row=0, column=2, sticky="w")
        # Prefer a date picker if tkcalendar is available
        if _DateEntry is not None:
            self.entry_date = _DateEntry(form, date_pattern="yyyy-mm-dd", state="readonly")
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

        tk.Label(form, text="Açıklama").grid(row=1, column=2, sticky="w")
        self.entry_desc = tk.Entry(form)
        self.entry_desc.grid(row=1, column=3, sticky="ew", padx=(6, 20))

        self.lbl_invoice = tk.Label(form, text="Fatura No")
        self.lbl_invoice.grid(row=2, column=0, sticky="w")
        self.entry_invoice = tk.Entry(form)
        self.entry_invoice.grid(row=2, column=1, sticky="ew", padx=(6, 20))

        self.lbl_company = tk.Label(form, text="Firma Adı")
        self.lbl_company.grid(row=2, column=2, sticky="w")
        self.entry_company = tk.Entry(form)
        self.entry_company.grid(row=2, column=3, sticky="ew", padx=(6, 20))
        # Toggle expense-only fields by type
        self.combo_type.bind("<<ComboboxSelected>>", lambda _e: self._toggle_invoice())

        form.columnconfigure(1, weight=1)
        form.columnconfigure(3, weight=2)

        # Buttons
        btns = tk.Frame(self)
        btns.pack(fill="x", padx=20, pady=(6, 8))
        self.btn_add = ttk.Button(btns, text="Ekle", command=self.add_entry)
        self.btn_add.pack(side="left")
        self.btn_update = ttk.Button(btns, text="Guncelle", command=self.update_entry)
        self.btn_update.pack(side="left", padx=8)
        self.btn_delete = ttk.Button(btns, text="Sil", command=self.delete_entry)
        self.btn_delete.pack(side="left")

        # List
        columns = ("id", "date", "type", "amount", "description", "invoice_no", "company")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=12)
        self.tree.heading("id", text="ID")
        self.tree.heading("date", text="Tarih")
        self.tree.heading("type", text="Tür")
        self.tree.heading("amount", text="Tutar")
        self.tree.heading("description", text="Açıklama")
        self.tree.heading("invoice_no", text="Fatura No")
        self.tree.heading("company", text="Firma Adı")
        self.tree.column("id", width=40, anchor="center")
        self.tree.column("date", width=110)
        self.tree.column("type", width=80, anchor="center")
        self.tree.column("amount", width=120, anchor="e")
        self.tree.column("description", width=260)
        self.tree.column("invoice_no", width=120)
        self.tree.column("company", width=160)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        self.tree.pack(fill="both", expand=True, padx=20)

        # Hide type picker (we use tabs instead)
        try:
            self.lbl_type.grid_remove()
            self.combo_type.grid_remove()
        except Exception:
            pass
        # Hide type picker (we use tabs instead)
        try:
            self.lbl_type.grid_remove()
            self.combo_type.grid_remove()
        except Exception:
            pass
        # Set initial state for invoice field (and visibility)
        self._toggle_invoice()

        self.refresh()

    def on_show(self, **kwargs) -> None:
        self.controller.title("Kooperatif - Gelir/Gider Kaydı")
        try:
            # Clear form inputs
            for w in (getattr(self, 'entry_amount', None), getattr(self, 'entry_desc', None), getattr(self, 'entry_invoice', None), getattr(self, 'entry_company', None)):
                if w is not None:
                    w.delete(0, tk.END)
            # Clear selection
            for sel in self.tree.selection():
                self.tree.selection_remove(sel)
        except Exception:
            pass
        self.refresh()
        self.refresh_style()

    def refresh_style(self):
        theme = getattr(self.controller, "saved_theme", "light")
        style = ttk.Style()
        if theme == "dark":
            style.configure("Custom.TButton", background="white", foreground="black")
            style.configure("Treeview", background="#1e2023", fieldbackground="#1e2023", foreground="white")
            style.configure("TNotebook.Tab", background="#1e2023", foreground="white")
        else:
            style.configure("Custom.TButton", background="#1e2023", foreground="white")
            style.configure("Treeview", background="white", fieldbackground="white", foreground="black")
            style.configure("TNotebook.Tab", background="white", foreground="black")
        for btn in (getattr(self, "btn_add", None), getattr(self, "btn_update", None), getattr(self, "btn_delete", None)):
            if btn:
                btn.configure(style="Custom.TButton")

    def _on_tab_changed(self) -> None:
        try:
            idx = self.nb.index(self.nb.select())
        except Exception:
            idx = 0
        self._current_type = 'gelir' if idx == 0 else 'gider'
        # Sync hidden combo to keep existing logic and toggles working
        try:
            self.combo_type.set('GELİR' if self._current_type == 'gelir' else 'GİDER')
        except Exception:
            pass
        self._toggle_invoice()
        self.refresh()

    def _current_db_type(self) -> str:
        return self._current_type

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
        _id, d, typ, amount, desc, invoice_no, company = self.tree.item(sel[0], "values")
        try:
            self.combo_type.set(typ)
        except Exception:
            pass
        try:
            if getattr(self, "_has_datepicker", False):
                # d expected 'YYYY-MM-DD'
                try:
                    y, m, dd = map(int, str(d).split('-'))
                    from datetime import date as _date
                    self.entry_date.set_date(_date(y, m, dd))
                except Exception:
                    pass
            else:
                self.entry_date.delete(0, tk.END)
                self.entry_date.insert(0, d)
        except Exception:
            pass
        try:
            self.entry_amount.delete(0, tk.END)
            self.entry_amount.insert(0, str(amount))
            self.entry_desc.delete(0, tk.END)
            self.entry_desc.insert(0, desc)
            self.entry_invoice.delete(0, tk.END)
            self.entry_invoice.insert(0, invoice_no)
            self.entry_company.delete(0, tk.END)
            self.entry_company.insert(0, company)
        except Exception:
            pass
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
        # Filter list by current tab (type)
        cur.execute("SELECT id, date, type, amount, COALESCE(description,''), COALESCE(invoice_no,''), COALESCE(company,'') FROM ledger WHERE type = ? ORDER BY date DESC, id DESC LIMIT 200", (self._current_db_type(),))
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
        db_type = self._current_db_type()
        date = self.entry_date.get().strip()
        amount = self._parse_amount(self.entry_amount.get().strip())
        desc = self.entry_desc.get().strip() or None
        invoice_no = (self.entry_invoice.get().strip() or None) if db_type == 'gider' else None
        company = (self.entry_company.get().strip() or None) if db_type == 'gider' else None
        if amount != amount or amount <= 0:  # NaN or non-positive
            messagebox.showwarning("Geçersiz tutar", "Pozitif bir tutar girin.")
            return
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        if date:
            cur.execute("INSERT INTO ledger (date, type, amount, description, invoice_no, company) VALUES (?, ?, ?, ?, ?, ?)", (date, db_type, amount, desc, invoice_no, company))
        else:
            cur.execute("INSERT INTO ledger (type, amount, description, invoice_no, company) VALUES (?, ?, ?, ?, ?)", (db_type, amount, desc, invoice_no, company))
        conn.commit()
        conn.close()
        self.entry_amount.delete(0, tk.END)
        self.entry_desc.delete(0, tk.END)
        self.refresh()

    def update_entry(self) -> None:
        lid = self._selected_id()
        if lid is None:
            messagebox.showinfo("Seçim yok", "Güncellenecek kaydı seçin.")
            return
        db_type = self._current_db_type()
        date = self.entry_date.get().strip()
        amount = self._parse_amount(self.entry_amount.get().strip())
        desc = self.entry_desc.get().strip() or None
        invoice_no = (self.entry_invoice.get().strip() or None) if db_type == 'gider' else None
        company = (self.entry_company.get().strip() or None) if db_type == 'gider' else None
        if amount != amount or amount <= 0:
            messagebox.showwarning("Geçersiz tutar", "Pozitif bir tutar girin.")
            return
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("UPDATE ledger SET date = ?, type = ?, amount = ?, description = ?, invoice_no = ?, company = ? WHERE id = ?", (date or None, db_type, amount, desc, invoice_no, company, lid))
        conn.commit()
        conn.close()
        self.refresh()

    def _toggle_invoice(self) -> None:
        # Show invoice/company fields only in Gider tab
        try:
            cur = self._current_db_type() if hasattr(self, '_current_type') else (
                'gelir' if (self.combo_type.get().strip() or '').lower().startswith('gel') else 'gider'
            )
        except Exception:
            cur = 'gelir'
        try:
            if cur == 'gider':
                # Show and enable
                self.lbl_invoice.grid()
                self.entry_invoice.grid()
                self.lbl_company.grid()
                self.entry_company.grid()
                self.entry_invoice.configure(state='normal')
                self.entry_company.configure(state='normal')
            else:
                # Hide and disable
                self.entry_invoice.configure(state='disabled')
                self.entry_company.configure(state='disabled')
                self.lbl_invoice.grid_remove()
                self.entry_invoice.grid_remove()
                self.lbl_company.grid_remove()
                self.entry_company.grid_remove()
        except Exception:
            pass

    def delete_entry(self) -> None:
        lid = self._selected_id()
        if lid is None:
            messagebox.showinfo("Seçim yok", "Silinecek kaydı seçin.")
            return
        if not messagebox.askyesno("Onay", "Seçili kaydı silmek istiyor musunuz?"):
            return
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("DELETE FROM ledger WHERE id = ?", (lid,))
        conn.commit()
        conn.close()
        self.refresh()
