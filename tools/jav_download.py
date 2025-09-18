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

def create_lock_file():
    if LOCK_FILE.exists():
        print("存在锁文件，请检查。")
        sys.exit(0)
    LOCK_FILE.touch()
    print("锁文件 'work' 已创建。")

def delete_lock_file():
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
def filter_videos():
    sources = load_sources()

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, date, title, chinese_sub, state FROM jav_videos")
    videos = cursor.fetchall()
    print(f"\nTotal videos in DB: {len(videos)}")

    filtered_videos = []

    for s in sources:
        name = s["Name"]
        enable_download = s.get("Enable_Download", 1)
        filter_rule = s.get("Filter", "")  # 避免使用 Python 保留字 filter

        if enable_download != 1:
            print(f"Skipping name {name} because Enable_Download != 1")
            continue

        date_min, date_max, keywords = parse_filter(filter_rule)
        print(f"\nFiltering for actress: {name}, Filter: {filter_rule}")

        for video in videos:
            vid, v_name, v_date, v_title, chinese_sub, state = video
            print(f"Checking video: {vid}, name={v_name}, title={v_title}, state={state}")

            if v_name != name:
                continue
            if state in ("download", "no_res", "out_number"):
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

# ------------------ 调用外部脚本获取 m3u8_url ------------------
def fetch_m3u8_url(video_id, video_source):
    try:
        command = [
            'python3',
            str(PROJECT_ROOT / 'tools' / 'jav_link_fetch' / f"video_fetch_{video_source['name']}.py"),
            video_id
        ]

        # 调试：打印即将运行的命令
        print("[DEBUG] Running command:", " ".join(command))

        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0:
            return None, None

        output = result.stdout
        m3u8_url_line = [line for line in output.splitlines() if line.strip().startswith("m3u8_url_")]
        m3u8_url = m3u8_url_line[0].split(":", 1)[-1].strip() if m3u8_url_line else None

        chinese_sub_line = [line for line in output.splitlines() if line.strip().startswith("chinese_sub")]
        chinese_sub = chinese_sub_line[0].split(":", 1)[-1].strip() if chinese_sub_line else None

        return m3u8_url, chinese_sub
    except Exception as e:
        print(f"Exception fetching m3u8_url: {e}")
        return None, None


# def process_video_ids(filtered_videos, video_data_sources, cfg):
#     import subprocess
#     download_cmds = []

#     # 选择下载器：第一个值为1的
#     downloader_cfg = cfg.get("Downloader", [])
#     selected_downloader = None
#     for d in downloader_cfg:
#         for name, flag in d.items():
#             if flag == 1:
#                 selected_downloader = name
#                 break
#         if selected_downloader:
#             break
#     if not selected_downloader:
#         print("No downloader selected!")
#         return

#     SavePath_Sub = Path(cfg.get("SavePath_Sub"))
#     SavePath_noSub = Path(cfg.get("SavePath_noSub"))
#     Proxy_Download = cfg.get("Proxy_Download", "")
#     IsNeedDownloadProxy = str(cfg.get("IsNeedDownloadProxy", "0"))

#     # 连接数据库
#     conn = sqlite3.connect(db_path)
#     cursor = conn.cursor()

#     for video in filtered_videos:
#         video_id, name, video_date, video_title, chinese_sub, state = video

#         # 获取下载 URL（调用现有 fetch_m3u8_url）
#         m3u8_url = None
#         for source in sorted(video_data_sources, key=lambda x: x.get("order", 0)):
#             if source.get("order", 0) == 0:
#                 continue
#             url, sub_flag = fetch_m3u8_url(video_id, source)
#             if url and url not in ["false", "404"]:
#                 m3u8_url = url
#                 break
#         if not m3u8_url:
#             print(f"{video_id} 返回的url:{url} 跳过...")
#             continue  # 全部失败或 false/404，跳过该 ID

#         # 根据 chinese_sub 选择保存目录
#         save_path = SavePath_Sub if chinese_sub == 1 else SavePath_noSub
#         # 根据 chinese_sub 构建保存文件名
#         savename = f"{video_id}-C" if chinese_sub == 1 else video_id
        
