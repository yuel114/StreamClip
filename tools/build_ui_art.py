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

    for name, usage in (("wallpaper-day.png", ["极昼地貌页头来源", "旧Tk工作台"]),
                        ("wallpaper-night.png", ["黑夜地貌页头来源"]),
                        ("wallpaper-sun.png", ["极昼工作台太阳娘壁纸"]),
                        ("wallpaper-moon.png", ["黑夜工作台月亮娘壁纸"]),
                        ("app-icon-source.png", ["通用视频录制、剪辑与上传图标原图"])):
        assert sources[name]["references"] == [], "Bundled artwork must not depend on character references."
        assert hashlib.sha256((ASSETS / name).read_bytes()).hexdigest() == sources[name]["sha256"]
        record(name, usage)

    for key in ("day", "night"):
        name = f"wallpaper-{key}.png"
        with Image.open(ASSETS / name) as source:
            banner = ImageOps.fit(source.convert("RGB"), (1800, 300), centering=(1.0, 0.5))
        save(f"wallpaper-{key}-header.png", banner, name, ["页头背景"],
             "Proportional 1800x300 center crop of the original terrain; no painted content added.")

    with Image.open(ASSETS / "app-icon-source.png") as source:
        assert source.size == (1024, 1024)
        assert source.convert("RGBA").getchannel("A").getextrema() == (255, 255), "App icon source must be opaque."
        icon = source.convert("RGBA").resize((768, 768), Image.Resampling.LANCZOS)
    # Transparency is applied only to the application tile's rounded corners.
    mask = Image.new("L", icon.size)
    ImageDraw.Draw(mask).rounded_rectangle((8, 8, 759, 759), radius=164, fill=255)
    icon.putalpha(mask)
    icon = icon.resize((256, 256), Image.Resampling.LANCZOS)
    save("app-icon.png", icon, "app-icon-source.png", ["窗口图标", "侧栏应用标识", "旧版顶栏和列表空态"],
         "Proportional generic video-tool icon resize with rounded application-tile corners; solid background retained.")
    icon.save(ASSETS / "app-icon.ico", format="ICO", sizes=[(n, n) for n in (16, 24, 32, 48, 64, 128, 256)])
    record("app-icon.ico", ["Windows EXE 图标"], "app-icon-source.png", "Seven ICO sizes derived from app-icon.png.")
    manifest = {"method": "generated-images-with-offline-derivatives", "new_ai_generation": True,
                "generation_provenance": "generation-provenance.json", "rebuild": "python -X utf8 -B tools/build_ui_art.py", "assets": records}
    (ASSETS / "art-provenance.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Built and verified {len(records)} UI assets from {len(sources)} generated originals.")


if __name__ == "__main__":
    build()
