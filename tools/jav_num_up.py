#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
from pathlib import Path
import datetime
import subprocess
import requests
from collections import deque
import yaml
import datetime
import time

# ------------------ 动态添加项目根目录 ------------------

CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = next(p for p in CURRENT_FILE.parents if (p / "cfg").exists())

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DB_PATH = PROJECT_ROOT / "db" / "data.db"
CFG_PATH = PROJECT_ROOT / "cfg" / "config.yaml"
SOURCE_PATH = PROJECT_ROOT / "cfg" / "source.yaml"

# ------------------ 导入数据源脚本 ------------------
from tools.jav_data_fetch import data_AvBase  # 默认用 AvBase（enable=1 且第一个）
from tools.Data_Base_Edit.db_edit import db_edit
from tools.jav_data_fetch import data_AvBase
from switch_clash import switch_clash_group # 导入 switch_clash_group 函数

# ---------- 确保表存在 ----------
def ensure_table():
    """
    确保 jav_videos 表存在
    """
    sql = """
    CREATE TABLE IF NOT EXISTS jav_videos (
        name TEXT,
        date TEXT,
        id TEXT PRIMARY KEY,
        actress_name TEXT,
        actress_count INTEGER,
        chinese_sub INTEGER,
        state TEXT,
        favorite INTEGER,
        watched INTEGER,
        m3u8 TEXT,
        m3u8_source TEXT,
        title TEXT
    )
    """
    db_edit.execute(sql)
    print("[INFO] 表 jav_videos 已确保存在")

