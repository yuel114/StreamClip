"""Bundled Qt skins; appearance is saved separately from business settings."""

import json
import logging
from pathlib import Path

from PySide6.QtCore import QObject, Property, Signal, Slot

from app import write_json_atomic


SKINS = {
    "day": {
        "name": "极昼",
        "dark": False,
        "scene": "wallpaper-sun.png",
        "sceneFit": True,
        "sceneBackground": "#F9F9F9",
        "header": "wallpaper-day-header.png",
        "colors": {
            "background": "#F2F3F3", "surface": "#FFFFFF", "rail": "#EAEBEB",
            "ink": "#242827", "muted": "#57615D", "primary": "#246550",
            "primaryHover": "#1D5543", "primaryPressed": "#174535",
            "onPrimary": "#FFFFFF", "danger": "#AC3441", "warning": "#855B14",
            "navSelected": "#D3DED9", "navHover": "#DFE3E1",
            "selection": "#DCECE4", "selectionInk": "#214F3E", "listHover": "#F0F3F1",
            "control": "#FFFFFF", "controlHover": "#E9EEEB", "controlPressed": "#DCE4DF",
            "controlBorder": "#C6CECA", "button": "#FAFAFA",
            "fieldBorder": "#909D96", "placeholder": "#626D67",
            "disabled": "#E4E7E5", "disabledInk": "#7A847E", "disabledText": "#5D6761",
            "segmented": "#E2E6E3", "segmentHover": "#F1F4F2", "segmentBorder": "#CDD5D0",
            "choicePressed": "#CDDFD4", "switchOff": "#728178", "switchDisabled": "#BCC5BF",
            "switchThumb": "#FFFFFF", "dialog": "#FAFBFA", "shadow": "#30202422",
            "scrim": "#60202422", "unavailable": "#7A847E",
        },
    },
    "night": {
        "name": "黑夜",
        "dark": True,
        "scene": "wallpaper-moon.png",
        "sceneFit": True,
        "sceneBackground": "#232426",
        "header": "wallpaper-night-header.png",
        "colors": {
            "background": "#151617", "surface": "#202122", "rail": "#1C1D1E",
            "ink": "#F0F2F1", "muted": "#BEC7C1", "primary": "#8DD9BA",
            "primaryHover": "#A8E7CD", "primaryPressed": "#74C4A3",
            "onPrimary": "#10251C", "danger": "#F398A0", "warning": "#E3BE76",
            "navSelected": "#34463E", "navHover": "#2B312E",
            "selection": "#314E40", "selectionInk": "#D9F3E5", "listHover": "#2C312E",
            "control": "#2B2E2C", "controlHover": "#373D39", "controlPressed": "#414B45",
            "controlBorder": "#525C55", "button": "#202122",
            "fieldBorder": "#69766E", "placeholder": "#A4AFA7",
            "disabled": "#292D2A", "disabledInk": "#77867B", "disabledText": "#A5B1A9",
            "segmented": "#191C1A", "segmentHover": "#2C342F", "segmentBorder": "#465049",
            "choicePressed": "#3C5F4C", "switchOff": "#56685C", "switchDisabled": "#3B443E",
            "switchThumb": "#FFFFFF", "dialog": "#262927", "shadow": "#80000000",
            "scrim": "#99000000", "unavailable": "#7B8B80",
        },
    },
}


class UiTheme(QObject):
    changed = Signal()
    transitioningChanged = Signal()
    error = Signal(str)

    def __init__(self, path, parent=None):
        super().__init__(parent)
        self.path = Path(path)
        self._key = "day"
        self._transitioning = False
        try:
            saved = json.loads(self.path.read_text(encoding="utf-8"))
            key = saved.get("skin") if isinstance(saved, dict) else None
            # Read old choices without rewriting the user's preference on startup.
            if isinstance(key, str):
                key = {"mint": "day", "rose": "night"}.get(key, key)
            if isinstance(key, str) and key in SKINS:
                self._key = key
        except FileNotFoundError:
            pass
        except (OSError, ValueError):
            logging.warning("无法读取皮肤偏好，使用默认皮肤；原文件保留。")

    @Property(str, notify=changed)
    def key(self):
        return self._key

    @Property("QVariantMap", notify=changed)
    def current(self):
        return SKINS[self._key]

    @Property(str, notify=changed)
    def nextKey(self):
        keys = list(SKINS)
        return keys[(keys.index(self._key) + 1) % len(keys)]

    @Property(str, notify=changed)
    def nextName(self):
        return SKINS[self.nextKey]["name"]

    @Property(bool, notify=transitioningChanged)
    def transitioning(self):
        return self._transitioning

    @transitioning.setter
    def transitioning(self, value):
        if self._transitioning != value:
            self._transitioning = value
            self.transitioningChanged.emit()

    @Slot(str, result=bool)
    def select(self, key):
        if key not in SKINS:
            self.error.emit("皮肤不存在。")
            return False
        if key == self._key:
            return True
        try:
            write_json_atomic(self.path, {"skin": key})
        except OSError:
            logging.exception("保存皮肤偏好失败")
            self.error.emit("皮肤未切换：无法保存偏好，请检查数据目录是否可写。")
            return False
        self._key = key
        self.changed.emit()
        return True
