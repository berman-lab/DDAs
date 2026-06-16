# -*- mode: python ; coding: utf-8 -*-

# Some notes on getting a smaller bundle:
# 1) On macOS UPX is turned off by default by PyInstaller, due to signing and other issues, so probably not worth trying.
# 2) Installing a fresh environment (using menv - not anaconda!) for the packaging works well. Don't forget openpyxl for reading Excel files (it's not in the imports).

import sys
import os
import re

is_mac = sys.platform == 'darwin'

# 1. Extract version from dda_panel_creator.py
version = "unknown"
try:
    with open('dda_panel_creator.py', 'r', encoding='utf-8') as f:
        match = re.search(r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]', f.read(), re.MULTILINE)
        if match:
            version = match.group(1)
except Exception:
    pass

# 2. Fallback / Override with GitHub Actions tag if available (and it's a version tag like 'v1.0.0')
github_ref = os.environ.get('GITHUB_REF_NAME')
if github_ref and github_ref.startswith('v'):
    version = github_ref.lstrip('v')

app_name = f'DDAPanelCreator-v{version}'

a = Analysis(
    ['dda_panel_creator.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=['matplotlib', 'matplotlib.pyplot'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[ 
        'scipy',  # The big four bloaters # We do need numpy and pandas
        'PyQt5', 'PyQt6', 'PySide2', 'PySide6',    # GUI bloat
        'tkinter', 'test',    # Standard library bloat # fails without 'email' for some reason, and unittest is required for matplotlib
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
    name=app_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=not is_mac,
    upx_exclude=[],
    runtime_tmpdir=None,
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
    upx=not is_mac,
    upx_exclude=[],
    name=app_name,
)

if is_mac:
    app = BUNDLE(
        coll,
        name=f'{app_name}.app',
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
# AUTOMATED POST-BUILD WORKFLOW (Pure ASCII - Cross-Platform)
# =============================================================================
import os

print("\n" + "="*60)
print("--- [Post-Build] Dynamically Patching OpenCV Portability ---")
print("="*60)

# 1. Dynamically walk the 'dist' directory to find where 'cv2' ended up
cv2_targets = []
for root, dirs, files in os.walk('dist'):
    if 'cv2' in dirs:
        cv2_targets.append(os.path.join(root, 'cv2'))

if cv2_targets:
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

    for target_dir in cv2_targets:
        print(f"Found OpenCV directory at: {target_dir}")
        
        # Grab any file starting with 'config' (e.g., config.py, config-3.11.py)
        config_files = [f for f in os.listdir(target_dir) if f.startswith('config') and f.endswith('.py')]
        
        if config_files:
            for file_name in config_files:
                file_path = os.path.join(target_dir, file_name)
                print(f"[Scrubbing] Removing local paths from: {file_name}")
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(portable_config_content)
            print("SUCCESS: OpenCV config files patched successfully!")
        else:
            print("[Info] No absolute path config files found in this cv2 instance (likely a native portable Pip wheel).")
else:
    print("WARNING: Could not locate any 'cv2' directory inside 'dist/'.")
print("="*60 + "\n")