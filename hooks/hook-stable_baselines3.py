# hook-stable_baselines3.py
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

hiddenimports = collect_submodules('stable_baselines3')
datas = collect_data_files('stable_baselines3')  # includes version.txt and others
