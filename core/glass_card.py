# -*- coding: utf-8 -*-
"""
Qingxin Translator - Glass Card
Skia 渲染的自绘透明小窗口（UpdateLayeredWindow per-pixel alpha）

用途：悬浮翻译按钮 / 托盘 tooltip——自定义圆角 + 自定义阴影，替代 WebView2 小窗口。

限制：UpdateLayeredWindow 内容在 DPI 缩放 > 100% 的屏幕上不显示（Windows layered
窗口的已知限制）——调用方需先检测目标屏 DPI，>100% 时回退 WebView2 窗口。
"""

import ctypes
import math
import re
from ctypes import wintypes

import skia

from core.logger import log

user32 = ctypes.windll.user32
gdi32 = ctypes.WinDLL('gdi32')
kernel32 = ctypes.windll.kernel32

WS_POPUP = 0x80000000
WS_EX_LAYERED = 0x00080000
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_NOACTIVATE = 0x08000000
ULW_ALPHA = 0x00000002
SW_SHOW = 5
SW_HIDE = 0


class GlassCard:
    """Skia 自绘透明卡片窗口"""

    _class_atom = None
    _wnd_proc = None

    def __init__(self, title="QingxinGlass", on_click=None,
                 on_hover=None, on_leave=None, on_mouse_down=None):
        self.hwnd = None
        self._title = title
        self._on_click = on_click          # 无坐标点击回调（悬浮按钮用）
        self._on_hover = on_hover          # 鼠标移动回调 (x, y)
        self._on_leave = on_leave          # 鼠标离开窗口回调 ()
        self._on_mouse_down = on_mouse_down  # 鼠标按下回调 (x, y)
        self.visible = False

    @classmethod
    def _register_class(cls):
        if cls._class_atom:
            return cls._class_atom
        WNDPROC = ctypes.WINFUNCTYPE(
            ctypes.c_longlong, wintypes.HWND, wintypes.UINT,
            wintypes.WPARAM, wintypes.LPARAM)

        def wnd_proc(hwnd, msg, wparam, lparam):
            if msg in (0x0010, 0x0002):  # WM_CLOSE / WM_DESTROY
                return 0
            try:
                inst = cls._hwnd_map.get(hwnd)
            except Exception:
                inst = None
            if msg == 0x0200:  # WM_MOUSEMOVE：hover 回调（带坐标）
                try:
                    if inst and inst._on_hover:
                        x = lparam & 0xFFFF
                        y = (lparam >> 16) & 0xFFFF
                        inst._on_hover(x, y)
                except Exception as e:
                    log.debug(f"GlassCard hover error: {e}")
                return 0
            if msg == 0x02A3:  # WM_MOUSELEAVE：离开回调
                try:
                    if inst and inst._on_leave:
                        inst._on_leave()
                except Exception as e:
                    log.debug(f"GlassCard leave error: {e}")
                return 0
            if msg == 0x0201:  # WM_LBUTTONDOWN
                try:
                    if inst and inst._on_mouse_down:
                        x = lparam & 0xFFFF
                        y = (lparam >> 16) & 0xFFFF
                        inst._on_mouse_down(x, y)
                        return 0
                    if inst and inst._on_click:
                        inst._on_click()
                except Exception as e:
                    log.debug(f"GlassCard click error: {e}")
                return 0
            u32 = ctypes.WinDLL('user32')
            u32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT,
                                           wintypes.WPARAM, wintypes.LPARAM]
            u32.DefWindowProcW.restype = ctypes.c_longlong
            return u32.DefWindowProcW(hwnd, msg, wparam, lparam)

        cls._wnd_proc = WNDPROC(wnd_proc)
        cls._hwnd_map = {}

        class WNDCLASSEX(ctypes.Structure):
            _fields_ = [
                ("cbSize", wintypes.UINT), ("style", wintypes.UINT),
                ("lpfnWndProc", WNDPROC), ("cbClsExtra", ctypes.c_int),
                ("cbWndExtra", ctypes.c_int), ("hInstance", wintypes.HINSTANCE),
                ("hIcon", wintypes.HICON), ("hCursor", wintypes.HANDLE),
                ("hbrBackground", wintypes.HBRUSH), ("lpszMenuName", wintypes.LPCWSTR),
                ("lpszClassName", wintypes.LPCWSTR), ("hIconSm", wintypes.HICON),
            ]

        wc = WNDCLASSEX()
        wc.cbSize = ctypes.sizeof(WNDCLASSEX)
        wc.lpfnWndProc = cls._wnd_proc
        wc.hInstance = kernel32.GetModuleHandleW(None)
        wc.lpszClassName = "QingxinGlassCard"
        cls._class_atom = user32.RegisterClassExW(ctypes.byref(wc))
        return cls._class_atom

    def create(self, w, h):
        atom = self._register_class()
        self.hwnd = user32.CreateWindowExW(
            WS_EX_LAYERED | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE,
            atom, self._title, WS_POPUP,
            -10000, -10000, w, h, None, None,
            kernel32.GetModuleHandleW(None), None)
        if self.hwnd:
            self._hwnd_map[self.hwnd] = self
        return self.hwnd

    def render(self, img_bytes, w, h):
        """渲染 BGRA 预乘字节（Skia surface 输出）"""
        buf = ctypes.create_string_buffer(img_bytes, len(img_bytes))

        class BITMAPINFOHEADER(ctypes.Structure):
            _fields_ = [("biSize", wintypes.DWORD), ("biWidth", ctypes.c_long),
                        ("biHeight", ctypes.c_long), ("biPlanes", wintypes.WORD),
                        ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
                        ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", ctypes.c_long),
                        ("biYPelsPerMeter", ctypes.c_long), ("biClrUsed", wintypes.DWORD),
                        ("biClrImportant", wintypes.DWORD)]

        class BITMAPINFO(ctypes.Structure):
            _fields_ = [("bmiHeader", BITMAPINFOHEADER)]

        bmi = BITMAPINFO()
        bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bmi.bmiHeader.biWidth = w
        bmi.bmiHeader.biHeight = -h
        bmi.bmiHeader.biPlanes = 1
        bmi.bmiHeader.biBitCount = 32
        bits = ctypes.c_void_p()
        hbmp = gdi32.CreateDIBSection(None, ctypes.byref(bmi), 0, ctypes.byref(bits), None, 0)
        if not hbmp:
            return False
        ctypes.memmove(bits, buf, len(img_bytes))
        hdc = gdi32.CreateCompatibleDC(None)
        old = gdi32.SelectObject(hdc, hbmp)
        # ptDst 传 None（不移动窗口）——若传 (0,0) 每次 render 会把窗口移到屏幕原点，
        # 悬浮按钮/tooltip 显示前 render 无感，但菜单显示后 hover 重渲染会跳位
        sz = wintypes.SIZE(w, h)
        ppt = wintypes.POINT(0, 0)

        class BLENDFUNCTION(ctypes.Structure):
            _fields_ = [("BlendOp", ctypes.c_byte), ("BlendFlags", ctypes.c_byte),
                        ("SourceConstantAlpha", ctypes.c_byte), ("AlphaFormat", ctypes.c_byte)]

        blend = BLENDFUNCTION(0, 0, 255, 1)  # AC_SRC_ALPHA
        ok = user32.UpdateLayeredWindow(
            self.hwnd, None, None, ctypes.byref(sz),
            hdc, ctypes.byref(ppt), 0, ctypes.byref(blend), ULW_ALPHA)
        gdi32.SelectObject(hdc, old)
        gdi32.DeleteDC(hdc)
        gdi32.DeleteObject(hbmp)
        return bool(ok)

    def show(self, x, y):
        user32.SetWindowPos(self.hwnd, ctypes.c_void_p(-1), x, y, 0, 0, 0x0001 | 0x0010)
        user32.ShowWindow(self.hwnd, SW_SHOW)
        self.visible = True
        # 开启 WM_MOUSELEAVE 追踪（hover 离开回调需要）
        if self._on_leave:
            try:
                class TRACKMOUSEEVENT(ctypes.Structure):
                    _fields_ = [("cbSize", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
                                ("hwndTrack", wintypes.HWND), ("dwHoverTime", wintypes.DWORD)]
                tme = TRACKMOUSEEVENT()
                tme.cbSize = ctypes.sizeof(TRACKMOUSEEVENT)
                tme.dwFlags = 0x00000002  # TME_LEAVE
                tme.hwndTrack = self.hwnd
                user32.TrackMouseEvent(ctypes.byref(tme))
            except Exception:
                pass

    def hide(self):
        user32.ShowWindow(self.hwnd, SW_HIDE)
        self.visible = False

    def destroy(self):
        if self.hwnd:
            self._hwnd_map.pop(self.hwnd, None)
            user32.DestroyWindow(self.hwnd)
            self.hwnd = None


# ==================== Skia 渲染 ====================

def _typeface():
    return skia.Typeface('Microsoft YaHei')


def render_button(text="翻译", card_w=56, card_h=28, radius=8,
                  shadow_alpha=100, shadow_blur=5):
    """悬浮按钮卡片（逻辑尺寸，100% DPI）——返回 (BGRA字节, 宽, 高)"""
    pad = 11
    W, H = card_w + pad * 2, card_h + pad * 2
    surface = skia.Surface(W, H)
    canvas = surface.getCanvas()
    canvas.clear(skia.ColorTRANSPARENT)

    # 阴影
    shadow = skia.Paint(AntiAlias=True, Color=skia.ColorSetARGB(shadow_alpha, 0, 0, 0))
    shadow.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, shadow_blur))
    canvas.drawRoundRect(skia.Rect.MakeXYWH(pad, pad + 2, card_w, card_h), radius, radius, shadow)
    # 卡片
    card = skia.Paint(AntiAlias=True, Color=skia.ColorWHITE)
    canvas.drawRoundRect(skia.Rect.MakeXYWH(pad, pad, card_w, card_h), radius, radius, card)
    # 边框
    border = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style,
                        StrokeWidth=1, Color=skia.ColorSetARGB(255, 232, 160, 166))
    canvas.drawRoundRect(skia.Rect.MakeXYWH(pad, pad, card_w, card_h), radius, radius, border)
    # 圆点 + 文字（整体水平/垂直居中）
    tf = _typeface()
    font = skia.Font(tf, 12)
    text_w = font.measureText(text)
    metrics = font.getMetrics()
    ascent = -metrics.fAscent
    descent = metrics.fDescent
    dot_r = 2.5
    group_w = dot_r * 2 + 6 + text_w
    start_x = pad + (card_w - group_w) / 2
    dot = skia.Paint(AntiAlias=True, Color=skia.ColorSetARGB(255, 240, 196, 200))
    canvas.drawCircle(start_x + dot_r, pad + card_h / 2, dot_r, dot)
    baseline = pad + (card_h - (ascent + descent)) / 2 + ascent
    text_p = skia.Paint(AntiAlias=True, Color=skia.ColorSetARGB(255, 51, 51, 51))
    canvas.drawString(text, start_x + dot_r * 2 + 6, baseline, font, text_p)

    image = surface.makeImageSnapshot()
    return image.tobytes(), W, H


