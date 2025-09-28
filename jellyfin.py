import os
import re
import sys
import requests
import shutil
import time
import yaml
from pathlib import Path


# ------------------ 获取项目根目录 ------------------
SCRIPT_PATH = os.path.realpath(sys.argv[0])
PROJECT_ROOT = os.path.dirname(SCRIPT_PATH)

while not os.path.isdir(os.path.join(PROJECT_ROOT, "cfg")):
    PROJECT_ROOT = os.path.dirname(PROJECT_ROOT)
    if PROJECT_ROOT == "/":
        print("未找到项目根目录（缺少 cfg 文件夹）")
        sys.exit(1)

CONFIG_FILE = os.path.join(PROJECT_ROOT, "cfg", "config.yaml")
from tools.Data_Base_Edit.db_edit import db_edit
from tools.get_id_from_url_jable import update_video_names

# 读取 Jellyfin 配置
with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

JELLYFIN_URL = config.get("Jellyfin")
API_KEY = config.get("Jellyfin_API")
SAVE_SUB = config.get("SavePath_Sub")

SAVE_PATH_REAL = SAVE_SUB

MRGX = "每日更新"
MRGXDSC = "每日更新_待删除"
JXSC = "精选收藏"
HJ = "合集"
MRGX_TMP = os.path.join(SAVE_PATH_REAL, MRGXDSC)

# 获取媒体库 ID
def get_library_id(name):
    response = requests.get(f"{JELLYFIN_URL}/Library/VirtualFolders", headers={
        "X-Emby-Token": API_KEY
    })
    libraries = response.json()
    for library in libraries:
        if library["Name"] == name:
            return library["ItemId"]
    return None

MRGX_ID = get_library_id(MRGX)
MRGXDSC_ID = get_library_id(MRGXDSC)
JXSC_ID = get_library_id(JXSC)
HJ_ID = get_library_id(HJ)

# 获取用户 ID
response = requests.get(f"{JELLYFIN_URL}/Users", headers={
    "X-Emby-Token": API_KEY
})
USER_ID = response.json()[0]["Id"]

# 刷新媒体库
def refresh_library(library_id):
    """
    刷新指定 Jellyfin 媒体库

    参数:
        library_id (str): Jellyfin 库的 ID
    """
    print(f"正在刷新 Jellyfin 媒体库 {library_id}...")
    response = requests.post(
        f"{JELLYFIN_URL}/Library/Refresh",
        headers={"X-Emby-Token": API_KEY},
        params={"Id": library_id}
    )
    if response.status_code == 204:
        print(f"Jellyfin 媒体库 {library_id} 刷新完成！")
    else:
        print(f"[错误] 刷新失败: {response.status_code} {response.text}")


# 移动已观看且未收藏的媒体
def move_watched_unfavorite():
    # print(f"执行移动操作：移动已观看且未收藏的媒体到 {MRGX_TMP}")

    os.makedirs(MRGX_TMP, exist_ok=True)

    params = {
        "Recursive": "true",
        "ParentId": MRGX_ID,
        "fields": "Path,UserData"
    }
    response = requests.get(
        f"{JELLYFIN_URL}/Users/{USER_ID}/Items",
        headers={"X-Emby-Token": API_KEY},
        params=params
    )

    folders_to_delete = [
        item["Path"] for item in response.json()["Items"]
        if item["UserData"]["Played"] and not item["UserData"]["IsFavorite"]
    ]

    for path in folders_to_delete:

        # 取影片所在的目录
        movie_dir = os.path.dirname(path)
        parent_dir = os.path.dirname(movie_dir)

        # print(f"调试: movie_dir = {movie_dir}, parent_dir = {parent_dir}")  # 🟢 调试信息

        # 保护措施：如果目录就是媒体库根目录，直接跳过
        if movie_dir == SAVE_PATH_REAL or parent_dir == SAVE_PATH_REAL:
            print(f"⚠️ 跳过媒体库根目录: {movie_dir}")
            continue

        folder_name = os.path.basename(movie_dir)
        dest = os.path.join(MRGX_TMP, folder_name)

        # 进一步保护：如果文件夹名称中包含敏感关键字，也跳过
        blacklist_keywords = ["000-Movie_SP", "000-JAV", "每日更新"]
        if any(keyword in folder_name for keyword in blacklist_keywords) or \
           any(keyword in os.path.basename(dest) for keyword in blacklist_keywords):
            print(f"⚠️ 跳过含有敏感关键字的目录: {folder_name}")
            continue

        # 如果源目录不存在，跳过
        if not os.path.exists(movie_dir):
            print(f"❌ 源目录不存在，跳过: {movie_dir}")
            continue

        # 如果目标已存在，加时间戳
        if os.path.exists(dest):
            timestamp = int(time.time())
            dest = f"{dest}_{timestamp}"

        print(f"移动文件夹: {movie_dir} -> {dest}")
        shutil.move(movie_dir, dest)

    print("删除操作完成！")


