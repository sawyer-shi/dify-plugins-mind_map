THEMES = {
    "classic": {
        "background": "#FFFFFF",
        "node_fill": "#FFFFFF",
        "root_color": "#333333",
        "branch_colors": [
            "#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FECA57", "#FF9FF3",
            "#54A0FF", "#5F27CD", "#00D2D3", "#FF9F43", "#EE5A24", "#0984E3",
        ],
    },
    "dark": {
        "background": "#202124",
        "node_fill": "#2B2E33",
        "root_color": "#7EE8D5",
        "branch_colors": [
            "#FF8A80", "#80D8CF", "#82B1FF", "#B9F6CA", "#FFE082", "#F48FB1",
            "#80DEEA", "#B388FF", "#84FFFF", "#FFCC80", "#FFAB91", "#8C9EFF",
        ],
    },
    "sepia": {
        "background": "#F5F1E8",
        "node_fill": "#FFFDF7",
        "root_color": "#6B5B45",
        "branch_colors": [
            "#B85C38", "#7A9E7E", "#5B7C99", "#C99A3C", "#A26769", "#8B6F47",
            "#4F8A8B", "#B0764C", "#7E6BA5", "#987284", "#5E8C61", "#C77B4F",
        ],
    },
    "industrial": {
        "background": "#2F343B",
        "node_fill": "#39404A",
        "root_color": "#F5A623",
        "branch_colors": [
            "#F28C28", "#5DADE2", "#F4D03F", "#7DCEA0", "#EC7063", "#AF7AC5",
            "#48C9B0", "#F5B041", "#85C1E9", "#AAB7B8", "#E67E22", "#52BE80",
        ],
        "grid": {
            "color": "#3D444D",
            "size": 40,
        },
    },
}


def get_theme(name):
    key = str(name or "industrial").strip().lower()
    return THEMES.get(key, THEMES["industrial"])


def draw_canvas_grid(img, draw, theme):
    grid = theme.get("grid")
    if not grid:
        return
    w, h = img.size
    step = grid["size"]
    color = grid["color"]
    for x in range(0, w, step):
        draw.line([(x, 0), (x, h)], fill=color, width=1)
    for y in range(0, h, step):
        draw.line([(0, y), (w, y)], fill=color, width=1)
