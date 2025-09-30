import sqlite3
import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
from datetime import date
try:
    from tkcalendar import DateEntry as _DateEntry  # type: ignore
except Exception:
    _DateEntry = None  # type: ignore
from ui import make_back_arrow

DB_NAME = "coop.db"


class InvestorsFrame(tk.Frame):
    def __init__(self, parent: tk.Misc, controller) -> None:
        super().__init__(parent)
        self.controller = controller

        header = tk.Frame(self)
        header.pack(fill='x')
        back = make_back_arrow(header, self.go_back)
        back.pack(side='left', padx=(10,6), pady=(10,6))
        tk.Label(header, text="Yatırımcılar", font=("Arial", 16, "bold")).pack(side='left', pady=(16,6))

        # Pool percent setting
        pool = tk.Frame(self)
        pool.pack(fill="x", padx=20, pady=(0, 8))
        tk.Label(pool, text="Yatırım Havuzu % (Ortaklığa açık pay)").pack(side="left")
        self.entry_pool = tk.Entry(pool, width=6)
        self.entry_pool.pack(side="left", padx=(6, 6))
        self.btn_save_pool = ttk.Button(pool, text="Kaydet", command=self.save_pool_percent)
        self.btn_save_pool.pack(side="left")
        # Live computed label
        self.lbl_pool_info = tk.Label(pool, text="")
        self.lbl_pool_info.pack(side="left", padx=(12, 0))


        # Tabs: Investors and Transactions
        nb = ttk.Notebook(self)
        nb.pack(fill='both', expand=True)
        tab_list = tk.Frame(nb)
        tab_tx = tk.Frame(nb)
        nb.add(tab_list, text='Yatırımcılar')
        nb.add(tab_tx, text='Yatırımcı İşlemleri')

        # List
        columns = ("id", "name", "phone", "initial_capital", "current_capital", "pool_share_%", "shop_share_%", "initial_date")
        # Keep the top list compact so the transactions list below stays readable
        self.tree = ttk.Treeview(tab_list, columns=columns, show="headings", height=7)
        self.tree.heading("id", text="ID")
        self.tree.heading("name", text="İsim")
        self.tree.heading("phone", text="Telefon")
        self.tree.heading("initial_capital", text="Başlangıç Sermayesi")
        self.tree.heading("current_capital", text="Güncel Sermaye")
        self.tree.heading("pool_share_%", text="Havuz Payı %")
        self.tree.heading("shop_share_%", text="Dükkan Payı %")
        self.tree.heading("initial_date", text="Tarih")
        self.tree.column("id", width=50, anchor="center")
        self.tree.column("name", width=220)
        self.tree.column("phone", width=150)
        self.tree.column("initial_capital", width=140, anchor="e")
        self.tree.column("current_capital", width=140, anchor="e")
        self.tree.column("pool_share_%", width=120, anchor="e")
        self.tree.column("shop_share_%", width=120, anchor="e")
        self.tree.column("initial_date", width=100)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        self.tree.pack(fill="both", expand=False, padx=20)

        # Form
        form = tk.Frame(tab_list)
        form.pack(fill="x", padx=20, pady=10)

        tk.Label(form, text="İsim").grid(row=0, column=0, sticky="w")
        self.entry_name = tk.Entry(form)
        self.entry_name.grid(row=0, column=1, sticky="ew", padx=(6, 20))

        tk.Label(form, text="Telefon").grid(row=1, column=0, sticky="w")
        self.entry_phone = tk.Entry(form)
        self.entry_phone.grid(row=1, column=1, sticky="ew", padx=(6, 20))

        tk.Label(form, text="Başlangıç Sermayesi").grid(row=0, column=2, sticky="w")
        self.entry_capital = tk.Entry(form)
        self.entry_capital.grid(row=0, column=3, sticky="ew", padx=(6, 20))

        tk.Label(form, text="Tarih").grid(row=1, column=2, sticky="w")
        if _DateEntry is not None:
            self.entry_date = _DateEntry(form, date_pattern="yyyy-mm-dd", state="readonly")
            try:
                self.entry_date.set_date(date.today())
            except Exception:
                pass
        else:
            self.entry_date = tk.Entry(form)
        self.entry_date.grid(row=1, column=3, sticky="ew", padx=(6, 20))

        tk.Label(form, text="Notlar").grid(row=0, column=4, sticky="w")
        self.entry_notes = tk.Entry(form, width=30)
        self.entry_notes.grid(row=0, column=5, sticky="ew")

        form.columnconfigure(1, weight=2)
        form.columnconfigure(3, weight=1)
        form.columnconfigure(5, weight=2)

        # Buttons
        btns = tk.Frame(tab_list)
        btns.pack(fill="x", padx=20, pady=(0, 10))
        self.btn_add = ttk.Button(btns, text="Ekle", command=self.add_investor)
        self.btn_add.pack(side="left")
        self.btn_update = ttk.Button(btns, text="Guncelle", command=self.update_investor)
        self.btn_update.pack(side="left", padx=8)
        self.btn_delete = ttk.Button(btns, text="Sil", command=self.delete_investor)
        self.btn_delete.pack(side="left")

        # Transactions section
        sep = ttk.Separator(tab_tx, orient="horizontal")
        sep.pack(fill="x", padx=20, pady=(6, 6))

        tk.Label(tab_tx, text="Yatırımcı İşlemleri", font=("Arial", 12, "bold")).pack(anchor="w", padx=20)
        tx_form = tk.Frame(tab_tx)
        tx_form.pack(fill="x", padx=20)
        tk.Label(tx_form, text="Tarih").grid(row=0, column=0, sticky="w")
        if _DateEntry is not None:
            self.tx_date = _DateEntry(tx_form, date_pattern="yyyy-mm-dd", width=12, state="readonly")
            try:
                self.tx_date.set_date(date.today())
            except Exception:
                pass
        else:
            self.tx_date = tk.Entry(tx_form, width=12)
        self.tx_date.grid(row=0, column=1, sticky="w", padx=(6, 20))
        tk.Label(tx_form, text="Tutar").grid(row=0, column=2, sticky="w")
        self.tx_amount = tk.Entry(tx_form, width=12)
        self.tx_amount.grid(row=0, column=3, sticky="w", padx=(6, 20))
        tk.Label(tx_form, text="Not").grid(row=0, column=4, sticky="w")
        self.tx_notes = tk.Entry(tx_form)
        self.tx_notes.grid(row=0, column=5, sticky="ew", padx=(6, 20))
        tx_form.columnconfigure(5, weight=1)

        tx_btns = tk.Frame(tab_tx)
        tx_btns.pack(fill="x", padx=20, pady=(6, 6))
        self.btn_add_tx_contribution = ttk.Button(tx_btns, text="Katki Ekle", command=lambda: self.add_tx('contribution'))
        self.btn_add_tx_contribution.pack(side="left")
        self.btn_add_tx_withdrawal = ttk.Button(tx_btns, text="Cekim Ekle", command=lambda: self.add_tx('withdrawal'))
        self.btn_add_tx_withdrawal.pack(side="left", padx=(8, 0))
        self.btn_delete_tx = ttk.Button(tx_btns, text="Islemi Sil", command=self.delete_tx)
        self.btn_delete_tx.pack(side="left", padx=(8, 0))

        tx_cols = ("id", "date", "type", "amount", "notes")
        # Give more room to transactions
        self.tx_tree = ttk.Treeview(tab_tx, columns=tx_cols, show="headings", height=12)
        for c, lbl, w, anc in (
            ("id", "ID", 50, "center"),
            ("date", "Tarih", 100, "w"),
            ("type", "Tür", 120, "center"),
            ("amount", "Tutar", 120, "e"),
            ("notes", "Not", 400, "w"),
        ):
            self.tx_tree.heading(c, text=lbl)
            self.tx_tree.column(c, width=w, anchor=anc)
        self.tx_tree.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        self.refresh()

    def on_show(self, **kwargs) -> None:
        self.controller.title("Kooperatif - Yatırımcılar")
        try:
            for w in (getattr(self, 'entry_name', None), getattr(self, 'entry_phone', None), getattr(self, 'entry_capital', None), getattr(self, 'entry_notes', None)):
                if w is not None:
                    w.delete(0, tk.END)
            for w in (getattr(self, 'tx_date', None), getattr(self, 'tx_amount', None), getattr(self, 'tx_notes', None)):
                if hasattr(w, 'delete'):
                    w.delete(0, tk.END)
            # clear selections and tx list
            for sel in self.tree.selection():
                self.tree.selection_remove(sel)
            for iid in self.tx_tree.get_children():
                self.tx_tree.delete(iid)
        except Exception:
            pass
        self.refresh()
        self.refresh_style()

    def refresh_style(self):
        theme = getattr(self.controller, "saved_theme", "light")
        style = ttk.Style()
        # Configure custom button style for ttk.Button
        if theme == "dark":
            style.configure("Custom.TButton", background="white", foreground="black")
        else:
            style.configure("Custom.TButton", background="#1e2023", foreground="white")
        # Apply the custom style to all relevant buttons
        for btn in (
            getattr(self, "btn_save_pool", None),
            getattr(self, "btn_add", None),
            getattr(self, "btn_update", None),
            getattr(self, "btn_delete", None),
            getattr(self, "btn_add_tx_contribution", None),
            getattr(self, "btn_add_tx_withdrawal", None),
            getattr(self, "btn_delete_tx", None),
        ):
            if btn:
                btn.configure(style="Custom.TButton")

        # ttk styles for Treeview and Notebook (unchanged)
        if theme == "dark":
            style.configure("Treeview", background="#1e2023", fieldbackground="#1e2023", foreground="white")
            style.configure("TNotebook.Tab", background="#1e2023", foreground="white")
        else:
            style.configure("Treeview", background="white", fieldbackground="white", foreground="black")
            style.configure("TNotebook.Tab", background="white", foreground="black")

    # Helpers
    def _selected_id(self):
        sel = self.tree.selection()
        if not sel:
            return None
        vals = self.tree.item(sel[0], "values")
        return int(vals[0])

    def _parse_amount(self, s: str) -> float:
        try:
            s = s.replace(",", ".")
            return float(s)
        except Exception:
            return float("nan")

    def on_select(self, _e=None) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        values = self.tree.item(sel[0], "values")
        _id, name, phone, cap_init, _cap_curr, _pool_pct, _shop_pct, d = values
        self.entry_name.delete(0, tk.END)
        self.entry_name.insert(0, name)
        self.entry_phone.delete(0, tk.END)
        self.entry_phone.insert(0, phone)
        self.entry_capital.delete(0, tk.END)
        self.entry_capital.insert(0, cap_init)
        try:
            if isinstance(self.entry_date, tk.Entry):
                self.entry_date.delete(0, tk.END)
                self.entry_date.insert(0, d)
            else:
                # DateEntry: parse ISO date safely
                try:
                    y, m, dd = map(int, str(d).split('-'))
                    from datetime import date as _date
                    self.entry_date.set_date(_date(y, m, dd))
                except Exception:
                    pass
        except Exception:
            pass
        # Load notes for selected id
        row = None
        try:
            conn = sqlite3.connect(DB_NAME)
            cur = conn.cursor()
            cur.execute("SELECT COALESCE(notes,'') FROM investors WHERE id = ?", (int(_id),))
            row = cur.fetchone()
        finally:
            conn.close()
        if row:
            self.entry_notes.delete(0, tk.END)
            self.entry_notes.insert(0, row[0])
        self.refresh_transactions(int(_id))

    # Navigation
    def go_back(self) -> None:
        user = getattr(self.controller, "active_user", None)
        if user and "username" in user and "role" in user:
            self.controller.show_role_screen(user["role"], user["username"])
        else:
            self.controller.logout()

    # CRUD
    def refresh(self) -> None:
        for row in self.tree.get_children():
            self.tree.delete(row)
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS investors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT,
                initial_capital REAL NOT NULL DEFAULT 0,
                initial_date TEXT NOT NULL DEFAULT (date('now')),
                notes TEXT
            )
            """
        )
        # Ensure transactions and settings tables
        cur.execute(
            "CREATE TABLE IF NOT EXISTS investor_transactions (id INTEGER PRIMARY KEY AUTOINCREMENT, investor_id INTEGER NOT NULL, date TEXT NOT NULL DEFAULT (date('now')), type TEXT NOT NULL CHECK(type IN ('contribution','withdrawal')), amount REAL NOT NULL, notes TEXT, FOREIGN KEY(investor_id) REFERENCES investors(id) ON DELETE CASCADE)"
        )
        cur.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
        cur.execute("INSERT OR IGNORE INTO settings(key, value) VALUES('investor_pool_percent','20')")

        # Load pool percent
        cur.execute("SELECT value FROM settings WHERE key='investor_pool_percent'")
        pool_val = cur.fetchone()
        pool_percent = float(pool_val[0]) if pool_val and pool_val[0] else 0.0
        self.entry_pool.delete(0, tk.END)
        self.entry_pool.insert(0, f"{pool_percent:g}")

        # Compute current capital and shares
        cur.execute(
            """
            SELECT i.id, i.name, COALESCE(i.phone,''), i.initial_capital,
                   COALESCE(i.initial_date,''),
                   COALESCE((SELECT SUM(CASE WHEN t.type='contribution' THEN t.amount WHEN t.type='withdrawal' THEN -t.amount ELSE 0 END)
                            FROM investor_transactions t WHERE t.investor_id = i.id), 0)
            FROM investors i
            ORDER BY i.id
            """
        )
        rows = cur.fetchall()
        totals_current = []
        for _iid, _name, _phone, init_cap, _date, tx_sum in rows:
            totals_current.append(float(init_cap) + float(tx_sum))
        total_current_cap = sum(totals_current) if totals_current else 0.0

        # Fill tree with computed fields
        for idx, (iid, name, phone, init_cap, d, tx_sum) in enumerate(rows):
            current_cap = float(init_cap) + float(tx_sum)
            pool_share = (current_cap / total_current_cap * 100.0) if total_current_cap > 0 else 0.0
            shop_share = pool_share * (pool_percent / 100.0)
            self.tree.insert(
                "",
                "end",
                values=(iid, name, phone, f"{float(init_cap):.2f}", f"{current_cap:.2f}", f"{pool_share:.2f}", f"{shop_share:.2f}", d),
            )

        # Default date to today if empty and tx default date
        cur.execute("SELECT date('now')")
        today = cur.fetchone()[0]
        conn.close()
        try:
            if isinstance(self.entry_date, tk.Entry) and not self.entry_date.get().strip():
                self.entry_date.insert(0, today)
            if isinstance(self.tx_date, tk.Entry) and not self.tx_date.get().strip():
                self.tx_date.insert(0, today)
        except Exception:
            pass
        # Update pool info label
        self.lbl_pool_info.config(text=f"Toplam havuz: {pool_percent:.2f}%, Dükkan kalan: {100.0 - pool_percent:.2f}%")

    def add_investor(self) -> None:
        name = self.entry_name.get().strip()
        phone = self.entry_phone.get().strip() or None
        notes = self.entry_notes.get().strip() or None
        date = self.entry_date.get().strip() or None
        cap = self._parse_amount(self.entry_capital.get().strip() or "0")
        if not name:
            messagebox.showwarning("Eksik bilgi", "İsim gerekli.")
            return
        if cap != cap or cap < 0:
            messagebox.showwarning("Geçersiz tutar", "Geçersiz başlangıç sermayesi.")
            return
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        if date:
            cur.execute(
                "INSERT INTO investors (name, phone, initial_capital, initial_date, notes) VALUES (?, ?, ?, ?, ?)",
                (name, phone, cap, date, notes),
            )
        else:
            cur.execute(
                "INSERT INTO investors (name, phone, initial_capital, notes) VALUES (?, ?, ?, ?)",
                (name, phone, cap, notes),
            )
        conn.commit()
        conn.close()
        self.entry_name.delete(0, tk.END)
        self.entry_phone.delete(0, tk.END)
        self.entry_capital.delete(0, tk.END)
        self.entry_notes.delete(0, tk.END)
        self.refresh()

    def update_investor(self) -> None:
        iid = self._selected_id()
        if iid is None:
            messagebox.showinfo("Seçim yok", "Güncellenecek yatırımcıyı seçin.")
            return
        name = self.entry_name.get().strip()
        phone = self.entry_phone.get().strip() or None
        notes = self.entry_notes.get().strip() or None
        date = self.entry_date.get().strip() or None
        cap = self._parse_amount(self.entry_capital.get().strip() or "0")
        if not name:
            messagebox.showwarning("Eksik bilgi", "İsim gerekli.")
            return
        if cap != cap or cap < 0:
            messagebox.showwarning("Geçersiz tutar", "Geçersiz başlangıç sermayesi.")
            return
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        if not date:
            cur.execute("SELECT date('now')")
            date = cur.fetchone()[0]
        cur.execute(
            "UPDATE investors SET name = ?, phone = ?, initial_capital = ?, initial_date = ?, notes = ? WHERE id = ?",
            (name, phone, cap, date, notes, iid),
        )
        conn.commit()
        conn.close()
        self.refresh()

    def delete_investor(self) -> None:
        iid = self._selected_id()
        if iid is None:
            messagebox.showinfo("Seçim yok", "Silinecek yatırımcıyı seçin.")
            return
        if not messagebox.askyesno("Onay", "Seçili yatırımcıyı silmek istiyor musunuz?"):
            return
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("DELETE FROM investors WHERE id = ?", (iid,))
        conn.commit()
        conn.close()
        self.refresh()

    # Transactions
    def _selected_investor_id(self):
        sel = self.tree.selection()
        if not sel:
            return None
        vals = self.tree.item(sel[0], "values")
        return int(vals[0])

    def refresh_transactions(self, investor_id: int) -> None:
        for iid in self.tx_tree.get_children():
            self.tx_tree.delete(iid)
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute(
            "SELECT id, COALESCE(date,''), type, amount, COALESCE(notes,'') FROM investor_transactions WHERE investor_id = ? ORDER BY date DESC, id DESC",
            (investor_id,),
        )
        for tid, d, typ, amt, notes in cur.fetchall():
            self.tx_tree.insert("", "end", values=(tid, d, typ, f"{float(amt):.2f}", notes))
        conn.close()

    def add_tx(self, typ: str) -> None:
        iid = self._selected_investor_id()
        if iid is None:
            messagebox.showinfo("Seçim yok", "İşlem için yatırımcı seçin.")
            return
        date = self.tx_date.get().strip() or None
        try:
            amt = float(self.tx_amount.get().replace(",", "."))
        except Exception:
            amt = float("nan")
        if amt != amt or amt <= 0:
            messagebox.showwarning("Geçersiz tutar", "Pozitif bir tutar girin.")
            return
        notes = self.tx_notes.get().strip() or None
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        if date:
            cur.execute(
                "INSERT INTO investor_transactions (investor_id, date, type, amount, notes) VALUES (?, ?, ?, ?, ?)",
                (iid, date, typ, amt, notes),
            )
        else:
            cur.execute(
                "INSERT INTO investor_transactions (investor_id, type, amount, notes) VALUES (?, ?, ?, ?)",
                (iid, typ, amt, notes),
            )
        conn.commit()
        conn.close()
        self.tx_amount.delete(0, tk.END)
        self.tx_notes.delete(0, tk.END)
        self.refresh()
        self.refresh_transactions(iid)

    def delete_tx(self) -> None:
        sel = self.tx_tree.selection()
        if not sel:
            messagebox.showinfo("Seçim yok", "Silinecek işlemi seçin.")
            return
        tid = int(self.tx_tree.item(sel[0], "values")[0])
        if not messagebox.askyesno("Onay", "Seçili işlemi silmek istiyor musunuz?"):
            return
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("DELETE FROM investor_transactions WHERE id = ?", (tid,))
        conn.commit()
        conn.close()
        iid = self._selected_investor_id()
        self.refresh()
        if iid is not None:
            self.refresh_transactions(iid)

    def save_pool_percent(self) -> None:
        try:
            val = float(self.entry_pool.get().replace(",", "."))
        except Exception:
            val = float("nan")
        if val != val or val < 0 or val > 100:
            messagebox.showwarning("Geçersiz değer", "Havuz % 0 ile 100 arası olmalıdır.")
            return
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("INSERT INTO settings(key, value) VALUES('investor_pool_percent', ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (f"{val}",))
        conn.commit()
        conn.close()
        self.refresh()

