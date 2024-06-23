# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['app.py'],
    pathex=['.'],
    binaries=[
        ('assets/ForceBindIP.exe', '.'), 
        ('assets/BindIP.dll', '.'), 
        ('assets/BindIP64.dll', '.'), 
        ('assets/ForceBindIP64.exe', '.'),
        ('assets/help_icon.png', '.'),
        ('assets/github_logo.png', '.')
    ],
    datas=[],
    hiddenimports=[],
    hookspath=['.'],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='ForceBindIP-GUI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['assets/FBI.ico'],
)
