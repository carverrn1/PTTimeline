"""
ptt_splash.py - Splash screen support for PTTimeline applications.

Provides show_splash(), update_splash(), and close_splash() for displaying
a tkinter-based splash screen before Qt and other heavy modules are imported.

Usage:
    from ptt_splash import show_splash, update_splash, close_splash

    splash, splash_label, splash_img = show_splash('myapp_splash.png', res_dir)
    # ... heavy imports and initialization ...
    update_splash(splash, splash_label, splash_img, 'Loading file...')
    # ... more initialization ...
    close_splash(splash)
"""

import os


def show_splash(splash_filename, res_dir):
    """Display a tkinter splash screen as early as possible during startup.

    Args:
        splash_filename: Basename of the splash image file (e.g. 'pttedit_splash.png')
        res_dir:         Path to the resources directory (_RES_DIR from the calling app)

    Returns:
        (splash, label, base_img) tuple.
        base_img is the original PIL image kept for text compositing.
        Returns (None, None, None) if splash cannot be shown.
    """
    try:
        import tkinter as tk
        from PIL import Image, ImageTk
        splash_path = os.path.join(res_dir, splash_filename)
        if not os.path.isfile(splash_path):
            return None, None, None
        splash = tk.Tk()
        splash.overrideredirect(True)   # No title bar or borders
        splash.attributes('-topmost', True)  # Stay on top
        # Force geometry update before reading screen dimensions
        splash.update_idletasks()
        base_img = Image.open(splash_path)
        photo = ImageTk.PhotoImage(base_img)
        w, h = base_img.width, base_img.height
        # Use ctypes on Windows to get primary monitor size only,
        # avoiding multi-monitor virtual desktop total from tkinter
        try:
            import ctypes
            user32 = ctypes.windll.user32
            user32.SetProcessDPIAware()
            sw = user32.GetSystemMetrics(0)  # SM_CXSCREEN - primary monitor width
            sh = user32.GetSystemMetrics(1)  # SM_CYSCREEN - primary monitor height
        except Exception:
            # macOS/Linux fallback - single monitor assumed correct
            sw = splash.winfo_screenwidth()
            sh = splash.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        splash.geometry(f'{w}x{h}+{x}+{y}')
        label = tk.Label(splash, image=photo, bd=0)
        label.image = photo  # Keep reference on label to prevent GC
        label.pack()
        splash.update()  # Force immediate display
        return splash, label, base_img
    except Exception:
        return None, None, None


def update_splash(splash, label, base_img, text):
    """Update splash screen status text by compositing onto the base image.
    No-op if splash is None.

    Args:
        splash:   tkinter Tk window returned by show_splash()
        label:    tkinter Label returned by show_splash()
        base_img: PIL Image returned by show_splash()
        text:     Status text to display
    """
    try:
        if splash is None or label is None or base_img is None:
            return
        from PIL import Image, ImageDraw, ImageFont, ImageTk
        # Work on a copy so base_img stays clean for next update
        img = base_img.copy()
        draw = ImageDraw.Draw(img)
        # Try Arial, fall back to PIL default
        try:
            font = ImageFont.truetype('arial.ttf', 20)
        except Exception:
            font = ImageFont.load_default()
        draw.text((30, 205), text, fill='white', font=font)
        photo = ImageTk.PhotoImage(img)
        label.config(image=photo)
        label.image = photo  # Keep reference to prevent GC
        splash.update()
    except Exception:
        pass


def close_splash(splash):
    """Close and destroy the splash screen. No-op if splash is None.

    Args:
        splash: tkinter Tk window returned by show_splash()
    """
    try:
        if splash is not None:
            splash.destroy()
    except Exception:
        pass
