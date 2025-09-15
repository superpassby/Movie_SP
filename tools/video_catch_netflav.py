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
from tools.catch import run_curl, config, source

# print("config:", config)
# print("source:", source)


# ------------------ 正式函数 ------------------

def parse_page(html):
    soup = BeautifulSoup(html, 'html.parser')
    title = ""
    actress_name = ""
    avatar_url = ""
    poster_url = ""
    tag_list = ""
    download_path = ""


    # 提取title、actress_name、avatar_url
    # 定位到 <div class="info-header">
    info_header = soup.find('div', class_='info-header')
    if info_header:
        # 提取 <h4> title
        h4_tag = info_header.find('h4')
        if h4_tag:
            title = h4_tag.get_text().strip()
        # else:
        #     title = ""

        # 提取 <img> 的 title 属性和 src 属性
        img_tag = info_header.find('img', class_='avatar rounded-circle')
        if img_tag:
            actress_name = img_tag['title']
            avatar_url = img_tag['src']
        # else:
        #     actress_name = ''
        #     avatar_url = ''

        # print("title:", title)
        # print("actress_name:", actress_name)
        # print("avatar_url:", avatar_url)
    # else:
    #     print("未找到 info-header 区域")

    # 提取 m3u8 相关信息
    # 定位到 <div id="site-content" class="site-content">
    site_content = soup.find('div', id='site-content')
    if site_content:
        # 提取 <video> 的 poster 属性
        video_tag = site_content.find('video', attrs={'poster': re.compile(r'^http.*')})
        if video_tag:
            poster_url = video_tag.get('poster', '')
        # else:
        #     poster_url = ''

        # 提取 <script> 中的 hlsUrl
        script_tag = site_content.find('script', string=re.compile(r'var\s+hlsUrl'))
        if script_tag:
            # 使用正则表达式匹配 hlsUrl
            match = re.search(r"var\s+hlsUrl\s*=\s*['\"]([^'\"]+)['\"]", script_tag.string)
            m3u8_url = match.group(1) if match else ''
        else:
            m3u8_url = 'false'

        # print("poster_url:", poster_url)
        # print("m3u8_url:", m3u8_url)
    else:
        # 检查是否为 404 页面
        title_tag = soup.find('title')
        if title_tag and title_tag.get_text().strip() == '404 Not Found':
            m3u8_url = '404'
        else:
            m3u8_url = 'false'

        # print("未找到 site-content 区域")
        # print("poster_url:", '未知')
        # print("m3u8_url:", m3u8_url)

    # 提取Tags
    # 定位到 <h5 class="tags h6-md">
    tags_h5 = soup.find('h5', class_='tags h6-md')
    if tags_h5:
        # 提取所有 <a> Tags的文本
        tag_links = tags_h5.find_all('a')
        if tag_links:
            # tag_list = [tag.get_text().strip() for tag in tag_links]
            tag_list = ", ".join(tag.get_text().strip() for tag in tag_links)
        else:
            tag_list = ['未知']

        # print("Tags:", ', '.join(tag_list))
        
        # 检查 m3u8_url 是否为 'false' 或 '404'，决定Download_Path
        if m3u8_url in ('false', '404'):
            download_path = ''  # 表示无下载路径
        else:
            # 检查Tags中是否包含“中文字幕”，输出对应Download_Path
            if '中文字幕' in tag_list:
                download_path = config['SavePath_Sub']
            else:
                download_path = config['SavePath_noSub']

    return title, actress_name, avatar_url, poster_url, m3u8_url, tag_list, download_path

# # ------------------ 正式 ------------------
# def main():
#     # if len(sys.argv) < 2:
#     #     print("Usage: python3 Jable.py <video_id>")
#     #     sys.exit(1)

#     # video_id = sys.argv[1].strip()
    
#     video_id = 'apaa-383'
    
#     # 从 config 中获取 的 URL
#     entry = next(
#         (d for d in config['DataSources'] if d.get('name') == 'Jable'),
#         None
#     )
#     if not entry or not entry.get('urls'):
#         print("[ERROR] MissAV URL 未配置！")
#         sys.exit(1)

#     base_url = entry['urls'][0].rstrip("/")

#     url = f"{base_url}/{video_id}/"

#     html = run_curl(url)

#     parse_page(html)
#     title, actress_name, avatar_url, poster_url, m3u8_url, tag_list, download_path = parse_page(html)
#     print(f"title_jable: {title}") 
#     print(f"actress_name_jable: {actress_name}")
#     print(f"avatar_url_jable: {actress_name}")
#     print(f"poster_url_jable: {poster_url}") 
#     print(f"m3u8_ur_jable: {m3u8_url}") 
#     print(f"Tags_jable: {tag_list}") 
#     print(f"download_path: {download_path}") 





# # ------------------ 测试 ------------------
def main():
    # HTML 文件路径，可以改成你需要解析的文件
    html_dir = PROJECT_ROOT / "test_html" / "NetFlav"
    html_files = ["404.html", "cn_sub.html", "cloudflare.html", "nosub.html"]

    for filename in html_files:
        html_path = html_dir / filename
        if not html_path.exists():
            print(f"[WARN] 文件不存在: {html_path}")
            continue

        # 读取本地 HTML
        html = html_path.read_text(encoding="utf-8")

        print(f"\n=== 解析文件: {filename} ===")
        parse_page(html)

        title, actress_name, avatar_url, poster_url, m3u8_url, tag_list, download_path = parse_page(html)

        print(f"title_jable: {title}") 
        print(f"actress_name_jable: {actress_name}")
        print(f"avatar_url_jable: {actress_name}")
        print(f"poster_url_jable: {poster_url}") 
        print(f"m3u8_ur_jable: {m3u8_url}") 
        print(f"Tags_jable: {tag_list}") 
        print(f"download_path: {download_path}") 



if __name__ == "__main__":
    main()