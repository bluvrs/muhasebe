import sqlite3
import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
from ui import make_back_arrow, tinted_bg

DB_NAME = "coop.db"


class ProductsFrame(tk.Frame):
    def __init__(self, parent: tk.Misc, controller) -> None:
        super().__init__(parent)
        self.controller = controller

        header = tk.Frame(self)
        header.pack(fill='x')
        back = make_back_arrow(header, self.go_back)
        back.pack(side='left', padx=(10,6), pady=(10,6))
        tk.Label(header, text="Ürün Yönetimi", font='TkHeadingFont').pack(side='left', pady=(16,6))

        # Search
        search_bar = tk.Frame(self)
        search_bar.pack(fill="x", padx=20)
        tk.Label(search_bar, text="Ara (isim/barkod):").pack(side="left")
        self.entry_search = tk.Entry(search_bar)
        self.entry_search.pack(side="left", fill="x", expand=True, padx=(8, 8))
        # Enter on search field triggers search
        self.entry_search.bind('<Return>', lambda _e: self.search())
        self.btn_search = ttk.Button(search_bar, text="Ara", command=self.search)
        self.btn_search.pack(side="left")
        self.btn_clear = ttk.Button(search_bar, text="Temizle", command=self.clear_search)
        self.btn_clear.pack(side="left", padx=(8, 0))

        # Products list
        columns = ("id", "name", "barcode", "price", "cost", "stock", "unit")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=12)
        self.tree.heading("id", text="ID")
        self.tree.heading("name", text="İsim")
        self.tree.heading("barcode", text="Barkod")
        self.tree.heading("price", text="Fiyat")
        self.tree.heading("cost", text="Maliyet")
        self.tree.heading("stock", text="Stok")
        self.tree.heading("unit", text="Birim")
        self.tree.column("id", width=40, anchor="center")
        self.tree.column("name", width=220)
        self.tree.column("barcode", width=160)
        self.tree.column("price", width=100, anchor="e")
        self.tree.column("cost", width=100, anchor="e")
        self.tree.column("stock", width=80, anchor="e")
        self.tree.column("unit", width=80, anchor="center")
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        self.tree.pack(fill="both", expand=False, padx=20, pady=(6, 0))

        # Form (outlined and compact) – order: Barcode, Name, Cost, Price, Unit, Stock
        form_wrap = tk.Frame(self, bd=0, highlightthickness=1, highlightbackground='#888', bg=tinted_bg(self, 0.07))
        form_wrap.pack(fill="x", padx=20, pady=10)
        form = tk.Frame(form_wrap, bd=0, bg=form_wrap.cget('bg'))
        form.pack(fill='x', padx=10, pady=8)

        # Barkod
        tk.Label(form, text="Barkod", bg=form.cget('bg')).grid(row=0, column=0, sticky="w")
        self.entry_barcode = tk.Entry(form)
        self.entry_barcode.grid(row=0, column=1, sticky="ew", padx=(6, 16))
        # Ürün adı
        tk.Label(form, text="İsim", bg=form.cget('bg')).grid(row=0, column=2, sticky="w")
        self.entry_name = tk.Entry(form)
        self.entry_name.grid(row=0, column=3, sticky="ew", padx=(6, 16))
        # Maliyet
        tk.Label(form, text="Maliyet", bg=form.cget('bg')).grid(row=0, column=4, sticky="w")
        self.entry_cost = tk.Entry(form)
        self.entry_cost.grid(row=0, column=5, sticky="ew", padx=(6, 16))
        # Fiyat
        tk.Label(form, text="Fiyat", bg=form.cget('bg')).grid(row=0, column=6, sticky="w")
        self.entry_price = tk.Entry(form)
        self.entry_price.grid(row=0, column=7, sticky="ew", padx=(6, 16))
        # Birim (alt satır) – combobox daha dar
        tk.Label(form, text="Birim", bg=form.cget('bg')).grid(row=1, column=0, sticky="w", pady=(8,0))
        self.combo_unit = ttk.Combobox(form, values=["adet", "kg", "lt", "paket"], state="readonly", width=8)
        self.combo_unit.set("adet")
        self.combo_unit.grid(row=1, column=1, sticky="w", padx=(6, 16), pady=(8,0))
        # Stok (alt satÄ±r)
        tk.Label(form, text="Stok", bg=form.cget('bg')).grid(row=1, column=2, sticky="w", pady=(8,0))
        self.entry_stock = tk.Entry(form)
        self.entry_stock.grid(row=1, column=3, sticky="ew", pady=(8,0))

        # Responsive columns
        for c in (1, 3, 5, 7):
            form.columnconfigure(c, weight=1)

        # Buttons
        btns = tk.Frame(self)
        btns.pack(fill="x", padx=20, pady=(0, 10))
        self.btn_add = ttk.Button(btns, text="Ekle", command=self.add_product)
        self.btn_add.pack(side="left")
        self.btn_update = ttk.Button(btns, text="Güncelle", command=self.update_product)
        self.btn_update.pack(side="left", padx=8)
        self.btn_delete = ttk.Button(btns, text="Sil", command=self.delete_product)
        self.btn_delete.pack(side="left")

        self.refresh()

    def on_show(self, **kwargs) -> None:
        self.controller.title("Kooperatif - Ürün Yönetimi")
        try:
            # Reset inputs
            for w in (getattr(self, 'entry_search', None), getattr(self, 'entry_name', None), getattr(self, 'entry_barcode', None), getattr(self, 'entry_price', None), getattr(self, 'entry_stock', None), getattr(self, 'entry_cost', None)):
                if w is not None:
                    w.delete(0, tk.END)
            if hasattr(self, 'combo_unit'):
                self.combo_unit.set('adet')
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
        for btn in (
            getattr(self, "btn_search", None),
            getattr(self, "btn_clear", None),
            getattr(self, "btn_add", None),
            getattr(self, "btn_update", None),
            getattr(self, "btn_delete", None),
        ):
            if btn:
                btn.configure(style="Custom.TButton")

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
                "SELECT id, name, barcode, price, cost, stock, unit FROM products WHERE name LIKE ? OR barcode LIKE ? ORDER BY id",
                (kw, kw),
            )
        else:
            cur.execute("SELECT id, name, barcode, price, cost, stock, unit FROM products ORDER BY id")
        for pid, name, barcode, price, cost, stock, unit in cur.fetchall():
            self.tree.insert(
                "",
                "end",
                values=(pid, name, barcode or "", f"{price:.2f}", f"{cost:.2f}", f"{stock:g}", unit),
            )
        conn.close()

    def on_select(self, _event=None) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        _id, name, barcode, price, cost, stock, unit = self.tree.item(sel[0], "values")
        self.entry_name.delete(0, tk.END)
        self.entry_name.insert(0, name)
        self.entry_barcode.delete(0, tk.END)
        self.entry_barcode.insert(0, barcode)
        self.entry_price.delete(0, tk.END)
        self.entry_price.insert(0, price)
        # Cost
        if not hasattr(self, 'entry_cost'):
            self.entry_cost = tk.Entry(self)
        self.entry_cost.delete(0, tk.END)
        self.entry_cost.insert(0, cost)
        self.entry_stock.delete(0, tk.END)
        self.entry_stock.insert(0, stock)
        self.combo_unit.set(unit)

    def add_product(self) -> None:
        name = self.entry_name.get().strip()
        barcode = self.entry_barcode.get().strip() or None
        price = self._parse_float(self.entry_price.get().strip(), 0.0)
        cost = self._parse_float(getattr(self, 'entry_cost', self.entry_price).get().strip(), 0.0)
        stock = self._parse_float(self.entry_stock.get().strip(), 0.0)
        unit = (self.combo_unit.get() or "adet").strip()

        if not name:
            messagebox.showwarning("Eksik bilgi", "İsim gerekli.")
            return
        try:
            conn = sqlite3.connect(DB_NAME)
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO products (name, barcode, price, cost, stock, unit) VALUES (?, ?, ?, ?, ?, ?)",
                (name, barcode, price, cost, stock, unit),
            )
            conn.commit()
        except sqlite3.IntegrityError:
            messagebox.showerror("Hata", "Barkod benzersiz olmalıdır.")
        finally:
            conn.close()
            self.refresh()

    def update_product(self) -> None:
        pid = self._selected_id()
        if pid is None:
            messagebox.showinfo("Seçim yok", "Güncellenecek ürünü seçin.")
            return
        name = self.entry_name.get().strip()
        barcode = self.entry_barcode.get().strip() or None
        price = self._parse_float(self.entry_price.get().strip(), 0.0)
        cost = self._parse_float(getattr(self, 'entry_cost', self.entry_price).get().strip(), 0.0)
        stock = self._parse_float(self.entry_stock.get().strip(), 0.0)
        unit = (self.combo_unit.get() or "adet").strip()
        if not name:
            messagebox.showwarning("Eksik bilgi", "Ä°sim gerekli.")
            return
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        try:
            cur.execute(
                "UPDATE products SET name = ?, barcode = ?, price = ?, cost = ?, stock = ?, unit = ? WHERE id = ?",
                (name, barcode, price, cost, stock, unit, pid),
            )
            conn.commit()
        except sqlite3.IntegrityError:
            messagebox.showerror("Hata", "Barkod benzersiz olmalÄ±dÄ±r.")
        finally:
            conn.close()
            self.refresh()

    def delete_product(self) -> None:
        pid = self._selected_id()
        if pid is None:
            messagebox.showinfo("SeÃ§im yok", "Silinecek Ã¼rÃ¼nÃ¼ seÃ§in.")
            return
        if not messagebox.askyesno("Onay", "SeÃ§ili Ã¼rÃ¼nÃ¼ silmek istiyor musunuz?"):
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

