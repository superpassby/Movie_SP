import sqlite3
import yaml
import subprocess
import sys

from pathlib import Path
from datetime import datetime

# ------------------ 动态添加项目根目录 ------------------
CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = next(p for p in CURRENT_FILE.parents if (p / "cfg").exists())

# 构造数据库路径
db_path = PROJECT_ROOT / 'db' / 'data.db'
cfg_path = PROJECT_ROOT / 'cfg' / 'config.yaml'


# 读取 actresses 表内容
def list_actresses(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT name, filter FROM actresses")
    for row in cursor.fetchall():
        print(f"Name: {row['name']}, Filter: {row['filter']}")

    conn.close()


# 解析过滤规则并应用
def apply_filters(jav_videos, actress, filter_rule, enable_scan):
    if enable_scan == 0:
        return []
    
    filter_rule = filter_rule or ''  # 最小修改，避免 NoneType 报错

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
        if video['chinese_sub'] == 1 or video['state'] in ["skip", "out_number"]:
            continue

        
        if video['date'] is not None:  # 只有有日期时才进行日期过滤
            video_date = datetime.strptime(video['date'], "%Y.%m.%d")
            if (date_min and video_date < date_min) or (date_max and video_date > date_max):
                continue
        
        if any(keyword in video['id'] or keyword in (video['title'] or "") for keyword in keywords):
            continue

        filtered_videos.append(video)

    return filtered_videos


# 列出 jav_videos 并应用过滤
# def list_jav_videos(db_path):
def list_jav_videos(db_path, target_actresses=None):

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT id, name, date, title, chinese_sub, state FROM jav_videos")
    jav_videos = cursor.fetchall()

    cursor.execute("SELECT name, filter, enable_scan FROM actresses")
    actresses = cursor.fetchall()

    all_filtered_videos = []

    for actress_row in actresses:
        actress = actress_row['name']
        # 最小修改：只处理指定演员
        if target_actresses is not None and actress not in target_actresses:
            continue

        filter_rule = actress_row['filter']
        enable_scan = actress_row['enable_scan'] or 0  # 修正可能为 None
        filtered_videos = apply_filters(jav_videos, actress, filter_rule, enable_scan)

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


# 调用外部脚本获取 m3u8_url
def fetch_m3u8_url(id, video_source):
    try:
        command = [
            'python3',
            str(PROJECT_ROOT / 'tools' / 'jav_link_fetch' / f'video_fetch_{video_source["name"]}.py'),
            id
        ]
        result = subprocess.run(command, capture_output=True, text=True)

        if result.returncode != 0:
            print(f"Error running {command}: {result.stderr}")
            return None, None

        output = result.stdout
        print(f"Output from {video_source['name']} for ID {id}: {output}")

        if any(line.strip().startswith("m3u8_url_") and line.strip().endswith("false") for line in output.splitlines()):
            return "false", None

        m3u8_url_line = [line for line in output.splitlines() if line.strip().startswith("m3u8_url_")]
        m3u8_url = m3u8_url_line[0].split(":", 1)[-1].strip() if m3u8_url_line else None

        chinese_sub_line = [line for line in output.splitlines() if line.strip().startswith("chinese_sub")]
        chinese_sub = int(chinese_sub_line[0].split(":", 1)[-1].strip()) if chinese_sub_line else 0

        return m3u8_url, chinese_sub

    except Exception as e:
        print(f"Exception when fetching m3u8_url: {e}")
        return None, None


# 处理筛选后的 ID 并更新数据库
def process_ids(filtered_videos, video_data_sources):
    all_404_ids = []
    m3u8_results = []
    has_false = False   # <<< 标志位

    for video in filtered_videos:
        vid_id = video['id']
        print(f"\nProcessing ID: {vid_id}...")
        attempted_results = []
        skipped_due_to_false = False

        for source in sorted(video_data_sources, key=lambda x: x['order']):
            if source['order'] == 0:
                print(f"Skipping source {source['name']} because order is 0")
                continue

            print(f"Trying source {source['name']}...")
            m3u8_url, chinese_sub = fetch_m3u8_url(vid_id, source)
            attempted_results.append(m3u8_url if m3u8_url else "404")

            if m3u8_url == "false":
                print(f"m3u8_url from {source['name']} is false, skipping ID {vid_id}...")
                skipped_due_to_false = True
                has_false = True  # <<< 只要遇到 false 就记下来
                break

            if not m3u8_url or m3u8_url == "404":
                print(f"m3u8_url from {source['name']} is {m3u8_url}, try next source...")
                continue

            print(f"Success! m3u8_url for ID {vid_id} from {source['name']}: {m3u8_url}")
            m3u8_results.append({
                "ID": vid_id,
                "m3u8_url": m3u8_url,
                "chinese_sub": chinese_sub,
                "source_name": source["name"]
            })
            break

        if skipped_due_to_false:
            continue

        if attempted_results and all(r == "404" for r in attempted_results):
            print(f"All sources returned 404 for ID {vid_id}. Adding to 404 list.")
            all_404_ids.append(vid_id)
        else:
            print(f"Not marking ID {vid_id} as failed (results: {attempted_results}).")

    print(f"\nALL_404 IDs: {all_404_ids}")
    print(f"Success m3u8 URLs: {m3u8_results}")

    edit_db(db_path, all_404_ids, m3u8_results)

    return has_false   # <<< 返回是否出现 false


# 更新数据库
def edit_db(db_path, all_404_ids, m3u8_results):
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        for vid_id in all_404_ids:
            cursor.execute("UPDATE jav_videos SET state = 'no_res' WHERE id = ?", (vid_id,))
            print(f"[DB] Set state = 'no_res' for ID {vid_id}")

        for result in m3u8_results:
            vid_id = result["ID"]
            m3u8_url = result["m3u8_url"]
            chinese_sub_new = result.get("chinese_sub", 0)
            source_name = result.get("source_name", "")

            cursor.execute("SELECT state, chinese_sub FROM jav_videos WHERE id = ?", (vid_id,))
            row = cursor.fetchone()
            if row:
                state_old, chinese_sub_old = row
                if state_old == "download" and chinese_sub_old == 0 and chinese_sub_new == 1:
                    new_state = "new"
                else:
                    new_state = state_old
            else:
                continue  # 没有记录就跳过

            cursor.execute(
                "UPDATE jav_videos SET chinese_sub = ?, m3u8 = ?, m3u8_source = ?, state = ? WHERE id = ?",
                (chinese_sub_new, m3u8_url, source_name, new_state, vid_id)
            )
            print(f"[DB] Updated ID {vid_id}, chinese_sub={chinese_sub_new}, m3u8, m3u8_source={source_name}, state={new_state}")

        conn.commit()
        print("[DB] Database update completed.")
    except Exception as e:
        print(f"[DB] Error updating database: {e}")
    finally:
        conn.close()


# 主函数
def main():
    # 最小修改：接收外部演员参数
    target_actresses = sys.argv[1:] if len(sys.argv) > 1 else None

    # filtered_videos = list_jav_videos(db_path)
    filtered_videos = list_jav_videos(db_path, target_actresses)
    video_data_sources = video_fetch(cfg_path)
    has_false = process_ids(filtered_videos, video_data_sources)

    if has_false:
        sys.exit(1)   # <<< 出现 false，返回错误码 1
    else:
        sys.exit(0)   # <<< 否则返回成功


if __name__ == '__main__':
    main()
