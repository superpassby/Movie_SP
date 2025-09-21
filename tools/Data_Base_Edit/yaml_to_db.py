#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
from pathlib import Path
import yaml
# ------------------ 动态添加项目根目录 ------------------
CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = next(p for p in CURRENT_FILE.parents if (p / "cfg").exists())

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# 现在再导入 db_edit
from tools.Data_Base_Edit.db_edit import db_edit


# ------------------ 锁文件 ------------------
LOCK_FILE = PROJECT_ROOT / 'work'

def create_lock_file():
    if LOCK_FILE.exists():
        print("存在锁文件，请检查。")
        sys.exit(0)
    LOCK_FILE.touch()
    print("锁文件 'work' 已创建。")

def delete_lock_file():
    if LOCK_FILE.exists():
        LOCK_FILE.unlink()
        print("锁文件 'work' 已删除。")

# ------------------ 创建数据库目录和文件 ------------------
def create_db_file():
    db_dir = PROJECT_ROOT / 'db'
    db_file = db_dir / 'data.db'

    db_dir.mkdir(exist_ok=True)
    if not db_file.exists():
        print(f"数据库文件 {db_file} 不存在，正在创建...")
    else:
        print(f"数据库文件 {db_file} 已存在。")

    return db_file

# ------------------ 创建数据库表 ------------------
def create_tables():
    sql = '''
    CREATE TABLE IF NOT EXISTS actresses (
        name TEXT PRIMARY KEY,
        individual_movie TEXT,
        only_scan_first_page INTEGER,
        enable_scan INTEGER,
        max_actress_count INTEGER,
        enable_download INTEGER,
        filter TEXT,
        aka TEXT,
        birthday TEXT,
        height TEXT,
        bust TEXT,
        waist TEXT,
        hip TEXT,
        cup TEXT                                    
    )
    '''
    db_edit.execute(sql)
    print("[INFO] 表 actresses 已确保存在")

# ------------------ 插入/更新数据（增量更新 + 插入） ------------------
def insert_actresses(data):
    count = 0
    for actress in data:
        name = actress.get('Name')
        individual_movie = actress.get('Individual_Movie')
        only_scan_first_page = actress.get('Only_Scan_First_Page', 0)
        enable_scan = actress.get('Enable_Scan', 1)
        max_actress_count = actress.get('Max_Actress_Count', 10)
        enable_download = actress.get('Enable_Download', 0)
        filter = actress.get('Filter', 'VR')

        sql = '''
        INSERT INTO actresses (name, individual_movie, only_scan_first_page, enable_scan, max_actress_count, enable_download, filter)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(name) DO UPDATE SET
            individual_movie=excluded.individual_movie,
            only_scan_first_page=excluded.only_scan_first_page,
            enable_scan=excluded.enable_scan,
            max_actress_count=excluded.max_actress_count,
            enable_download=excluded.enable_download,
            filter=excluded.filter
        '''
        db_edit.execute(sql, (name, individual_movie, only_scan_first_page, enable_scan, max_actress_count, enable_download, filter))
        count += 1
    return count

# ------------------ 主程序 ------------------
def main():
    create_lock_file()
    try:
        # 加载 YAML 数据
        yaml_file = PROJECT_ROOT / 'cfg' / 'source.yaml'
        with yaml_file.open('r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        # 创建数据库文件
        create_db_file()

        # 创建表
        create_tables()

        # ------------------- 删除数据库中不在 YAML 的记录 -------------------
        names_in_yaml = [actress['Name'] for actress in data]
        if names_in_yaml:  # 防止列表为空报错
            placeholders = ','.join('?' for _ in names_in_yaml)
            sql_delete = f'DELETE FROM actresses WHERE name NOT IN ({placeholders})'
            db_edit.execute(sql_delete, names_in_yaml)
        else:
            db_edit.execute('DELETE FROM actresses')

        # ------------------- 增量更新/插入 -------------------
        actress_count = insert_actresses(data)

        print(f"数据已成功同步到数据库！共插入/更新 {actress_count} 条女演员数据。")

    finally:
        delete_lock_file()

if __name__ == "__main__":
    main()
