#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
import sys
from bs4 import BeautifulSoup
from pathlib import Path
from datetime import datetime
import sqlite3
import json

# ------------------ 动态添加项目根目录 ------------------
CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = next(p for p in CURRENT_FILE.parents if (p / "cfg").exists())

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# ------------------ 导入项目模块 ------------------
from tools.fetch import fetch_html, config

# ------------------ 演员页面 URL 搜索 ------------------
def search_actresss(html_search: str, base_url: str):
    """
    从演员搜索页面 HTML 中找到第一个演员详情页 URL
    """
    soup = BeautifulSoup(html_search, "html.parser")
    a_tag = next((a for a in soup.find_all("a", href=True) if a["href"].startswith("/talents/")), None)
    url_actress = f"{base_url}{a_tag['href']}" if a_tag else ""
    return url_actress

# ------------------ 视频解析函数 ------------------
def search_video(html_video: str):
    """
    解析 AvBase 视频页面 HTML，提取番号、标题、日期、演员列表、演员数量
    返回 (视频列表, 最大页数)
    """
    results = []

    # ---------- 解析 JSON 数据 ----------
    soup = BeautifulSoup(html_video, "html.parser")
    script_tag = soup.find("script", id="__NEXT_DATA__")
    if not script_tag:
        return results, 1

    data = json.loads(script_tag.string)
    works_list = data.get("props", {}).get("pageProps", {}).get("works", [])

    for work in works_list:
        # 番号
        video_id = work.get("work_id", "")

        # 标题
        title = work.get("title", "")

        # 日期
        raw_date = work.get("min_date", "")
        formatted_date = ""
        try:
            dt = datetime.strptime(raw_date[:15], "%a %b %d %Y")
            formatted_date = dt.strftime("%Y.%m.%d")
        except:
            formatted_date = raw_date

        # 演员列表（最多10个用于显示）
        actors = [a.get("name", "") for a in work.get("actors", [])]
        talents = actors[:10]

        # 演员数量（真实数量）
        actress_count = len(actors)

        results.append({
            "id": video_id,
            "title": title,
            "date": formatted_date,
            "actresses": talents,
            "actress_count": actress_count
        })

    # ---------- 最大页数 ----------
    html_video_decoded = html_video.replace("&amp;", "&")
    pages = re.findall(r"[?&]page=(\d+)", html_video_decoded)
    page_nums = [int(p) for p in pages] if pages else [1]
    max_N = max(page_nums)
    # print(f"[DEBUG] 最大页数: {max_N}")

    return results, max_N

# ------------------ 主函数：按演员和页码抓取视频 ------------------
def fetch_videos_by_page(actress_name: str, page: int = 1):
    """
    根据演员名称抓取 AvBase 指定页的视频
    返回 (视频列表, 最大页数)
    """
    db_path = PROJECT_ROOT / "db" / "data.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 直接查actresses表
    cursor.execute("SELECT individual_movie FROM actresses WHERE name=?", (actress_name,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        print(f"[ERROR] 演员 '{actress_name}' 不在数据库中！")
        return [], 1

    individual_movie = row["individual_movie"]
    base_url = "https://avbase.net"
    url_search = f"{base_url}/works/{individual_movie}"

    html_search = fetch_html(url_search)
    if not html_search:
        print(f"[ERROR] 获取演员页面失败: {url_search}")
        return [], 1

    url_actress = search_actresss(html_search, base_url)
    if not url_actress:
        return [], 1

    # 请求指定页
    url_video = f"{url_actress}?page={page}"
    html_video = fetch_html(url_video)
    if not html_video:
        print(f"[ERROR] 获取视频页面失败: {url_video}")
        return [], 1

    videos, max_N = search_video(html_video)
    return videos, max_N

# ------------------ main 仅用于直接运行 ------------------
def main():
    if len(sys.argv) < 2:
        print("请提供演员姓名，例如：python3 tools/jav_data_fetch/data_AvBase.py 白峰美羽 [页码]")
        sys.exit(1)

    input_name = sys.argv[1].strip()
    page = int(sys.argv[2]) if len(sys.argv) > 2 else 1

    videos, max_page = fetch_videos_by_page(input_name, page)


    for v in videos:
        print(f"番号: {v['id']}")
        print(f"标题: {v['title']}")
        print(f"日期: {v['date']}")
        print(f"演员列表: {', '.join(v['actresses'])}")
        print(f"演员数量: {v['actress_count']}")
        print("-" * 60)

    print(f"[INFO] 当前页: {page} / 最大页数: {max_page}\n")

if __name__ == "__main__":
    main()
