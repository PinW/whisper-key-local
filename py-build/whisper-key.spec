# whisper-key.spec
# -*- mode: python ; coding: utf-8 -*-

import os
import sys
import pathlib
import site

# Project paths
project_root = pathlib.Path.cwd()
src_path = project_root / "src"
spec_dir = pathlib.Path(SPECPATH)

# Build variant: "cuda" (default) or "rocm"
build_variant = os.environ.get("WHISPER_KEY_VARIANT", "cuda")

# Dynamic ten_vad library path detection
ten_vad_data = []
for site_dir in site.getsitepackages():
    ten_vad_lib = pathlib.Path(site_dir) / 'ten_vad' / 'lib'
    if ten_vad_lib.exists():
        ten_vad_data.append((str(ten_vad_lib), 'ten_vad/lib'))
        break

a = Analysis(
    [str(project_root / 'whisper-key.py')],
    pathex=[str(project_root)],
    binaries=[],
    datas=[
        (str(project_root / 'src' / 'whisper_key' / 'config.defaults.yaml'), '.'),
        (str(project_root / 'src' / 'whisper_key' / 'assets'), 'assets'),
        (str(project_root / 'src' / 'whisper_key' / 'platform' / 'windows' / 'assets'), 'platform/windows/assets'),
    ] + ten_vad_data,
    hiddenimports=[
        'win32gui', 'win32con', 'win32clipboard', 'win32api',
        'global_hotkeys',
        'pystray._win32', 'PIL._tkinter_finder',
        'sounddevice', 'numpy.core._methods',
        'faster_whisper', 'ctranslate2',
        'ten_vad',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[str(spec_dir / 'hooks' / 'rth_rocm_paths.py')] if build_variant == 'rocm' else [],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

# Exclude bundled MSVC runtime - use system version instead
# ctranslate2 4.6.3+ compiled with VS 2022 requires newer MSVCP140.dll than PyInstaller bundles
a.binaries = [b for b in a.binaries if b[0].lower() != 'msvcp140.dll']

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