import sys
from pathlib import Path
from bs4 import BeautifulSoup
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
    根据输入的 source_name（如 'Jable'）获取 base_url
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


def parse_video_info(html: str):
    
    soup = BeautifulSoup(html, "html.parser")

    # 1. site-content 是否存在
    site_content = soup.select_one("#site-content")
    if not site_content:
        m3u8_url = "false"
        chinese_sub = ""   # 没有 m3u8，就返回空
        return m3u8_url, chinese_sub

    # 2.1 默认值
    m3u8_url = "404"      # 默认没有找到 m3u8
    chinese_sub = ""      # 没有 m3u8，就返回空

    # 2.2 查找 m3u8
    scripts = site_content.find_all("script")
    for s in scripts:
        if s.string:
            match = re.search(r"var\s+hlsUrl\s*=\s*'([^']+\.m3u8)'", s.string)
            if match:
                m3u8_url = match.group(1)
                chinese_sub = 0   # 找到 m3u8，才去判定字幕
                break

    # 2.3 查找 chinese-subtitle (只有找到 m3u8 才执行)
    if isinstance(chinese_sub, int):  # 说明找到了 m3u8
        text_center = site_content.select_one("div.text-center")
        if text_center:
            links = text_center.find_all("a", href=True)
            for a in links:
                if "chinese-subtitle" in a["href"]:
                    chinese_sub = 1
                    break

    return m3u8_url, chinese_sub


def get_video_info_jable(video_id: str, source: str = "Jable"):
    """
    输入 video_id，输出 m3u8_url 和 chinese_sub
    """
    base_url = get_base_url(source)
    if not base_url:
        m3u8_url = "false"   # 显式赋值
        chinese_sub = ""     # 显式赋值
        return m3u8_url, chinese_sub

    url_works = f"{base_url}/videos/{video_id.lower()}/"
    html_works = fetch_html(url_works)

    m3u8_url, chinese_sub = parse_video_info(html_works)
    return m3u8_url, chinese_sub


# =================== 测试 main ===================
if __name__ == "__main__":
    video_id = "SONE-967"
    m3u8_url, chinese_sub = get_video_info_jable(video_id)

    print(f"m3u8_url = {m3u8_url}")
    print(f"chinese_sub = {chinese_sub}")