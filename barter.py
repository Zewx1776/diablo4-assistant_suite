import PySimpleGUI as sg
import pyautogui
import pytesseract
import cv2
import numpy as np
import json
import os
import threading
import time
import win32gui
import win32api
import win32con
import keyboard
import logging
import tkinter as tk
from PIL import ImageGrab, ImageTk
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
import re 
from threading import Lock
from shared_config import apply_theme

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

CONFIG_FILE = 'restock_config.json'

# Set up logging
logging.basicConfig(filename='restock_assistant.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


@dataclass
class RestockConfig:
    restock_button: Tuple[int, int]
    scan_regions: List[Tuple[int, int, int, int]]  # List of 8 scan regions
    target_words: List[str] = None  # Changed from target_word to target_words

    def __post_init__(self):
        if self.target_words is None:
            self.target_words = ["Item Name"]

def load_config() -> RestockConfig:
    default_config = RestockConfig((0, 0), [(0, 0, 0, 0)] * 8)  # 8 default regions
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                config_dict = json.load(f)
            
            # Handle the transition from target_word to target_words
            if 'target_word' in config_dict:
                config_dict['target_words'] = [config_dict.pop('target_word')]
            
            # Update the dictionary with default values for new fields
            default_config_dict = asdict(default_config)
            default_config_dict.update(config_dict)
            
            # Remove any unexpected keys
            valid_keys = {'restock_button', 'scan_regions', 'target_words'}
            default_config_dict = {k: v for k, v in default_config_dict.items() if k in valid_keys}
            
            return RestockConfig(**default_config_dict)
    except (json.JSONDecodeError, KeyError) as e:
        logging.error(f"Config error: {e}. Using default configuration.")
    return default_config

class RestockProcess(threading.Thread):
    def __init__(self, config: RestockConfig, window: sg.Window):
        super().__init__()
        self.config = config
        self.window = window
        self.stop_event = threading.Event()
        self.keyboard_lock = Lock()

    def run(self) -> None:
        while not self.stop_event.is_set():
            try:
                found_target = False
                
                # Check each region for any of the target words
                for region_index, region in enumerate(self.config.scan_regions):
                    scanned_text = scan_for_text(region)
                    self.window.write_event_value('-UPDATE-', 
                        f"Scanning region {region_index + 1}: {scanned_text}")
                    
                    # Check each target word
                    for target_word in self.config.target_words:
                        if self.flexible_match(target_word.strip(), scanned_text):
                            # Right click at the center of the specific region where word was found
                            x = region[0] + region[2] // 2
                            y = region[1] + region[3] // 2
                            pyautogui.rightClick(x, y)
                            self.window.write_event_value('-UPDATE-', 
                                f"Found '{target_word}' in region {region_index + 1}")
                            found_target = True
                            break
                    
                    if found_target:
                        break
                
                if not found_target:
                    click_button(*self.config.restock_button)
                    self.window.write_event_value('-UPDATE-', "Clicked Restock button")
                
                time.sleep(1)
            except Exception as e:
                logging.error(f"Error in restock process: {e}")
                self.window.write_event_value('-UPDATE-', f"Error occurred: {e}")
                time.sleep(5)

    def flexible_match(self, target: str, text: str) -> bool:
        target = target.lower()
        text = text.lower()
        
        def normalize_spaces(s: str) -> str:
            return re.sub(r'\s+', ' ', s).strip()
        
        target = normalize_spaces(target)
        text = normalize_spaces(text)
        
        target_words = target.split()
        
        def partial_word_match(word: str, text: str) -> bool:
            if word in text:
                return True
            
            min_match_length = max(3, len(word) // 2)
            for i in range(len(text) - min_match_length + 1):
                if text[i:i+min_match_length] in word:
                    return True
            return False
        
        text_words = text.split()
        matched_words = set()
        
        for target_word in target_words:
            if any(partial_word_match(target_word, text_word) for text_word in text_words):
                matched_words.add(target_word)
        
        return len(matched_words) == len(target_words)

    def stop(self) -> None:
        with self.keyboard_lock:
            self.stop_event.set()

def create_main_window(config: RestockConfig) -> sg.Window:
    layout = [
        [sg.Text("Restock Configuration", font=('Helvetica', 20, 'bold'))],
        [sg.Text("Restock Button:", font=('Helvetica', 12)), 
         sg.Input(key='RESTOCK', 
                 default_text=f"{config.restock_button[0]},{config.restock_button[1]}", 
                 size=(30, 1),
                 font=('Helvetica', 12)), 
         sg.Button("Get", key='GET_RESTOCK', font=('Helvetica', 12))],
        [sg.Text("Target Words (comma-separated):", font=('Helvetica', 12)), 
         sg.Input(key='TARGET_WORDS', default_text=','.join(config.target_words), 
                 size=(50, 1),
                 font=('Helvetica', 12))],
        [sg.Text("Scan Regions:", font=('Helvetica', 14, 'bold'))],
    ]
    
    # Add 8 scan regions (2 rows of 4)
    for row in range(2):
        region_row = []
        for col in range(4):
            region_index = row * 4 + col
            region = config.scan_regions[region_index]
            region_row.extend([
                sg.Text(f"Region {region_index + 1}:", font=('Helvetica', 12)),
                sg.Input(key=f'SCAN_REGION_{region_index}', 
                        default_text=','.join(map(str, region)), 
                        size=(30, 1),
                        font=('Helvetica', 12)),
                sg.Button("Get", key=f'GET_SCAN_REGION_{region_index}',
                         font=('Helvetica', 12))
            ])
        layout.append(region_row)

    layout.extend([
        [sg.Button("Save Configuration", font=('Helvetica', 12)), 
         sg.Button("Start Process", font=('Helvetica', 12)), 
         sg.Button("Stop Process", font=('Helvetica', 12)), 
         sg.Button("Exit", font=('Helvetica', 12))],
        [sg.Multiline(size=(70, 10), key='OUTPUT', disabled=True, 
                     font=('Courier', 11))]
    ])
    
    return sg.Window("Restock Helper", 
                    layout, 
                    finalize=True,
                    keep_on_top=True)

def validate_config(config: RestockConfig) -> bool:
    if config.restock_button == (0, 0):
        return False
    if any(region == (0, 0, 0, 0) for region in config.scan_regions):
        return False
    if not config.target_words or not any(word.strip() for word in config.target_words):
        return False
    return True

def capture_screen_region(region: Tuple[int, int, int, int]) -> Optional[np.ndarray]:
    try:
        screenshot = pyautogui.screenshot(region=region)
        return cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
    except Exception as e:
        logging.error(f"Error capturing screen region: {e}")
        return None

def preprocess_image(image: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]

def scan_for_text(region: Tuple[int, int, int, int]) -> str:
    image = capture_screen_region(region)
    if image is None:
        return ""
    processed_image = preprocess_image(image)
    try:
        text = pytesseract.image_to_string(processed_image)
        return text.strip()
    except Exception as e:
        logging.error(f"Error scanning for text: {e}")
        return ""

def get_mouse_click() -> Tuple[int, int]:
    while True:
        if win32api.GetAsyncKeyState(0x01) & 0x8000:  # Left mouse button
            time.sleep(0.1)  # Wait for button release
            return win32gui.GetCursorPos()
        time.sleep(0.01)

def get_mouse_position(window: sg.Window, key: str) -> Tuple[int, int]:
    window.hide()
    popup = sg.Window("Get Position", 
                     [[sg.Text(f"Click on the desired position for {key}")]], 
                     no_titlebar=True, 
                     keep_on_top=True,
                     finalize=True,
                     alpha_channel=0.9)  # Added slight transparency
    
    position = get_mouse_click()
    
    popup.close()
    window.un_hide()
    return position

def make_window_transparent(window):
    hwnd = window.TKroot.winfo_id()
    win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE,
                           win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE) | win32con.WS_EX_LAYERED | win32con.WS_EX_TRANSPARENT)
    win32gui.SetLayeredWindowAttributes(hwnd, win32api.RGB(0, 0, 0), 0, win32con.LWA_COLORKEY)

