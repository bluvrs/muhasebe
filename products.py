import sqlite3
import tkinter as tk
from tkinter import messagebox
from tkinter import ttk

DB_NAME = "coop.db"


class ProductsFrame(tk.Frame):
    def __init__(self, parent: tk.Misc, controller) -> None:
        super().__init__(parent)
        self.controller = controller

        tk.Label(self, text="Urun Yonetimi", font=("Arial", 16, "bold")).pack(pady=(20, 10))

        # Search
        search_bar = tk.Frame(self)
        search_bar.pack(fill="x", padx=20)
        tk.Label(search_bar, text="Ara (isim/barkod):").pack(side="left")
        self.entry_search = tk.Entry(search_bar)
        self.entry_search.pack(side="left", fill="x", expand=True, padx=(8, 8))
        tk.Button(search_bar, text="Ara", command=self.search).pack(side="left")
        tk.Button(search_bar, text="Temizle", command=self.clear_search).pack(side="left", padx=(8, 0))

        # Products list
        columns = ("id", "name", "barcode", "price", "stock", "unit")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=12)
        self.tree.heading("id", text="ID")
        self.tree.heading("name", text="Isim")
        self.tree.heading("barcode", text="Barkod")
        self.tree.heading("price", text="Fiyat")
        self.tree.heading("stock", text="Stok")
        self.tree.heading("unit", text="Birim")
        self.tree.column("id", width=40, anchor="center")
        self.tree.column("name", width=220)
        self.tree.column("barcode", width=160)
        self.tree.column("price", width=100, anchor="e")
        self.tree.column("stock", width=80, anchor="e")
        self.tree.column("unit", width=80, anchor="center")
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        self.tree.pack(fill="both", expand=False, padx=20, pady=(6, 0))

        # Form
        form = tk.Frame(self)
        form.pack(fill="x", padx=20, pady=10)

        tk.Label(form, text="Isim").grid(row=0, column=0, sticky="w")
        self.entry_name = tk.Entry(form)
        self.entry_name.grid(row=0, column=1, sticky="ew", padx=(8, 20))

        tk.Label(form, text="Barkod").grid(row=1, column=0, sticky="w")
        self.entry_barcode = tk.Entry(form)
        self.entry_barcode.grid(row=1, column=1, sticky="ew", padx=(8, 20))

        tk.Label(form, text="Fiyat").grid(row=0, column=2, sticky="w")
        self.entry_price = tk.Entry(form)
        self.entry_price.grid(row=0, column=3, sticky="ew", padx=(8, 20))

        tk.Label(form, text="Stok").grid(row=1, column=2, sticky="w")
        self.entry_stock = tk.Entry(form)
        self.entry_stock.grid(row=1, column=3, sticky="ew", padx=(8, 20))

        tk.Label(form, text="Birim").grid(row=0, column=4, sticky="w")
        self.combo_unit = ttk.Combobox(form, values=["adet", "kg", "lt", "paket"], state="readonly")
        self.combo_unit.set("adet")
        self.combo_unit.grid(row=0, column=5, sticky="w")

        form.columnconfigure(1, weight=2)
        form.columnconfigure(3, weight=1)

        # Buttons
        btns = tk.Frame(self)
        btns.pack(fill="x", padx=20, pady=(0, 10))
        tk.Button(btns, text="Ekle", command=self.add_product).pack(side="left")
        tk.Button(btns, text="Guncelle", command=self.update_product).pack(side="left", padx=8)
        tk.Button(btns, text="Sil", command=self.delete_product).pack(side="left")
        tk.Button(btns, text="Geri", command=self.go_back).pack(side="right")

        self.refresh()

    def on_show(self, **kwargs) -> None:
        self.controller.title("Kooperatif - Urun Yonetimi")
        self.refresh()

    # --- Helpers ---
    def _parse_float(self, value: str, default: float = 0.0) -> float:
        try:
            value = value.replace(",", ".")
            return float(value)
        except Exception:
            return default

    def _selected_id(self):
        sel = self.tree.selection()
        if not sel:
            return None
        vals = self.tree.item(sel[0], "values")
        return int(vals[0])

    # --- Navigation ---
    def go_back(self) -> None:
        user = getattr(self.controller, "active_user", None)
        if user and "username" in user and "role" in user:
            self.controller.show_role_screen(user["role"], user["username"])
        else:
            self.controller.logout()

    # --- CRUD ---
    def refresh(self, keyword: str = "") -> None:
        for row in self.tree.get_children():
            self.tree.delete(row)
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        if keyword:
            kw = f"%{keyword}%"
            cur.execute(
                "SELECT id, name, barcode, price, stock, unit FROM products WHERE name LIKE ? OR barcode LIKE ? ORDER BY id",
                (kw, kw),
            )
        else:
            cur.execute("SELECT id, name, barcode, price, stock, unit FROM products ORDER BY id")
        for pid, name, barcode, price, stock, unit in cur.fetchall():
            self.tree.insert("", "end", values=(pid, name, barcode or "", f"{price:.2f}", f"{stock:g}", unit))
        conn.close()

    def on_select(self, _event=None) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        _id, name, barcode, price, stock, unit = self.tree.item(sel[0], "values")
        self.entry_name.delete(0, tk.END)
        self.entry_name.insert(0, name)
        self.entry_barcode.delete(0, tk.END)
        self.entry_barcode.insert(0, barcode)
        self.entry_price.delete(0, tk.END)
        self.entry_price.insert(0, price)
        self.entry_stock.delete(0, tk.END)
        self.entry_stock.insert(0, stock)
        self.combo_unit.set(unit)

    def add_product(self) -> None:
        name = self.entry_name.get().strip()
        barcode = self.entry_barcode.get().strip() or None
        price = self._parse_float(self.entry_price.get().strip(), 0.0)
        stock = self._parse_float(self.entry_stock.get().strip(), 0.0)
        unit = (self.combo_unit.get() or "adet").strip()

        if not name:
            messagebox.showwarning("Eksik bilgi", "Isim gerekli.")
            return
        try:
            conn = sqlite3.connect(DB_NAME)
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO products (name, barcode, price, stock, unit) VALUES (?, ?, ?, ?, ?)",
                (name, barcode, price, stock, unit),
            )
            conn.commit()
        except sqlite3.IntegrityError:
            messagebox.showerror("Hata", "Barkod benzersiz olmalidir.")
        finally:
            conn.close()
            self.refresh()

    def update_product(self) -> None:
        pid = self._selected_id()
        if pid is None:
            messagebox.showinfo("Secim yok", "Guncellenecek urunu secin.")
            return
        name = self.entry_name.get().strip()
        barcode = self.entry_barcode.get().strip() or None
        price = self._parse_float(self.entry_price.get().strip(), 0.0)
        stock = self._parse_float(self.entry_stock.get().strip(), 0.0)
        unit = (self.combo_unit.get() or "adet").strip()
        if not name:
            messagebox.showwarning("Eksik bilgi", "Isim gerekli.")
            return
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        try:
            cur.execute(
                "UPDATE products SET name = ?, barcode = ?, price = ?, stock = ?, unit = ? WHERE id = ?",
                (name, barcode, price, stock, unit, pid),
            )
            conn.commit()
        except sqlite3.IntegrityError:
            messagebox.showerror("Hata", "Barkod benzersiz olmalidir.")
        finally:
            conn.close()
            self.refresh()

    def delete_product(self) -> None:
        pid = self._selected_id()
        if pid is None:
            messagebox.showinfo("Secim yok", "Silinecek urunu secin.")
            return
        if not messagebox.askyesno("Onay", "Secili urunu silmek istiyor musunuz?"):
            return
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("DELETE FROM products WHERE id = ?", (pid,))
        conn.commit()
        conn.close()
        self.refresh()

    # --- Search ---
    def search(self) -> None:
        kw = self.entry_search.get().strip()
        self.refresh(kw)

    def clear_search(self) -> None:
        self.entry_search.delete(0, tk.END)
        self.refresh()

