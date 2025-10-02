import tkinter as tk

def _contrast_fill(widget: tk.Misc, bg: str) -> tuple[str, str]:
    """Return (normal_fill, hover_fill) for given background color name.
    Chooses white on dark backgrounds and dark gray on light backgrounds.
    """
    try:
        r16, g16, b16 = widget.winfo_rgb(bg)
        # Normalize to 0-1
        r = r16 / 65535.0
        g = g16 / 65535.0
        b = b16 / 65535.0
        # Perceived luminance (sRGB approximation)
        lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
    except Exception:
        lum = 1.0  # assume light
    if lum < 0.5:  # dark background
        return ("#FFFFFF", "#EEEEEE")
    else:  # light background
        return ("#333333", "#000000")

def make_back_arrow(parent: tk.Misc, command) -> tk.Canvas:
    """Create a 50x50 back arrow canvas acting like a button.
    The canvas draws a left arrow and calls `command` on click.
    """
    size = 50
    try:
        bg = parent.cget('bg')
    except Exception:
        bg = 'white'
    normal_fill, hover_fill = _contrast_fill(parent, bg)

    c = tk.Canvas(parent, width=size, height=size, highlightthickness=0, bg=bg)
    # Draw a simple left arrow
    arrow = c.create_polygon(
        34, 10,
        16, 25,
        34, 40,
        34, 32,
        24, 25,
        34, 18,
        fill=normal_fill, outline='')
    # Keep refs for theme refresh
    try:
        c._arrow_id = arrow  # type: ignore[attr-defined]
        c._arrow_base_bg = bg  # type: ignore[attr-defined]
        c._arrow_normal_fill = normal_fill  # type: ignore[attr-defined]
        c._arrow_hover_fill = hover_fill  # type: ignore[attr-defined]
    except Exception:
        pass

    # Hover effect
    def _on_enter(_e=None):
        try:
            hf = getattr(c, '_arrow_hover_fill', hover_fill)
        except Exception:
            hf = hover_fill
        c.itemconfig(arrow, fill=hf)

    def _on_leave(_e=None):
        try:
            nf = getattr(c, '_arrow_normal_fill', normal_fill)
        except Exception:
            nf = normal_fill
        c.itemconfig(arrow, fill=nf)

    c.bind('<Enter>', _on_enter)
    c.bind('<Leave>', _on_leave)
    # Extra guards so it never sticks in hover color
    c.bind('<ButtonRelease-1>', _on_leave)
    c.bind('<FocusOut>', _on_leave)
    def _on_click(_e=None):
        try:
            if callable(command):
                command()
        except Exception:
            pass
    c.bind('<Button-1>', _on_click)
    c.configure(cursor='hand2')
    # Expose a refresh hook for theme changes
    try:
        def _refresh_theme(_e=None):
            refresh_back_arrow(c)
        c.refresh_theme = _refresh_theme  # type: ignore[attr-defined]
    except Exception:
        pass
    return c


def refresh_back_arrow(canvas: tk.Canvas) -> None:
    """Recompute back arrow canvas colors based on parent background."""
    try:
        parent = canvas.master
        try:
            bg = parent.cget('bg')
        except Exception:
            bg = canvas.cget('bg')
        normal_fill, hover_fill = _contrast_fill(parent, bg)
        try:
            canvas.configure(bg=bg)
        except Exception:
            pass
        try:
            arrow_id = getattr(canvas, '_arrow_id', None)
            if arrow_id:
                canvas.itemconfig(arrow_id, fill=normal_fill)
        except Exception:
            pass
        try:
            canvas._arrow_normal_fill = normal_fill  # type: ignore[attr-defined]
            canvas._arrow_hover_fill = hover_fill    # type: ignore[attr-defined]
        except Exception:
            pass
    except Exception:
        pass

def refresh_all_back_arrows(root: tk.Misc) -> None:
    """Refresh all back-arrow Canvas widgets in the widget tree."""
    try:
        def _walk(w: tk.Misc):
            try:
                children = w.winfo_children()
            except Exception:
                children = []
            for c in children:
                try:
                    if isinstance(c, tk.Canvas) and getattr(c, '_arrow_id', None):
                        refresh_back_arrow(c)  # type: ignore[arg-type]
                except Exception:
                    pass
                _walk(c)
        _walk(root)
    except Exception:
        pass


from typing import Optional

# Fixed card surface accent colors (light/dark modes)
CARD_BG_LIGHT = '#f0f0f0'
CARD_BG_DARK = '#2a2f33'


class ThemeManager:
    """Single entry point to apply the selected theme consistently.
    Usage: ThemeManager.apply_all(root, theme_name, scale, base_pt)
    """
    @staticmethod
    def apply_all(root: tk.Misc, theme_name: Optional[str], scale: Optional[float], base_pt: Optional[int]) -> None:
        try:
            # 1) Base theme + fonts + ttk palette
            apply_theme(root, scale=scale, theme_name=theme_name, base_pt=base_pt)
        except Exception:
            pass
        try:
            # 2) Ensure card surfaces use fixed accent colors for current mode
            refresh_card_tints(root)
        except Exception:
            pass
        try:
            # 3) Force controls inside cards to match card background exactly
            ensure_card_control_backgrounds(root)
        except Exception:
            pass
        try:
            # 4) Enforce contrasting text colors for classic widgets based on bg
            ensure_contrast_text_colors(root)
        except Exception:
            pass
        try:
            # 5) Adjust ttk styles' foregrounds to contrast with their bg
            ensure_ttk_contrast_styles(root)
        except Exception:
            pass
        try:
            # 6) Refresh any back-arrow canvases so their icon color matches new bg
            refresh_all_back_arrows(root)
        except Exception:
            pass
        try:
            # 7) Per-widget contrast for ttk.Label instances
            ensure_ttk_label_contrast(root)
        except Exception:
            pass

def fix_mojibake_text(s: Optional[str]) -> Optional[str]:
    """Best‑effort fix for UTF‑8 text that was mis‑decoded as Latin‑1/Windows‑1252.
    If conversion fails, returns the original string.
    """
    try:
        if not isinstance(s, str):
            return s
        # Try the common path: original UTF‑8 bytes were decoded as latin‑1
        return s.encode('latin-1').decode('utf-8')
    except Exception:
        return s


