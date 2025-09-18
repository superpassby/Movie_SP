#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import sqlite3
import yaml
from pathlib import Path
import datetime
import subprocess


# ------------------ 动态添加项目根目录 ------------------
CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = next(p for p in CURRENT_FILE.parents if (p / "cfg").exists())

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DB_PATH = PROJECT_ROOT / "db" / "data.db"
CFG_PATH = PROJECT_ROOT / "cfg" / "config.yaml"

# ------------------ 导入数据源脚本 ------------------
from tools.jav_data_fetch import data_AvBase  # 默认用 AvBase（enable=1 且第一个）



# def update_yaml_fetch_state(actress_name, fetch_state_msg):
#     yaml_path = PROJECT_ROOT / "cfg" / "source.yaml"

#     with open(yaml_path, "r", encoding="utf-8") as f:
#         data = yaml.safe_load(f)

#     for entry in data:
#         if entry.get("Name") == actress_name:
#             # 插入到 Name 下一行，只保留最近一次结果
#             entry["Fetch_State"] = fetch_state_msg
#             break

#     with open(yaml_path, "w", encoding="utf-8") as f:
#         yaml.dump(data, f, allow_unicode=True, sort_keys=False)


def update_yaml_fetch_state(actress_name, fetch_state_msg):
    """
    使用 sed 更新 cfg/source.yaml 中指定演员的 Fetch_State，
    插入到 Name 行下一行，只保留最新的结果
    """
    yaml_path = PROJECT_ROOT / "cfg" / "source.yaml"

    # 1. 删除原来的 Fetch_State 行（紧跟在 Name 后面）
    subprocess.run([
        "sed", "-i",
        f"/- Name: {actress_name}/{{n; s/^[[:space:]]*Fetch_State:.*//}}",
        str(yaml_path)
    ], check=True)

    # 2. 在 Name 行后插入新的 Fetch_State
    subprocess.run([
        "sed", "-i",
        f"/- Name: {actress_name}/a\\  Fetch_State: {fetch_state_msg}",
        str(yaml_path)
    ], check=True)


# ------------------ 确保表存在 ------------------
def ensure_table(conn):
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS jav_videos (
        name TEXT,
        date TEXT,
        id TEXT PRIMARY KEY,
        actress_count INTEGER,
        chinese_sub INTEGER,
        state TEXT,
        favorite INTEGER,
        watched INTEGER,
        m3u8 TEXT,
        m3u8_source TEXT,
        title TEXT
    )
    """)
    conn.commit()

# ------------------ 插入/更新 ------------------
def upsert_video(conn, video, max_count, actress_name):
    cursor = conn.cursor()
    vid = video.get("id")

    cursor.execute("SELECT id FROM jav_videos WHERE id=?", (vid,))
    existing = cursor.fetchone()

    # 状态判断
    state_val = None
    if max_count is not None and video.get("actress_count") and video["actress_count"] > max_count:
        state_val = "out_number"

    if existing:
        sql = """
        UPDATE jav_videos
        SET name=?, date=?, title=?, actress_count=?, state=?
        WHERE id=?
        """
        cursor.execute(sql, (
            actress_name,
            video.get("date"),
            video.get("title"),
            video.get("actress_count"),
            state_val,
            vid
        ))
    else:
        sql = """
        INSERT INTO jav_videos
        (name, date, id, actress_count, chinese_sub, state, favorite, watched, m3u8, m3u8_source, title)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        cursor.execute(sql, (
            actress_name,
            video.get("date"),
            vid,
            video.get("actress_count"),
            None,
            state_val,
            None,
            None,
            None,
            None,
            video.get("title"),
        ))
    conn.commit()

# ------------------ 按演员处理 ------------------
def process_actress(conn, source_name, actress_name, only_first, max_count):
    page = 1
    last_max_N = None   # 记录上一次成功获取的最大页数

    while True:
        if source_name == "AvBase":
            videos, max_N = data_AvBase.fetch_videos_by_page(actress_name, page)
        else:
            print(f"[ERROR] 暂不支持数据源 {source_name}")
            return
        
        if videos:
            last_max_N = max_N   # 更新最新的 max_N
        else:
            # 如果 page > max_N，并且有 last_max_N，则用 last_max_N
            if last_max_N and page > max_N:
                max_N = last_max_N

            msg = f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}, 获取第 {page} 页失败, 已知有 {max_N or '?'} 页"
            print(f"[WARN] {msg}")
            update_yaml_fetch_state(actress_name, msg)
            break

        for v in videos:
            print(f"[INFO] 写入 {v.get('id')} - {v.get('title')}")
            upsert_video(conn, v, max_count, actress_name)

        # 翻页逻辑
        if only_first == 1 or page >= max_N:
            break
        page += 1

    # ---------- post 处理 ----------
    cursor = conn.cursor()
    cursor.execute("SELECT id, actress_count FROM jav_videos WHERE name LIKE ?", (f"%{actress_name}%",))
    rows = cursor.fetchall()
    for vid, count in rows:
        if count is not None and max_count is not None and count <= max_count:
            cursor.execute("UPDATE jav_videos SET state=NULL WHERE id=? AND state='out_number'", (vid,))
    conn.commit()

# ------------------ 主函数 ------------------
def main():
    conn = sqlite3.connect(DB_PATH)
    ensure_table(conn)

    # 读取配置
    with open(CFG_PATH, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    data_sources = config.get("DataSources", [])
    target_source = next((s for s in data_sources if s.get("enable") == 1), None)

    if not target_source:
        print("[ERROR] 没有启用的数据源")
        sys.exit(1)

    source_name = target_source["name"]
    print(f"[INFO] 使用数据源: {source_name}")

    # 读取演员列表
    cursor = conn.cursor()
    cursor.execute("SELECT name, only_scan_first_page, enable_scan, max_actress_count FROM actresses")
    actresses = cursor.fetchall()

    for name, only_first, enable_scan, max_count in actresses:
        if enable_scan != 1:
            continue
        print(f"[INFO] 开始抓取演员: {name}")
        process_actress(conn, source_name, name, only_first, max_count)

    conn.close()
    print("[SUCCESS] 所有任务完成！")

# ------------------ 执行 ------------------
if __name__ == "__main__":
    main()
