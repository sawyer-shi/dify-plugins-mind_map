from PIL import Image, ImageDraw, ImageFont

def add_watermark(image, text, opacity=40, layout='corners', font_path=None):
    """
    Add watermark to the image.
    :param image: PIL Image object
    :param text: Watermark text
    :param opacity: 0-255
    :param layout: 'tile', 'tile_rotate', 'corners', 'br', 'bl', 'tr', 'tl'
    :param font_path: Path to font file
    :return: PIL Image object with watermark
    """
    if not text:
        return image

    rgba_image = image.convert('RGBA')
    txt_layer = Image.new('RGBA', rgba_image.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(txt_layer)

    # Font setup
    font_size = 40
    font = None
    if font_path:
        try:
            font = ImageFont.truetype(font_path, font_size)
        except Exception:
            pass
    
    if font is None:
        try:
            font = ImageFont.load_default()
        except:
            return image

    # Calculate text size
    try:
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
    except AttributeError:
        # Fallback for older Pillow versions
        text_width, text_height = draw.textsize(text, font=font)

    # Color with opacity
    try:
        opacity = int(opacity)
    except:
        opacity = 40
    
    # Ensure opacity is within 0-255
    opacity = max(0, min(255, opacity))
    color = (128, 128, 128, opacity)

    width, height = image.size
    margin = 20

    if layout == 'corners':
        positions = [
            (margin, margin), # tl
            (width - text_width - margin, margin), # tr
            (margin, height - text_height - margin), # bl
            (width - text_width - margin, height - text_height - margin) # br
        ]
        for pos in positions:
            draw.text(pos, text, font=font, fill=color)

    elif layout == 'tl':
        draw.text((margin, margin), text, font=font, fill=color)
    elif layout == 'tr':
        draw.text((width - text_width - margin, margin), text, font=font, fill=color)
    elif layout == 'bl':
        draw.text((margin, height - text_height - margin), text, font=font, fill=color)
    elif layout == 'br':
        draw.text((width - text_width - margin, height - text_height - margin), text, font=font, fill=color)

    elif layout == 'tile':
        gap_x = text_width + 200
        gap_y = text_height + 200
        for y in range(margin, height, gap_y):
            for x in range(margin, width, gap_x):
                draw.text((x, y), text, font=font, fill=color)

    elif layout == 'center':
        # Center the watermark
        center_x = (width - text_width) // 2
        center_y = (height - text_height) // 2
        draw.text((center_x, center_y), text, font=font, fill=color)
                
    else:
        # Default to corners if unknown layout
        positions = [
            (margin, margin),
            (width - text_width - margin, margin),
            (margin, height - text_height - margin),
            (width - text_width - margin, height - text_height - margin)
        ]
        for pos in positions:
            draw.text(pos, text, font=font, fill=color)

    out = Image.alpha_composite(rgba_image, txt_layer)
    return out.convert('RGB')
