#!/usr/bin/env python3
"""Generate the images for the extensions.blender.org listing into store/ (icon, featured image, previews).

Uses the real Blender screenshots in docs/images/ and a macOS system font (Apple SD Gothic Neo) for the text.

  python3 tools/make_store_assets.py
"""
import math
import pathlib

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = pathlib.Path(__file__).resolve().parent.parent
IMG = ROOT / "docs" / "images"
OUT = ROOT / "store"
FONT = "/System/Library/Fonts/AppleSDGothicNeo.ttc"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    # AppleSDGothicNeo.ttc holds several weights; pick by style name.
    for i in range(12):
        try:
            f = ImageFont.truetype(FONT, size, index=i)
        except OSError:
            break
        if (f.getname()[1] == "Bold") == bold and f.getname()[1] in ("Bold", "Regular"):
            return f
    return ImageFont.truetype(FONT, size, index=0)


def dome(radius: int) -> Image.Image:
    """半球(点字のドット)を、斜め上からの光で shading した RGBA 画像。"""
    n = radius * 2
    y, x = np.mgrid[-radius:radius, -radius:radius].astype(float)
    r2 = (x * x + y * y) / (radius * radius)
    inside = r2 <= 1.0
    nz = np.sqrt(np.clip(1.0 - r2, 0, 1))
    nx, ny = x / radius, y / radius
    light = np.array([-0.45, -0.55, 0.70]); light /= np.linalg.norm(light)
    lam = np.clip(nx * light[0] + ny * light[1] + nz * light[2], 0, 1)
    spec = np.clip(lam, 0, 1) ** 24 * 0.55
    shade = 0.50 + 0.50 * lam
    base = np.array([244, 247, 253], dtype=float)
    shadow_tint = np.array([150, 170, 215], dtype=float)
    rgb = (base * shade[..., None] + shadow_tint * (1 - shade[..., None]) * 0.35)
    rgb = np.clip(rgb + spec[..., None] * 255, 0, 255)
    alpha = np.where(inside, 255, 0).astype(np.uint8)
    # soften the rim
    rim = np.clip((1.0 - np.sqrt(r2)) * radius / 1.5, 0, 1)
    alpha = (alpha * rim).astype(np.uint8)
    out = np.dstack([rgb.astype(np.uint8), alpha])
    return Image.fromarray(out, "RGBA")


def rounded_gradient(size: int, radius: int, c1, c2) -> Image.Image:
    a = np.linspace(0, 1, size)
    t = (a[None, :] + a[:, None]) / 2
    img = np.zeros((size, size, 3), dtype=np.uint8)
    for k in range(3):
        img[..., k] = (c1[k] * (1 - t) + c2[k] * t).astype(np.uint8)
    base = Image.fromarray(img, "RGB").convert("RGBA")
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, size - 1, size - 1), radius=radius, fill=255)
    base.putalpha(mask)
    return base


def make_icon(size: int = 1024) -> Image.Image:
    icon = rounded_gradient(size, int(size * 0.22), (22, 58, 138), (60, 132, 236))
    # 点字セル「て」(点1,2,3 と 点4,5)
    cell = [(0, 0), (0, 1), (0, 2), (1, 0), (1, 1)]
    r = int(size * 0.105)
    xs = [size * 0.37, size * 0.63]
    ys = [size * 0.26, size * 0.50, size * 0.74]
    shadow = Image.new("RGBA", icon.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    d = dome(r)
    for cx, cy in cell:
        x, y = xs[cx], ys[cy]
        off = int(r * 0.22)
        sd.ellipse((x - r + off, y - r + off * 1.3, x + r + off, y + r + off * 1.3), fill=(5, 20, 70, 150))
    shadow = shadow.filter(ImageFilter.GaussianBlur(r * 0.22))
    icon = Image.alpha_composite(icon, shadow)
    for cx, cy in cell:
        x, y = xs[cx], ys[cy]
        icon.alpha_composite(d, (int(x - r), int(y - r)))
    return icon


def fit(im: Image.Image, box_w: int, box_h: int) -> Image.Image:
    s = min(box_w / im.width, box_h / im.height)
    return im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.LANCZOS)


