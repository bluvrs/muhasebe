import sqlite3
import tkinter as tk
from tkinter import messagebox, ttk
import tkinter.font as tkfont
from typing import Dict, List, Optional, Type, Callable
import unicodedata
from members import MembersFrame
from ui import apply_theme, tinted_bg, smart_tinted_bg, rounded_outline, apply_entry_margins, apply_button_margins, _icon_for_action, fix_mojibake_text, create_card, refresh_card_tints, ensure_card_control_backgrounds, CARD_BG_LIGHT, CARD_BG_DARK, ThemeManager
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

def _norm_text(s: str) -> str:
    try:
        # Normalize accents (İ, ı, ş, ğ etc.) to ASCII where possible
        n = unicodedata.normalize('NFKD', s)
        n = ''.join(ch for ch in n if not unicodedata.combining(ch))
        n = n.replace('İ', 'I').replace('ı', 'i')
        return n.lower()
    except Exception:
        return (s or '').lower()

def menu_key_from_label(label: str) -> str:
    low = (label or '').lower()
    nn = _norm_text(label or '')
    if 'üye' in low or 'uye' in low or 'uye' in nn:
        return 'members'
    if 'ür' in low or 'urun' in low or 'prod' in low or 'urun' in nn:
        return 'products'
    if 'sat' in low and ('iade' not in low and 'i̇ade' not in low):
        return 'sale'
    if 'iade' in low or 'iade' in nn:
        return 'return'
    if 'gelir' in low or 'gider' in low or 'ledger' in low or 'gelir' in nn or 'gider' in nn:
        return 'ledger'
    if 'yat' in low or 'yati' in nn:
        return 'investors'
    if 'rapor' in low or 'rapor' in nn:
        return 'reports'
    if 'ayar' in low or 'ayar' in nn or 'settings' in nn:
        return 'settings'
    return low.replace(' ', '_')

# Unified main action list and handlers
def get_main_actions() -> List[str]:
    return [
        "Üye yönetimi",
        "Ürün yönetimi",
        "Yeni satış",
        "İade işlemi",
        "Gelir/Gider kaydı",
        "Yatırımcılar",
        "Raporlar",
        "Ayarlar",
    ]

def build_main_handlers(controller: 'App') -> Dict[str, Callable[[], None]]:
    handlers: Dict[str, Callable[[], None]] = {}
    # Members
    handlers["Üye yönetimi"] = (lambda: controller.show_frame(MembersFrame)) if 'MembersFrame' in globals() and MembersFrame is not None else (lambda: controller.show_placeholder("Üye yönetimi"))
    # Products
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
    # Ledger
    if LedgerFrame is not None:
        handlers["Gelir/Gider kaydı"] = lambda: controller.show_frame(LedgerFrame)  # type: ignore[arg-type]
    else:
        handlers["Gelir/Gider kaydı"] = lambda: controller.show_placeholder("Gelir/Gider kaydı")
    # Investors
    if 'InvestorsFrame' in globals() and InvestorsFrame is not None:
        handlers["Yatırımcılar"] = lambda: controller.show_frame(InvestorsFrame)  # type: ignore[arg-type]
    else:
        handlers["Yatırımcılar"] = lambda: controller.show_placeholder("Yatırımcılar")
    # Reports
    if ReportsFrame is not None:
        handlers["Raporlar"] = lambda: controller.show_frame(ReportsFrame)  # type: ignore[arg-type]
    else:
        handlers["Raporlar"] = lambda: controller.show_placeholder("Raporlar")
    # Settings
    if SettingsFrame is not None:
        handlers["Ayarlar"] = lambda: controller.show_frame(SettingsFrame)  # type: ignore[arg-type]
    else:
        handlers["Ayarlar"] = lambda: controller.show_placeholder("Ayarlar")
    return handlers