def render_tooltip(text, card_h=28, radius=8, shadow_alpha=80, shadow_blur=4):
    """tooltip 卡片（宽度自适应内容）——返回 (BGRA字节, 宽, 高)"""
    tf = _typeface()
    font = skia.Font(tf, 11)
    tw = int(font.measureText(text))
    card_w = tw + 8 + 6 + 20 + 2  # 圆点 + 间距 + padding + 边框
    pad = 10
    W, H = card_w + pad * 2, card_h + pad * 2
    surface = skia.Surface(W, H)
    canvas = surface.getCanvas()
    canvas.clear(skia.ColorTRANSPARENT)

    shadow = skia.Paint(AntiAlias=True, Color=skia.ColorSetARGB(shadow_alpha, 0, 0, 0))
    shadow.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, shadow_blur))
    canvas.drawRoundRect(skia.Rect.MakeXYWH(pad, pad + 2, card_w, card_h), radius, radius, shadow)
    canvas.drawRoundRect(skia.Rect.MakeXYWH(pad, pad, card_w, card_h), radius, radius,
                         skia.Paint(AntiAlias=True, Color=skia.ColorWHITE))
    border = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style,
                        StrokeWidth=1, Color=skia.ColorSetARGB(255, 240, 196, 200))
    canvas.drawRoundRect(skia.Rect.MakeXYWH(pad, pad, card_w, card_h), radius, radius, border)
    # 圆点 + 文字（垂直居中，左对齐）
    dot = skia.Paint(AntiAlias=True, Color=skia.ColorSetARGB(255, 240, 196, 200))
    canvas.drawCircle(pad + 12, pad + card_h / 2, 2.5, dot)
    metrics = font.getMetrics()
    ascent = -metrics.fAscent
    descent = metrics.fDescent
    baseline = pad + (card_h - (ascent + descent)) / 2 + ascent
    text_p = skia.Paint(AntiAlias=True, Color=skia.ColorSetARGB(255, 51, 51, 51))
    canvas.drawString(text, pad + 20, baseline, font, text_p)

    image = surface.makeImageSnapshot()
    return image.tobytes(), W, H


