from PIL import Image, ImageDraw

def draw_shield_icon(size):
    # Create RGBA canvas
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    padding = max(1, size // 10)
    w, h = size, size
    
    # Shield points: top-left, top-right, bottom-middle
    shield_pts = [
        (w // 2, padding),
        (w - padding, padding + h // 6),
        (w - padding, h // 2),
        (w // 2, h - padding),
        (padding, h // 2),
        (padding, padding + h // 6)
    ]
    
    # Fill shield with blue/cyan gradient color
    draw.polygon(shield_pts, fill=(56, 189, 248, 255), outline=(129, 140, 248, 255))
    
    # Draw checkmark inside if size >= 32
    if size >= 32:
        check_pts = [
            (w * 0.35, h * 0.48),
            (w * 0.46, h * 0.62),
            (w * 0.68, h * 0.38)
        ]
        line_w = max(2, size // 16)
        draw.line(check_pts, fill=(15, 23, 42, 255), width=line_w, joint="round")
        
    return img

if __name__ == "__main__":
    from pathlib import Path
    assets_dir = Path(__file__).parent
    assets_dir.mkdir(exist_ok=True)
    
    for s in [16, 48, 128]:
        icon = draw_shield_icon(s)
        icon.save(assets_dir / f"icon{s}.png")
        print(f"Generated icon{s}.png")
