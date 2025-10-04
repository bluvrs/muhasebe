import sqlite3
import os
import sys
from datetime import datetime
import time
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

# App metadata
APP_NAME = 'Kooperatif'
APP_VERSION = '1.00'

def resource_path(name: str) -> str:
    try:
        base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    except Exception:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, name)

# Try to read version from VERSION.txt (packaged via PyInstaller)
try:
    vfile = resource_path('VERSION.txt')
    if os.path.exists(vfile):
        with open(vfile, 'r', encoding='utf-8', errors='ignore') as f:
            ver = f.readline().strip()
            if ver:
                APP_VERSION = ver
except Exception:
    pass


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
        # Use custom borderless title bar. We'll keep inputs typeable by
        # aggressively restoring keyboard focus after we enable borderless.
        # (We avoid disabling borderless because the app relies on the
        # custom chrome.)
        # Use custom borderless title bar by default
        self.use_borderless = True
        # Set window icon for packaged exe as well as dev run
        try:
            def _res_path(name: str) -> str:
                base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
                return os.path.join(base, name)
            ico = _res_path('app.ico')
            if os.path.exists(ico):
                try:
                    self.iconbitmap(default=ico)  # Works on Windows
                except Exception:
                    pass
            # If a PNG icon is available, set it for platforms where ico is ignored (macOS/Linux)
            png = _res_path('app.png')
            if os.path.exists(png):
                try:
                    self.iconphoto(True, tk.PhotoImage(file=png))
                except Exception:
                    pass
        except Exception:
            pass
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
        # Defer enabling borderless chrome until after theme and first frame
        # are initialized to avoid early focus issues on some platforms.
        # System menubar disabled to remove Help/About entry
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
            # After theme and scale are applied, restyle the custom title bar
            try:
                self._style_titlebar()
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
        # Enable automatic margins for inputs and buttons across screens
        self.auto_margins_enabled: bool = True
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
        # Now that the initial UI is up with the correct theme and focus,
        # enable borderless chrome if requested and set up taskbar anchor (Windows).
        if getattr(self, 'use_borderless', False):
            try:
                self._create_taskbar_anchor()
            except Exception:
                pass
            try:
                self._enable_borderless_chrome()
            except Exception:
                pass

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

    def show_about(self) -> None:
        """Custom About dialog with clickable URL; no wrapping."""
        try:
            import webbrowser, tkinter as _tk
            # Close previous if any
            try:
                if hasattr(self, '_about_win') and self._about_win.winfo_exists():  # type: ignore[attr-defined]
                    self._about_win.destroy()  # type: ignore[attr-defined]
            except Exception:
                pass
            top = _tk.Toplevel(self)
            self._about_win = top  # type: ignore[attr-defined]
            top.title('Hakkında')
            top.transient(self)
            top.resizable(True, False)  # genişletilebilir (yatay)
            try:
                # When closed, restore focus to the active view (login, etc.)
                def _on_close():
                    try:
                        top.destroy()
                    except Exception:
                        pass
                    try:
                        self.after(50, self._return_focus_to_active)
                        self.after(80, lambda: self._start_focus_guard(800))
                    except Exception:
                        pass
                top.protocol('WM_DELETE_WINDOW', _on_close)
                top.bind('<Destroy>', lambda _e: (self.after(50, self._return_focus_to_active), self.after(80, lambda: self._start_focus_guard(800))))
            except Exception:
                pass
            # Try to copy app icon to dialog
            try:
                png = None
                try:
                    import os, sys
                    base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
                    png = os.path.join(base, 'app.png')
                except Exception:
                    png = None
                if png and os.path.exists(png):
                    top.iconphoto(True, _tk.PhotoImage(file=png))
            except Exception:
                pass
            # Content
            container = _tk.Frame(top, padx=18, pady=14)
            container.pack(fill='both', expand=True)
            # Try to show app icon inside dialog (left side)
            icon_row = _tk.Frame(container)
            icon_row.pack(anchor='w', fill='x')
            try:
                img = None
                if png and os.path.exists(png):
                    img = _tk.PhotoImage(file=png)
                if img is not None:
                    lbl_img = _tk.Label(icon_row, image=img)
                    lbl_img.image = img  # keep ref
                    lbl_img.pack(side='left', padx=(0, 12))
            except Exception:
                pass
            # App name + version (slightly smaller than TkHeadingFont)
            text_col = _tk.Frame(icon_row)
            text_col.pack(side='left', anchor='w')
            try:
                import tkinter.font as tkfont
                hf = tkfont.nametofont('TkHeadingFont')
                sz = max(10, int(hf.actual('size')) - 2)
                head_font = (hf.actual('family'), sz, 'bold')
            except Exception:
                head_font = 'TkHeadingFont'
            _tk.Label(text_col, text=APP_NAME, font=head_font, anchor='w').pack(anchor='w')
            _tk.Label(text_col, text=f'Sürüm: {APP_VERSION}', anchor='w').pack(anchor='w', pady=(2, 6))
            # Build date/time from executable (frozen) or this file
            try:
                src = sys.executable if getattr(sys, 'frozen', False) else __file__
                ts = os.path.getmtime(src)
                built = datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
            except Exception:
                built = ''
            if built:
                _tk.Label(container, text=f'Yapım Tarihi: {built}', anchor='w').pack(anchor='w')
            # Clickable link
            url = 'https://murathodja.com'
            link = _tk.Label(container, text=url, fg='#0a66c2', cursor='hand2', anchor='w')
            link.pack(anchor='w', pady=(2, 6))
            def _open(_e=None):
                try:
                    webbrowser.open(url)
                except Exception:
                    pass
            link.bind('<Button-1>', _open)
            # Copyright line
            _tk.Label(container, text=f'© {datetime.now().year} murathodja.com', anchor='center', justify='center').pack(anchor='center', pady=(0, 6), fill='x')
            # Close button
            btn = _tk.Button(container, text='Kapat', command=top.destroy)
            btn.pack(anchor='e', pady=(10, 0))
            # Size/position
            try:
                top.update_idletasks()
                w = max(420, top.winfo_reqwidth() + 40)
                h = top.winfo_reqheight() + 20
                x = max(0, self.winfo_rootx() + (self.winfo_width() - w)//2)
                y = max(0, self.winfo_rooty() + (self.winfo_height() - h)//3)
                top.geometry(f'{w}x{h}+{x}+{y}')
            except Exception:
                pass
        except Exception:
            pass

    def _return_focus_to_active(self) -> None:
        """Return keyboard focus to the most relevant control on the active view.
        Prefer the login username entry when on the Login screen."""
        try:
            # If an editable widget already has focus, keep it
            try:
                w = self.focus_get()
            except Exception:
                w = None
            try:
                from tkinter import Text as _Text
                if w is not None and not self._is_titlebar_widget(w) and isinstance(w, (tk.Entry, ttk.Entry, _Text)):
                    return
            except Exception:
                pass
            cur = getattr(self, 'current_frame_class', None)
            fr = self.frames.get(cur) if cur in self.frames else None
        except Exception:
            fr = None
        try:
            # Prefer explicit username entry on Login
            if fr is not None and getattr(cur, '__name__', '') == 'LoginFrame':
                ent = getattr(fr, 'entry_user', None)
                if ent:
                    try:
                        self.focus_force()
                    except Exception:
                        pass
                    try:
                        ent.focus_force()
                    except Exception:
                        pass
                    return
        except Exception:
            pass
        # Fallbacks
        try:
            # Try first focusable input in the current frame
            self._focus_first_entry_in_frame()
        except Exception:
            pass
        try:
            self.focus_force()
        except Exception:
            pass

    def _schedule_focus_restore(self) -> None:
        """Try restoring focus several times to overcome platform race conditions
        after popups/menus close under override-redirect."""
        delays = (10, 80, 160, 320)
        for d in delays:
            try:
                self.after(d, self._return_focus_to_active)
            except Exception:
                pass

    def _focus_first_entry_in_frame(self) -> None:
        try:
            cur = getattr(self, 'current_frame_class', None)
            fr = self.frames.get(cur) if cur in self.frames else None
            if not fr:
                return
            # DFS search for first Entry-like widget
            stack = list(fr.winfo_children())
            while stack:
                w = stack.pop(0)
                try:
                    if isinstance(w, (tk.Entry, ttk.Entry)):
                        w.focus_set()
                        return
                except Exception:
                    pass
                try:
                    stack.extend(w.winfo_children())
                except Exception:
                    pass
        except Exception:
            pass

    def _is_titlebar_widget(self, w) -> bool:
        try:
            if not w:
                return False
            tb = getattr(self, '_titlebar', None)
            if tb is None:
                return False
            # Walk up parents to see if this widget lives under titlebar
            cur = w
            while cur is not None:
                if cur is tb:
                    return True
                try:
                    cur = cur.nametowidget(cur.winfo_parent()) if cur.winfo_parent() else None
                except Exception:
                    break
            return False
        except Exception:
            return False

    def _start_focus_guard(self, duration_ms: int = 1200) -> None:
        end_time = time.time() + (duration_ms / 1000.0)

        def _tick():
            try:
                if time.time() >= end_time:
                    return
                w = None
                try:
                    w = self.focus_get()
                except Exception:
                    w = None
                # If focus is missing or on a non-editable widget (or titlebar), refocus
                bad = False
                try:
                    if w is None or self._is_titlebar_widget(w):
                        bad = True
                    else:
                        from tkinter import Text
                        if not isinstance(w, (tk.Entry, ttk.Entry, Text)):
                            bad = True
                except Exception:
                    bad = True
                if bad:
                    self._return_focus_to_active()
                self.after(60, _tick)
            except Exception:
                pass

        try:
            self.after(30, _tick)
        except Exception:
            pass

    def _macos_focus_fix(self) -> None:
        """Specific fixes for macOS borderless window focus issues."""
        try:
            if sys.platform != 'darwin':
                return
        except Exception:
            return
        # Force initial focus
        try:
            self.after(100, self._force_macos_focus)
        except Exception:
            pass
        # Set up more aggressive focus restoration
        try:
            self.bind("<Button-1>", self._on_click_restore_focus, add="+")
        except Exception:
            pass
        try:
            self.bind("<FocusIn>", self._on_focus_in, add="+")
        except Exception:
            pass
        # Menu-specific focus restoration
        try:
            if hasattr(self, '_title_menu_btn') and self._title_menu_btn:
                self._title_menu_btn.bind("<ButtonRelease-1>", self._after_menu_focus, add="+")  # type: ignore[attr-defined]
        except Exception:
            pass

    def _force_macos_focus(self) -> None:
        """Force focus to the main window and appropriate input field."""
        try:
            if sys.platform != 'darwin':
                return
        except Exception:
            return
        try:
            # If an editable widget already has focus, keep it
            try:
                w = self.focus_get()
            except Exception:
                w = None
            try:
                from tkinter import Text as _Text
                if w is not None and not self._is_titlebar_widget(w) and isinstance(w, (tk.Entry, ttk.Entry, _Text)):
                    return
            except Exception:
                pass
            # Ensure the window is focused
            self.focus_force()
            # Then focus the appropriate input field based on current frame
            current_frame = getattr(self, 'current_frame_class', None)
            frame_instance = self.frames.get(current_frame) if current_frame in self.frames else None
            if frame_instance and hasattr(frame_instance, 'entry_user'):
                # On login screen, focus username field
                try:
                    frame_instance.entry_user.focus_force()
                    return
                except Exception:
                    pass
            # Otherwise, find first focusable entry
            self._focus_first_entry_in_frame()
        except Exception:
            pass

    def _on_click_restore_focus(self, event) -> None:
        """Restore focus when user clicks anywhere in the window."""
        try:
            if sys.platform != 'darwin':
                return
        except Exception:
            return
        try:
            # Only restore if click is not on titlebar widgets
            w = getattr(event, 'widget', None)
            from tkinter import Text as _Text
            if w is not None and (isinstance(w, (tk.Entry, ttk.Entry, _Text))):
                return
            if not self._is_titlebar_widget(w):
                self.after(10, self._force_macos_focus)
        except Exception:
            pass

    def _on_focus_in(self, event) -> None:
        """Handle focus events to ensure inputs remain focusable."""
        try:
            if sys.platform != 'darwin':
                return
        except Exception:
            return
        try:
            # When window gains focus, ensure inputs are focusable
            self.after(50, self._ensure_inputs_focusable)
        except Exception:
            pass

    def _after_menu_focus(self, event) -> None:
        """Special focus restoration after menu interactions."""
        try:
            if sys.platform != 'darwin':
                return
        except Exception:
            return
        try:
            self.after(100, self._force_macos_focus)
            self.after(500, self._start_extended_focus_guard)
        except Exception:
            pass

    def _ensure_inputs_focusable(self) -> None:
        """Ensure all input fields are in a focusable state."""
        try:
            if sys.platform != 'darwin':
                return
        except Exception:
            return
        try:
            current_frame = getattr(self, 'current_frame_class', None)
            frame_instance = self.frames.get(current_frame) if current_frame in self.frames else None
            if frame_instance:
                # If we're on Login, aggressively ensure username/password are editable
                try:
                    if getattr(current_frame, '__name__', '') == 'LoginFrame':
                        ent_user = getattr(frame_instance, 'entry_user', None)
                        ent_pass = getattr(frame_instance, 'entry_pass', None)
                        if ent_user is not None:
                            self._force_enable_entry(ent_user)
                        if ent_pass is not None:
                            self._force_enable_entry(ent_pass)
                except Exception:
                    pass
                # Re-enable other entry widgets best-effort (non-destructive)
                for widget in list(frame_instance.winfo_children()):
                    self._reenable_entry_widgets(widget)
        except Exception:
            pass

    def _force_enable_entry(self, widget) -> None:
        """Force an entry to be editable regardless of prior state (Login only)."""
        try:
            # ttk.Entry: use state flags
            if isinstance(widget, ttk.Entry):
                try:
                    widget.state(['!disabled', '!readonly'])
                except Exception:
                    pass
            # tk.Entry: set state to normal
            elif isinstance(widget, tk.Entry):
                try:
                    widget.configure(state='normal')
                except Exception:
                    pass
        except Exception:
            pass

    def _reenable_entry_widgets(self, widget) -> None:
        """Recursively re-enable entry widgets (no-op if disabled)."""
        try:
            if isinstance(widget, ttk.Entry):
                # Non-destructively try to clear disabled state; don't force readonly here
                try:
                    if widget.instate(('disabled',)):
                        widget.state(['!disabled'])
                except Exception:
                    pass
            elif isinstance(widget, tk.Entry):
                try:
                    if widget.cget('state') == 'disabled':
                        widget.configure(state='normal')
                except Exception:
                    pass
            try:
                widget.update_idletasks()
            except Exception:
                pass
            # Recurse into children if any
            try:
                for child in widget.winfo_children():
                    self._reenable_entry_widgets(child)
            except Exception:
                pass
        except Exception:
            pass

    def _start_extended_focus_guard(self, duration_ms: int = 2000) -> None:
        """Extended focus guard specifically for macOS menu issues."""
        try:
            if sys.platform != 'darwin':
                return
        except Exception:
            return
        end_time = time.time() + (duration_ms / 1000.0)

        def _tick():
            try:
                if time.time() >= end_time:
                    return
                # Check if focus is lost or on non-input widgets
                try:
                    focused_widget = self.focus_get()
                except Exception:
                    focused_widget = None
                from tkinter import Text as _Text
                # If already on an editable widget, don't touch it
                if focused_widget is not None and not self._is_titlebar_widget(focused_widget) and isinstance(focused_widget, (tk.Entry, ttk.Entry, _Text)):
                    self.after(100, _tick)
                    return
                should_refocus = (
                    focused_widget is None or
                    self._is_titlebar_widget(focused_widget) or
                    not isinstance(focused_widget, (tk.Entry, ttk.Entry, _Text))
                )
                if should_refocus:
                    self._force_macos_focus()
                self.after(100, _tick)
            except Exception:
                pass

        try:
            self.after(50, _tick)
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
                        apply_button_margins(frame, padx=2, pady=2)
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
        # Fallback: occupy full screen work area
        try:
            self.update_idletasks()
            w = self.winfo_screenwidth()
            h = self.winfo_screenheight()
            self.geometry(f"{w}x{h}+0+0")
        except Exception:
            pass

    def _enable_borderless_chrome(self) -> None:
        """Make the main window borderless and add a custom draggable title bar
        with minimize and close buttons. Keeps the window maximized."""
        # Enable borderless mode
        try:
            self.overrideredirect(True)
        except Exception:
            return

        try:
            # Force taskbar registration on Windows even when borderless
            self._force_taskbar_register()
        except Exception:
            pass
        titlebar = tk.Frame(self, highlightthickness=0)
        # Keep title bar dimensions and font constant (not scaled)
        try:
            if not hasattr(self, '_titlebar_font'):
                base_family = tkfont.nametofont('TkDefaultFont').actual('family')
                # Slightly larger fixed font for title bar
                self._titlebar_font = tkfont.Font(family=base_family, size=24, weight='bold')
            # Taller fixed height to prevent jumping on content changes
            titlebar.configure(height=56)
            titlebar.pack_propagate(False)
        except Exception:
            pass
        try:
            # Ensure it appears at the very top, above the main container
            titlebar.pack(fill='x', side='top', before=getattr(self, 'container', None))
        except Exception:
            titlebar.pack(fill='x', side='top')

        # Common paddings
        pad_x = 16
        gap_x = 12

        # Simple text menu at the far left
        menu_btn = tk.Label(titlebar, text='☰')
        try:
            menu_btn.configure(font=getattr(self, '_titlebar_font', None))
        except Exception:
            pass
        menu_btn.pack(side='left', padx=(pad_x, 8), pady=8)
        try:
            menu_btn.configure(takefocus=0)
        except Exception:
            pass
        def _post_menu(event=None):
            try:
                self._ensure_title_popup_menu()
                # Ensure menu close events will restore focus reliably
                try:
                    self._wire_menu_close_focus(self._title_popup_menu)  # type: ignore[attr-defined]
                except Exception:
                    pass
                # Visual pressed feedback handled by press/release handlers
                
                self._title_popup_menu.tk_popup(event.x_root, event.y_root + 30)  # type: ignore[attr-defined]
            finally:
                try:
                    self._title_popup_menu.grab_release()  # type: ignore[attr-defined]
                except Exception:
                    pass
                # Ensure any global grabs are released and keyboard focus returns
                try:
                    self.grab_release()
                except Exception:
                    pass
                try:
                    # Immediately restore and re-enable inputs, then schedule retries
                    try:
                        self._force_macos_focus()
                    except Exception:
                        pass
                    try:
                        self._ensure_inputs_focusable()
                    except Exception:
                        pass
                    self._schedule_focus_restore()
                    self._start_focus_guard(800)
                    # On some WMs, reapplying borderless helps after menu closes
                    try:
                        self._reapply_borderless()
                    except Exception:
                        pass
                except Exception:
                    pass
        # Add hover/press color handling to menu label
        try:
            menu_btn._normal_fg = getattr(self, '_title_fg', 'black')  # type: ignore[attr-defined]
            menu_btn._hover_fg = getattr(self, '_title_fg_hover', '#333333')  # type: ignore[attr-defined]
            menu_btn._pressed_fg = getattr(self, '_title_fg_pressed', '#222222')  # type: ignore[attr-defined]
            def _m_enter(_e):
                try:
                    menu_btn.configure(fg=getattr(menu_btn, '_hover_fg', menu_btn.cget('fg')))
                except Exception:
                    pass
            def _m_leave(_e):
                try:
                    menu_btn.configure(fg=getattr(menu_btn, '_normal_fg', menu_btn.cget('fg')))
                except Exception:
                    pass
            def _m_press(_e):
                try:
                    menu_btn.configure(fg=getattr(menu_btn, '_pressed_fg', menu_btn.cget('fg')))
                except Exception:
                    pass
            def _m_release(_e):
                try:
                    w = menu_btn.winfo_containing(_e.x_root, _e.y_root)
                    if w is menu_btn:
                        menu_btn.configure(fg=getattr(menu_btn, '_hover_fg', menu_btn.cget('fg')))
                        _post_menu(_e)
                    else:
                        menu_btn.configure(fg=getattr(menu_btn, '_normal_fg', menu_btn.cget('fg')))
                except Exception:
                    pass
            menu_btn.bind('<Enter>', _m_enter)
            menu_btn.bind('<Leave>', _m_leave)
            menu_btn.bind('<ButtonPress-1>', _m_press)
            menu_btn.bind('<ButtonRelease-1>', _m_release)
        except Exception:
            pass

        # Optional app icon (to the right of menu)
        icon_container = tk.Frame(titlebar, bd=0, highlightthickness=0)
        icon_container.pack(side='left', padx=(0, 8))
        self._tb_icon_img = None  # type: ignore[attr-defined]
        try:
            png = resource_path('app.png')
            if os.path.exists(png):
                img = tk.PhotoImage(file=png)
                # Downscale if too large for the title bar
                try:
                    iw, ih = img.width(), img.height()
                    if iw > 24 or ih > 24:
                        fx = max(1, iw // 24)
                        fy = max(1, ih // 24)
                        img = img.subsample(fx, fy)
                except Exception:
                    pass
                self._tb_icon_img = img  # keep reference
                tk.Label(icon_container, image=img, bd=0, highlightthickness=0).pack(side='left')
        except Exception:
            pass

        # Title text (label-like; blends with bar)
        title = tk.Label(titlebar, text=APP_NAME)
        try:
            title.configure(font=getattr(self, '_titlebar_font', None))
        except Exception:
            pass
        title.pack(side='left', padx=(8, pad_x), pady=8)
# Button row (labels behaving like buttons)
        btn_row = tk.Frame(titlebar, bd=0, highlightthickness=0)
        btn_row.pack(side='right', padx=pad_x)

        def _mk_text_btn(parent, text, cmd):
            lbl = tk.Label(parent, text=text, cursor='hand2')
            try:
                lbl.configure(font=getattr(self, '_titlebar_font', None))
            except Exception:
                pass
            # Use widget-local normal/hover fg to avoid stale globals
            lbl._normal_fg = getattr(self, '_title_fg', 'black')  # type: ignore[attr-defined]
            lbl._hover_fg = getattr(self, '_title_fg_hover', '#333333')  # type: ignore[attr-defined]
            lbl._pressed_fg = getattr(self, '_title_fg_pressed', '#222222')  # type: ignore[attr-defined]
            def on_enter(_e):
                try:
                    lbl.configure(fg=getattr(lbl, '_hover_fg', lbl.cget('fg')))
                except Exception:
                    pass
            def on_leave(_e):
                try:
                    lbl.configure(fg=getattr(lbl, '_normal_fg', lbl.cget('fg')))
                except Exception:
                    pass
            def on_press(_e):
                try:
                    lbl.configure(fg=getattr(lbl, '_pressed_fg', lbl.cget('fg')))
                except Exception:
                    pass
            def on_release(_e):
                try:
                    w = lbl.winfo_containing(_e.x_root, _e.y_root)
                    if w is lbl:
                        lbl.configure(fg=getattr(lbl, '_hover_fg', lbl.cget('fg')))
                        try:
                            cmd()
                        except Exception:
                            pass
                    else:
                        lbl.configure(fg=getattr(lbl, '_normal_fg', lbl.cget('fg')))
                except Exception:
                    pass
            lbl.bind('<Enter>', on_enter)
            lbl.bind('<Leave>', on_leave)
            lbl.bind('<ButtonPress-1>', on_press)
            lbl.bind('<ButtonRelease-1>', on_release)
            # Do not take keyboard focus
            try:
                lbl.configure(takefocus=0)
            except Exception:
                pass
            return lbl

        # Close at far right; minimize to its left
        b_close = _mk_text_btn(btn_row, '×', self.destroy)
        b_close.pack(side='right', padx=(0, 0), pady=8)
        b_min = _mk_text_btn(btn_row, '-', self._safe_iconify)
        # Add explicit space between minimize and close
        b_min.pack(side='right', padx=(0, gap_x), pady=8)
        # Avoid stealing keyboard focus from content widgets
        try:
            for w in (titlebar, title, btn_row, b_close, b_min, icon_container):
                w.configure(takefocus=0)
            # Keep references for theming/dragging
            self._titlebar = titlebar            # type: ignore[attr-defined]
            self._title_label = title            # type: ignore[attr-defined]
            self._title_min = b_min              # type: ignore[attr-defined]
            self._title_close = b_close          # type: ignore[attr-defined]
            self._title_menu_btn = menu_btn      # type: ignore[attr-defined]
        except Exception:
            pass

        # Drag to move
        pos = {"x": 0, "y": 0}

        def _start(e):
            pos["x"], pos["y"] = e.x, e.y

        def _drag(e):
            try:
                self.geometry(f"+{self.winfo_x() + e.x - pos['x']}+{self.winfo_y() + e.y - pos['y']}")
            except Exception:
                pass

        for w in (titlebar, title):
            w.bind('<Button-1>', _start)
            w.bind('<B1-Motion>', _drag)

        # Hover colors are handled by per-widget enter/leave bindings; avoid
        # global motion hooks which can interfere with focus on some platforms.

        # Keep maximized size in borderless mode and make sure app has focus
        try:
            self.update_idletasks()
            w = self.winfo_screenwidth()
            h = self.winfo_screenheight()
            self.geometry(f"{w}x{h}+0+0")
            self.minsize(w, h)
            # Activate window and directly focus the active frame's best input
            try:
                # Topmost toggle helps the WM activate the window in OR mode
                self.attributes('-topmost', True)
                self.attributes('-topmost', False)
                # Force window focus, then reinforce on the active entry
                try:
                    self.focus_force()
                except Exception:
                    pass
            except Exception:
                pass
            # Directly focus the active frame's best input (e.g., login username)
            try:
                cur = getattr(self, 'current_frame_class', None)
                fr = self.frames.get(cur) if cur in self.frames else None
                ent = getattr(fr, 'entry_user', None) if fr is not None else None
                if ent:
                    try:
                        ent.focus_force()
                    except Exception:
                        pass
                else:
                    self.after(50, self._schedule_focus_restore)
            except Exception:
                self.after(50, self._schedule_focus_restore)
        except Exception:
            pass

        # On some platforms, deiconify drops overrideredirect; reapply
        try:
            self.bind('<Map>', lambda _e: self._reapply_borderless())
        except Exception:
            pass

        # Apply initial title bar styling based on theme
        try:
            self._style_titlebar()
        except Exception:
            pass
        # Ensure Windows taskbar registers this window even when borderless
        try:
            self.after(300, self._force_taskbar_register)
        except Exception:
            pass

        # Start a short-lived guard to keep focus stable after enabling
        try:
            self._start_focus_guard(1500)
        except Exception:
            pass

        # Enhanced macOS focus handling
        try:
            self._macos_focus_fix()
        except Exception:
            pass

    def _safe_iconify(self) -> None:
        """Minimize even when in override-redirect (borderless) mode by
        temporarily disabling it, then iconifying. Reapplied on <Map>."""
        if not getattr(self, 'use_borderless', False):
            try:
                self.iconify()
            except Exception:
                pass
            return
        try:
            self.overrideredirect(False)
        except Exception:
            pass
        # On Windows, ensure the window shows in the taskbar when minimized
        try:
            self._ensure_taskbar_icon()
        except Exception:
            pass
        # Minimize the taskbar anchor as well; restoring it will trigger main restore
        try:
            anchor = getattr(self, '_taskbar_anchor', None)
            if anchor is not None:
                anchor.iconify()
        except Exception:
            pass
        try:
            self.iconify()
        except Exception:
            # If iconify fails, reapply borderless immediately
            try:
                self._reapply_borderless()
            except Exception:
                pass

    def _create_taskbar_anchor(self) -> None:
        """Create a tiny, transparent normal window to provide a taskbar icon
        on Windows when running the main window in borderless mode.
        Safe no-op on other platforms."""
        try:
            if sys.platform != 'win32':
                return
            if hasattr(self, '_taskbar_anchor') and getattr(self, '_taskbar_anchor'):
                return
            anc = tk.Toplevel(self)
            anc.overrideredirect(False)
            try:
                anc.wm_attributes('-toolwindow', False)
            except Exception:
                pass
            try:
                anc.wm_attributes('-alpha', 0.0)
            except Exception:
                pass
            try:
                anc.iconbitmap(default=getattr(self, '_app_ico_path', resource_path('app.ico')))
            except Exception:
                pass
            try:
                anc.title(self.title())
            except Exception:
                pass
            anc.geometry('1x1+0+0')
            anc.deiconify()
            anc.lower()
            # When the anchor is restored from the taskbar, restore the main window
            def _restore_main(_e=None):
                try:
                    self.deiconify()
                except Exception:
                    pass
                try:
                    self._reapply_borderless()
                except Exception:
                    pass
                try:
                    self.lift()
                except Exception:
                    pass
                try:
                    anc.lower()
                except Exception:
                    pass
            try:
                anc.bind('<Map>', _restore_main, add='+')
                anc.bind('<FocusIn>', _restore_main, add='+')
            except Exception:
                pass
            self._taskbar_anchor = anc  # type: ignore[attr-defined]
        except Exception:
            pass

    def _reapply_borderless(self) -> None:
        if not getattr(self, 'use_borderless', False):
            return
        try:
            self.overrideredirect(True)
        except Exception:
            pass
        # Ensure we keep maximized/fullscreen-like geometry
        try:
            self.update_idletasks()
            w = self.winfo_screenwidth()
            h = self.winfo_screenheight()
            self.geometry(f"{w}x{h}+0+0")
        except Exception:
            pass

    def _reapply_borderless(self) -> None:
        """Reapply override-redirect and geometry, and reassert taskbar flags."""
        if not getattr(self, 'use_borderless', False):
            return
        try:
            self.overrideredirect(True)
        except Exception:
            pass
        # Keep maximized/fullscreen-like geometry
        try:
            self.update_idletasks()
            w = self.winfo_screenwidth()
            h = self.winfo_screenheight()
            self.geometry(f"{w}x{h}+0+0")
        except Exception:
            pass
        # Ensure Windows taskbar shows this window
        try:
            self.wm_attributes('-toolwindow', False)
        except Exception:
            pass
        try:
            self._ensure_taskbar_icon()
        except Exception:
            pass

    def _force_taskbar_register(self) -> None:
        """Force Explorer to register the window in the taskbar on Windows."""
        try:
            if sys.platform != 'win32':
                return
            # Briefly withdraw/deiconify to force taskbar registration
            self.withdraw()
            self.after(50, lambda: (self.deiconify(), self._ensure_taskbar_icon()))
        except Exception:
            pass
    def _ensure_taskbar_icon(self) -> None:
        """On Windows, make sure the window uses APPWINDOW style so it appears
        on the taskbar when minimized. Safe no-op on other platforms."""
        try:
            if sys.platform != 'win32':
                return
            import ctypes
            from ctypes import wintypes
            GWL_EXSTYLE = -20
            WS_EX_TOOLWINDOW = 0x00000080
            WS_EX_APPWINDOW = 0x00040000
            SWP_NOSIZE = 0x0001
            SWP_NOMOVE = 0x0002
            SWP_NOZORDER = 0x0004
            SWP_FRAMECHANGED = 0x0020
            hwnd = self.winfo_id()
            user32 = ctypes.windll.user32
            get_long = user32.GetWindowLongW
            set_long = user32.SetWindowLongW
            set_pos = user32.SetWindowPos
            get_long.restype = ctypes.c_long
            get_long.argtypes = [wintypes.HWND, ctypes.c_int]
            set_long.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_long]
            set_pos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint]
            ex = get_long(hwnd, GWL_EXSTYLE)
            ex &= ~WS_EX_TOOLWINDOW
            ex |= WS_EX_APPWINDOW
            set_long(hwnd, GWL_EXSTYLE, ex)
            # Notify the window manager that styles changed
            set_pos(hwnd, None, 0, 0, 0, 0, SWP_NOSIZE | SWP_NOMOVE | SWP_NOZORDER | SWP_FRAMECHANGED)
        except Exception:
            pass
        # Re-apply titlebar colors for current theme after remap
        try:
            self._style_titlebar()
        except Exception:
            pass
        # Nudge focus back to UI after restore
        try:
            try:
                self.focus_force()
            except Exception:
                pass
            self._schedule_focus_restore()
            self._start_focus_guard(1000)
        except Exception:
            pass

    def _ensure_title_popup_menu(self) -> None:
        try:
            if hasattr(self, '_title_popup_menu') and self._title_popup_menu:  # type: ignore[attr-defined]
                return
        except Exception:
            pass
        m = tk.Menu(self, tearoff=False)
        try:
            # Force light look for this popup regardless of app theme
            m.configure(bg='white', fg='black', activebackground='#f0f0f0', activeforeground='black', disabledforeground='#9a9a9a')
            m.configure(borderwidth=0, relief='flat', activeborderwidth=0, highlightthickness=0)
        except Exception:
            pass
        m.add_command(label='Hakkında…', command=self.show_about)
        m.add_separator()
        m.add_command(label='Ayarlar', command=self._open_settings_from_title_menu)
        m.add_command(label='Çıkış', command=self.destroy)
        self._title_popup_menu = m  # type: ignore[attr-defined]
        # Bind close/unmap to restore focus strongly
        try:
            self._wire_menu_close_focus(m)
        except Exception:
            pass

    def _open_settings_from_title_menu(self) -> None:
        try:
            if SettingsFrame is not None:
                self.show_frame(SettingsFrame)  # type: ignore[arg-type]
            else:
                self.show_placeholder('Ayarlar')
        except Exception:
            pass

    def _wire_menu_close_focus(self, menu: tk.Menu) -> None:
        """Bind menu close/unmap events to restore focus and reapply borderless."""
        try:
            def _after_close(_e=None):
                try:
                    # Reapply OR on some platforms to regain focusability
                    try:
                        self._reapply_borderless()
                    except Exception:
                        pass
                    # Force and guard focus back to inputs
                    try:
                        self._force_macos_focus()
                    except Exception:
                        pass
                    self._schedule_focus_restore()
                    self._start_focus_guard(1000)
                except Exception:
                    pass
            # Unmap (menu dismissed), FocusOut (lost focus), Escape to close
            try:
                menu.bind('<Unmap>', _after_close, add='+')
            except Exception:
                pass
            try:
                menu.bind('<FocusOut>', _after_close, add='+')
            except Exception:
                pass
            try:
                menu.bind('<Escape>', _after_close, add='+')
            except Exception:
                pass
            # Also after any click inside menu (selection), when released
            try:
                menu.bind('<ButtonRelease-1>', _after_close, add='+')
            except Exception:
                pass
        except Exception:
            pass

    def _style_titlebar(self) -> None:
        """Apply theme-aware colors to the custom title bar and its controls."""
        tb = getattr(self, '_titlebar', None)
        if not tb:
            return
        theme = getattr(self, 'saved_theme', 'light') or 'light'
        t = str(theme).lower()
        if 'dark' in t:
            bar_bg = '#1e2023'
            fg = 'white'
            fg_hover = '#d0d0d0'
            fg_pressed = '#bbbbbb'
        else:
            bar_bg = 'white'
            fg = 'black'
            fg_hover = '#333333'
            fg_pressed = '#000000'
        self._title_fg = fg
        self._title_fg_hover = fg_hover
        self._title_fg_pressed = fg_pressed
        try:
            tb.configure(bg=bar_bg)
            for w in (getattr(self, '_title_label', None), getattr(self, '_title_min', None), getattr(self, '_title_close', None), getattr(self, '_title_menu_btn', None)):
                if w:
                    w.configure(bg=bar_bg, fg=fg)
                    # Update per-widget normal/hover colors
                    try:
                        w._normal_fg = fg  # type: ignore[attr-defined]
                        w._hover_fg = fg_hover  # type: ignore[attr-defined]
                        w._pressed_fg = fg_pressed  # type: ignore[attr-defined]
                    except Exception:
                        pass
            if hasattr(self, '_tb_icon_img'):
                for ch in tb.winfo_children():
                    try:
                        if isinstance(ch, tk.Frame):
                            ch.configure(bg=bar_bg)
                            for cc in ch.winfo_children():
                                try:
                                    cc.configure(bg=bar_bg)
                                except Exception:
                                    pass
                    except Exception:
                        pass
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
        # Re-style custom titlebar to blend with theme
        try:
            self._style_titlebar()
        except Exception:
            pass
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
            # if perms is None:
            #     print(f"[perm] user={username} role={role} -> ALL")
            # else:
            #     print(f"[perm] user={username} role={role} -> {sorted(list(perms))}")
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
        self.card_container.place(relx=0.5, rely=0.5, anchor='center', width=560, height=460)

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

        # Use classic tk.Button for full control of bg/fg across themes
        self.btn_login = tk.Button(inner, text='Giris Yap', command=self.do_login, relief='flat', bd=0, highlightthickness=0, padx=20, pady=10)
        self.btn_login.pack(pady=(8, 6))
        try:
            self._apply_login_button_theme()
        except Exception:
            pass

        # Ensure the login card is tall enough for current theme/font
        try:
            def _resize_card():
                try:
                    inner.update_idletasks()
                    req_h = inner.winfo_reqheight()
                    # Add slack for borders/padding
                    target_h = max(460, req_h + 28)
                    self.card_container.configure(height=target_h)
                except Exception:
                    pass
            # run two passes to catch late style application
            self.after(0, _resize_card)
            self.after(120, _resize_card)
        except Exception:
            pass


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
            try:
                self.controller.focus_force()
            except Exception:
                pass
            self.entry_user.focus_force()
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
        try:
            self._apply_login_button_theme()
        except Exception:
            pass
    
    def _apply_login_button_theme(self) -> None:
        try:
            theme = getattr(self.controller, 'saved_theme', None) or 'light'
            low = str(theme).lower()
            if 'dark' in low or 'koyu' in low:
                bbg, babg, bfg = '#f0f0f0', '#e6e6e6', '#000000'
            else:
                bbg, babg, bfg = '#1e2023', '#2a2f33', '#ffffff'
            # Apply directly to classic tk.Button for reliable colors
            if hasattr(self, 'btn_login') and self.btn_login:
                try:
                    self.btn_login.configure(bg=bbg, fg=bfg, activebackground=babg, activeforeground=bfg)
                except Exception:
                    pass
        except Exception:
            pass



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
        # Subtle border: thin highlight line instead of thick 3D relief
        try:
            self.configure(bd=0, relief='flat', highlightthickness=1, highlightbackground='#c8cdd4', highlightcolor='#c8cdd4')
        except Exception:
            pass
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
        # Update thin border color per theme for better contrast
        try:
            line = '#4a4f55' if theme == 'dark' else '#c8cdd4'
            self.configure(highlightbackground=line, highlightcolor=line)
        except Exception:
            pass


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
        user_holder.pack(pady=(0, 10), anchor='center')
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
                    card.configure(width=620, height=h)
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
                    row_h = max(btn_h, lbl_h) + 24
                    header_row.grid_rowconfigure(0, minsize=row_h)
                    inner.update_idletasks()
                    h = inner.winfo_reqheight() + padding_val * 2 
                    if h < 92:
                        h = 80
                    card.configure(height=h)
                except Exception:
                    pass
            self.after(80, _fit_row)
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
        self.user_label.grid(row=0, column=0, padx=12, pady=20, sticky='nsw')
        logout_btn = ttk.Button(header_row, text="Çıkış yap", command=self.controller.logout, style='Logout.TButton', padding=(16,2))
        # Use default ttk font for logout; MenuButtonFont is only for menu tiles
        logout_btn.grid(row=0, column=1, padx=12, pady=20, sticky='nse')
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
                self.logout_btn.configure(style='Logout.TButton', padding=(16,2))
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
       
        actions = get_main_actions()
        handlers = build_main_handlers(controller)
        super().__init__(parent, controller, "Kasiyer Ekranı", actions, handlers)


class AccountingFrame(RoleFrame):
    def __init__(self, parent: tk.Misc, controller: App) -> None:
        actions = get_main_actions()
        handlers = build_main_handlers(controller)
        super().__init__(parent, controller, "Muhasebe Paneli", actions, handlers)


class MemberFrame(RoleFrame):
    def __init__(self, parent: tk.Misc, controller: App) -> None:
       
        actions = get_main_actions()
        handlers = build_main_handlers(controller)
        super().__init__(parent, controller, "Üye Paneli", actions, handlers)


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
