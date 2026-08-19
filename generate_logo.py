"""
Qingxin Translator - Logo Generator
生成不同尺寸的Logo图标

设计概念：Q 字母 + 打开的书页 + 现代悬浮层次感
- Q 字母的圆环化身翻开的书页
- Q 的尾巴变成翻动的书角 / 语言转换的弧线
- 多层阴影营造悬浮感，延续应用的 UI 设计语言
"""

import sys
import math
from pathlib import Path

ROOT_DIR = Path(__file__).parent
sys.path.insert(0, str(ROOT_DIR))

from PIL import Image, ImageDraw, ImageFont


# ==================== 配色方案 ====================
# 主色系（樱花粉渐变）
PINK_DEEP    = (232, 160, 170, 255)   # 深粉 #E8A0AA
PINK_MID     = (240, 196, 200, 255)   # 中粉 #F0C4C8
PINK_LIGHT   = (250, 218, 222, 255)   # 浅粉 #FADADE
PINK_PALE    = (255, 235, 238, 255)   # 极浅粉 #FFEBEE

# 背景与文字
WHITE        = (255, 255, 255, 255)
TEXT_DARK    = (51, 51, 51, 255)       # #333333
TEXT_LIGHT   = (153, 153, 153, 255)    # #999999

# 阴影色
SHADOW_SOFT  = (0, 0, 0, 18)          # 极淡阴影
SHADOW_MED   = (0, 0, 0, 30)          # 中等阴影


def _draw_shadow_rounded_rect(draw, bbox, radius, shadow_color, shadow_offset, blur_passes=3):
    """绘制带模糊阴影的圆角矩形（多层叠加模拟高斯模糊）"""
    x1, y1, x2, y2 = bbox
    ox, oy = shadow_offset
    for i in range(blur_passes, 0, -1):
        expand = i * 2
        alpha = shadow_color[3] // (blur_passes + 1) * (blur_passes - i + 1)
        c = (shadow_color[0], shadow_color[1], shadow_color[2], alpha)
        draw.rounded_rectangle(
            [x1 + ox - expand, y1 + oy - expand, x2 + ox + expand, y2 + oy + expand],
            radius=radius + expand,
            fill=c
        )


def _draw_gradient_circle(draw, cx, cy, r, color_inner, color_outer, steps=20):
    """绘制径向渐变圆形（从内到外）"""
    for i in range(steps, 0, -1):
        ratio = i / steps
        cr = int(r * ratio)
        # 插值颜色
        c = tuple(
            int(color_inner[j] + (color_outer[j] - color_inner[j]) * (1 - ratio))
            for j in range(4)
        )
        draw.ellipse(
            [cx - cr, cy - cr, cx + cr, cy + cr],
            fill=c
        )


def _draw_filled_sector(draw, cx, cy, r, start_angle, end_angle, color, steps=1):
    """用扇形近似绘制 Q 尾巴的弧形"""
    points = []
    for i in range(steps + 1):
        angle = math.radians(start_angle + (end_angle - start_angle) * i / steps)
        points.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
    # 回到圆心
    points.append((cx, cy))
    if len(points) >= 3:
        draw.polygon(points, fill=color)


