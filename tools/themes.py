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
    "aurora": {
        "background": "#171A21",
        "node_fill": "#232734",
        "root_color": "#7BF0C8",
        "branch_colors": [
            "#6EE3F5", "#C39BF7", "#F2A9DD", "#9CCC65", "#FFD54F", "#FF8A65",
            "#4DD0E1", "#B39DDB", "#AED581", "#FFD180", "#F06292", "#81D4FA",
        ],
    },
}


def get_theme(name):
    key = str(name or "classic").strip().lower()
    return THEMES.get(key, THEMES["classic"])