def sync_favorite_status():
    """
    查找 MRGX 媒体库中所有已收藏的项目，通过 path 获取 video_id
    在数据库中将对应 video_id 的 favorite 列设置为 1
    """
    print("开始同步收藏状态...")
    
    # 1. 获取 MRGX 媒体库中所有已收藏的项目
    resp = requests.get(
        f"{JELLYFIN_URL}/Users/{USER_ID}/Items",
        headers={"X-Emby-Token": API_KEY},
        params={"Recursive": "true", "ParentId": MRGX_ID, "Fields": "Path,UserData"}
    )
    
    if resp.status_code != 200:
        print(f"获取收藏项目失败: {resp.status_code} - {resp.text}")
        return
    
    items = resp.json().get("Items", [])
    favorite_items = [item for item in items if item.get("UserData", {}).get("IsFavorite")]
    
    print(f"找到 {len(favorite_items)} 个已收藏项目")
    
    # 2. 提取 video_id
    video_ids = []
    for item in favorite_items:
        path = item.get("Path", "")
        if path:
            # 从路径中提取 video_id（去掉可能的 -C 后缀）
            video_id = Path(path).stem
            if video_id.endswith("-C"):
                video_id = video_id[:-2]
            video_ids.append(video_id)
    
    # 3. 更新数据库 favorite 列为 1
    updated_count = 0
    for video_id in video_ids:
        result = db_edit.execute("UPDATE jav_videos SET favorite = 1 WHERE id = ?", (video_id,))
        if result:
            updated_count += 1
            print(f"已更新: {video_id} -> favorite=1")
        else:
            print(f"未找到或更新失败: {video_id}")
    
    print(f"同步完成！共更新 {updated_count} 条记录")


def adjust_jablesub_watched_status():
    """
    将 jav_videos 表中所有 name = 'Jable_cnSUB', watched = 2, favorite 不为 1 的项（包括NULL），
    将 watched 调整为 3
    """
    print("开始调整 Jable_cnSUB 的 watched 状态...")
    
    # 执行更新操作，处理 favorite 为 NULL 的情况
    result = db_edit.execute(
        "UPDATE jav_videos SET watched = 3 WHERE name = ? AND watched = ? AND (favorite != 1 OR favorite IS NULL)",
        ("Jable_cnSUB", 2)
    )
    
    print(f"调整完成！共更新 {result} 条记录")
    return result


# # 移动已收藏的媒体
# def move_favorites():
#     print(f"执行移动操作：移动已收藏的媒体到 {JXSC_PATH}")
#     os.makedirs(JXSC_PATH, exist_ok=True)

#     params = {
#         "Recursive": "true",
#         "ParentId": MRGX_ID,
#         "fields": "Path,UserData"
#     }
#     response = requests.get(f"{JELLYFIN_URL}/Users/{USER_ID}/Items", headers={
#         "X-Emby-Token": API_KEY
#     }, params=params)
#     folders_to_move = [
#         item["Path"] for item in response.json()["Items"]
#         if item["UserData"]["IsFavorite"]
#     ]

#     for path in folders_to_move:
#         target_dir = os.path.dirname(path)

