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

    # Hover effect
    def _on_enter(_e=None):
        c.itemconfig(arrow, fill=hover_fill)

    def _on_leave(_e=None):
        c.itemconfig(arrow, fill=normal_fill)

    c.bind('<Enter>', _on_enter)
    c.bind('<Leave>', _on_leave)
    c.bind('<Button-1>', lambda _e: command())
    c.configure(cursor='hand2')
    return c


from typing import Optional


def apply_theme(root: tk.Tk, scale: Optional[float] = None, theme_name: Optional[str] = None) -> None:
    """Apply a larger, cleaner Tk/ttk theme for readability.
    - Increases default fonts
    - Pads buttons/entries
    - Enlarges Treeview rows and headings
    """
    try:
        # Global scaling (makes all points render larger)
        try:
            # Double-size UI by default
            root.tk.call('tk', 'scaling', float(scale) if scale else 1.2)
        except Exception:
            pass

        import tkinter.font as tkfont
        # Bump core fonts noticeably
        for fname, size, weight in (
            ('TkDefaultFont', 13, 'normal'),
            ('TkTextFont', 13, 'normal'),
            ('TkMenuFont', 13, 'normal'),
            ('TkHeadingFont', 18, 'bold'),
            ('TkTooltipFont', 12, 'normal'),
        ):
            try:
                f = tkfont.nametofont(fname)
                f.configure(size=size, weight=weight)
            except Exception:
                pass

        # Apply defaults to classic Tk widgets too
        try:
            app_font = tkfont.nametofont('TkDefaultFont')
            heading_font = tkfont.nametofont('TkHeadingFont')
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
        style.configure('TButton', padding=(12, 10))
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
    style.configure('TButton', background=light_btn_bg, foreground='#000000', relief='flat', borderwidth=0)
    style.map('TButton', background=[('active', light_btn_bg_active)], foreground=[('active', '#000000')], relief=[('pressed', 'flat'), ('!pressed', 'flat')])
    style.configure('TNotebook', background=bg)
    style.configure('TNotebook.Tab', background=accent, foreground=fg)
    style.map('TNotebook.Tab', background=[('selected', bg)])
    style.configure('Treeview', background=accent, fieldbackground=accent, foreground=fg)
    style.map('Treeview', background=[('selected', sel_bg)], foreground=[('selected', sel_fg)])
    style.configure('Treeview.Heading', background='#333333', foreground=fg)
    style.configure('TEntry', fieldbackground=accent, foreground=fg)
    # Make combobox/button visuals readable on dark theme
    style.configure('TCombobox', fieldbackground=light_btn_bg, background=light_btn_bg, foreground='#000000')
    style.map('TCombobox', fieldbackground=[('readonly', light_btn_bg)], foreground=[('readonly', '#000000')])


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
    style.configure('TButton', background=btn_bg, foreground=btn_fg, relief='flat', borderwidth=0)
    style.map('TButton', background=[('active', btn_bg_active)], foreground=[('active', btn_fg)], relief=[('pressed', 'flat'), ('!pressed', 'flat')])
    style.configure('TNotebook', background=bg)
    style.configure('TNotebook.Tab', background=accent, foreground=fg)
    style.map('TNotebook.Tab', background=[('selected', bg)])
    style.configure('Treeview', background='#ffffff', fieldbackground='#ffffff', foreground=fg)
    style.map('Treeview', background=[('selected', sel_bg)], foreground=[('selected', sel_fg)])
    style.configure('Treeview.Heading', background=accent, foreground=fg)
    style.configure('TEntry', fieldbackground='#ffffff', foreground=fg)
    style.configure('TCombobox', fieldbackground='#ffffff', background='#ffffff', foreground=fg)
    style.map('TCombobox', fieldbackground=[('readonly', '#ffffff')], foreground=[('readonly', fg)])


def create_menu_button(parent: tk.Misc, text: str, command) -> tk.Button:
    """Create a big, square-like menu button for role dashboards.
    Uses fixed character width/height for a consistent square feel.
    """
    btn = tk.Button(
        parent,
        text=text,
        width=14,   # chars
        height=4,   # text lines
        wraplength=120,
        justify='center',
        relief='flat',
        bd=0,
        highlightthickness=0,
        command=command,
    )
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


def apply_entry_margins(container: tk.Misc, pady: int = 6, padx: int = 0) -> None:
    """Walk the widget tree under container and add vertical margins to Entry/Spinbox widgets.
    Works for both pack and grid managers without altering order.
    """
    try:
        children = container.winfo_children()
    except Exception:
        return
    for w in children:
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
                    if not isinstance(cur_pady, (list, tuple)):
                        cur = int(cur_pady)
                    else:
                        cur = max(int(cur_pady[0]), int(cur_pady[1]))
                    if cur < pady:
                        w.pack_configure(pady=pady, padx=padx)
                elif manager == 'grid':
                    info = w.grid_info()
                    cur_pady = info.get('pady', 0)
                    if not isinstance(cur_pady, (list, tuple)):
                        cur = int(cur_pady)
                    else:
                        cur = max(int(cur_pady[0]), int(cur_pady[1]))
                    if cur < pady:
                        w.grid_configure(pady=pady, padx=padx)
            except Exception:
                pass
        # Recurse
        apply_entry_margins(w, pady=pady, padx=padx)
