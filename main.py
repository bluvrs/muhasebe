import sqlite3
import tkinter as tk
from tkinter import messagebox
from typing import Dict, List, Optional, Type, Callable
from members import MembersFrame
from typing import Tuple
try:
    from products import ProductsFrame
except Exception:
    ProductsFrame = None  # type: ignore[assignment]
try:
    from reports import ReportsFrame
except Exception:
    ReportsFrame = None  # type: ignore[assignment]
try:
    from ledger import LedgerFrame
except Exception:
    LedgerFrame = None  # type: ignore[assignment]
try:
    from sales import SalesFrame
except Exception:
    SalesFrame = None  # type: ignore[assignment]

DB_NAME = "coop.db"


# --- Database Setup ---
def init_db() -> None:
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            role TEXT
        )
        """
    )
    # Basic products table for inventory
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            barcode TEXT UNIQUE,
            price REAL NOT NULL DEFAULT 0,
            stock REAL NOT NULL DEFAULT 0,
            unit TEXT NOT NULL DEFAULT 'adet'
        )
        """
    )
    # Simple ledger table for income (gelir) and outcome (gider)
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS ledger (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL DEFAULT (date('now')),
            type TEXT NOT NULL CHECK(type IN ('gelir','gider')),
            amount REAL NOT NULL,
            description TEXT
        )
        """
    )
    # Sales header and lines
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL DEFAULT (datetime('now')),
            total REAL NOT NULL
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS sale_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sale_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity REAL NOT NULL,
            price REAL NOT NULL,
            FOREIGN KEY(sale_id) REFERENCES sales(id) ON DELETE CASCADE,
            FOREIGN KEY(product_id) REFERENCES products(id)
        )
        """
    )
    cursor.execute("SELECT 1 FROM users WHERE username = ?", ("admin",))
    if not cursor.fetchone():
        cursor.execute(
            "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
            ("admin", "1234", "admin"),
        )
    conn.commit()
    conn.close()


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Kooperatif Giris")
        self.minsize(800, 600)
        self.frames: Dict[Type[tk.Frame], tk.Frame] = {}
        self.active_user: Optional[Dict[str, str]] = None

        container = tk.Frame(self)
        container.pack(fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)
        self.container = container

        self.role_screens: Dict[str, Type[tk.Frame]] = {
            "admin": AdminFrame,
            "kasiyer": CashierFrame,
            "muhasebe": AccountingFrame,
            "yonetici": ManagerFrame,
            "uye": MemberFrame,
        }

        self.show_frame(LoginFrame)

    def show_frame(self, frame_class: Type[tk.Frame], **kwargs) -> None:
        frame = self.frames.get(frame_class)
        if frame is None:
            frame = frame_class(parent=self.container, controller=self)
            self.frames[frame_class] = frame
            frame.grid(row=0, column=0, sticky="nsew")
        if hasattr(frame, "on_show"):
            frame.on_show(**kwargs)
        frame.tkraise()

    def authenticate(self, username: str, password: str) -> None:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT role FROM users WHERE username = ? AND password = ?",
            (username, password),
        )
        row = cursor.fetchone()
        conn.close()

        if row:
            role = row[0]
            self.show_role_screen(role, username)
        else:
            messagebox.showerror("Login failed", "Invalid username or password")

    def show_role_screen(self, role: str, username: str) -> None:
        frame_class = self.role_screens.get(role)
        if frame_class is None:
            messagebox.showerror("Error", "No screen defined for this role")
            return

        self.active_user = {"username": username, "role": role}
        self.title("Kooperatif - {}".format(role.title()))
        self.show_frame(frame_class, username=username, role=role)

    def logout(self) -> None:
        self.active_user = None
        self.title("Kooperatif Giris")
        self.show_frame(LoginFrame)

    def show_placeholder(self, action_name: str) -> None:
        messagebox.showinfo("Coming soon", "Action '{}' is not implemented yet.".format(action_name))


class LoginFrame(tk.Frame):
    def __init__(self, parent: tk.Misc, controller: App) -> None:
        super().__init__(parent)
        self.controller = controller

        tk.Label(self, text="Kooperatif Giris", font=("Arial", 16, "bold")).pack(pady=20)

        tk.Label(self, text="Kullanici adi").pack(pady=(0, 5))
        self.entry_user = tk.Entry(self)
        self.entry_user.pack(padx=40, fill="x")
        self.entry_user.bind("<Return>", lambda _e: self.do_login())

        tk.Label(self, text="Sifre").pack(pady=(15, 5))
        self.entry_pass = tk.Entry(self, show="*")
        self.entry_pass.pack(padx=40, fill="x")
        self.entry_pass.bind("<Return>", lambda _e: self.do_login())

        tk.Button(self, text="Giris Yap", command=self.do_login).pack(pady=20)

    def _on_return(self, event: tk.Event) -> None:  # type: ignore[name-defined]
        self.do_login()

    def do_login(self) -> None:
        username = self.entry_user.get().strip()
        password = self.entry_pass.get().strip()

        if not username or not password:
            messagebox.showwarning("Eksik bilgi", "Lutfen kullanici adi ve sifre girin.")
            return

        self.controller.authenticate(username, password)

    def on_show(self) -> None:
        self.entry_user.delete(0, tk.END)
        self.entry_pass.delete(0, tk.END)
        self.entry_user.focus_set()


