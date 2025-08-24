import os
from stable_baselines3 import PPO

def save_model(model, path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    model.save(path)

def load_model(path: str):
    if not os.path.exists(path):
        return None
    return PPO.load(path, device="cpu")
