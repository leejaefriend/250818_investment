# hooks/hook-stable_baselines3.py
from PyInstaller.utils.hooks import collect_data_files
datas = collect_data_files('stable_baselines3')  # version.txt 등 포함
