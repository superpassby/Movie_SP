#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
from pathlib import Path

# import re
# from bs4 import BeautifulSoup
# from datetime import datetime
# import sqlite3
# import json

# ------------------ 动态添加项目根目录 ------------------
PROJECT_ROOT = next(p for p in Path(__file__).resolve().parents if (p / "cfg").exists())
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# ------------------ 导入其它模块 ------------------
from tools.fetch import fetch_html
db_path = PROJECT_ROOT / "db" / "data.db"

# ------------------- 定义异常类 -------------------
class NotFoundError(Exception):
    """自定义异常: 未找到演员页网址后缀"""
    pass

# ------------------- 根据演员名称获取 individual_movie 字段 -------------------
def get_individual_movie_by_name(name):
    import sqlite3
    """
    :param name: 演员名称
    :return: individual_movie 的值
    :raises NotFoundError: 如果名称或 individual_movie 不存在
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 查询该名称对应的行
    cursor.execute("SELECT individual_movie FROM actresses WHERE name = ?", (name,))
    result = cursor.fetchone()
    
    conn.close()
    
    if result is None:
        # 表中没有该名称
        raise NotFoundError(f"{name} 不在数据库中")
    
    individual_movie = result[0]
    
    if not individual_movie:
        # individual_movie 为空
        raise NotFoundError(f"{name} 无对应番号，请添加")
    
    return individual_movie

# ------------------- 获取演员页后缀 -------------------
def extract_talent_suffix(html):

    from bs4 import BeautifulSoup

    """从HTML内容中提取演员页的网址后缀"""
    soup = BeautifulSoup(html, 'html.parser')
    talent_suffix = soup.find('a', href=lambda x: x and '/talents/' in x)
    
    if talent_suffix:
        return talent_suffix['href'].split('/talents/')[1]
    
    raise NotFoundError("没有找到演员页的网址后缀")
    
# # ------------------- 测试示例 -------------------
# # HTML 内容来自文件
# file_path = 'test.html'
# with open(file_path, 'r', encoding='utf-8') as f:
#     html_content = f.read()

# try:
#     suffix = extract_talent_suffix(html_content)
#     print(f"演员页网址后缀: {suffix}")
# except NotFoundError as e:
#     print(f"错误: {e}")


# ------------------- 获取json -------------------
def parse_next_data(html):
    from bs4 import BeautifulSoup
    import json
    """
    从 HTML 中提取 id="__NEXT_DATA__" 的 JSON 内容
    :param html: HTML 字符串
    :return: Python dict
    :raises NotFoundError: 如果未找到或解析失败
    """
    soup = BeautifulSoup(html, 'html.parser')
    script_tag = soup.find('script', id="__NEXT_DATA__")
    if not script_tag or not script_tag.string:
        raise NotFoundError("__NEXT_DATA__ JSON 未找到")
    try:
        return json.loads(script_tag.string)
    except json.JSONDecodeError as e:
        raise NotFoundError(f"JSON 解析失败: {e}")

# ---------- 最大页数 ----------
def get_max_page(html):
    import re
    """
    从 HTML 内容中获取显示的最大页码
    :param html: HTML 字符串
    :return: 最大页码 int
    """
    # 把 &amp; 替换回 &
    html_decoded = html.replace("&amp;", "&")
    
    # 查找所有 ?page= 或 &page= 的数字
    pages = re.findall(r"[?&]page=(\d+)", html_decoded)
    
    # 转成整数列表，如果没有找到 page 参数，则默认为 [1]
    page_nums = [int(p) for p in pages] if pages else [1]
    
    # 返回最大页码
    max_page = max(page_nums)
    return max_page


# ---------- 处理 JSON 数据 ----------
def process_json_data(json_data):
    # 加载模块
    import json
    from datetime import datetime

    # 访问 primary 下的 name 字段，使用 get() 方法防止 KeyError
    primary_name = json_data['props']['pageProps']['talent']['primary'].get('name', '')

    # 提取所有演员的 name，使用 get() 方法防止 KeyError
    actors_names = [actor.get('name', '') for actor in json_data['props']['pageProps']['talent'].get('actors', [])]

    # 创建一个集合来跟踪已见过的名字，去重
    seen_names = set()
    unique_names = []

    for name in [primary_name] + actors_names:
        if name and name not in seen_names:  # 忽略空值和重复的名字
            unique_names.append(name)
            seen_names.add(name)

    aka = " ".join(unique_names)

    # 提取演员的基本信息，确保每个字段都可以安全获取
    try:
        fanza_meta = json_data['props']['pageProps']['talent']['actors'][0].get('meta', {}).get('fanza', {})
        actor_info = {
            'aka': aka,  # 将 aka 放入 actor_info 中
            'birthday': fanza_meta.get('birthday', ''),
            'height': fanza_meta.get('height', ''),
            'bust': fanza_meta.get('bust', ''),
            'waist': fanza_meta.get('waist', ''),
            'hip': fanza_meta.get('hip', ''),
            'cup': fanza_meta.get('cup', '')
        }
    except IndexError:
        actor_info = {'aka': aka}  # 如果演员列表为空，至少返回 aka

    # 提取 works 数据，确保每个字段都可以安全获取
    works_info = []
    for work in json_data['props']['pageProps'].get('works', []):
        work_id = work.get('work_id', '')
        title = work.get('title', '')
        issue_date = ''
        try:
            # 转换 min_date 为指定的格式，处理可能为空的字段
            issue_date = datetime.strptime(work.get('min_date', ''), '%a %b %d %Y %H:%M:%S GMT+0900 (Japan Standard Time)').strftime("%Y.%m.%d")  
        except ValueError:
            pass  # 如果无法解析日期，保持为空字符串
        actors_names_str = ' '.join([actor.get('name', '') for actor in work.get('actors', [])])
        actors_count = len(work.get('actors', []))

        works_info.append({
            'work_id': work_id,
            'title': title,
            'issue_date': issue_date,
            'actors_names': actors_names_str,
            'actors_count': actors_count
        })

    # 返回结果
    return {
        'actor_info': actor_info,  # 现在只返回 actor_info 和 works_info
        'works_info': works_info
    }

# # def process_json_data(json_data) 示例用法 用本地文件 test.json ，和本函数同一目录：
# with open('test.json', 'r', encoding='utf-8') as file:
#     json_data = json.load(file)

# result = process_json_data(json_data)

# # 打印结果
# print("Actor Info:")
# for key, value in result['actor_info'].items():
#     print(f"{key.capitalize()}: {value}")

# print("\nWorks Info:")
# for work in result['works_info']:
#     print(f"Work ID: {work['work_id']}")
#     print(f"Title: {work['title']}")
#     print(f"Issue Date: {work['issue_date']}")
#     print(f"Actors Names: {work['actors_names']}")
#     print(f"Actors Count: {work['actors_count']}")
#     print("\n" + "-"*30 + "\n")



# # ---------- 用于外部调用 ----------
# def fetch_actor_data(input_name, page=1):
#     """
#     根据演员姓名和页码获取演员信息和作品信息
#     :param input_name: 演员名称
#     :param page: 页码，默认 1
#     :return: dict，包括 actor_info, works_info, talent_suffix, url_works, max_page
#     :raises NotFoundError: 如果数据未找到
#     """
#     base_url = "https://avbase.net"

