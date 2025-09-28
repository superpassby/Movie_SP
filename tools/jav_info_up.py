import sqlite3
import yaml
import subprocess
import sys
from pathlib import Path
from datetime import datetime, timedelta
import concurrent.futures
import threading

# ------------------ 动态添加项目根目录 ------------------
CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = next(p for p in CURRENT_FILE.parents if (p / "cfg").exists())

# 将项目根目录加入 sys.path，这样可以直接 import 根目录下的模块
sys.path.insert(0, str(PROJECT_ROOT))

# 现在可以直接 import switch_clash
from switch_clash import switch_clash_group
from tools.jav_link_fetch.video_fetch_Jable import get_video_info_jable
from tools.jav_link_fetch.video_fetch_MissAV import get_video_info_missav
from tools.Data_Base_Edit.db_edit import db_edit

# 构造数据库路径
db_path = PROJECT_ROOT / 'db' / 'data.db'
cfg_path = PROJECT_ROOT / 'cfg' / 'config.yaml'
SOURCE_PATH = PROJECT_ROOT / "cfg" / "source.yaml"

MAX_WORKERS = 3

# def update_proxy():
#     test_group = "自定义代理"
#     test_filter = "|"
#     test_url_key = "jable"
#     switch_clash_group(test_group, test_filter, test_url_key)

def update_proxy():
    test_group = "自定义代理"
    test_filter = "NB|"
    test_url_key = "jable"
    switch_clash_group(test_group, test_filter, test_url_key)



# # 读取 actresses 表内容
# def list_actresses(db_path):
#     conn = sqlite3.connect(db_path)
#     conn.row_factory = sqlite3.Row
#     cursor = conn.cursor()

#     cursor.execute("SELECT name, filter FROM actresses")
#     for row in cursor.fetchall():
#         print(f"Name: {row['name']}, Filter: {row['filter']}")

#     conn.close()


def apply_filters(jav_videos, actress, filter_rule, enable_scan, download_mode=False):
    if enable_scan == 0:
        return []

    filter_rule = filter_rule or ''
    date_min = None
    date_max = None
    keywords = []

    for part in filter_rule.split('|'):
        part = part.strip()
        if part.startswith('>'):
            date_min = datetime.strptime(part[1:].strip(), "%Y.%m.%d")
        elif part.startswith('<'):
            date_max = datetime.strptime(part[1:].strip(), "%Y.%m.%d")
        else:
            if part:
                keywords.append(part)

    filtered_videos = []
    for video in jav_videos:
        if video['name'] != actress:
            continue

        # 根据 download_mode 决定过滤状态
        if download_mode:
            excluded_states = ["skip", "out_number", "download", "no_res", "wait"]
        else:
            excluded_states = ["skip", "out_number"]

        if video['chinese_sub'] == 1 or video['state'] in excluded_states:
            continue

        if video['date'] is not None:
            video_date = datetime.strptime(video['date'], "%Y.%m.%d")
            if (date_min and video_date < date_min) or (date_max and video_date > date_max):
                continue

        if any(keyword in video['id'] or keyword in (video['title'] or "") for keyword in keywords):
            continue

        filtered_videos.append(video)

    return filtered_videos


def list_jav_videos(db_path, target_actresses=None, download_mode=False, refresh_mode=False):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT id, name, date, title, chinese_sub, state FROM jav_videos")
    jav_videos = cursor.fetchall()

    ## - - - - 从数据库获取
    # cursor.execute("SELECT name, filter, enable_scan FROM actresses")
    # actresses = cursor.fetchall()

    ## - - - - 从 yaml 获取
    with open(SOURCE_PATH, 'r', encoding='utf-8') as f:
        source_config = yaml.safe_load(f)

    # 替换原来的数据库查询，使用 source.yaml 的数据
    actresses = [{'name': row['Name'], 'filter': row['Filter'], 'enable_scan': row['Enable_Scan']} for row in source_config]

    all_filtered_videos = []

    for actress_row in actresses:
        actress = actress_row['name']
        if target_actresses is not None and actress not in target_actresses:
            continue

        filter_rule = actress_row['filter']

        # 如果 refresh_mode，则替换 filter
        if refresh_mode:
            # three_months_ago = datetime.now() - timedelta(days=90)  # 近似3个月
            three_months_ago = datetime.now() - timedelta(days=90000)  # 近似3个月

            filter_rule = f"VR | > {three_months_ago.strftime('%Y.%m.%d')}"

        enable_scan = actress_row['enable_scan'] or 0
        filtered_videos = apply_filters(jav_videos, actress, filter_rule, enable_scan, download_mode)

        print(f"Filtered Videos for {actress}:")
        for video in filtered_videos:
            print(f"ID: {video['id']}, Actress: {video['name']}, Date: {video['date']}")

        all_filtered_videos.extend(filtered_videos)

    conn.close()
    return all_filtered_videos