#         # 保护措施：不要移动媒体库根目录
#         if target_dir == SAVE_PATH_REAL:
#             print(f"⚠️ 跳过媒体库根目录: {target_dir}")
#             continue

#         folder_name = os.path.basename(target_dir)
#         dest = os.path.join(JXSC_PATH, folder_name)

#         print(f"移动文件夹: {target_dir} -> {dest}")
#         # shutil.move(target_dir, dest)

#     print(f"收藏的媒体已成功移动到 {JXSC_PATH}！")


def get_favorite_paths_and_ids():
    """获取每日更新库中已收藏项目的路径和视频ID"""
    resp = requests.get(
        f"{JELLYFIN_URL}/Users/{USER_ID}/Items",
        headers={"X-Emby-Token": API_KEY},
        params={"Recursive": "true", "ParentId": MRGX_ID, "Fields": "Path,UserData"}
    )

    if resp.status_code != 200:
        print(f"获取项目失败: {resp.status_code} - {resp.text}")
        return 0, [], []

    items = resp.json().get("Items", [])
    paths = [item["Path"] for item in items if item.get("UserData", {}).get("IsFavorite")]
    video_ids = [Path(p).stem[:-2] if Path(p).stem.endswith("-C") else Path(p).stem for p in paths]

    return len(paths), paths, video_ids


def filter_favorite_items(paths, video_ids):
    """
    基于 get_favorite_paths_and_ids 的 paths 和 video_ids，
    查询数据库获取 name，跳过 name 为 'Jable_cnSUB' 或未查询到的项
    并将符合条件的记录的 watched 列设置为 2
    返回列表：[{path, video_id, name}, ...]
    """
    result = []
    for path, vid in zip(paths, video_ids):
        row = db_edit.fetch_one("SELECT name FROM jav_videos WHERE id = ?", (vid,))
        if not row:
            print(f"[跳过] 数据库中未找到 video_id={vid}")
            continue

        name = row[0]
        if name == "Jable_cnSUB":
            print(f"[跳过] video_id={vid} name=Jable_cnSUB")
            continue

        # 更新 watched 列
        updated = db_edit.execute("UPDATE jav_videos SET watched = 2 WHERE id = ?", (vid,))
        print(f"[更新] video_id={vid}, name={name}, watched=2, 更新行数={updated}")

        result.append({"path": path, "video_id": vid, "name": name})

    print(f"[结果] 共筛选到 {len(result)} 个有效项目")
    return result

def move_favorite_to_jxsc_merge(items_list, save_path_real, jxsc_folder):
    for item in items_list:
        src_path = Path(item["path"])
        parent_dir = src_path.parent
        name = item["name"]

        dest_dir = Path(save_path_real) / jxsc_folder / name / parent_dir.name
        dest_dir.parent.mkdir(parents=True, exist_ok=True)

        try:
            # 合并文件夹，如果目标已存在则合并
            shutil.copytree(src_path.parent, dest_dir, dirs_exist_ok=True)
            shutil.rmtree(src_path.parent)  # 删除原目录
            print(f"已移动并合并: {src_path.parent} -> {dest_dir}")
        except Exception as e:
            print(f"移动失败: {src_path.parent} -> {dest_dir}, 错误: {e}")

def process_favorites():
    """
    一键处理 Jellyfin 每日更新库的已收藏项目：
    1. 获取已收藏路径和视频 ID
    2. 过滤并更新数据库 watched=2
    3. 移动并合并到精选收藏目录
    """
    total, paths, video_ids = get_favorite_paths_and_ids()
    print(f"总已收藏项目数: {total}")

    items_list = filter_favorite_items(paths, video_ids)
    for item in items_list:
        print(f"{item['path']} -> {item['video_id']} -> {item['name']}")

    move_favorite_to_jxsc_merge(items_list, SAVE_PATH_REAL, JXSC)


