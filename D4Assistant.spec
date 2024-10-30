# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules

hiddenimports = ['pytesseract', 'cv2', 'PIL', 'PIL._tkinter', 'win32gui', 'win32api', 'win32con', 'keyboard', 'numpy', 'pyautogui', 'mouseinfo', 'pygetwindow', 'pyrect', 'pyscreeze', 'pytweening']
hiddenimports += collect_submodules('cv2')


a = Analysis(
    ['launcher.py'],
    pathex=[],
    binaries=[],
    datas=[('shared_config.py', '.'), ('masterwork.py', '.'), ('kurast.py', '.'), ('barter.py', '.'), ('enchant.py', '.'), ('theme_config.json', '.'), ('images/*', 'images/'), ('C:\\Program Files\\Tesseract-OCR', 'Tesseract-OCR')],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='D4Assistant',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
