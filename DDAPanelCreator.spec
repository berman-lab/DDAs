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