def sync_watched_to_jellyfin(library_id=JXSC_ID):
    """
    从数据库中取出 watched=2 的视频 id，
    在指定 Jellyfin 媒体库中查找匹配的文件，
    并将 Jellyfin 标记为已播放，确认成功后再更新数据库 watched=1

    参数:
        library_id: Jellyfin 媒体库 ID，默认为 JXSC_ID

    返回:
        list[dict]: 每个元素包含 {
            "video_id": str,
            "status": str,  # success / skipped / already_played / failed
            "message": str, # 描述信息
        }
    """
    results = []

    # 1. 取出 watched=2 的所有 id (修改这里为 3 )
    rows = db_edit.fetch_all("SELECT id FROM jav_videos WHERE watched = 2")
    ids = [r[0] for r in rows]

    if not ids:
        return results

    # 2. 获取 Jellyfin 精选收藏库的项目
    # resp = requests.get(
    #     f"{JELLYFIN_URL}/Users/{USER_ID}/Items",
    #     headers={"X-Emby-Token": API_KEY},
    #     params={"Recursive": "true", "ParentId": JXSC_ID, "Fields": "Path,UserData"}
    # )
    resp = requests.get(
        f"{JELLYFIN_URL}/Users/{USER_ID}/Items",
        headers={"X-Emby-Token": API_KEY},
        params={"Recursive": "true", "ParentId": library_id, "Fields": "Path,UserData"}
    )

    if resp.status_code != 200:
        results.append({
            "video_id": None,
            "status": "failed",
            "message": f"获取 Jellyfin 精选收藏库失败: {resp.status_code} {resp.text}"
        })
        return results

    jellyfin_items = resp.json().get("Items", [])

    # 3. 遍历 ids，逐个匹配
    for vid in ids:
        matched_item = None
        for item in jellyfin_items:
            jellyfin_path = item.get("Path", "")
            if not jellyfin_path:
                continue
            if vid in Path(jellyfin_path).name:  # 文件名包含该 id
                matched_item = item
                break

        if not matched_item:
            results.append({
                "video_id": vid,
                "status": "skipped",
                "message": "Jellyfin 中未找到匹配文件"
            })
            continue

        item_id = matched_item["Id"]
        jellyfin_path = matched_item["Path"]
        played_status = matched_item.get("UserData", {}).get("Played", False)

        if played_status:
            db_edit.execute("UPDATE jav_videos SET watched = 1 WHERE id = ?", (vid,))
            results.append({
                "video_id": vid,
                "status": "already_played",
                "message": f"已在 Jellyfin 播放过 -> 更新数据库 watched=1 ({jellyfin_path})"
            })
            continue

        # 调用 Jellyfin API 标记为已播放
        mark_resp = requests.post(
            f"{JELLYFIN_URL}/Users/{USER_ID}/PlayedItems/{item_id}",
            headers={"X-Emby-Token": API_KEY}
        )

        if mark_resp.status_code == 204:
            db_edit.execute("UPDATE jav_videos SET watched = 1 WHERE id = ?", (vid,))
            results.append({
                "video_id": vid,
                "status": "success",
                "message": f"已设置 Jellyfin Played 并更新数据库 watched=1 ({jellyfin_path})"
            })
        else:
            results.append({
                "video_id": vid,
                "status": "failed",
                "message": f"设置 Jellyfin Played 失败 -> 状态码={mark_resp.status_code}"
            })

    for r in results:
        vid = r["video_id"]
        print(f"[{r['status'].upper()}] video_id={vid}, {r['message']}")

    # return results

# results = sync_watched_to_jellyfin()
# for r in results:
#     vid = r["video_id"]
#     print(f"[{r['status'].upper()}] video_id={vid}, {r['message']}")

def get_nfo_paths():
    dirs = [
        "/Volumes/SATA_SSD_2T/000-Movie_SP/000-JAV/",
        "/Volumes/NVME_2T/000-Movie_SP/000-JAV/"
    ]
    path_nfo = []
    for d in dirs:
        base = Path(d)
        if base.exists():
            for f in base.rglob("*.nfo"):
                path_nfo.append(str(f))
    return path_nfo

