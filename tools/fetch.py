import subprocess
import time
from pathlib import Path
from playwright.sync_api import sync_playwright
import socket
import sys
import yaml
from curl_cffi import requests  # 使用 curl_cffi 提供的 requests
from typing import Optional  # 导入 Optional 类型

# 获取当前脚本路径
CURRENT_FILE = Path(__file__).resolve()

# 找到项目根目录（假设项目根目录下有 cfg 目录）
PROJECT_ROOT = next(p for p in CURRENT_FILE.parents if (p / "cfg").exists())

# 将项目根目录加入 sys.path
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

CONFIG_FILE = PROJECT_ROOT / "cfg" / "config.yaml"
# 直接加载 YAML 文件
with open(CONFIG_FILE, "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)


# ---------------- 抓取模式配置 ----------------
# 可选值: "local_chrome", "playwright_chromium", "curl_cffi"
FETCH_MODE = config.get("FetchMode", "playwright_chromium")  # 从配置读取，默认使用 playwright_chromium

# ---------------- 主抓取函数（根据模式选择） ----------------
def fetch_html(url: str, referer: str = "") -> Optional[str]:
    """根据配置的抓取模式选择不同的实现"""
    if FETCH_MODE == "local_chrome":
        return fetch_html_local_chrome(url)
    elif FETCH_MODE == "curl_cffi":
        return fetch_html_curl(url, referer)
    elif FETCH_MODE == "playwright_chromium":
        return fetch_html_playwright(url)
    else:  # 明确指定默认情况
        return fetch_html_curl(url)


# ---------------- Chrome 配置 ----------------
CHROME_PATH = PROJECT_ROOT / "chrome/chrome-mac-x64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"
ADGUARD_EXTENSION_PATH = PROJECT_ROOT / "chrome/extensions/AdguardBrowser"
DEBUG_PORT = 9222
USER_DATA_DIR = PROJECT_ROOT / "tmp/playwright_user_data"

# ---------------- 工具函数 ----------------
def is_debug_port_open(port: int) -> bool:
    """检查 remote-debugging 端口是否被 Chrome 占用"""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.settimeout(0.5)
            s.connect(("127.0.0.1", port))
            return True
        except:
            return False

# 增加代理参数
def start_chrome():
    """启动 Chrome，如果没运行"""
    if is_debug_port_open(DEBUG_PORT):
        return
    USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    # 构建启动参数
    chrome_args = [
        str(CHROME_PATH),
        f"--remote-debugging-port={DEBUG_PORT}",
        f"--load-extension={ADGUARD_EXTENSION_PATH}",
        f"--user-data-dir={USER_DATA_DIR}",
        "--no-first-run",
        "--no-default-browser-check"
    ]
    
    # 添加代理参数
    if config.get("IsNeedFetchProxy") == "1":
        proxy_server = config.get("Proxy_Fetch")
        if proxy_server:
            chrome_args.append(f"--proxy-server={proxy_server}")
    
    subprocess.Popen(chrome_args)
    
    # 等待 Chrome 启动
    print("启动 Chrome 中，请稍候...")
    for i in range(10):
        if is_debug_port_open(DEBUG_PORT):
            break
        time.sleep(0.5)
    else:
        raise RuntimeError("Chrome 启动失败或调试端口无法连接")

# # ---------------- 抓取函数(本地chrome-test) ----------------
def fetch_html_local_chrome(url: str) -> str:
    """在已有 Chrome 中新建标签页抓取 HTML，抓取后关闭该标签页"""
    start_chrome()
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(f"http://127.0.0.1:{DEBUG_PORT}")
        # 复用第一个上下文
        if not browser.contexts:
            context = browser.new_context()
        else:
            context = browser.contexts[0]
        page = context.new_page()
        page.goto(url, wait_until="load")
        html = page.content()
        page.close()
        return html

# # 可行，但无法并行
# def fetch_html(url: str) -> str:
#     """复用同一个页面进行导航，避免新建标签页"""
#     start_chrome()
#     with sync_playwright() as p:
#         browser = p.chromium.connect_over_cdp(f"http://127.0.0.1:{DEBUG_PORT}")
        
#         if not browser.contexts:
#             context = browser.new_context(viewport=None)
#             page = context.new_page()
#         else:
#             context = browser.contexts[0]
#             # 复用第一个页面而不是创建新页面
#             page = context.pages[0] if context.pages else context.new_page()
        
#         # 保存当前URL（可选）
#         original_url = page.url
        
#         # 在同一个页面中导航
#         page.goto(url, wait_until="load")
#         html = page.content()
        
#         # 可以选择返回原页面
#         # if original_url and original_url != "about:blank":
#         #     page.goto(original_url, wait_until="load")
        
#         # 不关闭页面，以便下次复用
#         # page.close()
        
#         return html

# 方案二：使用已有 Chrome 实例 + 高级配置 可行
# Playwright 自带 Chromium

def fetch_html_playwright(url: str) -> str:
    """针对 Cloudflare 优化的无头浏览器配置"""

    # 配置代理
    proxy_server = None
    if config.get("IsNeedFetchProxy") == "1":
        proxy_server = config.get("Proxy_Fetch")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                f"--load-extension={ADGUARD_EXTENSION_PATH}",
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-blink-features=AutomationControlled",
                "--disable-features=VizDisplayCompositor",
                "--disable-background-timer-throttling",
                "--disable-backgrounding-occluded-windows",
                "--disable-renderer-backgrounding",
                "--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ] + ([f"--proxy-server={proxy_server}"] if proxy_server else [])
        )
        
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            extra_http_headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
            }
        )
        
        page = context.new_page()
        
        # 在导航前移除 webdriver 属性
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
            delete navigator.__proto__.webdriver;
        """)
        
        # 设置超时时间
        page.set_default_timeout(30000)
        
        try:
            page.goto(url, wait_until="networkidle", timeout=45000)
            html = page.content()
        except Exception:
            html = ""
        finally:
            browser.close()
        
        return html

# def fetch_html_playwright(url: str) -> str:
#     """针对 Cloudflare 优化的无头浏览器配置"""

#     # 配置代理
#     proxy_server = None
#     if config.get("IsNeedFetchProxy") == "1":
#         proxy_server = config.get("Proxy_Fetch")

#     with sync_playwright() as p:
#         browser = p.chromium.launch(
#             headless=True,  # 保持无头但优化配置
#             args=[
#                 f"--load-extension={ADGUARD_EXTENSION_PATH}",
#                 "--no-first-run",
#                 "--no-default-browser-check",
#                 "--disable-blink-features=AutomationControlled",  # 重要：移除自动化标志
#                 "--disable-features=VizDisplayCompositor",
#                 "--disable-background-timer-throttling",
#                 "--disable-backgrounding-occluded-windows",
#                 "--disable-renderer-backgrounding",
#                 "--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"  # 真实UA
#             ] + ([f"--proxy-server={proxy_server}"] if proxy_server else [])
#         )
        
#         context = browser.new_context(
#             viewport={"width": 1920, "height": 1080},  # 设置真实视口
#             user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
#             extra_http_headers={
#                 "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
#                 "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
#                 "Accept-Encoding": "gzip, deflate, br",
#                 "Cache-Control": "no-cache",
#                 "Pragma": "no-cache",
#             }
#         )
        
#         # 注入脚本移除自动化痕迹
#         page = context.new_page()
        
#         # 在导航前移除 webdriver 属性
#         page.add_init_script("""
#             Object.defineProperty(navigator, 'webdriver', {
#                 get: () => undefined,
#             });
#             delete navigator.__proto__.webdriver;
#         """)
        
