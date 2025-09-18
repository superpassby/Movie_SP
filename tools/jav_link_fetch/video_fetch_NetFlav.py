import sys
import re
from bs4 import BeautifulSoup
from pathlib import Path
import json
import js2py


# ------------------ 动态添加项目根目录 ------------------
# 1. 获取当前脚本文件路径
CURRENT_FILE = Path(__file__).resolve()

# 2. 找到项目根目录（假设项目根目录下有 cfg 目录）
PROJECT_ROOT = next(p for p in CURRENT_FILE.parents if (p / "cfg").exists())

# 3. 将项目根目录加入 Python 模块搜索路径
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
# ------------------ 导入项目模块 ------------------
from tools.fetch import fetch_html, config

# print("config:", config)




def search_startpage(html_search: str) -> str:
    """
    从 Startpage 搜索结果 HTML 中提取 NetFlav 视频链接
    """
    # 使用正则查找 URL
    match = re.search(r'https://(?:www\.)?netflav\.com/video\?id=[\w\d_-]+', html_search)
    if match:
        url = match.group(0)
        print(f"[INFO] 找到视频 URL: {url}")
        return url
    else:
        print("[WARN] 未找到视频 URL")
        # 检查是否搜索结果为空
        if "there are no results for this search" in html_search.lower():
            print("[INFO] 搜索结果为空")
            return {
                "title": "",
                "actress_name": "",
                "avatar_url": "",
                "poster_url": "",
                "m3u8_url": "404",
                "tag_list": "",
                "download_path": "",
                 "chinese_sub": ""
            }
        else:
            print("=== Startpage 搜索结果 HTML ===")
            print(html_search)
            print("=== End of HTML ===\n")
            return {
                "title": "",
                "actress_name": "",
                "avatar_url": "",
                "poster_url": "",
                "m3u8_url": "false",
                "tag_list": "",
                "download_path": "",
                 "chinese_sub": ""
            }




# ------------------ 正式函数 ------------------

def parse_page(html_video):
    if not html_video:
        print("[ERROR] 页面内容为空，跳过解析")
        return {
            "title": "",
            "actress_name": "",
            "avatar_url": "",
            "poster_url": "",
            "m3u8_url": "false",
            "tag_list": "",
            "download_path": "",
             "chinese_sub": ""
        }

    soup = BeautifulSoup(html_video, 'html.parser')

    # 找到 __NEXT_DATA__ 脚本
    next_data_script = soup.find("script", {"id": "__NEXT_DATA__"})
    if not next_data_script:
        print("[ERROR] 页面中没有找到 __NEXT_DATA__ 脚本")
        return {
            "title": "",
            "actress_name": "",
            "avatar_url": "",
            "poster_url": "",
            "m3u8_url": "false",
            "tag_list": "",
            "download_path": "",
            "chinese_sub": ""
        }

    try:
        data = json.loads(next_data_script.string)
        # 关键修正：路径是 props -> initialState -> video -> data
        video_data = data.get("props", {}).get("initialState", {}).get("video", {}).get("data", {})

        # 提取演员（只取 zh: 前缀）
        title = video_data.get("title_zh", "")
        title_sub = video_data.get("title", "")
        
        # 根据 title_sub 判断下载路径
        if "中文字幕" in title_sub:
            download_path = config["SavePath_Sub"]
            chinese_sub = 1
        else:
            download_path = config["SavePath_noSub"]
            chinese_sub = 0

        # 提取演员（中文名）
        actors = video_data.get("actors", [])
        actress_name = ",".join([a.replace("zh:", "") for a in actors if a.startswith("zh:")])


        # 提取封面图 preview_hp
        poster_url = video_data.get("preview_hp", "")

        # 提取 tags（只取 zh: 前缀）
        tags = video_data.get("tags", [])
        tag_list = ",".join([t.replace("zh:", "") for t in tags if t.startswith("zh:")])

        # 提取 srcs 第一个
        srcs = video_data.get("srcs", [])
        if srcs:
            html_m3u8 = fetch_html(srcs[0])
            m3u8_url = get_m3u8(html_m3u8)
        else:
            m3u8_url = "false"
        

    except Exception as e:
        print(f"[ERROR] JSON解析失败: {e}")
        return {
            "title": "",
            "actress_name": "",
            "avatar_url": "",
            "poster_url": "",
            "m3u8_url": "false",
            "tag_list": "",
            "download_path": ""
        }

    return {
        "title": title,
        "actress_name": actress_name,
        "avatar_url": "",      # 页面没提供头像，先空
        "poster_url": poster_url,
        "m3u8_url": m3u8_url,
        "tag_list": tag_list,
        "download_path": download_path,
        "chinese_sub": chinese_sub
    }


