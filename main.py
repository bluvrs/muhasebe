import sqlite3
import tkinter as tk
from tkinter import messagebox, ttk
import tkinter.font as tkfont
from typing import Dict, List, Optional, Type, Callable
from members import MembersFrame
from ui import apply_theme, tinted_bg, smart_tinted_bg, rounded_outline, apply_entry_margins, apply_button_margins, _icon_for_action
import sqlite3 as _sqlite3
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
    from sales import SalesFrame, ReturnFrame
except Exception:
    SalesFrame = None  # type: ignore[assignment]
    ReturnFrame = None  # type: ignore[assignment]
try:
    from investors import InvestorsFrame
except Exception:
    InvestorsFrame = None  # type: ignore[assignment]
try:
    from settings import SettingsFrame
except Exception:
    SettingsFrame = None  # type: ignore[assignment]

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
            cost REAL NOT NULL DEFAULT 0,
            stock REAL NOT NULL DEFAULT 0,
            unit TEXT NOT NULL DEFAULT 'adet'
        )
        """
    )
    # Migration: add cost column if missing (for existing DBs)
    cursor.execute("PRAGMA table_info(products)")
    cols = [r[1] for r in cursor.fetchall()]
    if 'cost' not in cols:
        cursor.execute("ALTER TABLE products ADD COLUMN cost REAL NOT NULL DEFAULT 0")
    # Simple ledger table for income (gelir) and outcome (gider)
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS ledger (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL DEFAULT (date('now')),
            type TEXT NOT NULL CHECK(type IN ('gelir','gider')),
            amount REAL NOT NULL,
            description TEXT,
            invoice_no TEXT,
            company TEXT
        )
        """
    )
    # Migration: add invoice_no/company to ledger if missing
    cursor.execute("PRAGMA table_info(ledger)")
    _cols = [r[1] for r in cursor.fetchall()]
    if 'invoice_no' not in _cols:
        cursor.execute("ALTER TABLE ledger ADD COLUMN invoice_no TEXT")
    if 'company' not in _cols:
        cursor.execute("ALTER TABLE ledger ADD COLUMN company TEXT")
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
    # Cashbook and Bankbook for cash/bank tracking
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS cashbook (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL DEFAULT (datetime('now')),
            type TEXT NOT NULL CHECK(type IN ('in','out')),
            amount REAL NOT NULL,
            description TEXT
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS bankbook (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL DEFAULT (datetime('now')),
            type TEXT NOT NULL CHECK(type IN ('in','out')),
            amount REAL NOT NULL,
            description TEXT
        )
        """
    )
    # Investors for tracking initial capital
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS investors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT,
            initial_capital REAL NOT NULL DEFAULT 0,
            initial_date TEXT NOT NULL DEFAULT (date('now')),
            notes TEXT
        )
        """
    )
    # Investor transactions: contributions and withdrawals
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS investor_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            investor_id INTEGER NOT NULL,
            date TEXT NOT NULL DEFAULT (date('now')),
            type TEXT NOT NULL CHECK(type IN ('contribution','withdrawal')),
            amount REAL NOT NULL,
            notes TEXT,
            FOREIGN KEY(investor_id) REFERENCES investors(id) ON DELETE CASCADE
        )
        """
    )
    # Settings KV store
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
        """
    )
    # Default investor pool percent to 20 if not set
    cursor.execute("INSERT OR IGNORE INTO settings(key, value) VALUES('investor_pool_percent','20')")
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
        # --- MenuButtonFont and style ---
        try:
            base_family = tkfont.nametofont("TkDefaultFont").actual("family")
        except Exception:
            base_family = "Arial"
        menu_font = tkfont.Font(name="MenuButtonFont", family=base_family, size=56, weight="bold")
        print("MenuButtonFont actual:", menu_font.actual())
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Menu.TButton",
            font=menu_font,
            foreground="white",
            background="#1e2023",
            anchor="center",
            justify="center"
        )
        style.map(
            "Menu.TButton",
            background=[("active", "#2a2f33")],
            foreground=[("active", "white")]
        )
        # --- End MenuButtonFont and style ---
        self.title("Kooperatif Giris")
        self.minsize(800, 600)
        # Start maximized when the app launches
        self._maximize_startup()
        # Apply font scaling only (no tk scaling), then theme
        try:
            scale, theme = self._load_ui_settings()
            # Default to light theme if not set
            if not theme:
                theme = 'light'
            try:
                s = float(scale)
                if s <= 0:
                    s = 1.0
            except Exception:
                s = 1.0
            apply_theme(self, scale=s, theme_name=theme)
            try:
                self.ui_scale = float(s)
            except Exception:
                self.ui_scale = 1.0
            # remember user preference
            self.saved_scale = float(self.ui_scale)
            self.saved_theme = theme
            try:
                self.set_min_window_for_scale(self.ui_scale)
            except Exception:
                pass
        except Exception:
            try:
                apply_theme(self)
                self.ui_scale = 1.5
                self.saved_scale = 1.5
                self.saved_theme = None
                try:
                    self.set_min_window_for_scale(self.ui_scale)
                except Exception:
                    pass
            except Exception:
                pass
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
        # Ensure bigger fonts on Login (2.0x); otherwise use saved
        try:
            desired_scale = 2.0 if frame_class.__name__ == 'LoginFrame' else getattr(self, 'saved_scale', None)
            desired_theme = getattr(self, 'saved_theme', None) or 'light'
            if desired_scale is not None:
                try:
                    s = float(desired_scale)
                    if s <= 0:
                        s = 1.0
                except Exception:
                    s = 1.0
                apply_theme(self, scale=s, theme_name=desired_theme)
                try:
                    self.ui_scale = float(s)
                    if hasattr(self, 'set_min_window_for_scale'):
                        # Keep window min size independent from font scale
                        self.set_min_window_for_scale(1.0)
                except Exception:
                    pass
        except Exception:
            pass
        frame = self.frames.get(frame_class)
        if frame is None:
            frame = frame_class(parent=self.container, controller=self)
            self.frames[frame_class] = frame
            frame.grid(row=0, column=0, sticky="nsew")
        if hasattr(frame, "on_show"):
            frame.on_show(**kwargs)
        frame.tkraise()
        # Ensure inputs have comfortable spacing on most screens (skip Login)
        try:
            if frame.__class__.__name__ != 'LoginFrame':
                apply_entry_margins(frame, pady=8)
        except Exception:
            pass
        # Ensure all buttons have consistent external margins (skip Login)
        try:
            if frame.__class__.__name__ != 'LoginFrame':
                apply_button_margins(frame, padx=12, pady=12)
        except Exception:
            pass

    def _maximize_startup(self) -> None:
        # Try native maximize first (works on Windows/Linux)
        try:
            self.state("zoomed")
            return
        except Exception:
            pass

    def _load_ui_settings(self):
        try:
            conn = _sqlite3.connect(DB_NAME)
            cur = conn.cursor()
            cur.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
            cur.execute("SELECT key, value FROM settings WHERE key IN ('ui_theme','ui_scale')")
            rows = dict(cur.fetchall())
            conn.close()
            # Load scale if available
            try:
                scale = float(rows.get('ui_scale') or 1.5)
                if scale <= 0:
                    scale = 1.5
            except Exception:
                scale = 1.5
            theme = None
            if 'ui_theme' in rows and rows['ui_theme']:
                theme = rows['ui_theme']
            return scale, theme
        except Exception:
            return 2.0, None

    def refresh_theme(self) -> None:
        try:
            for frame in self.frames.values():
                if hasattr(frame, 'on_theme_changed'):
                    frame.on_theme_changed()
        except Exception:
            pass
        # Adjust window minimum size for current scale
        try:
            self.set_min_window_for_scale(getattr(self, 'ui_scale', 1.5))
        except Exception:
            pass
        # Fallback: manually size to screen
        try:
            self.update_idletasks()
            w = self.winfo_screenwidth()
            h = self.winfo_screenheight()
            self.geometry(f"{w}x{h}+0+0")
        except Exception:
            # If anything fails, keep default size
            pass

    def set_min_window_for_scale(self, scale: float) -> None:
        """Set a minimum window size that comfortably fits UI at given scale."""
        try:
            base_w, base_h = 800, 600
            w = int(base_w * max(1.0, float(scale)))
            h = int(base_h * max(1.0, float(scale)))
            self.minsize(w, h)
            self.ui_scale = float(scale)
        except Exception:
            pass

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

        # Build centered login card
        self._build_login_card()

    def _build_login_card(self) -> None:
        try:
            if hasattr(self, 'card_container') and self.card_container.winfo_exists():
                self.card_container.destroy()
        except Exception:
            pass
        
        # Plain rectangular login card (no rounded canvas)
        tint = smart_tinted_bg(self)
        self.card_container = tk.Frame(self, bg=tint, bd=1, relief='solid')
        self.card_container.place(relx=0.5, rely=0.5, anchor='center', width=560, height=420)

        inner = tk.Frame(self.card_container, bg=tint)
        inner.pack(fill='both', expand=True, padx=20, pady=16)

        tk.Label(inner, text='Kooperatif Giris', font=('Arial', 18, 'bold'), bg=tint).pack(pady=(0, 10))

        tk.Label(inner, text='Kullanici adi', bg=tint).pack(anchor='center', pady=(4, 2))
        self.entry_user = ttk.Entry(inner)
        self.entry_user.pack(fill='x', padx=24, pady=(0, 6))
        self.entry_user.bind('<Return>', lambda _e: self.do_login())

        tk.Label(inner, text='Sifre', bg=tint).pack(anchor='center', pady=(8, 2))
        self.entry_pass = ttk.Entry(inner, show='*')
        self.entry_pass.pack(fill='x', padx=24, pady=(0, 10))
        self.entry_pass.bind('<Return>', lambda _e: self.do_login())

        ttk.Button(inner, text='Giris Yap', command=self.do_login).pack(pady=(8, 6))


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

    def on_theme_changed(self) -> None:
        # Rebuild card to refresh tinted backgrounds with current theme
        self._build_login_card()