# ==================== 托盘菜单渲染 ====================

# 菜单颜色（与 web/styles/main.css 的 CSS 变量逐项一致）
_MENU_BG = 0xFFFFFFFF              # --background: #FFFFFF
_MENU_BORDER_A = 128               # --border: rgba(250,218,222,0.5)
_MENU_BORDER_RGB = (250, 218, 222)
_MENU_BORDER_STRONG = 0xFFFADADE   # --border-strong: #FADADE（radio/check 未选边框）
_MENU_PINK_DARK = 0xFFF0C4C8       # --pink-dark: #F0C4C8（标题/选中/hover 图标）
_MENU_PINK_LIGHT = 0xFFFFF0F2      # --pink-light: #FFF0F2（item hover 背景）
_MENU_TEXT = 0xFF666666            # --text-secondary（item 文字）
_MENU_TEXT_DARK = 0xFF333333       # --text-primary（hover 文字）
_MENU_TEXT_LIGHT = 0xFF999999      # --text-tertiary（label/图标）
_MENU_QUIT = 0xFFD9534F            # 退出红（main.css .tray-menu-quit）
_MENU_QUIT_HOVER = 0x14D9534F      # rgba(217,83,79,0.08)（quit hover 浅红底）

# 布局常量（按 CSS padding 计算；微软雅黑 12px 行高≈15.84、10px≈13.2 已实测）
MENU_ITEM_H = 30     # item: 7 + 15.84 + 7
MENU_HEADER_H = 35   # header: 6 + 15.84 + 8 + 1(border) + 4(margin-bottom)
MENU_LABEL_H = 21    # label: 4 + 13.2 + 4
MENU_SEP_H = 9       # sep: 4 + 1 + 4
MENU_PAD = 6         # 容器 padding（CSS .tray-menu padding: 6px）

