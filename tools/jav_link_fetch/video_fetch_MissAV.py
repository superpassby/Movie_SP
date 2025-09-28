import sys
from pathlib import Path
from bs4 import BeautifulSoup
import js2py
import re
import yaml

# 获取当前脚本路径
CURRENT_FILE = Path(__file__).resolve()

# 找到项目根目录（假设项目根目录下有 cfg 目录）
PROJECT_ROOT = next(p for p in CURRENT_FILE.parents if (p / "cfg").exists())

# 将项目根目录加入 sys.path
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# 现在可以导入 tools.fetch
from tools.fetch import fetch_html

CONFIG_FILE = PROJECT_ROOT / "cfg" / "config.yaml"

# 直接加载 YAML 文件
with open(CONFIG_FILE, "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)


def get_base_url(source_name: str):
    """
    根据输入的 source_name（如 'MissAV'）获取 base_url
    如果未配置则返回 None
    """
    entry = next(
        (d for d in config.get('JAV_Video_DataSources', []) if d.get('name') == source_name),
        None
    )
    if not entry or not entry.get('urls'):
        print(f"[ERROR] {source_name} URL 未配置！")
        return None

    base_url = entry['urls'][0].rstrip("/")
    return base_url

def get_works_url_from_html(html: str, video_id: str):
    """
    从 HTML 中查找 div.content-with-search 下的链接
    - 排除 href 中包含 "search" 的链接
    - 优先返回包含 video_id 和 chinese-subtitle 的链接
    - 如果没有，再返回包含 video_id 但不含 chinese-subtitle 的链接
    返回：
        url_works: 找到的链接 / 'false' / '404'
        chinese_sub: 1/0/'' 
    """
    soup = BeautifulSoup(html, "html.parser")

    target = soup.select_one("div.content-with-search")
    if not target:
        return {"url_works": "false", "chinese_sub": ""}

    links = target.find_all("a", href=True)
    video_id_lower = video_id.lower()

    matched_link = None
    chinese_sub = ""

    # 先找包含 chinese-subtitle 的链接
    for a in links:
        href = a['href']
        href_lower = href.lower()
        if "search" in href_lower:
            continue
        if video_id_lower in href_lower and "chinese-subtitle" in href_lower:
            matched_link = href
            chinese_sub = 1
            break

    # 如果没有找到，再找不包含 chinese-subtitle 的链接
    if not matched_link:
        for a in links:
            href = a['href']
            href_lower = href.lower()
            if "search" in href_lower:
                continue
            if video_id_lower in href_lower:
                matched_link = href
                chinese_sub = 0
                break

    if matched_link:
        url_works = matched_link
    else:
        url_works = "404"
        chinese_sub = ""

    return {"url_works": url_works, "chinese_sub": chinese_sub}


def get_playlist_m3u8_from_html(html):
    """
    从 HTML 字符串中提取执行 JS 后的 playlist.m3u8 链接
    :param html: HTML 内容字符串
    :return: m3u8_url 字符串，如果未找到赋值为 "false"
    """
    soup = BeautifulSoup(html, "html.parser")
    scripts = soup.find_all("script", {"type": "text/javascript"})

    js_code = None
    for s in scripts:
        for line in (s.get_text() or "").splitlines():
            if "function" in line and "m3u8" in line:
                if line.strip().startswith("eval"):
                    js_code = line.strip()[4:]  # 去掉 eval
                else:
                    js_code = line.strip()
                break
        if js_code:
            break

    if js_code:
        encrypted = r"""%s""" % js_code
        unpacked = js2py.eval_js(encrypted)

        # 提取所有 .m3u8 链接
        urls = re.findall(r'https?://[^\s\'";]+\.m3u8', str(unpacked))

        # 找到 playlist.m3u8 的 URL
        m3u8_url = next((u for u in urls if u.endswith("playlist.m3u8")), "false")
    else:
        m3u8_url = "false"

    return m3u8_url

def get_video_info_missav(video_id: str, source: str = "MissAV"):
    """
    根据 video_id 获取视频的 m3u8 链接和字幕信息
    :param video_id: 视频编号
    :param source: 数据源名称，默认 "MissAV"
    :return: m3u8_url, chinese_sub
        - m3u8_url: 链接字符串，如果未找到为 "false"
        - chinese_sub: 1/0/""  如果 m3u8_url 未找到，则为空字符串
    """
    base_url = get_base_url(source)
    if not base_url:
        m3u8_url = "false"
        chinese_sub = ""
        return m3u8_url, chinese_sub

    # 第一次请求搜索页面
    url_search = f"{base_url}/search/{video_id.lower()}"
    html_search = fetch_html(url_search)
    
    if not html_search:
        m3u8_url = "false"
        chinese_sub = ""
        return m3u8_url, chinese_sub
            
    # 解析搜索结果
    result = get_works_url_from_html(html_search, video_id)
    url_works = result["url_works"]
    chinese_sub = result["chinese_sub"]

    m3u8_url = result["url_works"]  # 赋值
    chinese_sub = result["chinese_sub"]
    # print(f"m3u8_url = {m3u8_url}")
    # print(f"chinese_sub = {chinese_sub}")
    
    # 只有 m3u8_url 有效才去请求视频页面解析真正的 m3u8
    if m3u8_url not in ["false", "404"]:
        html_works = fetch_html(m3u8_url)
        if html_works:
            m3u8_url = get_playlist_m3u8_from_html(html_works)
        else:
            m3u8_url = "false"
            chinese_sub = ""  # m3u8 不存在则字幕无效

    # if m3u8_url == "false":
    #     chinese_sub = ""

    return m3u8_url, chinese_sub

if __name__ == "__main__":
    video_id = "300MIUM-1268"
    m3u8_url, chinese_sub = get_video_info_missav(video_id)

    print(f"m3u8_url = {m3u8_url}")
    print(f"chinese_sub = {chinese_sub}")