# --- MenuTile class definition ---
class MenuTile(tk.Label):
    _default_fg = "white"
    _base_size = 32

    def __init__(self, parent, icon, text, command, scale: float = 1.0, *args, **kwargs):
        display_text = f"{icon}\n\n{text}"
        self._default_bg = "#1e2023"
        self._hover_bg = "#2a2f33"
        self._default_fg = self._default_fg
        self._base_size = self._base_size
        super().__init__(
            parent,
            text=display_text,
            bg=self._default_bg,
            fg=self._default_fg,
            font=("Arial", int(self._base_size * scale), "bold"),
            justify="center",
            *args,
            **kwargs
        )
        self._command = command
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)
        self.configure(cursor="hand2", wraplength=300)

    def _on_enter(self, event=None):
        self.configure(bg=self._hover_bg)

    def _on_leave(self, event=None):
        self.configure(bg=self._default_bg)

    def _on_click(self, event=None):
        if self._command:
            self._command()

    def refresh_style(self, scale: float = 1.0):
        self.configure(
            bg=self._default_bg,
            fg=self._default_fg,
            font=("Arial", int(self._base_size * scale), "bold"),
        )


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
        # Title
        tk.Label(self, text=title, font=("Arial", 16, "bold")).pack(pady=(20, 6))
        # Centered user card with rounded outline
        user_holder = tk.Frame(self)
        user_holder.pack(pady=(0, 10), anchor='n')
        card, inner = rounded_outline(user_holder, radius=12, padding=10, border='#888')
        card.pack(anchor='center')
        try:
            tint = smart_tinted_bg(self)
            inner.configure(bg=tint)
        except Exception:
            pass
        # Set a comfortable width for the card
        try:
            card.configure(width=520, height=64)
            card.pack_propagate(False)
        except Exception:
            pass
        # Row inside the card: username label (left) + logout button (right)
        header_row = tk.Frame(inner, bg=inner.cget('bg'))
        header_row.pack(fill='x')
        self.user_label = tk.Label(header_row, text="", bg=inner.cget('bg'))
        self.user_label.pack(side='left', padx=12, pady=6)
        logout_btn = ttk.Button(header_row, text="Çıkış yap", command=self.controller.logout, style='Menu.TButton')
        # Use default ttk font for logout; MenuButtonFont is only for menu tiles
        logout_btn.pack(side='right', padx=12, pady=6)

        if description:
            tk.Label(self, text=description, wraplength=360, justify="center").pack(pady=20)

        if actions:
            # Responsive grid of square menu tiles (2/3/4 columns based on width)
            self.grid_frame = tk.Frame(self)
            self.grid_frame.pack(padx=16, pady=10, fill='both', expand=True)

            self._buttons: List[tk.Widget] = []
            ui_scale = getattr(controller, "ui_scale", 1.0)
            for action in actions:
                handler = None
                if action_handlers:
                    handler = action_handlers.get(action)
                if handler is None:
                    handler = lambda name=action: controller.show_placeholder(name)
                try:
                    icon, short = _icon_for_action(str(action))  # type: ignore[attr-defined]
                except Exception:
                    icon, short = "", str(action)
                # Create MenuTile instead of tk.Button, pass scale
                tile = MenuTile(
                    self.grid_frame,
                    icon=icon,
                    text=short,
                    command=handler,
                    scale=ui_scale
                )
                self._buttons.append(tile)

            self._current_cols = 0

            def _desired_cols(width: int) -> int:
                # Breakpoints for column count
                if width >= 1400:
                    return 4
                if width >= 1000:
                    return 3
                if width >= 680:
                    return 2
                return 1

            def _layout(cols: int) -> None:
                # Clear old grid configs
                for i in range(0, 8):
                    try:
                        self.grid_frame.grid_columnconfigure(i, weight=0)
                    except Exception:
                        pass
                # Place tiles
                for idx, tile in enumerate(self._buttons):
                    r, c = divmod(idx, cols)
                    tile.grid(row=r, column=c, padx=10, pady=10, sticky='nsew')
                for c in range(cols):
                    self.grid_frame.grid_columnconfigure(c, weight=1)

            def _on_resize(_e=None):
                try:
                    w = self.grid_frame.winfo_width()
                    if w <= 1:
                        # Use requested width before first layout
                        w = self.winfo_width()
                except Exception:
                    w = 800
                cols = _desired_cols(int(w))
                if cols != self._current_cols:
                    self._current_cols = cols
                    _layout(cols)

            # Initial layout, then reflow on resize
            self.after(0, _on_resize)
            self.bind('<Configure>', _on_resize)

        # Removed bottom-placed logout; now shown next to username

    def on_theme_changed(self) -> None:
        # Refresh style for MenuTile buttons if present
        ui_scale = getattr(self.controller, "ui_scale", 1.0)
        if hasattr(self, "_buttons"):
            for btn in self._buttons:
                if hasattr(btn, "refresh_style"):
                    btn.refresh_style(scale=ui_scale)

    def on_show(self, username: str, role: str) -> None:
        self.user_label.config(text="Signed in as {} ({})".format(username, role))