# 菜单图标（与 web/tray_menu.html 的 SVG 完全一致：24 viewBox、stroke 1.5）
# value = (path d, 附加元素)；附加元素 circleCx,Cy,R / lineX1,Y1,X2,Y2
_ICON_SVGS = {
    "show": (
        "M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z",
        "circle12,12,3"),
    "hide": (
        "M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94"
        "M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19"
        "m-6.72-1.07a3 3 0 11-4.24-4.24",
        "line1,1,23,23"),
    "trash": (
        "M3 6L5 6L21 6M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4"
        "a2 2 0 012 2v2",
        None),
    "power": (
        "M18.36 6.64a9 9 0 11-12.73 0M12 2v10",
        None),
}

_NUM_RE = re.compile(r"[+-]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][+-]?\d+)?")


def _svg_arc_params(x1, y1, x2, y2, rx, ry, large, sweep):
    """SVG 椭圆弧参数 → (圆心 cx, cy, 起始角°, 扫过角°)（供 Path.arcTo(oval,...)）
    按 W3C 标准圆心算法；仅支持 x-axis-rotation=0。
    不用 Path.arcTo 的 SVG 重载：其半圆边界（两点距离=2r）实现有误。
    返回的圆心为 SVG 坐标（调用方需自行缩放/平移构造 oval）"""
    if x1 == x2 and y1 == y2:
        return x1, y1, 0.0, 0.0
    dx = (x1 - x2) / 2.0
    dy = (y1 - y2) / 2.0
    d2 = dx * dx + dy * dy
    # 半轴钳制（d2 > r² 时按比例放大）
    r2 = rx * rx
    if d2 > r2:
        scale = math.sqrt(d2 / r2)
        rx *= scale
        ry *= scale
        r2 = rx * rx
    lam = math.sqrt(max(r2 - d2, 0.0)) / math.sqrt(d2)
    # large==sweep 取负号圆心（W3C 算法）
    sign = -1.0 if large == sweep else 1.0
    cx = (x1 + x2) / 2.0 + sign * lam * (y1 - y2) / 2.0
    cy = (y1 + y2) / 2.0 + sign * lam * (x2 - x1) / 2.0
    t1 = math.atan2(y1 - cy, x1 - cx)
    t2 = math.atan2(y2 - cy, x2 - cx)
    delta = t2 - t1
    if sweep:
        while delta < 0:
            delta += 2 * math.pi
    else:
        while delta > 0:
            delta -= 2 * math.pi
    if large and abs(delta) <= math.pi:
        delta = (2 * math.pi - abs(delta)) * (1.0 if sweep else -1.0)
    return cx, cy, math.degrees(t1), math.degrees(delta)


