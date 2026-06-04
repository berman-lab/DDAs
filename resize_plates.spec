# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['resize_plates.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
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
    [],
    exclude_binaries=True,
    name='PlateCropper',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
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
    upx=False,
    upx_exclude=[],
    name='resize_plates',
)

app = BUNDLE(
    coll,
    name=f'PlateCropper.app',
    icon=None,
    bundle_identifier=None,
    # This fixes a weird bug on macOS where the text would be white on light backgrounds or black on dark backgrounds.
    # This seems to force a theme, fixing this issue.
    info_plist={
        'NSRequiresAquaSystemAppearance': 'True', # Forces Light Mode
        'NSAppearance': 'Aqua',                   # Forces the Aqua (Light) theme
    },
)