class AdminFrame(RoleFrame):
    def __init__(self, parent: tk.Misc, controller: App) -> None:
        actions = [
            "Üye yönetimi",
            "Ürün yönetimi",
            "Yeni satış",
            "İade işlemi",
            "Gelir/Gider kaydı",
            "Yatırımcılar",
            "Raporlar",
            "Ayarlar",
        ]
        handlers: Dict[str, Callable[[], None]] = {
            "Üye yönetimi": lambda: controller.show_frame(MembersFrame),
        }
        # Add product management if available
        if ProductsFrame is not None:
            handlers["Ürün yönetimi"] = lambda: controller.show_frame(ProductsFrame)  # type: ignore[arg-type]
        else:
            handlers["Ürün yönetimi"] = lambda: controller.show_placeholder("Ürün yönetimi")
        # Sales
        if SalesFrame is not None:
            handlers["Yeni satış"] = lambda: controller.show_frame(SalesFrame)  # type: ignore[arg-type]
        else:
            handlers["Yeni satış"] = lambda: controller.show_placeholder("Yeni satış")
        # Returns
        if 'ReturnFrame' in globals() and ReturnFrame is not None:
            handlers["İade işlemi"] = lambda: controller.show_frame(ReturnFrame)  # type: ignore[arg-type]
        else:
            handlers["İade işlemi"] = lambda: controller.show_placeholder("İade işlemi")
        # Ledger (income/outcome)
        if LedgerFrame is not None:
            handlers["Gelir/Gider kaydı"] = lambda: controller.show_frame(LedgerFrame)  # type: ignore[arg-type]
        else:
            handlers["Gelir/Gider kaydı"] = lambda: controller.show_placeholder("Gelir/Gider kaydı")
        # Investors
        if 'InvestorsFrame' in globals() and InvestorsFrame is not None:
            handlers["Yatırımcılar"] = lambda: controller.show_frame(InvestorsFrame)  # type: ignore[arg-type]
        else:
            handlers["Yatırımcılar"] = lambda: controller.show_placeholder("Yatırımcılar")
        # Ensure Investors tab opens even if class failed to import at startup
        def _show_investors():
            try:
                from investors import InvestorsFrame as _IF  # type: ignore
                controller.show_frame(_IF)  # type: ignore[arg-type]
            except Exception:
                controller.show_placeholder("Yatırımcılar")
        handlers["Yat��r��mc��lar"] = _show_investors
        # Reports
        # Ensure Investors menu opens even with encoding/import issues
        def _open_investors():
            try:
                from investors import InvestorsFrame as _IF  # type: ignore
                controller.show_frame(_IF)  # type: ignore[arg-type]
            except Exception:
                controller.show_placeholder("Yatırımcılar")
        try:
            for _k in list(actions):
                if isinstance(_k, str) and 'yat' in _k.lower():
                    handlers[_k] = _open_investors
        except Exception:
            pass

        if ReportsFrame is not None:
            handlers["Raporlar"] = lambda: controller.show_frame(ReportsFrame)  # type: ignore[arg-type]
        else:
            handlers["Raporlar"] = lambda: controller.show_placeholder("Raporlar")
        if SettingsFrame is not None:
            handlers["Ayarlar"] = lambda: controller.show_frame(SettingsFrame)  # type: ignore[arg-type]
        else:
            handlers["Ayarlar"] = lambda: controller.show_placeholder("Ayarlar")
        super().__init__(parent, controller, "Admin Panel", actions, handlers)


