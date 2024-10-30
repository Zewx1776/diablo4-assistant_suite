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

CONFIG_FILE = 'enchant_config.json'

logging.basicConfig(filename='enchant_assistant.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

@dataclass
class EnchantConfig:
    enchant_button: Tuple[int, int]
    replace_button: Tuple[int, int]
    close_button: Tuple[int, int]
    scan_regions: List[Tuple[int, int, int, int]]  # List of 2 scan regions
    scan_buttons: List[Tuple[int, int]]  # List of 2 buttons corresponding to scan regions
    target_words: List[str] = None
    click_delay: float = 0.1        # Delay after each click
    enchant_delay: float = 1.0      # Delay after clicking enchant
    replace_delay: float = 0.5      # Delay between scan and replace
    loop_delay: float = 1.0         # Delay between iterations

    def __post_init__(self):
        if self.target_words is None:
            self.target_words = ["Target Affix"]

def load_config() -> EnchantConfig:
    default_config = EnchantConfig(
        (0, 0), (0, 0), (0, 0), 
        [(0, 0, 0, 0)] * 2,  # 2 scan regions
        [(0, 0)] * 2,  # 2 scan buttons
    )
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                config_dict = json.load(f)
            
            if 'target_word' in config_dict:
                config_dict['target_words'] = [config_dict.pop('target_word')]
            
            default_config_dict = asdict(default_config)
            default_config_dict.update(config_dict)
            
            valid_keys = {'enchant_button', 'replace_button', 'close_button', 
                         'scan_regions', 'scan_buttons', 'target_words', 
                         'click_delay', 'enchant_delay', 'replace_delay', 'loop_delay'}
            default_config_dict = {k: v for k, v in default_config_dict.items() 
                                 if k in valid_keys}
            
            return EnchantConfig(**default_config_dict)
    except Exception as e:
        logging.error(f"Config error: {e}. Using default configuration.")
    return default_config

class EnchantProcess(threading.Thread):
    def __init__(self, config: EnchantConfig, window: sg.Window):
        super().__init__()
        self.config = config
        self.window = window
        self.stop_event = threading.Event()
        self.keyboard_lock = Lock()

    def run(self) -> None:
        while not self.stop_event.is_set():
            try:
                # Click enchant button
                click_button(*self.config.enchant_button, self.config.click_delay)
                self.window.write_event_value('-UPDATE-', "Clicked Enchant button")
                time.sleep(self.config.enchant_delay)

                found_target = False
                # Check each region for any of the target words
                for region_index, region in enumerate(self.config.scan_regions):
                    scanned_text = scan_for_text(region)
                    self.window.write_event_value('-UPDATE-', 
                        f"Scanning region {region_index + 1}: {scanned_text}")
                    
                    # Check each target word
                    for target_word in self.config.target_words:
                        if self.flexible_match(target_word.strip(), scanned_text):
                            # Click the corresponding scan button for this region
                            click_button(*self.config.scan_buttons[region_index], self.config.click_delay)
                            self.window.write_event_value('-UPDATE-', 
                                f"Found '{target_word}' in region {region_index + 1} and clicked its button")
                            
                            # Click replace button
                            time.sleep(self.config.replace_delay)
                            click_button(*self.config.replace_button, self.config.click_delay)
                            self.window.write_event_value('-UPDATE-', "Clicked Replace button")
                            found_target = True
                            
                            # Stop the process after replacing
                            self.stop()
                            self.window.write_event_value('-UPDATE-', 
                                "Target found and replaced. Process stopped.")
                            return
                    
                    if found_target:
                        break
                
                if not found_target:
                    # If target not found, click close
                    click_button(*self.config.close_button)
                    self.window.write_event_value('-UPDATE-', "Target not found, clicked Close button")
                
                time.sleep(self.config.loop_delay)
            except Exception as e:
                logging.error(f"Error in enchant process: {e}")
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
        text_words = text.split()
        matched_words = set()
        
        for target_word in target_words:
            if any(self.partial_word_match(target_word, text_word) for text_word in text_words):
                matched_words.add(target_word)
        
        return len(matched_words) == len(target_words)

    def partial_word_match(self, word: str, text: str) -> bool:
        if word in text:
            return True
        
        min_match_length = max(3, len(word) // 2)
        for i in range(len(text) - min_match_length + 1):
            if text[i:i+min_match_length] in word:
                return True
        return False

    def stop(self) -> None:
        with self.keyboard_lock:
            self.stop_event.set()

def create_main_window(config: EnchantConfig) -> sg.Window:
    layout = [
        [sg.Text("Enchant Configuration")],
        [sg.Text("Enchant Button:"), 
         sg.Input(key='ENCHANT', default_text=f"{config.enchant_button[0]},{config.enchant_button[1]}", 
                 size=(15, 1)), 
         sg.Button("Get", key='GET_ENCHANT')],
        [sg.Text("Replace Button:"), 
         sg.Input(key='REPLACE', default_text=f"{config.replace_button[0]},{config.replace_button[1]}", 
                 size=(15, 1)), 
         sg.Button("Get", key='GET_REPLACE')],
        [sg.Text("Close Button:"), 
         sg.Input(key='CLOSE', default_text=f"{config.close_button[0]},{config.close_button[1]}", 
                 size=(15, 1)), 
         sg.Button("Get", key='GET_CLOSE')],
        [sg.Text("Target Words (comma-separated):"), 
         sg.Input(key='TARGET_WORDS', default_text=','.join(config.target_words), size=(40, 1))],
        [sg.Text("Scan Regions and Buttons:", font=('Helvetica', 10, 'bold'))],
        [sg.Text("Delays (seconds):", font=('Helvetica', 10, 'bold'))],
        [sg.Text("Click Delay:"), 
         sg.Input(key='CLICK_DELAY', default_text=str(config.click_delay), size=(5, 1))],
        [sg.Text("Enchant Delay:"), 
         sg.Input(key='ENCHANT_DELAY', default_text=str(config.enchant_delay), size=(5, 1))],
        [sg.Text("Replace Delay:"), 
         sg.Input(key='REPLACE_DELAY', default_text=str(config.replace_delay), size=(5, 1))],
        [sg.Text("Loop Delay:"), 
         sg.Input(key='LOOP_DELAY', default_text=str(config.loop_delay), size=(5, 1))],
    ]
    
    # Add 2 scan regions with their corresponding buttons
    for i in range(2):
        region = config.scan_regions[i]
        button = config.scan_buttons[i]
        layout.extend([
            [sg.Text(f"Scan Region {i + 1}:"),
             sg.Input(key=f'SCAN_REGION_{i}', 
                     default_text=','.join(map(str, region)), 
                     size=(20, 1)),
             sg.Button("Get", key=f'GET_SCAN_REGION_{i}')],
            [sg.Text(f"Scan Button {i + 1}:"),
             sg.Input(key=f'SCAN_BUTTON_{i}', 
                     default_text=f"{button[0]},{button[1]}", 
                     size=(15, 1)),
             sg.Button("Get", key=f'GET_SCAN_BUTTON_{i}')]
        ])

    layout.extend([
        [sg.Button("Save Configuration"), sg.Button("Start Process"), 
         sg.Button("Stop Process"), sg.Button("Exit")],
        [sg.Multiline(size=(60, 10), key='OUTPUT', disabled=True)]
    ])
    
    return sg.Window("Enchant Helper", layout, finalize=True)

def validate_config(config: EnchantConfig) -> bool:
    if config.enchant_button == (0, 0):
        return False
    if config.replace_button == (0, 0):
        return False
    if config.close_button == (0, 0):
        return False
    if any(region == (0, 0, 0, 0) for region in config.scan_regions):
        return False
    if any(button == (0, 0) for button in config.scan_buttons):
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
    popup = sg.Window("Get Position", [[sg.Text(f"Click on the desired position for {key}")]], 
                     no_titlebar=True, keep_on_top=True, finalize=True)
    position = get_mouse_click()
    popup.close()
    window.un_hide()
    return position

def make_window_transparent(window):
    hwnd = window.TKroot.winfo_id()
    win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE,
                          win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE) | 
                          win32con.WS_EX_LAYERED | win32con.WS_EX_TRANSPARENT)
    win32gui.SetLayeredWindowAttributes(hwnd, win32api.RGB(0, 0, 0), 0, win32con.LWA_COLORKEY)

