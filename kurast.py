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

CONFIG_FILE = 'kurast_config.json'

logging.basicConfig(filename='enchant_assistant.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

@dataclass
class KurastConfig:
    scan_region: Tuple[int, int, int, int]  # Portal scan region
    target_image: str = None  # Path to portal target image
    tribute_spot: Tuple[int, int] = (0, 0)  # Coordinates for tribute right-click
    portal_button: Tuple[int, int] = (0, 0)  # Coordinates for portal button click
    click_delay: float = 0.1
    loop_delay: float = 0.5
    confidence: float = 0.8

    def __post_init__(self):
        if self.target_image is None:
            self.target_image = ""

def find_image_in_region(template_path: str, region: Tuple[int, int, int, int], confidence: float = 0.8) -> Optional[Tuple[int, int]]:
    try:
        # Capture the screen region
        screenshot = np.array(pyautogui.screenshot(region=region))
        screenshot_bgr = cv2.cvtColor(screenshot, cv2.COLOR_RGB2BGR)
        
        # Read the template image
        template = cv2.imread(template_path)
        if template is None:
            logging.error(f"Could not load template image: {template_path}")
            return None
            
        # Get template dimensions
        h, w = template.shape[:2]
        
        # Perform template matching
        result = cv2.matchTemplate(screenshot_bgr, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        
        if max_val >= confidence:
            # Return the center point of the match, relative to screen
            match_x = region[0] + max_loc[0] + w//2
            match_y = region[1] + max_loc[1] + h//2
            return (match_x, match_y)
        
        return None
    except Exception as e:
        logging.error(f"Error in image matching: {e}")
        return None

def highlight_click(x: int, y: int, duration: float = 0.5):
    try:
        # Create a small overlay window
        root = tk.Tk()
        root.overrideredirect(True)  # Remove window border
        root.attributes('-topmost', True)  # Keep on top
        root.attributes('-alpha', 0.7)  # Semi-transparent
        
        # Create a small red circle
        size = 20
        canvas = tk.Canvas(root, width=size, height=size, 
                         bg='red', highlightthickness=0)
        canvas.create_oval(2, 2, size-2, size-2, fill='red')
        canvas.pack()
        
        # Position the window centered on click coordinates
        root.geometry(f'{size}x{size}+{x-size//2}+{y-size//2}')
        
        # Schedule the window to close
        root.after(int(duration * 1000), root.destroy)
        root.mainloop()
    except Exception as e:
        logging.error(f"Error highlighting click: {e}")

class KurastProcess(threading.Thread):
    def __init__(self, config: KurastConfig, window: sg.Window):
        super().__init__()
        self.config = config
        self.window = window
        self.stop_event = threading.Event()
        self.keyboard_lock = Lock()

    def run(self) -> None:
        while not self.stop_event.is_set():
            try:
                # Look for the portal target image
                match_pos = find_image_in_region(
                    self.config.target_image,
                    self.config.scan_region,
                    self.config.confidence
                )
                
                if match_pos:
                    # Show where it's going to click
                    highlight_click(*match_pos)
                    # Move mouse and click portal target
                    pyautogui.moveTo(match_pos[0], match_pos[1], duration=0.2)
                    time.sleep(0.1)
                    pyautogui.click()
                    time.sleep(self.config.click_delay)
                    
                    # Right click tribute spot
                    if self.config.tribute_spot != (0, 0):
                        self.window.write_event_value('-UPDATE-', f"Moving to tribute spot {self.config.tribute_spot}")
                        pyautogui.moveTo(self.config.tribute_spot[0], self.config.tribute_spot[1], duration=0.2)
                        time.sleep(0.1)
                        pyautogui.click(button='right')
                        time.sleep(self.config.click_delay)
                    
                    # Click portal button
                    if self.config.portal_button != (0, 0):
                        pyautogui.moveTo(self.config.portal_button[0], self.config.portal_button[1], duration=0.2)
                        time.sleep(0.1)
                        pyautogui.click()
                        time.sleep(self.config.click_delay)
                    
                    self.window.write_event_value('-UPDATE-', 
                        f"Completed portal sequence")
                    self.stop()
                    return
                else:
                    self.window.write_event_value('-UPDATE-', "Portal target not found")
                
                time.sleep(self.config.loop_delay)
            except Exception as e:
                logging.error(f"Error in Kurast process: {e}")
                self.window.write_event_value('-UPDATE-', f"Error occurred: {e}")
                time.sleep(1)

    def stop(self) -> None:
        with self.keyboard_lock:
            self.stop_event.set()

def create_main_window(config: KurastConfig) -> sg.Window:
    layout = [
        [sg.Text("Kurast Configuration")],
        [sg.Text("Portal Scan Region:"), 
         sg.Input(key='SCAN_REGION', 
                 default_text=','.join(map(str, config.scan_region)), 
                 size=(20, 1)),
         sg.Button("Get", key='GET_SCAN_REGION')],
        [sg.Text("Portal Target Image:"), 
         sg.Input(key='TARGET_IMAGE', default_text=config.target_image, size=(40, 1)),
         sg.FileBrowse(file_types=(("PNG Files", "*.png"), ("All Files", "*.*"))),
         sg.Button("Capture", key='CAPTURE_TARGET')],
        [sg.Text("Tribute Spot:"),
         sg.Input(key='TRIBUTE_SPOT', 
                 default_text=','.join(map(str, config.tribute_spot)),
                 size=(20, 1)),
         sg.Button("Get", key='GET_TRIBUTE_SPOT')],
        [sg.Text("Portal Button:"),
         sg.Input(key='PORTAL_BUTTON',
                 default_text=','.join(map(str, config.portal_button)),
                 size=(20, 1)),
         sg.Button("Get", key='GET_PORTAL_BUTTON')],
        [sg.Text("Match Confidence:"),
         sg.Input(key='CONFIDENCE', default_text=str(config.confidence), size=(5, 1))],
        [sg.Text("Click Delay:"),
         sg.Input(key='CLICK_DELAY', default_text=str(config.click_delay), size=(5, 1))],
        [sg.Text("Loop Delay:"),
         sg.Input(key='LOOP_DELAY', default_text=str(config.loop_delay), size=(5, 1))],
        [sg.Button("Save Configuration"), sg.Button("Start Process"), 
         sg.Button("Stop Process"), sg.Button("Exit")],
        [sg.Multiline(size=(60, 10), key='OUTPUT', disabled=True)]
    ]
    
    return sg.Window("Kurast Helper", layout, finalize=True)

def validate_config(config: KurastConfig) -> bool:
    if config.scan_region == (0, 0, 0, 0):
        return False
    if config.target_image == "":
        return False
    return True

def save_config(config: KurastConfig) -> None:
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(asdict(config), f)
        logging.info("Configuration saved successfully.")
    except Exception as e:
        logging.error(f"Error saving configuration: {e}")

def load_config() -> KurastConfig:
    default_config = KurastConfig((0, 0, 0, 0))
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                config_dict = json.load(f)
                return KurastConfig(**config_dict)
    except Exception as e:
        logging.error(f"Error loading configuration: {e}")
    return default_config

def click_button(x: int, y: int, delay: float = 0.1) -> None:
    try:
        # Move mouse smoothly to position
        pyautogui.moveTo(x, y, duration=0.2)  # 0.2 seconds for smooth movement
        time.sleep(0.1)  # Small pause after movement
        pyautogui.click()
        time.sleep(delay)
    except Exception as e:
        logging.error(f"Error clicking button at ({x}, {y}): {e}")

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
    drawing = False  # Add flag to track drawing state

    def on_mouse_down(event):
        nonlocal start_x, start_y, rect, drawing
        start_x, start_y = event.x, event.y
        drawing = True
        if rect:
            canvas.delete(rect)
        rect = canvas.create_rectangle(start_x, start_y, start_x, start_y, outline='red', width=2)

    def on_mouse_move(event):
        nonlocal rect, drawing
        if drawing:  # Only update rectangle if we're drawing
            if rect:
                canvas.delete(rect)
            rect = canvas.create_rectangle(start_x, start_y, event.x, event.y, outline='red', width=2)

    def on_mouse_up(event):
        nonlocal region, drawing
        drawing = False
        end_x, end_y = event.x, event.y
        x = min(start_x, end_x)
        y = min(start_y, end_y)
        width = abs(end_x - start_x)
        height = abs(end_y - start_y)
        
        if width > 5 and height > 5:  # Only set region if the selection is larger than 5x5 pixels
            region = (x, y, width, height)
            root.after(100, root.quit)  # Delay quit slightly to show final rectangle

    def on_key(event):
        if event.keysym == 'Escape':
            root.quit()

    # Bind mouse events
    canvas.bind("<Button-1>", on_mouse_down)
    canvas.bind("<B1-Motion>", on_mouse_move)
    canvas.bind("<ButtonRelease-1>", on_mouse_up)
    root.bind("<Key>", on_key)

    # Make sure the window is on top
    root.lift()
    root.attributes('-topmost', True)

    root.mainloop()
    root.destroy()

    return region

def capture_target_image(window: sg.Window) -> Optional[str]:
    try:
        root = tk.Tk()
        root.attributes('-alpha', 0.3)
        root.attributes('-fullscreen', True)
        root.configure(background='grey')

        canvas = tk.Canvas(root, cursor="cross")
        canvas.pack(fill=tk.BOTH, expand=True)

        rect = None
        start_x = start_y = 0
        region = None
        drawing = False

        def on_mouse_down(event):
            nonlocal start_x, start_y, rect, drawing
            start_x, start_y = event.x, event.y
            drawing = True
            if rect:
                canvas.delete(rect)
            rect = canvas.create_rectangle(start_x, start_y, start_x, start_y, outline='red', width=2)

        def on_mouse_move(event):
            nonlocal rect, drawing
            if drawing:
                if rect:
                    canvas.delete(rect)
                rect = canvas.create_rectangle(start_x, start_y, event.x, event.y, outline='red', width=2)

        def on_mouse_up(event):
            nonlocal region, drawing
            drawing = False
            end_x, end_y = event.x, event.y
            x = min(start_x, end_x)
            y = min(start_y, end_y)
            width = abs(end_x - start_x)
            height = abs(end_y - start_y)
            
            if width > 5 and height > 5:
                region = (x, y, width, height)
                root.after(100, root.quit)

        def on_key(event):
            if event.keysym == 'Escape':
                root.quit()

        canvas.bind("<Button-1>", on_mouse_down)
        canvas.bind("<B1-Motion>", on_mouse_move)
        canvas.bind("<ButtonRelease-1>", on_mouse_up)
        root.bind("<Key>", on_key)

        root.lift()
        root.attributes('-topmost', True)

        window.hide()  # Hide main window while selecting
        root.mainloop()
        root.destroy()
        window.un_hide()

        if region:
            # Create images directory if it doesn't exist
            if not os.path.exists('images'):
                os.makedirs('images')

            # Generate filename with timestamp
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            filename = f'images/target_{timestamp}.png'

            # Capture and save the screenshot
            screenshot = pyautogui.screenshot(region=region)
            screenshot.save(filename)
            return filename

        return None

    except Exception as e:
        logging.error(f"Error capturing target image: {e}")
        return None

def main():
    apply_theme()
    config = load_config()
    window = create_main_window(config)
    kurast_process = None
    keyboard_lock = Lock()

    while True:
        event, values = window.read(timeout=100)
        if event == sg.WINDOW_CLOSED or event == "Exit":
            break
        elif event.startswith('GET_'):
            key = event.replace('GET_', '')
            if key == "SCAN_REGION":
                window.hide()
                region = get_scan_region()
                window.un_hide()
                if region:
                    window['SCAN_REGION'].update(','.join(map(str, region)))
            elif key in ["TRIBUTE_SPOT", "PORTAL_BUTTON"]:
                window.hide()
                time.sleep(2)  # Give user time to position mouse
                pos = pyautogui.position()
                window.un_hide()
                window[key].update(f"{pos[0]},{pos[1]}")
            elif event == "CAPTURE_TARGET":
                filename = capture_target_image(window)
                if filename:
                    window['TARGET_IMAGE'].update(filename)
                    window['OUTPUT'].print(f"Captured target image: {filename}")
            else:
                position = get_mouse_position(window, key)
                window[key].update(f"{position[0]},{position[1]}")
        elif event == "CAPTURE_TARGET":
            filename = capture_target_image(window)
            if filename:
                window['TARGET_IMAGE'].update(filename)
                window['OUTPUT'].print(f"Captured target image: {filename}")
        elif event == "Save Configuration":
            try:
                scan_region = tuple(map(int, values['SCAN_REGION'].split(',')))
                target_image = values['TARGET_IMAGE']
                tribute_spot = tuple(map(int, values['TRIBUTE_SPOT'].split(',')))
                portal_button = tuple(map(int, values['PORTAL_BUTTON'].split(',')))
                click_delay = float(values['CLICK_DELAY'])
                loop_delay = float(values['LOOP_DELAY'])
                confidence = float(values['CONFIDENCE'])

                new_config = KurastConfig(
                    scan_region=scan_region,
                    target_image=target_image,
                    tribute_spot=tribute_spot,
                    portal_button=portal_button,
                    click_delay=click_delay,
                    loop_delay=loop_delay,
                    confidence=confidence
                )
                if validate_config(new_config):
                    save_config(new_config)
                    config = new_config
                    window['OUTPUT'].print(f"Configuration saved successfully. Tribute spot: {tribute_spot}")
                else:
                    window['OUTPUT'].print("Invalid configuration. Please check all fields.")
            except ValueError as e:
                window['OUTPUT'].print(f"Invalid input. Please check all fields. Error: {e}")
        elif event == "Start Process":
            if kurast_process is None or not kurast_process.is_alive():
                if validate_config(config):
                    kurast_process = KurastProcess(config, window)
                    kurast_process.start()
                else:
                    window['OUTPUT'].print("Invalid configuration. Please check all fields.")
        elif event == "Stop Process":
            if kurast_process and kurast_process.is_alive():
                kurast_process.stop()
                kurast_process.join()
                window['OUTPUT'].print("Process stopped.")
        elif event == '-UPDATE-':
            window['OUTPUT'].print(values['-UPDATE-'])
        
        try:
            with keyboard_lock:
                if keyboard.is_pressed('p'):
                    if kurast_process and kurast_process.is_alive():
                        kurast_process.stop()
                        kurast_process.join(timeout=1.0)
                        if kurast_process.is_alive():
                            kurast_process.join()
                        window['OUTPUT'].print("Process terminated by user (P key pressed)")
                        kurast_process = None
                    time.sleep(0.1)
        except Exception as e:
            logging.error(f"Error in keyboard handling: {e}")
            window['OUTPUT'].print(f"Error in keyboard handling: {e}")

    if kurast_process and kurast_process.is_alive():
        kurast_process.stop()
        kurast_process.join(timeout=1.0)

    window.close()

if __name__ == "__main__":
    main()