class CashierFrame(RoleFrame):
    def __init__(self, parent: tk.Misc, controller: App) -> None:
        description = "Barkod okutun ve işlemleri tamamlayın."
        actions = ["Yeni satış", "İade işlemi"]
        handlers: Dict[str, Callable[[], None]] = {}
        # Kasiyer sadece satis yapabilsin: iade eylemini menuden kaldir
        try:
            actions = [a for a in actions if 'Yeni' in str(a)]
        except Exception:
            pass
        if SalesFrame is not None:
            handlers["Yeni satış"] = lambda: controller.show_frame(SalesFrame)  # type: ignore[arg-type]
        else:
            handlers["Yeni satış"] = lambda: controller.show_placeholder("Yeni satış")
        # Keep returns as placeholder for now
        if 'ReturnFrame' in globals() and ReturnFrame is not None:
            handlers["İade işlemi"] = lambda: controller.show_frame(ReturnFrame)  # type: ignore[arg-type]
        else:
            handlers["İade işlemi"] = lambda: controller.show_placeholder("İade işlemi")
        super().__init__(parent, controller, "Kasiyer Ekranı", actions, handlers, description)


class AccountingFrame(RoleFrame):
    def __init__(self, parent: tk.Misc, controller: App) -> None:
        actions = ["Gelir girişi", "Gider girişi", "Bilanço"]
        super().__init__(parent, controller, "Muhasebe Paneli", actions)


