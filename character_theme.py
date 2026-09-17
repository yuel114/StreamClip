"""The character's silver, mint and blue orbital language on native ttk widgets."""

import ctypes
import logging
import os
import time
from pathlib import Path
from tkinter import Canvas, font as tkfont

from PIL import Image, ImageChops, ImageDraw, ImageTk
import ttkbootstrap as ttk
from ttkbootstrap.style import ThemeDefinition


UI_COLORS = {
    "primary": "#426E78", "secondary": "#586B83", "success": "#416C51",
    "info": "#426595", "warning": "#806122", "danger": "#A24761",
    "light": "#E9EDF7", "dark": "#34445F", "bg": "#E9EDF7", "fg": "#34445F",
    "selectbg": "#D9E8ED", "selectfg": "#304D65", "border": "#879BAC",
    "inputfg": "#34445F", "inputbg": "#FCFDFE", "active": "#DCEBE9",
}
ASSET_DIR = Path(__file__).resolve().parent / "assets" / "ui"
SURFACE = "#F6F8FC"
HEADER = "#F2F5FA"
RAIL = "#E3EFEC"
TABLE_HEADER = "#E1E9F4"
STRIPE = "#EDF2F8"
MUTED = "#52657C"
DISABLED_BG = "#E4EAF1"
DISABLED_FG = "#596A7E"


def motion_enabled() -> bool:
    """Read Windows' client-area animation preference; never change it."""
    if os.name != "nt":
        return False
    enabled = ctypes.c_int()
    return bool(ctypes.windll.user32.SystemParametersInfoW(0x1042, 0, ctypes.byref(enabled), 0) and enabled.value)


def native_window_drag(event):
    """Let Windows track the title area, including snapping and mouse capture."""
    if os.name != "nt":
        return
    from ctypes import wintypes
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
    user32.GetAncestor.restype = wintypes.HWND
    user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    user32.PostMessageW.restype = wintypes.BOOL
    handle = user32.GetAncestor(event.widget.winfo_toplevel().winfo_id(), 2)
    user32.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
    user32.GetCursorPos.restype = wintypes.BOOL
    point = wintypes.POINT()
    if not handle or not user32.GetCursorPos(ctypes.byref(point)):
        return
    coordinates = (point.x & 0xFFFF) | ((point.y & 0xFFFF) << 16)
    user32.ReleaseCapture()
    # Let this Python/Tcl callback return before Windows starts its modal loop.
    # A synchronous SendMessage can re-enter Tk painting without its thread state.
    if user32.PostMessageW(handle, 0x00A1, 2, coordinates):  # WM_NCLBUTTONDOWN, HTCAPTION
        return "break"


