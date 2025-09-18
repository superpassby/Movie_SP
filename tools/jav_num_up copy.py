#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import sqlite3
from pathlib import Path

# ------------------ 动态添加项目根目录 ------------------
CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = next(p for p in CURRENT_FILE.parents if (p / "cfg").exists())

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DB_PATH = PROJECT_ROOT / "db" / "data.db"

# ------------------ 导入 data_javdb.py ------------------
from tools.jav_data_fetch.data_javdb import fetch_all_videos

# ------------------ 确保表存在 ------------------
def ensure_table(conn):
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS jav_videos (
        actress TEXT,
        date TEXT,
        id TEXT PRIMARY KEY,
        title TEXT,
        chinese_sub INTEGER,
        state TEXT,
        favorite INTEGER,
        watched INTEGER,
        m3u8 TEXT,
    )
    """)
    conn.commit()

# ------------------ 数据库插入或更新函数 ------------------
def upsert_video(conn, actress_name, video_info):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM jav_videos WHERE id=?", (video_info.get("id"),))
    existing = cursor.fetchone()

    if existing:
        updates = []
        values = []

        # 始终更新 actress
        updates.append("actress=?")
        values.append(actress_name)

        # 其他字段只更新抓到的非空值
        for key in ["date", "title", "chinese_sub", "state", "favorite", "watched", "m3u8_chn_sub", "m3u8_no_sub"]:
            val = video_info.get(key)
            if val is not None and val != "":
                updates.append(f"{key}=?")
                values.append(val)

        if updates:
            values.append(video_info.get("id"))
            sql = f"UPDATE jav_videos SET {', '.join(updates)} WHERE id=?"
            cursor.execute(sql, values)
    else:
        cursor.execute("""
            INSERT INTO jav_videos
            (actress, date, id, title, chinese_sub, state, favorite, watched, m3u8_chn_sub, m3u8_no_sub)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            actress_name,
            video_info.get("date"),
            video_info.get("id"),
            video_info.get("title"),
            video_info.get("chinese_sub"),
            video_info.get("state"),
            video_info.get("favorite"),
            video_info.get("watched"),
            video_info.get("m3u8_chn_sub"),
            video_info.get("m3u8_no_sub")
        ))
    conn.commit()

# ------------------ 获取所有演员列表 ------------------
def get_actress_list(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT official_name, only_scan_first_page FROM actresses WHERE enable_download=1")
    rows = cursor.fetchall()
    actress_list = [{"official_name": r[0], "only_scan_first_page": r[1]} for r in rows]
    return actress_list

# ------------------ 主函数 ------------------
def main():
    conn = sqlite3.connect(DB_PATH)
    ensure_table(conn)

    actress_list = get_actress_list(conn)
    if not actress_list:
        print("[ERROR] 数据库中没有启用下载的演员！")
        conn.close()
        sys.exit(1)

    for actress in actress_list:
        official_name = actress["official_name"]
        only_first = actress.get("only_scan_first_page", 0)

        print(f"[INFO] 开始抓取演员: {official_name} (只抓第一页: {only_first})")

        # 调用 data_javdb.fetch_all_videos，传入 only_first 参数
        videos = fetch_all_videos(official_name, only_first_page=only_first)

        if not videos:
            print(f"[WARN] 没有获取到 '{official_name}' 的视频")
            continue

        for v in videos:
            print(f"[INFO] 写入/更新视频: {v.get('id')} - {v.get('title')}")
            upsert_video(conn, official_name, v)

    conn.close()
    print("[SUCCESS] 所有视频已写入数据库！")

# ------------------ 执行 ------------------
if __name__ == "__main__":
    main()