def _svg_to_path(d, scale=1.0, dx=0.0, dy=0.0):
    """简易 SVG path 解析（M L H V C S Q T A Z，绝对/相对）→ skia.Path
    坐标变换：p' = p*scale + (dx, dy)"""
    path = skia.Path()
    i, n = 0, len(d)
    cur = None          # 当前命令
    last = None         # 上次命令（S/T 反射用）
    x = y = sx = sy = 0.0
    cpx = cpy = 0.0     # 上次 cubic 第二控制点（S 反射）
    qpx = qpy = 0.0     # 上次 quad 控制点（T 反射）

    def skip():
        nonlocal i
        while i < n and d[i] in " \t\r\n,":
            i += 1

    def num():
        nonlocal i
        skip()
        m = _NUM_RE.match(d, i)
        if not m:
            raise ValueError(f"bad number at {i} in: {d}")
        i = m.end()
        return float(m.group(0))

    def flag():
        nonlocal i
        skip()
        if i < n and d[i] in "01":
            v = d[i] == "1"
            i += 1
            return v
        raise ValueError(f"bad flag at {i} in: {d}")

    def pair(rel):
        """读一对坐标（相对则累加当前点）"""
        nonlocal x, y
        nx, ny = num(), num()
        if rel:
            nx += x
            ny += y
        return nx, ny

    def emit(cmd, rel, up):
        """处理一组参数，返回是否还有同命令的更多组"""
        nonlocal x, y, sx, sy, cpx, cpy, qpx, qpy, last, cur
        if up == "M":
            nx, ny = pair(rel)
            path.moveTo(nx * scale + dx, ny * scale + dy)
            x, y = nx, ny
            sx, sy = nx, ny
        elif up == "L":
            nx, ny = pair(rel)
            path.lineTo(nx * scale + dx, ny * scale + dy)
            x, y = nx, ny
        elif up == "H":
            nx = num() + (x if rel else 0)
            path.lineTo(nx * scale + dx, y * scale + dy)
            x = nx
        elif up == "V":
            ny = num() + (y if rel else 0)
            path.lineTo(x * scale + dx, ny * scale + dy)
            y = ny
        elif up == "C":
            x1, y1 = pair(rel)
            x2, y2 = pair(rel)
            nx, ny = pair(rel)
            path.cubicTo(x1 * scale + dx, y1 * scale + dy,
                         x2 * scale + dx, y2 * scale + dy,
                         nx * scale + dx, ny * scale + dy)
            cpx, cpy = x2, y2
            x, y = nx, ny
        elif up == "S":
            if last in ("C", "c", "S", "s"):
                x1, y1 = 2 * x - cpx, 2 * y - cpy
            else:
                x1, y1 = x, y
            x2, y2 = pair(rel)
            nx, ny = pair(rel)
            path.cubicTo(x1 * scale + dx, y1 * scale + dy,
                         x2 * scale + dx, y2 * scale + dy,
                         nx * scale + dx, ny * scale + dy)
            cpx, cpy = x2, y2
            x, y = nx, ny
        elif up == "Q":
            qx, qy = pair(rel)
            nx, ny = pair(rel)
            path.quadTo(qx * scale + dx, qy * scale + dy,
                        nx * scale + dx, ny * scale + dy)
            qpx, qpy = qx, qy
            x, y = nx, ny
        elif up == "T":
            if last in ("Q", "q", "T", "t"):
                qx, qy = 2 * x - qpx, 2 * y - qpy
            else:
                qx, qy = x, y
            nx, ny = pair(rel)
            path.quadTo(qx * scale + dx, qy * scale + dy,
                        nx * scale + dx, ny * scale + dy)
            qpx, qpy = qx, qy
            x, y = nx, ny
        elif up == "A":
            rx, ry = num(), num()
            rot = num()
            la = flag()
            sw = flag()
            nx, ny = num(), num()
            if rel:
                nx += x
                ny += y
            if rot != 0:
                raise ValueError(f"arc rotation {rot} not supported")
            cx, cy, start_deg, sweep_deg = _svg_arc_params(
                x, y, nx, ny, rx, ry, la, sw)
            # oval 需与 path 同坐标空间（SVG 坐标 → 缩放+平移）
            rxs, rys = rx * scale, ry * scale
            oval = skia.Rect.MakeXYWH(cx * scale + dx - rxs,
                                      cy * scale + dy - rys,
                                      rxs * 2, rys * 2)
            path.arcTo(oval, start_deg, sweep_deg, False)
            x, y = nx, ny
        elif up == "Z":
            path.close()
            x, y = sx, sy
        last = up
        # 若还有更多参数，继续同一命令（M 的隐式后续为 L）
        skip()
        if i < n and not d[i].isalpha():
            if up == "M":
                cur = "l" if rel else "L"
                return True
            return True
        return False

    while i < n:
        skip()
        if i >= n:
            break
        ch = d[i]
        if ch.isalpha():
            cur = ch
            i += 1
        elif cur is None:
            break
        cmd = cur
        while True:
            if not emit(cmd, cmd.islower(), cmd.upper()):
                break
    return path


