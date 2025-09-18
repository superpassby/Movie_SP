#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import re
import sqlite3
from pathlib import Path

# ------------------ 动态添加项目根目录 ------------------
CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = next(p for p in CURRENT_FILE.parents if (p / "cfg").exists())
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# ------------------ 导入项目模块 ------------------
from tools.fetch import fetch_html

# ------------------ 默认 URL ------------------
DEFAULT_URL = "https://jable.tv/categories/chinese-subtitle"

# ------------------ 函数定义 ------------------
def deduplicate(seq):
    """去重保持顺序"""
    return list(dict.fromkeys(seq))

def fetch_video_ids(page_url):
    """抓取单页的番号列表"""
    html = fetch_html(page_url)
    if not html:
        return []
    return [vid.upper() for vid in re.findall(r'https://jable\.tv/videos/([^/"]+)', html)]

def save_new_ids_to_db(db_path, new_ids):
    """
    将抓取到的新 ID 写入 jav_videos 表
    已存在的 ID 不重复写入
    name 固定为 'Jable_cnSUB'
    """
    if not new_ids:
        return

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row  # 使用列名访问字段
        cursor = conn.cursor()

        # 获取已有 ID
        cursor.execute("SELECT id FROM jav_videos")
        existing_ids = set(row["id"] for row in cursor.fetchall())

        # 筛选出新的 ID
        ids_to_insert = [vid for vid in new_ids if vid not in existing_ids]

        for vid in ids_to_insert:
            cursor.execute("""
                INSERT INTO jav_videos (id, name)
                VALUES (?, ?)
            """, (vid, "Jable_cnSUB"))
            print(f"[DB] 插入新 ID: {vid}, name=Jable_cnSUB")

        conn.commit()
        if ids_to_insert:
            print(f"[DB] 插入完成，共 {len(ids_to_insert)} 条新记录。")
        else:
            print("[DB] 没有新 ID 需要插入。")

    except Exception as e:
        print(f"[DB] 写入新 ID 时出错: {e}")
    finally:
        conn.close()


# ------------------ 主函数 ------------------
def main():
    args = sys.argv[1:]

    URL = DEFAULT_URL
    PAGE_START = 1
    PAGE_END = 1

    # 数据库路径
    db_path = PROJECT_ROOT / 'db' / 'data.db'

    # ------------------ 参数解析 ------------------
    if args:
        if args[0].isdigit():
            PAGE_START = int(args[0])
            PAGE_END = int(args[1]) if len(args) > 1 else PAGE_START
        else:
            URL = args[0]
            if len(args) > 1 and args[1].isdigit():
                PAGE_START = int(args[1])
                PAGE_END = int(args[2]) if len(args) > 2 else PAGE_START

    # ------------------ 搜索 URL 特殊处理 ------------------
    is_search = False
    if re.match(r'https://jable\.tv/search/([^/]+)/', URL):
        X1 = re.findall(r'https://jable\.tv/search/([^/]+)/', URL)[0]
        X2 = X1.replace("-", "%20")
        SEARCH_URL = f"https://jable.tv/search/{X1}/?mode=async&function=get_block&block_id=list_videos_videos_list_search_result&q={X2}&sort_by=post_date&from="
        is_search = True

    all_ids = []

    # ------------------ 分页抓取 ------------------
    for page in range(PAGE_START, PAGE_END + 1):
        if is_search:
            page_url = f"{SEARCH_URL}{page}"
        else:
            if not URL.endswith("/"):
                URL += "/"
            page_url = f"{URL}?mode=async&function=get_block&block_id=list_videos_common_videos_list&sort_by=post_date&from={page:02d}"

        print(f"抓取第 {page} 页: {page_url}")
        ids = fetch_video_ids(page_url)
        all_ids.extend(ids)

    # 去重
    new_ids = deduplicate(all_ids)

    # ------------------ 输出抓取结果 ------------------
    if new_ids:
        print(f"\n抓取完成，共 {len(new_ids)} 个番号：")
        print("\n".join(new_ids))
    else:
        print("\n没有抓取到番号。")

    # ------------------ 写入数据库 ------------------
    save_new_ids_to_db(db_path, new_ids)

# ------------------ 入口 ------------------
if __name__ == "__main__":
    main()
