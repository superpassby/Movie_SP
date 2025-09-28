# #!/usr/bin/env python3
# # -*- coding: utf-8 -*-

# import sys
# import re
# import sqlite3
# from pathlib import Path

# # ------------------ 动态添加项目根目录 ------------------
# CURRENT_FILE = Path(__file__).resolve()
# PROJECT_ROOT = next(p for p in CURRENT_FILE.parents if (p / "cfg").exists())
# if str(PROJECT_ROOT) not in sys.path:
#     sys.path.insert(0, str(PROJECT_ROOT))

# # ------------------ 导入项目模块 ------------------
# from tools.fetch import fetch_html

# # ------------------ 默认 URL ------------------
# DEFAULT_URL = "https://jable.tv/categories/chinese-subtitle"

# # ------------------ 函数定义 ------------------
# def deduplicate(seq):
#     """去重保持顺序"""
#     return list(dict.fromkeys(seq))

# def fetch_video_ids(page_url):
#     """抓取单页的番号列表"""
#     html = fetch_html(page_url)
#     if not html:
#         return []
#     return [vid.upper() for vid in re.findall(r'https://jable\.tv/videos/([^/"]+)', html)]

# def save_new_ids_to_db(db_path, new_ids):
#     """
#     将抓取到的新 ID 写入 jav_videos 表
#     已存在的 ID 不重复写入
#     name 固定为 'Jable_cnSUB'
#     """
#     if not new_ids:
#         return

#     try:
#         conn = sqlite3.connect(db_path)
#         conn.row_factory = sqlite3.Row  # 使用列名访问字段
#         cursor = conn.cursor()

#         # 获取已有 ID
#         cursor.execute("SELECT id FROM jav_videos")
#         existing_ids = set(row["id"] for row in cursor.fetchall())

#         # 筛选出新的 ID
#         ids_to_insert = [vid for vid in new_ids if vid not in existing_ids]

#         for vid in ids_to_insert:
#             cursor.execute("""
#                 INSERT INTO jav_videos (id, name)
#                 VALUES (?, ?)
#             """, (vid, "Jable_cnSUB"))
#             print(f"[DB] 插入新 ID: {vid}, name=Jable_cnSUB")

#         conn.commit()
#         if ids_to_insert:
#             print(f"[DB] 插入完成，共 {len(ids_to_insert)} 条新记录。")
#         else:
#             print("[DB] 没有新 ID 需要插入。")

#     except Exception as e:
#         print(f"[DB] 写入新 ID 时出错: {e}")
#     finally:
#         conn.close()


# # ------------------ 主函数 ------------------
# def main():
#     args = sys.argv[1:]

#     URL = DEFAULT_URL
#     PAGE_START = 1
#     PAGE_END = 1

#     # 数据库路径
#     db_path = PROJECT_ROOT / 'db' / 'data.db'

#     # ------------------ 参数解析 ------------------
#     if args:
#         if args[0].isdigit():
#             PAGE_START = int(args[0])
#             PAGE_END = int(args[1]) if len(args) > 1 else PAGE_START
#         else:
#             URL = args[0]
#             if len(args) > 1 and args[1].isdigit():
#                 PAGE_START = int(args[1])
#                 PAGE_END = int(args[2]) if len(args) > 2 else PAGE_START

#     # ------------------ 搜索 URL 特殊处理 ------------------
#     is_search = False
#     if re.match(r'https://jable\.tv/search/([^/]+)/', URL):
#         X1 = re.findall(r'https://jable\.tv/search/([^/]+)/', URL)[0]
#         X2 = X1.replace("-", "%20")
#         SEARCH_URL = f"https://jable.tv/search/{X1}/?mode=async&function=get_block&block_id=list_videos_videos_list_search_result&q={X2}&sort_by=post_date&from="
#         is_search = True

#     all_ids = []

#     # ------------------ 分页抓取 ------------------
#     for page in range(PAGE_START, PAGE_END + 1):
#         if is_search:
#             page_url = f"{SEARCH_URL}{page}"
#         else:
#             if not URL.endswith("/"):
#                 URL += "/"
#             page_url = f"{URL}?mode=async&function=get_block&block_id=list_videos_common_videos_list&sort_by=post_date&from={page:02d}"