def list_played_items_and_update():
    """
    列出 Jellyfin 所有媒体库中已播放的项目路径（跳过 合集），
    并将对应 video_id 的数据库 watched 字段更新为 2
    """
    results = []

    # 获取所有媒体库
    resp = requests.get(
        f"{JELLYFIN_URL}/Library/VirtualFolders",
        headers={"X-Emby-Token": API_KEY}
    )
    if resp.status_code != 200:
        print(f"获取媒体库失败: {resp.status_code} {resp.text}")
        return results

    libraries = resp.json()
    for lib in libraries:
        lib_name = lib["Name"]
        if lib_name == "合集":   # 跳过合集
            continue

        lib_id = lib["ItemId"]

        params = {"Recursive": "true", "ParentId": lib_id, "Fields": "Path,UserData"}
        items_resp = requests.get(
            f"{JELLYFIN_URL}/Users/{USER_ID}/Items",
            headers={"X-Emby-Token": API_KEY},
            params=params
        )
        if items_resp.status_code != 200:
            print(f"获取库 {lib_name} 失败: {items_resp.status_code}")
            continue

        items = items_resp.json().get("Items", [])
        for item in items:
            if item.get("UserData", {}).get("Played"):
                path = item.get("Path")
                if not path:
                    continue

                # 解析 video_id
                vid = Path(path).stem
                if vid.endswith("-C"):
                    vid = vid[:-2]

                # 更新数据库 watched=2
                updated = db_edit.execute("UPDATE jav_videos SET watched = 2 WHERE id = ?", (vid,))
                status = "更新成功" if updated else "未找到匹配记录"

                results.append({"library": lib_name, "path": path, "video_id": vid, "db_status": status})
                print(f"[已播放] {lib_name}: {path} -> video_id={vid}, {status}")

    print(f"\n共找到 {len(results)} 个已播放项目（不含 合集）")
    return results

# def check_nfo_files(path_nfo_list):
#     not_match = []
#     not_avbase = []

#     for path in path_nfo_list:
#         p = Path(path)
#         video_id = p.parent.name  # 上一级目录名

#         try:
#             content = p.read_text(encoding="utf-8", errors="ignore")
#         except Exception as e:
#             print(f"读取失败 {p}: {e}")
#             continue

#         # 提取 <title> 和 <metatubeid>
#         title_match = re.search(r"<title>(.*?)</title>", content, re.S | re.I)
#         metatubeid_match = re.search(r"<metatubeid>(.*?)</metatubeid>", content, re.S | re.I)

#         title = title_match.group(1).strip() if title_match else ""
#         metatubeid = metatubeid_match.group(1).strip() if metatubeid_match else ""

#     # 打印 not_match
#     print("\n=== not_match (metatubeid 不含 video_id) ===")
#     delete_targets = []
#     for p, mid in not_match:
#         print(f"{p} | metatubeid: {mid}")
#         parent = p.parent
#         candidates = list(parent.glob("*.nfo")) + list(parent.glob("*.jpg"))
#         if candidates:
#             print("  将删除以下文件：")
#             for c in candidates:
#                 print(f"    {c}")
#             delete_targets.extend(candidates)
#     print(f"共 {len(not_match)} 个\n")

#     # 确认删除
#     if delete_targets:
#         confirm = input("确认要删除以上文件吗？(y/n): ").strip().lower()
#         if confirm == "y":
#             for c in delete_targets:
#                 try:
#                     c.unlink()
#                     print(f"已删除 {c}")
#                 except Exception as e:
#                     print(f"删除失败 {c}: {e}")
#         else:
#             print("取消删除。")

#     return not_match, not_avbase