def create_logo(size: int) -> Image.Image:
    """
    创建 Logo（带文字版）— 用于展示/官网
    设计：悬浮卡片 + Q 书页 + "青欣翻译" 文字
    """
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    scale = size / 512

    # ---- 1. 底层阴影卡片（营造悬浮感）----
    card_margin = int(40 * scale)
    card_radius = int(60 * scale)
    card_bbox = [card_margin, card_margin, size - card_margin, size - card_margin]

    # 多层阴影
    _draw_shadow_rounded_rect(draw, card_bbox, card_radius, SHADOW_SOFT, (0, int(8 * scale)), blur_passes=4)
    _draw_shadow_rounded_rect(draw, card_bbox, card_radius, SHADOW_MED, (0, int(4 * scale)), blur_passes=2)

    # 白色卡片
    draw.rounded_rectangle(card_bbox, radius=card_radius, fill=WHITE)

    # ---- 2. Q 字母主体（圆形书页）----
    q_cx = size // 2
    q_cy = int(200 * scale)
    q_r = int(90 * scale)

    # Q 的圆环 — 用渐变粉色填充（渐变圆）
    _draw_gradient_circle(draw, q_cx, q_cy, q_r, PINK_PALE, PINK_LIGHT, steps=25)

    # 圆环的"镂空"效果 — 中间画白色圆
    inner_r = int(58 * scale)
    draw.ellipse(
        [q_cx - inner_r, q_cy - inner_r, q_cx + inner_r, q_cy + inner_r],
        fill=WHITE
    )

    # 圆环外圈 — 加一圈深粉描边增加层次
    outline_w = max(int(3 * scale), 1)
    draw.ellipse(
        [q_cx - q_r, q_cy - q_r, q_cx + q_r, q_cy + q_r],
        outline=PINK_MID, width=outline_w
    )

    # ---- 3. Q 的尾巴 — 翻动的书角 / 弧线 ----
    # 尾巴从圆环右下延伸，像翻开的书页角
    tail_cx = q_cx + int(55 * scale)
    tail_cy = q_cy + int(55 * scale)
    tail_r = int(45 * scale)

    # 尾巴弧形（用圆弧 + 填充模拟）
    _draw_gradient_circle(draw, tail_cx, tail_cy, tail_r, PINK_MID, PINK_DEEP, steps=20)

    # 用白色遮盖尾巴圆的上半部分，只保留右下弧形
    # 计算遮罩区域：圆环与尾巴重叠部分保留，其余白色覆盖
    # 简化处理：画一个白色矩形遮盖尾巴圆的左上部分
    clip_x = tail_cx - tail_r - int(5 * scale)
    clip_y = tail_cy - tail_r - int(5 * scale)
    # 遮盖尾巴圆中超出 Q 圆环的部分（左上方向）
    draw.ellipse(
        [q_cx - inner_r - int(10 * scale), q_cy - inner_r - int(10 * scale),
         q_cx + inner_r + int(10 * scale), q_cy + inner_r + int(10 * scale)],
        fill=WHITE
    )
    # 重新画 Q 的圆环（因为被尾巴遮盖了部分）
    # 内圈白色
    draw.ellipse(
        [q_cx - inner_r, q_cy - inner_r, q_cx + inner_r, q_cy + inner_r],
        fill=WHITE
    )

    # 用更巧妙的方式：直接画 Q 的环形弧线 + 尾巴
    # 清除之前的渐变，用描边方式重绘
    # 重新绘制圆环描边（深粉）
    ring_width = int(28 * scale)
    draw.ellipse(
        [q_cx - q_r, q_cy - q_r, q_cx + q_r, q_cy + q_r],
        outline=PINK_MID, width=ring_width
    )
    # 内侧浅色描边（营造渐变环效果）
    draw.ellipse(
        [q_cx - q_r + int(4 * scale), q_cy - q_r + int(4 * scale),
         q_cx + q_r - int(4 * scale), q_cy + q_r - int(4 * scale)],
        outline=PINK_PALE, width=int(8 * scale)
    )

    # Q 的尾巴 — 从右下圆环处延伸的弧形
    # 用一个倾斜的椭圆弧来模拟
    tail_w = int(24 * scale)
    # 尾巴主体线段
    tail_start_x = q_cx + int(62 * scale)
    tail_start_y = q_cy + int(62 * scale)
    tail_end_x = q_cx + int(90 * scale)
    tail_end_y = q_cy + int(95 * scale)

    draw.line(
        [(tail_start_x, tail_start_y), (tail_end_x, tail_end_y)],
        fill=PINK_DEEP, width=tail_w
    )
    # 尾巴末端圆润
    dot_r = tail_w // 2
    draw.ellipse(
        [tail_end_x - dot_r, tail_end_y - dot_r, tail_end_x + dot_r, tail_end_y + dot_r],
        fill=PINK_DEEP
    )

    # ---- 4. 书页装饰线条（在 Q 的内圈中）----
    # 用 2-3 条平行弧线暗示翻开的书页
    page_color = (*PINK_LIGHT[:3], 100)  # 半透明浅粉
    for i, offset_y in enumerate([-12, 0, 12]):
        oy = int(offset_y * scale)
        line_y = q_cy + oy
        line_half_w = int(30 * scale) - abs(oy) // 2
        if line_half_w > 5:
            lw = max(int(2 * scale), 1)
            draw.line(
                [(q_cx - line_half_w, line_y), (q_cx + line_half_w, line_y)],
                fill=page_color, width=lw
            )

    # ---- 5. 底部文字 "青欣翻译" ----
    try:
        font_size = int(36 * scale)
        font = ImageFont.truetype("msyh.ttc", font_size)
    except Exception:
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except Exception:
            font = ImageFont.load_default()

    text = "青欣翻译"
    text_bbox = draw.textbbox((0, 0), text, font=font)
    text_w = text_bbox[2] - text_bbox[0]
    text_x = (size - text_w) // 2
    text_y = int(340 * scale)
    draw.text((text_x, text_y), text, fill=TEXT_DARK, font=font)

    # ---- 6. 底部小字 "Qingxin Translator" ----
    try:
        sub_font_size = int(16 * scale)
        sub_font = ImageFont.truetype("msyh.ttc", sub_font_size)
    except Exception:
        try:
            sub_font = ImageFont.truetype("arial.ttf", sub_font_size)
        except Exception:
            sub_font = ImageFont.load_default()

    sub_text = "Qingxin Translator"
    sub_bbox = draw.textbbox((0, 0), sub_text, font=sub_font)
    sub_w = sub_bbox[2] - sub_bbox[0]
    sub_x = (size - sub_w) // 2
    sub_y = int(390 * scale)
    draw.text((sub_x, sub_y), sub_text, fill=TEXT_LIGHT, font=sub_font)

    return img