#         save_path_real = f"{save_path}/{name}/{video_id}"
#         save_path_real = Path(save_path_real)  # 转换成 Path
#         Path(save_path_real).mkdir(parents=True, exist_ok=True)

#         tmp_path = f"{save_path.parent}/{save_path.parent.name}_tmp/{selected_downloader}/{video_id}" 
#         Path(tmp_path).mkdir(parents=True, exist_ok=True)


#         # 构建下载命令
#         if selected_downloader == "N_m3u8DL_RE":
#             # cmd = f"{PROJECT_ROOT}/tools/m3u8_Downloader/N_m3u8DL-RE {m3u8_url} --auto-select True --thread-count 32 --tmp-dir {save_path}/000-TMP --save-dir {save_path_real} --save-name {savename}"
#             cmd = (
#                 f"{PROJECT_ROOT}/tools/m3u8_Downloader/N_m3u8DL-RE {m3u8_url} "
#                 f"--auto-select True --thread-count 32 "
#                 f"--tmp-dir {tmp_path} "
#                 f"--save-dir {save_path_real} "
#                 f"--save-name {savename}"
#             )
            
#             if IsNeedDownloadProxy == "1":
#                 cmd += f" --custom-proxy {Proxy_Download}"

#         elif selected_downloader == "m3u8-Downloader-Go":
#             go_cmd = (
#                 f"{PROJECT_ROOT}/tools/m3u8_Downloader/m3u8-Downloader-Go -c 32 -u {m3u8_url} "
#                 f"-o {tmp_path}/{video_id}.ts "
#             )
            
#             if IsNeedDownloadProxy == "1":
#                 go_cmd += f" -p {Proxy_Download}"

#             ffmpeg_cmd = (
#                 f"ffmpeg -i {tmp_path}/{video_id}.ts -c copy -f mp4 {save_path_real}/{savename}.mp4 && "
#                 f"rm {tmp_path}/{video_id}.ts "
#             )

#             cmd = f"{go_cmd} && {ffmpeg_cmd}"

#         elif selected_downloader == "m3u8-linux-amd64":
#             # cmd = f"{PROJECT_ROOT}/tools/m3u8_Downloader/m3u8-linux-amd64 -u {m3u8_url} -o {savename} -sp {save_path_real}"
#             cmd = (
#             f"{PROJECT_ROOT}/tools/m3u8_Downloader/m3u8-linux-amd64 -u {m3u8_url} "
#             f"-o {savename} -sp {tmp_path} && "
#             f"mv {tmp_path} {save_path_real}"
#             )
            

#             if IsNeedDownloadProxy == "1":
#                 cmd = (
#                 f"export http_proxy={Proxy_Download} https_proxy={Proxy_Download} && "
#                 f"{PROJECT_ROOT}/tools/m3u8_Downloader/m3u8-linux-amd64 -u {m3u8_url} "
#                 f"-o {savename} -sp {tmp_path} && "
#                 f"mv {tmp_path} {save_path_real.parent} && "
#                 "unset http_proxy https_proxy"
#                 )


#         # 执行下载
#         print(f"Executing download: {cmd}")
#         subprocess.run(cmd, shell=True)

#         # 下载完成后检查 {id}.mp4 是否存在
#         mp4_file = save_path / name / video_id / f"{savename}.mp4"
#         if mp4_file.exists():
#             cursor.execute("UPDATE jav_videos SET state='download' WHERE id=?", (video_id,))
#             conn.commit()
#             print(f"[DB] Set state='download' for ID {video_id}")
#         else:
#             print(f"[WARN] {mp4_file} not found. Skipping DB update.")

#         # 保存命令记录，可选
#         download_cmds.append(cmd)

#     conn.close()

#     print("\nAll download commands executed:")
#     for cmd in download_cmds:
#         print(cmd)

