import sys
import re
from bs4 import BeautifulSoup
from pathlib import Path

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


# title: MKMP-659 專屬 巨乳辣妹從早到晚吃春藥，汗水與潮液四濺的24小時春藥耐久戰 乙愛麗絲
# actress_name: 乙アリス
# avatar_url: https://assets-cdn.jable.tv/contents/models/2261/s1_s1_alice-otsu.jpg
# poster_url: https://assets-cdn.jable.tv/contents/videos_screenshots/53000/53278/preview.jpg
# m3u8_url: https://asf-doc.mushroomtrack.com/hls/n1uvEuc90bAN0I1sVqJ6Cg/1757926360/53000/53278/53278.m3u8
# Tags: 中文字幕, 角色劇情, 多P群交, 媚藥, 吊帶襪, 美尻, 漁網, 多P, 潮吹, 短髮, 顏射, 巨乳, 少女
# Download_Path: /mnt/mac/SATA_SSD_2T/000-NASSAV/000-Sub/



# ------------------ 正式函数 ------------------

def parse_page(html):
    if not html:
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
    soup = BeautifulSoup(html, 'html.parser')
    title = ""
    actress_name = ""
    avatar_url = ""
    poster_url = ""
    tag_list = ""
    download_path = ""
    chinese_sub = ""

    # 提取title、actress_name、avatar_url
    # 定位到 <div class="info-header">
    info_header = soup.find('meta', property='og:title')
    if info_header:
        # 提取 <h4> title
        title = info_header.get('content', '未知')
    else:
        title = ''
        # print("title:", title)
    # else:
    #     print("未找到 info-header 区域")

    info_actor = soup.find('meta', property='og:video:actor')
    if info_actor:
        actress_name = info_actor.get('content', '未知')
    else:
        actress_name = ''


    info_poster = soup.find('video', attrs={'data-poster': True})
    if info_poster:
        poster_url = info_poster.get('data-poster', '未知')
    else:
        poster_url = ''
        # print("poster_url:", poster_url)
    # else:
    #     print("未找到 info_poster 区域")



    # 查找所有 script 标签
    m3u8_urls = []
    script_tags = soup.find_all("script")

    for s in script_tags:
        content = s.string or s.get_text() or ""
        if not content:
            continue

        # 优先解析 eval 混淆 JS
        if "eval(function(p,a,c,k,e,d)" in content:
            decoded_urls = decode_eval_js(content) or []
            if decoded_urls:
                m3u8_urls.extend(decoded_urls)
                continue  # 继续检查其他 script，可能有更多 URLs

        # 如果不是 eval，直接找普通 m3u8
        m = re.search(r"https?://[^\s'\"]+\.m3u8", content)
        if m:
            m3u8_urls.append(m.group(0).strip())

    # 筛选 URLs：优先包含“1080”，次优先包含“720”，否则取最后一个
    selected_url = None
    if m3u8_urls:
        # 优先找包含“1080”的 URL
        for url in m3u8_urls:
            if "1080" in url:
                selected_url = url
                break
        # 如果没有“1080”，找包含“720”的 URL
        if not selected_url:
            for url in m3u8_urls:
                if "720" in url:
                    selected_url = url
                    break
        # 如果既没有“1080”也没有“720”，取最后一个
        if not selected_url:
            selected_url = m3u8_urls[-1]

    # 打印结果
    if selected_url:
        m3u8_url = selected_url
    else:
        # 检查是否为 404 页面
        p_tag = soup.find('p', class_=re.compile(r'.*'), string='404')
        if p_tag:
            m3u8_url = '404'
        else:
            m3u8_url = 'false'
    
    # 遍历所有 text-secondary div
    Tags = []
    for div in soup.find_all("div", class_="text-secondary"):
        # 先判断这一行是否包含关键字 "genres"
        if any("/genres/" in a.get("href", "") for a in div.find_all("a", href=True)):
            # 抓取这一行所有 <a> 标签的文字
            for a in div.find_all("a", href=True):
                Tags.append(a.get_text(strip=True))
            break  # 找到目标行就退出


    # 类似 title 的判断
    if Tags:
        tag_list = ", ".join(Tags)
    else:
        tag_list = ""
        # print("Tags:", tag_list)
    # else:
    #     print("未找到 Tags 区域")

    # 检查 m3u8_url 是否为 'false' 或 '404'，决定Download_Path
    # 设置 download_path
    if m3u8_url in ('false', '404'):
        download_path = ''  # 表示无下载路径
    elif '中文字幕' in tag_list:
        download_path = config['SavePath_Sub']
        chinese_sub = 1
    else:
        download_path = config['SavePath_noSub']
        chinese_sub = 0

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