def apply_theme(root: tk.Tk, scale: Optional[float] = None, theme_name: Optional[str] = None, base_pt: Optional[int] = None) -> None:
    """Apply a larger, cleaner Tk/ttk theme for readability.
    - Increases default fonts
    - Pads buttons/entries
    - Enlarges Treeview rows and headings
    """
    # Only scale fonts (do NOT use tk scaling so widget geometry stays same)
    try:
        import tkinter.font as tkfont
        try:
            s = float(scale) if scale else 1.0
            if s <= 0:
                s = 1.0
        except Exception:
            s = 1.0
        # Base font point sizes (unscaled). Allow override via base_pt.
        try:
            bpt = int(base_pt) if base_pt is not None else None
        except Exception:
            bpt = None
        b_default = bpt if bpt and bpt > 6 else 12
        b_heading = max(8, b_default + 2)
        b_menu = max(8, b_default + 2)
        b_tooltip = b_default
        # Menu buttons use a dedicated named font and are excluded from global base size
        base = {
            'TkDefaultFont': b_default,
            'TkTextFont': b_default,
            'TkMenuFont': b_menu,
            'TkHeadingFont': b_heading,
            'TkTooltipFont': b_tooltip,
            'MenuButtonFont': 46,
        }
        for fname, bsize in base.items():
            try:
                new_size = max(8, int(round(bsize * s)))
                if fname == 'MenuButtonFont':
                    # Use pixel sizing for reliability across platforms
                    try:
                        tkfont.nametofont('MenuButtonFont').configure(size=-new_size, weight='bold')
                    except Exception:
                        tkfont.Font(name='MenuButtonFont', size=-new_size, weight='bold')
                else:
                    f = tkfont.nametofont(fname)
                    # Preserve family, update size and weight for Heading
                    if fname == 'TkHeadingFont':
                        f.configure(size=new_size, weight='bold')
                    else:
                        f.configure(size=new_size)
            except Exception:
                pass
        # Apply defaults to classic Tk widgets too
        try:
            app_font = tkfont.nametofont('TkDefaultFont')
            root.option_add('*Font', app_font)
            root.option_add('*Button.Font', app_font)
            root.option_add('*Label.Font', app_font)
            root.option_add('*Entry.Font', app_font)
        except Exception:
            pass
    except Exception:
        pass

    try:
        from tkinter import ttk
        style = ttk.Style(root)
        # Use available theme; keep current if custom
        try:
            themes = style.theme_names()
            # Handle special virtual themes: 'dark' / 'light'
            if theme_name and theme_name.lower() in ('dark', 'koyu'):
                # Base on a modern theme, then recolor
                base = 'clam' if 'clam' in themes else style.theme_use()
                style.theme_use(base)
                _apply_dark_palette(style, root)
            elif theme_name and theme_name.lower() in ('light', 'acik', 'açık'):
                base = 'clam' if 'clam' in themes else style.theme_use()
                style.theme_use(base)
                _apply_light_palette(style, root)
            else:
                if theme_name and theme_name in themes:
                    style.theme_use(theme_name)
                # If current theme is too old, pick a modern default
                if style.theme_use() == 'classic':
                    for th in ('clam', 'default', 'alt'):
                        if th in themes:
                            style.theme_use(th)
                            break
        except Exception:
            pass

        # Buttons
        style.configure('TButton', padding=(12, 2))
        style.map('TButton', relief=[('pressed', 'sunken'), ('!pressed', 'raised')])
        # Notebook tabs
        style.configure('TNotebook.Tab', padding=(14, 10))
        # Treeview
        style.configure('Treeview', rowheight=32)
        # Larger heading font for treeviews
        try:
            import tkinter.font as tkfont
            tv_head = tkfont.Font(family=tkfont.nametofont('TkHeadingFont').actual('family'), size=14, weight='bold')
            style.configure('Treeview.Heading', padding=(8, 8), font=tv_head)
        except Exception:
            style.configure('Treeview.Heading', padding=(8, 8))
        # After applying palette, recolor existing classic Tk widgets so changes are visible immediately
        try:
            _recolor_existing_classic_widgets(root, theme_name)
        except Exception:
            pass
        # Then, unify ttk control backgrounds for card containers
        try:
            _apply_card_control_styles(root, theme_name)
        except Exception:
            pass
    except Exception:
        pass