def get_scan_region():
    root = tk.Tk()
    root.attributes('-alpha', 0.3)  # Set window transparency
    root.attributes('-fullscreen', True)
    root.configure(background='grey')

    canvas = tk.Canvas(root, cursor="cross")
    canvas.pack(fill=tk.BOTH, expand=True)

    rect = None
    start_x = start_y = 0
    region = None

    def on_mouse_down(event):
        nonlocal start_x, start_y, rect
        start_x, start_y = event.x, event.y
        if rect:
            canvas.delete(rect)
        rect = canvas.create_rectangle(start_x, start_y, start_x, start_y, outline='red', width=2)

    def on_mouse_move(event):
        nonlocal rect
        if rect:
            canvas.delete(rect)
            rect = canvas.create_rectangle(start_x, start_y, event.x, event.y, outline='red', width=2)

    def on_mouse_up(event):
        nonlocal region
        end_x, end_y = event.x, event.y
        region = (min(start_x, end_x), min(start_y, end_y), 
                  abs(end_x - start_x), abs(end_y - start_y))
        root.quit()

    def on_key(event):
        if event.keysym == 'Escape':
            root.quit()

    canvas.bind("<ButtonPress-1>", on_mouse_down)
    canvas.bind("<B1-Motion>", on_mouse_move)
    canvas.bind("<ButtonRelease-1>", on_mouse_up)
    root.bind("<Key>", on_key)

    root.mainloop()
    root.destroy()

    return region