# 读取配置文件中的视频数据源
def video_fetch(cfg_path):
    with open(cfg_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    video_data_sources = config.get('JAV_Video_DataSources', [])
    print("JAV_Video_DataSources 配置:")
    for source in video_data_sources:
        print(source)

    return video_data_sources


def fetch_m3u8_by_sources(video_id: str, video_data_sources: list):
    """
    按 video_data_sources 中 order 顺序获取 m3u8_url 和 chinese_sub
    如果某个数据源返回 "false"，立即返回 "false" 并停止尝试其他数据源
    如果某个数据源返回有效 URL，立即返回该 URL
    如果所有数据源都返回 "404"，返回 "404"
    """
    sources_sorted = sorted(video_data_sources, key=lambda s: s.get('order', 0))

    # 默认返回值（如果所有 source 都返回 404）
    m3u8_url_final = "404"
    chinese_sub_final = ""
    source_name_final = ""

    for source in sources_sorted:
        order = source.get('order', 0)
        if order == 0:
            continue  # 跳过 order=0

        source_name = source.get('name', '')
        name_lower = source_name.lower()

        try:
            if name_lower == "jable":
                m3u8_url_temp, chinese_sub_temp = get_video_info_jable(video_id)
            elif name_lower == "missav":
                m3u8_url_temp, chinese_sub_temp = get_video_info_missav(video_id)
            else:
                print(f"[WARN] Unknown video source: {source_name}")
                continue

            chinese_sub_temp = int(chinese_sub_temp) if chinese_sub_temp else 0

            if m3u8_url_temp == "false":
                # 遇到 false，立即退出，不尝试其他数据源
                update_proxy()
                return "false", "", ""
            elif m3u8_url_temp not in ["404", None]:
                # 成功获取
                return m3u8_url_temp, chinese_sub_temp, source_name
            # 如果是 "404"，继续尝试下一个 source

        except Exception as e:
            print(f"[ERROR] Error fetching from {source_name} for {video_id}: {e}")
            continue

    # 所有 source 都返回 404
    return "404", "", ""

# def fetch_m3u8_parallel(filtered_videos: list, video_data_sources: list):
#     """
#     并行获取 filtered_videos 中所有 video 的 m3u8_url 和 chinese_sub
#     :param filtered_videos: list of dict, 每个 dict 包含 'id'
#     :param video_data_sources: 数据源列表
#     :return: list of dict, 每个 dict 包含 ID, m3u8_url, chinese_sub, source_name
#     """
#     results = []
#     has_false = False
#     has_false_lock = threading.Lock()  # 线程锁，用于同步对 has_false 的修改

#     # 按 ID 字典序排序
#     sorted_videos = sorted(filtered_videos, key=lambda v: v['id'])

#     def task(video_id: str):
#         m3u8_url, chinese_sub, source_name = fetch_m3u8_by_sources(video_id, video_data_sources)
#         return {"ID": video_id, "m3u8_url": m3u8_url, "chinese_sub": chinese_sub, "source_name": source_name}

#     # 使用线程池并行处理
#     with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
#         future_to_id = {executor.submit(task, video['id']): video['id'] for video in sorted_videos}
#         total = len(future_to_id)          # <<< 新增：总任务数
#         completed = 0                      # <<< 新增：已完成数

#         for future in concurrent.futures.as_completed(future_to_id):
#             vid_id = future_to_id[future]
#             try:
#                 result = future.result()
#                 results.append(result)

#                 if result["m3u8_url"] == "false":
#                     with has_false_lock:
#                         if not has_false:
#                             has_false = True
#                     print(f"[Check] hs_false: {has_false}")

#                 completed += 1  # <<< 每完成一个任务 +1
#                 print(f"[{completed}/{total}] DONE ID {vid_id}: {result}")  # <<< 修改输出行

#             except Exception as e:
#                 print(f"[ERROR] ID {vid_id} fetch failed: {e}")
#                 results.append({"ID": vid_id, "m3u8_url": "false", "chinese_sub": "", "source_name": ""})
#                 with has_false_lock:
#                     if not has_false:
#                         has_false = True

#     # 调用 write_to_db 函数进行数据库写入
#     write_to_db(results)

#     return has_false

def fetch_m3u8_parallel(filtered_videos: list, video_data_sources: list):
    """
    并行获取 filtered_videos 中所有 video 的 m3u8_url 和 chinese_sub
    :param filtered_videos: list of dict, 每个 dict 包含 'id'
    :param video_data_sources: 数据源列表
    :return: list of dict, 每个 dict 包含 ID, m3u8_url, chinese_sub, source_name
    """
    results = []
    has_false = False
    has_false_lock = threading.Lock()  # 线程锁，用于同步对 has_false 的修改

    # 按 ID 字典序排序
    sorted_videos = sorted(filtered_videos, key=lambda v: v['id'])

    def task(video_id: str):
        m3u8_url, chinese_sub, source_name = fetch_m3u8_by_sources(video_id, video_data_sources)
        return {"ID": video_id, "m3u8_url": m3u8_url, "chinese_sub": chinese_sub, "source_name": source_name}

    # 使用线程池并行处理
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_id = {executor.submit(task, video['id']): video['id'] for video in sorted_videos}
        total = len(future_to_id)          # 总任务数
        completed = 0                      # 已完成数
        completed_count = 0                # 每次写入数据库时，计数已完成的任务数量

        for future in concurrent.futures.as_completed(future_to_id):
            vid_id = future_to_id[future]
            try:
                result = future.result()
                results.append(result)

                if result["m3u8_url"] == "false":
                    with has_false_lock:
                        if not has_false:
                            has_false = True
                    print(f"[Check] hs_false: {has_false}")

                completed += 1  # 每完成一个任务 +1
                completed_count += 1  # 计数已完成的任务

                print(f"[{completed}/{total}] DONE ID {vid_id}: {result}")  # 输出完成情况

                # 每完成20个任务，就写入一次数据库
                if completed_count >= 20:
                    write_to_db(results)
                    results.clear()  # 清空已写入的结果
                    completed_count = 0  # 重置计数器

            except Exception as e:
                print(f"[ERROR] ID {vid_id} fetch failed: {e}")
                results.append({"ID": vid_id, "m3u8_url": "false", "chinese_sub": "", "source_name": ""})
                with has_false_lock:
                    if not has_false:
                        has_false = True

    # 如果还有剩余的结果未写入数据库，则写入
    if results:
        write_to_db(results)

    return has_false

def write_to_db(results):
    """
    将 m3u8_url 和 chinese_sub 写入数据库
    :param results: 每个视频的结果列表，包含 ID, m3u8_url, chinese_sub, source_name
    """

    for r in results:
        vid_id = r["ID"]
        m3u8_url = r["m3u8_url"]
        chinese_sub_new = r["chinese_sub"]
        source_name = r["source_name"]

        if m3u8_url == "404":
            # 情况 1：无资源
            db_edit.execute(
                "UPDATE jav_videos SET state = 'no_res' WHERE id = ?",
                (vid_id,)
            )

        elif m3u8_url and m3u8_url not in ("false", "404"):
            # 情况 2：正常 m3u8 链接
            row = db_edit.fetch_one(
                "SELECT state, chinese_sub FROM jav_videos WHERE id = ?",
                (vid_id,)
            )

            if not row:
                continue  # 没有记录，跳过

            state_old, chinese_sub_old = row

            # 判断 state 是否要改
            # ============ 新增判断 ============ 
            if state_old in (None, "", " "):  # 原来为空或 NULL
               new_state = "wait"
            elif state_old == "download" and chinese_sub_old == 0 and chinese_sub_new == 1:
                new_state = "new"
            else:
                new_state = state_old
            # =================================

            print(f"[DB WRITE] ID={vid_id}, m3u8='{m3u8_url}', chinese_sub={chinese_sub_new}, "
                  f"source_name='{source_name}', state='{new_state}'")

            db_edit.execute(
                "UPDATE jav_videos SET chinese_sub = ?, m3u8 = ?, m3u8_source = ?, state = ? WHERE id = ?",
                (chinese_sub_new, m3u8_url, source_name, new_state, vid_id)
            )

    print(f"[DB] 已处理 {len(results)} 条记录")

# ==================== 测试 main ====================
if __name__ == "__main__":
    
    args = sys.argv[1:]

    # 判断是否有 download_mode 和 refresh_mode
    download_mode = "download_mode" in args
    refresh_mode = "refresh_mode" in args

    # 过滤掉模式参数，剩下的作为指定演员列表
    target_actresses = [a for a in args if a not in ["download_mode", "refresh_mode"]]
    if not target_actresses:
        target_actresses = None  # 这里是关键    
    
    
    
    
    # 假设已经有 filtered_videos 和 video_data_sources
    filtered_videos = list_jav_videos(db_path, target_actresses, download_mode, refresh_mode)
    video_data_sources = video_fetch(cfg_path)

    has_false = fetch_m3u8_parallel(filtered_videos, video_data_sources)
    sys.exit(1 if has_false else 0)
    