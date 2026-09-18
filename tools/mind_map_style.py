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
