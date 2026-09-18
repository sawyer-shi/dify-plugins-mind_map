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
}


def get_theme(name):
    key = str(name or "classic").strip().lower()
    return THEMES.get(key, THEMES["classic"])