def create_app_icon(size: int) -> Image.Image:
    """
    创建应用图标（简洁版）— 用于任务栏/托盘/小尺寸
    设计：悬浮 Q 书页符号，无文字
    """
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    scale = size / 256

    # ---- 1. 圆角方形背景（粉色渐变）----
    bg_radius = int(52 * scale)

    # 底层阴影
    shadow_bbox = [int(4 * scale), int(6 * scale), size - int(4 * scale), size - int(2 * scale)]
    _draw_shadow_rounded_rect(draw, shadow_bbox, bg_radius, SHADOW_SOFT, (0, int(4 * scale)), blur_passes=3)

    # 背景渐变（从上到下：浅粉 → 深粉，用多层矩形模拟）
    gradient_steps = 20
    for i in range(gradient_steps):
        ratio = i / gradient_steps
        y1 = int(size * i / gradient_steps)
        y2 = int(size * (i + 1) / gradient_steps)
        c = tuple(
            int(PINK_LIGHT[j] + (PINK_MID[j] - PINK_LIGHT[j]) * ratio)
            for j in range(3)
        ) + (255,)
        # 每层画一个圆角矩形（外层裁剪）
        temp = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        temp_draw = ImageDraw.Draw(temp)
        temp_draw.rounded_rectangle([0, y1, size, y2], radius=0, fill=c)
        img = Image.alpha_composite(img, temp)

    # 重新获取 draw 对象
    draw = ImageDraw.Draw(img)

    # 整体圆角裁剪
    mask = Image.new('L', (size, size), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle([0, 0, size - 1, size - 1], radius=bg_radius, fill=255)
    img.putalpha(mask)

    draw = ImageDraw.Draw(img)

    # ---- 2. Q 字母主体（白色）----
    q_cx = size // 2
    q_cy = int(112 * scale)
    q_r = int(52 * scale)
    ring_w = max(int(16 * scale), 2)

    # Q 的圆环（白色描边）
    draw.ellipse(
        [q_cx - q_r, q_cy - q_r, q_cx + q_r, q_cy + q_r],
        outline=WHITE, width=ring_w
    )

    # Q 的尾巴（白色粗线）
    tail_w = max(int(14 * scale), 2)
    tail_sx = q_cx + int(36 * scale)
    tail_sy = q_cy + int(36 * scale)
    tail_ex = q_cx + int(55 * scale)
    tail_ey = q_cy + int(58 * scale)
    draw.line([(tail_sx, tail_sy), (tail_ex, tail_ey)], fill=WHITE, width=tail_w)
    # 尾巴末端圆润
    dot_r = tail_w // 2 + int(1 * scale)
    draw.ellipse(
        [tail_ex - dot_r, tail_ey - dot_r, tail_ex + dot_r, tail_ey + dot_r],
        fill=WHITE
    )

    # ---- 3. 书页装饰线（在 Q 内部）----
    page_alpha = (255, 255, 255, 90)
    for offset_y in [-8, 0, 8]:
        oy = int(offset_y * scale)
        ly = q_cy + oy
        lhw = int(22 * scale) - abs(oy) // 3
        if lhw > 3:
            lw = max(int(2 * scale), 1)
            draw.line([(q_cx - lhw, ly), (q_cx + lhw, ly)], fill=page_alpha, width=lw)

    # ---- 4. 底部小装饰点（三个点，暗示"更多语言"）----
    dot_y = int(200 * scale)
    dot_spacing = int(14 * scale)
    dot_r_small = max(int(3 * scale), 1)
    dot_color = (255, 255, 255, 160)
    for dx in [-dot_spacing, 0, dot_spacing]:
        draw.ellipse(
            [q_cx + dx - dot_r_small, dot_y - dot_r_small,
             q_cx + dx + dot_r_small, dot_y + dot_r_small],
            fill=dot_color
        )

    return img


def main():
    """生成所有图标"""
    icons_dir = ROOT_DIR / "resources" / "icons"
    icons_dir.mkdir(parents=True, exist_ok=True)

    # 生成带文字的 Logo（大尺寸展示用）
    print("Generating logos...")
    for size in [512, 256, 128, 64]:
        img = create_logo(size)
        filepath = icons_dir / f"logo_{size}.png"
        img.save(filepath, "PNG")
        print(f"  Created: {filepath}")

    # 生成应用图标（简洁版，用于任务栏/托盘）
    print("\nGenerating app icons...")
    for size in [256, 128, 64, 48, 32, 16]:
        img = create_app_icon(size)
        filepath = icons_dir / f"app_{size}.png"
        filepath2 = icons_dir / f"icon_{size}.png"
        img.save(filepath, "PNG")
        img.save(filepath2, "PNG")
        print(f"  Created: {filepath}")

    # 生成 ICO 文件（多尺寸）
    print("\nGenerating ICO file...")
    ico_sizes = [16, 32, 48, 64, 128, 256]
    ico_images = [create_app_icon(s) for s in ico_sizes]

    ico_path = icons_dir / "app.ico"
    # 注意：主图必须是最大尺寸（Pillow 以主图大小作为上限过滤，
    # 若主图为 16x16 则所有大于 16 的尺寸都会被跳过，导致图标模糊）
    ico_images[-1].save(
        ico_path,
        format="ICO",
        sizes=[(s, s) for s in ico_sizes],
        append_images=ico_images[:-1]
    )
    print(f"  Created: {ico_path}")

    print("\nAll icons generated successfully!")


if __name__ == "__main__":
    main()