def save_config(config: RestockConfig) -> None:
    with open(CONFIG_FILE, 'w') as f:
        json.dump(asdict(config), f)
    logging.info("Configuration saved successfully.")

def click_button(x: int, y: int) -> None:
    """Click at the specified coordinates."""
    try:
        pyautogui.click(x, y)
        time.sleep(0.1)  # Small delay after clicking
    except Exception as e:
        logging.error(f"Error clicking button at ({x}, {y}): {e}")

def main():
    apply_theme()
    config = load_config()
    window = create_main_window(config)
    restock_process = None
    keyboard_lock = Lock()  # Add lock for thread safety

    while True:
        event, values = window.read(timeout=100)  # Add timeout for more responsive keyboard checking
        if event == sg.WINDOW_CLOSED or event == "Exit":
            break
        elif event.startswith('GET_'):
            key = event.replace('GET_', '')
            if key.startswith('SCAN_REGION_'):
                window.hide()
                region = get_scan_region()
                window.un_hide()
                if region:
                    window[key].update(','.join(map(str, region)))
            else:
                position = get_mouse_position(window, key)
                window[key].update(f"{position[0]},{position[1]}")
        elif event == "Save Configuration":
            try:
                # Parse all 8 scan regions
                scan_regions = []
                for i in range(8):
                    region_values = values[f'SCAN_REGION_{i}'].split(',')
                    scan_regions.append(tuple(map(int, region_values)))

                new_config = RestockConfig(
                    restock_button=tuple(map(int, values['RESTOCK'].split(','))),
                    scan_regions=scan_regions,
                    target_words=values['TARGET_WORDS'].split(',')
                )
                if validate_config(new_config):
                    save_config(new_config)
                    config = new_config
                    window['OUTPUT'].print("Configuration saved successfully.")
                else:
                    window['OUTPUT'].print("Invalid configuration. Please check all fields.")
            except ValueError:
                window['OUTPUT'].print("Invalid input. Please check all fields.")
        elif event == "Start Process":
            if restock_process is None or not restock_process.is_alive():
                if validate_config(config):
                    restock_process = RestockProcess(config, window)
                    restock_process.start()
                else:
                    window['OUTPUT'].print("Invalid configuration. Please check all fields.")
        elif event == "Stop Process":
            if restock_process and restock_process.is_alive():
                restock_process.stop()
                restock_process.join()
                window['OUTPUT'].print("Process stopped.")
        elif event == '-UPDATE-':
            window['OUTPUT'].print(values['-UPDATE-'])
        
        # Modified keyboard check
        try:
            with keyboard_lock:
                if keyboard.is_pressed('p'):
                    if restock_process and restock_process.is_alive():
                        restock_process.stop()
                        restock_process.join(timeout=1.0)  # Add timeout to prevent hanging
                        if restock_process.is_alive():
                            # Force terminate if process doesn't stop gracefully
                            restock_process.join()
                        window['OUTPUT'].print("Process terminated by user (P key pressed)")
                        restock_process = None
                    time.sleep(0.1)  # Prevent multiple triggers
        except Exception as e:
            logging.error(f"Error in keyboard handling: {e}")
            window['OUTPUT'].print(f"Error in keyboard handling: {e}")

    # Cleanup when closing
    try:
        if restock_process and restock_process.is_alive():
            restock_process.stop()
            restock_process.join(timeout=1.0)
    except Exception as e:
        logging.error(f"Error during cleanup: {e}")

    window.close()

if __name__ == "__main__":
    main()