def _draw_menu_icon(canvas, icon, x, y, color):
    """绘制菜单 SVG 图标：24 viewBox 缩放到 14×14 区域（左上角 x,y），线宽≈1px"""
    item = _ICON_SVGS.get(icon)
    if not item:
        return
    d, extra = item
    scale = 14.0 / 24.0
    # path 中心 (12,12) → 目标区域中心 (x+7, y+7)
    dx = x + 7 - 12 * scale
    dy = y + 7 - 12 * scale
    paint = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style,
                       StrokeWidth=1, Color=color)
    canvas.drawPath(_svg_to_path(d, scale, dx, dy), paint)
    if extra:
        if extra.startswith("circle"):
            cx, cy, r = map(float, extra[6:].split(","))
            canvas.drawCircle(cx * scale + dx, cy * scale + dy, r * scale, paint)
        elif extra.startswith("line"):
            x1, y1, x2, y2 = map(float, extra[4:].split(","))
            canvas.drawLine(x1 * scale + dx, y1 * scale + dy,
                            x2 * scale + dx, y2 * scale + dy, paint)


def _draw_menu_radio_check(canvas, x, y, m, checked):
    """radio / check 控件（14×14）——CSS .tray-menu-radio / .tray-menu-check"""
    size = 14
    if m.get("radio"):
        if checked:
            stroke = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style,
                                StrokeWidth=1.5, Color=_MENU_PINK_DARK)
            canvas.drawCircle(x + size / 2, y + size / 2, size / 2, stroke)
            dot = skia.Paint(AntiAlias=True, Color=_MENU_PINK_DARK)
            canvas.drawCircle(x + size / 2, y + size / 2, size / 2 - 3, dot)  # inset 3px
        else:
            stroke = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style,
                                StrokeWidth=1.5, Color=_MENU_BORDER_STRONG)
            canvas.drawCircle(x + size / 2, y + size / 2, size / 2, stroke)
    else:
        if checked:
            fg = skia.Paint(AntiAlias=True, Color=_MENU_PINK_DARK)
            canvas.drawRoundRect(skia.Rect.MakeXYWH(x, y, size, size), 3, 3, fg)
            # 白色对勾（stroke！fill 会把三点区域填成三角块）
            check_p = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style,
                                 StrokeWidth=2, Color=skia.ColorWHITE)
            path = skia.Path()
            path.moveTo(x + 3.4, y + 7.2)
            path.lineTo(x + 6.2, y + 10.0)
            path.lineTo(x + 10.8, y + 4.0)
            canvas.drawPath(path, check_p)
        else:
            stroke = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style,
                                StrokeWidth=1.5, Color=_MENU_BORDER_STRONG)
            canvas.drawRoundRect(skia.Rect.MakeXYWH(x, y, size, size), 3, 3, stroke)