def _apply_dark_palette(style, root: tk.Tk) -> None:
    bg = '#1e1e1e'
    fg = '#eaeaea'
    accent = '#2d2d2d'
    sel_bg = '#094771'
    sel_fg = '#ffffff'
    # Tk widget defaults
    try:
        root.configure(bg=bg)
        # Generic defaults
        root.option_add('*Background', bg)
        root.option_add('*Foreground', fg)
        # tk.Entry
        root.option_add('*Entry.Background', accent)
        root.option_add('*Entry.Foreground', fg)
        root.option_add('*Entry.InsertBackground', fg)
        root.option_add('*Entry.SelectBackground', sel_bg)
        root.option_add('*Entry.SelectForeground', sel_fg)
        # tk.Button (light button on dark bg)
        root.option_add('*Button.Background', '#f0f0f0')
        root.option_add('*Button.Foreground', '#000000')
        root.option_add('*Button.ActiveBackground', '#e6e6e6')
        root.option_add('*Button.ActiveForeground', '#000000')
        root.option_add('*Button.Relief', 'flat')
        root.option_add('*Button.BorderWidth', 0)
        root.option_add('*Button.HighlightThickness', 0)
        # Other classic widgets
        root.option_add('*Menubutton.Background', accent)
        root.option_add('*Menubutton.Foreground', fg)
        root.option_add('*Checkbutton.Background', bg)
        root.option_add('*Checkbutton.Foreground', fg)
        root.option_add('*Radiobutton.Background', bg)
        root.option_add('*Radiobutton.Foreground', fg)
        root.option_add('*Listbox.Background', accent)
        root.option_add('*Listbox.Foreground', fg)
        root.option_add('*Listbox.SelectBackground', sel_bg)
        root.option_add('*Listbox.SelectForeground', sel_fg)
        root.option_add('*Spinbox.Background', accent)
        root.option_add('*Spinbox.Foreground', fg)
    except Exception:
        pass
    # ttk widgets
    style.configure('.', background=bg, foreground=fg)
    style.configure('TFrame', background=bg)
    style.configure('TLabel', background=bg, foreground=fg)
    # Buttons should be light with dark text for visibility and FLAT
    light_btn_bg = '#f0f0f0'
    light_btn_bg_active = '#e6e6e6'
    style.configure('TButton', background=light_btn_bg, foreground='#000000', relief='flat', borderwidth=0,
                    padding=(20, 16))
    style.map('TButton', background=[('active', light_btn_bg_active)], foreground=[('active', '#000000')], relief=[('pressed', 'flat'), ('!pressed', 'flat')])
    style.configure('TNotebook', background=bg)
    style.configure('TNotebook.Tab', background=accent, foreground=fg)
    # Ensure selected tab foreground also updates (avoid white-on-white when
    # switching from dark to light)
    style.map('TNotebook.Tab', background=[('selected', bg)],
                                   foreground=[('selected', fg), ('!selected', fg)])
    style.configure('Treeview', background=accent, fieldbackground=accent, foreground=fg)
    style.map('Treeview', background=[('selected', sel_bg)], foreground=[('selected', sel_fg)])
    style.configure('Treeview.Heading', background='#333333', foreground=fg)
    style.configure('TEntry', fieldbackground=accent, foreground=fg)
    # TSpinbox (ttk) styling for dark theme
    try:
        style.configure('TSpinbox', fieldbackground=accent, background=accent, foreground=fg, insertcolor=fg, arrowsize=14)
        # Some Tk builds accept bordercolor/arrowcolor via element options; ignore errors
        style.map('TSpinbox', fieldbackground=[('readonly', accent)], foreground=[('disabled', fg)])
    except Exception:
        pass
    # Define card styles; they will be applied selectively by walker
    try:
        from tkinter import ttk
        card_bg = CARD_BG_DARK
        style = ttk.Style(root)
        style.configure('Card.TEntry', fieldbackground=card_bg, background=card_bg, foreground=fg)
        style.configure('Card.TSpinbox', fieldbackground=card_bg, background=card_bg, foreground=fg, insertcolor=fg)
        style.configure('Card.TCombobox', fieldbackground=card_bg, background=card_bg, foreground=fg)
        style.configure('Card.Treeview', background=card_bg, fieldbackground=card_bg)
    except Exception:
        pass
    # Inner padding for ttk.Entry in dark theme
    try:
        style.configure('TEntry', padding=(8, 6))
    except Exception:
        pass
    # Make combobox/button visuals readable on dark theme
    style.configure('TCombobox', fieldbackground=light_btn_bg, background=light_btn_bg, foreground='#000000')
    style.map('TCombobox', fieldbackground=[('readonly', light_btn_bg)], foreground=[('readonly', '#000000')])
    # Menu buttons style (will get padding updated per-scale at runtime)
    try:
        style.layout('Menu.TButton', [
            ('Button.border', {'sticky': 'nswe', 'children': [
                ('Button.focus', {'sticky': 'nswe', 'children': [
                    ('Button.padding', {'sticky': 'nswe', 'children': [
                        ('Button.label', {'sticky': 'nswe'})
                    ]})
                ]})
            ]})
        ])
        style.configure('Menu.TButton', background=light_btn_bg, foreground='#000000', relief='flat', borderwidth=0,
                        padding=(20, 16), anchor='center', justify='center', font='MenuButtonFont')
        style.map('Menu.TButton', background=[('pressed', light_btn_bg_active), ('active', light_btn_bg_active)])
    except Exception:
        pass