class WindowInteraction:
    """Defer application refreshes while Tk keeps native resize painting live."""
    def __init__(self, root):
        self.root = root
        self.active = self.installed = False
        if os.name != "nt":
            return
        from ctypes import wintypes as w
        self._user = ctypes.WinDLL("user32", use_last_error=True)
        self._controls = ctypes.WinDLL("comctl32", use_last_error=True)
        callback_type = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, w.HWND, w.UINT, w.WPARAM, w.LPARAM, ctypes.c_size_t, ctypes.c_size_t)
        self._callback = callback_type(self._dispatch)
        for library, name, result, arguments in (
            (self._user, "GetAncestor", w.HWND, [w.HWND, w.UINT]),
            (self._user, "GetClassLongPtrW", ctypes.c_size_t, [w.HWND, ctypes.c_int]),
            (self._user, "SetClassLongPtrW", ctypes.c_size_t, [w.HWND, ctypes.c_int, ctypes.c_ssize_t]),
            (self._controls, "SetWindowSubclass", w.BOOL, [w.HWND, callback_type, ctypes.c_size_t, ctypes.c_size_t]),
            (self._controls, "RemoveWindowSubclass", w.BOOL, [w.HWND, callback_type, ctypes.c_size_t]),
            (self._controls, "DefSubclassProc", ctypes.c_ssize_t, [w.HWND, w.UINT, w.WPARAM, w.LPARAM]),
        ):
            function = getattr(library, name)
            function.restype, function.argtypes = result, arguments
        root.bind("<Map>", self._attach, add="+")
        if root.winfo_ismapped():
            self._attach()

    def _attach(self, event=None):
        if self.installed or (event is not None and event.widget is not self.root):
            return
        self._hwnd = self._user.GetAncestor(self.root.winfo_id(), 2)
        # Tk already redraws changed widgets on Configure/Expose. Its Windows
        # classes also request a full redraw (CS_HREDRAW | CS_VREDRAW) for every
        # resize, repainting unchanged descendants repeatedly. These classes
        # belong to this process; keep all other class flags and normal painting.
        for handle in (self._hwnd, self.root.winfo_id()):
            flags = self._user.GetClassLongPtrW(handle, -26)  # GCL_STYLE
            if flags & 0x0003:
                ctypes.set_last_error(0)
                previous = self._user.SetClassLongPtrW(handle, -26, flags & ~0x0003)
                if not previous and ctypes.get_last_error():
                    raise ctypes.WinError(ctypes.get_last_error())
        if not self._controls.SetWindowSubclass(self._hwnd, self._callback, id(self), 0):
            raise ctypes.WinError(ctypes.get_last_error())
        self.installed = True

    def begin(self):
        self.active = True

    def end(self):
        self.active = False

    def _dispatch(self, hwnd, message, wparam, lparam, _identifier, _data):
        try:
            if message == 0x0112 and (wparam & 0xFFF0) in (0xF000, 0xF010):
                # Never disable Tcl servicing here: newly exposed client areas
                # must lay out and paint before the user releases the frame.
                self.begin()
                try:
                    return self._controls.DefSubclassProc(hwnd, message, wparam, lparam)
                finally:
                    self.end()
            if message == 0x0231:  # WM_ENTERSIZEMOVE
                self.begin()
            if message in (0x0232, 0x001F, 0x0006):  # exit, cancel, activation change
                result = self._controls.DefSubclassProc(hwnd, message, wparam, lparam)
                self.end()
                return result
            if message == 0x0082:  # WM_NCDESTROY
                self._controls.RemoveWindowSubclass(hwnd, self._callback, id(self))
                self.installed = False
                result = self._controls.DefSubclassProc(hwnd, message, wparam, lparam)
                self.end()
                return result
        except Exception:
            self.end()
            logging.exception("窗口交互调度失败")
        return self._controls.DefSubclassProc(hwnd, message, wparam, lparam)



def window_interacting(root) -> bool:
    return bool(getattr(getattr(root, "_window_interaction", None), "active", False))


class Motion:
    """Short, keyed Tk transitions: a new action cancels the previous one."""
    def __init__(self, root):
        self.root = root
        self.pending = {}
        root.bind("<Destroy>", self._destroy, add="+")

    def cancel(self, key):
        task = self.pending.pop(key, None)
        if task is not None:
            self.root.after_cancel(task)

    def defer(self, key, callback, delay=0):
        self.cancel(key)

        def deliver():
            self.pending.pop(key, None)
            callback()

        self.pending[key] = self.root.after(delay, deliver) if delay else self.root.after_idle(deliver)

    def run(self, key, update, duration=180):
        self.cancel(key)
        if duration <= 0 or window_interacting(self.root) or not motion_enabled() or not self.root.winfo_viewable():
            update(1.0)
            return
        started = time.perf_counter()

        def frame():
            self.pending.pop(key, None)
            progress = 1.0 if window_interacting(self.root) else min(1.0, (time.perf_counter() - started) * 1000 / duration)
            update(1 - (1 - progress) ** 3)
            if progress < 1:
                self.pending[key] = self.root.after(16, frame)

        frame()

    def _destroy(self, event):
        if event.widget is self.root:
            for key in tuple(self.pending):
                self.cancel(key)


def rounded_image(image: Image.Image, radius: int, background: str) -> Image.Image:
    """Clip a UI surface's corners, retaining its authored artwork and content."""
    mask = Image.new("L", image.size)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, image.width - 1, image.height - 1), radius=radius, fill=255)
    result = Image.new("RGB", image.size, background)
    result.paste(image, (0, 0), mask)
    return result


