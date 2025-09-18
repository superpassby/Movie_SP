import yaml
import subprocess
from pathlib import Path
from curl_cffi import requests  # 使用 curl_cffi 提供的 requests
from typing import Optional



PROJECT_ROOT = next(p for p in Path(__file__).resolve().parents if (p / "cfg").exists())

CONFIG_FILE = PROJECT_ROOT / "cfg" / "config.yaml"
SOURCE_FILE = PROJECT_ROOT / "cfg" / "source.yaml"
ACTRESS_DIR = PROJECT_ROOT / "data"
CURL = PROJECT_ROOT / "tools" / "curl_chrome116"

# 确保目录存在（相当于 mkdir -p）
ACTRESS_DIR.mkdir(parents=True, exist_ok=True)

# 直接加载 YAML 文件
with open(CONFIG_FILE, "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

with open(SOURCE_FILE, "r", encoding="utf-8") as f:
    source = yaml.safe_load(f)

# print("config:", config)
# print("source:", source)


from curl_cffi import requests  # 使用 curl_cffi 提供的 requests
from typing import Optional  # 导入 Optional 类型

# 直接定义一个独立的 fetch_html 函数
def fetch_html(url: str, referer: str = "") -> Optional[str]:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5"
    }

    if referer:
        headers["Referer"] = referer

    proxies = None
    if config.get("IsNeedFetchProxy") == "1":
        proxies = {
            'http': config.get("Proxy_Fetch"),
            'https': config.get("Proxy_Fetch")
        }

    # 打印调试信息，看看是否使用了代理
    print("[DEBUG] URL:", url)
    # print("[DEBUG] Headers:", headers)
    print("[DEBUG] Proxies:", proxies)

    try:
        response = requests.get(
            url,
            headers=headers,
            proxies=proxies,
            timeout=60,
            impersonate="chrome120",
        )
        return response.text
    except Exception as e:
        print("[DEBUG] 请求异常:", e)
        return None

# 使用示例
# html_content = fetch_html("https://netflav.com/chinese-sub")

# html_content = fetch_html("https://avbase.net/works/wanz:WAAA-576")
# print(html_content)
