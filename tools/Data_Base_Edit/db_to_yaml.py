#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import yaml
import sys
from pathlib import Path

# ------------------ 项目根目录 ------------------
CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = next(p for p in CURRENT_FILE.parents if (p / "cfg").exists())

# ------------------ 锁文件 ------------------
LOCK_FILE = PROJECT_ROOT / 'work'
# USE_LOCK = True  # <- 这里设置是否启用锁文件
USE_LOCK = False
def create_lock_file():
    if USE_LOCK and LOCK_FILE.exists():
        print("存在锁文件，请检查。")
        sys.exit(0)
    if USE_LOCK:
        LOCK_FILE.touch()
        print("锁文件 'work' 已创建。")

def delete_lock_file():
    if USE_LOCK and LOCK_FILE.exists():
        LOCK_FILE.unlink()
        print("锁文件 'work' 已删除。")

# ------------------ 导出 YAML ------------------
def db_to_yaml(db_file, yaml_file):
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT name, individual_movie, only_scan_first_page, enable_scan, max_actress_count, enable_download, filter
        FROM actresses
        ORDER BY name
    ''')
    rows = cursor.fetchall()
    conn.close()

    yaml_list = []
    for row in rows:
        # 转成普通 dict 保证 safe_dump 可以序列化
        yaml_list.append(dict([
            ('Name', row[0]),
            ('Individual_Movie', row[1]),
            ('Only_Scan_First_Page', row[2]),
            ('Enable_Scan', row[3]),
            ('Max_Actress_Count', row[4]),
            ('Enable_Download', row[5]),
            ('Filter', row[6]),
        ]))

    # 写 YAML，每个演员之间空一行
    with yaml_file.open('w', encoding='utf-8') as f:
        for item in yaml_list:
            yaml.safe_dump([item], f, allow_unicode=True, sort_keys=False)
            f.write("\n")  # 空一行

    print(f"成功生成 YAML 文件: {yaml_file}")

# ------------------ main ------------------
def main():
    create_lock_file()
    try:
        db_file = PROJECT_ROOT / 'db' / 'data.db'
        yaml_file = PROJECT_ROOT / 'cfg' / 'source.yaml'

        db_to_yaml(db_file, yaml_file)

    finally:
        delete_lock_file()

if __name__ == "__main__":
    main()