def reveal_art(canvas):
    """Only the illustration fades; text, focus and actions stay immediately usable."""
    if not hasattr(canvas, "_rendered"):
        return
    root = canvas.winfo_toplevel()
    source = canvas._rendered
    ground = Image.new("RGB", source.size, canvas.cget("background"))

    def paint(progress):
        if canvas.winfo_exists() and canvas.winfo_ismapped():
            canvas._art.paste(source if progress == 1 else Image.blend(ground, source, progress))

    root._motion.run("page-art", paint, 200)


def flat_surface(fill: str, border: str, focus: bool = False) -> Image.Image:
    """A flat, small-radius native control face; states never move its content."""
    # ttk tiles the image center instead of stretching it. A generous solid center
    # avoids hundreds of tiny Windows drawing calls for each resized control.
    image = Image.new("RGBA", (768, 192))
    ImageDraw.Draw(image).rounded_rectangle((3, 3, 764, 188), radius=30, fill=fill, outline=border, width=6 if focus else 3)
    return image.resize((256, 64), Image.Resampling.LANCZOS)


def art_photo(root, name: str, size: tuple[int, int]) -> ImageTk.PhotoImage:
    image = root._ui_art[name].copy()
    image.thumbnail(size, Image.Resampling.LANCZOS)
    return ImageTk.PhotoImage(image, master=root)


def wallpaper_image(source: Image.Image, size: tuple[int, int], background: str, fill_width: bool = False) -> Image.Image:
    """Keep artwork at the right edge; extend/crop the quiet left area, never stretch."""
    width, height = size
    scale = max(width / source.width, height / source.height) if fill_width else height / source.height
    scaled = source.resize((max(1, round(source.width * scale)), max(1, round(source.height * scale))), Image.Resampling.LANCZOS)
    image = Image.new("RGB", size, background)
    # A UI reading scrim, not a character matte: the original wallpaper stays intact.
    # Reserve its quiet left half for native text and blend only the transition.
    mask = Image.new("L", (scaled.width, 1))
    mask.putdata([round(255 * min(1, max(0, (x / scaled.width - 0.54) / 0.15))) for x in range(scaled.width)])
    mask = mask.resize(scaled.size)
    if not fill_width:
        edge = Image.new("L", (1, scaled.height))
        edge.putdata([round(255 * min(1, y / max(1, height * 0.18), (height - 1 - y) / max(1, height * 0.18))) for y in range(scaled.height)])
        mask = ImageChops.multiply(mask, edge.resize(scaled.size))
    if scaled.mode == "RGBA":
        mask = ImageChops.multiply(mask, scaled.getchannel("A"))
    image.paste(scaled, (width - scaled.width, 0), mask)
    return image


