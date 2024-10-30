import PySimpleGUI as sg
import sys
import os
import importlib.util
from shared_config import load_theme, save_theme, apply_theme
from typing import Tuple

def get_resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def create_main_window() -> sg.Window:
    themes = sg.theme_list()
    current_theme = load_theme()
    
    layout = [
        [sg.Text("D4 Assistant Launcher", font=('Helvetica', 20, 'bold'))],
        [sg.Text("Select theme:", font=('Helvetica', 12)),
         sg.Combo(themes, key='THEME', default_value=current_theme, 
                 enable_events=True, font=('Helvetica', 12), size=(30, 1))],
        [sg.Text("Select tool to launch:", font=('Helvetica', 12))],
        [sg.Combo(
            ['Kurast Helper', 'Barter Assistant', 'Enchant Helper', 'Masterwork Assistant'],
            key='TOOL',
            default_value='Kurast Helper',
            font=('Helvetica', 12),
            size=(30, 4)
        )],
        [sg.Button("Launch", font=('Helvetica', 12)), 
         sg.Button("Exit", font=('Helvetica', 12))],
        [sg.Text("", size=(40, 1), key='STATUS', font=('Helvetica', 12))]
    ]
    
    return sg.Window("D4 Assistant Launcher", 
                    layout, 
                    finalize=True,
                    keep_on_top=False)

def import_module_from_file(module_name, file_path):
    try:
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None:
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    except Exception as e:
        print(f"Error importing module: {e}")
        return None

def launch_tool(tool_name: str) -> bool:
    tool_map = {
        'Kurast Helper': 'kurast',
        'Barter Assistant': 'barter',
        'Enchant Helper': 'enchant',
        'Masterwork Assistant': 'masterwork'
    }
    
    if tool_name not in tool_map:
        return False
        
    try:
        module_name = tool_map[tool_name]
        file_path = get_resource_path(f"{module_name}.py")
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Tool file not found: {file_path}")
            
        # Debug information
        print(f"Loading module from: {file_path}")
        print(f"Resource path base: {os.path.dirname(file_path)}")
        print(f"Available files: {os.listdir(os.path.dirname(file_path))}")
        
        with open(file_path, 'r') as f:
            code = compile(f.read(), file_path, 'exec')
            module_globals = {}
            exec(code, module_globals)
            
        if 'main' not in module_globals:
            raise ImportError(f"No main function found in {module_name}")
            
        module_globals['main']()
        return True
        
    except Exception as e:
        import traceback
        error_msg = f"Error launching {tool_name}:\n{str(e)}\n\n{traceback.format_exc()}"
        print(error_msg)  # Print to console for debugging
        sg.popup_error(error_msg)
        return False

def main():
    apply_theme()
    window = create_main_window()
    
    while True:
        event, values = window.read()
        
        if event == sg.WIN_CLOSED or event == 'Exit':
            break
            
        if event == 'THEME':
            save_theme(values['THEME'])
            sg.theme(values['THEME'])
            window.close()
            window = create_main_window()
            
        if event == 'Launch':
            tool_name = values['TOOL']
            window['STATUS'].update("Launching " + tool_name)
            if not launch_tool(tool_name):
                window['STATUS'].update("Failed to launch " + tool_name)
            else:
                window['STATUS'].update(tool_name + " launched successfully")
    
    window.close()

if __name__ == '__main__':
    main()