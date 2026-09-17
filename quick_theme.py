"""Bundled Qt skins; appearance is saved separately from business settings."""

import json
import logging
from pathlib import Path

from PySide6.QtCore import QObject, Property, Signal, Slot

from app import write_json_atomic


SKINS = {
    "mint": {
        "name": "羽啾 · 薄荷",
        "profileName": "羽啾chu2u",
        "profileUrl": "https://space.bilibili.com/2138961136",
        "scene": "wallpaper-studio.png",
        "sceneFit": False,
        "header": "wallpaper-sky.png",
        "colors": {
            "background": "#EEF2F5", "surface": "#FCFDFE", "rail": "#E3EFEC",
            "ink": "#34445F", "muted": "#52657C", "primary": "#426E78",
            "primaryHover": "#365D67", "primaryPressed": "#304D65",
            "onPrimary": "#FFFFFF", "danger": "#A24761", "warning": "#B64458",
            "navSelected": "#CFDFDE", "navHover": "#D8E7E4",
            "selection": "#D9E8ED", "selectionInk": "#304D65", "listHover": "#EDF2F8",
            "control": "#FFFFFF", "controlHover": "#E3ECEC", "controlPressed": "#D8E6E5",
            "controlBorder": "#CDD7DC", "button": "#F6F8FC",
            "fieldBorder": "#AABAC4", "placeholder": "#627582",
            "disabled": "#E8ECEF", "disabledInk": "#77838B", "disabledText": "#596A7E",
            "segmented": "#E2E9EC", "segmentHover": "#EEF3F4", "segmentBorder": "#CFDADD",
            "choicePressed": "#D8E6EB", "switchOff": "#83969F", "switchDisabled": "#C1CCD1",
            "dialog": "#F9FBFC", "shadow": "#3024313B", "scrim": "#502A3641",
            "unavailable": "#879BAC",
        },
    },
    # Keep the stored key so the previous second-skin preference survives upgrades.
    "rose": {
        "name": "冰蓝 · 蝶影",
        "profileName": "雨纪_Ameki",
        "profileUrl": "https://space.bilibili.com/1932862336",
        "scene": "wallpaper-ice-studio.png",
        "sceneFit": True,
        "header": "wallpaper-ice-header.png",
        "colors": {
            "background": "#F0F3F8", "surface": "#FCFDFF", "rail": "#DFEAF8",
            "ink": "#303D58", "muted": "#52657F", "primary": "#3D629D",
            "primaryHover": "#325487", "primaryPressed": "#294770",
            "onPrimary": "#FFFFFF", "danger": "#A43551", "warning": "#A43551",
            "navSelected": "#D7DDF3", "navHover": "#D2E3F7",
            "selection": "#E4E0F5", "selectionInk": "#45416F", "listHover": "#EEF3FB",
            "control": "#FFFFFF", "controlHover": "#E6EEFA", "controlPressed": "#D8E5F7",
            "controlBorder": "#CAD5E5", "button": "#F5F7FB",
            "fieldBorder": "#A2B3CC", "placeholder": "#5D6F88",
            "disabled": "#E6EBF2", "disabledInk": "#78869A", "disabledText": "#5C6C83",
            "segmented": "#E2E8F3", "segmentHover": "#EEF2FC", "segmentBorder": "#CDD7EA",
            "choicePressed": "#DADDF3", "switchOff": "#8298B8", "switchDisabled": "#C3CFDF",
            "dialog": "#F8FAFE", "shadow": "#30233352", "scrim": "#50303D58",
            "unavailable": "#879BB6",
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
        self._key = "mint"
        self._transitioning = False
        try:
            saved = json.loads(self.path.read_text(encoding="utf-8"))
            key = saved.get("skin") if isinstance(saved, dict) else None
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
