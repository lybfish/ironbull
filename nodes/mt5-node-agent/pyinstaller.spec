# -*- mode: python ; coding: utf-8 -*-

"""
PyInstaller 打包配置
用于将 mt5-node-agent 打包为 Windows 可执行文件

打包命令:
    pyinstaller pyinstaller.spec

输出:
    dist/mt5-node-agent/
        ├── mt5-node-agent.exe
        └── config.yaml.sample
"""

import os

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[os.path.dirname(os.path.abspath(__file__))],
    binaries=[],
    datas=[
        # 配置文件
        ('config.yaml.sample', '.'),
    ],
    hiddenimports=[
        # WebSocket
        'websockets',
        # YAML
        'yaml',
        'yaml.cyaml',
        # Pydantic
        'pydantic',
        'pydantic.fields',
        'pydantic.dataclasses',
        # HTTP
        'httpx',
        'httpcore',
        'anyio',
        # MT5 SDK (如果安装了)
        'MetaTrader5',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'test',
        'unittest',
        'pydoc',
        'doctest',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='mt5-node-agent',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    console=False,  # False = 无控制台窗口 (后台运行)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # 如果有图标，添加: icon='resources/icon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='mt5-node-agent',
)
