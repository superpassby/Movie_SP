#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
import sys
from bs4 import BeautifulSoup
from pathlib import Path
from datetime import datetime
import sqlite3

# ------------------ 动态添加项目根目录 ------------------
CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = next(p for p in CURRENT_FILE.parents if (p / "cfg").exists())

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# ------------------ 导入项目模块 ------------------
from tools.fetch import fetch_html, config


# ------------------ 配置文件路径 ------------------
cfg_source_path = PROJECT_ROOT / "cfg" / "source.yaml"
cfg_path        = PROJECT_ROOT / "cfg" / "config.yaml"
db_path         = PROJECT_ROOT / "db" / "data.db"


# # ------------------ 演员搜索函数 ------------------
# def search_actresss(html_search: str, base_url: str):
#     soup = BeautifulSoup(html_search, "html.parser")
#     info_actress = soup.find("div", id="actors", class_="actors")
#     if info_actress:
#         a_tag = info_actress.find("a")
#         href = a_tag.get("href", "") if a_tag else ""
#     else:
#         href = ""
#     url_actress = f"{base_url}{href}" if href else ""
#     return url_actress

# ------------------ 演员搜索函数 ------------------
def search_actresss(html_search: str, base_url: str, order: int = None):
    soup = BeautifulSoup(html_search, "html.parser")
    info_actress = soup.find("div", id="actors", class_="actors")
    if info_actress:
        a_tags = info_actress.find_all("a")
        index = (order - 1) if order else 0  # order为空默认取第一个
        href = a_tags[index].get("href", "") if len(a_tags) > index else ""
    else:
        href = ""
    url_actress = f"{base_url}{href}" if href else ""
    return url_actress

# ------------------ 视频解析函数 ------------------
def search_video(html_video: str):
    soup = BeautifulSoup(html_video, "html.parser")

    results = []
    for a in soup.find_all("a", class_="box"):
        title = a.get("title", "").strip()

        # 海报
        img_tag = a.find("img")
        poster_url = img_tag.get("src", "").strip() if img_tag else ""

        # 番号 id
        video_title_div = a.find("div", class_="video-title")
        if video_title_div and video_title_div.find("strong"):
            video_id = video_title_div.find("strong").get_text(strip=True)
        else:
            video_id = ""

        # 日期
        meta_div = a.find("div", class_="meta")
        raw_date = meta_div.get_text(strip=True) if meta_div else ""
        formatted_date = ""
        if raw_date:
            try:
                dt = datetime.strptime(raw_date, "%m/%d/%Y")
                formatted_date = dt.strftime("%Y.%m.%d")
            except ValueError:
                formatted_date = raw_date  # 保留原始值

        results.append({
            "title": title,
            "poster_url": poster_url,
            "id": video_id,
            "date": formatted_date
        })

    # ---------------- 计算最大页数 ----------------
    pages = re.findall(r"/actors/[^/?#]+(?:\?page=(\d+))?", html_video)
    page_nums = [int(p) if p else 1 for p in pages]
    max_N = max(page_nums) if page_nums else 1

    return results, max_N

# ------------------ 新增函数：抓取所有视频 ------------------
def fetch_all_videos(official_name: str, only_first_page: int = 0):
    """
    根据演员官方名抓取所有视频，返回列表，每个元素是 video_info 字典
    only_first_page=1 时只抓取第一页
    调用原有的 fetch_html、search_actresss、search_video
    """
    db_path = PROJECT_ROOT / "db" / "data.db"

    # 获取 alias_name
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # cursor.execute("""
    #     SELECT aliases_name FROM aliases
    #     WHERE official_name=? AND source='JavDB'
    #     ORDER BY alias_order
    # """, (official_name,))
    
    cursor.execute("""
        SELECT aliases_name, alias_order FROM aliases
        WHERE official_name=? AND source='JavDB'
        ORDER BY alias_order
        LIMIT 1
    """, (official_name,))

    alias_row = cursor.fetchone()
    conn.close()
    if not alias_row:
        return []

    alias_name = alias_row[0]
    alias_order = int(alias_row[1]) if alias_row[1] else None


    base_url = "https://javdb.com"
    url_search = f"{base_url}/search?f=actor&q={alias_name}"
    html_search = fetch_html(url_search)
    if not html_search:
        print(f"[ERROR] 网络异常，无法请求演员搜索页面: {url_search}")
        return []
    
    # url_actress = search_actresss(html_search, base_url)
    url_actress = search_actresss(html_search, base_url, order=alias_order)

    
    if not url_actress:
        return []

    # 分页抓取视频
    videos_all = []
    page = 1
    while True:
        url_video = f"{url_actress}?page={page}"
        html_video = fetch_html(url_video)
        if not html_video:
            print(f"[ERROR] 网络异常，无法请求视频页面: {url_video}")
            break
        videos, max_page = search_video(html_video)
        videos_all.extend(videos)

        # 如果设置只抓第一页，直接跳出
        if only_first_page == 1:
            break

        if page >= max_page:
            break
        page += 1

    return videos_all


# ------------------ main 仅用于直接运行 ------------------
def main():
    if len(sys.argv) < 2:
        print("请提供演员姓名，例如：python3 data_javdb.py 白峰美羽")
        sys.exit(1)

    input_name = sys.argv[1].strip()

    # ------------------ 打开数据库 ------------------
    db_path = PROJECT_ROOT / "db" / "data.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # ------------------ 检查演员是否存在 ------------------
    cursor.execute("SELECT * FROM actresses WHERE official_name=?", (input_name,))
    actress_row = cursor.fetchone()
    if not actress_row:
        print(f"[ERROR] 演员 '{input_name}' 不在数据库中，请先添加信息！")
        sys.exit(1)

    # ------------------ 查找别名表中对应 JavDB 别名 ------------------
    # cursor.execute("""
    #     SELECT aliases_name FROM aliases 
    #     WHERE official_name=? AND source='JavDB' 
    #     ORDER BY alias_order
    #     """, (input_name,))
   
    cursor.execute("""
        SELECT aliases_name, alias_order FROM aliases 
        WHERE official_name=? AND source='JavDB' 
        ORDER BY alias_order
        """, (input_name,))    
    
    
    alias_row = cursor.fetchone()
    if not alias_row:
        print(f"[ERROR] 演员 '{input_name}' 在 aliases 表中没有对应 JavDB 别名！")
        sys.exit(1)

    alias_name = alias_row[0]
    alias_order = int(alias_row[1]) if alias_row[1] else None

    base_url = "https://javdb.com"
    url_actress = f"{base_url}/search?f=actor&q={alias_name}"
    
    print(f"[DEBUG] 请求 URL: {url_actress}")
    
    # ------------------ 获取演员页面 URL ------------------
    html_search = fetch_html(url_actress)
    # url_actress = search_actresss(html_search, base_url)
    url_actress = search_actresss(html_search, base_url, order=alias_order)

    # ------------------ 分页抓取视频 ------------------
    n = 1
    while True:
        url_video = f"{url_actress}?page={n}"
        print(f"[DEBUG-3] 请求 URL: {url_video}")
        html_video = fetch_html(url_video)
        if not html_video:
            print(f"[ERROR] 获取页面失败: {url_video}")
            sys.exit(1)
        videos, max_N = search_video(html_video)

        for v in videos:
            print("ID:", v["id"])
            print("Title:", v["title"])
            print("Poster:", v["poster_url"])
            print("Date:", v["date"])
            print("-" * 40)

        if n >= max_N:
            break
        n += 1

    conn.close()

if __name__ == "__main__":
    main()