class MemberFrame(RoleFrame):
    def __init__(self, parent: tk.Misc, controller: App) -> None:
        description = "Kârdan düşen payınızı ve geçmiş işlemleri inceleyin."
        actions = ["Pay görüntüle", "Ekstre al"]
        super().__init__(parent, controller, "Üye Paneli", actions, None, description)


class ManagerFrame(RoleFrame):
    def __init__(self, parent: tk.Misc, controller: App) -> None:
        actions = [
            "Ürün yönetimi",
            "Yeni satış",
            "İade işlemi",
            "Gelir/Gider kaydı",
            "Yatırımcılar",
            "Raporlar",
            "Ayarlar",
        ]
        handlers: Dict[str, Callable[[], None]] = {}
        if ProductsFrame is not None:
            handlers["Ürün yönetimi"] = lambda: controller.show_frame(ProductsFrame)  # type: ignore[arg-type]
        else:
            handlers["Ürün yönetimi"] = lambda: controller.show_placeholder("Ürün yönetimi")
        # Sales
        if SalesFrame is not None:
            handlers["Yeni satış"] = lambda: controller.show_frame(SalesFrame)  # type: ignore[arg-type]
        else:
            handlers["Yeni satış"] = lambda: controller.show_placeholder("Yeni satış")
        # Returns
        if 'ReturnFrame' in globals() and ReturnFrame is not None:
            handlers["İade işlemi"] = lambda: controller.show_frame(ReturnFrame)  # type: ignore[arg-type]
        else:
            handlers["İade işlemi"] = lambda: controller.show_placeholder("İade işlemi")
        if LedgerFrame is not None:
            handlers["Gelir/Gider kaydı"] = lambda: controller.show_frame(LedgerFrame)  # type: ignore[arg-type]
        else:
            handlers["Gelir/Gider kaydı"] = lambda: controller.show_placeholder("Gelir/Gider kaydı")
        if 'InvestorsFrame' in globals() and InvestorsFrame is not None:
            handlers["Yatırımcılar"] = lambda: controller.show_frame(InvestorsFrame)  # type: ignore[arg-type]
        else:
            handlers["Yatırımcılar"] = lambda: controller.show_placeholder("Yatırımcılar")
       

        if ReportsFrame is not None:
            handlers["Raporlar"] = lambda: controller.show_frame(ReportsFrame)  # type: ignore[arg-type]
        else:
            handlers["Raporlar"] = lambda: controller.show_placeholder("Raporlar")
        if SettingsFrame is not None:
            handlers["Ayarlar"] = lambda: controller.show_frame(SettingsFrame)  # type: ignore[arg-type]
        else:
            handlers["Ayarlar"] = lambda: controller.show_placeholder("Ayarlar")
        super().__init__(parent, controller, "Yönetici Paneli", actions, handlers)


if __name__ == "__main__":
    init_db()
    app = App()
    app.mainloop()
