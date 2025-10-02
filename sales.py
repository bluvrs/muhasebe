import sqlite3
import tkinter as tk
import tkinter.font as tkfont
from tkinter import messagebox
from tkinter import ttk
from datetime import datetime, date
import time
try:
    from tkcalendar import DateEntry as _DateEntry  # type: ignore
except Exception:
    _DateEntry = None  # type: ignore
from ui import make_back_arrow, tinted_bg

DB_NAME = "coop.db"


class SalesFrame(tk.Frame):
    def __init__(self, parent: tk.Misc, controller) -> None:
        super().__init__(parent)
        self.controller = controller
        # Opt-out from global margin walkers to prevent unintended vertical
        # growth after theme/font changes. This frame manages its own spacing.
        try:
            self._preserve_theme = True
        except Exception:
            pass

        # Font setup for small controls
        base_font = tkfont.nametofont("TkDefaultFont")
        small_size = int(base_font.actual("size") * 0.8)
        small_font = (base_font.actual("family"), small_size)

        # Header with back arrow
        header = tk.Frame(self)
        header.pack(fill='x')
        back = make_back_arrow(header, self.go_back)
        back.pack(side='left', padx=(10,6), pady=(10,6))
        tk.Label(header, text="Yeni Satış", font='TkHeadingFont').pack(side='left', pady=(16,6))
        self.header = header

        # Scan/Search bar
        sb = tk.Frame(self)
        sb.pack(fill="x", padx=20)
        self.sb = sb
        tk.Label(sb, text="Barkod/İsim:").pack(side="left")
        self.entry_scan = tk.Entry(sb)
        self.entry_scan.pack(side="left", fill="x", expand=True, padx=(6, 6))
        tk.Label(sb, text="Adet/Miktar:").pack(side="left")
        # Numeric up-down for quantity
        # Use ttk.Spinbox to avoid odd first-click reversal seen with tk.Spinbox
        # when combined with key validation on some Tk builds.
        self.entry_qty = ttk.Spinbox(sb, from_=1, to=1000000, width=6, increment=1)
        self.entry_qty.delete(0, tk.END)
        self.entry_qty.insert(0, "1")
        self.entry_qty.pack(side="left", padx=(6, 6))
        # On focus out, clamp to minimum 1 and coerce non-digits
        self.entry_qty.bind('<FocusOut>', lambda _e: self._qty_clamp(self.entry_qty))
        ttk.Button(sb, text="Ekle", command=self.add_to_cart).pack(side="left")
        ttk.Button(sb, text="Sepeti Temizle", command=self.clear_cart).pack(side="left", padx=(8, 0))

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

        # Cart tools: quick quantity adjust and remove selected line
        tools = tk.Frame(self)
        tools.pack(fill='x', padx=20, pady=(0, 6))
        self.tools = tools
        ttk.Button(tools, text="− Azalt (−)", command=lambda: self._adjust_selected_qty(-1)).pack(side='left')
        ttk.Button(tools, text="+ Artır (+)", command=lambda: self._adjust_selected_qty(+1)).pack(side='left', padx=(6, 0))
        ttk.Button(tools, text="Satırı Sil (Del)", command=self._remove_selected).pack(side='left', padx=(12, 0))
        # Keyboard shortcuts on cart
        self.cart.bind('<Delete>', lambda _e: (self._remove_selected(), 'break'))
        self.cart.bind('<minus>', lambda _e: (self._adjust_selected_qty(-1), 'break'))
        self.cart.bind('<KP_Subtract>', lambda _e: (self._adjust_selected_qty(-1), 'break'))
        self.cart.bind('<plus>', lambda _e: (self._adjust_selected_qty(+1), 'break'))
        self.cart.bind('<KP_Add>', lambda _e: (self._adjust_selected_qty(+1), 'break'))

        # Totals + actions
        bottom = tk.Frame(self)
        bottom.pack(side='bottom', fill="x", padx=20, pady=(0, 10))
        self.bottom = bottom
        # Left group: date + toplam
        left_box = tk.Frame(bottom)
        left_box.pack(side='left')
        # Add date_outline frame
        date_outline = tk.Frame(left_box, bd=1, relief="solid", padx=4, pady=4)
        date_outline.pack(side="left", padx=(6, 20), pady=8)  # Extra padding here
        date_frame = tk.Frame(date_outline)
        date_frame.pack()
        tk.Label(date_frame, text="Tarih:", font=small_font).pack(anchor="center", pady=2)
        if _DateEntry is not None:
            self.entry_date = _DateEntry(date_frame, date_pattern="yyyy-mm-dd", state="readonly", font=small_font)
            try:
                self.entry_date.set_date(date.today())
            except Exception:
                pass
        else:
            self.entry_date = tk.Entry(date_frame, width=20, font=small_font)
        self.entry_date.pack(anchor="center", pady=2)
        ttk.Button(date_frame, text="Şimdi", command=self._set_now, style="TButton").pack(anchor="center", pady=2)
        # Apply small font to the "Şimdi" button
        # Find the button widget and set its font (ttk Button, so we need a style)
        # We'll create a style for small font button
        style = ttk.Style()
        style.configure("Small.TButton", font=small_font)
        # Reconfigure the button to use the style
        for w in date_frame.winfo_children():
            if isinstance(w, ttk.Button):
                w.configure(style="Small.TButton")
        # Continue with totals to the right of date_frame
        self.total_var = tk.StringVar(value="0.00")
        # New frame for total labels
        total_frame = tk.Frame(left_box)
        total_frame.pack(side="left", anchor="center")
        tk.Label(total_frame, text="Genel Toplam:").pack(side="left", anchor="center")
        tk.Label(total_frame, textvariable=self.total_var, font='TkHeadingFont').pack(side="left", padx=(6, 20), anchor="center")

        # Right group: button + payment (outlined)
        right_box = tk.Frame(bottom)
        right_box.pack(side='right')
        # Compact outlined box (square corners for stability)
        pay_box = tk.Frame(right_box, bd=0, highlightthickness=1, highlightbackground='#888', bg=tinted_bg(self, 0.07))
        pay_box.pack(side='right')
        # Payment + action button inside outline
        tk.Label(pay_box, text="Ödenen:", bg=pay_box.cget('bg')).pack(side="left", padx=(8, 4), pady=6)
        self.entry_paid = tk.Entry(pay_box, width=10)
        self.entry_paid.pack(side="left", padx=(0, 8), pady=6)
        self._bind_select_all(self.entry_paid)
        tk.Label(pay_box, text="Paraüstü:", bg=pay_box.cget('bg')).pack(side="left", pady=6)
        self.change_var = tk.StringVar(value="0.00")
        tk.Label(pay_box, textvariable=self.change_var, font='TkHeadingFont', bg=pay_box.cget('bg')).pack(side="left", padx=(6, 12), pady=6)
        btn = ttk.Button(pay_box, text="Satışı Tamamla", command=self.complete_sale)
        btn.pack(side='left', padx=(6, 8), pady=6)
        # Enlarge button approximately to 100x50 using internal padding
        btn.pack_configure(ipadx=24, ipady=6)

        # Inline status message (instead of many popups)
        self.status_var = tk.StringVar(value="")
        status = tk.Label(self, textvariable=self.status_var, fg="#444")
        status.pack(fill="x", padx=20, pady=(0, 6))

        # Suggestions (typeahead) as dropdown under the search entry
        self._suggest_results = []  # list of (id, name, barcode, price, stock, unit)
        self._suggest_win = tk.Toplevel(self)
        self._suggest_win.withdraw()
        try:
            self._suggest_win.overrideredirect(True)
        except Exception:
            pass
        try:
            self._suggest_win.transient(self.winfo_toplevel())
        except Exception:
            pass
        # container with listbox + scrollbar
        self._suggest_container = tk.Frame(self._suggest_win)
        self._suggest_container.pack(fill='both', expand=True)
        self.suggest = tk.Listbox(self._suggest_container, height=6, activestyle='dotbox', exportselection=False)
        self.suggest.pack(side='left', fill='both', expand=True)
        self._suggest_scroll = ttk.Scrollbar(self._suggest_container, orient='vertical', command=self.suggest.yview)
        self._suggest_scroll.pack(side='right', fill='y')
        self.suggest.configure(yscrollcommand=self._suggest_scroll.set)
        self._suggest_visible = False
        # Global binds: click outside closes; window move keeps position; periodic guard
        try:
            self._app_root = self.winfo_toplevel()
            self._app_root.bind_all('<Button-1>', self._on_global_click, add=True)
            self._app_root.bind('<Configure>', lambda _e: (self._suggest_visible and self._position_suggest_popup()))
        except Exception:
            self._app_root = None
        self.after(300, self._guard_suggest_visibility)
        # Keep a fast barcode scan buffer
        self._scan_buf = ""
        self._scan_last_ts = 0.0
        self._scan_threshold = 0.08  # seconds between keypresses to count as scanner

        # Bind enter to add item and key events for suggestions
        self.entry_scan.bind("<Return>", lambda _e: self.add_to_cart())
        self.entry_scan.bind("<KeyRelease>", self._on_scan_key)
        # Down arrow focuses the suggestion dropdown
        self.entry_scan.bind("<Down>", self._focus_suggest)
        # Hide dropdown when entry loses focus (unless it moves into the dropdown)
        self.entry_scan.bind("<FocusOut>", self._on_entry_focus_out)
        # Hide when suggestions lose focus to elsewhere
        self.suggest.bind("<FocusOut>", self._on_suggest_focus_out)
        # Also hide when this frame is hidden or destroyed (navigating screens)
        self.bind("<Unmap>", lambda _e: self._hide_suggest())
        self.bind("<Destroy>", lambda _e: self._hide_suggest())
        # Capture keypress to detect fast barcode scans
        self.entry_scan.bind("<KeyPress>", self._scan_keypress, add=True)
        self.suggest.bind("<Return>", self._choose_suggest)
        self.suggest.bind("<Double-1>", self._choose_suggest)
        self.suggest.bind("<ButtonRelease-1>", self._click_suggest)
        self.suggest.bind("<Escape>", lambda _e: self._hide_suggest())
        self.suggest.bind("<Up>", self._suggest_up)
        self.entry_qty.bind("<Return>", lambda _e: self.add_to_cart())
        # Update change dynamically when paid input changes
        self.entry_paid.bind("<KeyRelease>", self._update_change)
        # Track user edits on paid field so auto-fill doesn't override manual input
        self._paid_user_edited = False
        self._last_auto_paid = ''
        self.entry_paid.bind('<Key>', lambda _e: self._mark_paid_edited())

        self._set_now()
        self._recalc_total()

    def on_show(self, **kwargs) -> None:
        self.controller.title("Kooperatif - Yeni Satış")
        try:
            # Reset inputs and lists on entry
            self.entry_scan.delete(0, tk.END)
            self.entry_qty.delete(0, tk.END)
            self.entry_qty.insert(0, '1')
            self.entry_paid.delete(0, tk.END)
            for iid in self.cart.get_children():
                self.cart.delete(iid)
            self._recalc_total()
            self.status_var.set("")
            self._paid_user_edited = False
            self._last_auto_paid = ''
        except Exception:
            pass
        self.entry_scan.focus_set()
        # Stabilize layout after fonts/theme settle on first show
        try:
            self.after(0, self._stabilize_layout)
            self.after(120, self._stabilize_layout)
        except Exception:
            pass

    def _stabilize_layout(self) -> None:
        try:
            # Enforce deterministic paddings for critical rows
            if hasattr(self, 'header'):
                self.header.pack_configure(fill='x')
            if hasattr(self, 'sb'):
                self.sb.pack_configure(fill='x', padx=20, pady=(4, 4))
            # Treeview keeps its own expand area
            try:
                self.cart.pack_configure(padx=20, pady=(8, 8))
            except Exception:
                pass
            if hasattr(self, 'tools'):
                self.tools.pack_configure(fill='x', padx=20, pady=(4, 6))
            if hasattr(self, 'bottom'):
                self.bottom.pack_configure(fill='x', padx=20, pady=(0, 10))
            # Force geometry evaluation twice
            self.update_idletasks()
        except Exception:
            pass

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

    def _qty_clamp(self, widget: tk.Spinbox) -> None:
        try:
            val = widget.get().strip()
            if not val.isdigit() or int(val) <= 0:
                widget.delete(0, tk.END)
                widget.insert(0, '1')
        except Exception:
            try:
                widget.delete(0, tk.END)
                widget.insert(0, '1')
            except Exception:
                pass

    # --- Typeahead suggestions ---
    def _on_scan_key(self, _e=None) -> None:
        q = (self.entry_scan.get() or '').strip()
        if not q:
            self._hide_suggest()
            return
        # query by barcode prefix or name contains
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        like = f"%{q}%"
        cur.execute(
            "SELECT id, name, COALESCE(barcode,''), price, stock, unit FROM products WHERE barcode LIKE ? OR name LIKE ? ORDER BY name LIMIT 10",
            (like, like),
        )
        self._suggest_results = cur.fetchall()
        conn.close()
        if not self._suggest_results:
            self._hide_suggest()
            return
        self.suggest.delete(0, tk.END)
        for pid, name, barcode, price, stock, unit in self._suggest_results:
            left = f"{name}"
            if barcode:
                left += f" ({barcode})"
            right = f" {float(price):.2f}"
            self.suggest.insert(tk.END, left + right)
        # Position and show dropdown under the entry
        try:
            self._suggest_win.update_idletasks()
        except Exception:
            pass
        self._position_suggest_popup()
        if not self._suggest_visible:
            try:
                self._suggest_win.deiconify()
                self._suggest_win.lift()
            except Exception:
                pass
            self._suggest_visible = True

    def _hide_suggest(self) -> None:
        if self._suggest_visible:
            try:
                self._suggest_win.withdraw()
            except Exception:
                pass
            self._suggest_visible = False

    def _focus_suggest(self, _e=None) -> str:
        if self._suggest_visible and self.suggest.size() > 0:
            self.suggest.focus_set()
            self.suggest.selection_clear(0, tk.END)
            self.suggest.selection_set(0)
            self.suggest.activate(0)
            return "break"
        return "break"

    def _on_entry_focus_out(self, _e=None):
        # Delay a tick to allow focus to move into the suggestion popup
        def _later():
            try:
                cur = self.focus_get()
                if cur and (cur == self.suggest or cur.winfo_toplevel() == self._suggest_win):
                    return
            except Exception:
                pass
            self._hide_suggest()
        try:
            self.after(1, _later)
        except Exception:
            _later()

    def _on_suggest_focus_out(self, _e=None):
        try:
            cur = self.focus_get()
            if cur and (cur == self.entry_scan or cur.winfo_toplevel() == self._suggest_win):
                return
        except Exception:
            pass
        self._hide_suggest()

    def _click_suggest(self, _e=None):
        # On single-click, accept the highlighted item
        return self._choose_suggest(_e)

    def _on_global_click(self, e=None):
        try:
            w = getattr(e, 'widget', None)
            # If click is inside the entry or inside the suggestion popup, ignore
            if w is self.entry_scan:
                return
            if w is not None:
                try:
                    if w.winfo_toplevel() == self._suggest_win:
                        return
                except Exception:
                    pass
        except Exception:
            pass
        self._hide_suggest()

    def _guard_suggest_visibility(self):
        try:
            if self._suggest_visible:
                # Hide if screen or entry is not viewable (e.g., navigated away)
                if not self.winfo_viewable() or not self.entry_scan.winfo_viewable():
                    self._hide_suggest()
        except Exception:
            pass
        # keep guarding
        try:
            self.after(300, self._guard_suggest_visibility)
        except Exception:
            pass

    def _position_suggest_popup(self) -> None:
        try:
            # Position the suggestion popup just under the search entry
            ex = self.entry_scan.winfo_rootx()
            ey = self.entry_scan.winfo_rooty()
            ew = self.entry_scan.winfo_width()
            eh = self.entry_scan.winfo_height()
            x = ex
            y = ey + eh + 2  # small gap
            # Compute desired height based on item count (up to 8 rows)
            rows = self.suggest.size()
            rows = 1 if rows <= 0 else rows
            rows = rows if rows <= 8 else 8
            # Row height from bbox of first item; fallback to ~18px
            try:
                lh = self.suggest.bbox(0)[3]
            except Exception:
                lh = 18
            h = rows * lh + 4
            # Minimum width to look nice
            w = max(ew, 240)
            self._suggest_win.geometry(f"{w}x{h}+{x}+{y}")
        except Exception:
            pass

    def _suggest_up(self, _e=None) -> str:
        try:
            idx = self.suggest.curselection()
            if idx and idx[0] == 0:
                self.entry_scan.focus_set()
                return "break"
        except Exception:
            pass
        return None

    def _choose_suggest(self, _e=None) -> str:
        try:
            idx = self.suggest.curselection()
            if not idx:
                return "break"
            sel = self._suggest_results[idx[0]]
        except Exception:
            return "break"
        _pid, _name, barcode, _price, _stock, _unit = sel
        self.entry_scan.delete(0, tk.END)
        self.entry_scan.insert(0, barcode or _name)
        self.entry_scan.focus_set()
        self._hide_suggest()
        return "break"

    def _scan_keypress(self, e) -> None:
        # Build a buffer for very fast key sequences typical of barcode scanners
        ch = e.char or ""
        now = time.time()
        if now - self._scan_last_ts > self._scan_threshold:
            # too slow -> start new buffer (likely human typing)
            self._scan_buf = ""
        self._scan_last_ts = now
        if e.keysym == 'Return':
            if len(self._scan_buf) >= 4:
                # treat as scanner input
                self.entry_scan.delete(0, tk.END)
                self.entry_scan.insert(0, self._scan_buf)
                # Auto-add with qty 1
                self.add_to_cart()
                self._scan_buf = ""
                # Keep focus for next scan
                self.entry_scan.focus_set()
                return "break"
            return None
        # Accept only printable alnum and common barcode chars
        if ch.isprintable() and not ch.isspace():
            self._scan_buf += ch

    def _recalc_total(self) -> None:
        total = 0.0
        for iid in self.cart.get_children():
            vals = self.cart.item(iid, "values")
            total += float(vals[5])
        self.total_var.set(f"{total:.2f}")
        # Auto-fill paid if not edited or empty/previous auto value
        self._sync_paid_with_total(total)
        self._update_change()

    def _get_product_by_id(self, pid: int):
        try:
            conn = sqlite3.connect(DB_NAME)
            cur = conn.cursor()
            cur.execute("SELECT id, name, barcode, price, stock, unit FROM products WHERE id = ?", (int(pid),))
            row = cur.fetchone()
            conn.close()
            return row
        except Exception:
            return None

    def _remove_selected(self) -> None:
        sel = self.cart.selection()
        if not sel:
            self.status_var.set("Önce listeden bir satır seçin.")
            return
        for iid in sel:
            self.cart.delete(iid)
        self._recalc_total()
        self.status_var.set("")

    def _adjust_selected_qty(self, delta: float) -> None:
        sel = self.cart.selection()
        if not sel:
            self.status_var.set("Önce listeden bir satır seçin.")
            return
        iid = sel[0]
        vals = list(self.cart.item(iid, "values"))
        try:
            pid = int(vals[0])
            price = float(vals[3])
            cur_qty = float(vals[4])
        except Exception:
            self.status_var.set("Satır verisi okunamadı.")
            return
        new_qty = cur_qty + float(delta)
        # If new qty <= 0, remove the line
        if new_qty <= 0:
            self.cart.delete(iid)
            self._recalc_total()
            self.status_var.set("")
            return
        prod = self._get_product_by_id(pid)
        if not prod:
            self.status_var.set("Ürün bilgisi bulunamadı.")
            return
        _pid, _name, _barcode, _p, stock, unit = prod
        try:
            max_stock = float(stock or 0)
        except Exception:
            max_stock = 0.0
        if new_qty > max_stock:
            self.status_var.set(f"Yetersiz stok. Stokta {max_stock:g} {unit} var.")
            return
        line_total = price * new_qty
        vals[4] = f"{new_qty:g}"
        vals[5] = f"{line_total:.2f}"
        self.cart.item(iid, values=tuple(vals))
        self._recalc_total()
        self.status_var.set("")

    def _sync_paid_with_total(self, total: float) -> None:
        try:
            val = f"{float(total):.2f}"
            cur = self.entry_paid.get().strip() if hasattr(self, 'entry_paid') else ''
            if (not getattr(self, '_paid_user_edited', False)) or (not cur) or (cur == getattr(self, '_last_auto_paid', '')):
                self.entry_paid.delete(0, tk.END)
                self.entry_paid.insert(0, val)
                self._last_auto_paid = val
                self._paid_user_edited = False
        except Exception:
            pass

    def _mark_paid_edited(self) -> None:
        try:
            self._paid_user_edited = True
        except Exception:
            pass

    def _bind_select_all(self, entry_widget: tk.Entry) -> None:
        try:
            entry_widget.bind('<FocusIn>', lambda e: (entry_widget.select_range(0, 'end'), entry_widget.icursor('end')))
            entry_widget.bind('<Button-1>', lambda e: entry_widget.after(1, lambda: (entry_widget.select_range(0, 'end'), entry_widget.icursor('end'))))
        except Exception:
            pass

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
        tk.Label(header, text="İade İşlemi", font='TkHeadingFont').pack(side='left', pady=(16,6))

        # Keep sale id internally; UI removed for clarity
        self.sale_id_var = tk.StringVar(value="")
        self.sale_info_var = tk.StringVar(value="")

        # Scan/Search bar
        sb = tk.Frame(self)
        sb.pack(fill="x", padx=20)
        tk.Label(sb, text="Barkod/İsim:").pack(side="left")
        self.entry_scan = tk.Entry(sb)
        self.entry_scan.pack(side="left", fill="x", expand=True, padx=(6, 6))
        ttk.Button(sb, text="Satışları Listele", command=self._list_sales_for_product).pack(side="left", padx=(0, 10))
        tk.Label(sb, text="İade Adedi:").pack(side="left")
        vcmd = (self.register(lambda s: s.isdigit() or s==''), '%P')
        # Numeric up-down for quantity (integer only)
        self.entry_qty = tk.Spinbox(sb, from_=1, to=1000000, width=6, validate='key', validatecommand=vcmd)
        self.entry_qty.delete(0, tk.END)
        self.entry_qty.insert(0, "1")
        self.entry_qty.pack(side="left", padx=(6, 6))
        self.entry_qty.bind('<FocusOut>', lambda _e: self._qty_clamp(self.entry_qty))
        ttk.Button(sb, text="Ekle", command=self.add_to_cart).pack(side="left")
        ttk.Button(sb, text="Sepeti Temizle", command=self.clear_cart).pack(side="left", padx=(8, 0))

        # Middle: side-by-side panes (left: Son Satışlar, right: İade Sepeti)
        middle = tk.Frame(self)
        middle.pack(fill='both', expand=True, padx=20, pady=(6, 0))

        # Left pane: Son Satışlar
        left_pane = tk.Frame(middle)
        left_pane.pack(side='left', fill='both', expand=True)
        tk.Label(left_pane, text="Son Satışlar", font='TkHeadingFont').pack(anchor='w')
        self.purchases = ttk.Treeview(left_pane, columns=("sale_id","date","name","qty","returned","remaining","price"), show='headings', height=14)
        for col, lbl, w, anc in (
            ("sale_id","Satış #",80,"center"),
            ("date","Tarih",140,"w"),
            ("name","Ürün",220,"w"),
            ("qty","Adet",70,"e"),
            ("returned","İade",70,"e"),
            ("remaining","Kalan",70,"e"),
            ("price","Fiyat",80,"e"),
        ):
            self.purchases.heading(col, text=lbl)
            self.purchases.column(col, width=w, anchor=anc)
        self.purchases.pack(fill='both', expand=True)
        self.purchases.bind('<Double-1>', self._on_purchase_dblclick)

        # Right pane: İade Sepeti
        right_pane = tk.Frame(middle)
        right_pane.pack(side='left', fill='both', expand=True, padx=(12,0))
        tk.Label(right_pane, text="İade Sepeti", font='TkHeadingFont').pack(anchor='w')
        columns = ("product_id", "name", "barcode", "price", "qty", "total")
        self.cart = ttk.Treeview(right_pane, columns=columns, show="headings", height=14)
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
        self.cart.pack(fill='both', expand=True)

        # Totals + actions (wrapped in a fixed-height bottom container)
        bottom_wrap = tk.Frame(self)
        bottom_wrap.pack(side='bottom', fill='x')
        try:
            bottom_wrap.configure(height=160)
            bottom_wrap.pack_propagate(False)
        except Exception:
            pass
        # Main bottom content (totals + payment)
        bottom = tk.Frame(bottom_wrap)
        bottom.pack(side='top', fill="x", padx=20, pady=(0, 6))
        left_box = tk.Frame(bottom)
        left_box.pack(side='left')
        tk.Label(left_box, text="Tarih:").pack(side="left")
        if _DateEntry is not None:
            self.entry_date = _DateEntry(left_box, date_pattern="yyyy-mm-dd", state="readonly")
            try:
                self.entry_date.set_date(date.today())
            except Exception:
                pass
        else:
            self.entry_date = tk.Entry(left_box, width=20)
        self.entry_date.pack(side="left", padx=(6, 6))
        ttk.Button(left_box, text="Şimdi", command=self._set_now).pack(side="left", padx=(0, 20))
        self.total_var = tk.StringVar(value="0.00")
        tk.Label(left_box, text="İade Tutarı:").pack(side="left")
        tk.Label(left_box, textvariable=self.total_var, font='TkHeadingFont').pack(side="left", padx=(6, 20))

        right_box = tk.Frame(bottom)
        right_box.pack(side='right')
        pay_box = tk.Frame(right_box, bd=0, highlightthickness=1, highlightbackground='#888', bg=tinted_bg(self, 0.07))
        pay_box.pack(side='right')
        tk.Label(pay_box, text="Verilen:", bg=pay_box.cget('bg')).pack(side="left", padx=(8,4), pady=6)
        self.entry_paid = tk.Entry(pay_box, width=10)
        self.entry_paid.pack(side="left", padx=(0,8), pady=6)
        self._bind_select_all(self.entry_paid)
        tk.Label(pay_box, text="Fark:", bg=pay_box.cget('bg')).pack(side="left", pady=6)
        self.change_var = tk.StringVar(value="0.00")
        tk.Label(pay_box, textvariable=self.change_var, font='TkHeadingFont', bg=pay_box.cget('bg')).pack(side="left", padx=(6,12), pady=6)
        btnr = ttk.Button(pay_box, text="İadeyi Tamamla", command=self.complete_return)
        btnr.pack(side='left', padx=(6,8), pady=6)
        btnr.pack_configure(ipadx=24, ipady=6)
        # Rebuild date area to match sales screen (outlined box + small Şimdi button)
        try:
            for w in left_box.winfo_children():
                w.pack_forget()
        except Exception:
            pass
        base_font = tkfont.nametofont("TkDefaultFont")
        small_size = int(base_font.actual("size") * 0.8)
        small_font = (base_font.actual("family"), small_size)
        date_outline = tk.Frame(left_box, bd=1, relief="solid", padx=4, pady=4)
        date_outline.pack(side="left", padx=(6, 20), pady=8)
        date_frame = tk.Frame(date_outline)
        date_frame.pack()
        tk.Label(date_frame, text="Tarih:", font=small_font).pack(anchor="center", pady=2)
        if _DateEntry is not None:
            self.entry_date = _DateEntry(date_frame, date_pattern="yyyy-mm-dd", state="readonly", font=small_font)
            try:
                self.entry_date.set_date(date.today())
            except Exception:
                pass
        else:
            self.entry_date = tk.Entry(date_frame, width=20, font=small_font)
        self.entry_date.pack(anchor="center", pady=2)
        ttk.Button(date_frame, text="Şimdi", command=self._set_now).pack(anchor="center", pady=2)
        # small font style for the button (ttk style)
        try:
            style = ttk.Style()
            style.configure("Small.TButton", font=small_font)
            for _w in date_frame.winfo_children():
                if isinstance(_w, ttk.Button):
                    _w.configure(style="Small.TButton")
        except Exception:
            pass
        total_frame = tk.Frame(left_box)
        total_frame.pack(side="left", anchor="center")
        tk.Label(total_frame, text="İade Tutarı:").pack(side="left", anchor="center")
        tk.Label(total_frame, textvariable=self.total_var, font='TkHeadingFont').pack(side="left", padx=(6, 20), anchor="center")
        # Track user edits on paid field for return flow
        self._paid_user_edited = False
        self._last_auto_paid = ''
        self.entry_paid.bind('<Key>', lambda _e: self._mark_paid_edited())

        # Status label inside bottom wrapper so it never gets pushed off-screen
        self.status_var = tk.StringVar(value="")
        status = tk.Label(bottom_wrap, textvariable=self.status_var, fg="#444")
        status.pack(side='bottom', fill="x", padx=20, pady=(0, 4))

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
        try:
            self.entry_scan.delete(0, tk.END)
            self.entry_qty.delete(0, tk.END)
            self.entry_qty.insert(0, '1')
            self.entry_paid.delete(0, tk.END)
            for iid in self.purchases.get_children():
                self.purchases.delete(iid)
            for iid in self.cart.get_children():
                self.cart.delete(iid)
            self._recalc_total()
            self.status_var.set("")
        except Exception:
            pass
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

    def _mark_paid_edited(self) -> None:
        try:
            self._paid_user_edited = True
        except Exception:
            pass

    def _bind_select_all(self, entry_widget: tk.Entry) -> None:
        try:
            entry_widget.bind('<FocusIn>', lambda e: (entry_widget.select_range(0, 'end'), entry_widget.icursor('end')))
            # After the default click behavior, select all text
            entry_widget.bind('<Button-1>', lambda e: entry_widget.after(1, lambda: (entry_widget.select_range(0, 'end'), entry_widget.icursor('end'))))
        except Exception:
            pass

    def _sync_paid_with_total(self, total: float) -> None:
        try:
            val = f"{float(total):.2f}"
            cur = self.entry_paid.get().strip() if hasattr(self, 'entry_paid') else ''
            if (not getattr(self, '_paid_user_edited', False)) or (not cur) or (cur == getattr(self, '_last_auto_paid', '')):
                self.entry_paid.delete(0, tk.END)
                self.entry_paid.insert(0, val)
                self._last_auto_paid = val
                self._paid_user_edited = False
        except Exception:
            pass

    def _recalc_total(self) -> None:
        total = 0.0
        for iid in self.cart.get_children():
            vals = self.cart.item(iid, "values")
            total += float(vals[5])
        self.total_var.set(f"{total:.2f}")
        # Auto-fill paid if not edited or empty/previous auto value
        self._sync_paid_with_total(total)
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
        pid, prod_name, _barcode, _price, _stock, _unit = prod
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
                self.purchases.insert('', 'end', values=(sid, d, prod_name, f"{float(qty):g}", f"{returned:g}", f"{remaining:g}", f"{float(price):.2f}"))
        conn.close()
        self._active_pid = int(pid)
        self.status_var.set("Satışlar listelendi. Bir satıra çift tıklayın.")

    def _on_purchase_dblclick(self, _e=None):
        sel = self.purchases.selection()
        if not sel:
            return
        vals = self.purchases.item(sel[0], 'values')
        sid = int(vals[0])
        # Load the selected sale to compute remaining quantities
        self.sale_id_var.set(str(sid))
        self._load_sale()
        # Determine active product (from earlier search)
        pid = int(self._active_pid or 0)
        if not pid:
            return
        remaining = float(self._allowed_qty.get(pid, 0.0))
        if remaining <= 0:
            self.status_var.set("Bu üründe iade hakkı kalmamış.")
            return
        # Add N items based on Spinbox (default 1)
        try:
            qty = int((self.entry_qty.get() or '1'))
        except Exception:
            qty = 1
        if qty <= 0:
            qty = 1
        if qty > remaining:
            qty = int(remaining)
        # Fetch product details for display
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("SELECT name, COALESCE(barcode,'') FROM products WHERE id = ?", (pid,))
        row = cur.fetchone()
        conn.close()
        name = row[0] if row else str(pid)
        barcode = row[1] if row else ''
        price = float(self._orig_price.get(pid, 0.0))
        # Merge/insert into return cart
        for iid in self.cart.get_children():
            cv = self.cart.item(iid, 'values')
            if int(cv[0]) == pid:
                new_qty = float(cv[4]) + qty
                if new_qty > remaining:
                    new_qty = remaining
                line_total = float(price) * new_qty
                self.cart.item(iid, values=(pid, name, barcode, f"{price:.2f}", f"{new_qty:g}", f"{line_total:.2f}"))
                break
        else:
            line_total = float(price) * qty
            self.cart.insert('', 'end', values=(pid, name, barcode, f"{price:.2f}", f"{qty:g}", f"{line_total:.2f}"))
        self._recalc_total()
        self.entry_scan.focus_set()
        self.status_var.set(f"Satış #{sid} → sepete eklendi.")

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