def _apply_light_palette(style, root: tk.Tk) -> None:
    bg = '#ffffff'
    fg = '#222222'
    accent = '#e0e0e0'  # general light surfaces (tabs, headings)
    btn_bg = '#1e2023'  # requested button color
    btn_bg_active = '#2a2f33'
    btn_fg = '#ffffff'
    sel_bg = '#cde8ff'
    sel_fg = '#000000'
    try:
        root.configure(bg=bg)
        root.option_add('*Background', bg)
        root.option_add('*Foreground', fg)
        # tk.Entry
        root.option_add('*Entry.Background', '#ffffff')
        root.option_add('*Entry.Foreground', fg)
        root.option_add('*Entry.InsertBackground', fg)
        root.option_add('*Entry.SelectBackground', sel_bg)
        root.option_add('*Entry.SelectForeground', sel_fg)
        # tk.Button (classic)
        root.option_add('*Button.Background', btn_bg)
        root.option_add('*Button.Foreground', btn_fg)
        root.option_add('*Button.ActiveBackground', btn_bg_active)
        root.option_add('*Button.ActiveForeground', btn_fg)
        # Others
        root.option_add('*Menubutton.Background', accent)
        root.option_add('*Menubutton.Foreground', fg)
        root.option_add('*Checkbutton.Background', bg)
        root.option_add('*Checkbutton.Foreground', fg)
        root.option_add('*Radiobutton.Background', bg)
        root.option_add('*Radiobutton.Foreground', fg)
        root.option_add('*Listbox.Background', '#ffffff')
        root.option_add('*Listbox.Foreground', fg)
        root.option_add('*Listbox.SelectBackground', sel_bg)
        root.option_add('*Listbox.SelectForeground', sel_fg)
        root.option_add('*Spinbox.Background', '#ffffff')
        root.option_add('*Spinbox.Foreground', fg)
    except Exception:
        pass
    style.configure('.', background=bg, foreground=fg)
    style.configure('TFrame', background=bg)
    style.configure('TLabel', background=bg, foreground=fg)
    # ttk Button styling (override to requested color)
    # Force background color for ttk.Button across states. Many themes ignore 'background'
    # unless we also set layout/element options. Use a custom style that draws a flat background.
    try:
        # Create a solid background layout to ensure our color is visible
        style.layout('Solid.TButton', [
            ('Button.border', {'sticky': 'nswe', 'children': [
                ('Button.focus', {'sticky': 'nswe', 'children': [
                    ('Button.padding', {'sticky': 'nswe', 'children': [
                        ('Button.label', {'sticky': 'nswe'})
                    ]})
                ]})
            ]})
        ])
        style.configure('Solid.TButton', background=btn_bg, foreground=btn_fg, relief='flat', borderwidth=0,
                        padding=(20, 16))  # increase inner horizontal/vertical padding
        style.map('Solid.TButton',
                   background=[('pressed', btn_bg_active), ('active', btn_bg_active), ('focus', btn_bg)],
                   foreground=[('disabled', '#bbbbbb'), ('!disabled', btn_fg)])
        # Also try to set Button element colors used by many themes
        style.configure('TButton', background=btn_bg, foreground=btn_fg, padding=(20, 16))
        style.map('TButton', background=[('pressed', btn_bg_active), ('active', btn_bg_active)])
        # Menu buttons style (will get padding updated per-scale at runtime)
        style.layout('Menu.TButton', [
            ('Button.border', {'sticky': 'nswe', 'children': [
                ('Button.focus', {'sticky': 'nswe', 'children': [
                    ('Button.padding', {'sticky': 'nswe', 'children': [
                        ('Button.label', {'sticky': 'nswe'})
                    ]})
                ]})
            ]})
        ])
        style.configure('Menu.TButton', background=btn_bg, foreground=btn_fg, relief='flat', borderwidth=0,
                        padding=(20, 16), anchor='center', justify='center', font='MenuButtonFont')
        style.map('Menu.TButton', background=[('pressed', btn_bg_active), ('active', btn_bg_active)])
    except Exception:
        style.configure('TButton', background=btn_bg, foreground=btn_fg, relief='flat', borderwidth=0)
        style.map('TButton', background=[('active', btn_bg_active)], foreground=[('active', btn_fg)], relief=[('pressed', 'flat'), ('!pressed', 'flat')])
    style.configure('TNotebook', background=bg)
    style.configure('TNotebook.Tab', background=accent, foreground=fg)
    # On light theme, force selected tab text to dark fg; also set default
    # non-selected to fg to overwrite any previous theme map from dark mode.
    style.map('TNotebook.Tab', background=[('selected', bg)],
                                   foreground=[('selected', fg), ('!selected', fg)])
    style.configure('Treeview', background='#ffffff', fieldbackground='#ffffff', foreground=fg)
    style.map('Treeview', background=[('selected', sel_bg)], foreground=[('selected', sel_fg)])
    style.configure('Treeview.Heading', background=accent, foreground=fg)
    style.configure('TEntry', fieldbackground='#ffffff', foreground=fg)
    # TSpinbox (ttk) styling for light theme
    try:
        style.configure('TSpinbox', fieldbackground='#ffffff', background='#ffffff', foreground=fg, insertcolor=fg, arrowsize=14)
        style.map('TSpinbox', fieldbackground=[('readonly', '#ffffff')])
    except Exception:
        pass
    # Inner padding for ttk.Entry in light theme
    try:
        style.configure('TEntry', padding=(8, 6))
    except Exception:
        pass
    style.configure('TCombobox', fieldbackground='#ffffff', background='#ffffff', foreground=fg)
    style.map('TCombobox', fieldbackground=[('readonly', '#ffffff')], foreground=[('readonly', fg)])

    # Define card styles with fixed accent color
    try:
        from tkinter import ttk
        card_bg = CARD_BG_LIGHT
        style = ttk.Style(root)
        style.configure('Card.TEntry', fieldbackground=card_bg, background=card_bg)
        style.configure('Card.TSpinbox', fieldbackground=card_bg, background=card_bg)
        style.configure('Card.TCombobox', fieldbackground=card_bg, background=card_bg)
        style.configure('Card.Treeview', background=card_bg, fieldbackground=card_bg)
    except Exception:
        pass


def _recolor_existing_classic_widgets(root: tk.Misc, theme_name: Optional[str]) -> None:
    """Best-effort recolor of existing classic Tk widgets (Frame, Button, etc.).
    ttk widgets update via Style; classic widgets need manual bg/fg updates.
    """
    try:
        # Determine palette from theme_name or by measuring bg luminance
        bg = root.cget('bg') if hasattr(root, 'cget') else '#ffffff'
        # Default to light fg; override for dark theme
        fg = '#222222'
        btn_bg = '#1e2023'
        btn_bg_active = '#2a2f33'
        btn_fg = '#ffffff'
        entry_bg = '#ffffff'
        list_bg = '#ffffff'
        if theme_name and str(theme_name).lower() in ('dark', 'koyu'):
            bg = '#1e1e1e'
            fg = '#eaeaea'
            btn_bg = '#f0f0f0'
            btn_bg_active = '#e6e6e6'
            btn_fg = '#000000'
            entry_bg = '#2d2d2d'
            list_bg = '#2d2d2d'
        else:
            # If not specified, infer by luminance
            try:
                r16, g16, b16 = root.winfo_rgb(bg)
                lum = 0.2126 * (r16/65535.0) + 0.7152 * (g16/65535.0) + 0.0722 * (b16/65535.0)
                if lum < 0.5:
                    # dark inferred
                    fg = '#eaeaea'
                    btn_bg = '#f0f0f0'
                    btn_bg_active = '#e6e6e6'
                    btn_fg = '#000000'
                    entry_bg = '#2d2d2d'
                    list_bg = '#2d2d2d'
            except Exception:
                pass

        def _is_in_card(widget: tk.Misc) -> bool:
            try:
                p = widget
                for _ in range(0, 12):
                    if getattr(p, '_is_card_inner', False):
                        return True
                    p = p.master  # type: ignore[attr-defined]
                    if p is None:
                        break
            except Exception:
                pass
            return False

        # Slightly shifted surface tone for cards
        def _card_tone(base_bg: str) -> str:
            try:
                r16, g16, b16 = root.winfo_rgb(base_bg)
                lum = 0.2126 * (r16/65535.0) + 0.7152 * (g16/65535.0) + 0.0722 * (b16/65535.0)
            except Exception:
                lum = 1.0
            return tinted_bg(root, 0.10 if lum < 0.5 else -0.10)

        card_bg = _card_tone(bg)

        def _walk(w: tk.Misc) -> None:
            try:
                children = w.winfo_children()
            except Exception:
                children = []
            for c in children:
                try:
                    cls = str(c.winfo_class())
                except Exception:
                    cls = ''
                # Skip ttk widgets (their classes typically start with 'T')
                is_ttk = cls.startswith('T')
                if not is_ttk:
                    try:
                        # Respect opt-out flag for custom-styled widgets
                        if getattr(c, '_preserve_theme', False):
                            raise Exception('skip-theme-preserve')
                        in_card = _is_in_card(c)
                        surface_bg = card_bg if in_card else bg
                        # Frames and Canvas adopt surface bg
                        if isinstance(c, tk.Frame) or isinstance(c, tk.Toplevel) or isinstance(c, tk.Canvas):
                            c.configure(bg=surface_bg)
                        # Classic Buttons get explicit palette
                        elif isinstance(c, tk.Button):
                            c.configure(bg=btn_bg, fg=btn_fg, activebackground=btn_bg_active, activeforeground=btn_fg, highlightthickness=0, bd=0, relief='flat')
                        # Entry-like
                        elif isinstance(c, tk.Entry) or isinstance(c, tk.Spinbox):
                            ebg = card_bg if in_card else entry_bg
                            c.configure(bg=ebg, fg=fg, insertbackground=fg)
                        # Listbox
                        elif isinstance(c, tk.Listbox):
                            lbg = card_bg if in_card else list_bg
                            c.configure(bg=lbg, fg=fg)
                        # Check/Radiobuttons should blend with bg and use fg
                        elif isinstance(c, tk.Checkbutton) or isinstance(c, tk.Radiobutton):
                            c.configure(bg=surface_bg, fg=fg, activebackground=surface_bg, activeforeground=fg, selectcolor=surface_bg)
                        # Labels: set foreground contrasting to the label's own
                        # background so custom badges stay readable across theme
                        # switches.
                        elif isinstance(c, tk.Label):
                            try:
                                # Align label background with current surface
                                c.configure(bg=surface_bg)
                                use_light = _is_dark_bg(c, surface_bg)
                                c.configure(fg=('#ffffff' if use_light else '#000000'))
                            except Exception:
                                pass
                    except Exception:
                        pass
                # Recurse
                _walk(c)

        _walk(root)
    except Exception:
        pass