def default_allowed_by_role(role: str) -> set[str]:
    r = (role or '').lower()
    if r == 'admin':
        return {'members','products','sale','return','ledger','investors','reports','settings'}
    if r == 'kasiyer':
        return {'sale', 'return'}
    if r == 'muhasebe':
        return {'ledger', 'reports'}
    if r == 'yonetici':
        return {'members','products','investors','ledger','reports','settings'}
    if r == 'uye':
        return set()
    return {'members','products','sale','return','ledger','investors','reports','settings'}

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
    # Per-user menu permissions (optional). If no rows for a user, defaults to allow-all.
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS user_permissions (
            username TEXT NOT NULL,
            menu_key TEXT NOT NULL,
            allowed INTEGER NOT NULL DEFAULT 1,
            PRIMARY KEY(username, menu_key)
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
    # Seed default UI settings if missing
    cursor.execute("INSERT OR IGNORE INTO settings(key, value) VALUES('ui_theme','light')")
    cursor.execute("INSERT OR IGNORE INTO settings(key, value) VALUES('ui_scale','1.5')")
    cursor.execute("INSERT OR IGNORE INTO settings(key, value) VALUES('ui_base_pt','12')")
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
        menu_font = tkfont.Font(name="MenuButtonFont", family=base_family, size=32, weight="bold")
       
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
            scale, theme, base_pt = self._load_ui_settings()
            # Default to light theme if not set
            if not theme:
                theme = 'light'
            try:
                s = float(scale)
                if s <= 0:
                    s = 1.0
            except Exception:
                s = 1.0
            apply_theme(self, scale=s, theme_name=theme, base_pt=base_pt)
            try:
                self.ui_scale = float(s)
            except Exception:
                self.ui_scale = 1.0
            # remember user preference
            self.saved_scale = float(self.ui_scale)
            self.saved_theme = theme
            try:
                self.saved_base_pt = int(base_pt) if base_pt else 12
            except Exception:
                self.saved_base_pt = 12
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
                self.saved_base_pt = 12
                try:
                    self.set_min_window_for_scale(self.ui_scale)
                except Exception:
                    pass
            except Exception:
                pass
        self.frames: Dict[Type[tk.Frame], tk.Frame] = {}
        self.active_user: Optional[Dict[str, str]] = None
        # Disable automatic margin walkers by default to avoid layout drift
        # on first entry after theme/font changes. Screens manage their own
        # spacing explicitly.
        self.auto_margins_enabled: bool = False
        # Track currently shown frame to allow safe re-render after
        # base font size changes.
        self.current_frame_class: Optional[Type[tk.Frame]] = None
        self.current_frame_kwargs: Dict = {}

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
        # Current user's allowed menu keys (None => allow all)
        self.user_permissions: Optional[set[str]] = None

        # Normalize window title text if mojibake slipped in
        try:
            self.title(fix_mojibake_text(self.title()) or self.title())
        except Exception:
            pass
        # Wrap messagebox functions so all messages are fixed at call-time
        self._wrap_messagebox_mojibake_fix()
        self.show_frame(LoginFrame)

    # IMPORTANT: Do not override Tk.__call__ — Tkinter relies on it to call
    # underlying Tcl commands. Overriding it breaks internals and can surface
    # confusing errors in callbacks. Instead, provide a dedicated helper that
    # developers can bind to when they need a safe no-op callback target.
    def safe_noop(self, *args, **kwargs):
        try:
            import sys
            print("[warn] safe_noop invoked; ignoring.", file=sys.stderr)
        except Exception:
            pass

    # Centralized callback exception handler so Tkinter shows a clear error
    # instead of failing with obscure AttributeErrors in some environments.
    def report_callback_exception(self, exc, val, tb):  # type: ignore[override]
        try:
            import traceback, sys
            traceback.print_exception(exc, val, tb)
            try:
                # Show a concise error message to the user
                messagebox.showerror("Hata", f"Beklenmeyen hata: {exc.__name__}: {val}")
            except Exception:
                # Fallback to stderr if UI messagebox fails
                print(f"[tk-error] {exc.__name__}: {val}", file=sys.stderr)
        except Exception:
            pass

    def _wrap_messagebox_mojibake_fix(self) -> None:
        try:
            import tkinter.messagebox as _mb
            def _wrap(fn):
                def inner(title, message, *a, **kw):
                    try:
                        title2 = fix_mojibake_text(title)
                        msg2 = fix_mojibake_text(message)
                        return fn(title2, msg2, *a, **kw)
                    except Exception:
                        return fn(title, message, *a, **kw)
                return inner
            for name in ("showinfo","showwarning","showerror","askyesno","askokcancel","askquestion","askretrycancel","askyesnocancel"):
                if hasattr(_mb, name):
                    setattr(_mb, name, _wrap(getattr(_mb, name)))
        except Exception:
            pass

    def _fix_texts_recursive(self, widget) -> None:
        try:
            # Fix classic Tk widgets with 'text' option
            if hasattr(widget, 'cget') and 'text' in widget.keys():
                try:
                    txt = widget.cget('text')
                    fixed = fix_mojibake_text(txt)
                    if fixed != txt:
                        widget.configure(text=fixed)
                except Exception:
                    pass
            # Special cases: ttk.Notebook tab texts
            try:
                from tkinter import ttk as _ttk
                if isinstance(widget, _ttk.Notebook):
                    for i in range(widget.index('end') or 0):
                        try:
                            tabtxt = widget.tab(i, option='text')
                            fixed = fix_mojibake_text(tabtxt)
                            if fixed != tabtxt:
                                widget.tab(i, text=fixed)
                        except Exception:
                            pass
            except Exception:
                pass
            # Special cases: ttk.Treeview headings
            try:
                from tkinter import ttk as _ttk
                if isinstance(widget, _ttk.Treeview):
                    cols = widget.cget('columns') or ()
                    for c in cols:
                        try:
                            htxt = widget.heading(c, option='text')
                            fixed = fix_mojibake_text(htxt)
                            if fixed != htxt:
                                widget.heading(c, text=fixed)
                        except Exception:
                            pass
            except Exception:
                pass
            # Recurse
            for child in widget.winfo_children():
                self._fix_texts_recursive(child)
        except Exception:
            pass

    def show_frame(self, frame_class: Type[tk.Frame], **kwargs) -> None:
        # Ensure bigger fonts on Login (2.0x); otherwise use saved
        try:
            desired_scale = 2.0 if frame_class.__name__ == 'LoginFrame' else getattr(self, 'saved_scale', None)
            desired_theme = getattr(self, 'saved_theme', None) or 'light'
            desired_base_pt = getattr(self, 'saved_base_pt', 12)
            if desired_scale is not None:
                try:
                    s = float(desired_scale)
                    if s <= 0:
                        s = 1.0
                except Exception:
                    s = 1.0
                apply_theme(self, scale=s, theme_name=desired_theme, base_pt=desired_base_pt)
                try:
                    self.ui_scale = float(s)
                    if hasattr(self, 'set_min_window_for_scale'):
                        # Keep window min size independent from font scale
                        self.set_min_window_for_scale(1.0)
                except Exception:
                    pass
        except Exception:
            pass
        # For volatile screens that are sensitive to initial layout timing,
        # recreate the frame on every entry so geometry starts from a clean
        # state (fixes first-entry misalignment). Currently only SalesFrame.
        try:
            volatile = frame_class.__name__ in ('SalesFrame',)
        except Exception:
            volatile = False

        frame = self.frames.get(frame_class)
        if volatile and frame is not None:
            try:
                frame.destroy()
            except Exception:
                pass
            try:
                del self.frames[frame_class]
            except Exception:
                pass
            frame = None
        if frame is None:
            frame = frame_class(parent=self.container, controller=self)
            self.frames[frame_class] = frame
            frame.grid(row=0, column=0, sticky="nsew")
        if hasattr(frame, "on_show"):
            frame.on_show(**kwargs)
        frame.tkraise()
        # Remember current for potential re-render triggers
        try:
            self.current_frame_class = frame_class
            # Shallow copy to avoid accidental external mutation
            self.current_frame_kwargs = dict(kwargs) if kwargs else {}
        except Exception:
            pass
        # Do NOT touch margins immediately; wait for fonts/theme to settle.
        # Enforce contrasting text colors for classic widgets in the shown frame
        try:
            from ui import ensure_contrast_text_colors as _ectc
            _ectc(frame)
        except Exception:
            pass
        # And ttk.Label per-widget contrast
        try:
            from ui import ensure_ttk_label_contrast as _etl
            _etl(frame)
        except Exception:
            pass
        # Layout fix after fonts/theme settle: run after idle (two passes).
        try:
            def _reflow_pass():
                try:
                    frame.update_idletasks()
                except Exception:
                    pass
                try:
                    if self.auto_margins_enabled and frame.__class__.__name__ != 'LoginFrame':
                        apply_entry_margins(frame, pady=8)
                        apply_button_margins(frame, padx=12, pady=12)
                except Exception:
                    pass
                # Allow frames to customize post-show reflow
                try:
                    if hasattr(frame, 'on_post_show'):
                        frame.on_post_show()
                except Exception:
                    pass
            # Immediate idle and a second pass shortly after
            self.after(0, _reflow_pass)
            self.after(120, _reflow_pass)
        except Exception:
            pass
        # After the frame is shown, fix any mojibake text in its subtree and window title
        try:
            self._fix_texts_recursive(frame)
            self.title(fix_mojibake_text(self.title()) or self.title())
        except Exception:
            pass
        # Avoid reapplying the whole theme here — it was causing vertical drift
        # on some screens. Theme is applied centrally; frames handle their own
        # stabilization in on_show/idle reflow.

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
            cur.execute("SELECT key, value FROM settings WHERE key IN ('ui_theme','ui_scale','ui_base_pt')")
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
            try:
                base_pt = int(rows.get('ui_base_pt') or 12)
                if base_pt < 8:
                    base_pt = 8
            except Exception:
                base_pt = 12
            return scale, theme, base_pt
        except Exception:
            return 2.0, None, 12

    def refresh_theme(self) -> None:
        # Centralized theme application
        ThemeManager.apply_all(
            self,
            theme_name=getattr(self, 'saved_theme', None) or 'light',
            scale=getattr(self, 'ui_scale', 1.5),
            base_pt=getattr(self, 'saved_base_pt', 12),
        )
        # Now, after theme applied and recoloring, notify all frames of theme change
        try:
            for frame in self.frames.values():
                if hasattr(frame, 'on_theme_changed'):
                    frame.on_theme_changed()
        except Exception:
            pass
        # Avoid forcing a global reflow here; each frame handles its own
        # layout in on_show/show_frame to prevent cumulative padding drift.
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
        """Set a minimum window size that comfortably fits UI at given scale.
        Note: does NOT mutate self.ui_scale; this is only a min-size policy.
        """
        try:
            base_w, base_h = 800, 600
            w = int(base_w * max(1.0, float(scale)))
            h = int(base_h * max(1.0, float(scale)))
            self.minsize(w, h)
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
        # Load per-user permissions (if any). None => allow all
        try:
            if str(role).lower() == 'admin':
                # Admin is always full access; ignore any stored overrides
                self.user_permissions = None
            else:
                conn = sqlite3.connect(DB_NAME)
                cur = conn.cursor()
                cur.execute("CREATE TABLE IF NOT EXISTS user_permissions (username TEXT, menu_key TEXT, allowed INTEGER, PRIMARY KEY(username, menu_key))")
                cur.execute("SELECT menu_key FROM user_permissions WHERE username=? AND allowed=1", (username,))
                rows = [r[0] for r in cur.fetchall()]
                conn.close()
                # For non-admins: never use defaults; show exactly what DB says
                self.user_permissions = set(rows)
        except Exception:
            # On any error, be safe: show nothing for non-admins
            self.user_permissions = set()
        # Debug: print current user's resolved permissions
        try:
            perms = self.user_permissions
            if perms is None:
                print(f"[perm] user={username} role={role} -> ALL")
            else:
                print(f"[perm] user={username} role={role} -> {sorted(list(perms))}")
        except Exception:
            pass
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

        tk.Label(inner, text='Kooperatif Giris', font='TkHeadingFont', bg=tint).pack(pady=(0, 10))

        tk.Label(inner, text='Kullanici adi', bg=tint).pack(anchor='center', pady=(4, 2))
        self.entry_user = ttk.Entry(inner)
        self.entry_user.pack(fill='x', padx=24, pady=(0, 6))
        self.entry_user.bind('<Return>', lambda _e: self.do_login())

        tk.Label(inner, text='Sifre', bg=tint).pack(anchor='center', pady=(8, 2))
        self.entry_pass = ttk.Entry(inner, show='*')
        self.entry_pass.pack(fill='x', padx=24, pady=(0, 10))
        self.entry_pass.bind('<Return>', lambda _e: self.do_login())

        ttk.Button(inner, text='Giris Yap', command=self.do_login, style='Solid.TButton').pack(pady=(8, 6))


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
        # Rebuild the login card every time we show this frame.
        # After navigating between role screens, theme/background tints can change,
        # and the old labels keep their previous background color which looks like
        # grey blocks behind the text. Recreating the card ensures all widgets
        # pick up the current theme/tint correctly.
        try:
            self._build_login_card()
        except Exception:
            pass
        # Clear fields and focus username
        try:
            self.entry_user.delete(0, tk.END)
            self.entry_pass.delete(0, tk.END)
            self.entry_user.focus_set()
        except Exception:
            pass

    def on_theme_changed(self) -> None:
        # Refresh style for MenuTile buttons if present
        ui_scale = getattr(self.controller, "ui_scale", 1.0)
        for frame in self.controller.frames.values():
            if hasattr(frame, "_buttons"):
                for btn in frame._buttons:
                    if hasattr(btn, "refresh_style"):
                        btn.refresh_style(scale=ui_scale)
        self._build_login_card()



# --- MenuTile class definition ---
class MenuTile(tk.Label):
    _default_fg = "white"
    _base_size = 14

    def __init__(self, parent, icon, text, command, scale: float = 1.0, *args, **kwargs):
        display_text = f"{icon}\n\n{text}"
        # Determine theme from parent.controller if possible
        theme = "light"
        controller = getattr(parent, "controller", None)
        if controller is not None:
            theme = getattr(controller, "saved_theme", "light")
        if theme is None:
            theme = "light"
        theme = str(theme).lower()
        if theme == "dark":
            self._default_bg = "white"
            self._default_fg = "black"
        else:
            self._default_bg = "#1e2023"
            self._default_fg = "white"
        self._hover_bg = "#2a2f33"
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
        # Mark this tile to opt out from global recolor passes
        try:
            self._preserve_theme = True
            self._preserve_fg = True
        except Exception:
            pass
        # Add padding for larger menu buttons
        self.configure(padx=20, pady=20)
        self._command = command
        # derive a menu_key from text for permission checks
        try:
            key = menu_key_from_label(text)
            self._menu_key = key
        except Exception:
            self._menu_key = None
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)
        self.configure(cursor="hand2", wraplength=300)
        # Immediately set correct theme-based colors
        self.refresh_style(scale)

    def _on_enter(self, event=None):
        self.configure(bg=self._hover_bg)

    def _on_leave(self, event=None):
        self.configure(bg=self._default_bg)

    def _on_click(self, event=None):
        try:
            if callable(self._command):
                self._command()
        except Exception:
            pass

    def refresh_style(self, scale: float = 1.0):
        # Try to get theme from controller if available
        theme = "light"
        controller = None
        parent = self.master
        if hasattr(parent, "controller"):
            controller = parent.controller
        elif hasattr(parent, "master") and hasattr(parent.master, "controller"):
            controller = parent.master.controller
        if controller is not None:
            theme = getattr(controller, "saved_theme", "light")
        if theme is None:
            theme = "light"
        theme = str(theme).lower()
        if theme == "dark":
            self._default_bg = "white"
            self._default_fg = "black"
        else:
            self._default_bg = "#1e2023"
            self._default_fg = "white"
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
        tk.Label(self, text=title, font='TkHeadingFont').pack(pady=(20, 6))
        # Centered user card with rounded outline
        user_holder = tk.Frame(self)
        user_holder.pack(pady=(0, 10), anchor='n')
        padding_val = 10
        card, inner = create_card(user_holder, radius=12, padding=padding_val, border='#888')
        card.pack(anchor='center')
        # Save card and inner for later theme updates
        self.card = card
        self.inner = inner
        # Set width and compute height to fit inner content (so canvas border
        # draws correctly and text is not clipped). Keep pack_propagate(False).
        try:
            def _fit_card(_e=None):
                try:
                    inner.update_idletasks()
                    h = inner.winfo_reqheight() + padding_val * 2
                    if h < 72:
                        h = 72
                    card.configure(width=520, height=h)
                    card.pack_propagate(False)
                except Exception:
                    pass
            # Fit after widgets are realized
            self.after(0, _fit_card)
            # Second pass to ensure row fits tallest child and no text crops
            def _fit_row(_e=None):
                try:
                    header_row.update_idletasks()
                    btn_h = logout_btn.winfo_reqheight()
                    lbl_h = self.user_label.winfo_reqheight()
                    row_h = max(btn_h, lbl_h) + 8
                    header_row.grid_rowconfigure(0, minsize=row_h)
                    inner.update_idletasks()
                    h = inner.winfo_reqheight() + padding_val * 2 + 8
                    if h < 80:
                        h = 80
                    card.configure(height=h)
                except Exception:
                    pass
            self.after(60, _fit_row)
        except Exception:
            pass
        # Row inside the card: username label (left) + logout button (right)
        header_row = tk.Frame(inner, bg=inner.cget('bg'))
        header_row.pack(fill='x')
        # Keep a reference for theme updates
        self.header_row = header_row
        # Use grid so items are vertically centered within the row
        header_row.grid_columnconfigure(0, weight=1)
        header_row.grid_rowconfigure(0, weight=1)
        self.user_label = tk.Label(header_row, text="", bg=inner.cget('bg'))
        self.user_label.grid(row=0, column=0, padx=12, pady=6, sticky='nsw')
        logout_btn = ttk.Button(header_row, text="Çıkış yap", command=self.controller.logout, style='Menu.TButton', padding=(24,12))
        # Use default ttk font for logout; MenuButtonFont is only for menu tiles
        logout_btn.grid(row=0, column=1, padx=12, pady=6, sticky='nse')
        # Keep reference to reapply padding after theme changes
        self.logout_btn = logout_btn

        if description:
            tk.Label(self, text=description, wraplength=360, justify="center").pack(pady=20)

        if actions:
            # Responsive grid of square menu tiles (2/3/4 columns based on width)
            self.grid_frame = tk.Frame(self)
            self.grid_frame.pack(padx=16, pady=10, fill='both', expand=True)

            self._buttons: List[tk.Widget] = []
            self._layout_ready = False
            ui_scale = getattr(controller, "ui_scale", 1.0)
            for action in actions:
                handler = None
                if action_handlers:
                    try:
                        handler = action_handlers.get(action)  # type: ignore[assignment]
                    except Exception:
                        handler = None
                # Fallback to placeholder if handler missing or not callable
                if (handler is None) or (not callable(handler)):
                    handler = lambda name=action: controller.show_placeholder(name)
                try:
                    icon, short = _icon_for_action(str(action))  # type: ignore[attr-defined]
                except Exception:
                    icon, short = "", str(action)
                # Permission key derived from original action label
                try:
                    key = menu_key_from_label(str(action))
                except Exception:
                    key = None
                # Create MenuTile instead of tk.Button, pass scale
                tile = MenuTile(
                    self.grid_frame,
                    icon=icon,
                    text=short,
                    command=handler,
                    scale=ui_scale
                )
                try:
                    if key:
                        tile._menu_key = key  # ensure consistent key for visibility checks
                except Exception:
                    pass
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

            def _on_resize(_e=None):
                try:
                    if not getattr(self, '_layout_ready', False):
                        return
                    w = self.grid_frame.winfo_width()
                    if w <= 1:
                        # Use requested width before first layout
                        w = self.winfo_width()
                except Exception:
                    w = 800
                cols = _desired_cols(int(w))
                if cols != self._current_cols:
                    self._current_cols = cols
                # Always relayout visible (allowed) tiles on resize
                try:
                    allowed = getattr(self, '_current_allowed', None)
                except Exception:
                    allowed = None
                self._relayout_visible_tiles(allowed)

            # Reflow on resize; initial layout is handled in on_show
            self.bind('<Configure>', _on_resize)

        # Removed bottom-placed logout; now shown next to username

    def on_theme_changed(self) -> None:
        # Determine theme
        theme = getattr(self.controller, "saved_theme", None)
        if not theme:
            theme = "light"
        theme = str(theme).lower()
        # Theme-based colors
        if theme == "dark":
            card_bg = "white"
            inner_bg = "white"
            header_row_bg = "#1e2023"
            user_label_bg = "#1e2023"
            user_label_fg = "white"
            logout_btn_bg = "white"
            logout_btn_fg = "black"
            logout_btn_active_bg = "#ddd"
        else:
            card_bg = "#1e2023"
            inner_bg = "#1e2023"
            header_row_bg = "white"
            user_label_bg = "white"
            user_label_fg = "black"
            logout_btn_bg = "#1e2023"
            logout_btn_fg = "white"
            logout_btn_active_bg = "#2a2f33"

        # Refresh style for MenuTile buttons if present
        ui_scale = getattr(self.controller, "ui_scale", 1.0)
        if hasattr(self, "_buttons"):
            for btn in self._buttons:
                if hasattr(btn, "refresh_style"):
                    btn.refresh_style(scale=ui_scale)
        # Ensure logout button keeps its vertical padding after theme restyle
        try:
            if hasattr(self, 'logout_btn'):
                self.logout_btn.configure(style='Menu.TButton', padding=(24,12))
        except Exception:
            pass

        # Update card and inner backgrounds if they exist
        try:
            self.card.configure(bg=card_bg)
        except Exception:
            pass
        try:
            self.inner.configure(bg=inner_bg)
        except Exception:
            pass
        # Update header_row background if exists
        header_row = None
        if hasattr(self, "header_row"):
            header_row = self.header_row
        elif hasattr(self, "inner"):
            # Try to find header_row as the first child of inner
            try:
                children = self.inner.winfo_children()
                if children:
                    header_row = children[0]
                    self.header_row = header_row
            except Exception:
                pass
        if header_row is not None:
            try:
                header_row.configure(bg=header_row_bg)
            except Exception:
                pass
        # Update user_label background/foreground to match its parent
        if hasattr(self, "user_label"):
            try:
                self.user_label.configure(bg=user_label_bg, fg=user_label_fg)
            except Exception:
                pass
        # Update logout button style (search for it in header_row's children)
        if header_row is not None:
            try:
                for child in header_row.winfo_children():
                    # Try to find the logout button by text or widget type
                    if isinstance(child, tk.Button) or isinstance(child, ttk.Button):
                        # Try to match by text
                        try:
                            if getattr(child, "cget", lambda x: None)("text") == "Çıkış yap":
                                # If it's a tk.Button, set directly; if ttk, fallback to configure
                                try:
                                    child.configure(
                                        bg=logout_btn_bg,
                                        fg=logout_btn_fg,
                                        activebackground=logout_btn_active_bg,
                                    )
                                except Exception:
                                    # For ttk.Button, use style if possible
                                    style = ttk.Style()
                                    style_name = "Logout.TButton"
                                    style.configure(
                                        style_name,
                                        background=logout_btn_bg,
                                        foreground=logout_btn_fg,
                                    )
                                    style.map(
                                        style_name,
                                        background=[("active", logout_btn_active_bg)],
                                        foreground=[("active", logout_btn_fg)],
                                    )
                                    child.configure(style=style_name)
                        except Exception:
                            pass
            except Exception:
                pass

    def on_show(self, username: str, role: str) -> None:
        self.user_label.config(text="{} ({})".format(username, role))
        # Apply per-user permissions by hiding disallowed tiles
        try:
            allowed = getattr(self.controller, 'user_permissions', None)
            try:
                self._current_allowed = allowed
            except Exception:
                pass
            if hasattr(self, '_buttons') and self._buttons:
                for btn in self._buttons:
                    key = getattr(btn, '_menu_key', None)
                    ok = True if allowed is None else (key in allowed)
                    try:
                        print(f"[perm] tile key={key} allowed={ok}")
                    except Exception:
                        pass
                    try:
                        if ok:
                            btn.grid()  # ensure visible
                        else:
                            btn.grid_remove()
                    except Exception:
                        pass
                # Make layout active and relayout visible tiles to remove gaps
                try:
                    self._layout_ready = True
                    self._relayout_visible_tiles(allowed)
                except Exception:
                    pass
                # Debug: print visible tile keys actually shown on screen
                try:
                    vis = []
                    for btn in self._buttons:
                        if getattr(btn, 'winfo_ismapped', lambda: False)():
                            k = getattr(btn, '_menu_key', None)
                            if k:
                                vis.append(k)
                    # print(f"[perm] visible_menus={sorted(vis)}")
                except Exception:
                    pass
        except Exception:
            pass

    def _relayout_visible_tiles(self, allowed_set) -> None:
        try:
            if not hasattr(self, '_buttons'):
                return
            # Determine which tiles should be visible per allowed_set
            def _is_allowed(btn) -> bool:
                try:
                    key = getattr(btn, '_menu_key', None)
                    return True if allowed_set is None else (key in allowed_set)
                except Exception:
                    return False
            tiles = [b for b in self._buttons if _is_allowed(b)]
            if not tiles:
                return
            # Determine columns based on width similar to initial layout
            try:
                w = self.grid_frame.winfo_width()
                if w <= 1:
                    w = self.winfo_width()
            except Exception:
                w = 800
            cols = 1
            if w >= 1400:
                cols = 4
            elif w >= 1000:
                cols = 3
            elif w >= 680:
                cols = 2
            # Clear existing grid weights
            for i in range(0, 8):
                try:
                    self.grid_frame.grid_columnconfigure(i, weight=0)
                except Exception:
                    pass
            # Place tiles densely
            idx = 0
            for tile in tiles:
                r, c = divmod(idx, cols)
                try:
                    tile.grid_configure(row=r, column=c, padx=10, pady=10, sticky='nsew')
                except Exception:
                    pass
                idx += 1
            # Hide disallowed tiles explicitly
            for tile in self._buttons:
                if tile not in tiles:
                    try:
                        tile.grid_remove()
                    except Exception:
                        pass
            for c in range(cols):
                try:
                    self.grid_frame.grid_columnconfigure(c, weight=1)
                except Exception:
                    pass
        except Exception:
            pass