def navigation_icon(root, name: str, selected: bool = False) -> ImageTk.PhotoImage:
    """One drawn line-icon family, with a matching selected state."""
    image = Image.new("RGBA", (72, 72))
    draw = ImageDraw.Draw(image)
    ink = "#FFFFFF" if selected else UI_COLORS["primary"]
    accent = "#DCEBED" if selected else "#B2D6C6"
    if name == "工作台":
        draw.ellipse((19, 19, 53, 53), fill=accent, outline=ink, width=4)
        draw.arc((6, 24, 66, 48), 0, 360, fill=ink, width=4)
        draw.ellipse((53, 9, 62, 18), fill="#ECD69B" if not selected else "#FFFFFF")
    elif name == "直播间":
        draw.rounded_rectangle((11, 19, 61, 59), radius=7, outline=ink, width=4)
        draw.line((23, 8, 36, 18, 49, 8), fill=ink, width=4)
        draw.polygon(((30, 28), (30, 49), (46, 39)), fill=ink)
        draw.ellipse((51, 10, 62, 21), fill=accent)
    elif name == "录播与总结":
        draw.rounded_rectangle((13, 10, 57, 62), radius=6, outline=ink, width=4)
        draw.rounded_rectangle((22, 18, 48, 29), radius=3, fill=accent)
        for y, end in ((24, 47), (36, 47), (48, 38)):
            draw.line((24, y, end, y), fill=ink, width=4)
    elif name == "切片":
        draw.ellipse((10, 42, 28, 60), fill=accent, outline=ink, width=4)
        draw.ellipse((44, 42, 62, 60), outline=ink, width=4)
        draw.line((22, 44, 52, 10), fill=ink, width=4)
        draw.line((50, 44, 20, 10), fill=ink, width=4)
    elif name == "投稿":
        draw.line((11, 47, 11, 60, 61, 60, 61, 47), fill=ink, width=4)
        draw.line((36, 48, 36, 10), fill=ink, width=4)
        draw.line((20, 27, 36, 10, 52, 27), fill=ink, width=4)
    elif name == "任务":
        for y in (17, 35, 53):
            draw.line((11, y, 16, y + 5, 24, y - 4), fill=ink, width=4)
            draw.line((33, y, 61, y), fill=ink, width=4)
    elif name == "账号":
        draw.ellipse((24, 10, 48, 34), fill=accent, outline=ink, width=4)
        draw.arc((12, 39, 60, 78), start=185, end=355, fill=ink, width=4)
        draw.line((12, 57, 60, 57), fill=ink, width=4)
    elif name == "设置":
        for x, y in ((18, 28), (36, 46), (54, 22)):
            draw.line((x, 10, x, 62), fill=ink, width=4)
            draw.ellipse((x - 6, y - 6, x + 6, y + 6), fill=accent, outline=ink, width=4)
    else:
        raise ValueError(f"Unknown navigation icon: {name}")
    return ImageTk.PhotoImage(image.resize((20, 20), Image.Resampling.LANCZOS), master=root)


class OrbitArt(Canvas):
    def __init__(self, master, width=190, height=44, background=UI_COLORS["bg"]):
        super().__init__(master, width=width, height=height, background=background, highlightthickness=0, takefocus=False)
        self._size = None
        self._image_item = self.create_image(0, 0, anchor="nw")
        self.bind("<Configure>", self._draw)

    def _draw(self, event=None):
        if not self.winfo_exists():
            return
        size = (max(1, self.winfo_width()), max(1, self.winfo_height()))
        if size == self._size:
            return
        root = self.winfo_toplevel()
        self._size = size
        root._motion.cancel("page-art")
        self._rendered = wallpaper_image(root._ui_art["wallpaper-orbits.png"], size, self.cget("background"))
        self._art = ImageTk.PhotoImage(self._rendered, master=root)
        self.itemconfigure(self._image_item, image=self._art)


class PageHeading(ttk.Frame):
    """A shared orbital wallpaper behind the native, readable page title."""
    def __init__(self, master, title: str, textvariable=None):
        super().__init__(master, style="App.TFrame")
        self.columnconfigure(0, weight=1)
        self.orbits = OrbitArt(self, width=1, height=58)
        self.orbits.grid(row=0, column=0, sticky="nsew")
        self._icon = navigation_icon(self.winfo_toplevel(), title)
        self.title_label = ttk.Label(self, text=title, textvariable=textvariable, image=self._icon, compound="left", style="NavTitle.TLabel", padding=(0, 0, 16, 0))
        self.title_label.grid(row=0, column=0, sticky="w", padx=12)


