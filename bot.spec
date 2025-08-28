# bot.spec
# PyInstaller robust spec for RL bot

from PyInstaller.utils.hooks import collect_data_files, collect_submodules
from PyInstaller.building.build_main import Analysis, PYZ, EXE, COLLECT
import os

block_cipher = None

# --- 데이터/서브모듈 수집 (핵심) ---
sb3_datas = collect_data_files('stable_baselines3', include_py_files=False)
gym_datas = collect_data_files('gymnasium', include_py_files=False)

hidden = [
    'train',
    'trade_hourly',
]

hidden += collect_submodules('stable_baselines3')  # 예방적
# gymnasium은 보통 필요 없지만 환경에 따라 추가 가능
# hidden += collect_submodules('gymnasium')

a = Analysis(
    ['bot.py'],
    pathex=[os.getcwd()],
    binaries=[],
    datas=sb3_datas + gym_datas,
    hiddenimports=hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='bot',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,   # 콘솔 숨기려면 False 로 바꿔
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None
)