def shadowed(im: Image.Image, canvas: Image.Image, xy, radius: int = 18) -> None:
    sh = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((xy[0] + 8, xy[1] + 14, xy[0] + im.width + 8, xy[1] + im.height + 14), radius=radius, fill=(0, 0, 0, 120))
    canvas.alpha_composite(sh.filter(ImageFilter.GaussianBlur(18)))
    mask = Image.new("L", im.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, im.width - 1, im.height - 1), radius=radius, fill=255)
    canvas.paste(im.convert("RGB"), xy, mask)


def dark_canvas(w=1920, h=1080, c1=(24, 26, 32), c2=(38, 42, 54)) -> Image.Image:
    t = np.linspace(0, 1, w)[None, :] * 0.6 + np.linspace(0, 1, h)[:, None] * 0.4
    arr = np.dstack([(c1[k] * (1 - t) + c2[k] * t).astype(np.uint8) for k in range(3)])
    return Image.fromarray(arr, "RGB").convert("RGBA")


def make_featured(icon: Image.Image) -> Image.Image:
    cv = dark_canvas()
    shot = Image.open(IMG / "view-cylinder.png").convert("RGB")
    shot = fit(shot, 900, 960)
    shadowed(shot, cv, (1920 - shot.width - 70, (1080 - shot.height) // 2))
    ic = icon.resize((190, 190), Image.LANCZOS)
    cv.alpha_composite(ic, (90, 130))
    d = ImageDraw.Draw(cv)
    d.text((90, 360), "Tenji P-Fab:", font=font(112, True), fill=(255, 255, 255))
    d.text((90, 490), "Japanese Braille", font=font(112, True), fill=(120, 178, 255))
    d.text((94, 660), "Project Japanese braille onto 3D models", font=font(44), fill=(226, 230, 240))
    d.text((94, 730), "日本語を点字にして、3Dモデルの表面に載せる", font=font(40), fill=(176, 184, 204))
    d.text((94, 880), "Blender 5.2+  ·  Live update  ·  Adjustable dot dimensions", font=font(32), fill=(140, 150, 175))
    return cv.convert("RGB")


def letterbox(images: list[Image.Image], gap: int = 40, margin: int = 60) -> Image.Image:
    cv = dark_canvas(c1=(43, 43, 46), c2=(52, 52, 56))
    h = 1080 - 2 * margin
    scaled = []
    for im in images:
        s = h / im.height
        scaled.append(im.resize((int(im.width * s), h), Image.LANCZOS))
    total = sum(i.width for i in scaled) + gap * (len(scaled) - 1)
    if total > 1920 - 2 * margin:        # shrink uniformly to fit the width
        k = (1920 - 2 * margin) / total
        scaled = [i.resize((int(i.width * k), int(i.height * k)), Image.LANCZOS) for i in scaled]
        total = sum(i.width for i in scaled) + int(gap * k) * (len(scaled) - 1)
        gap = int(gap * k)
    x = (1920 - total) // 2
    for i in scaled:
        shadowed(i, cv, (x, (1080 - i.height) // 2), radius=10)
        x += i.width + gap
    return cv.convert("RGB")


def main() -> None:
    OUT.mkdir(exist_ok=True)
    icon = make_icon(1024)
    icon.resize((256, 256), Image.LANCZOS).save(OUT / "icon-256.png", optimize=True)
    make_featured(icon).save(OUT / "featured-1920x1080.png", optimize=True)
    load = lambda n: Image.open(IMG / n).convert("RGB")
    letterbox([load("panel-3-text.png"), load("view-plate.png")], gap=50).save(OUT / "preview-1-workflow.png", optimize=True)
    letterbox([load("view-cylinder.png")]).save(OUT / "preview-2-curved-surface.png", optimize=True)
    letterbox([load("view-two-labels.png")]).save(OUT / "preview-3-multiple-labels.png", optimize=True)
    letterbox([load("panel-1-initial.png"), load("panel-2-selected.png"), load("panel-3-text.png")], gap=36).save(OUT / "preview-4-panel.png", optimize=True)
    for p in sorted(OUT.glob("*.png")):
        print(f"{p.name:34s} {Image.open(p).size}  {p.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
