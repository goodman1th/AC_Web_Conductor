import json
import os

CONFIG_FILE = "config.json"

DEFAULT_CONFIG = {
    "GOOGLE_API_KEY": "",
    "NAVER_ACCOUNTS": {}
}

def load_config():
    """설정 파일(JSON)을 읽어옵니다. 없으면 기본값을 반환합니다."""
    if not os.path.exists(CONFIG_FILE):
        return DEFAULT_CONFIG
    
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"설정 로드 실패: {e}")
        return DEFAULT_CONFIG

def save_config(config_data):
    """설정 데이터를 JSON 파일로 영구 저장합니다."""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config_data, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        print(f"설정 저장 실패: {e}")
        return False