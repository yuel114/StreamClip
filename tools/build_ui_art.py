"""Build offline UI-size derivatives from verified generated originals."""
import hashlib
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageOps, PngImagePlugin

ASSETS = Path(__file__).resolve().parents[1] / "assets" / "ui"


def build():
    provenance = json.loads((ASSETS / "generation-provenance.json").read_text(encoding="utf-8"))
    sources = {item["file"]: item for item in provenance["sources"]}
    records = []

    def record(name, usage, source=None, recipe="Original generated pixels, unchanged."):
        path = ASSETS / name
        item = {"file": name, "usage": usage, "derived_from": source or name,
                "recipe": recipe, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        with Image.open(path) as image:
            image.load()
            item.update(size=list(image.size), mode=image.mode)
            if path.suffix == ".ico":
                item["sizes"] = sorted([list(size) for size in image.ico.sizes()])
            else:
                assert image.info.get("impeccable:prompt"), f"Missing prompt: {name}"
        records.append(item)

    def save(name, image, source, usage, recipe):
        metadata = PngImagePlugin.PngInfo()
        metadata.add_text("impeccable:prompt", sources[source]["prompt"])
        metadata.add_text("Source", source + "; generation-provenance.json")
        metadata.add_text("Description", recipe)
        image.save(ASSETS / name, pnginfo=metadata, optimize=True)
        record(name, usage, source, recipe)

    for name, usage in (("wallpaper-studio.png", ["工作台角色场景壁纸"]),
                        ("wallpaper-sky.png", ["独立天空壁纸", "页头背景来源"]),
                        ("character-sticker.png", ["顶栏头像", "列表空态"]),
                        ("app-icon-source.png", ["通用视频录制、剪辑与上传图标原图"]),
                        ("wallpaper-ice-studio.png", ["冰蓝蝶影皮肤角色壁纸"]),
                        ("wallpaper-ice-sky.png", ["冰蓝蝶影皮肤蝴蝶纹样页头原图"])):
        assert hashlib.sha256((ASSETS / name).read_bytes()).hexdigest() == sources[name]["sha256"]
        record(name, usage)

    with Image.open(ASSETS / "wallpaper-sky.png") as source:
        # A viewport crop, not a new illustration or a claimed alpha matte.
        banner = ImageOps.fit(source.convert("RGB"), (1800, 300), centering=(1.0, 0.34))
    save("wallpaper-orbits.png", banner, "wallpaper-sky.png", ["七页页头", "导航底部"],
         "Proportional 1800x300 viewport crop of sky wallpaper, vertical center 0.34; no painted content added.")

    with Image.open(ASSETS / "wallpaper-ice-sky.png") as source:
        banner = ImageOps.fit(source.convert("RGB"), (1800, 300), centering=(1.0, 0.5))
    save("wallpaper-ice-header.png", banner, "wallpaper-ice-sky.png", ["冰蓝蝶影皮肤页头"],
         "Proportional 1800x300 center crop of the generated butterfly wallpaper; original pixels retained without painted additions.")

    with Image.open(ASSETS / "app-icon-source.png") as source:
        assert source.size == (1024, 1024)
        assert source.convert("RGBA").getchannel("A").getextrema() == (255, 255), "App icon source must be opaque."
        icon = source.convert("RGBA").resize((768, 768), Image.Resampling.LANCZOS)
    # Transparency is applied only to the application tile's rounded corners.
    mask = Image.new("L", icon.size)
    ImageDraw.Draw(mask).rounded_rectangle((8, 8, 759, 759), radius=164, fill=255)
    icon.putalpha(mask)
    icon = icon.resize((256, 256), Image.Resampling.LANCZOS)
    save("app-icon.png", icon, "app-icon-source.png", ["窗口图标", "侧栏应用标识"],
         "Proportional generic video-tool icon resize with rounded application-tile corners; solid background retained.")
    icon.save(ASSETS / "app-icon.ico", format="ICO", sizes=[(n, n) for n in (16, 24, 32, 48, 64, 128, 256)])
    record("app-icon.ico", ["Windows EXE 图标"], "app-icon-source.png", "Seven ICO sizes derived from app-icon.png.")
    manifest = {"method": "generated-images-with-offline-derivatives", "new_ai_generation": True,
                "generation_provenance": "generation-provenance.json", "rebuild": "python -X utf8 -B tools/build_ui_art.py", "assets": records}
    (ASSETS / "art-provenance.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Built and verified {len(records)} UI assets from {len(sources)} generated originals.")


if __name__ == "__main__":
    build()
