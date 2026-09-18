import colorsys
import os
import re
import threading
import unicodedata

RENDER_GATE = threading.Semaphore(1)
SEND_GATE = threading.Semaphore(1)

_active_render_scale = 1.0


def render_scale():
    return max(_active_render_scale, 0.12)


def run_heavy(func, *args, **kwargs):
    try:
        from gevent import monkey as _gm
        if _gm.is_module_patched("socket"):
            import gevent
            return gevent.get_hub().threadpool.apply(func, args, kwargs)
    except Exception:
        pass
    return func(*args, **kwargs)


def new_figure(fig_width, fig_height, dpi):
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    fig = Figure(figsize=(fig_width, fig_height), dpi=dpi)
    FigureCanvasAgg(fig)
    ax = fig.add_subplot(1, 1, 1)
    return fig, ax


def budget_dpi(fig_width, fig_height, base_dpi=100, budget_px=8300):
    global _active_render_scale
    fig_max = max(float(fig_width or 0), float(fig_height or 0), 1.0)
    dpi = int(base_dpi)
    if fig_max * dpi > budget_px:
        dpi = max(int(budget_px / fig_max), 12)
    _active_render_scale = max(0.12, min(dpi / 100.0, 1.0))
    return dpi


def load_font(font_file, font_size):
    from PIL import ImageFont
    font = None
    if font_file and os.path.exists(font_file):
        try:
            font = ImageFont.truetype(font_file, font_size)
        except Exception:
            pass
    if font is None:
        try:
            font = ImageFont.load_default()
        except Exception:
            font = None
    return font


def _char_is_cjk(ch: str) -> bool:
    cp = ord(ch)
    return (
        0x3400 <= cp <= 0x4DBF
        or 0x4E00 <= cp <= 0x9FFF
        or 0xF900 <= cp <= 0xFAFF
        or 0x20000 <= cp <= 0x3FFFF
    )