def check_nfo_files(path_nfo_list):
    not_match = []
    not_avbase = []

    # 需要检查的必需文件
    required_files = ["backdrop.jpg", "folder.jpg", "landscape.jpg", "movie.nfo"]

    # 缺少文件的统计结果
    missing_report = []

    for path in path_nfo_list:
        p = Path(path)
        video_id = p.parent.name  # 上一级目录名

        try:
            content = p.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            print(f"读取失败 {p}: {e}")
            continue

        # 提取 <title> 和 <metatubeid>
        title_match = re.search(r"<title>(.*?)</title>", content, re.S | re.I)
        metatubeid_match = re.search(r"<metatubeid>(.*?)</metatubeid>", content, re.S | re.I)

        title = title_match.group(1).strip() if title_match else ""
        metatubeid = metatubeid_match.group(1).strip() if metatubeid_match else ""

        # 检查 title 是否包含 video_id（不分大小写）
        if title and video_id.lower() not in title.lower():
            not_match.append((p, title))


        # ===== 新增：统计父目录文件完整性 =====
        parent = p.parent
        missing = []

        for f in required_files:
            if not (parent / f).exists():
                missing.append(f)

        if not list(parent.glob("*.mp4")):
            missing.append("*.mp4")

        if missing:
            missing_report.append((parent, missing))

    # 打印 not_match
    print("\n=== not_match (title 不含 video_id) ===")
    delete_targets = []
    for p, mid in not_match:
        print(f"{p} | metatubeid: {mid}")
        parent = p.parent
        candidates = list(parent.glob("*.nfo")) + list(parent.glob("*.jpg"))
        if candidates:
            print("  将删除以下文件：")
            for c in candidates:
                print(f"    {c}")
            delete_targets.extend(candidates)
    print(f"共 {len(not_match)} 个\n")

    # 打印缺少文件情况（只是统计，不删除）
    print("=== 缺少文件统计 ===")
    for parent, missing in missing_report:
        print(f"{parent} 缺少: {', '.join(missing)}")
    print(f"共 {len(missing_report)} 个目录缺少必要文件\n")

    # 确认删除（逻辑保持不变）
    if delete_targets:
        confirm = input("确认要删除以上文件吗？(y/n): ").strip().lower()
        if confirm == "y":
            for c in delete_targets:
                try:
                    c.unlink()
                    print(f"已删除 {c}")
                except Exception as e:
                    print(f"删除失败 {c}: {e}")
        else:
            print("取消删除。")

    return not_match, not_avbase, missing_report

def delete_nfo_and_jpg():
    dirs = [
        "/Volumes/NVME_2T/000-Movie_SP",
        "/Volumes/SATA_SSD_2T/000-Movie_SP"
    ]
    exts = {".nfo", ".jpg"}
    deleted = []

    for d in dirs:
        base = Path(d)
        if base.exists():
            for f in base.rglob("*"):
                if f.suffix.lower() in exts and f.is_file():
                    deleted.append(str(f))
                    f.unlink()

    print(f"共删除 {len(deleted)} 个文件")
    for f in deleted:
        print(f"删除: {f}")

# adjust_watched_status()

# 主入口：支持参数或交互
def main(action=None):
    if action is None:
        print("请选择操作:")
        print("1) [每日更新]移动已观看且未收藏的媒体")
        print("2) [每日更新]同步收藏状态到数据库")
        print("3) [每日更新]移动已收藏的媒体到[精选收藏]")
        print("4) [精选收藏]、[每日更新]的媒体设置为已播放[watched=2]")
        print("5) 将所有已播放的媒体，记录到数据库[watched=2]")
        print("6) 统计不符合规则的nfo")
        print("7) 清空所有.nfo .jpg")
        action = input("请输入: ")

    if action == "1":
        move_watched_unfavorite()
    elif action == "2":
        sync_favorite_status()
        time.sleep(2)
        adjust_jablesub_watched_status()
    elif action == "3":
        update_video_names()
        process_favorites()
    elif action == "4":
        refresh_library(JXSC_ID)
        refresh_library(MRGX_ID)
        print("等待 10 秒让 Jellyfin 完成刷新 ...")
        time.sleep(10)
        sync_watched_to_jellyfin(JXSC_ID)
        sync_watched_to_jellyfin(MRGX_ID)
    elif action == "5":
        list_played_items_and_update()
    elif action == "6":
        nfo_files = get_nfo_paths()
        print(f"共找到 {len(nfo_files)} 个 nfo 文件")
        not_match, not_avbase, missing_report = check_nfo_files(nfo_files)
    elif action == "7":
        delete_nfo_and_jpg()
    else:
        print(f"无效选项: {action}")
        sys.exit(1)

    refresh_library(MRGX_ID)
    refresh_library(MRGXDSC)
    refresh_library(JXSC_ID)

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