#         print(f"抓取第 {page} 页: {page_url}")
#         ids = fetch_video_ids(page_url)
#         all_ids.extend(ids)

#     # 去重
#     new_ids = deduplicate(all_ids)

#     # ------------------ 输出抓取结果 ------------------
#     if new_ids:
#         print(f"\n抓取完成，共 {len(new_ids)} 个番号：")
#         print("\n".join(new_ids))
#     else:
#         print("\n没有抓取到番号。")

#     # ------------------ 写入数据库 ------------------
#     save_new_ids_to_db(db_path, new_ids)

# # ------------------ 入口 ------------------
# if __name__ == "__main__":
#     main()


#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
import sys
import json
import sqlite3
from pathlib import Path
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import quote

# ------------------ 动态添加项目根目录 ------------------
CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = next(p for p in CURRENT_FILE.parents if (p / "cfg").exists())
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# ------------------ 导入项目模块 ------------------
from tools.fetch import fetch_html_curl
fetch_html = fetch_html_curl
from switch_clash import switch_clash_group # 导入 switch_clash_group 函数
from tools.Data_Base_Edit.db_edit import db_edit

# ------------------ 默认 URL ------------------
DEFAULT_URL = "https://jable.tv/categories/chinese-subtitle"

# ------------------ 函数定义 ------------------

def update_proxy():
    test_group = "自定义代理"
    test_filter = "|jp 日本"
    test_url_key = "jable"
    switch_clash_group(test_group, test_filter, test_url_key)

def fetch_and_save_video_ids(url=DEFAULT_URL, page_start=1, page_end=1, db_path=None):
    """
    抓取视频 ID 并写入数据库（去重、保持顺序）
    """
    if not db_path:
        db_path = PROJECT_ROOT / 'db' / 'data.db'

    is_search = False
    all_ids = []

    # 搜索 URL 特殊处理
    search_match = re.match(r'https://jable\.tv/search/([^/]+)/', url)
    if search_match:
        X1 = search_match[1]
        X2 = X1.replace("-", "%20")
        search_url = f"https://jable.tv/search/{X1}/?mode=async&function=get_block&block_id=list_videos_videos_list_search_result&q={X2}&sort_by=post_date&from="
        is_search = True

    # 分页抓取
    for page in range(page_start, page_end + 1):
        if is_search:
            page_url = f"{search_url}{page}"
        else:
            page_url = f"{url.rstrip('/')}/?mode=async&function=get_block&block_id=list_videos_common_videos_list&sort_by=post_date&from={page:02d}"
        print(f"抓取第 {page} 页: {page_url}")

        html = fetch_html(page_url)
        if not html:
            continue

        # 提取视频 ID 并大写
        ids = [vid.upper() for vid in re.findall(r'https://jable\.tv/videos/([^/"]+)', html)]
        all_ids.extend(ids)

    # 去重保持顺序
    new_ids = list(dict.fromkeys(all_ids))

    # 输出抓取结果
    if new_ids:
        print(f"\n抓取完成，共 {len(new_ids)} 个番号：")
        print("\n".join(new_ids))
    else:
        print("\n没有抓取到番号。")

    # 写入数据库
    if new_ids:
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("SELECT id FROM jav_videos")
            existing_ids = set(row["id"] for row in cursor.fetchall())

            ids_to_insert = [vid for vid in new_ids if vid not in existing_ids]
            for vid in ids_to_insert:
                cursor.execute("INSERT INTO jav_videos (id, name) VALUES (?, ?)", (vid, "Jable_cnSUB"))
                print(f"[DB] 插入新 ID: {vid}, name=Jable_cnSUB")

            conn.commit()
            print(f"[DB] 插入完成，共 {len(ids_to_insert)} 条新记录。" if ids_to_insert else "[DB] 没有新 ID 需要插入。")
        except Exception as e:
            print(f"[DB] 写入新 ID 时出错: {e}")
        finally:
            conn.close()

###############

