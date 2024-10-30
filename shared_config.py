import json
import PySimpleGUI as sg

THEME_CONFIG_FILE = 'theme_config.json'

def load_theme() -> str:
    try:
        with open(THEME_CONFIG_FILE, 'r') as f:
            config = json.load(f)
            return config.get('theme', 'DarkGrey9')
    except:
        return 'DarkGrey9'

def save_theme(theme: str) -> None:
    with open(THEME_CONFIG_FILE, 'w') as f:
        json.dump({'theme': theme}, f)

def apply_theme() -> None:
    theme = load_theme()
    sg.theme(theme)