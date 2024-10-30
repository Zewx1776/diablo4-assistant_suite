import PySimpleGUI as sg
import subprocess
import sys
import os
from shared_config import load_theme, save_theme, apply_theme

def create_main_window() -> sg.Window:
    themes = sg.theme_list()
    current_theme = load_theme()
    
    layout = [
        [sg.Text("D4 Assistant Launcher", font=('Helvetica', 16))],
        [sg.Text("Select theme:"),
         sg.Combo(themes, key='THEME', default_value=current_theme, enable_events=True)],
        [sg.Text("Select tool to launch:")],
        [sg.Combo(
            ['Kurast Helper', 'Barter Assistant', 'Enchant Helper', 'Masterwork Assistant'],
            key='TOOL',
            default_value='Kurast Helper',
            size=(20, 4)
        )],
        [sg.Button("Launch"), sg.Button("Exit")],
        [sg.Text("", size=(40, 1), key='STATUS')]
    ]
    
    return sg.Window("D4 Assistant Launcher", layout, finalize=True)

def launch_tool(tool_name: str) -> bool:
    tool_map = {
        'Kurast Helper': 'kurast.py',
        'Barter Assistant': 'barter.py',
        'Enchant Helper': 'enchant.py',
        'Masterwork Assistant': 'masterwork.py'
    }
    
    if tool_name not in tool_map:
        return False
        
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        tool_path = os.path.join(script_dir, tool_map[tool_name])
        
        if not os.path.exists(tool_path):
            raise FileNotFoundError(f"Tool not found: {tool_path}")
            
        python_executable = sys.executable
        subprocess.Popen([python_executable, tool_path])
        return True
    except Exception as e:
        print(f"Error launching tool: {e}")
        return False

def main():
    apply_theme()
    window = create_main_window()
    
    while True:
        event, values = window.read()
        
        if event == sg.WINDOW_CLOSED or event == "Exit":
            break
            
        elif event == "THEME":
            save_theme(values['THEME'])
            sg.theme(values['THEME'])
            window.close()
            window = create_main_window()
            
        elif event == "Launch":
            tool_name = values['TOOL']
            if launch_tool(tool_name):
                window['STATUS'].update(f"Launched {tool_name} successfully!")
            else:
                window['STATUS'].update(f"Failed to launch {tool_name}")
    
    window.close()

if __name__ == "__main__":
    main()