class RoleFrame(tk.Frame):
    def __init__(
        self,
        parent: tk.Misc,
        controller: App,
        title: str,
        actions: Optional[List[str]] = None,
        action_handlers: Optional[Dict[str, Callable[[], None]]] = None,
        description: Optional[str] = None,
    ) -> None:
        super().__init__(parent)
        self.controller = controller
        self.user_label = tk.Label(self, text="")

        tk.Label(self, text=title, font=("Arial", 16, "bold")).pack(pady=(20, 10))
        self.user_label.pack()

        if description:
            tk.Label(self, text=description, wraplength=360, justify="center").pack(pady=20)

        if actions:
            for action in actions:
                handler = None
                if action_handlers:
                    handler = action_handlers.get(action)
                if handler is None:
                    handler = lambda name=action: controller.show_placeholder(name)
                tk.Button(self, text=action, command=handler).pack(fill="x", padx=60, pady=5)

        tk.Button(self, text="Cikis yap", command=self.controller.logout).pack(pady=30)

    def on_show(self, username: str, role: str) -> None:
        self.user_label.config(text="Signed in as {} ({})".format(username, role))


class AdminFrame(RoleFrame):
    def __init__(self, parent: tk.Misc, controller: App) -> None:
        actions = ["Uye yonetimi", "Urun yonetimi", "Gelir/Gider kaydi", "Raporlar"]
        handlers: Dict[str, Callable[[], None]] = {
            "Uye yonetimi": lambda: controller.show_frame(MembersFrame),
        }
        # Add product management if available
        if ProductsFrame is not None:
            handlers["Urun yonetimi"] = lambda: controller.show_frame(ProductsFrame)  # type: ignore[arg-type]
        else:
            handlers["Urun yonetimi"] = lambda: controller.show_placeholder("Urun yonetimi")
        # Ledger (income/outcome)
        if LedgerFrame is not None:
            handlers["Gelir/Gider kaydi"] = lambda: controller.show_frame(LedgerFrame)  # type: ignore[arg-type]
        else:
            handlers["Gelir/Gider kaydi"] = lambda: controller.show_placeholder("Gelir/Gider kaydi")
        # Reports
        if ReportsFrame is not None:
            handlers["Raporlar"] = lambda: controller.show_frame(ReportsFrame)  # type: ignore[arg-type]
        else:
            handlers["Raporlar"] = lambda: controller.show_placeholder("Raporlar")
        super().__init__(parent, controller, "Admin Panel", actions, handlers)


class CashierFrame(RoleFrame):
    def __init__(self, parent: tk.Misc, controller: App) -> None:
        description = "Barkod okutun ve islemleri tamamlayin."
        actions = ["Yeni satis", "Iade islemi"]
        handlers: Dict[str, Callable[[], None]] = {}
        if SalesFrame is not None:
            handlers["Yeni satis"] = lambda: controller.show_frame(SalesFrame)  # type: ignore[arg-type]
        else:
            handlers["Yeni satis"] = lambda: controller.show_placeholder("Yeni satis")
        # Keep returns as placeholder for now
        handlers["Iade islemi"] = lambda: controller.show_placeholder("Iade islemi")
        super().__init__(parent, controller, "Kasiyer Ekrani", actions, handlers, description)


class AccountingFrame(RoleFrame):
    def __init__(self, parent: tk.Misc, controller: App) -> None:
        actions = ["Gelir girisi", "Gider girisi", "Bilanco"]
        super().__init__(parent, controller, "Muhasebe Paneli", actions)


class MemberFrame(RoleFrame):
    def __init__(self, parent: tk.Misc, controller: App) -> None:
        description = "Kardan dusen payinizi ve gecmis islemleri inceleyin."
        actions = ["Pay goruntule", "Ekstre al"]
        super().__init__(parent, controller, "Uye Paneli", actions, None, description)


class ManagerFrame(RoleFrame):
    def __init__(self, parent: tk.Misc, controller: App) -> None:
        actions = ["Urun yonetimi", "Gelir/Gider kaydi", "Raporlar"]
        handlers: Dict[str, Callable[[], None]] = {}
        if ProductsFrame is not None:
            handlers["Urun yonetimi"] = lambda: controller.show_frame(ProductsFrame)  # type: ignore[arg-type]
        else:
            handlers["Urun yonetimi"] = lambda: controller.show_placeholder("Urun yonetimi")
        if LedgerFrame is not None:
            handlers["Gelir/Gider kaydi"] = lambda: controller.show_frame(LedgerFrame)  # type: ignore[arg-type]
        else:
            handlers["Gelir/Gider kaydi"] = lambda: controller.show_placeholder("Gelir/Gider kaydi")
        if ReportsFrame is not None:
            handlers["Raporlar"] = lambda: controller.show_frame(ReportsFrame)  # type: ignore[arg-type]
        else:
            handlers["Raporlar"] = lambda: controller.show_placeholder("Raporlar")
        super().__init__(parent, controller, "Yonetici Paneli", actions, handlers)


if __name__ == "__main__":
    init_db()
    app = App()
    app.mainloop()
