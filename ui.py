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
