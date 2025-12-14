import json
import os

CONFIG_FILE = "config.json"
DEFAULT_CONFIG = {"GOOGLE_API_KEY": "", "NAVER_ACCOUNTS": {}}

def load_config():
    if not os.path.exists(CONFIG_FILE): return DEFAULT_CONFIG
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f: return json.load(f)
    except: return DEFAULT_CONFIG

def save_config(data):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        return True
    except: return False