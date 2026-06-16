# -*- mode: python ; coding: utf-8 -*-

# Some notes on getting a smaller bundle:
# 1) On macOS UPX is turned off by default by PyInstaller, due to signing and other issues, so probably not worth trying.
# 2) Installing a fresh environment (using menv - not anaconda!) for the packaging works well. Don't forget openpyxl for reading Excel files (it's not in the imports).

a = Analysis(
    ['dda_panel_creator.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[ 
        'matplotlib', 'scipy',  # The big four bloaters # We do need numpy and pandas
        'PyQt5', 'PyQt6', 'PySide2', 'PySide6',    # GUI bloat
        'tkinter', 'test', 'unittest',    # Standard library bloat # fails without 'email' for some reason
        'notebook', 'IPython',                     # Jupyter bloat
        # More PyQT and other exclusions:
        'qt6', 'qt', 'Qt6', 'Qt', # Binary name variations
        'PyQt6.QtCore', 'PyQt6.QtGui', 'PyQt6.QtWidgets',
        'tcl', 'tk'
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='DDAPanelCreator',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='DDAPanelCreator',
)
app = BUNDLE(
    coll,
    name='DDAPanelCreator.app',
    icon=None,
    bundle_identifier=None,
    # This fixes a weird bug on macOS where the text would be white on light backgrounds or black on dark backgrounds.
    # This seems to force a theme, fixing this issue.
    info_plist={
        'NSRequiresAquaSystemAppearance': 'True', # Forces Light Mode
        'NSAppearance': 'Aqua',                   # Forces the Aqua (Light) theme
    },
)

# =============================================================================
# AUTOMATED POST-BUILD WORKFLOW (Runs on both Mac and Windows)
# =============================================================================
import os

print("\n" + "="*60)
print("--- [Post-Build] Automatically Patching OpenCV Portability ---")
print("="*60)

# 1. Define where OpenCV could hide based on the OS structure
cv2_search_paths = [
    os.path.join('dist', 'DDAPanelCreator.app', 'Contents', 'Frameworks', 'cv2'), # macOS Bundle
    os.path.join('dist', 'DDAPanelCreator', 'cv2'),                                # Windows / Linux / macOS CLI
]

cv2_target_dir = None
for path in cv2_search_paths:
    if os.path.exists(path):
        cv2_target_dir = path
        break

# 2. If we find it, neutralize the absolute paths inside the config files
if cv2_target_dir:
    print(f"Target located at: {cv2_target_dir}")
    
    # Grab any file starting with 'config' (e.g., config.py, config-3.11.py)
    config_files = [f for f in os.listdir(cv2_target_dir) if f.startswith('config') and f.endswith('.py')]
    
    # This replacement script forces OpenCV to strictly use relative anchor paths
    portable_config_content = """import os
import sys

# Dynamically locate the path relative to the active runtime bundle
_cv2_dir = os.path.dirname(os.path.abspath(__file__))

if 'BINARIES_PATHS' not in locals():
    BINARIES_PATHS = []
if 'PYTHON_EXTENSIONS_PATHS' not in locals():
    PYTHON_EXTENSIONS_PATHS = []

BINARIES_PATHS = [ _cv2_dir ] + BINARIES_PATHS
PYTHON_EXTENSIONS_PATHS = [ os.path.join(_cv2_dir, 'python-3.11') ] + PYTHON_EXTENSIONS_PATHS
"""

    for file_name in config_files:
        file_path = os.path.join(cv2_target_dir, file_name)
        print(f"🧹 Scrubbing local developer environment paths out of: {file_name}")
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(portable_config_content)
            
    print("✅ SUCCESS: OpenCV has been successfully immunized for distribution!")
else:
    print("⚠️ Warning: Could not locate the bundled 'cv2' directory inside 'dist/'.")
    print("If you haven't compiled yet, this is normal. Otherwise, double-check your app name.")
print("="*60 + "\n")