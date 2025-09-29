import sqlite3
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from datetime import date, timedelta, datetime
import tempfile
import webbrowser
import os

DB_NAME = "coop.db"

try:
    from tkcalendar import DateEntry as _DateEntry  # type: ignore
except Exception:
    _DateEntry = None  # type: ignore

# Optional PDF support via reportlab
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    _PDF_AVAILABLE = True
except Exception:
    _PDF_AVAILABLE = False


class ReportsFrame(tk.Frame):
    def __init__(self, parent: tk.Misc, controller) -> None:
        super().__init__(parent)
        self.controller = controller

        header = tk.Frame(self)
        header.pack(fill="x")
        tk.Label(header, text="Raporlar", font=("Arial", 16, "bold")).pack(side="left", pady=(20, 10), padx=20)
        tk.Button(header, text="Geri", command=self.go_back).pack(side="right", padx=20, pady=(20, 10))

        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True)

        # Tabs
        self.daily_tab = tk.Frame(self.nb)
        self.cash_tab = tk.Frame(self.nb)
        self.inventory_tab = tk.Frame(self.nb)
        self.nb.add(self.daily_tab, text="Gunluk Gelir/Satis")
        self.nb.add(self.cash_tab, text="Kasa Defteri")
        self.nb.add(self.inventory_tab, text="Envanter Defteri")

        self._build_daily_tab()
        self._build_cash_tab()
        self._build_inventory_tab()

        # Header actions
        tk.Button(header, text="PDF", command=self._export_pdf).pack(side="right", padx=(0, 8), pady=(20, 10))
        tk.Button(header, text="Yazdir", command=self._print_preview).pack(side="right", padx=(0, 8), pady=(20, 10))

        self.refresh()

    def on_show(self, **kwargs) -> None:
        self.controller.title("Kooperatif - Raporlar")
        self.refresh()

    # Navigation
    def go_back(self) -> None:
        user = getattr(self.controller, "active_user", None)
        if user and "username" in user and "role" in user:
            self.controller.show_role_screen(user["role"], user["username"])
        else:
            self.controller.logout()

    # --- Daily sales tab ---
    def _build_daily_tab(self) -> None:
        bar = tk.Frame(self.daily_tab)
        bar.pack(fill="x", padx=20, pady=(10, 6))
        tk.Button(bar, text="<", width=3, command=lambda: self._change_day(-1)).pack(side="left")
        if _DateEntry is not None:
            self.daily_date = _DateEntry(bar, date_pattern="yyyy-mm-dd")
            try:
                self.daily_date.set_date(date.today())
            except Exception:
                pass
        else:
            self.daily_date = tk.Entry(bar, width=12)
            self.daily_date.insert(0, date.today().isoformat())
        self.daily_date.pack(side="left", padx=(6, 6))
        tk.Button(bar, text=">", width=3, command=lambda: self._change_day(1)).pack(side="left")
        tk.Button(bar, text="Bugun", command=self._set_today).pack(side="left", padx=(6, 12))
        tk.Button(bar, text="Yenile", command=self._refresh_daily).pack(side="left")

        columns = ("id", "time", "total")
        self.sales_tree = ttk.Treeview(self.daily_tab, columns=columns, show="headings", height=12)
        self.sales_tree.heading("id", text="Satis #")
        self.sales_tree.heading("time", text="Saat")
        self.sales_tree.heading("total", text="Tutar")
        self.sales_tree.column("id", width=80, anchor="center")
        self.sales_tree.column("time", width=80, anchor="center")
        self.sales_tree.column("total", width=120, anchor="e")
        self.sales_tree.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        bottom = tk.Frame(self.daily_tab)
        bottom.pack(fill="x", padx=20, pady=(0, 10))
        self.daily_total_var = tk.StringVar(value="0.00")
        tk.Label(bottom, text="Gunluk Toplam:").pack(side="left")
        tk.Label(bottom, textvariable=self.daily_total_var, font=("Arial", 12, "bold")).pack(side="left", padx=(6, 20))

    def _get_selected_day(self) -> str:
        if _DateEntry is not None:
            try:
                d = self.daily_date.get_date()
                return d.isoformat()
            except Exception:
                pass
        return self.daily_date.get().strip()

    def _set_today(self) -> None:
        if _DateEntry is not None:
            try:
                self.daily_date.set_date(date.today())
            except Exception:
                pass
        else:
            self.daily_date.delete(0, tk.END)
            self.daily_date.insert(0, date.today().isoformat())
        self._refresh_daily()

    def _change_day(self, delta: int) -> None:
        try:
            cur = date.fromisoformat(self._get_selected_day())
            newd = cur + timedelta(days=delta)
            if _DateEntry is not None:
                self.daily_date.set_date(newd)
            else:
                self.daily_date.delete(0, tk.END)
                self.daily_date.insert(0, newd.isoformat())
        except Exception:
            # ignore parse errors
            pass
        self._refresh_daily()

    def _refresh_daily(self) -> None:
        for iid in self.sales_tree.get_children():
            self.sales_tree.delete(iid)
        day = self._get_selected_day() or date.today().isoformat()
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("SELECT id, strftime('%H:%M', date), total FROM sales WHERE date(date)=? ORDER BY date, id", (day,))
        rows = cur.fetchall()
        cur.execute("SELECT COALESCE(SUM(total),0) FROM sales WHERE date(date)=?", (day,))
        total = cur.fetchone()[0]
        conn.close()
        for sid, t, tot in rows:
            self.sales_tree.insert("", "end", values=(sid, t, f"{float(tot):.2f}"))
        self.daily_total_var.set(f"{float(total):.2f}")

    # --- Cash/Bank tab ---
    def _build_cash_tab(self) -> None:
        top = tk.Frame(self.cash_tab)
        top.pack(fill="x", padx=20, pady=(10, 6))
        self.cash_total_var = tk.StringVar(value="0.00")
        self.bank_total_var = tk.StringVar(value="0.00")
        tk.Label(top, text="Kasa Toplami:").pack(side="left")
        tk.Label(top, textvariable=self.cash_total_var, font=("Arial", 12, "bold")).pack(side="left", padx=(6, 20))
        tk.Label(top, text="Banka Toplami:").pack(side="left")
        tk.Label(top, textvariable=self.bank_total_var, font=("Arial", 12, "bold")).pack(side="left", padx=(6, 20))

        # Actions
        actions = tk.Frame(self.cash_tab)
        actions.pack(fill="x", padx=20, pady=(0, 10))
        # Cash in/out
        tk.Label(actions, text="Kasa islem tutari").grid(row=0, column=0, sticky="w")
        self.cash_amount = tk.Entry(actions, width=12)
        self.cash_amount.grid(row=0, column=1, sticky="w", padx=(6, 10))
        tk.Label(actions, text="Aciklama").grid(row=0, column=2, sticky="w")
        self.cash_desc = tk.Entry(actions, width=40)
        self.cash_desc.grid(row=0, column=3, sticky="w", padx=(6, 10))
        tk.Button(actions, text="Kasaya Ekle", command=lambda: self._cash_op('in')).grid(row=0, column=4, padx=(6, 0))
        tk.Button(actions, text="Kasadan Cik", command=lambda: self._cash_op('out')).grid(row=0, column=5, padx=(6, 0))

        # Transfer to bank
        tk.Label(actions, text="Bankaya aktar tutari").grid(row=1, column=0, sticky="w")
        self.transfer_amount = tk.Entry(actions, width=12)
        self.transfer_amount.grid(row=1, column=1, sticky="w", padx=(6, 10))
        tk.Label(actions, text="Aciklama").grid(row=1, column=2, sticky="w")
        self.transfer_desc = tk.Entry(actions, width=40)
        self.transfer_desc.grid(row=1, column=3, sticky="w", padx=(6, 10))
        tk.Button(actions, text="Bankaya Aktar", command=self._transfer_to_bank).grid(row=1, column=4, padx=(6, 0))

        actions.columnconfigure(3, weight=1)

        # Lists
        lists = tk.PanedWindow(self.cash_tab, sashrelief='raised')
        lists.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        cash_frame = tk.Frame(lists)
        bank_frame = tk.Frame(lists)
        lists.add(cash_frame)
        lists.add(bank_frame)

        tk.Label(cash_frame, text="Kasa Islemleri", font=("Arial", 12, "bold")).pack(anchor="w")
        ccols = ("date", "type", "amount", "description")
        self.cash_tree = ttk.Treeview(cash_frame, columns=ccols, show="headings", height=12)
        for c in ccols:
            self.cash_tree.heading(c, text=c.capitalize())
        self.cash_tree.column("date", width=120)
        self.cash_tree.column("type", width=80, anchor="center")
        self.cash_tree.column("amount", width=120, anchor="e")
        self.cash_tree.column("description", width=300)
        self.cash_tree.pack(fill="both", expand=True, pady=(4, 0))

        tk.Label(bank_frame, text="Banka Islemleri", font=("Arial", 12, "bold")).pack(anchor="w")
        bcols = ("date", "type", "amount", "description")
        self.bank_tree = ttk.Treeview(bank_frame, columns=bcols, show="headings", height=12)
        for c in bcols:
            self.bank_tree.heading(c, text=c.capitalize())
        self.bank_tree.column("date", width=120)
        self.bank_tree.column("type", width=80, anchor="center")
        self.bank_tree.column("amount", width=120, anchor="e")
        self.bank_tree.column("description", width=300)
        self.bank_tree.pack(fill="both", expand=True, pady=(4, 0))

    def _cash_op(self, typ: str) -> None:
        amt_s = self.cash_amount.get().strip()
        try:
            amt = float(amt_s.replace(',', '.')) if amt_s else float('nan')
        except Exception:
            amt = float('nan')
        if amt != amt or amt <= 0:
            return
        desc = self.cash_desc.get().strip() or None
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("INSERT INTO cashbook (type, amount, description) VALUES (?, ?, ?)", (typ, amt, desc))
        conn.commit()
        conn.close()
        self.cash_amount.delete(0, tk.END)
        self.cash_desc.delete(0, tk.END)
        self._refresh_cash()

    def _transfer_to_bank(self) -> None:
        amt_s = self.transfer_amount.get().strip()
        try:
            amt = float(amt_s.replace(',', '.')) if amt_s else float('nan')
        except Exception:
            amt = float('nan')
        if amt != amt or amt <= 0:
            return
        desc = self.transfer_desc.get().strip() or None
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        # cash out
        cur.execute("INSERT INTO cashbook (type, amount, description) VALUES ('out', ?, ?)", (amt, desc))
        # bank in
        cur.execute("INSERT INTO bankbook (type, amount, description) VALUES ('in', ?, ?)", (amt, desc))
        conn.commit()
        conn.close()
        self.transfer_amount.delete(0, tk.END)
        self.transfer_desc.delete(0, tk.END)
        self._refresh_cash()

    def _refresh_cash(self) -> None:
        # Totals
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("SELECT COALESCE(SUM(CASE WHEN type='in' THEN amount WHEN type='out' THEN -amount ELSE 0 END),0) FROM cashbook")
        cash_total = cur.fetchone()[0]
        cur.execute("SELECT COALESCE(SUM(CASE WHEN type='in' THEN amount WHEN type='out' THEN -amount ELSE 0 END),0) FROM bankbook")
        bank_total = cur.fetchone()[0]
        # Lists
        cur.execute("SELECT date, type, amount, COALESCE(description,'') FROM cashbook ORDER BY date DESC, id DESC LIMIT 200")
        cash_rows = cur.fetchall()
        cur.execute("SELECT date, type, amount, COALESCE(description,'') FROM bankbook ORDER BY date DESC, id DESC LIMIT 200")
        bank_rows = cur.fetchall()
        conn.close()
        self.cash_total_var.set(f"{float(cash_total):.2f}")
        self.bank_total_var.set(f"{float(bank_total):.2f}")
        for iid in self.cash_tree.get_children():
            self.cash_tree.delete(iid)
        for d, t, a, desc in cash_rows:
            self.cash_tree.insert("", "end", values=(d, t, f"{float(a):.2f}", desc))
        for iid in self.bank_tree.get_children():
            self.bank_tree.delete(iid)
        for d, t, a, desc in bank_rows:
            self.bank_tree.insert("", "end", values=(d, t, f"{float(a):.2f}", desc))

    # --- Inventory tab ---
    def _build_inventory_tab(self) -> None:
        columns = ("name", "barcode", "stock", "unit", "price", "cost", "value_retail", "value_cost")
        self.inv_tree = ttk.Treeview(self.inventory_tab, columns=columns, show="headings", height=16)
        headers = {
            "name": "Urun",
            "barcode": "Barkod",
            "stock": "Stok",
            "unit": "Birim",
            "price": "Fiyat",
            "cost": "Maliyet",
            "value_retail": "Deger (Satis)",
            "value_cost": "Deger (Maliyet)",
        }
        widths = {
            "name": 220,
            "barcode": 140,
            "stock": 80,
            "unit": 80,
            "price": 100,
            "cost": 100,
            "value_retail": 130,
            "value_cost": 130,
        }
        for c in columns:
            self.inv_tree.heading(c, text=headers[c])
            anchor = 'e' if c in ("stock", "price", "cost", "value_retail", "value_cost") else 'w'
            self.inv_tree.column(c, width=widths[c], anchor=anchor)
        self.inv_tree.pack(fill="both", expand=True, padx=20, pady=10)

    # --- Top-level refresh ---
    def refresh(self) -> None:
        # Ensure tables exist
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, barcode TEXT UNIQUE, price REAL NOT NULL DEFAULT 0, cost REAL NOT NULL DEFAULT 0, stock REAL NOT NULL DEFAULT 0, unit TEXT NOT NULL DEFAULT 'adet')")
        cur.execute("CREATE TABLE IF NOT EXISTS sales (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT NOT NULL DEFAULT (datetime('now')), total REAL NOT NULL)")
        cur.execute("CREATE TABLE IF NOT EXISTS cashbook (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT NOT NULL DEFAULT (datetime('now')), type TEXT NOT NULL CHECK(type IN ('in','out')), amount REAL NOT NULL, description TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS bankbook (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT NOT NULL DEFAULT (datetime('now')), type TEXT NOT NULL CHECK(type IN ('in','out')), amount REAL NOT NULL, description TEXT)")
        conn.close()
        # Refresh each tab
        self._refresh_daily()
        self._refresh_cash()
        self._refresh_inventory()

    def _refresh_inventory(self) -> None:
        for iid in self.inv_tree.get_children():
            self.inv_tree.delete(iid)
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("SELECT name, COALESCE(barcode,''), stock, unit, price, cost FROM products ORDER BY name")
        for name, barcode, stock, unit, price, cost in cur.fetchall():
            value_retail = float(price) * float(stock)
            value_cost = float(cost) * float(stock)
            stock_display = str(int(stock)) if float(stock).is_integer() else str(stock)
            self.inv_tree.insert(
                "",
                "end",
                values=(name, barcode, stock_display, unit, f"{float(price):.2f}", f"{float(cost):.2f}", f"{value_retail:.2f}", f"{value_cost:.2f}"),
            )
        conn.close()

    # --- Print preview ---
    def _print_preview(self) -> None:
        try:
            active = self.nb.index(self.nb.select())
        except Exception:
            active = 0
        if active == 0:
            title = f"Gunluk Satis Raporu - {self._get_selected_day()}"
            html = self._html_daily()
        elif active == 1:
            title = "Kasa/Bank Raporu"
            html = self._html_cash()
        else:
            title = "Envanter Raporu"
            html = self._html_inventory()
        full_html = f"""
<!doctype html>
<html>
<head>
  <meta charset='utf-8'>
  <title>{title}</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 20px; }}
    h1 {{ font-size: 20px; margin-bottom: 10px; }}
    .meta {{ color: #555; margin-bottom: 12px; }}
    table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
    th, td {{ border: 1px solid #ccc; padding: 6px 8px; font-size: 12px; }}
    th {{ background: #f2f2f2; text-align: left; }}
    tfoot td {{ font-weight: bold; }}
    .right {{ text-align: right; }}
    .center {{ text-align: center; }}
  </style>
  <script>
    function onLoad() {{ window.focus(); }}
  </script>
  </head>
  <body onload="onLoad()">
    <h1>{title}</h1>
    <div class="meta">Olusturma: {datetime.now().strftime('%Y-%m-%d %H:%M')}</div>
    {html}
  </body>
</html>
"""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".html", mode="w", encoding="utf-8") as f:
            f.write(full_html)
            path = f.name
        try:
            webbrowser.open(f"file://{path}")
        except Exception:
            try:
                os.startfile(path)  # type: ignore[attr-defined]
            except Exception:
                pass

    def _html_daily(self) -> str:
        rows = [self.sales_tree.item(i, "values") for i in self.sales_tree.get_children()]
        total = self.daily_total_var.get()
        body = "".join(
            f"<tr><td class='center'>{sid}</td><td class='center'>{tm}</td><td class='right'>{float(tot):.2f}</td></tr>"
            for sid, tm, tot in rows
        )
        return (
            "<table><thead><tr><th>Satis #</th><th>Saat</th><th>Tutar</th></tr></thead>"
            f"<tbody>{body}</tbody><tfoot><tr><td colspan='2'>Toplam</td><td class='right'>{total}</td></tr></tfoot></table>"
        )

    def _html_cash(self) -> str:
        cash_rows = [self.cash_tree.item(i, "values") for i in self.cash_tree.get_children()]
        bank_rows = [self.bank_tree.item(i, "values") for i in self.bank_tree.get_children()]
        cash_total = self.cash_total_var.get()
        bank_total = self.bank_total_var.get()
        def rows_to_html(rows):
            return "".join(
                f"<tr><td>{d}</td><td class='center'>{t}</td><td class='right'>{float(a):.2f}</td><td>{desc}</td></tr>"
                for d, t, a, desc in rows
            )
        cash_html = (
            "<h2>Kasa</h2>"
            "<table><thead><tr><th>Tarih</th><th>Tur</th><th>Tutar</th><th>Aciklama</th></tr></thead>"
            f"<tbody>{rows_to_html(cash_rows)}</tbody><tfoot><tr><td colspan='2'>Toplam</td><td class='right'>{cash_total}</td><td></td></tr></tfoot></table>"
        )
        bank_html = (
            "<h2>Banka</h2>"
            "<table><thead><tr><th>Tarih</th><th>Tur</th><th>Tutar</th><th>Aciklama</th></tr></thead>"
            f"<tbody>{rows_to_html(bank_rows)}</tbody><tfoot><tr><td colspan='2'>Toplam</td><td class='right'>{bank_total}</td><td></td></tr></tfoot></table>"
        )
        return cash_html + bank_html

    def _html_inventory(self) -> str:
        rows = [self.inv_tree.item(i, "values") for i in self.inv_tree.get_children()]
        body = "".join(
            "<tr>" + "".join(
                f"<td class='{'right' if idx in (2,4,5,6,7) else ''}'>" + str(val) + "</td>" for idx, val in enumerate(r)
            ) + "</tr>"
            for r in rows
        )
        head = [
            "Urun","Barkod","Stok","Birim","Fiyat","Maliyet","Deger (Satis)","Deger (Maliyet)"
        ]
        thead = "".join(f"<th>{h}</th>" for h in head)
        return f"<table><thead><tr>{thead}</tr></thead><tbody>{body}</tbody></table>"

    # --- PDF export ---
    def _export_pdf(self) -> None:
        if not _PDF_AVAILABLE:
            messagebox.showinfo(
                "PDF desteği yok",
                "PDF oluşturmak için 'reportlab' kurulmalı.\nKurulum: pip install reportlab",
            )
            return
        try:
            active = self.nb.index(self.nb.select())
        except Exception:
            active = 0
        flows = []
        styles = getSampleStyleSheet()
        title_text = ""
        flows.append(Paragraph("Raporlar", styles['Title']))
        flows.append(Paragraph(f"Oluşturma: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
        flows.append(Spacer(1, 6))

        if active == 0:
            title_text = f"Günlük Satış Raporu - {self._get_selected_day()}"
            data = [["Satış #", "Saat", "Tutar"]]
            for sid, tm, tot in [self.sales_tree.item(i, "values") for i in self.sales_tree.get_children()]:
                data.append([str(sid), str(tm), f"{float(tot):.2f}"])
            data.append(["", "Toplam", self.daily_total_var.get()])
            flows.append(Paragraph(title_text, styles['Heading2']))
            t = Table(data, hAlign='LEFT')
            t.setStyle(TableStyle([
                ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
                ('BACKGROUND', (0,0), (-1,0), colors.whitesmoke),
                ('ALIGN', (2,1), (2,-1), 'RIGHT'),
                ('ALIGN', (0,1), (1,-2), 'CENTER'),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
            ]))
            flows.append(t)
        elif active == 1:
            title_text = "Kasa/Bank Raporu"
            flows.append(Paragraph(title_text, styles['Heading2']))
            # Cash
            cdata = [["Tarih", "Tür", "Tutar", "Açıklama"]]
            for d, ttyp, amt, desc in [self.cash_tree.item(i, "values") for i in self.cash_tree.get_children()]:
                cdata.append([str(d), str(ttyp), f"{float(amt):.2f}", str(desc)])
            cdata.append(["", "Toplam", self.cash_total_var.get(), ""])
            ct = Table(cdata, hAlign='LEFT', colWidths=[90, 50, 60, 280])
            ct.setStyle(TableStyle([
                ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
                ('BACKGROUND', (0,0), (-1,0), colors.whitesmoke),
                ('ALIGN', (2,1), (2,-1), 'RIGHT'),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
            ]))
            flows.append(ct)
            flows.append(Spacer(1, 8))
            # Bank
            bdata = [["Tarih", "Tür", "Tutar", "Açıklama"]]
            for d, ttyp, amt, desc in [self.bank_tree.item(i, "values") for i in self.bank_tree.get_children()]:
                bdata.append([str(d), str(ttyp), f"{float(amt):.2f}", str(desc)])
            bdata.append(["", "Toplam", self.bank_total_var.get(), ""])
            bt = Table(bdata, hAlign='LEFT', colWidths=[90, 50, 60, 280])
            bt.setStyle(TableStyle([
                ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
                ('BACKGROUND', (0,0), (-1,0), colors.whitesmoke),
                ('ALIGN', (2,1), (2,-1), 'RIGHT'),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
            ]))
            flows.append(bt)
        else:
            title_text = "Envanter Raporu"
            flows.append(Paragraph(title_text, styles['Heading2']))
            header = ["Ürün", "Barkod", "Stok", "Birim", "Fiyat", "Maliyet", "Değer (Satış)", "Değer (Maliyet)"]
            data = [header]
            for r in [self.inv_tree.item(i, "values") for i in self.inv_tree.get_children()]:
                data.append(list(r))
            col_widths = [140, 90, 40, 40, 55, 55, 90, 100]
            t = Table(data, hAlign='LEFT', colWidths=col_widths)
            t.setStyle(TableStyle([
                ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
                ('BACKGROUND', (0,0), (-1,0), colors.whitesmoke),
                ('ALIGN', (2,1), (2,-1), 'RIGHT'),
                ('ALIGN', (4,1), (7,-1), 'RIGHT'),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ]))
            flows.append(t)

        # Build and open PDF
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as f:
            pdf_path = f.name
        doc = SimpleDocTemplate(pdf_path, pagesize=A4, title=title_text)
        try:
            doc.build(flows)
        except Exception as e:
            messagebox.showerror("PDF hatası", f"PDF olusturulamadi: {e}")
            try:
                os.unlink(pdf_path)
            except Exception:
                pass
            return
        try:
            os.startfile(pdf_path)  # type: ignore[attr-defined]
        except Exception:
            try:
                webbrowser.open(f"file://{pdf_path}")
            except Exception:
                messagebox.showinfo("PDF hazır", f"PDF hazır: {pdf_path}")