def _icon_for_action(label: str) -> tuple[str, str]:
    """Return (icon, short_label) based on action text heuristics.
    Uses emoji so we don't depend on external image files.
    """
    low = (label or "").lower()
    # Heuristics tolerant to minor encoding issues
    if 'sat' in low:          # Yeni satış
        return '🛒', 'Satış'
    if 'ade' in low:          # İade işlemi
        return '↩️', 'İade'
    if 'rapor' in low:
        return '📊', 'Raporlar'
    if 'ayar' in low:
        return '⚙️', 'Ayarlar'
    if 'gelir' in low or 'gider' in low:
        return '💰', 'Gelir/Gider'
    if 'yat' in low:          # Yatırımcılar
        return '💼', 'Yatırımcılar'
    if 'üye' in low or 'uye' in low or 'oy' in low:  # Üye yönetimi (garbled tolerant)
        return '👥', 'Üyeler'
    if 'ür' in low or 'urun' in low or 'prod' in low:
        return '📦', 'Ürünler'
    return '🔘', label


def create_menu_button(parent: tk.Misc, text: str, command) -> tk.Button:
    """Create a big, icon-first menu button for role dashboards.
    Icons are emoji placed over a short label. No wrapping.
    """
    icon, short = _icon_for_action(text)
    # Add an extra blank line between icon and label to increase visual height
    btn_text = f"{icon}\n\n{short}"
    # Prefer ttk for consistent theming; fall back to tk.Button
    # Force classic tk.Button to bypass ttk theme overrides
    base_family = None
    try:
        import tkinter.font as tkfont
        try:
            base_family = tkfont.nametofont('TkDefaultFont').actual('family')
        except Exception:
            base_family = None
        # Large, guaranteed-visible font with pixel size (negative = pixels in Tk)
        try:
            tkfont.nametofont('MenuButtonFont').configure(size=-42, weight='bold')
        except Exception:
            if base_family:
                tkfont.Font(name='MenuButtonFont', family=base_family, size=-42, weight='bold')
            else:
                tkfont.Font(name='MenuButtonFont', size=-42, weight='bold')
        menu_font_name = 'MenuButtonFont'
    except Exception:
        menu_font_name = None

    btn = tk.Button(
        parent,
        text=btn_text,
        width=18,   # more width to match tall look
        height=5,
        justify='center',
        relief='flat',
        bd=0,
        highlightthickness=0,
        command=command,
        font=menu_font_name if menu_font_name else (tkfont.Font(family=base_family, size=-42, weight='bold') if base_family else None)
    )
    # Fixed colors for light theme preference; dark theme still readable
    try:
        btn.configure(bg='#1e2023', fg='#ffffff', activebackground='#2a2f33', activeforeground='#ffffff')
    except Exception:
        pass
    # Add internal padding to visually increase height
    try:
        btn.configure(ipady=16, padx=16, pady=10)
    except Exception:
        pass
    return btn


