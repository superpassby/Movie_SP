import os
import sys
import requests
import shutil
import time
import yaml
from pathlib import Path
import sqlite3

# ------------------ 动态添加项目根目录 ------------------
CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = next(p for p in CURRENT_FILE.parents if (p / "cfg").exists())

# 将项目根目录加入 sys.path，这样可以直接 import 根目录下的模块
sys.path.insert(0, str(PROJECT_ROOT))



CONFIG_FILE = os.path.join(PROJECT_ROOT, "cfg", "config.yaml")
db_path = PROJECT_ROOT / 'db' / 'data.db'
from tools.Data_Base_Edit.db_edit import db_edit

# 读取 Jellyfin 配置
with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

JELLYFIN_URL = config.get("Jellyfin")
API_KEY = config.get("Jellyfin_API")
SAVE_SUB = config.get("SavePath_Sub")
# DRIVE_PATH = config.get("DRIVE_Path")

SAVE_PATH_REAL = SAVE_SUB

MRGX = "每日更新"
JXSC = "精选收藏"
HJ = "合集"
MRGX_TMP = os.path.join(SAVE_PATH_REAL, "每日更新_待删除")
JXSC_PATH = os.path.join(SAVE_PATH_REAL, "精选收藏")

# 获取媒体库 ID
def get_library_id(name):
    response = requests.get(f"{JELLYFIN_URL}/Library/VirtualFolders", headers={
        "X-Emby-Token": API_KEY
    })
    libraries = response.json()
    for library in libraries:
        if library["Name"] == name:
            return library["ItemId"]
    return None

MRGX_ID = get_library_id(MRGX)
JXSC_ID = get_library_id(JXSC)
HJ_ID = get_library_id(HJ)


print(f"JELLYFIN_URL: {JELLYFIN_URL}")
print(f"API_KEY: {API_KEY}")
print(f"SAVE_PATH_REAL: {SAVE_PATH_REAL}")

print(f"库 {MRGX} 的 ID: {MRGX_ID}")
print(f"库 {JXSC} 的 ID: {JXSC_ID}")
print(f"库 {HJ} 的 ID: {HJ_ID}")

# 获取用户 ID
response = requests.get(f"{JELLYFIN_URL}/Users", headers={
    "X-Emby-Token": API_KEY
})
USER_ID = response.json()[0]["Id"]
print(f"用户 ID: {USER_ID}")



import requests

def create_test_library():
    """
    创建一个 Jellyfin 媒体库 'test'，使用默认参数
    """
    url = f"{JELLYFIN_URL}/Library/VirtualFolders"
    headers = {
        "X-Emby-Token": API_KEY,
        "Content-Type": "application/json"
    }

    payload = {
        "name": "test",                 # ✅ 必须小写
        "collectionType": "movies",     # 默认电影库
        "paths": [
            str(PROJECT_ROOT / "test_media")  # 默认路径
        ]
    }

    resp = requests.post(url, headers=headers, json=payload)
    if resp.status_code == 200:
        print("✅ 成功创建媒体库 'test'")
    else:
        print(f"❌ 创建失败: {resp.status_code} - {resp.text}")

create_test_library()

