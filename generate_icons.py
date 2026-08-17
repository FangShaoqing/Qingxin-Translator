"""
Qingxin Translator - Icon Generator
生成应用图标
"""

import sys
from pathlib import Path

# 尝试导入PIL
try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("PIL not installed. Using placeholder icons.")


def create_icon(size: int = 256) -> Image.Image:
    """
    创建应用图标
    
    Args:
        size: 图标大小
        
    Returns:
        PIL Image对象
    """
    # 创建透明背景
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # 绘制圆形背景（樱花粉）
    margin = size // 8
    draw.ellipse(
        [margin, margin, size - margin, size - margin],
        fill=(250, 218, 222, 255)  # #FADADE
    )
    
    # 绘制内部圆形（白色）
    inner_margin = size // 4
    draw.ellipse(
        [inner_margin, inner_margin, size - inner_margin, size - inner_margin],
        fill=(255, 255, 255, 255)
    )
    
    # 绘制文字 "QT" 或 "译"
    try:
        # 尝试加载字体
        font_size = size // 3
        font = ImageFont.truetype("arial.ttf", font_size)
    except:
        font = ImageFont.load_default()
    
    # 绘制文字
    text = "译"
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (size - text_width) // 2
    y = (size - text_height) // 2 - bbox[1]
    
    draw.text((x, y), text, fill=(250, 218, 222, 255), font=font)
    
    return img


def save_icons():
    """保存图标文件"""
    if not PIL_AVAILABLE:
        print("Cannot generate icons without PIL.")
        print("Please create icons manually or install PIL: pip install Pillow")
        return
    
    icons_dir = Path(__file__).parent / "resources" / "icons"
    icons_dir.mkdir(parents=True, exist_ok=True)
    
    # 生成不同尺寸的图标
    sizes = {
        "app.ico": 256,
        "app_16.png": 16,
        "app_32.png": 32,
        "app_48.png": 48,
        "app_64.png": 64,
        "app_128.png": 128,
        "app_256.png": 256,
    }
    
    for filename, size in sizes.items():
        img = create_icon(size)
        filepath = icons_dir / filename
        
        if filename.endswith('.ico'):
            # 保存为ICO格式（多尺寸）
            img.save(filepath, format='ICO', sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
        else:
            img.save(filepath, format='PNG')
        
        print(f"Created: {filepath}")


if __name__ == "__main__":
    save_icons()