def clear_flag(SOURCE_PATH, keyword=None):
    """
    清除 source.yaml 中所有包含指定关键词的行
    :param SOURCE_PATH: yaml 文件路径
    :param keyword: 需要匹配的关键词，必须提供
    """
    if not keyword:
        print(f"[WARN] 未提供 keyword，函数未执行")
        return

    try:
        with open(SOURCE_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # 删除包含 keyword 的行
        new_lines = [line for line in lines if keyword not in line]

        # 写回文件
        with open(SOURCE_PATH, "w", encoding="utf-8") as f:
            f.writelines(new_lines)

        print(f"[INFO] 清除了所有包含关键词 '{keyword}' 的行")

    except Exception as e:
        print(f"[ERROR] 清除行失败: {e}")


# def get_enabled_actresses():
#     """
#     获取需要扫描的演员列表
#     :return: [{ "name": ..., "only_scan_first_page": ... }, ...]
#     """
#     sql = """
#     SELECT name, only_scan_first_page, max_actress_count
#     FROM actresses
#     WHERE enable_scan = 1
#     """
#     rows = db_edit.fetch_all(sql)
#     # 转成字典列表返回
#     result = [{"name": row[0], "only_scan_first_page": row[1], "max_actress_count": row[2]} for row in rows]
#     return result

## 增加过滤逻辑
def get_enabled_actresses():
    """
    获取需要扫描的演员列表
    :return: [{ "name": ..., "only_scan_first_page": ... }, ...]
    """
    sql = """
    SELECT name, only_scan_first_page, max_actress_count
    FROM actresses
    WHERE enable_scan = 1
    """
    rows = db_edit.fetch_all(sql)
    
    # 需要过滤的name列表
    filter_names = {"Jable_cnSUB", "Jable_cnSUB1", "Jable_cnSUB2"}
    
    # 转成字典列表返回，过滤掉指定名称
    result = [{"name": row[0], "only_scan_first_page": row[1], "max_actress_count": row[2]} 
              for row in rows if row[0] not in filter_names]
    return result

def save_video_to_db(name, video, max_actress_count):
    """
    将单个视频信息写入数据库
    :param name: 演员名字
    :param video: 视频信息 dict
    :param max_actress_count: 超过演员数量时设置 state 为 out_number
    """
    vid = video.get("work_id")
    state_val = None
    if max_actress_count and video.get("actors_count") and video["actors_count"] > max_actress_count:
        state_val = "out_number"

    # 查询是否已存在，并获取当前 state
    sql_check = "SELECT id, state FROM jav_videos WHERE id=?"
    existing = db_edit.fetch_one(sql_check, (vid,))

    if existing:
        existing_state = existing[1]
        # 如果原 state 是 download 或 no_res 或 skip，则保持原值
        if existing_state in ("download", "no_res", "skip"):
            state_val = existing_state

        sql_update = """
        UPDATE jav_videos
        SET name=?, date=?, title=?, actress_count=?, state=?
        WHERE id=?
        """
        db_edit.execute(sql_update, (
            name,
            video.get("issue_date"),
            video.get("title"),
            video.get("actors_count"),
            state_val,
            vid
        ))
    else:
        sql_insert = """
        INSERT INTO jav_videos
        (id, name, title, date, actress_count, state)
        VALUES (?, ?, ?, ?, ?, ?)
        """
        db_edit.execute(sql_insert, (
            vid,
            name,
            video.get("title"),
            video.get("issue_date"),
            video.get("actors_count"),
            state_val
        ))

    print(f"[INFO] 写入 {vid} - {video.get('title')}")

def write_actor_info_to_db(name, actor_info):
    """
    将演员信息写入 actresses 表
    :param name: 演员姓名
    :param actor_info: dict，包括 aka, birthday, height, bust, waist, hip, cup
    """
    if not actor_info:
        print(f"[WARN] 没有提供 {name} 的演员信息，跳过写入")
        return

    sql_update_actor = """
    UPDATE actresses
    SET aka = ?, birthday = ?, height = ?, bust = ?, waist = ?, hip = ?, cup = ?
    WHERE name = ?
    """
    db_edit.execute(sql_update_actor, (
        actor_info.get("aka", ""),
        actor_info.get("birthday", ""),
        actor_info.get("height", ""),
        actor_info.get("bust", ""),
        actor_info.get("waist", ""),
        actor_info.get("hip", ""),
        actor_info.get("cup", ""),
        name
    ))
    print(f"[INFO] 演员 {name} 信息已写入数据库")

def update_yaml_fetch_state(actress_name, fetch_state_msg, page):

    import datetime
    import re

    # 如果 Name 是 "Jable_cnSUB"，直接跳过该块
    if actress_name == "Jable_cnSUB":
        print(f"[INFO] 跳过处理演员: {actress_name}")
        return

    with open(SOURCE_PATH, "r", encoding="utf-8") as f:
        lines = f.readlines()

    new_lines = []
    inside_block = False
    has_success = "success" in fetch_state_msg.lower()

    for i, line in enumerate(lines):
        stripped = line.strip()

        # 检测是否进入目标演员块
        if stripped == f"- Name: {actress_name}":
            inside_block = True
            new_lines.append(line)
            # 插入新的 Fetch_State，替换原有的或新增
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            new_lines.append(f'  Last_Page: "{page}"\n')
            new_lines.append(f'  Fetch_State: "{fetch_state_msg} | {timestamp}"\n')
            continue

        # 在演员块内时处理 Only_Scan_First_Page
        if inside_block:
            # 如果遇到下一块，结束当前块
            if stripped.startswith("- Name:") and stripped != f"- Name: {actress_name}":
                inside_block = False

            # 修改 Only_Scan_First_Page
            if has_success:
                m = re.match(r'(\s*)Only_Scan_First_Page:\s*(\d+)', line)
                if m and m.group(2) == "0":
                    indent = m.group(1)
                    line = f"{indent}Only_Scan_First_Page: 1\n"

            # 如果原行是旧的 Fetch_State，就跳过
            # if stripped.startswith("Fetch_State:"):
            if stripped.startswith("Fetch_State:") or stripped.startswith("Last_Page:"):
                continue

        new_lines.append(line)

    with open(SOURCE_PATH, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

def process_actress(name, only_scan_first_page, max_actress_count, page=None):
    """
    抓取演员的视频信息并写入数据库，支持 last_max_N 机制
    """
    # 最小修改：如果未传入 page，则从 1 开始
    if page is None:
        page = 1


    last_max_N = None  # 记录上一次成功获取的最大页数

    while True:
        try:
            data = data_AvBase.fetch_actor_data(name, page)
            if not data:
                msg = f"Failed | {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} 获取第 {page} 页返回 None"
                update_yaml_fetch_state(name, msg, Last_Page=page-1)
                print(f"[ERROR] {msg}")
                break
            works = data.get("works_info", [])
            max_N = data.get("max_page", None)

            # ---------- page=1 时写入 actor_info ----------
            if page == 1:
                actor_info = data.get("actor_info", {})
                write_actor_info_to_db(name, actor_info)

            # 检查是否只抓取第一页
            if only_scan_first_page == 1:
                msg = f"Success | {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} 第 {page} 页抓取正常，任务正常结束"
                update_yaml_fetch_state(name, msg, page)
                print(f"[INFO] {msg}")
                # break  # 结束任务

            if works:
                last_max_N = max_N
            else:
                if last_max_N and (not max_N or page > max_N):
                    max_N = last_max_N
                if page == last_max_N:
                    msg = f"Success | {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} 第 {page} 页抓取异常，但等于最大页 {last_max_N}，任务正常结束"
                    update_yaml_fetch_state(name, msg, page)
                    print(f"[INFO] {msg}")
                    break
                msg = f"Failed | {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} 获取第 {page} 页失败, 已知有 {max_N or '?'} 页"
                update_yaml_fetch_state(name, msg, page)
                print(f"[WARN] {msg}")
                break

            # 写入视频信息
            for w in works:
                save_video_to_db(name, w, max_actress_count)

        except Exception as e:
            if page == last_max_N:
                msg = f"Success | {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} 第 {page} 页抓取异常，但等于最大页 {last_max_N}，任务正常结束"
                update_yaml_fetch_state(name, msg, page)
                print(f"[INFO] {msg}")
                break
            # msg = f"Failed | {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} 获取第 {page} 页失败: {e}"
            error_msg = str(e).replace('\n', ' ').replace('"', "'").replace(':', ';')
            msg = f"Failed | {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} 获取第 {page} 页失败: {error_msg}"

            
            update_yaml_fetch_state(name, msg, page)
            print(f"[ERROR] {msg}")
            break

        # 翻页逻辑
        if only_scan_first_page or (max_N and page >= max_N):
            break
        page += 1

def main():
    import time
    ensure_table()

    clear_flag(SOURCE_PATH, 'Fetch_State: "Success')
    clear_flag(SOURCE_PATH, 'Fetch_State: "Failed')
    clear_flag(SOURCE_PATH, 'Last_Page')
    
    # ---------- 首次抓取所有启用演员 ----------
    actresses = get_enabled_actresses()
    for a in actresses:
        try:
            print(f"[INFO] 首次抓取: {a['name']} 从第 1 页")
            process_actress(
                name=a["name"],
                only_scan_first_page=a["only_scan_first_page"],
                max_actress_count=a["max_actress_count"],
                page=1
            )
        except Exception as e:
            print(f"[ERROR] 处理 {a['name']} 失败: {e}")
        time.sleep(1)  # 可选，避免频繁请求

    # ---------- 循环处理失败演员 ----------
    while True:
        # 读取 SOURCE_PATH
        with open(SOURCE_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or []


        # 构造失败演员列表
        failed_actors = []
        for item in data:
            name = item.get("Name", "")
            fetch_state = item.get("Fetch_State", "")
            Last_Page = item.get("Last_Page")
            if "Success" not in fetch_state:
                page = int(Last_Page) if Last_Page else 1
                failed_actors.append({
                    "name": name,
                    "page": page,
                    "only_scan_first_page": item.get("Only_Scan_First_Page", 0),
                    "max_actress_count": item.get("Max_Actress_Count", None)
                })

        if not failed_actors:
            break  # 所有演员都成功

        # 处理失败演员
        for a in failed_actors:
            print(f"[INFO] 开始处理: {a['name']} 从第 {a['page']} 页")
            try:
                process_actress(
                    name=a["name"],
                    only_scan_first_page=a["only_scan_first_page"],
                    max_actress_count=a["max_actress_count"],
                    page=a["page"]
                )
            except Exception as e:
                print(f"[ERROR] 处理 {a['name']} 失败: {e}")
            time.sleep(1)  # 可选，避免频繁请求

        # 检查启用演员是否全部成功
        enabled_actresses = get_enabled_actresses()
        all_success = True
        for ea in enabled_actresses:
            item = next((it for it in data if it.get("Name") == ea["name"]), None)
            if item:
                fetch_state = item.get("Fetch_State", "")
                if "Success" not in fetch_state:
                    all_success = False
                    break
        if all_success:
            break

    print("[INFO] 所有启用演员抓取完成！")

if __name__ == "__main__":
    main()