class AVBaseAPI:
    def __init__(self):
        self.base_url = "https://www.avbase.net/"
        self.build_id = self._get_build_id()

    def _get_build_id(self):
        """从页面中获取 buildId"""
        html = fetch_html(self.base_url)  # 使用 fetch_html 获取页面内容
        
        if not html:  # 如果获取不到 html，返回空值
            print("[ERROR] 未能获取到页面内容")
            return None
        
        soup = BeautifulSoup(html, 'html.parser')
        script = soup.find('script', id='__NEXT_DATA__')  # 获取包含 buildId 的 script 标签
        if not script:
            print("[ERROR] 页面中没有找到 __NEXT_DATA__ script 标签")
            return None
        
        data = json.loads(script.string)  # 解析 JSON 数据
        return data['buildId']  # 返回 buildId

    def get_search_api_url(self, movie_id):
        """根据 movie_id 生成 searchAPIURL"""
        id_upper = movie_id.upper()
        search_api_url = f"https://www.avbase.net/_next/data/{self.build_id}/works.json?q={quote(id_upper)}"
        return search_api_url

    def get_movie_info(self, movie_id):
        """获取电影信息"""
        # 获取 search API URL
        search_api_url = self.get_search_api_url(movie_id)

        # 获取 JSON 数据
        try:
            html = fetch_html(search_api_url)
            if not html:
                print(f"[ERROR] 无法获取电影信息：{movie_id}")
                return []  # 如果获取不到 HTML，返回空列表
            json_data = json.loads(html)
        except Exception as e:
            print(f"[ERROR] 获取电影信息失败：{movie_id}, 错误: {e}")
            return []  # 出现异常时返回空列表

        # 提取电影信息
        return self.process_movie_info(json_data)

    def process_movie_info(self, json_data):
        """处理并提取电影信息"""
        movie_info = []
        
        # 检查 'pageProps' 和 'works' 是否存在
        works = json_data.get('pageProps', {}).get('works', [])
        
        # 如果 'works' 不存在，则返回空值
        if not works:
            movie_info.append({
                'id': '',
                'title': '',
                'issue_date': '',
                'actors_names': ''
            })
        else:
            for movie in works:
                # 1. 生成 id
                prefix = movie.get('prefix', '')
                work_id = movie.get('work_id', '')
                movie_id = f"{prefix}:{work_id}" if prefix else work_id  # 如果 prefix 存在，则生成 prefix:work_id，否则使用 work_id
                
                # 2. 提取 title
                title = movie.get('title', '')
                
                # 3. 转换 min_date 为指定格式 (YYYY.MM.DD)
                issue_date = ''
                try:
                    issue_date = datetime.strptime(movie.get('min_date', ''), '%a %b %d %Y %H:%M:%S GMT+0900 (Japan Standard Time)').strftime("%Y.%m.%d")
                except ValueError:
                    pass  # 如果无法解析日期，保持为空字符串
                
                # 4. 提取所有演员的 name，空格隔开
                actors_names = [actor.get('name', '') for actor in movie.get('actors', [])]
                actors_names_str = ' '.join(actors_names)
                
                # 添加电影信息到列表
                movie_info.append({
                    'id': movie_id,
                    'title': title,
                    'issue_date': issue_date,
                    'actors_names': actors_names_str
                })
        
        return movie_info

def fetch_actresses_data():
    """从 actresses 表中获取所有演员的 name 和 aka"""
    sql = "SELECT name, aka FROM actresses"
    # 执行查询
    actresses_data = db_edit.fetch_all(sql)

    # 如果数据存在，返回一个字典列表
    if actresses_data:
        return [{'name': name, 'aka': aka} for name, aka in actresses_data]
    else:
        return []  # 如果没有数据，返回空列表
    
def find_name_by_aka(actors_names):
    """根据演员的 aka 查找对应的 name"""
    sql = "SELECT name, aka FROM actresses WHERE aka LIKE ?"
    # 使用模糊匹配，避免精确匹配失败
    result = db_edit.fetch_one(sql, (f"%{actors_names}%",))
    
    # 如果找到对应的 name，返回它；否则返回空字符串
    if result:
        name, _ = result
        return name
    else:
        return ""  # 如果没有找到对应的 name，返回空字符串