class AdminFrame(RoleFrame):
    def __init__(self, parent: tk.Misc, controller: App) -> None:
        actions = get_main_actions()
        handlers = build_main_handlers(controller)
        super().__init__(parent, controller, "Admin Panel", actions, handlers)


class CashierFrame(RoleFrame):
    def __init__(self, parent: tk.Misc, controller: App) -> None:
        description = "Barkod okutun ve işlemleri tamamlayın."
        actions = get_main_actions()
        handlers = build_main_handlers(controller)
        super().__init__(parent, controller, "Kasiyer Ekranı", actions, handlers, description)


class AccountingFrame(RoleFrame):
    def __init__(self, parent: tk.Misc, controller: App) -> None:
        actions = get_main_actions()
        handlers = build_main_handlers(controller)
        super().__init__(parent, controller, "Muhasebe Paneli", actions, handlers)


class MemberFrame(RoleFrame):
    def __init__(self, parent: tk.Misc, controller: App) -> None:
        description = "Kârdan düşen payınızı ve geçmiş işlemleri inceleyin."
        actions = get_main_actions()
        handlers = build_main_handlers(controller)
        super().__init__(parent, controller, "Üye Paneli", actions, handlers, description)


class ManagerFrame(RoleFrame):
    def __init__(self, parent: tk.Misc, controller: App) -> None:
        actions = get_main_actions()
        handlers = build_main_handlers(controller)
        super().__init__(parent, controller, "Yönetici Paneli", actions, handlers)
        super().__init__(parent, controller, "Yönetici Paneli", actions, handlers)


if __name__ == "__main__":
    init_db()
    app = App()
    app.mainloop()