def process_video_ids(filtered_videos, video_data_sources, cfg):
    import subprocess
    download_cmds = []

    # # 读取下载器配置，按 order 排序
    # downloader_cfg = cfg.get("Downloader", [])
    # # 转换为 (name, order) 列表
    # downloader_list = []
    # for d in downloader_cfg:
    #     for name, order in d.items():
    #         downloader_list.append((name, order))
    # downloader_list.sort(key=lambda x: x[1])  # 按 order 升序


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
        video_id, name, video_date, video_title, chinese_sub, state = video

        # 获取下载 URL
        m3u8_url = None
        for source in sorted(video_data_sources, key=lambda x: x.get("order", 0)):
            if source.get("order", 0) == 0:
                continue
            url, sub_flag = fetch_m3u8_url(video_id, source)
            
            
            # if url and url not in ["false", "404"]:
            #     m3u8_url = url
            #     break


            
            if url == "false":
                print(f"{video_id} 返回 false，放弃该 ID，继续下一个视频...")
                break  # 跳出当前 source 循环，m3u8_url 仍为 None

            if url != "404":
                m3u8_url = url
                break  # 找到有效 URL，停止尝试其他源


        if not m3u8_url:
            print(f"{video_id} 返回的url:{url} 跳过...")
            all_success = False
            continue

        save_path = SavePath_Sub if chinese_sub == 1 else SavePath_noSub
        savename = f"{video_id}-C" if chinese_sub == 1 else video_id
        save_path_real = Path(f"{save_path}/{name}/{video_id}")
        save_path_real.mkdir(parents=True, exist_ok=True)

        # tmp_path = Path(f"{save_path.parent}/{save_path.parent.name}_tmp")
        # tmp_path.mkdir(parents=True, exist_ok=True)

        # 依次尝试下载器
        success = False
        for selected_downloader, _ in downloader_list:
            
            tmp_path = f"{save_path.parent}/{save_path.parent.name}_tmp/{selected_downloader}/{video_id}" 
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
            f"{PROJECT_ROOT}/tools/m3u8_Downloader/N_m3u8DL-RE {m3u8_url} "
            f"--auto-select True --thread-count 32 "
            f"--tmp-dir {tmp_path} "
            f"--save-dir {save_path_real} "
            f"--save-name {savename}"
        )
        if IsNeedDownloadProxy == "1":
            cmd += f" --custom-proxy {Proxy_Download}"

    elif selected_downloader == "m3u8-Downloader-Go":
        go_cmd = (
            f"{PROJECT_ROOT}/tools/m3u8_Downloader/m3u8-Downloader-Go -c 32 -u {m3u8_url} "
            f"-o {tmp_path}/{savename}.ts "
        )
        if IsNeedDownloadProxy == "1":
            go_cmd += f" -p {Proxy_Download}"

        ffmpeg_cmd = (
            f"ffmpeg -i {tmp_path}/{savename}.ts -c copy -f mp4 {save_path_real}/{savename}.mp4 && "
            f"rm {tmp_path}/{savename}.ts "
        )
        cmd = f"{go_cmd} && {ffmpeg_cmd}"

    elif selected_downloader == "m3u8-linux-amd64":
        cmd = (
            f"{PROJECT_ROOT}/tools/m3u8_Downloader/m3u8-linux-amd64 -u {m3u8_url} "
            f"-o {savename} -sp {tmp_path} && "
            f"mv {tmp_path}/{savename}.mp4 {save_path_real}/"
        )
        if IsNeedDownloadProxy == "1":
            cmd = (
                f"export http_proxy={Proxy_Download} https_proxy={Proxy_Download} && "
                f"{PROJECT_ROOT}/tools/m3u8_Downloader/m3u8-linux-amd64 -u {m3u8_url} "
                f"-o {savename} -sp {tmp_path} && "
                f"mv {tmp_path}/{savename}.mp4 {save_path_real}/ && "
                "unset http_proxy https_proxy"
            )
    else:
        cmd = "echo 'Unsupported downloader'"
    return cmd


# # ------------------ 主函数 ------------------
# def main():
#     cfg = load_config()
#     filtered_videos = filter_videos()
#     video_data_sources = video_fetch(cfg_path)
#     process_video_ids(filtered_videos, video_data_sources, cfg)

# if __name__ == "__main__":
#     main()

# ------------------ 主函数 ------------------
def main():
    create_lock_file()
    try:
        cfg = load_config()
        filtered_videos = filter_videos()
        video_data_sources = video_fetch(cfg_path)
        process_video_ids(filtered_videos, video_data_sources, cfg)
    finally:
        delete_lock_file()

if __name__ == "__main__":
    main()