def _tokenize_wrap_units(text: str) -> list:
    tokens = []
    buf_text = ""
    buf_kind = ""

    def half_units(length):
        return max((int(length) + 1) // 2, 1)

    def flush():
        nonlocal buf_text, buf_kind
        if buf_text:
            if buf_kind in ("digit", "word", "half"):
                tokens.append((buf_text, buf_kind, half_units(len(buf_text))))
            else:
                tokens.append((buf_text, buf_kind, 1))
            buf_text = ""
            buf_kind = ""

    for ch in str(text or ""):
        if ch.isspace():
            flush()
            tokens.append((ch, "space", 0))
            continue
        if unicodedata.category(ch).startswith("M"):
            if buf_text:
                buf_text += ch
            elif tokens and tokens[-1][1] != "space":
                t, k, u = tokens[-1]
                tokens[-1] = (t + ch, k, u)
            else:
                tokens.append((ch, "wide", 1))
            continue
        if ch.isdigit():
            if buf_kind == "word":
                buf_text += ch
                continue
            if buf_kind != "digit":
                flush()
                buf_kind = "digit"
            buf_text += ch
            continue
        if _char_is_cjk(ch):
            flush()
            tokens.append((ch, "cjk", 1))
            continue
        if ch in ("'", "\u2019", "-", "\u2010") and buf_kind == "word":
            buf_text += ch
            continue
        if unicodedata.category(ch).startswith("L"):
            if buf_kind == "digit":
                buf_kind = "word"
                buf_text += ch
                continue
            if buf_kind != "word":
                flush()
                buf_kind = "word"
            buf_text += ch
            continue
        if ord(ch) < 0x80:
            if buf_kind != "half":
                flush()
                buf_kind = "half"
            buf_text += ch
            continue
        flush()
        tokens.append((ch, "wide", 1))
    flush()
    return tokens


def _wrap_limit(text: str) -> int:
    total_units = sum(u for _, _, u in _tokenize_wrap_units(text))
    if total_units <= 100:
        return 10
    if total_units <= 500:
        return 20
    return 30


def wrap_text(text: str, max_chars=None) -> list:
    safe = str(text or "").strip()
    if not safe:
        return ["Node"]
    line_limit = int(max_chars) if max_chars else _wrap_limit(safe)
    line_limit = max(line_limit, 1)
    rows = []
    for raw in re.split(r"\s*\n\s*", safe):
        part = raw.strip()
        if not part:
            continue
        current = ""
        units = 0
        pending = ""
        for tok_text, tok_kind, tok_units in _tokenize_wrap_units(part):
            if tok_kind == "space":
                if current:
                    pending = " "
                continue
            if current and units + tok_units > line_limit:
                rows.append(current)
                current = ""
                units = 0
                pending = ""
            current += pending + tok_text
            pending = ""
            units += tok_units
            if tok_kind == "digit" and units >= line_limit:
                rows.append(current)
                current = ""
                units = 0
        if current:
            rows.append(current)
    return rows or ["Node"]


def estimate_width_units(text, depth_level):
    eff = max(1, min(int(depth_level), 5))
    scale = max(1.0 - (eff - 1) * 0.08, 0.68)
    max_line = 0.0
    for line in wrap_text(str(text)):
        w = 0.0
        for ch in line:
            if ch.isspace():
                w += 0.25
            elif ord(ch) > 127:
                w += 1.0
            else:
                w += 0.58
        if w > max_line:
            max_line = w
    est = max_line * scale * 0.40 + 0.95
    return max(est, 1.35)


def node_height_units(text, depth_level):
    eff = max(1, min(int(depth_level), 5))
    line_count = len(wrap_text(str(text)))
    base = max(1.00 - 0.04 * (eff - 1), 0.78)
    extra = max(0.46 - 0.025 * (eff - 1), 0.34)
    return base + max(line_count - 1, 0) * extra


def _legacy_border(depth_level) -> int:
    return 4 if int(depth_level) <= 1 else 3


def node_border_width(depth_level) -> int:
    level = max(1, min(int(depth_level), 5))
    if level >= 5:
        return _legacy_border(5)
    root_w = _legacy_border(1) * 5
    target = _legacy_border(5)
    return max(target, int(round(root_w - (root_w - target) * (level - 1) / 4.0)))


def node_corner_radius(depth_level) -> int:
    level = max(1, min(int(depth_level), 5))
    base = 6
    if level >= 5:
        return base
    root_r = base * 5
    return max(base, int(round(root_r - (root_r - base) * (level - 1) / 4.0)))


def inner_corner_radius(depth_level) -> int:
    return max(6, int(round(node_corner_radius(depth_level) - node_border_width(depth_level))))


def line_linewidth_for(depth_level) -> float:
    return node_border_width(depth_level) * 0.72


def _hex_to_rgb(color):
    c = str(color).strip().lstrip("#")
    if len(c) == 6:
        return (int(c[0:2], 16) / 255.0, int(c[2:4], 16) / 255.0, int(c[4:6], 16) / 255.0)
    raise ValueError("bad hex color: %s" % color)


def _luminance(color):
    r, g, b = _hex_to_rgb(color)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def dark_text_color(border_color):
    try:
        r, g, b = _hex_to_rgb(border_color)
    except Exception:
        return "#1F1F1F"
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    dark_s = min(max(s * 1.15, 0.55), 1.0)
    dark_v = 0.33
    if abs(dark_v - v) < 0.18:
        dark_v = max(v - 0.25, 0.08)
        dark_s = s
    dr, dg, db = colorsys.hsv_to_rgb(h, dark_s, dark_v)
    return "#%02X%02X%02X" % (int(round(dr * 255)), int(round(dg * 255)), int(round(db * 255)))


def light_text_color(border_color):
    try:
        r, g, b = _hex_to_rgb(border_color)
    except Exception:
        return "#F5F5F5"
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    light_v = 0.90
    light_s = min(max(s * 0.9, 0.10), 0.55)
    if abs(light_v - v) < 0.18:
        light_v = min(v + 0.30, 0.97)
        light_s = s
    lr, lg, lb = colorsys.hsv_to_rgb(h, light_s, light_v)
    return "#%02X%02X%02X" % (int(round(lr * 255)), int(round(lg * 255)), int(round(lb * 255)))


def contrast_text_color(border_color, bg_color):
    try:
        if _luminance(bg_color) >= 0.5:
            return dark_text_color(border_color)
        return light_text_color(border_color)
    except Exception:
        return border_color
