import sqlite3
import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
from datetime import datetime, date
try:
    from tkcalendar import DateEntry as _DateEntry  # type: ignore
except Exception:
    _DateEntry = None  # type: ignore
from ui import make_back_arrow

DB_NAME = "coop.db"


class SalesFrame(tk.Frame):
    def __init__(self, parent: tk.Misc, controller) -> None:
        super().__init__(parent)
        self.controller = controller

        # Header with back arrow
        header = tk.Frame(self)
        header.pack(fill='x')
        back = make_back_arrow(header, self.go_back)
        back.pack(side='left', padx=(10,6), pady=(10,6))
        tk.Label(header, text="Yeni Satış", font=("Arial", 16, "bold")).pack(side='left', pady=(16,6))

        # Scan/Search bar
        sb = tk.Frame(self)
        sb.pack(fill="x", padx=20)
        tk.Label(sb, text="Barkod/İsim:").pack(side="left")
        self.entry_scan = tk.Entry(sb)
        self.entry_scan.pack(side="left", fill="x", expand=True, padx=(6, 6))
        tk.Label(sb, text="Adet/Miktar:").pack(side="left")
        self.entry_qty = tk.Entry(sb, width=8)
        self.entry_qty.insert(0, "1")
        self.entry_qty.pack(side="left", padx=(6, 6))
        tk.Button(sb, text="Ekle", command=self.add_to_cart).pack(side="left")
        tk.Button(sb, text="Sepeti Temizle", command=self.clear_cart).pack(side="left", padx=(8, 0))

        # Cart
        columns = ("product_id", "name", "barcode", "price", "qty", "total")
        self.cart = ttk.Treeview(self, columns=columns, show="headings", height=12)
        self.cart.heading("product_id", text="PID")
        self.cart.heading("name", text="Isim")
        self.cart.heading("barcode", text="Barkod")
        self.cart.heading("price", text="Fiyat")
        self.cart.heading("qty", text="Miktar")
        self.cart.heading("total", text="Toplam")
        self.cart.column("product_id", width=60, anchor="center")
        self.cart.column("name", width=240)
        self.cart.column("barcode", width=150)
        self.cart.column("price", width=100, anchor="e")
        self.cart.column("qty", width=80, anchor="e")
        self.cart.column("total", width=120, anchor="e")
        self.cart.pack(fill="both", expand=True, padx=20, pady=(8, 8))

        # Totals + actions
        bottom = tk.Frame(self)
        bottom.pack(fill="x", padx=20, pady=(0, 10))
        # Sale date controls
        tk.Label(bottom, text="Tarih:").pack(side="left")
        if _DateEntry is not None:
            self.entry_date = _DateEntry(bottom, date_pattern="yyyy-mm-dd", state="readonly")
            try:
                self.entry_date.set_date(date.today())
            except Exception:
                pass
        else:
            self.entry_date = tk.Entry(bottom, width=20)
        self.entry_date.pack(side="left", padx=(6, 6))
        tk.Button(bottom, text="Şimdi", command=self._set_now).pack(side="left", padx=(0, 20))
        self.total_var = tk.StringVar(value="0.00")
        tk.Label(bottom, text="Genel Toplam:").pack(side="left")
        tk.Label(bottom, textvariable=self.total_var, font=("Arial", 12, "bold")).pack(side="left", padx=(6, 20))
        # Payment inputs
        tk.Label(bottom, text="Ödenen:").pack(side="left")
        self.entry_paid = tk.Entry(bottom, width=10)
        self.entry_paid.pack(side="left", padx=(6, 6))
        tk.Label(bottom, text="Paraüstü:").pack(side="left")
        self.change_var = tk.StringVar(value="0.00")
        tk.Label(bottom, textvariable=self.change_var, font=("Arial", 12, "bold")).pack(side="left", padx=(6, 20))
        # Actions
        tk.Button(bottom, text="Satışı Tamamla", command=self.complete_sale).pack(side="right")

        # Inline status message (instead of many popups)
        self.status_var = tk.StringVar(value="")
        status = tk.Label(self, textvariable=self.status_var, fg="#444")
        status.pack(fill="x", padx=20, pady=(0, 6))

        # Bind enter to add item
        self.entry_scan.bind("<Return>", lambda _e: self.add_to_cart())
        self.entry_qty.bind("<Return>", lambda _e: self.add_to_cart())
        # Update change dynamically when paid input changes
        self.entry_paid.bind("<KeyRelease>", self._update_change)

        self._set_now()
        self._recalc_total()

    def on_show(self, **kwargs) -> None:
        self.controller.title("Kooperatif - Yeni Satış")
        self.entry_scan.focus_set()

    def go_back(self) -> None:
        user = getattr(self.controller, "active_user", None)
        if user and "username" in user and "role" in user:
            self.controller.show_role_screen(user["role"], user["username"])
        else:
            self.controller.logout()

    # Helpers
    def _set_now(self) -> None:
        nowd = date.today()
        try:
            if isinstance(self.entry_date, tk.Entry):
                self.entry_date.delete(0, tk.END)
                self.entry_date.insert(0, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            else:
                self.entry_date.set_date(nowd)
        except Exception:
            pass

    def _parse_qty(self, s: str) -> float:
        try:
            s = s.replace(",", ".")
            return float(s)
        except Exception:
            return float("nan")

    def _find_product(self, text: str):
        text = text.strip()
        if not text:
            return None
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        # Prefer barcode exact match, fall back to name like
        cur.execute("SELECT id, name, barcode, price, stock, unit FROM products WHERE barcode = ?", (text,))
        row = cur.fetchone()
        if not row:
            cur.execute(
                "SELECT id, name, barcode, price, stock, unit FROM products WHERE name LIKE ? ORDER BY id LIMIT 1",
                (f"%{text}%",),
            )
            row = cur.fetchone()
        conn.close()
        return row

    def _recalc_total(self) -> None:
        total = 0.0
        for iid in self.cart.get_children():
            vals = self.cart.item(iid, "values")
            total += float(vals[5])
        self.total_var.set(f"{total:.2f}")
        self._update_change()

    def _parse_money(self, s: str) -> float:
        try:
            s = (s or "").strip().replace(",", ".")
            return float(s) if s else 0.0
        except Exception:
            return float("nan")

    def _update_change(self, _e=None) -> None:
        try:
            total = float(self.total_var.get())
        except Exception:
            total = 0.0
        paid = self._parse_money(self.entry_paid.get() if hasattr(self, 'entry_paid') else "0")
        if paid != paid:  # NaN
            self.change_var.set("0.00")
            return
        change = paid - total
        if change < 0:
            change = 0.0
        self.change_var.set(f"{change:.2f}")

    def clear_cart(self) -> None:
        for iid in self.cart.get_children():
            self.cart.delete(iid)
        self._recalc_total()
        self.status_var.set("")

    def add_to_cart(self) -> None:
        query = self.entry_scan.get().strip()
        qty = self._parse_qty(self.entry_qty.get().strip() or "1")
        if qty != qty or qty <= 0:
            self.status_var.set("Geçersiz miktar. Pozitif bir miktar girin.")
            return
        prod = self._find_product(query)
        if not prod:
            self.status_var.set("Ürün bulunamadı.")
            return
        pid, name, barcode, price, stock, unit = prod
        if stock is None:
            stock = 0.0
        if qty > float(stock):
            self.status_var.set(f"Yetersiz stok. Stokta {stock} {unit} var.")
            return
        # Merge with existing line if same product
        for iid in self.cart.get_children():
            vals = self.cart.item(iid, "values")
            if int(vals[0]) == int(pid):
                cur_qty = float(vals[4])
                new_qty = cur_qty + qty
                if new_qty > float(stock):
                    self.status_var.set(f"Yetersiz stok. Stokta {stock} {unit} var.")
                    return
                line_total = float(price) * new_qty
                self.cart.item(iid, values=(pid, name, barcode or "", f"{float(price):.2f}", f"{new_qty:g}", f"{line_total:.2f}"))
                break
        else:
            line_total = float(price) * qty
            self.cart.insert("", "end", values=(pid, name, barcode or "", f"{float(price):.2f}", f"{qty:g}", f"{line_total:.2f}"))
        self.entry_scan.delete(0, tk.END)
        self.entry_qty.delete(0, tk.END)
        self.entry_qty.insert(0, "1")
        self.entry_scan.focus_set()
        self._recalc_total()
        self.status_var.set("")

    def complete_sale(self) -> None:
        items = [self.cart.item(iid, "values") for iid in self.cart.get_children()]
        if not items:
            self.status_var.set("Sepet boş.")
            return
        total = float(self.total_var.get())
        paid = self._parse_money(self.entry_paid.get())
        if paid != paid:
            self.status_var.set("Geçersiz ödenen tutar.")
            return
        if paid < total:
            self.status_var.set("Ödenen tutar yetersiz.")
            return
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        try:
            # Create sale
            date_str = (self.entry_date.get().strip() if hasattr(self, 'entry_date') else "") or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cur.execute("INSERT INTO sales (date, total) VALUES (?, ?)", (date_str, total))
            sale_id = cur.lastrowid
            # Insert items and update stock
            for pid, _name, _barcode, price, qty, _line_total in items:
                cur.execute(
                    "INSERT INTO sale_items (sale_id, product_id, quantity, price) VALUES (?, ?, ?, ?)",
                    (sale_id, int(pid), float(qty), float(price)),
                )
                cur.execute("UPDATE products SET stock = stock - ? WHERE id = ?", (float(qty), int(pid)))
            # Add to ledger as income
            cur.execute(
                "INSERT INTO ledger (type, amount, description) VALUES ('gelir', ?, ?)",
                (total, f"Satış #{sale_id}"),
            )
            # Add to cashbook as cash-in
            cur.execute(
                "INSERT INTO cashbook (type, amount, description) VALUES ('in', ?, ?)",
                (total, f"Satış #{sale_id}"),
            )
            conn.commit()
        except Exception as e:
            conn.rollback()
            self.status_var.set(f"Satış tamamlanamadı: {e}")
            return
        finally:
            conn.close()
        self.clear_cart()
        change = paid - total
        self.entry_paid.delete(0, tk.END)
        self.status_var.set(f"Satış tamamlandı. Ödenen: {paid:.2f}, Paraüstü: {change:.2f}")
        self._update_change()


class ReturnFrame(tk.Frame):
    def __init__(self, parent: tk.Misc, controller) -> None:
        super().__init__(parent)
        self.controller = controller

        # Header
        header = tk.Frame(self)
        header.pack(fill='x')
        back = make_back_arrow(header, self.go_back)
        back.pack(side='left', padx=(10,6), pady=(10,6))
        tk.Label(header, text="İade İşlemi", font=("Arial", 16, "bold")).pack(side='left', pady=(16,6))

        # Select original sale
        sale_bar = tk.Frame(self)
        sale_bar.pack(fill='x', padx=20, pady=(4, 2))
        tk.Label(sale_bar, text="Satış #:").pack(side='left')
        self.sale_id_var = tk.StringVar(value="")
        self.entry_sale = tk.Entry(sale_bar, textvariable=self.sale_id_var, width=8)
        self.entry_sale.pack(side='left', padx=(6, 6))
        tk.Button(sale_bar, text="Yükle", command=self._load_sale).pack(side='left')
        self.sale_info_var = tk.StringVar(value="")
        tk.Label(sale_bar, textvariable=self.sale_info_var, fg="#555").pack(side='left', padx=(12,0))

        # Scan/Search bar
        sb = tk.Frame(self)
        sb.pack(fill="x", padx=20)
        tk.Label(sb, text="Barkod/İsim:").pack(side="left")
        self.entry_scan = tk.Entry(sb)
        self.entry_scan.pack(side="left", fill="x", expand=True, padx=(6, 6))
        tk.Button(sb, text="Satışları Listele", command=self._list_sales_for_product).pack(side="left", padx=(0, 10))
        tk.Label(sb, text="İade Adedi:").pack(side="left")
        vcmd = (self.register(lambda s: s.isdigit() or s==''), '%P')
        self.entry_qty = tk.Entry(sb, width=8, validate='key', validatecommand=vcmd)
        self.entry_qty.insert(0, "1")
        self.entry_qty.pack(side="left", padx=(6, 6))
        tk.Button(sb, text="Ekle", command=self.add_to_cart).pack(side="left")
        tk.Button(sb, text="Sepeti Temizle", command=self.clear_cart).pack(side="left", padx=(8, 0))

        # Past purchases list
        purchases_frame = tk.Frame(self)
        purchases_frame.pack(fill='x', padx=20, pady=(6, 0))
        tk.Label(purchases_frame, text="Geçmiş Satışlar", font=("Arial", 12, "bold")).pack(anchor='w')
        self.purchases = ttk.Treeview(purchases_frame, columns=("sale_id","date","qty","returned","remaining","price"), show='headings', height=6)
        for col, lbl, w, anc in (
            ("sale_id","Satış #",80,"center"),
            ("date","Tarih",140,"w"),
            ("qty","Adet",70,"e"),
            ("returned","İade",70,"e"),
            ("remaining","Kalan",70,"e"),
            ("price","Fiyat",80,"e"),
        ):
            self.purchases.heading(col, text=lbl)
            self.purchases.column(col, width=w, anchor=anc)
        self.purchases.pack(fill='x')
        self.purchases.bind('<Double-1>', self._on_purchase_dblclick)

        # Cart
        columns = ("product_id", "name", "barcode", "price", "qty", "total")
        self.cart = ttk.Treeview(self, columns=columns, show="headings", height=12)
        for col, lbl, w, anc in (
            ("product_id", "PID", 60, "center"),
            ("name", "İsim", 240, "w"),
            ("barcode", "Barkod", 150, "w"),
            ("price", "Fiyat", 100, "e"),
            ("qty", "Miktar", 80, "e"),
            ("total", "Toplam", 120, "e"),
        ):
            self.cart.heading(col, text=lbl)
            self.cart.column(col, width=w, anchor=anc)
        self.cart.pack(fill="both", expand=True, padx=20, pady=(8, 8))

        # Totals + actions
        bottom = tk.Frame(self)
        bottom.pack(fill="x", padx=20, pady=(0, 10))
        tk.Label(bottom, text="Tarih:").pack(side="left")
        if _DateEntry is not None:
            self.entry_date = _DateEntry(bottom, date_pattern="yyyy-mm-dd", state="readonly")
            try:
                self.entry_date.set_date(date.today())
            except Exception:
                pass
        else:
            self.entry_date = tk.Entry(bottom, width=20)
        self.entry_date.pack(side="left", padx=(6, 6))
        tk.Button(bottom, text="Şimdi", command=self._set_now).pack(side="left", padx=(0, 20))
        self.total_var = tk.StringVar(value="0.00")
        tk.Label(bottom, text="İade Tutarı:").pack(side="left")
        tk.Label(bottom, textvariable=self.total_var, font=("Arial", 12, "bold")).pack(side="left", padx=(6, 20))
        tk.Label(bottom, text="Verilen:").pack(side="left")
        self.entry_paid = tk.Entry(bottom, width=10)
        self.entry_paid.pack(side="left", padx=(6, 6))
        tk.Label(bottom, text="Fark:").pack(side="left")
        self.change_var = tk.StringVar(value="0.00")
        tk.Label(bottom, textvariable=self.change_var, font=("Arial", 12, "bold")).pack(side="left", padx=(6, 20))
        tk.Button(bottom, text="İadeyi Tamamla", command=self.complete_return).pack(side="right")

        # Status label
        self.status_var = tk.StringVar(value="")
        status = tk.Label(self, textvariable=self.status_var, fg="#444")
        status.pack(fill="x", padx=20, pady=(0, 6))

        # Binds
        self.entry_scan.bind("<Return>", lambda _e: self._list_sales_for_product())
        self.entry_qty.bind("<Return>", lambda _e: self.add_to_cart())
        self.entry_paid.bind("<KeyRelease>", self._update_change)

        self._set_now()
        self._recalc_total()

        # Internal maps for original sale
        self._allowed_qty = {}  # pid -> remaining refundable qty
        self._orig_price = {}   # pid -> original sale unit price
        self._active_pid = None

    def on_show(self, **kwargs) -> None:
        self.controller.title("Kooperatif - İade İşlemi")
        self.entry_scan.focus_set()

    # Navigation
    def go_back(self) -> None:
        user = getattr(self.controller, "active_user", None)
        if user and "username" in user and "role" in user:
            self.controller.show_role_screen(user["role"], user["username"])
        else:
            self.controller.logout()

    # Helpers
    def _set_now(self) -> None:
        try:
            if isinstance(self.entry_date, tk.Entry):
                self.entry_date.delete(0, tk.END)
                self.entry_date.insert(0, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            else:
                self.entry_date.set_date(date.today())
        except Exception:
            pass

    def _parse_qty(self, s: str) -> float:
        try:
            s = s.replace(",", ".")
            return float(s)
        except Exception:
            return float("nan")

    def _parse_money(self, s: str) -> float:
        try:
            s = (s or "").strip().replace(",", ".")
            return float(s) if s else 0.0
        except Exception:
            return float("nan")

    def _find_product(self, text: str):
        text = text.strip()
        if not text:
            return None
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("SELECT id, name, barcode, price, stock, unit FROM products WHERE barcode = ?", (text,))
        row = cur.fetchone()
        if not row:
            cur.execute(
                "SELECT id, name, barcode, price, stock, unit FROM products WHERE name LIKE ? ORDER BY id LIMIT 1",
                (f"%{text}%",),
            )
            row = cur.fetchone()
        conn.close()
        return row

    def _recalc_total(self) -> None:
        total = 0.0
        for iid in self.cart.get_children():
            vals = self.cart.item(iid, "values")
            total += float(vals[5])
        self.total_var.set(f"{total:.2f}")
        self._update_change()

    def _ensure_returns_table(self, cur) -> None:
        cur.execute(
            "CREATE TABLE IF NOT EXISTS returns (id INTEGER PRIMARY KEY AUTOINCREMENT, original_sale_id INTEGER NOT NULL, return_sale_id INTEGER NOT NULL, date TEXT NOT NULL DEFAULT (datetime('now')))"
        )

    def _list_sales_for_product(self) -> None:
        q = (self.entry_scan.get() or '').strip()
        for iid in getattr(self, 'purchases', ttk.Treeview()).get_children():
            self.purchases.delete(iid)
        if not q:
            self.status_var.set("Ürün barkodu/ismi girin.")
            return
        prod = self._find_product(q)
        if not prod:
            self.status_var.set("Ürün bulunamadı.")
            return
        pid, _name, _barcode, _price, _stock, _unit = prod
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        self._ensure_returns_table(cur)
        cur.execute(
            "SELECT s.id, s.date, SUM(si.quantity) AS qty, MAX(si.price) AS price FROM sales s JOIN sale_items si ON si.sale_id = s.id WHERE si.product_id = ? AND si.quantity > 0 GROUP BY s.id, s.date ORDER BY s.date DESC",
            (int(pid),)
        )
        rows = cur.fetchall()
        for sid, d, qty, price in rows:
            cur.execute("SELECT return_sale_id FROM returns WHERE original_sale_id = ?", (sid,))
            ret_ids = [r[0] for r in cur.fetchall()]
            returned = 0.0
            if ret_ids:
                qmarks = ",".join(["?"] * len(ret_ids))
                cur.execute(f"SELECT COALESCE(SUM(-quantity),0) FROM sale_items WHERE product_id = ? AND sale_id IN ({qmarks})", (int(pid), *ret_ids))
                returned = float(cur.fetchone()[0] or 0.0)
            remaining = float(qty or 0.0) - returned
            if remaining > 0:
                self.purchases.insert('', 'end', values=(sid, d, f"{float(qty):g}", f"{returned:g}", f"{remaining:g}", f"{float(price):.2f}"))
        conn.close()
        self._active_pid = int(pid)
        self.status_var.set("Satışlar listelendi. Bir satıra çift tıklayın.")

    def _on_purchase_dblclick(self, _e=None):
        sel = self.purchases.selection()
        if not sel:
            return
        sid, d, qty, returned, remaining, price = self.purchases.item(sel[0], 'values')
        # Load the selected sale
        self.sale_id_var.set(str(sid))
        self._load_sale()
        # Pre-fill qty 1
        self.entry_qty.delete(0, tk.END)
        self.entry_qty.insert(0, '1')
        self.status_var.set(f"Satış #{sid} yüklendi. İade adedini girip Ekle deyin.")

    def _load_sale(self) -> None:
        sid_txt = (self.sale_id_var.get() or "").strip()
        try:
            sid = int(sid_txt)
        except Exception:
            self.status_var.set("Geçersiz Satış #.")
            return
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        try:
            # Verify sale exists
            cur.execute("SELECT id, date, total FROM sales WHERE id = ?", (sid,))
            sale = cur.fetchone()
            if not sale:
                self.sale_info_var.set("")
                self.status_var.set("Satış bulunamadı.")
                return
            # Load purchased quantities and prices
            cur.execute("SELECT product_id, SUM(quantity), price FROM sale_items WHERE sale_id = ? GROUP BY product_id", (sid,))
            purchased = {int(pid): float(qty or 0.0) for pid, qty, _price in cur.fetchall()}
            # Prefer original price per product as last price in that sale
            cur.execute("SELECT product_id, price FROM sale_items WHERE sale_id = ?", (sid,))
            self._orig_price = {}
            for pid, price in cur.fetchall():
                self._orig_price[int(pid)] = float(price)
            # Subtract previous returns linked to this sale
            self._ensure_returns_table(cur)
            cur.execute("SELECT return_sale_id FROM returns WHERE original_sale_id = ?", (sid,))
            ret_ids = [r[0] for r in cur.fetchall()]
            returned = {}
            if ret_ids:
                qmarks = ",".join(["?"] * len(ret_ids))
                cur.execute(f"SELECT product_id, SUM(quantity) FROM sale_items WHERE sale_id IN ({qmarks}) GROUP BY product_id", ret_ids)
                for pid, qty in cur.fetchall():
                    # qty are negative; add to compute net remaining
                    returned[int(pid)] = float(qty or 0.0)
            # Compute remaining refundable
            self._allowed_qty = {}
            for pid, qty in purchased.items():
                prev = returned.get(pid, 0.0)
                remaining = float(qty) + float(prev)  # prev is negative
                if remaining > 0:
                    self._allowed_qty[pid] = remaining
            # Update info
            date_s = sale[1]
            total_s = float(sale[2])
            self.sale_info_var.set(f"Tarih: {date_s}, Toplam: {total_s:.2f}")
            self.status_var.set("Satış yüklendi. Ürünleri ekleyin.")
            # Clear current cart
            self.clear_cart()
        finally:
            conn.close()

    def _update_change(self, _e=None) -> None:
        try:
            total = float(self.total_var.get())
        except Exception:
            total = 0.0
        paid = self._parse_money(self.entry_paid.get())
        if paid != paid:
            self.change_var.set("0.00")
            return
        diff = paid - total  # >0 fazla verilmiş, <0 eksik
        self.change_var.set(f"{diff:.2f}")

    def clear_cart(self) -> None:
        for iid in self.cart.get_children():
            self.cart.delete(iid)
        self._recalc_total()
        self.status_var.set("")

    def add_to_cart(self) -> None:
        # Ensure a sale is selected
        try:
            sid = int((self.sale_id_var.get() or "").strip())
        except Exception:
            sid = 0
        if not sid or not self._allowed_qty:
            self.status_var.set("Önce listeden bir satış seçin.")
            return
        # Validate integer quantity
        qty_s = (self.entry_qty.get() or '').strip()
        if not qty_s.isdigit():
            self.status_var.set("İade adedi sadece rakam olmalıdır.")
            return
        qty = int(qty_s)
        if qty <= 0:
            self.status_var.set("İade adedi 0'dan büyük olmalı.")
            return
        # Resolve product from current query
        prod = self._find_product((self.entry_scan.get() or '').strip())
        if not prod:
            self.status_var.set("Ürün bulunamadı.")
            return
        pid, name, barcode, _price_ignore, _stock, _unit = prod
        if int(pid) not in self._allowed_qty:
            self.status_var.set("Bu ürün seçilen satışta yok ya da iade edilemez.")
            return
        remaining = float(self._allowed_qty.get(int(pid), 0.0))
        if qty > remaining:
            self.status_var.set(f"En fazla {remaining:g} iade edilebilir.")
            return
        price = float(self._orig_price.get(int(pid), _price_ignore or 0.0))
        # Merge lines
        for iid in self.cart.get_children():
            vals = self.cart.item(iid, "values")
            if int(vals[0]) == int(pid):
                cur_qty = float(vals[4])
                new_qty = cur_qty + qty
                if new_qty > remaining:
                    self.status_var.set(f"En fazla {remaining:g} iade edilebilir.")
                    return
                line_total = float(price) * new_qty
                self.cart.item(iid, values=(pid, name, barcode or "", f"{float(price):.2f}", f"{new_qty:g}", f"{line_total:.2f}"))
                break
        else:
            line_total = float(price) * qty
            self.cart.insert("", "end", values=(pid, name, barcode or "", f"{float(price):.2f}", f"{qty:g}", f"{line_total:.2f}"))
        self.entry_qty.delete(0, tk.END)
        self.entry_qty.insert(0, "1")
        self._recalc_total()
        self.status_var.set("Sepete eklendi.")

    def complete_return(self) -> None:
        items = [self.cart.item(iid, "values") for iid in self.cart.get_children()]
        if not items:
            self.status_var.set("Sepet boş.")
            return
        total = float(self.total_var.get())
        paid = self._parse_money(self.entry_paid.get())
        if paid != paid:
            self.status_var.set("Geçersiz verilen tutar.")
            return
        if paid < total:
            self.status_var.set("Verilen tutar yetersiz.")
            return
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        try:
            date_str = (self.entry_date.get().strip() or datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            # Record return as negative sale
            cur.execute("INSERT INTO sales (date, total) VALUES (?, ?)", (date_str, -total))
            sale_id = cur.lastrowid
            for pid, _name, _barcode, price, qty, _line_total in items:
                # Negative quantity represents return
                cur.execute(
                    "INSERT INTO sale_items (sale_id, product_id, quantity, price) VALUES (?, ?, ?, ?)",
                    (sale_id, int(pid), -float(qty), float(price)),
                )
                # Put items back to stock
                cur.execute("UPDATE products SET stock = stock + ? WHERE id = ?", (float(qty), int(pid)))
            # Ledger as expense (money leaves the till)
            cur.execute(
                "INSERT INTO ledger (type, amount, description) VALUES ('gider', ?, ?)",
                (total, f"İade #{sale_id}"),
            )
            # Cashbook as cash-out
            cur.execute(
                "INSERT INTO cashbook (type, amount, description) VALUES ('out', ?, ?)",
                (total, f"İade #{sale_id}"),
            )
            # Link this return with original sale
            self._ensure_returns_table(cur)
            try:
                orig_sid = int((self.sale_id_var.get() or "").strip())
            except Exception:
                orig_sid = None
            if orig_sid:
                cur.execute("INSERT INTO returns (original_sale_id, return_sale_id) VALUES (?, ?)", (orig_sid, sale_id))
            conn.commit()
        except Exception as e:
            conn.rollback()
            self.status_var.set(f"İade tamamlanamadı: {e}")
            return
        finally:
            conn.close()
        self.clear_cart()
        diff = paid - total
        self.entry_paid.delete(0, tk.END)
        self.status_var.set(f"İade tamamlandı. Verilen: {paid:.2f}, Fark: {diff:.2f}")
        self._update_change()

    def _parse_money(self, s: str) -> float:
        try:
            s = (s or "").strip().replace(",", ".")
            return float(s) if s else 0.0
        except Exception:
            return float("nan")

    def _update_change(self, _e=None) -> None:
        try:
            total = float(self.total_var.get())
        except Exception:
            total = 0.0
        paid = self._parse_money(self.entry_paid.get() if hasattr(self, 'entry_paid') else "0")
        if paid != paid:  # NaN
            self.change_var.set("0.00")
            return
        change = paid - total
        if change < 0:
            change = 0.0
        self.change_var.set(f"{change:.2f}")

    def clear_cart(self) -> None:
        for iid in self.cart.get_children():
            self.cart.delete(iid)
        self._recalc_total()
        self.status_var.set("")

    def add_to_cart(self) -> None:
        query = self.entry_scan.get().strip()
        qty = self._parse_qty(self.entry_qty.get().strip() or "1")
        if qty != qty or qty <= 0:
            self.status_var.set("Geçersiz miktar. Pozitif bir miktar girin.")
            return
        prod = self._find_product(query)
        if not prod:
            self.status_var.set("Ürün bulunamadı.")
            return
        pid, name, barcode, price, stock, unit = prod
        if stock is None:
            stock = 0.0
        if qty > float(stock):
            self.status_var.set(f"Yetersiz stok. Stokta {stock} {unit} var.")
            return
        # Merge with existing line if same product
        for iid in self.cart.get_children():
            vals = self.cart.item(iid, "values")
            if int(vals[0]) == int(pid):
                cur_qty = float(vals[4])
                new_qty = cur_qty + qty
                if new_qty > float(stock):
                    self.status_var.set(f"Yetersiz stok. Stokta {stock} {unit} var.")
                    return
                line_total = float(price) * new_qty
                self.cart.item(iid, values=(pid, name, barcode or "", f"{float(price):.2f}", f"{new_qty:g}", f"{line_total:.2f}"))
                break
        else:
            line_total = float(price) * qty
            self.cart.insert("", "end", values=(pid, name, barcode or "", f"{float(price):.2f}", f"{qty:g}", f"{line_total:.2f}"))
        self.entry_scan.delete(0, tk.END)
        self.entry_qty.delete(0, tk.END)
        self.entry_qty.insert(0, "1")
        self.entry_scan.focus_set()
        self._recalc_total()
        self.status_var.set("")

    def complete_sale(self) -> None:
        items = [self.cart.item(iid, "values") for iid in self.cart.get_children()]
        if not items:
            self.status_var.set("Sepet boş.")
            return
        total = float(self.total_var.get())
        paid = self._parse_money(self.entry_paid.get())
        if paid != paid:
            self.status_var.set("Geçersiz ödenen tutar.")
            return
        if paid < total:
            self.status_var.set("Ödenen tutar yetersiz.")
            return
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        try:
            # Create sale
            date_str = (self.entry_date.get().strip() if hasattr(self, 'entry_date') else "") or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cur.execute("INSERT INTO sales (date, total) VALUES (?, ?)", (date_str, total))
            sale_id = cur.lastrowid
            # Insert items and update stock
            for pid, _name, _barcode, price, qty, _line_total in items:
                cur.execute(
                    "INSERT INTO sale_items (sale_id, product_id, quantity, price) VALUES (?, ?, ?, ?)",
                    (sale_id, int(pid), float(qty), float(price)),
                )
                cur.execute("UPDATE products SET stock = stock - ? WHERE id = ?", (float(qty), int(pid)))
            # Add to ledger as income
            cur.execute(
                "INSERT INTO ledger (type, amount, description) VALUES ('gelir', ?, ?)",
                (total, f"Satış #{sale_id}"),
            )
            # Add to cashbook as cash-in
            cur.execute(
                "INSERT INTO cashbook (type, amount, description) VALUES ('in', ?, ?)",
                (total, f"Satış #{sale_id}"),
            )
            conn.commit()
        except Exception as e:
            conn.rollback()
            self.status_var.set(f"Satış tamamlanamadı: {e}")
            return
        finally:
            conn.close()
        self.clear_cart()
        change = paid - total
        self.entry_paid.delete(0, tk.END)
        self.status_var.set(f"Satış tamamlandı. Ödenen: {paid:.2f}, Paraüstü: {change:.2f}")
        self._update_change()
