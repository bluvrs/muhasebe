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
            return
        _id, uname, role = self.tree.item(sel[0], "values")
        self.entry_username.delete(0, tk.END)
        self.entry_username.insert(0, uname)
        self.entry_password.delete(0, tk.END)
        self.role_combo.set(role)

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