#     # individual_movie
#     individual_movie = get_individual_movie_by_name(input_name)
#     url_works = f"{base_url}/works/{individual_movie}"
#     html_works = fetch_html(url_works)

#     # 演员页后缀
#     talent_suffix = extract_talent_suffix(html_works)
    
#     url_talents_page = f"{base_url}/talents/{talent_suffix}?q=&page={page}"
#     html_talents_page = fetch_html(url_talents_page)

#     # 最大页数
#     max_page = get_max_page(html_talents_page)

#     # JSON 数据
#     json_data = parse_next_data(html_talents_page)
#     result = process_json_data(json_data)

#     # 返回所有需要的信息
#     return {
#         # "individual_movie": individual_movie,
#         # "url_works": url_works,
#         # "talent_suffix": talent_suffix,
#         # "url_talents_page": url_talents_page,
#         "max_page": max_page,
#         "actor_info": result["actor_info"],
#         "works_info": result["works_info"]
#     }


# 在模块顶部定义缓存
_actor_cache = {}

def fetch_actor_data(input_name, page=1):
    """
    根据演员姓名和页码获取演员信息和作品信息
    对每个演员，individual_movie、url_works、talent_suffix 只获取一次
    """
    global _actor_cache

    # 检查缓存
    if input_name in _actor_cache:
        cache = _actor_cache[input_name]
        individual_movie = cache["individual_movie"]
        url_works = cache["url_works"]
        talent_suffix = cache["talent_suffix"]
    else:
        base_url = "https://avbase.net"

        # individual_movie
        individual_movie = get_individual_movie_by_name(input_name)
        url_works = f"{base_url}/works/{individual_movie}"
        html_works = fetch_html(url_works)

        # 演员页后缀
        talent_suffix = extract_talent_suffix(html_works)

        # 保存到缓存
        _actor_cache[input_name] = {
            "individual_movie": individual_movie,
            "url_works": url_works,
            "talent_suffix": talent_suffix
        }

    # 构造演员页 URL
    base_url = "https://avbase.net"
    url_talents_page = f"{base_url}/talents/{talent_suffix}?q=&page={page}"
    html_talents_page = fetch_html(url_talents_page)

    # 最大页数
    max_page = get_max_page(html_talents_page)

    # JSON 数据
    json_data = parse_next_data(html_talents_page)
    result = process_json_data(json_data)

    return {
        "max_page": max_page,
        "actor_info": result["actor_info"],
        "works_info": result["works_info"]
    }



# ------------------ main 仅用于直接运行 ------------------
def main():

    # if len(sys.argv) < 2:
    #     print("请提供演员姓名，例如：python3 tools/jav_data_fetch/data_AvBase.py 白峰美羽 [页码]")
    #     sys.exit(1)

    # input_name = sys.argv[1].strip()
    # page = int(sys.argv[2]) if len(sys.argv) > 2 else 1

    input_name = "新有菜"  # 替换为实际名称
    page= 3

    try:
        data = fetch_actor_data(input_name, page)
        # 打印结果
        print("\n" + "-"*30 + "\n")
        print("Actor Info:")
        for key, value in data['actor_info'].items():
            print(f"{key.capitalize()}: {value}")
        
        print("\n" + "-"*30 + "\n")
        print("\nWorks Info:")
        print("\n" + "-"*30 + "\n")
        for work in data['works_info']:
            print(f"Work ID: {work['work_id']}")
            print(f"Title: {work['title']}")
            print(f"Issue Date: {work['issue_date']}")
            print(f"Actors Names: {work['actors_names']}")
            print(f"Actors Count: {work['actors_count']}")
            print("\n" + "-"*30 + "\n")

        print(f"[INFO] 当前页: {page} / 最大页数: {data['max_page']}\n")
    except NotFoundError as e:
        print("错误:", e)


if __name__ == "__main__":
    main()