def get_m3u8(html_m3u8: str) -> str:
    """
    从 HTML 内容中提取 eval(function(...)) 的 JS 代码并解码得到 m3u8 链接
    :param html_m3u8: HTML 内容字符串
    :return: m3u8 URL，如果未找到返回空字符串
    """
    js_code = ""
    for line in html_m3u8.splitlines():
        if "eval(function" in line:
            # print("[FOUND LINE]", line)
            idx = line.find("(function")
            js_code = r"""{}""".format(line[idx:])
            break

    if not js_code:
        print("[WARN] 未找到 eval(function)")
        return ""

    try:
        # 执行 JS 代码
        result = js2py.eval_js(js_code)
        # 提取 m3u8 URL
        urls = re.findall(r'https?://[^\s\'"]+\.m3u8[^\s\'"]*', str(result))
        if urls:
            return urls[0]
    except Exception as e:
        print(f"[ERROR] js2py 执行失败: {e}")
        return ""
    
    print("[WARN] 未找到 m3u8 URL")
    return ""

# # # # ------------------ 正式 ------------------
def main():
    # if len(sys.argv) < 2:
    #     print("Usage: python3 Jable.py <video_id>")
    #     sys.exit(1)

    # video_id = sys.argv[1].strip()
    
    video_id = 'hmn-684'
    
    # 从 config 中获取 NetFlav 的 URL
    entry = next(
        (d for d in config['JAV_Video_DataSources'] if d.get('name') == 'NetFlav'),
        None
    )
    if not entry or not entry.get('urls'):
        print("[ERROR] NetFlav URL 未配置！")
        sys.exit(1)

    # 获取 NetFlav 的基础 URL 并去掉 http/https 前缀
    netflav_url = entry['urls'][0].rstrip("/")
    # 移除 http:// 或 https:// 前缀
    domain = netflav_url.replace("https://", "").replace("http://", "")
    
    # 构建 Startpage 搜索 URL
    search_url = f"https://www.startpage.com/sp/search?query=site%3A{domain}+intitle%3A{video_id}"
    
    print(f"搜索URL: {search_url}")
    # 接下来可以使用这个 search_url 进行搜索

    
    html_search = fetch_html(search_url)
    # 统一结果字典（初始化为空）
    result = {
        "title": "",
        "actress_name": "",
        "avatar_url": "",
        "poster_url": "",
        "m3u8_url": "false",
        "tag_list": "",
        "download_path": "",
        "chinese_sub": ""

    }
    if not html_search:
        print("[ERROR] 获取搜索页面失败，返回默认结果")
        print("m3u8_url_netflav:", result.get("m3u8_url", "false"))
        print("chinese_sub:", result.get("chinese_sub", ""))
        sys.exit(1)   # 直接中止程序
        return result

    # 从搜索结果提取视频 URL
    video_url = search_startpage(html_search)

    # 初始化统一 result 字典
    result = {
        "title": "",
        "actress_name": "",
        "avatar_url": "",
        "poster_url": "",
        "m3u8_url": "false",
        "tag_list": "",
        "download_path": "",
        "chinese_sub": ""
    }

    # 如果返回的是字典，且 m3u8_url 为 "404" 或 "false"
    if isinstance(video_url, dict) and video_url.get("m3u8_url") in ("404", "false"):
        print("[INFO] 视频不可用，m3u8_url=404 或 false，跳过后续解析")
        result = video_url  # 直接用返回的字典
    elif video_url:
        print(f"视频 URL: {video_url}")
        html_video = fetch_html(video_url)
        page_result = parse_page(html_video)
        if page_result.get("m3u8_url") not in ("false", "404"):
            result.update(page_result)

    # 统一打印
    print("title_netflav:", result.get("title", ""))
    print("actress_name_netflav:", result.get("actress_name", ""))
    print("avatar_url_netflav:", result.get("avatar_url", ""))
    print("poster_url_netflav:", result.get("poster_url", ""))
    print("m3u8_url_netflav:", result.get("m3u8_url", "false"))
    print("tags_netflav:", result.get("tag_list", ""))
    print("download_path:", result.get("download_path", ""))
    print("chinese_sub:", result.get("chinese_sub", ""))

# # ------------------ 测试 ------------------
# def main():
#     # HTML 文件路径，可以改成你需要解析的文件
#     html_dir = PROJECT_ROOT / "test_html" / "NetFlav"
#     html_files = ["404.html", "cn_sub.html", "cloudflare.html", "nosub.html", "m3u8.html"]


#     htmll_m3u8_path = html_dir / "m3u8.html"

#     html_m3u8 = htmll_m3u8_path.read_text(encoding="utf-8")
#     m3u8_url = get_m3u8(html_m3u8)
#     # print("m3u8_url:", m3u8_url)

#     for filename in html_files:
#         html_path = html_dir / filename
#         if not html_path.exists():
#             print(f"[WARN] 文件不存在: {html_path}")
#             continue

#         # 读取本地 HTML
#         html_video = html_path.read_text(encoding="utf-8")

#         print(f"\n=== 解析文件: {filename} ===")
#         # parse_page(html_video)

#         result = parse_page(html_video)

#         print("title_netflav:", result.get("title", ""))
#         print("actress_name_netflav:", result.get("actress_name", ""))
#         print("avatar_url_netflav:", result.get("avatar_url", ""))
#         print("poster_url_netflav:", result.get("poster_url", ""))
#         print("m3u8_url_netflav:", result.get("m3u8_url", "false"))
#         print("Tags_netflav:", result.get("tag_list", ""))
#         print("download_path:", result.get("download_path", ""))
#         print("chinese_sub:", result.get("chinese_sub", ""))



if __name__ == "__main__":
    main()