def _draw_spaced(canvas, text, x, baseline, font, paint, spacing=1):
    """逐字绘制（模拟 CSS letter-spacing）"""
    for ch in text:
        canvas.drawString(ch, x, baseline, font, paint)
        x += font.measureText(ch) + spacing


def _menu_layout(menu):
    """计算菜单总高与各项位置；menu: list[dict]
    元素：{type: 'header'|'label'|'sep'|'item', text, checked?, sub?}
    rows 中 item 行记录【原始 menu 下标】（渲染/命中/动作统一用它索引 menu）
    高度按 CSS 计算：header 含底部 margin 4px；sep 上下各加 2px（相邻 group
    padding 2px 0）；末尾 group 的 padding-bottom 计入 total_h
    """
    rows = []       # (type, top, height, orig_index 或 None)
    y = MENU_PAD
    for orig_idx, m in enumerate(menu):
        t = m.get("type", "item")
        if t == "header":
            rows.append(("header", y, MENU_HEADER_H + 2, orig_idx))  # +group1 pad-top
            y += MENU_HEADER_H + 2
        elif t == "label":
            rows.append(("label", y, MENU_LABEL_H, orig_idx))
            y += MENU_LABEL_H
        elif t == "sep":
            rows.append(("sep", y, MENU_SEP_H + 4, orig_idx))  # 上下各 +2（相邻 group pad）
            y += MENU_SEP_H + 4
        else:
            rows.append(("item", y, MENU_ITEM_H, orig_idx))
            y += MENU_ITEM_H
    total_h = y + MENU_PAD + 2  # 最后 group 的 padding-bottom
    return rows, total_h