def find_video_ids_by_name(name):
    """根据 name 查找 jav_videos 表中的所有 id"""
    sql = "SELECT id FROM jav_videos WHERE name = ?"
    # 执行查询，查找所有 name 为 "Jable_cnSUB" 的记录
    results = db_edit.fetch_all(sql, (name,))
    
    # 如果找到对应的记录，返回 id 列表，否则返回空列表
    if results:
        return [result[0] for result in results]  # 提取 id 并返回
    else:
        return []  # 如果没有找到记录，返回空列表
    
# 更新视频信息
def update_video_names():
    if_html_false = 0  # 初始化标记为 0
    
    video_name = "Jable_cnSUB"
    
    # 查找所有视频的 id，并检查相关信息
    sql = "SELECT id, name, actress FROM jav_videos WHERE name = ?"
    video_ids = db_edit.fetch_all(sql, (video_name,))

    if not video_ids:
        print(f"[INFO] 没有找到名为 '{video_name}' 的视频.")
        return

    api = AVBaseAPI()

    for video in video_ids:
        video_id, name, actress = video

        # 检查 actress 列的内容是否为空或无实际意义
        if not actress or actress.strip().lower() in ['none', '']:
            print(f"[INFO] {video_id} 的 actress 列为空或无效，尝试获取电影信息")
            # 获取该 video_id 对应的电影信息
            movie_info = api.get_movie_info(video_id)

            if not movie_info:
                print(f"[INFO] 未找到 video_id {video_id} 的电影信息")
                if_html_false = 1  # 设置标记为 1，表示失败
                update_proxy()
            else:
                print(f"[INFO] 成功获取 video_id {video_id} 的电影信息")

            # 使用 movie_info 中的演员信息
            for movie in movie_info:
                actors_names = movie['actors_names']
                actors = actors_names.split(' ')  # 假设演员名字之间用空格隔开

                for actor in actors:
                    actor_name = find_name_by_aka(actor)
                    if actor_name:  # 如果找到了对应的 name
                        print(f"[INFO] 更新视频 {video_id}，演员名称: {actor_name}")
                        # 更新数据库，修改该视频的 name 字段
                        # sql = "UPDATE jav_videos SET name = ? WHERE id = ?"
                        # db_edit.execute(sql, (actor_name, video_id))
                        sql = "UPDATE jav_videos SET name = ?, date = ?, title = ? WHERE id = ?"
                        db_edit.execute(sql, (actor_name, movie['issue_date'], movie['title'], video_id))            
                    else:
                        print(f"[INFO] 未找到演员 '{actor}' 对应的 name")
                
                # 如果没有找到对应的演员名称，将 movie['actors_names'] 写入到 actress 列
                if not any(find_name_by_aka(actor) for actor in actors):
                    print(f"[INFO] 没有找到有效的演员名称，更新 actress 列")
                    # sql = "UPDATE jav_videos SET actress = ? WHERE id = ?"
                    # db_edit.execute(sql, (movie['actors_names'], video_id))
                    
                    sql = "UPDATE jav_videos SET actress = ?, date = ?, title = ? WHERE id = ?"
                    db_edit.execute(sql, (movie['actors_names'], movie['issue_date'], movie['title'], video_id))


        else:
            print(f"[INFO] {video_id} 的 actress 列有效，使用原数据")
            # 使用 `actress` 列中的演员信息
            actors = actress.split(' ')  # 假设演员名字之间用空格隔开

            for actor in actors:
                actor_name = find_name_by_aka(actor)
                if actor_name:  # 如果找到了对应的 name
                    print(f"[INFO] 更新视频 {video_id}，演员名称: {actor_name}")
                    # 更新数据库，修改该视频的 name 字段
                    sql = "UPDATE jav_videos SET name = ? WHERE id = ?"
                    db_edit.execute(sql, (actor_name, video_id))
                else:
                    print(f"[INFO] 未找到演员 '{actor}' 对应的 name")

    if if_html_false == 1:
        print("[INFO] HTML 获取失败，正在重新执行更新函数...")
        update_video_names()  # 重新执行
    else:
        print("[INFO] 视频更新完成")



if __name__ == "__main__":
    fetch_and_save_video_ids(url="https://jable.tv/categories/chinese-subtitle", page_start=1, page_end=2)
    update_video_names()