#         # 模拟人类行为：随机延迟
#         page.set_default_timeout(30000)
        
#         try:
#             page.goto(url, wait_until="networkidle", timeout=45000)
            
#             # 检查是否被 Cloudflare 拦截
#             if "challenge" in page.url or "cloudflare" in page.content().lower():
#                 print("检测到 Cloudflare 挑战，尝试等待...")
#                 # 等待可能的 JavaScript 挑战
#                 page.wait_for_timeout(5000)
                
#                 # 检查是否仍然在挑战页面
#                 if "challenge" in page.url:
#                     raise Exception("被 Cloudflare 拦截")
            
#             html = page.content()
            
#         except Exception as e:
#             print(f"首次尝试失败: {e}，尝试备用方案")
#             # 备用方案：重新加载或等待更长时间
#             page.wait_for_timeout(10000)
#             page.reload(wait_until="networkidle")
#             html = page.content()
        
#         finally:
#             browser.close()
        
#         return html

# ---------------- 测试 ----------------
if __name__ == "__main__":
    urls = [
        "https://missav.ai/search/300MIUM-1268",
        "https://missav.ai/search/123"
    ]
    for u in urls:
        html = fetch_html(u)
        print(f"{u} => {len(html)} chars")
        print(html[:2000])
    print("浏览器保持打开，可继续抓取更多页面")





# html_content1 = fetch_html("https://jable.tv/videos/jur-413/")
# print(html_content1)


# html_content2 = fetch_html("https://missav.ai/chuc-144-uncensored-leak/")
# print(html_content2)






# # 直接定义一个独立的 fetch_html 函数
def fetch_html_curl(url: str, referer: str = "") -> Optional[str]:
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

# # 使用示例
# # html_content = fetch_html("https://netflav.com/chinese-sub")
# # print(html_content)

# # html_content = fetch_html("https://avbase.net/works/wanz:WAAA-576")
# # print(html_content)

# # html_content = fetch_html("https://jable.tv/videos/jur-413/")
# # print(html_content)