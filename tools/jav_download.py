import sqlite3
import yaml
from pathlib import Path
from datetime import datetime
import subprocess
import sys

# ------------------ 动态添加项目根目录 ------------------
CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = next(p for p in CURRENT_FILE.parents if (p / "cfg").exists())

# ------------------ 配置文件路径 ------------------
cfg_path = PROJECT_ROOT / 'cfg' / 'config.yaml'
db_path = PROJECT_ROOT / 'db' / 'data.db'

# ------------------ 锁文件 ------------------
LOCK_FILE = PROJECT_ROOT / 'work'

# ------------------ 文件锁开关 ------------------
# ENABLE_LOCK = True  # True 表示启用锁文件，False 表示禁用
ENABLE_LOCK = False  # True 表示启用锁文件，False 表示禁用

# 现在可以直接 import switch_clash
sys.path.insert(0, str(PROJECT_ROOT))
from switch_clash import switch_clash_group
from tools.jav_link_fetch.video_fetch_Jable import get_video_info_jable
from tools.jav_link_fetch.video_fetch_MissAV import get_video_info_missav
from tools.Data_Base_Edit.db_edit import db_edit


def create_lock_file():
    if not ENABLE_LOCK:
        return
    if LOCK_FILE.exists():
        print("存在锁文件，请检查。")
        sys.exit(0)
    LOCK_FILE.touch()
    print("锁文件 'work' 已创建。")


def delete_lock_file():
    if not ENABLE_LOCK:
        return
    if LOCK_FILE.exists():
        LOCK_FILE.unlink()
        print("锁文件 'work' 已删除。")

# ------------------ 加载配置 ------------------
def load_config():
    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    print("\nConfig from config.yaml:")
    for key in ["SavePath_Sub", "SavePath_noSub", "SavePath_rou_video", "Proxy_Download", "IsNeedDownloadProxy", "Downloader"]:
        print(f"{key}: {cfg.get(key)}")
    return cfg

def load_sources():
    import sqlite3

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT name, enable_download, filter FROM actresses")
    rows = cursor.fetchall()

    sources = []
    print("\nActors from database (namees table):")
    for row in rows:
        name, enable_download, filter_rule = row
        sources.append({
            "Name": name,
            "Enable_Download": enable_download,
            "Filter": filter_rule
        })
        print({
            "Name": name,
            "Enable_Download": enable_download,
            "Filter": filter_rule
        })

    conn.close()
    return sources


