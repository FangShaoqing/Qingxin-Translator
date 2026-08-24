# -*- coding: utf-8 -*-
"""Skia 托盘菜单渲染测试：默认 / 选中 / hover / quit-hover 四种状态保存 PNG"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.glass_card import render_menu, _svg_to_path, _ICON_SVGS

MENU = [
    {"type": "header", "text": "青欣翻译"},
    {"type": "item", "text": "显示窗口", "icon": "show", "action": "show"},
    {"type": "item", "text": "隐藏窗口", "icon": "hide", "action": "hide"},
    {"type": "sep"},
    {"type": "label", "text": "划词模式"},
    {"type": "item", "text": "气泡", "sub": True, "radio": True, "checked": True, "action": "mode-bubble"},
    {"type": "item", "text": "窗口", "sub": True, "radio": True, "action": "mode-window"},
    {"type": "item", "text": "窗口置顶", "sub": True, "checked": True, "action": "on-top"},
    {"type": "item", "text": "开机自启", "sub": True, "action": "startup"},
    {"type": "sep"},
    {"type": "item", "text": "清空历史记录", "icon": "trash", "action": "clear-history"},
    {"type": "sep"},
    {"type": "item", "text": "退出", "icon": "power", "quit": True, "action": "quit"},
]

OUT = os.path.join(os.environ.get("TEMP", "."), "qxt_verify_v2")
os.makedirs(OUT, exist_ok=True)

# 菜单原始下标：header=0, show=1, hide=2, sep=3, label=4, bubble=5, window=6,
# on-top=7, startup=8, sep=9, clear=10, sep=11, quit=12

def save(name, data, w, h):
    import skia
    # skia-python 144：frombytes(buffer, ISize, colorType, alphaType, ...)（不接受 ImageInfo）
    img = skia.Image.frombytes(data, skia.ISize(w, h),
                               skia.kBGRA_8888_ColorType, skia.kPremul_AlphaType)
    png = img.encodeToData(skia.kPNG, 100)
    path = os.path.join(OUT, name)
    with open(path, "wb") as f:
        f.write(png.bytes())
    print("saved:", path, f"{w}x{h}")

# 1. 默认状态
data, w, h, rows = render_menu(MENU, hover_idx=-1)
save("menu_default.png", data, w, h)
print("default rows:", rows)

# 2. hover 显示窗口（index 1）
data, w, h, rows = render_menu(MENU, hover_idx=1)
save("menu_hover_show.png", data, w, h)

# 3. hover 退出（index 12）
data, w, h, rows = render_menu(MENU, hover_idx=12)
save("menu_hover_quit.png", data, w, h)

# 4. SVG path 解析自检：各图标 path 渲染成独立 PNG（白底黑线）
import skia
for name, (d, extra) in _ICON_SVGS.items():
    surface = skia.Surface(48, 48)
    canvas = surface.getCanvas()
    canvas.clear(skia.ColorWHITE)
    scale = 1.0
    dx = dy = 12.0
    paint = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style,
                       StrokeWidth=1, Color=skia.ColorBLACK)
    canvas.drawPath(_svg_to_path(d, scale, dx, dy), paint)
    if extra:
        if extra.startswith("circle"):
            cx, cy, r = map(float, extra[6:].split(","))
            canvas.drawCircle(cx * scale + dx, cy * scale + dy, r * scale, paint)
        elif extra.startswith("line"):
            x1, y1, x2, y2 = map(float, extra[4:].split(","))
            canvas.drawLine(x1 * scale + dx, y1 * scale + dy,
                            x2 * scale + dx, y2 * scale + dy, paint)
    image = surface.makeImageSnapshot()
    png = image.encodeToData(skia.kPNG, 100)
    path = os.path.join(OUT, f"icon_{name}.png")
    with open(path, "wb") as f:
        f.write(png.bytes())
    print("saved:", path)
print("done")
