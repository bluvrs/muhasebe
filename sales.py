import sqlite3
import tkinter as tk
from tkinter import messagebox
from tkinter import ttk

DB_NAME = "coop.db"


class SalesFrame(tk.Frame):
    def __init__(self, parent: tk.Misc, controller) -> None:
        super().__init__(parent)
        self.controller = controller

        tk.Label(self, text="Yeni Satis", font=("Arial", 16, "bold")).pack(pady=(20, 10))

        # Scan/Search bar
        sb = tk.Frame(self)
        sb.pack(fill="x", padx=20)
        tk.Label(sb, text="Barkod/Isim:").pack(side="left")
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
        self.total_var = tk.StringVar(value="0.00")
        tk.Label(bottom, text="Genel Toplam:").pack(side="left")
        tk.Label(bottom, textvariable=self.total_var, font=("Arial", 12, "bold")).pack(side="left", padx=(6, 20))
        tk.Button(bottom, text="Satışı Tamamla", command=self.complete_sale).pack(side="right")
        tk.Button(bottom, text="Geri", command=self.go_back).pack(side="right", padx=(8, 8))

        # Bind enter to add item
        self.entry_scan.bind("<Return>", lambda _e: self.add_to_cart())
        self.entry_qty.bind("<Return>", lambda _e: self.add_to_cart())

        self._recalc_total()

    def on_show(self, **kwargs) -> None:
        self.controller.title("Kooperatif - Yeni Satis")
        self.entry_scan.focus_set()

    def go_back(self) -> None:
        user = getattr(self.controller, "active_user", None)
        if user and "username" in user and "role" in user:
            self.controller.show_role_screen(user["role"], user["username"])
        else:
            self.controller.logout()

    # Helpers
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

    def clear_cart(self) -> None:
        for iid in self.cart.get_children():
            self.cart.delete(iid)
        self._recalc_total()

    def add_to_cart(self) -> None:
        query = self.entry_scan.get().strip()
        qty = self._parse_qty(self.entry_qty.get().strip() or "1")
        if qty != qty or qty <= 0:
            messagebox.showwarning("Gecersiz miktar", "Pozitif bir miktar girin.")
            return
        prod = self._find_product(query)
        if not prod:
            messagebox.showwarning("Bulunamadi", "Urun bulunamadi.")
            return
        pid, name, barcode, price, stock, unit = prod
        if stock is None:
            stock = 0.0
        if qty > float(stock):
            messagebox.showwarning("Yetersiz stok", f"Stokta {stock} {unit} var.")
            return
        # Merge with existing line if same product
        for iid in self.cart.get_children():
            vals = self.cart.item(iid, "values")
            if int(vals[0]) == int(pid):
                cur_qty = float(vals[4])
                new_qty = cur_qty + qty
                if new_qty > float(stock):
                    messagebox.showwarning("Yetersiz stok", f"Stokta {stock} {unit} var.")
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

    def complete_sale(self) -> None:
        items = [self.cart.item(iid, "values") for iid in self.cart.get_children()]
        if not items:
            messagebox.showinfo("Bos", "Sepet bos.")
            return
        total = float(self.total_var.get())
        if not messagebox.askyesno("Onay", f"Satis tamamlanacak. Toplam: {total:.2f}. Devam edilsin mi?"):
            return
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        try:
            # Create sale
            cur.execute("INSERT INTO sales (total) VALUES (?)", (total,))
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
                (total, f"Satis #{sale_id}"),
            )
            conn.commit()
        except Exception as e:
            conn.rollback()
            messagebox.showerror("Hata", f"Satis tamamlanamadi: {e}")
            return
        finally:
            conn.close()
        self.clear_cart()
        messagebox.showinfo("Tamam", "Satis tamamlandi.")

