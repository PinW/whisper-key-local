# whisper-key.spec
# -*- mode: python ; coding: utf-8 -*-

import sys
import pathlib
import site

# Project paths
project_root = pathlib.Path.cwd()
src_path = project_root / "src"

# Dynamic ten_vad library path detection
ten_vad_data = []
for site_dir in site.getsitepackages():
    ten_vad_candidate = pathlib.Path(site_dir) / 'ten_vad_library'
    if ten_vad_candidate.exists():
        ten_vad_data.append((str(ten_vad_candidate), 'ten_vad_library'))
        break

a = Analysis(
    [str(project_root / 'whisper-key.py')],
    pathex=[str(project_root)],
    binaries=[],
    datas=[
        (str(project_root / 'src' / 'whisper_key' / 'config.defaults.yaml'), '.'),
        (str(project_root / 'src' / 'whisper_key' / 'assets'), 'assets'),
    ] + ten_vad_data,
    hiddenimports=[
        'win32gui', 'win32con', 'win32clipboard', 'win32api',
        'global_hotkeys',
        'pystray._win32', 'PIL._tkinter_finder',
        'sounddevice', 'numpy.core._methods',
        'faster_whisper', 'ctranslate2',
        'ten_vad',
        'scipy.signal',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='whisper-key',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,  # Keep console for alpha testing
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='whisper-key',
)