class CharacterArt(Canvas):
    """Full-width welcome wallpaper with a real ttk frame for text and actions."""
    def __init__(self, master, **kwargs):
        super().__init__(master, width=1, height=220, background=UI_COLORS["bg"], highlightthickness=0, takefocus=False, **kwargs)
        self._size = None
        self._image_item = self.create_image(0, 0, anchor="nw")
        self.intro = ttk.Frame(self, style="Hero.TFrame")
        self._intro_item = self.create_window(24, 22, window=self.intro, anchor="nw")
        self.bind("<Configure>", self._layout)
        self.intro.bind("<Configure>", self._layout)

    def _layout(self, _event=None):
        if not self.winfo_exists():
            return
        width, height = max(1, self.winfo_width()), max(1, self.winfo_height())
        content_width = max(1, max(440, width // 2) - 48)
        if int(float(self.itemcget(self._intro_item, "width"))) != content_width:
            self.itemconfigure(self._intro_item, width=content_width)
        requested_height = max(220, self.intro.winfo_reqheight() + 44)
        if int(self.cget("height")) != requested_height:
            self.configure(height=requested_height)
        size = (width, height)
        if size != self._size:
            root = self.winfo_toplevel()
            self._size = size
            root._motion.cancel("page-art")
            self._rendered = rounded_image(wallpaper_image(root._ui_art["wallpaper-studio.png"], size, SURFACE, fill_width=True), 16, UI_COLORS["bg"])
            self._art = ImageTk.PhotoImage(self._rendered, master=root)
            self.itemconfigure(self._image_item, image=self._art)


def install_theme(root):
    style = ttk.Style(theme="flatly")
    style.register_theme(ThemeDefinition(name="liveclip-character", colors=UI_COLORS))
    style.theme_use("liveclip-character")
    root.style = style
    root._motion = Motion(root)
    root._ui_art = {}
    for name in ("wallpaper-studio.png", "wallpaper-orbits.png", "character-sticker.png", "app-icon.png"):
        with Image.open(ASSET_DIR / name) as image:
            root._ui_art[name] = image.convert("RGBA")
    root._window_icon = art_photo(root, "app-icon.png", (256, 256))
    root.iconphoto(True, root._window_icon)
    root._empty_art = art_photo(root, "character-sticker.png", (64, 64))
    root._theme_images = []
    for name in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont"):
        tkfont.nametofont(name, root=root).configure(family="Microsoft YaHei UI", size=10)
    style.configure(".", font=("Microsoft YaHei UI", 10), background=SURFACE, foreground=UI_COLORS["fg"], bordercolor=UI_COLORS["border"], lightcolor=SURFACE, darkcolor=SURFACE, focuscolor=UI_COLORS["primary"])
    # Native dialogs, text editors and combobox popdowns share the same palette.
    for widget_class in ("Text", "Listbox", "Menu"):
        for option, value in (("background", UI_COLORS["inputbg"]), ("foreground", UI_COLORS["fg"]), ("selectBackground", UI_COLORS["selectbg"]), ("selectForeground", UI_COLORS["selectfg"])):
            root.option_add(f"*{widget_class}.{option}", value)
    for option, value in (("insertBackground", UI_COLORS["primary"]), ("highlightBackground", UI_COLORS["border"]), ("highlightColor", UI_COLORS["primary"])):
        root.option_add(f"*Text.{option}", value)
    for name, background in (("TFrame", SURFACE), ("App.TFrame", UI_COLORS["bg"]), ("Surface.TFrame", SURFACE), ("Toolbar.TFrame", UI_COLORS["bg"]), ("Header.TFrame", HEADER), ("HeaderAccent.TFrame", "#D7DFEB"), ("Rail.TFrame", RAIL), ("Hero.TFrame", SURFACE), ("Deck.TFrame", SURFACE), ("Mint.TFrame", SURFACE), ("Blue.TFrame", SURFACE)):
        style.configure(name, background=background)
    for name, fill in (("Card.TFrame", SURFACE), ("Rail.TFrame", RAIL)):
        face = Image.new("RGB", (512, 256), UI_COLORS["bg"])
        ImageDraw.Draw(face).rounded_rectangle((1, 1, 510, 254), radius=16, fill=fill)
        photo = ImageTk.PhotoImage(face, master=root)
        root._theme_images.append(photo)
        element_name = "CharacterUI." + name
        style.element_create(element_name, "image", photo, border=18, width=96, height=96, sticky="nsew")
        style.layout(name, [(element_name, {"sticky": "nsew"})])
        style.configure(name, background=fill)
    labels = {
        "TLabel": (SURFACE, UI_COLORS["fg"], 10, "normal"), "App.TLabel": (UI_COLORS["bg"], UI_COLORS["fg"], 10, "normal"),
        "HeaderTitle.TLabel": (HEADER, UI_COLORS["fg"], 15, "bold"), "HeaderSubtitle.TLabel": (HEADER, MUTED, 9, "normal"),
        "Section.TLabel": (SURFACE, UI_COLORS["fg"], 12, "bold"), "Muted.TLabel": (SURFACE, MUTED, 9, "normal"),
        "AccountTitle.TLabel": (SURFACE, UI_COLORS["fg"], 13, "bold"), "AccountText.TLabel": (SURFACE, UI_COLORS["fg"], 10, "normal"),
        "AccountMuted.TLabel": (SURFACE, MUTED, 10, "normal"), "AccountPlatform.TLabel": (TABLE_HEADER, UI_COLORS["selectfg"], 11, "normal"),
        "AccountBadge.TLabel": ("#E3EFDD", UI_COLORS["success"], 9, "normal"),
        "DashboardTitle.TLabel": (SURFACE, UI_COLORS["fg"], 19, "bold"), "DashboardMuted.TLabel": (UI_COLORS["bg"], MUTED, 9, "normal"),
        "DashboardStatus.TLabel": (SURFACE, UI_COLORS["success"], 9, "bold"), "StatValue.TLabel": (UI_COLORS["bg"], UI_COLORS["primary"], 11, "bold"),
        "NavTitle.TLabel": (UI_COLORS["bg"], UI_COLORS["fg"], 15, "bold"), "NavMuted.TLabel": (UI_COLORS["bg"], MUTED, 9, "normal"),
        "RailTitle.TLabel": (RAIL, UI_COLORS["primary"], 11, "bold"), "RailMuted.TLabel": (RAIL, MUTED, 8, "normal"),
        "Empty.TLabel": (SURFACE, MUTED, 10, "normal"), "Step.TLabel": ("#E3EFEC", UI_COLORS["success"], 9, "bold"),
        "BlueStep.TLabel": (TABLE_HEADER, UI_COLORS["info"], 9, "bold"),
        "MintMuted.TLabel": (SURFACE, MUTED, 9, "normal"), "BlueMuted.TLabel": (SURFACE, MUTED, 9, "normal"),
    }
    for name, (background, foreground, size, weight) in labels.items():
        style.configure(name, background=background, foreground=foreground, font=("Microsoft YaHei UI", size, weight))
    style.configure("AccountBadge.TLabel", padding=(7, 3))
    style.configure("AccountPlatform.TLabel", padding=(14, 10))
    for name in ("Step.TLabel", "BlueStep.TLabel"):
        style.configure(name, padding=(8, 2))

    def element(name, fill, border, hover, pressed):
        images = {}
        for state, face, edge in (("normal", fill, border), ("active", hover, border), ("pressed", pressed, border), ("focus", fill, UI_COLORS["primary"]), ("disabled", DISABLED_BG, "#C3CFDC")):
            photo = ImageTk.PhotoImage(flat_surface(face, edge, state == "focus"), master=root)
            root._theme_images.append(photo)
            images[state] = photo
        style.element_create(name, "image", images["normal"], ("disabled", images["disabled"]), ("pressed", images["pressed"]), ("focus", images["focus"]), ("active", images["active"]), border=11, width=28, height=28, sticky="nsew")
        return name

    buttons = {
        "TButton": (SURFACE, UI_COLORS["fg"], "#B8C7D5", "#E8F0F3", "#D8E6EB"),
        "primary.TButton": (UI_COLORS["primary"], "#FFFFFF", UI_COLORS["primary"], "#365F6D", "#2D5262"),
        "success.TButton": (UI_COLORS["success"], "#FFFFFF", UI_COLORS["success"], "#355C46", "#2C4E3C"),
        "danger.TButton": (UI_COLORS["danger"], "#FFFFFF", UI_COLORS["danger"], "#913B54", "#793047"),
        "Header.TButton": (HEADER, UI_COLORS["primary"], "#B8C7D5", "#E6EDF5", "#D8E3EF"),
    }
    for name in ("secondary.TButton", "Pipeline.TButton", "AccountOutline.TButton", "AccountCancel.TButton"):
        buttons[name] = buttons["TButton"]
    buttons["AccountAction.TButton"] = buttons["primary.TButton"]
    buttons["Mint.Pipeline.TButton"] = (SURFACE, UI_COLORS["primary"], SURFACE, "#E3EFEC", "#D5E7E1")
    buttons["Blue.Pipeline.TButton"] = (SURFACE, UI_COLORS["info"], SURFACE, "#E1E9F4", "#D6E3F1")
    for role in ("primary", "secondary", "success", "info", "warning", "danger"):
        buttons[f"{role}.Outline.TButton"] = (SURFACE, UI_COLORS[role], "#B8C7D5", "#E8F0F3", "#D8E6EB")
    for name, (fill, foreground, border, hover, pressed) in buttons.items():
        style.configure(name, foreground=foreground, background=HEADER if name == "Header.TButton" else SURFACE, focuscolor=foreground, focusthickness=1, padding=(7, 1), font=("Microsoft YaHei UI", 9), relief="flat")
        face = element(f"CharacterUI.{name}", fill, border, hover, pressed)
        style.layout(name, [(face, {"sticky": "nsew", "children": [("Button.focus", {"sticky": "nsew", "children": [("Button.padding", {"sticky": "nsew", "children": [("Button.label", {"sticky": "nsew"})]})]})]})])
        style.map(name, foreground=[("disabled", DISABLED_FG), ("!disabled", foreground)], background=[("disabled", HEADER if name == "Header.TButton" else SURFACE), ("!disabled", HEADER if name == "Header.TButton" else SURFACE)])
    for name in ("Pipeline.TButton", "Mint.Pipeline.TButton", "Blue.Pipeline.TButton"):
        style.configure(name, font=("Microsoft YaHei UI", 10, "bold"), anchor="w")
    style.configure("Inline.TButton", font=("Microsoft YaHei UI", 9), background=SURFACE, foreground=UI_COLORS["primary"], padding=(7, 3), focuscolor=UI_COLORS["primary"])
    style.layout("Inline.TButton", [("Button.focus", {"sticky": "nsew", "children": [("Button.padding", {"sticky": "nsew", "children": [("Button.label", {"sticky": "nsew"})]})]})])
    style.map("Inline.TButton", foreground=[("disabled", DISABLED_FG), ("active", "#365F6D")])

    field = element("CharacterUI.field", UI_COLORS["inputbg"], UI_COLORS["border"], UI_COLORS["inputbg"], UI_COLORS["inputbg"])
    style.configure("TEntry", padding=(4, 0), foreground=UI_COLORS["fg"], fieldbackground=UI_COLORS["inputbg"], insertcolor=UI_COLORS["primary"], selectbackground=UI_COLORS["selectbg"], selectforeground=UI_COLORS["selectfg"])
    style.layout("TEntry", [(field, {"sticky": "nsew", "children": [("Entry.padding", {"sticky": "nsew", "children": [("Entry.textarea", {"sticky": "nsew"})]})]})])
    style.configure("TCombobox", padding=(4, 0), foreground=UI_COLORS["fg"], fieldbackground=UI_COLORS["inputbg"], arrowcolor=UI_COLORS["primary"], selectbackground=UI_COLORS["selectbg"], selectforeground=UI_COLORS["selectfg"])
    style.map("TCombobox", foreground=[("disabled", DISABLED_FG), ("!disabled", UI_COLORS["fg"])])
    style.layout("TCombobox", [(field, {"sticky": "nsew", "children": [("Combobox.padding", {"sticky": "nsew", "children": [("Combobox.downarrow", {"side": "right", "sticky": ""}), ("Combobox.textarea", {"sticky": "nsew"})]})]})])
    style.configure("AccountMenu.TMenubutton", padding=(6, 0), foreground=UI_COLORS["fg"])
    menu = element("CharacterUI.menu", SURFACE, "#B8C7D5", "#E8F0F3", "#D8E6EB")
    style.layout("AccountMenu.TMenubutton", [(menu, {"sticky": "nsew", "children": [("Menubutton.padding", {"sticky": "nsew", "children": [("TMenubutton.indicator", {"side": "right", "sticky": ""}), ("Menubutton.label", {"side": "left"})]})]})])

    style.configure("Surface.TLabelframe", background=SURFACE, bordercolor="#C4CFDE", borderwidth=1, relief="solid")
    style.configure("Surface.TLabelframe.Label", background=SURFACE, foreground=UI_COLORS["primary"], font=("Microsoft YaHei UI", 10, "bold"))
    style.configure("Treeview", rowheight=36, font=("Microsoft YaHei UI", 10), background=SURFACE, fieldbackground=SURFACE, foreground=UI_COLORS["fg"], borderwidth=0)
    style.map("Treeview", background=[("selected", UI_COLORS["selectbg"])], foreground=[("selected", UI_COLORS["selectfg"])])
    style.configure("Treeview.Heading", background=TABLE_HEADER, foreground=UI_COLORS["selectfg"], relief="flat", padding=(10, 8), font=("Microsoft YaHei UI", 9, "bold"))
    style.map("Treeview.Heading", background=[("active", "#D0DDED")], foreground=[("active", UI_COLORS["selectfg"])])
    for name, height in (("SettingsNav.Treeview", 40), ("Navigation.Treeview", 40)):
        style.configure(name, rowheight=height, font=("Microsoft YaHei UI", 10), background=RAIL, fieldbackground=RAIL, foreground=UI_COLORS["primary"], borderwidth=0, indent=8)
        style.map(name, background=[("selected", RAIL)], foreground=[("selected", "#FFFFFF" if name == "Navigation.Treeview" else UI_COLORS["selectfg"])])
        plain = ImageTk.PhotoImage(Image.new("RGB", (256, 40), RAIL), master=root)
        pill = Image.new("RGB", (256, 40), RAIL)
        ImageDraw.Draw(pill).rounded_rectangle((1, 3, 254, 36), radius=9, fill=UI_COLORS["primary"] if name == "Navigation.Treeview" else UI_COLORS["selectbg"])
        selected = ImageTk.PhotoImage(pill, master=root)
        root._theme_images.extend((plain, selected))
        item = "CharacterUI." + name + ".selection"
        style.element_create(item, "image", plain, ("selected", selected), border=(12, 10), width=48, height=40, sticky="nsew")
        style.layout(name + ".Item", [(item, {"sticky": "nsew", "children": [("Treeitem.padding", {"sticky": "nsew", "children": [("Treeitem.indicator", {"side": "left"}), ("Treeitem.image", {"side": "left"}), ("Treeitem.text", {"sticky": "nsew"})]})]})])
    style.configure("TNotebook", background=UI_COLORS["bg"], borderwidth=0, tabmargins=(0, 0, 0, 0))
    style.configure("TNotebook.Tab", padding=(18, 9), background=TABLE_HEADER, foreground=UI_COLORS["fg"], focuscolor=UI_COLORS["primary"], focusthickness=1, font=("Microsoft YaHei UI", 10))
    style.map("TNotebook.Tab", background=[("selected", SURFACE), ("active", "#DFE9F2")], foreground=[("selected", UI_COLORS["primary"]), ("!selected", MUTED)])
    style.configure("TPanedwindow", background="#D3DDE9")
    style.configure("TSeparator", background="#D3DDE9")
    for orientation in ("Horizontal", "Vertical"):
        name = f"{orientation}.TScrollbar"
        # The bundled theme's thumb has a one-pixel tile center. Native drawing
        # keeps long scrollbars O(1) instead of hundreds of image blits per frame.
        thumb = f"CharacterUI.{orientation}.Scrollbar.thumb"
        style.element_create(thumb, "from", "clam", f"{orientation}.Scrollbar.thumb")
        style.layout(name, [(f"{orientation}.Scrollbar.trough", {"sticky": "nsew", "children": [(thumb, {"expand": "1", "sticky": "nsew"})]})])
        style.configure(name, background="#657481", troughcolor=SURFACE, bordercolor=SURFACE, arrowcolor=MUTED, arrowsize=8, borderwidth=0, relief="flat", gripcount=0)
        style.map(name, background=[("pressed", UI_COLORS["primary"]), ("active", "#526A7D")])
    style.configure("TCheckbutton", font=("Microsoft YaHei UI", 9), background=SURFACE)
    style.configure("App.TCheckbutton", background=UI_COLORS["bg"], font=("Microsoft YaHei UI", 9))
    return style