def rounded_outline(parent: tk.Misc, radius: int = 10, padding: int = 8, border: str = '#888') -> tuple[tk.Frame, tk.Frame]:
    """Create a container with a rounded outline and an inner frame to pack widgets.
    Returns (container, inner_frame).
    """
    bg = parent.cget('bg') if hasattr(parent, 'cget') else 'white'
    container = tk.Frame(parent, bd=0, highlightthickness=0, bg=bg)
    canvas = tk.Canvas(container, bd=0, highlightthickness=0, bg=bg)
    canvas.pack(fill='both', expand=True)
    inner = tk.Frame(container, bd=0, highlightthickness=0, bg=bg)
    # Mark inner as a card container for theming walkers
    try:
        inner._is_card_inner = True  # type: ignore[attr-defined]
    except Exception:
        pass

    def _resize(event=None):
        w = container.winfo_width()
        h = container.winfo_height()
        if w < 4 or h < 4:
            return
        canvas.delete('rrect')
        r = max(2, min(radius, (min(w, h) // 2) - 2))
        x0, y0 = 2, 2
        x1, y1 = w - 3, h - 3
        # Straight edges
        canvas.create_line(x0 + r, y0, x1 - r, y0, fill=border, width=2, tags='rrect')
        canvas.create_line(x1, y0 + r, x1, y1 - r, fill=border, width=2, tags='rrect')
        canvas.create_line(x1 - r, y1, x0 + r, y1, fill=border, width=2, tags='rrect')
        canvas.create_line(x0, y1 - r, x0, y0 + r, fill=border, width=2, tags='rrect')
        # Corner arcs
        canvas.create_arc(x1 - 2*r, y0, x1, y0 + 2*r, start=0, extent=90, style='arc', outline=border, width=2, tags='rrect')
        canvas.create_arc(x0, y0, x0 + 2*r, y0 + 2*r, start=90, extent=90, style='arc', outline=border, width=2, tags='rrect')
        canvas.create_arc(x0, y1 - 2*r, x0 + 2*r, y1, start=180, extent=90, style='arc', outline=border, width=2, tags='rrect')
        canvas.create_arc(x1 - 2*r, y1 - 2*r, x1, y1, start=270, extent=90, style='arc', outline=border, width=2, tags='rrect')
        # Fit inner with padding
        inner.place(x=padding, y=padding, width=max(0, w - 2 * padding), height=max(0, h - 2 * padding))

    container.bind('<Configure>', _resize)
    return container, inner


def _theme_mode(root: tk.Misc, explicit: Optional[str] = None) -> str:
    try:
        if explicit:
            low = str(explicit).lower()
            if 'dark' in low or 'koyu' in low:
                return 'dark'
            if 'light' in low or 'acik' in low or 'açık' in low:
                return 'light'
        bg = root.cget('bg') if hasattr(root, 'cget') else '#ffffff'
        r16, g16, b16 = root.winfo_rgb(bg)
        lum = 0.2126 * (r16/65535.0) + 0.7152 * (g16/65535.0) + 0.0722 * (b16/65535.0)
        return 'dark' if lum < 0.5 else 'light'
    except Exception:
        return 'light'

def _compute_card_bg(widget: tk.Misc, theme_name: Optional[str] = None) -> str:
    mode = _theme_mode(widget, theme_name)
    return CARD_BG_DARK if mode == 'dark' else CARD_BG_LIGHT


def create_card(parent: tk.Misc, radius: int = 12, padding: int = 12, border: str = '#888') -> tuple[tk.Frame, tk.Frame]:
    """Create a standard card surface with unified background tone.
    Returns (card_container, inner_frame).
    """
    card, inner = rounded_outline(parent, radius=radius, padding=padding, border=border)
    try:
        inner.configure(bg=_compute_card_bg(parent))
    except Exception:
        pass
    return card, inner


def refresh_card_tints(root: tk.Misc) -> None:
    """Refresh background color of all card inner frames and non-input classic children.
    Applies the standard card tone relative to current theme background.
    """
    try:
        import tkinter as tk
        def _walk(w: tk.Misc):
            try:
                children = w.winfo_children()
            except Exception:
                children = []
            for c in children:
                try:
                    if getattr(c, '_is_card_inner', False):
                        new_bg = _compute_card_bg(root)
                        try:
                            c.configure(bg=new_bg)
                        except Exception:
                            pass
                        # Update classic children to match card bg, but skip inputs
                        for ch in c.winfo_children():
                            try:
                                if isinstance(ch, (tk.Entry, tk.Text, tk.Spinbox, tk.Listbox)):
                                    continue
                                cls = str(ch.winfo_class())
                                if not cls.startswith('T'):
                                    ch.configure(bg=new_bg)
                            except Exception:
                                pass
                except Exception:
                    pass
                _walk(c)
        _walk(root)
    except Exception:
        pass


def ensure_card_control_backgrounds(root: tk.Misc) -> None:
    """Force controls inside card inners to use the exact card inner bg.
    Creates per-tone ttk styles so colors match even on platforms that ignore generic colors.
    """
    try:
        from tkinter import ttk
        import tkinter as tk

        def _fg_for(bg: str) -> str:
            try:
                r16, g16, b16 = root.winfo_rgb(bg)
                lum = 0.2126 * (r16/65535.0) + 0.7152 * (g16/65535.0) + 0.0722 * (b16/65535.0)
                return '#eaeaea' if lum < 0.5 else '#222222'
            except Exception:
                return '#222222'

        style = ttk.Style(root)

        def _style_name(base: str, bg: str) -> str:
            key = bg.replace('#','') if isinstance(bg, str) else 'X'
            return f"Card{key}.{base}"

        def _apply_for_widget(w: tk.Misc, inner_bg: str):
            try:
                cls = str(w.winfo_class())
            except Exception:
                cls = ''
            # ttk widgets
            if cls.startswith('T'):
                fg = _fg_for(inner_bg)
                if cls in ('TEntry',):
                    sn = _style_name('TEntry', inner_bg)
                    try:
                        style.configure(sn, fieldbackground=inner_bg, background=inner_bg, foreground=fg)
                    except Exception:
                        pass
                    try:
                        w.configure(style=sn)  # type: ignore[call-arg]
                    except Exception:
                        pass
                elif cls in ('TSpinbox',):
                    sn = _style_name('TSpinbox', inner_bg)
                    try:
                        style.configure(sn, fieldbackground=inner_bg, background=inner_bg, foreground=fg, insertcolor=fg)
                    except Exception:
                        pass
                    try:
                        w.configure(style=sn)  # type: ignore[call-arg]
                    except Exception:
                        pass
                elif cls in ('TCombobox',):
                    sn = _style_name('TCombobox', inner_bg)
                    try:
                        style.configure(sn, fieldbackground=inner_bg, background=inner_bg, foreground=fg)
                    except Exception:
                        pass
                    try:
                        w.configure(style=sn)  # type: ignore[call-arg]
                    except Exception:
                        pass
                elif cls in ('Treeview',):
                    sn = _style_name('Treeview', inner_bg)
                    try:
                        style.configure(sn, background=inner_bg, fieldbackground=inner_bg, foreground=fg)
                    except Exception:
                        pass
                    try:
                        w.configure(style=sn)  # type: ignore[call-arg]
                    except Exception:
                        pass
            else:
                # Classic widgets: set bg directly except for inputs
                try:
                    if isinstance(w, (tk.Entry, tk.Spinbox, tk.Listbox, tk.Text)):
                        w.configure(bg=inner_bg)
                    elif isinstance(w, (tk.Frame, tk.Canvas, tk.Toplevel, tk.Label)):
                        w.configure(bg=inner_bg)
                except Exception:
                    pass

        def _is_card_inner(w: tk.Misc) -> bool:
            return bool(getattr(w, '_is_card_inner', False))

        def _find_card_inner(w: tk.Misc):
            p = w
            depth = 0
            while p is not None and depth < 12:
                if _is_card_inner(p):
                    return p
                p = getattr(p, 'master', None)
                depth += 1
            return None

        def _walk(w: tk.Misc):
            try:
                children = w.winfo_children()
            except Exception:
                children = []
            for c in children:
                inner = _find_card_inner(c)
                if inner is not None:
                    try:
                        inner_bg = inner.cget('bg')
                    except Exception:
                        inner_bg = None
                    if inner_bg:
                        _apply_for_widget(c, inner_bg)
                _walk(c)

        _walk(root)
    except Exception:
        pass


def tinted_bg(widget: tk.Misc, amount: float = 0.08) -> str:
    """Return a slightly tinted version of the widget background.
    amount>0 lightens; amount<0 darkens.
    """
    try:
        bg = widget.cget('bg')
    except Exception:
        bg = '#ffffff'
    if isinstance(bg, str) and bg.startswith('#') and len(bg) in (4, 7):
        if len(bg) == 4:
            bg = '#' + ''.join(c*2 for c in bg[1:])
        r = int(bg[1:3], 16)
        g = int(bg[3:5], 16)
        b = int(bg[5:7], 16)
        if amount >= 0:
            r = int(r + (255 - r) * amount)
            g = int(g + (255 - g) * amount)
            b = int(b + (255 - b) * amount)
        else:
            f = -amount
            r = int(r * (1 - f))
            g = int(g * (1 - f))
            b = int(b * (1 - f))
        return f"#{r:02x}{g:02x}{b:02x}"
    return bg

def smart_tinted_bg(widget: tk.Misc, light_amount: float = -0.06, dark_amount: float = 0.10) -> str:
    """Tint background based on luminance: on light themes, darken slightly; on dark themes, lighten."""
    try:
        bg = widget.cget('bg')
        r16, g16, b16 = widget.winfo_rgb(bg)
        r = r16 / 65535.0
        g = g16 / 65535.0
        b = b16 / 65535.0
        lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
        if lum < 0.5:
            return tinted_bg(widget, dark_amount)
        else:
            return tinted_bg(widget, light_amount)
    except Exception:
        return tinted_bg(widget, light_amount)


def _is_dark_bg(widget: tk.Misc, bg: Optional[str] = None) -> bool:
    try:
        color = bg if bg is not None else widget.cget('bg')
        r16, g16, b16 = widget.winfo_rgb(color)
        r = r16 / 65535.0
        g = g16 / 65535.0
        b = b16 / 65535.0
        lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
        return lum < 0.5
    except Exception:
        return False


def ensure_contrast_text_colors(container: tk.Misc) -> None:
    """Walk the widget tree and set a readable foreground color based on
    each widget's current background. Applies to classic Tk widgets only.
    - Dark bg -> light text
    - Light bg -> black text
    Respects an optional flag: widget._preserve_fg = True to opt out.
    Also updates Entry/Spinbox insert cursor color.
    """
    try:
        children = container.winfo_children()
    except Exception:
        children = []
    for w in children:
        try:
            cls = w.winfo_class()
        except Exception:
            cls = ''
        is_ttk = str(cls).startswith('T')
        if not is_ttk:
            try:
                bg = w.cget('bg') if hasattr(w, 'cget') else None
                if getattr(w, '_preserve_theme', False):
                    raise Exception('skip-theme-preserve')
                if bg is not None and not getattr(w, '_preserve_fg', False):
                    light_fg = '#ffffff'
                    dark_fg = '#000000'
                    use_light = _is_dark_bg(w, bg)
                    fg = light_fg if use_light else dark_fg
                    if isinstance(w, tk.Button):
                        w.configure(fg=fg)
                        if isinstance(w, tk.Button):
                            try:
                                # Keep activeforeground in sync when possible
                                w.configure(activeforeground=fg)
                            except Exception:
                                pass
                    elif isinstance(w, tk.Entry) or isinstance(w, tk.Spinbox):
                        w.configure(fg=fg)
                        try:
                            w.configure(insertbackground=fg)
                        except Exception:
                            pass
                    elif isinstance(w, tk.Listbox):
                        w.configure(fg=fg)
                    elif isinstance(w, tk.Checkbutton) or isinstance(w, tk.Radiobutton):
                        # For these, keep selectcolor as current bg but set text colors
                        w.configure(fg=fg, activeforeground=fg)
                    elif isinstance(w, tk.Label):
                        # Labels: contrast to their own bg
                        try:
                            use_light_lbl = _is_dark_bg(w, bg)
                            w.configure(fg=('#ffffff' if use_light_lbl else '#000000'))
                        except Exception:
                            pass
            except Exception:
                pass
        # Recurse
        try:
            ensure_contrast_text_colors(w)
        except Exception:
            pass


def ensure_ttk_contrast_styles(root: tk.Misc) -> None:
    """Ensure ttk styles have readable foregrounds vs their backgrounds.
    Uses theme mode heuristic. Covers: TButton, Solid.TButton, Menu.TButton,
    TEntry, TSpinbox, TCombobox, Treeview headings/rows.
    """
    try:
        from tkinter import ttk
        style = ttk.Style(root)
        mode = _theme_mode(root)
        if mode == 'dark':
            btn_fg = '#000000'  # dark theme uses light buttons
            entry_fg = '#eaeaea'
            tree_fg = '#eaeaea'
        else:
            btn_fg = '#ffffff'  # light theme uses dark buttons
            entry_fg = '#222222'
            tree_fg = '#222222'
        for sty in ('TButton', 'Solid.TButton', 'Menu.TButton'):
            try:
                style.configure(sty, foreground=btn_fg)
                style.map(sty, foreground=[('active', btn_fg), ('!disabled', btn_fg)])
            except Exception:
                pass
        # Ensure menu-styled buttons keep a comfortable height regardless of
        # platform/theme overrides by enforcing padding.
        try:
            style.configure('Menu.TButton', padding=(24, 12), anchor='center', justify='center')
        except Exception:
            pass
        for sty in ('TEntry', 'TSpinbox', 'TCombobox'):
            try:
                style.configure(sty, foreground=entry_fg)
            except Exception:
                pass
        try:
            style.configure('Treeview', foreground=tree_fg)
            style.configure('Treeview.Heading', foreground=tree_fg)
        except Exception:
            pass
    except Exception:
        pass


def ensure_ttk_label_contrast(root: tk.Misc) -> None:
    """Ensure each ttk.Label has readable text against its own background.
    Tries per-widget background via style lookup; then sets widget foreground.
    """
    try:
        from tkinter import ttk
        style = ttk.Style(root)
        # Helpers to detect card and compute surface tint similar to classic path
        def _is_in_card(widget: tk.Misc) -> bool:
            try:
                p = widget
                for _ in range(0, 12):
                    if getattr(p, '_is_card_inner', False):
                        return True
                    p = p.master  # type: ignore[attr-defined]
                    if p is None:
                        break
            except Exception:
                pass
            return False
        def _surface_bg_for(widget: tk.Misc) -> Optional[str]:
            try:
                base = root.cget('bg')
            except Exception:
                base = '#ffffff'
            try:
                # Match card tone if inside a card
                if _is_in_card(widget):
                    return _compute_card_bg(root)
            except Exception:
                pass
            # Otherwise use parent bg
            try:
                p = widget.master
                if p and hasattr(p, 'cget'):
                    return p.cget('bg')  # type: ignore[attr-defined]
            except Exception:
                pass
            return base
        def _bg_for(widget: tk.Misc) -> Optional[str]:
            try:
                # 1) Explicit background option on widget
                bg = widget.cget('background')  # type: ignore[call-arg]
                if bg:
                    return bg
            except Exception:
                pass
            try:
                # 2) Style-defined background
                sty = getattr(widget, 'cget', lambda *_: None)('style')
                sty = sty or 'TLabel'
                bg = style.lookup(sty, 'background')
                if bg:
                    return bg
            except Exception:
                pass
            try:
                # 3) Fallback to parent's bg
                p = widget.master
                if p and hasattr(p, 'cget'):
                    return p.cget('bg')  # type: ignore[attr-defined]
            except Exception:
                pass
            return None
        def _walk(w: tk.Misc):
            try:
                children = w.winfo_children()
            except Exception:
                children = []
            for c in children:
                try:
                    if isinstance(c, ttk.Label):
                        # Normalize background to current surface to avoid stale bg
                        surf = _surface_bg_for(c)
                        if surf:
                            try:
                                c.configure(background=surf)
                            except Exception:
                                pass
                            use_light = _is_dark_bg(c, surf)
                            c.configure(foreground=('#ffffff' if use_light else '#000000'))
                except Exception:
                    pass
                _walk(c)
        _walk(root)
    except Exception:
        pass


def apply_entry_margins(container: tk.Misc, pady: int = 6, padx: int = 0) -> None:
    """Walk the widget tree under container and add margins and internal padding
    to Entry/Spinbox widgets.
    - External spacing: pady/padx (min values)
    - Internal padding: sets a comfortable ipady/ipadx if smaller than desired
    Works for both pack and grid managers without altering order.
    """
    # Allow whole subtrees to opt out (frames that manage spacing precisely)
    try:
        if getattr(container, '_preserve_theme', False):
            return
    except Exception:
        pass
    try:
        children = container.winfo_children()
    except Exception:
        return
    for w in children:
        try:
            if getattr(w, '_preserve_theme', False):
                # Skip this widget and its subtree
                continue
        except Exception:
            pass
        try:
            manager = w.winfo_manager()
        except Exception:
            manager = ''
        try:
            cls = str(w.winfo_class()).lower()
        except Exception:
            cls = ''
        is_entry = isinstance(w, tk.Entry) or isinstance(w, tk.Spinbox) or 'entry' in cls or 'spinbox' in cls
        if is_entry:
            try:
                if manager == 'pack':
                    info = w.pack_info()
                    cur_pady = info.get('pady', 0)
                    cur_ipady = info.get('ipady', 0)
                    cur_ipadx = info.get('ipadx', 0)
                    if not isinstance(cur_pady, (list, tuple)):
                        cur = int(cur_pady)
                    else:
                        cur = max(int(cur_pady[0]), int(cur_pady[1]))
                    if cur < pady:
                        w.pack_configure(pady=pady, padx=padx)
                    # Inner padding for a comfier text field
                    if int(cur_ipady or 0) < 4:
                        w.pack_configure(ipady=4)
                    if int(cur_ipadx or 0) < 6:
                        w.pack_configure(ipadx=6)
                elif manager == 'grid':
                    info = w.grid_info()
                    cur_pady = info.get('pady', 0)
                    cur_ipady = info.get('ipady', 0)
                    cur_ipadx = info.get('ipadx', 0)
                    if not isinstance(cur_pady, (list, tuple)):
                        cur = int(cur_pady)
                    else:
                        cur = max(int(cur_pady[0]), int(cur_pady[1]))
                    if cur < pady:
                        w.grid_configure(pady=pady, padx=padx)
                    if int(cur_ipady or 0) < 4:
                        w.grid_configure(ipady=4)
                    if int(cur_ipadx or 0) < 6:
                        w.grid_configure(ipadx=6)
            except Exception:
                pass
        # Recurse
        apply_entry_margins(w, pady=pady, padx=padx)


def apply_button_margins(container: tk.Misc, pady: int = 12, padx: int = 12) -> None:
    """Ensure all Button/ttk.Button widgets under container have at least the
    given external margins (pady/padx). Works for both pack and grid managers.
    """
    try:
        children = container.winfo_children()
    except Exception:
        return
    for w in children:
        try:
            if getattr(w, '_preserve_theme', False):
                continue
        except Exception:
            pass
        try:
            manager = w.winfo_manager()
        except Exception:
            manager = ''
        try:
            cls = str(w.winfo_class()).lower()
        except Exception:
            cls = ''
        is_button = isinstance(w, tk.Button) or 'button' in cls
        if is_button:
            try:
                if manager == 'pack':
                    info = w.pack_info()
                    cur_pady = info.get('pady', 0)
                    cur_padx = info.get('padx', 0)
                    cur_py = int(cur_pady if not isinstance(cur_pady, (list, tuple)) else max(cur_pady))
                    cur_px = int(cur_padx if not isinstance(cur_padx, (list, tuple)) else max(cur_padx))
                    if cur_py < pady or cur_px < padx:
                        w.pack_configure(pady=max(pady, cur_py), padx=max(padx, cur_px))
                elif manager == 'grid':
                    info = w.grid_info()
                    cur_pady = info.get('pady', 0)
                    cur_padx = info.get('padx', 0)
                    cur_py = int(cur_pady if not isinstance(cur_pady, (list, tuple)) else max(cur_pady))
                    cur_px = int(cur_padx if not isinstance(cur_padx, (list, tuple)) else max(cur_padx))
                    if cur_py < pady or cur_px < padx:
                        w.grid_configure(pady=max(pady, cur_py), padx=max(padx, cur_px))
            except Exception:
                pass
        apply_button_margins(w, pady=pady, padx=padx)