def render_menu(menu, hover_idx=-1, card_w=190, radius=12,
                shadow_alpha=90, shadow_blur=5):
    """渲染托盘菜单卡片——返回 (BGRA字节, 宽, 高, 各项位置)

    布局与 web/tray_menu.html + web/styles/main.css 的 .tray-menu 完全一致：
    - 容器 padding 6px（MENU_PAD），圆角 12px（--radius-lg），边框 --border
    - header：12px #F0C4C8 标题（letter-spacing 1px）+ 底部 1px --border 分隔线
    - item：12px #666666，hover #FFF0F2 底 + #333333 文字，圆角 8px
    - svg 图标 14px：常态 #999999，hover #F0C4C8，quit 恒 #d9534f
    - sub：radio/check 14px，未选 #FADADE 1.5px 边框，选中 #F0C4C8
    - label：10px #999999（letter-spacing 1px）
    - sep：1px --border，margin 4px 8px
    - quit：#d9534f，hover 浅红底 rgba(217,83,79,0.08)

    menu: 菜单数据列表（同 _menu_layout），hover_idx 为当前高亮项下标（-1 无）
    """
    rows, total_h = _menu_layout(menu)
    pad = 10  # 阴影边距
    W, H = card_w + pad * 2, total_h + pad * 2
    surface = skia.Surface(W, H)
    canvas = surface.getCanvas()
    canvas.clear(skia.ColorTRANSPARENT)

    # 阴影 + 卡片 + 边框（--border 半透明粉）
    shadow = skia.Paint(AntiAlias=True, Color=skia.ColorSetARGB(shadow_alpha, 0, 0, 0))
    shadow.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, shadow_blur))
    canvas.drawRoundRect(skia.Rect.MakeXYWH(pad, pad + 2, card_w, total_h), radius, radius, shadow)
    canvas.drawRoundRect(skia.Rect.MakeXYWH(pad, pad, card_w, total_h), radius, radius,
                         skia.Paint(AntiAlias=True, Color=_MENU_BG))
    border = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style,
                        StrokeWidth=1, Color=skia.ColorSetARGB(_MENU_BORDER_A, *_MENU_BORDER_RGB))
    canvas.drawRoundRect(skia.Rect.MakeXYWH(pad, pad, card_w, total_h), radius, radius, border)

    tf = _typeface()
    font_title = skia.Font(tf, 12)
    font_item = skia.Font(tf, 12)
    font_label = skia.Font(tf, 10)

    # 分隔线/边框线（--border 半透明粉）
    sep_p = skia.Paint(AntiAlias=True,
                       Color=skia.ColorSetARGB(_MENU_BORDER_A, *_MENU_BORDER_RGB))

    # 绘制各项（菜单内坐标 = 窗口坐标 - pad；CSS 容器 padding 6 → 菜单内 x 6..184）
    for (rtype, top, rh, idx) in rows:
        cy = pad + top  # 窗口内 y
        if rtype == "sep":
            # CSS: height 1px, margin 4px 8px → 线 y=居中，x 14..176
            py = cy + rh / 2
            canvas.drawLine(pad + 14, py, pad + card_w - 14, py, sep_p)
            continue
        if rtype == "item":
            m = menu[idx]
        elif rtype in ("header", "label"):
            m = menu[idx]
        else:
            m = None
        if rtype == "header" and m:
            # CSS: padding 6px 12px 8px + border-bottom 1px + margin-bottom 4px
            text_p = skia.Paint(AntiAlias=True, Color=_MENU_PINK_DARK)
            metrics = font_title.getMetrics()
            asc = -metrics.fAscent
            baseline = cy + 6 + asc
            _draw_spaced(canvas, m.get("text", ""), pad + 18, baseline,
                         font_title, text_p, 1)
            # header 底部 1px 分隔线（CSS: padding 6+行高15.84+8 → 距行顶≈30.5；全宽 6..184）
            canvas.drawLine(pad + 6, cy + 30.5, pad + card_w - 6, cy + 30.5, sep_p)
            continue
        if rtype == "label" and m:
            # CSS: padding 4px 12px, 10px #999999, letter-spacing 1px
            text_p = skia.Paint(AntiAlias=True, Color=_MENU_TEXT_LIGHT)
            metrics = font_label.getMetrics()
            asc = -metrics.fAscent
            baseline = cy + 4 + asc
            _draw_spaced(canvas, m.get("text", ""), pad + 18, baseline,
                         font_label, text_p, 1)
            continue
        if rtype == "item" and m:
            y0 = cy
            is_sub = m.get("sub", False)
            checked = m.get("checked", False)
            is_quit = m.get("quit", False)
            is_hover = (idx == hover_idx)
            # hover 高亮（CSS: 全宽 6..184，圆角 8px；quit 用浅红底）
            if is_hover:
                hover_p = skia.Paint(
                    AntiAlias=True,
                    Color=_MENU_QUIT_HOVER if is_quit else _MENU_PINK_LIGHT)
                canvas.drawRoundRect(
                    skia.Rect.MakeXYWH(pad + 6, y0, card_w - 12, MENU_ITEM_H),
                    8, 8, hover_p)
            # 图标/控件（14×14 垂直居中）与文字 x（CSS 逐项对齐）
            if is_sub:
                # CSS: .tray-menu-sub padding-left 20 → 控件 26..40，文字 48
                _draw_menu_radio_check(canvas, pad + 26,
                                       y0 + (MENU_ITEM_H - 14) / 2, m, checked)
                text_x = pad + 48
            elif m.get("icon"):
                # CSS: svg 18..32，文字 40；常态 #999999，hover #F0C4C8，quit 恒红
                icon_color = (_MENU_QUIT if is_quit
                              else (_MENU_PINK_DARK if is_hover else _MENU_TEXT_LIGHT))
                _draw_menu_icon(canvas, m.get("icon"), pad + 18,
                                y0 + (MENU_ITEM_H - 14) / 2, icon_color)
                text_x = pad + 40
            else:
                text_x = pad + 18
            # 文字（CSS: 12px；常态 #666666，hover #333333，quit 恒 #d9534f）
            color = _MENU_QUIT if is_quit else (_MENU_TEXT_DARK if is_hover else _MENU_TEXT)
            text_p = skia.Paint(AntiAlias=True, Color=color)
            metrics = font_item.getMetrics()
            asc = -metrics.fAscent
            desc = metrics.fDescent
            baseline = y0 + (MENU_ITEM_H - (asc + desc)) / 2 + asc
            canvas.drawString(m.get("text", ""), text_x, baseline, font_item, text_p)

    image = surface.makeImageSnapshot()
    return image.tobytes(), W, H, rows


def hit_test_menu(rows, x, y, pad=10):
    """命中测试：窗口内坐标 (x, y) 对应菜单项【原始 menu 下标】；非 item 返回 None
    rows 的 top 是菜单内坐标（不含阴影边距），窗口坐标 = 菜单内坐标 + pad"""
    for (rtype, top, rh, idx) in rows:
        if rtype != "item":
            continue
        if top + pad <= y < top + rh + pad:
            return idx
    return None