def video_fetch(cfg_path):
    with open(cfg_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    video_data_sources = config.get('JAV_Video_DataSources', [])
    print("\nJAV_Video_DataSources 配置:")
    for source in video_data_sources:
        print(source)
    
    return video_data_sources

# ------------------ 解析 Filter ------------------
def parse_filter(filter):
    if filter is None:        # <-- 新增这一行
        filter = ""           # 避免 NoneType 错误
    date_min, date_max = None, None
    keywords = []

    for part in filter.split("|"):
        part = part.strip()
        if part.startswith(">"):
            date_min = datetime.strptime(part[1:].strip(), "%Y.%m.%d")
        elif part.startswith("<"):
            date_max = datetime.strptime(part[1:].strip(), "%Y.%m.%d")
        elif part:
            keywords.append(part)
    return date_min, date_max, keywords

# ------------------ 过滤视频 ------------------
# def filter_videos():
def filter_videos(target_actresses=None):
    sources = load_sources()

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, date, title, chinese_sub, state, m3u8 FROM jav_videos")
    videos = cursor.fetchall()
    print(f"\nTotal videos in DB: {len(videos)}")

    filtered_videos = []

    for s in sources:
        name = s["Name"]
        enable_download = s.get("Enable_Download", 1)
        filter_rule = s.get("Filter", "")  # 避免使用 Python 保留字 filter

        # <<< 新增逻辑：指定演员时，只处理这些
        if target_actresses is not None:
            if name not in target_actresses:
                continue
        else:
            if enable_download != 1:
                print(f"Skipping name {name} because Enable_Download != 1")
                continue

        date_min, date_max, keywords = parse_filter(filter_rule)
        print(f"\nFiltering for actress: {name}, Filter: {filter_rule}")

        for video in videos:
            vid, v_name, v_date, v_title, chinese_sub, state, m3u8 = video
            # print(f"Checking video: {vid}, name={v_name}, title={v_title}, state={state}, m3u8={m3u8}")

            if v_name != name:
                continue
    
            if state in ("download", "no_res", "out_number"):
                continue


            if not m3u8 or not isinstance(m3u8, str) or "http" not in m3u8.lower():
                continue

            # ⭐ 如果标题为空，就用 id 来代替
            if not v_title:
                v_title = vid            
            
            if any(k in vid or k in v_title for k in keywords):
            
                continue

            # ⭐ 如果日期为空，则跳过时间过滤
            if v_date:
                try:
                    dt = datetime.strptime(v_date, "%Y.%m.%d")
                except Exception:
                    dt = None
                if dt:
                    if (date_min and dt < date_min) or (date_max and dt > date_max):
                        continue


            # 返回完整视频信息
            filtered_videos.append(video)

    conn.close()
    return filtered_videos


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

    for source in sources_sorted:
        order = source.get('order', 0)
        if order == 0:
            continue  # 跳过 order=0

        source_name = source.get('name', '')
        name_lower = source_name.lower()

        try:
            if name_lower == "jable":
                m3u8_url, chinese_sub = get_video_info_jable(video_id)
            elif name_lower == "missav":
                m3u8_url, chinese_sub = get_video_info_missav(video_id)
            else:
                print(f"[WARN] Unknown video source: {source_name}")
                continue

            chinese_sub = int(chinese_sub) if chinese_sub else 0

            if m3u8_url == "false":
                # 遇到 false，立即退出，不尝试其他数据源
                return "false", ""
            elif m3u8_url not in ["404", None]:
                # 成功获取
                return m3u8_url, chinese_sub
            # 如果是 "404"，继续尝试下一个 source

        except Exception as e:
            print(f"[ERROR] Error fetching from {source_name} for {video_id}: {e}")
            continue

    # 所有 source 都返回 404
    return "404", ""










def process_video_ids(filtered_videos, video_data_sources, cfg):
    import subprocess
    download_cmds = []

    # 读取下载器配置，按 order 排序，0 表示禁用
    downloader_cfg = cfg.get("Downloader", [])
    downloader_list = []
    for d in downloader_cfg:
        for name, order in d.items():
            if order != 0:   # 0 表示禁用
                downloader_list.append((name, order))
    downloader_list.sort(key=lambda x: x[1])  # 按 order 升序



    if not downloader_list:
        print("No downloader configured!")
        return 1   # 失败状态码

    SavePath_Sub = Path(cfg.get("SavePath_Sub"))
    SavePath_noSub = Path(cfg.get("SavePath_noSub"))
    Proxy_Download = cfg.get("Proxy_Download", "")
    IsNeedDownloadProxy = str(cfg.get("IsNeedDownloadProxy", "0"))

    # 连接数据库
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    all_success = True  # 记录总结果

    for video in filtered_videos:
        # video_id, name, video_date, video_title, chinese_sub, state = video
        video_id, name, video_date, video_title, chinese_sub, state, m3u8 = video

        # # 获取下载 URL
        # m3u8_url = None
        # for source in sorted(video_data_sources, key=lambda x: x.get("order", 0)):
        #     if source.get("order", 0) == 0:
        #         continue
        #     url, sub_flag = fetch_m3u8_by_sources(video_id, source)
            
            
        #     if url and url not in ["false", "404"]:
        #         m3u8_url = url
        #         break


            
        #     if url == "false":
        #         print(f"{video_id} 返回 false，放弃该 ID，继续下一个视频...")
        #         break  # 跳出当前 source 循环，m3u8_url 仍为 None

        #     if url != "404":
        #         m3u8_url = url
        #         break  # 找到有效 URL，停止尝试其他源


        # if not m3u8_url:
        #     print(f"{video_id} 返回的url:{url} 跳过...")
        #     all_success = False
        #     continue
    

        # 获取下载 URL
        m3u8_url = None
        video_data_sources = video_fetch(cfg_path)
        m3u8_url, chinese_sub = fetch_m3u8_by_sources(video_id, video_data_sources)           

        # if m3u8_url and m3u8_url not in ["false", "404"]:
        #     m3u8_url = m3u8_url

        # 新增判断：跳过 false 或 404 的 m3u8_url
        if m3u8_url in ["false", "404"]:
            print(f"Skipping {video_id} because m3u8_url is {m3u8_url}")
            all_success = False
            continue  # 跳过当前视频，继续下一个

    
        save_path = SavePath_Sub if chinese_sub == 1 else SavePath_noSub
        savename = f"{video_id}-C" if chinese_sub == 1 else video_id
        # save_path_real = Path(f"{save_path}/{name}/{video_id}")

        # 根据演员名称调整保存目录
        if name.lower() == "jable_cnsub":
            save_path_real = Path(f"{save_path}/每日更新/{video_id}")
        else:
            save_path_real = Path(f"{save_path}/精选收藏/{name}/{video_id}")

        # # 创建保存目录
        # save_path_real.mkdir(parents=True, exist_ok=True)

        # 依次尝试下载器
        success = False
        for selected_downloader, _ in downloader_list:
            

            
            base_tmp_dir = f"{save_path.parent}/{save_path.name}_tmp/{selected_downloader}"
            # 删除 base_tmp_dir 下的空文件夹（递归）
            if Path(base_tmp_dir).exists():
                for p in sorted(Path(base_tmp_dir).rglob("*"), reverse=True):
                    if p.is_dir() and not any(p.iterdir()):  # 空文件夹
                        p.rmdir()

            tmp_path = f"{base_tmp_dir}/{video_id}" 
            Path(tmp_path).mkdir(parents=True, exist_ok=True)



            # tmp_path = f"{save_path.parent}/{save_path.name}_tmp/{selected_downloader}/{video_id}" 
            Path(tmp_path).mkdir(parents=True, exist_ok=True)

            cmd = build_download_cmd(selected_downloader, m3u8_url, tmp_path, save_path_real, savename, Proxy_Download, IsNeedDownloadProxy)

            print(f"Executing download with {selected_downloader}: {cmd}")
            ret = subprocess.run(cmd, shell=True)
            if ret.returncode == 0:
                mp4_file = save_path_real / f"{savename}.mp4"
                if mp4_file.exists():
                    cursor.execute("UPDATE jav_videos SET state='download' WHERE id=?", (video_id,))
                    conn.commit()
                    print(f"[DB] Set state='download' for ID {video_id}")
                    success = True
                    break
                else:
                    print(f"[WARN] {mp4_file} not found after {selected_downloader}.")
            else:
                print(f"[ERROR] {selected_downloader} failed for {video_id}")

        if not success:
            all_success = False

    conn.close()
    return 0 if all_success else 1

def build_download_cmd(selected_downloader, m3u8_url, tmp_path, save_path_real, savename, Proxy_Download, IsNeedDownloadProxy):
    if selected_downloader == "N_m3u8DL_RE":
        cmd = (
            f"ulimit -n 10000 && "
            f"N_m3u8DL-RE {m3u8_url} "
            f"--auto-select True --thread-count 32 --no-log "
            f"--tmp-dir {tmp_path} "
            f"--save-dir {tmp_path} "
            f"--save-name {savename} "
        )
        # 把代理参数放在 && 前面
        if IsNeedDownloadProxy == "1":
            cmd += f"--custom-proxy {Proxy_Download} "

        # 后处理
        cmd += f"&& mkdir -p {save_path_real} && mv {tmp_path}/{savename}.mp4 {save_path_real} && rm -rf {tmp_path} "

    elif selected_downloader == "m3u8-Downloader-Go":
        go_cmd = (
            f"/m3u8_Downloader/m3u8-Downloader-Go -c 32 -u {m3u8_url} "
            f"-o {tmp_path}/{savename}.ts "
        )
        if IsNeedDownloadProxy == "1":
            go_cmd += f" -p {Proxy_Download}"

        ffmpeg_cmd = (
            f"ffmpeg -i {tmp_path}/{savename}.ts -c copy -f mp4 {tmp_path}/{savename}.mp4 && "          
            f"mkdir -p {save_path_real} && "
            f"mv {tmp_path}/{savename}.mp4 {save_path_real} && "          
            f"rm -rf {tmp_path} "
        )
        cmd = f"{go_cmd} && {ffmpeg_cmd}"

    elif selected_downloader == "m3u8-linux-amd64":
        cmd = (
            f"/m3u8_Downloader/m3u8-linux-amd64 -u {m3u8_url} "
            f"-o {savename} -sp {tmp_path} && "
            f"mkdir -p {save_path_real} && "
            f"mv {tmp_path}/{savename}.mp4 {save_path_real}/"
        )
        if IsNeedDownloadProxy == "1":
            cmd = (
                f"export http_proxy={Proxy_Download} https_proxy={Proxy_Download} && "
                f"/m3u8_Downloader/m3u8-linux-amd64 -u {m3u8_url} "
                f"-o {savename} -sp {tmp_path} && "
                f"mkdir -p {save_path_real} && "
                f"mv {tmp_path}/{savename}.mp4 {save_path_real}/ && "
                "unset http_proxy https_proxy"
            )
    else:
        cmd = "echo 'Unsupported downloader'"
    return cmd

def main():
    create_lock_file()
    try:
        cfg = load_config()

        # 获取命令行指定的演员，支持多个
        target_actresses = sys.argv[1:] if len(sys.argv) > 1 else None

        filtered_videos = filter_videos(target_actresses)
        video_data_sources = video_fetch(cfg_path)
        # process_video_ids(filtered_videos, video_data_sources, cfg)
        exit_code = process_video_ids(filtered_videos, video_data_sources, cfg)    
        sys.exit(exit_code)
    finally:
        delete_lock_file()



if __name__ == "__main__":
    main()