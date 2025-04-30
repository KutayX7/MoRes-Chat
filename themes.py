themes = {
    "dark": {
        "theme.background.color0": "#2a2a2c",
        "theme.background.color1": "#3f3f4a",
        "theme.font": "Arial 10",
        "theme.foreground": "#ffffff",
        "theme.button.idle": "#30303a",
        "theme.button.hover": "#222",
        "theme.button.selected": "#11e",
        "theme.button.send.idle": "#4444aa",
        "theme.button.send.hover": "#333388",
        "theme.button.send.foreground": "#ffffff",
        "theme.button.send.text": "> Send >"
    },
    "light": {
        "theme.background.color0": "#d0d0d0",
        "theme.background.color1": "#e0e0e0",
        "theme.font": "Arial 10",
        "theme.foreground": "#000000",
        "theme.button.idle": "#aaabb5",
        "theme.button.hover": "#9d9daa",
        "theme.button.selected": "#a1b7ee",
        "theme.button.send.idle": "#4444aa",
        "theme.button.send.hover": "#333388",
        "theme.button.send.foreground": "#ffffff",
        "theme.button.send.text": "> Send >"
    },
    "pink": {
        "theme.background.color0": "#4A102A",
        "theme.background.color1": "#85193C",
        "theme.font": "Arial 10",
        "theme.foreground": "#ffffff",
        "theme.button.idle": "#3a304a",
        "theme.button.hover": "#222",
        "theme.button.selected": "#8d8d00",
        "theme.button.send.idle": "#643864",
        "theme.button.send.hover": "#552c55",
        "theme.button.send.foreground": "#ffffff",
        "theme.button.send.text": "> Send >"
    },
    "purple": {
        "theme.background.color0": "#381362",
        "theme.background.color1": "#532f72",
        "theme.font": "Arial 10",
        "theme.foreground": "#ffffff",
        "theme.button.idle": "#303a30",
        "theme.button.hover": "#222",
        "theme.button.selected": "#11af11",
        "theme.button.send.idle": "#52b853",
        "theme.button.send.hover": "#3f6d4e",
        "theme.button.send.foreground": "#ffffff",
        "theme.button.send.text": "> Send >"
    },
    "red": {
        "theme.background.color0": "#952323",
        "theme.background.color1": "#A73121",
        "theme.font": "Arial 10",
        "theme.foreground": "#ffffff",
        "theme.button.idle": "#3a3030",
        "theme.button.hover": "#222",
        "theme.button.selected": "#be762b",
        "theme.button.send.idle": "#FD841F",
        "theme.button.send.hover": "#fd711f",
        "theme.button.send.foreground": "#ffffff",
        "theme.button.send.text": "> Send >"
    },
    "green": {
        "theme.background.color0": "#18230F",
        "theme.background.color1": "#27391C",
        "theme.font": "Arial 10",
        "theme.foreground": "#ffffff",
        "theme.button.idle": "#303a30",
        "theme.button.hover": "#222",
        "theme.button.selected": "#115757",
        "theme.button.send.idle": "#52d053",
        "theme.button.send.hover": "#333388",
        "theme.button.send.foreground": "#ffffff",
        "theme.button.send.text": "> Send >"
    },
    "blue": {
        "theme.background.color0": "#213448",
        "theme.background.color1": "#547792",
        "theme.font": "Arial 10",
        "theme.foreground": "#ffffff",
        "theme.button.idle": "#3a303a",
        "theme.button.hover": "#222",
        "theme.button.selected": "#b311b3",
        "theme.button.send.idle": "#C95792",
        "theme.button.send.hover": "#7C4585",
        "theme.button.send.foreground": "#ffffff",
        "theme.button.send.text": "> Send >"
    }
}

def is_valid_theme(theme_name: str) -> bool:
    return theme_name in themes

def get_theme_settings(theme_name: str) -> dict:
    return themes.get(theme_name, {})