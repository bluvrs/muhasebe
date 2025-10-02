import sqlite3
import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
from ui import make_back_arrow

DB_NAME = "coop.db"


class MembersFrame(tk.Frame):
    def __init__(self, parent: tk.Misc, controller) -> None:
        super().__init__(parent)
        self.controller = controller

        header = tk.Frame(self)
        header.pack(fill='x')
        back = make_back_arrow(header, self.go_back)
        back.pack(side='left', padx=(10,6), pady=(10,6))
        tk.Label(header, text="Uye Yonetimi", font='TkHeadingFont').pack(side='left', pady=(16,6))

        # Users list
        columns = ("id", "username", "role")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=10)
        self.tree.heading("id", text="ID")
        self.tree.heading("username", text="Kullanici")
        self.tree.heading("role", text="Rol")
        self.tree.column("id", width=40, anchor="center")
        self.tree.column("username", width=200)
        self.tree.column("role", width=120, anchor="center")
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        self.tree.pack(fill="x", padx=20)

        # Form
        form = tk.Frame(self)
        form.pack(fill="x", padx=20, pady=10)

        tk.Label(form, text="Kullanici adi").grid(row=0, column=0, sticky="w")
        self.entry_username = tk.Entry(form)
        self.entry_username.grid(row=0, column=1, sticky="ew", padx=(8, 20))

        tk.Label(form, text="Sifre").grid(row=1, column=0, sticky="w")
        self.entry_password = tk.Entry(form, show="*")
        self.entry_password.grid(row=1, column=1, sticky="ew", padx=(8, 20))

        tk.Label(form, text="Rol").grid(row=0, column=2, sticky="w")
        self.role_combo = ttk.Combobox(form, values=["admin", "kasiyer", "muhasebe", "yonetici", "uye"], state="readonly")
        self.role_combo.grid(row=0, column=3, sticky="w")
        # When role changes from the combo, preselect permissions for that role
        try:
            self.role_combo.bind('<<ComboboxSelected>>', lambda _e: self._apply_role_defaults())
        except Exception:
            pass

        form.columnconfigure(1, weight=1)

        # Buttons
        btns = tk.Frame(self)
        btns.pack(fill="x", padx=20, pady=(0, 10))
        self.btn_add = ttk.Button(btns, text="Ekle", command=self.add_user)
        self.btn_add.pack(side="left")
        self.btn_update = ttk.Button(btns, text="Guncelle", command=self.update_user)
        self.btn_update.pack(side="left", padx=8)
        self.btn_delete = ttk.Button(btns, text="Sil", command=self.delete_user)
        self.btn_delete.pack(side="left")
        self.btn_reset_pwd = ttk.Button(btns, text="Sifreyi Sifirla", command=self.reset_password)
        self.btn_reset_pwd.pack(side="left", padx=8)

        # Permissions section
        perm_box = tk.LabelFrame(self, text="Yetkiler (menüler)")
        perm_box.pack(fill='x', padx=20, pady=(0, 10))
        self._perm_vars = {}
        self._perm_checks = []
        keys = [
            ('members', 'Üye yönetimi'),
            ('products', 'Ürün yönetimi'),
            ('sale', 'Yeni satış'),
            ('return', 'İade işlemi'),
            ('ledger', 'Gelir/Gider kaydı'),
            ('investors', 'Yatırımcılar'),
            ('reports', 'Raporlar'),
            ('settings', 'Ayarlar'),
        ]
        row = 0
        col = 0
        for k, label in keys:
            var = tk.BooleanVar(value=True)
            cb = tk.Checkbutton(perm_box, text=label, variable=var)
            cb.grid(row=row, column=col, sticky='w', padx=8, pady=4)
            self._perm_vars[k] = var
            self._perm_checks.append(cb)
            col += 1
            if col >= 4:
                col = 0
                row += 1
        self.btn_save_perms = ttk.Button(perm_box, text="Yetkileri Kaydet", command=self.save_permissions)
        self.btn_save_perms.grid(row=row+1, column=0, sticky='w', padx=8, pady=(6, 4))
        # Start disabled until a user is selected
        try:
            self._set_perm_controls_enabled(False)
        except Exception:
            pass

        self.refresh_users()

    def refresh_style(self) -> None:
        theme = getattr(self.controller, "saved_theme", "light")
        style = ttk.Style()
        if theme == "dark":
            style.configure("Custom.TButton", background="white", foreground="black")
            style.map("Custom.TButton",
                      background=[('active', 'white')],
                      foreground=[('active', 'black')])
            style.configure("Treeview",
                            background="#2a2f33",
                            foreground="white",
                            fieldbackground="#2a2f33")
            style.map("Treeview",
                      background=[('selected', '#1e2023')],
                      foreground=[('selected', 'white')])
            style.configure("TNotebook.Tab",
                            background="#2a2f33",
                            foreground="white")
            style.map("TNotebook.Tab",
                      background=[('selected', '#1e2023')],
                      foreground=[('selected', 'white')])
        else:
            style.configure("Custom.TButton", background="#1e2023", foreground="white")
            style.map("Custom.TButton",
                      background=[('active', '#2a2f33')],
                      foreground=[('active', 'white')])
            style.configure("Treeview",
                            background="white",
                            foreground="black",
                            fieldbackground="white")
            style.map("Treeview",
                      background=[('selected', '#1e2023')],
                      foreground=[('selected', 'white')])
            style.configure("TNotebook.Tab",
                            background="white",
                            foreground="black")
            style.map("TNotebook.Tab",
                      background=[('selected', '#1e2023')],
                      foreground=[('selected', 'white')])

        for btn in [self.btn_add, self.btn_update, self.btn_delete, self.btn_reset_pwd]:
            btn.configure(style="Custom.TButton")

    def on_show(self, **kwargs) -> None:
        self.controller.title("Kooperatif - Uye Yonetimi")
        self.refresh_users()
        self.refresh_style()
        # Ensure controls are disabled when nothing is selected
        try:
            if not self.tree.selection():
                self._set_perm_controls_enabled(False)
        except Exception:
            pass

    def refresh_users(self) -> None:
        for row in self.tree.get_children():
            self.tree.delete(row)
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("SELECT id, username, role FROM users ORDER BY id")
        for uid, uname, role in cur.fetchall():
            self.tree.insert("", "end", values=(uid, uname, role))
        conn.close()

    def get_selected_id(self):
        sel = self.tree.selection()
        if not sel:
            return None
        vals = self.tree.item(sel[0], "values")
        return int(vals[0])

    def on_select(self, _event=None) -> None:
        sel = self.tree.selection()
        if not sel:
            try:
                self._set_perm_controls_enabled(False)
            except Exception:
                pass
            return
        _id, uname, role = self.tree.item(sel[0], "values")
        self.entry_username.delete(0, tk.END)
        self.entry_username.insert(0, uname)
        self.entry_password.delete(0, tk.END)
        self.role_combo.set(role)
        # Load saved permissions; if none exist, apply role-based defaults
        self.load_permissions(uname, role)
        # Enable/disable permission controls based on admin role
        self._set_perm_controls_enabled(False if str(role).lower() == 'admin' else True)

    def go_back(self) -> None:
        user = getattr(self.controller, "active_user", None)
        if user and "username" in user and "role" in user:
            self.controller.show_role_screen(user["role"], user["username"])
        else:
            # If no active user (edge case), return to login via logout
            self.controller.logout()

    def add_user(self) -> None:
        uname = self.entry_username.get().strip()
        pwd = self.entry_password.get().strip()
        role = self.role_combo.get().strip()
        if not uname or not pwd or not role:
            messagebox.showwarning("Eksik bilgi", "Kullanici, sifre ve rol gerekli.")
            return
        try:
            conn = sqlite3.connect(DB_NAME)
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                (uname, pwd, role),
            )
            conn.commit()
            conn.close()
            self.refresh_users()
            self.entry_password.delete(0, tk.END)
            # Initialize default allow-all permissions for this user
            try:
                self.load_permissions(uname, self.role_combo.get().strip() or None)
                self._set_perm_controls_enabled(False if str(self.role_combo.get()).lower() == 'admin' else True)
            except Exception:
                pass
        except sqlite3.IntegrityError:
            messagebox.showerror("Hata", "Bu kullanici adi zaten var.")

    def update_user(self) -> None:
        uid = self.get_selected_id()
        if uid is None:
            messagebox.showinfo("Secim yok", "Guncellenecek uyeyi secin.")
            return
        uname = self.entry_username.get().strip()
        pwd = self.entry_password.get().strip()
        role = self.role_combo.get().strip()
        if not uname or not role:
            messagebox.showwarning("Eksik bilgi", "Kullanici ve rol gerekli.")
            return
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        try:
            if pwd:
                cur.execute(
                    "UPDATE users SET username = ?, password = ?, role = ? WHERE id = ?",
                    (uname, pwd, role, uid),
                )
            else:
                cur.execute(
                    "UPDATE users SET username = ?, role = ? WHERE id = ?",
                    (uname, role, uid),
                )
            conn.commit()
        except sqlite3.IntegrityError:
            messagebox.showerror("Hata", "Bu kullanici adi zaten var.")
        finally:
            conn.close()
            self.refresh_users()
            self.entry_password.delete(0, tk.END)
            try:
                self.load_permissions(uname, role)
                self._set_perm_controls_enabled(False if str(role).lower() == 'admin' else True)
            except Exception:
                pass

    def delete_user(self) -> None:
        uid = self.get_selected_id()
        if uid is None:
            messagebox.showinfo("Secim yok", "Silinecek uyeyi secin.")
            return
        # Prevent deleting current logged-in user
        try:
            sel = self.tree.selection()[0]
            _id, uname, _role = self.tree.item(sel, "values")
        except Exception:
            uname = None

        if self.controller.active_user and uname == self.controller.active_user.get("username"):
            messagebox.showwarning("Islem engellendi", "Oturum acik kullaniciyi silemezsiniz.")
            return

        if not messagebox.askyesno("Onay", "Secili uyeyi silmek istiyor musunuz?"):
            return
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("DELETE FROM users WHERE id = ?", (uid,))
        conn.commit()
        conn.close()
        self.refresh_users()
        try:
            self._set_perm_controls_enabled(False)
        except Exception:
            pass

    # --- Permissions helpers ---
    def _default_allowed_by_role(self, role: str):
        role = (role or '').lower()
        if role == 'admin':
            return {k for k in self._perm_vars.keys()}
        if role == 'kasiyer':
            return {'sale', 'return'}
        if role == 'muhasebe':
            return {'ledger', 'reports'}
        if role == 'yonetici':
            return {'members', 'products', 'investors', 'ledger', 'reports', 'settings'}
        if role == 'uye':
            return set()
        return {k for k in self._perm_vars.keys()}

    def load_permissions(self, username: str, role: str | None = None) -> None:
        """Load permission rows for username. If none saved, default by role.
        Uses a presence check so 'hepsi kapalı' durumu da ayırt edilir.
        """
        try:
            conn = sqlite3.connect(DB_NAME)
            cur = conn.cursor()
            cur.execute("CREATE TABLE IF NOT EXISTS user_permissions (username TEXT, menu_key TEXT, allowed INTEGER, PRIMARY KEY(username, menu_key))")
            cur.execute("SELECT 1 FROM user_permissions WHERE username=? LIMIT 1", (username,))
            has_any = bool(cur.fetchone())
            cur.execute("SELECT menu_key FROM user_permissions WHERE username=? AND allowed=1", (username,))
            rows = [r[0] for r in cur.fetchall()]
            conn.close()
        except Exception:
            rows = []
            has_any = False
        if has_any:
            allowed = set(rows)
        else:
            allowed = self._default_allowed_by_role(role or '')
        for key, var in self._perm_vars.items():
            var.set(key in allowed)

    def _apply_role_defaults(self) -> None:
        """When role combo changes, preselect default permissions for that role
        (does not save until the user clicks 'Yetkileri Kaydet')."""
        try:
            role = self.role_combo.get().strip()
            allowed = self._default_allowed_by_role(role)
            for key, var in self._perm_vars.items():
                var.set(key in allowed)
        except Exception:
            pass

    def save_permissions(self) -> None:
        """Save the checked permissions for the currently selected username."""
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Seçim yok", "Önce listeden bir üye seçin.")
            return
        _id, uname, _role = self.tree.item(sel[0], "values")
        if str(_role).lower() == 'admin':
            messagebox.showinfo("Yetkiler", "Admin her zaman tam yetkilidir ve değiştirilemez.")
            return
        try:
            conn = sqlite3.connect(DB_NAME)
            cur = conn.cursor()
            cur.execute("CREATE TABLE IF NOT EXISTS user_permissions (username TEXT, menu_key TEXT, allowed INTEGER, PRIMARY KEY(username, menu_key))")
            # Clear existing
            cur.execute("DELETE FROM user_permissions WHERE username=?", (uname,))
            # Insert a presence marker so 'hepsi kapalı' durumu da kaydedilsin
            cur.execute("INSERT OR REPLACE INTO user_permissions(username, menu_key, allowed) VALUES(?,?,0)", (uname, '__custom__'))
            # Insert allowed ones
            for key, var in self._perm_vars.items():
                if var.get():
                    cur.execute("INSERT OR REPLACE INTO user_permissions(username, menu_key, allowed) VALUES(?,?,1)", (uname, key))
            conn.commit()
            conn.close()
            messagebox.showinfo("Yetkiler", "Yetkiler kaydedildi.")
        except Exception as e:
            messagebox.showerror("Hata", str(e))

    def _set_perm_controls_enabled(self, enabled: bool) -> None:
        """Enable/disable permissions UI controls (admin -> disabled)."""
        st = 'normal' if enabled else 'disabled'
        try:
            for cb in self._perm_checks:
                cb.configure(state=st)
        except Exception:
            pass
        try:
            if hasattr(self, 'btn_save_perms'):
                self.btn_save_perms.configure(state=st)
        except Exception:
            pass

    def reset_password(self) -> None:
        uid = self.get_selected_id()
        if uid is None:
            messagebox.showinfo("Secim yok", "Sifresi sifirlanacak uyeyi secin.")
            return
        new_pwd = self.entry_password.get().strip() or "1234"
        if not messagebox.askyesno("Onay", f"Yeni sifre: '{new_pwd}'. Devam edilsin mi?"):
            return
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("UPDATE users SET password = ? WHERE id = ?", (new_pwd, uid))
        conn.commit()
        conn.close()
        self.entry_password.delete(0, tk.END)
        messagebox.showinfo("Tamam", "Sifre guncellendi.")
