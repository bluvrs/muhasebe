import sqlite3
import tkinter as tk
from tkinter import ttk

DB_NAME = "coop.db"


class ReportsFrame(tk.Frame):
    def __init__(self, parent: tk.Misc, controller) -> None:
        super().__init__(parent)
        self.controller = controller

        tk.Label(self, text="Raporlar", font=("Arial", 16, "bold")).pack(pady=(20, 10))

        self.container = tk.Frame(self)
        self.container.pack(fill="x", padx=20)

        # Stats area
        self.stats_vars = {
            "total_products": tk.StringVar(value="0"),
            "total_stock_items": tk.StringVar(value="0"),
            "total_stock_value": tk.StringVar(value="0.00"),
            "total_income": tk.StringVar(value="0.00"),
            "total_outcome": tk.StringVar(value="0.00"),
            "net": tk.StringVar(value="0.00"),
        }

        grid = tk.Frame(self.container)
        grid.pack(fill="x", pady=(10, 10))

        def add_row(r, label, var):
            tk.Label(grid, text=label).grid(row=r, column=0, sticky="w", padx=(0, 10))
            tk.Label(grid, textvariable=var, font=("Arial", 12, "bold")).grid(row=r, column=1, sticky="w")

        add_row(0, "Toplam Urun:", self.stats_vars["total_products"])
        add_row(1, "Toplam Stok (birim):", self.stats_vars["total_stock_items"])
        add_row(2, "Toplam Stok Degeri:", self.stats_vars["total_stock_value"])
        add_row(3, "Toplam Gelir:", self.stats_vars["total_income"])
        add_row(4, "Toplam Gider:", self.stats_vars["total_outcome"])
        add_row(5, "Net (Gelir - Gider):", self.stats_vars["net"])

        # Ledger list (read-only)
        tk.Label(self, text="Gelir/Gider Kayitlari", font=("Arial", 12, "bold")).pack(anchor="w", padx=20)
        columns = ("date", "type", "amount", "description")
        self.ledger_tree = ttk.Treeview(self, columns=columns, show="headings", height=10)
        self.ledger_tree.heading("date", text="Tarih")
        self.ledger_tree.heading("type", text="Tur")
        self.ledger_tree.heading("amount", text="Tutar")
        self.ledger_tree.heading("description", text="Aciklama")
        self.ledger_tree.column("date", width=100)
        self.ledger_tree.column("type", width=80, anchor="center")
        self.ledger_tree.column("amount", width=120, anchor="e")
        self.ledger_tree.column("description", width=400)
        self.ledger_tree.pack(fill="both", expand=True, padx=20, pady=(4, 10))

        btns = tk.Frame(self)
        btns.pack(fill="x", padx=20, pady=(0, 10))
        tk.Button(btns, text="Yenile", command=self.refresh).pack(side="left")
        tk.Button(btns, text="Geri", command=self.go_back).pack(side="right")

        self.refresh()

    def on_show(self, **kwargs) -> None:
        self.controller.title("Kooperatif - Raporlar")
        self.refresh()

    def go_back(self) -> None:
        user = getattr(self.controller, "active_user", None)
        if user and "username" in user and "role" in user:
            self.controller.show_role_screen(user["role"], user["username"])
        else:
            self.controller.logout()

    def refresh(self) -> None:
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        # Ensure tables exist in case of fresh DB
        cur.execute("CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, barcode TEXT UNIQUE, price REAL NOT NULL DEFAULT 0, stock REAL NOT NULL DEFAULT 0, unit TEXT NOT NULL DEFAULT 'adet')")
        cur.execute("CREATE TABLE IF NOT EXISTS ledger (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT NOT NULL DEFAULT (date('now')), type TEXT NOT NULL CHECK(type IN ('gelir','gider')), amount REAL NOT NULL, description TEXT)")
        # Stats
        cur.execute("SELECT COUNT(*), COALESCE(SUM(stock), 0), COALESCE(SUM(price * stock), 0) FROM products")
        count, total_stock, total_value = cur.fetchone()
        # Income/Outcome totals
        cur.execute("SELECT COALESCE(SUM(amount),0) FROM ledger WHERE type='gelir'")
        total_income = cur.fetchone()[0]
        cur.execute("SELECT COALESCE(SUM(amount),0) FROM ledger WHERE type='gider'")
        total_outcome = cur.fetchone()[0]
        # Load last 100 ledger rows
        cur.execute("SELECT date, type, amount, COALESCE(description,'') FROM ledger ORDER BY date DESC, id DESC LIMIT 100")
        rows = cur.fetchall()
        conn.close()
        self.stats_vars["total_products"].set(str(count))
        # Show stock without trailing .0 if integer-like
        if float(total_stock).is_integer():
            self.stats_vars["total_stock_items"].set(str(int(total_stock)))
        else:
            self.stats_vars["total_stock_items"].set(str(total_stock))
        self.stats_vars["total_stock_value"].set(f"{float(total_value):.2f}")
        self.stats_vars["total_income"].set(f"{float(total_income):.2f}")
        self.stats_vars["total_outcome"].set(f"{float(total_outcome):.2f}")
        self.stats_vars["net"].set(f"{float(total_income - total_outcome):.2f}")

        for row in self.ledger_tree.get_children():
            self.ledger_tree.delete(row)
        for d, t, a, desc in rows:
            self.ledger_tree.insert("", "end", values=(d, t, f"{float(a):.2f}", desc))