def get_scan_region():
    root = tk.Tk()
    root.attributes('-alpha', 0.3)
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

def save_config(config: EnchantConfig) -> None:
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(asdict(config), f)
        logging.info("Configuration saved successfully.")
    except Exception as e:
        logging.error(f"Error saving configuration: {e}")

def click_button(x: int, y: int, delay: float = 0.1) -> None:
    try:
        pyautogui.click(x, y)
        time.sleep(delay)
    except Exception as e:
        logging.error(f"Error clicking button at ({x}, {y}): {e}")

def main():
    apply_theme()
    config = load_config()
    window = create_main_window(config)
    enchant_process = None
    keyboard_lock = Lock()

    while True:
        event, values = window.read(timeout=100)
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
                scan_regions = []
                scan_buttons = []
                for i in range(2):
                    region_values = values[f'SCAN_REGION_{i}'].split(',')
                    button_values = values[f'SCAN_BUTTON_{i}'].split(',')
                    scan_regions.append(tuple(map(int, region_values)))
                    scan_buttons.append(tuple(map(int, button_values)))

                new_config = EnchantConfig(
                    enchant_button=tuple(map(int, values['ENCHANT'].split(','))),
                    replace_button=tuple(map(int, values['REPLACE'].split(','))),
                    close_button=tuple(map(int, values['CLOSE'].split(','))),
                    scan_regions=scan_regions,
                    scan_buttons=scan_buttons,
                    target_words=[word.strip() for word in values['TARGET_WORDS'].split(',') if word.strip()],
                    click_delay=float(values['CLICK_DELAY']),
                    enchant_delay=float(values['ENCHANT_DELAY']),
                    replace_delay=float(values['REPLACE_DELAY']),
                    loop_delay=float(values['LOOP_DELAY'])
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
            if enchant_process is None or not enchant_process.is_alive():
                if validate_config(config):
                    enchant_process = EnchantProcess(config, window)
                    enchant_process.start()
                else:
                    window['OUTPUT'].print("Invalid configuration. Please check all fields.")
        elif event == "Stop Process":
            if enchant_process and enchant_process.is_alive():
                enchant_process.stop()
                enchant_process.join()
                window['OUTPUT'].print("Process stopped.")
        elif event == '-UPDATE-':
            window['OUTPUT'].print(values['-UPDATE-'])
        
        try:
            with keyboard_lock:
                if keyboard.is_pressed('p'):
                    if enchant_process and enchant_process.is_alive():
                        enchant_process.stop()
                        enchant_process.join(timeout=1.0)
                        if enchant_process.is_alive():
                            enchant_process.join()
                        window['OUTPUT'].print("Process terminated by user (P key pressed)")
                        enchant_process = None
                    time.sleep(0.1)
        except Exception as e:
            logging.error(f"Error in keyboard handling: {e}")
            window['OUTPUT'].print(f"Error in keyboard handling: {e}")

    if enchant_process and enchant_process.is_alive():
        enchant_process.stop()
        enchant_process.join(timeout=1.0)

    window.close()

if __name__ == "__main__":
    main()