# --- Runtime enhancements: clear inputs after add, scroll to new row ---
def _pf_clear_product_form(self) -> None:
    try:
        self.entry_name.delete(0, tk.END)
        self.entry_barcode.delete(0, tk.END)
        self.entry_price.delete(0, tk.END)
        getattr(self, 'entry_cost', self.entry_price).delete(0, tk.END)
        self.entry_stock.delete(0, tk.END)
        self.combo_unit.set("adet")
        try:
            self.entry_barcode.focus_set()
        except Exception:
            pass
    except Exception:
        pass

def _pf_add_product(self) -> None:
    name = self.entry_name.get().strip()
    barcode = self.entry_barcode.get().strip() or None
    price = self._parse_float(self.entry_price.get().strip(), 0.0)
    cost = self._parse_float(getattr(self, 'entry_cost', self.entry_price).get().strip(), 0.0)
    stock = self._parse_float(self.entry_stock.get().strip(), 0.0)
    unit = (self.combo_unit.get() or "adet").strip()

    if not name:
        messagebox.showwarning("Eksik bilgi", "İsim gerekli.")
        return
    ins_id = None
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO products (name, barcode, price, cost, stock, unit) VALUES (?, ?, ?, ?, ?, ?)",
            (name, barcode, price, cost, stock, unit),
        )
        conn.commit()
        try:
            ins_id = cur.lastrowid
        except Exception:
            ins_id = None
    except sqlite3.IntegrityError:
        messagebox.showerror("Hata", "Barkod benzersiz olmalıdır.")
        return
    except Exception as e:
        messagebox.showerror("Hata", str(e))
        return
    finally:
        try:
            if conn:
                conn.close()
        except Exception:
            pass

    # Clear form and refresh list
    try:
        _pf_clear_product_form(self)
    except Exception:
        pass
    self.refresh()

    # Select and scroll to the newly added product
    try:
        if ins_id:
            target = None
            for iid in self.tree.get_children():
                vals = self.tree.item(iid, "values")
                if str(vals[0]) == str(ins_id):
                    target = iid
                    break
            if target is None:
                kids = self.tree.get_children()
                target = kids[-1] if kids else None
            if target:
                # Only scroll into view; do not select to avoid refilling inputs
                self.tree.see(target)
    except Exception:
        pass

try:
    ProductsFrame._clear_product_form = _pf_clear_product_form  # type: ignore[attr-defined]
    ProductsFrame.add_product = _pf_add_product  # type: ignore[attr-defined]
except Exception:
    pass