def decode_eval_js(js_code: str) -> str:
    """
    解包典型的 eval(function(p,a,c,k,e,d){...})(payload,a,c,k.split('|'),...)
    返回解包后找到的最后一个 .m3u8 URL（若没有则返回 None）。
    """
    # 匹配 eval 混淆 JS 的 payload, a, c, k
    m = re.search(
        r"eval\(function\(p,a,c,k,e,d\).*?\(\s*(['\"])(.+?)\1\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(['\"])(.+?)\5\.split\('\|'\)",
        js_code, re.S
    )
    if not m:
        return None

    payload = m.group(2)
    a = int(m.group(3))
    c = int(m.group(4))
    k = m.group(6).split("|")

    # 按 JS 规则替换 payload 中的数字为对应字符串
    for i in range(c-1, -1, -1):
        if i < len(k) and k[i]:
            pattern = r"\b{}\b".format(base36encode(i))
            payload = re.sub(pattern, k[i], payload)

    # 提取 .m3u8 链接
    urls = re.findall(r"https?://[^\s'\";]+\.m3u8", payload)
    return urls  # 返回所有 URLs，而不是最后一个

def base36encode(number: int) -> str:
    """把 10 进制数字转成 base36（js 中 c.toString(36) 的逆过程）"""
    if number < 0:
        raise ValueError("必须是非负整数")
    digits = "0123456789abcdefghijklmnopqrstuvwxyz"
    res = ""
    while number:
        number, i = divmod(number, 36)
        res = digits[i] + res
    return res or "0"


#------------------ 正式 ------------------
def main():
    if len(sys.argv) < 2:
        print("Usage: python3 Jable.py <video_id>")
        sys.exit(1)

    video_id = sys.argv[1].strip()
    
    # video_id = 'soe-198'

    # 从 config 中获取 的 URL
    entry = next(
        (d for d in config['JAV_Video_DataSources'] if d.get('name') == 'MissAV'),
        None
    )
    if not entry or not entry.get('urls'):
        print("[ERROR] MissAV URL 未配置！")
        sys.exit(1)

    base_url = entry['urls'][0].rstrip("/")

    # 第一次请求 MissAV 中文字幕页面
    url = f"{base_url}/{video_id}-chinese-subtitle"
    html = fetch_html(url)
    result = parse_page(html)


    # 如果 m3u8_url 返回 404，则请求 MissAV 原始页面
    if result.get("m3u8_url") == '404':
        url = f"{base_url}/{video_id}/"
        html = fetch_html(url)
        result = parse_page(html)
    
    # 打印结果
    print("title_missav:", result.get("title", ""))
    print("actress_name_missav:", result.get("actress_name", ""))
    print("avatar_url_missav:", result.get("avatar_url", ""))
    print("poster_url_missav:", result.get("poster_url", ""))
    print("m3u8_url_missav:", result.get("m3u8_url", "false"))
    print("tags_missav:", result.get("tag_list", ""))
    print("download_path:", result.get("download_path", ""))
    print("chinese_sub:", result.get("chinese_sub", ""))


# # # # ------------------ 测试 ------------------
# def main():
#     # HTML 文件路径，可以改成你需要解析的文件
#     html_dir = PROJECT_ROOT / "test_html" / "MissAV"
#     html_files = ["404.html", "cn_sub.html", "cloudflare.html", "nosub.html", "1080.html", "480.html"]

#     for filename in html_files:
#         html_path = html_dir / filename
#         if not html_path.exists():
#             print(f"[WARN] 文件不存在: {html_path}")
#             continue

#         # 读取本地 HTML
#         html = html_path.read_text(encoding="utf-8")

#         print(f"\n=== 解析文件: {filename} ===")
        
#         result = parse_page(html)

#         print("title_missav:", result.get("title", ""))
#         print("actress_name_missav:", result.get("actress_name", ""))
#         print("avatar_url_missav:", result.get("avatar_url", ""))
#         print("poster_url_missav:", result.get("poster_url", ""))
#         print("m3u8_url_missav:", result.get("m3u8_url", "false"))
#         print("Tags_missav:", result.get("tag_list", ""))
#         print("download_path:", result.get("download_path", ""))
#         print("chinese_sub:", result.get("chinese_sub", ""))



if __name__ == "__main__":
    main()
