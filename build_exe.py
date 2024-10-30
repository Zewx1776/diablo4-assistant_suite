import PyInstaller.__main__
import os
import shutil
import sys
from pathlib import Path

def check_tesseract():
    tesseract_path = r'C:\Program Files\Tesseract-OCR'
    if not os.path.exists(tesseract_path):
        print("""
ERROR: Tesseract-OCR not found!
Please install Tesseract-OCR first:
1. Download from: https://github.com/UB-Mannheim/tesseract/releases/download/v5.3.1.20230401/tesseract-ocr-w64-setup-5.3.1.20230401.exe
2. Install to the default location (C:\\Program Files\\Tesseract-OCR)
3. Run this script again
""")
        sys.exit(1)
    return tesseract_path

# Check for Tesseract installation
tesseract_path = check_tesseract()

# Clean previous builds
if os.path.exists('dist'):
    shutil.rmtree('dist')
if os.path.exists('build'):
    shutil.rmtree('build')

# Create data list including Tesseract
datas = [
    ('shared_config.py', '.'),
    ('masterwork.py', '.'),
    ('kurast.py', '.'),
    ('barter.py', '.'),
    ('enchant.py', '.'),
    ('theme_config.json', '.'),
    ('images/*', 'images/'),
    (tesseract_path, 'Tesseract-OCR'),
]

# Create hidden imports list
hidden_imports = [
    'pytesseract',
    'cv2',
    'PIL',
    'PIL._tkinter',
    'win32gui',
    'win32api',
    'win32con',
    'keyboard',
    'numpy',
    'pyautogui',
    'mouseinfo',
    'pygetwindow',
    'pyrect',
    'pyscreeze',
    'pytweening',
]

# Get the site-packages directory
import site
site_packages = site.getsitepackages()[0]

# Find OpenCV DLLs
opencv_dir = Path(site_packages) / "cv2"
if opencv_dir.exists():
    binaries = [(str(dll), '.') for dll in opencv_dir.glob('*.dll')]
else:
    print("Warning: OpenCV directory not found")
    binaries = []

# Run PyInstaller
PyInstaller.__main__.run([
    'launcher.py',
    '--name=D4Assistant',
    '--onefile',
    '--noconsole',
    *[f'--add-data={src};{dst}' for src, dst in datas],
    *[f'--hidden-import={imp}' for imp in hidden_imports],
    *[f'--add-binary={src};{dst}' for src, dst in binaries],  # Add OpenCV DLLs
    '--collect-submodules=cv2',
])